"""Step 5.1: the recogniser's settings, weight pins, audio checks and HTTP (no model needed)."""

import io
import time
import wave
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np
import pytest
from fastapi.testclient import TestClient

from nodetrail_asr.model import (
    FILES,
    TRANSCRIBE_OPTIONS,
    BadAudio,
    PinMismatch,
    Settings,
    check_pins,
    keep_words,
    samples,
    sha256,
)
from nodetrail_asr.server import create_app


def wav(values: list[int], rate: int = 16_000, channels: int = 1) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(np.array(values, dtype="<i2").tobytes())
    return buf.getvalue()


def test_the_spec_settings_are_the_ones_used() -> None:
    o = TRANSCRIBE_OPTIONS
    assert o["language"] == "en" and o["condition_on_previous_text"] is False
    assert o["vad_filter"] is True and o["word_timestamps"] is True
    assert "goes to school" in o["initial_prompt"]  # the verbatim prompt


def test_short_words_are_dropped_and_the_rest_kept_in_order() -> None:
    w = [
        SimpleNamespace(word=" I", start=0.0, end=0.2, probability=0.91),
        SimpleNamespace(word=" uh", start=0.2, end=0.22, probability=0.5),  # 20 ms: an artefact
        SimpleNamespace(word=" goes", start=0.3, end=0.6, probability=0.876543),
    ]
    kept = keep_words(w)
    assert [x.word for x in kept] == ["I", "goes"] and kept[1].probability == 0.877


def test_audio_must_be_16k_mono_pcm() -> None:
    x = samples(wav([0, 16384, -32768]))
    assert x.dtype == np.float32 and x[1] == pytest.approx(0.5) and x[2] == -1.0
    for bad in (wav([0] * 10, rate=44_100), wav([0] * 10, channels=2), b"not audio"):
        with pytest.raises(BadAudio):
            samples(bad)


def test_weights_must_match_their_pins(tmp_path: Path) -> None:
    for name in FILES:
        (tmp_path / name).write_bytes(name.encode())
    pins = {name: sha256(tmp_path / name) for name in FILES}
    check_pins(tmp_path, pins)
    (tmp_path / "model.bin").write_bytes(b"tampered")
    with pytest.raises(PinMismatch, match=r"model\.bin"):
        check_pins(tmp_path, pins)
    (tmp_path / "config.json").unlink()
    with pytest.raises(PinMismatch, match="missing"):
        check_pins(tmp_path, {"config.json": "x"})


def test_settings_read_one_pin_per_file() -> None:
    env = {
        "ASR_MODEL": "Systran/faster-whisper-small.en",
        "ASR_REVISION": "abc",
        "ASR_SHA256_CONFIG": "1",
        "ASR_SHA256_MODEL": "2",
        "ASR_SHA256_TOKENIZER": "3",
        "ASR_SHA256_VOCABULARY": "4",
    }
    s = Settings.from_env(env)
    assert s.pins == {
        "config.json": "1",
        "model.bin": "2",
        "tokenizer.json": "3",
        "vocabulary.txt": "4",
    }
    assert str(s.cache) == "/models"


class Fake:
    def transcribe(self, data: bytes) -> dict[str, Any]:
        samples(data)
        return {"text": "hello", "words": []}


def ready(client: TestClient) -> None:
    for _ in range(50):
        if client.get("/health").status_code == 200:
            return
        time.sleep(0.02)
    raise AssertionError("never ready")


def test_http_answers_after_loading_and_refuses_bad_audio() -> None:
    with TestClient(create_app(Fake)) as client:
        ready(client)
        r = client.post("/transcribe", content=wav([0] * 1600))
        assert r.status_code == 200 and r.json()["text"] == "hello"
        assert client.post("/transcribe", content=b"nope").status_code == 422
        assert client.post("/transcribe", content=b"x" * 5_000_001).status_code == 413


def test_a_model_that_fails_to_load_is_reported() -> None:
    def broken() -> Fake:
        raise PinMismatch("model.bin differs")

    with TestClient(create_app(broken)) as client:
        for _ in range(50):
            r = client.get("/health")
            if "differs" in r.text:
                break
            time.sleep(0.02)
        assert r.status_code == 503 and "model.bin differs" in r.json()["detail"]
        assert client.post("/transcribe", content=wav([0])).status_code == 503
