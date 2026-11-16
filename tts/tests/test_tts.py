import hashlib
import io
import os
import wave
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from nodetrail_tts.server import create_app
from nodetrail_tts.voice import Cache, Pin, Speaker, fetch, verify

PIN = Pin(
    voice="en_GB-test",
    path="en/en_GB/test/high",
    revision="a" * 40,
    model_sha256=hashlib.sha256(b"model").hexdigest(),
    config_sha256=hashlib.sha256(b"config").hexdigest(),
)


def fake_wav(text: str, pace: str) -> bytes:
    return f"RIFF:{pace}:{text}".encode()


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app(PIN, fake_wav))


def test_speaks_a_word_as_wav(client: TestClient) -> None:
    r = client.post("/speak", json={"text": "important"})
    assert r.status_code == 200
    assert r.headers["content-type"] == "audio/wav"
    assert r.headers["x-voice"] == "en_GB-test"
    assert r.content == b"RIFF:normal:important"


def test_slow_pace_and_text_is_normalised(client: TestClient) -> None:
    r = client.post("/speak", json={"text": "  a piece\n of  cake ", "pace": "slow"})
    assert r.content == b"RIFF:slow:a piece of cake"
    assert client.post("/speak", json={"text": "café au lait"}).content.endswith(
        "café au lait".encode()
    )


@pytest.mark.parametrize(
    "body",
    [
        {"text": ""},
        {"text": "x" * 301},
        {"text": "123 — !!"},
        {"text": "word", "pace": "fast"},
        {"text": "word", "voice": "other"},
    ],
)
def test_refuses_bad_requests(client: TestClient, body: dict[str, str]) -> None:
    assert client.post("/speak", json=body).status_code == 422


def test_health_names_the_pinned_voice(client: TestClient) -> None:
    assert client.get("/health").json() == {
        "status": "ok",
        "voice": "en_GB-test",
        "revision": "a" * 40,
    }


def test_pin_from_env_needs_every_value(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in ("VOICE", "PATH", "REVISION", "MODEL_SHA256", "CONFIG_SHA256"):
        monkeypatch.delenv(f"TTS_{key}", raising=False)
    with pytest.raises(SystemExit, match="TTS_VOICE"):
        Pin.from_env()
    monkeypatch.setenv("TTS_VOICE", "v")
    monkeypatch.setenv("TTS_PATH", "p")
    monkeypatch.setenv("TTS_REVISION", "short")
    monkeypatch.setenv("TTS_MODEL_SHA256", "m")
    monkeypatch.setenv("TTS_CONFIG_SHA256", "c")
    with pytest.raises(SystemExit, match="full commit"):
        Pin.from_env()
    monkeypatch.setenv("TTS_REVISION", "b" * 40)
    assert Pin.from_env().url("x.onnx") == (
        f"https://huggingface.co/rhasspy/piper-voices/resolve/{'b' * 40}/p/x.onnx"
    )


def test_fetch_downloads_once_and_checks_the_pin(tmp_path: Path) -> None:
    calls: list[str] = []

    def download(url: str, dest: Path) -> None:
        calls.append(url)
        dest.write_bytes(b"config" if dest.name.endswith(".json") else b"model")

    model = fetch(PIN, tmp_path, download)
    assert model.name == "en_GB-test.onnx" and model.read_bytes() == b"model"
    assert len(calls) == 2 and calls[0].endswith("/en/en_GB/test/high/en_GB-test.onnx")
    fetch(PIN, tmp_path, download)  # cached: no new download
    assert len(calls) == 2


def test_fetch_refuses_a_changed_file(tmp_path: Path) -> None:
    def download(url: str, dest: Path) -> None:
        dest.write_bytes(b"tampered")

    with pytest.raises(SystemExit, match="expected"):
        fetch(PIN, tmp_path, download)
    good = tmp_path / "f"
    good.write_bytes(b"model")
    verify(good, PIN.model_sha256)


def test_cache_keeps_the_most_recent() -> None:
    c = Cache(2)
    c.put(("a", "normal"), b"1")
    c.put(("b", "normal"), b"2")
    assert c.get(("a", "normal")) == b"1"  # a is now the most recent
    c.put(("c", "normal"), b"3")
    assert c.get(("b", "normal")) is None
    assert c.get(("a", "normal")) == b"1" and c.get(("c", "normal")) == b"3"
    assert c.get(("a", "slow")) is None


@pytest.mark.skipif(not os.environ.get("TTS_TEST_MODEL"), reason="set TTS_TEST_MODEL to a .onnx")
def test_the_real_voice_speaks_and_slow_is_longer() -> None:
    speaker = Speaker(Path(os.environ["TTS_TEST_MODEL"]))

    def seconds(audio: bytes) -> float:
        with wave.open(io.BytesIO(audio)) as w:
            return float(w.getnframes()) / float(w.getframerate())

    normal = speaker("It is important to sleep well.", "normal")
    slow = speaker("It is important to sleep well.", "slow")
    assert normal[:4] == b"RIFF" and seconds(normal) > 1.0
    assert seconds(slow) > seconds(normal) * 1.2
    assert speaker("It is important to sleep well.", "normal") is normal  # from the cache
