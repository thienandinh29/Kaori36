# ruff: noqa: RUF001, RUF002
import base64
import io
import math
import wave
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from nodetrail_pron.model import FILES, Pin, fetch, key
from nodetrail_pron.server import create_app

VOCAB = {"<pad>": 0, "ð": 1, "ɪ": 2, "s": 3, "z": 4}
PIN = Pin("org/model", "a" * 40, {f: "0" * 64 for f in FILES})


def wav(seconds: float = 0.2) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(b"\x00\x00" * int(16000 * seconds))
    return buf.getvalue()


def fake(samples: list[float]) -> list[list[float]]:
    """ "this" said as "ðɪz": blank, ð, ɪ, z, blank (one row per 20 ms frame)."""
    best = [0, 1, 1, 2, 2, 4, 4, 0]
    return [[math.log(0.9 if k == b else 0.025) for k in range(5)] for b in best]


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app(PIN, fake, VOCAB, 0))


def test_recognise_returns_the_heard_phones(client: TestClient) -> None:
    r = client.post("/recognise", content=wav())
    assert r.json() == {"phones": ["ð", "ɪ", "z"], "frames": 8}


def test_score_aligns_the_expected_phones_and_names_a_competitor(client: TestClient) -> None:
    body = {"audio": base64.b64encode(wav()).decode(), "phones": ["ð", "ɪ", "s"]}
    out = client.post("/score", json=body).json()
    assert out["recognised"] == ["ð", "ɪ", "z"]
    ð, _, s = out["phones"]
    assert ð["gop"] > 0 and ð["competitor"] is None and ð["start_ms"] == 20
    assert s["gop"] < 0 and s["competitor"] == "z"  # expected /s/, heard /z/


def test_bad_input_is_refused(client: TestClient) -> None:
    good = base64.b64encode(wav()).decode()
    assert client.post("/score", json={"audio": good, "phones": ["q"]}).status_code == 422
    assert client.post("/score", json={"audio": "!!", "phones": ["s"]}).status_code == 422
    stereo = io.BytesIO()
    with wave.open(stereo, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(b"\x00\x00\x00\x00" * 100)
    assert client.post("/recognise", content=stereo.getvalue()).status_code == 422


def test_fetch_downloads_once_and_refuses_a_changed_file(tmp_path: Path) -> None:
    import hashlib

    content = {f: f.encode() for f in FILES}
    pin = Pin("org/model", "b" * 40, {f: hashlib.sha256(c).hexdigest() for f, c in content.items()})
    calls: list[str] = []

    def download(url: str, dest: Path) -> None:
        calls.append(url)
        dest.write_bytes(content[dest.name])

    folder = fetch(pin, tmp_path, download)
    assert sorted(p.name for p in folder.iterdir()) == sorted(FILES) and len(calls) == len(FILES)
    fetch(pin, tmp_path, download)
    assert len(calls) == len(FILES)  # cached
    (folder / "vocab.json").write_bytes(b"changed")
    with pytest.raises(SystemExit, match=r"vocab\.json"):
        fetch(pin, tmp_path, download)
    assert key("pytorch_model.bin") == "PYTORCH_MODEL"
