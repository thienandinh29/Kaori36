"""Whisper small.en through faster-whisper, with the settings measured in docs/v2/asr-candidates.md.

The weights are downloaded once at a pinned revision and checked against SHA-256 pins before
loading; after that the service needs no network. Every setting below is one the spec names
(step 5.1): English-only model, the verbatim prompt, no conditioning on the previous window,
voice activity detection so nothing is transcribed over silence, and words shorter than 50 ms
dropped.
"""

import hashlib
import io
import os
import wave
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

RATE = 16_000
MIN_WORD_SECONDS = 0.05
# An example in the style wanted back: fillers and learner errors kept (asr-candidates.md).
VERBATIM_PROMPT = (
    "Umm, so, uh, I goes to school yesterday and he don't like it. We was, um, very tired, "
    "and my friend have two cat."
)
FILES = ("config.json", "model.bin", "tokenizer.json", "vocabulary.txt")


class BadAudio(ValueError):
    """Not a 16 kHz mono 16-bit PCM WAV."""


class PinMismatch(RuntimeError):
    """A downloaded weight file does not match its SHA-256 pin."""


@dataclass(frozen=True)
class Settings:
    model: str
    revision: str
    pins: Mapping[str, str]  # file name -> SHA-256
    cache: Path
    threads: int

    @classmethod
    def from_env(cls, env: Mapping[str, str] = os.environ) -> "Settings":
        pins = {f: env[f"ASR_SHA256_{f.split('.')[0].upper()}"] for f in FILES}
        return cls(
            model=env["ASR_MODEL"],
            revision=env["ASR_REVISION"],
            pins=pins,
            cache=Path(env.get("ASR_CACHE", "/models")),
            threads=int(env.get("ASR_THREADS", "4")),
        )


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def check_pins(folder: Path, pins: Mapping[str, str]) -> None:
    """Refuse to load weights that differ from their pins (or are missing)."""
    for name, want in pins.items():
        path = folder / name
        if not path.is_file():
            raise PinMismatch(f"{name} is missing")
        got = sha256(path)
        if got != want:
            raise PinMismatch(f"{name}: sha256 {got} differs from the pin {want}")


def fetch(settings: Settings) -> Path:
    """The model folder at the pinned revision, downloaded on first use, checked every start."""
    folder = settings.cache / settings.model.replace("/", "--") / settings.revision
    if not all((folder / f).is_file() for f in FILES):
        from huggingface_hub import snapshot_download

        snapshot_download(
            settings.model,
            revision=settings.revision,
            allow_patterns=list(FILES),
            local_dir=folder,
        )
    check_pins(folder, settings.pins)
    return folder


def samples(data: bytes) -> np.ndarray[Any, np.dtype[np.float32]]:
    """Float samples in [-1, 1] from a 16 kHz mono 16-bit PCM WAV; anything else is refused."""
    try:
        with wave.open(io.BytesIO(data), "rb") as w:
            if (w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getcomptype()) != (
                1, 2, RATE, "NONE"):  # fmt: skip
                raise BadAudio("expected 16 kHz mono 16-bit PCM WAV")
            frames = w.readframes(w.getnframes())
    except (wave.Error, EOFError) as exc:
        raise BadAudio(str(exc)) from None
    pcm = np.frombuffer(frames[: len(frames) // 2 * 2], dtype="<i2")
    return (pcm.astype(np.float32) / 32768.0).astype(np.float32)


@dataclass(frozen=True)
class Word:
    word: str
    start: float
    end: float
    probability: float


def keep_words(words: Iterable[Any]) -> list[Word]:
    """Words of at least 50 ms (shorter ones are looping artefacts), stripped, rounded."""
    out = []
    for w in words:
        text = str(w.word).strip()
        if text and float(w.end) - float(w.start) >= MIN_WORD_SECONDS:
            out.append(
                Word(
                    text,
                    round(float(w.start), 2),
                    round(float(w.end), 2),
                    round(float(w.probability), 3),
                )
            )
    return out


TRANSCRIBE_OPTIONS: dict[str, Any] = {
    "language": "en",
    "beam_size": 5,
    "initial_prompt": VERBATIM_PROMPT,
    "condition_on_previous_text": False,
    "vad_filter": True,
    "word_timestamps": True,
}


class Recogniser:
    def __init__(self, settings: Settings) -> None:
        from faster_whisper import WhisperModel

        self.settings = settings
        folder = fetch(settings)
        self.model = WhisperModel(
            str(folder), device="cpu", compute_type="int8", cpu_threads=settings.threads
        )

    def transcribe(self, data: bytes) -> dict[str, Any]:
        audio = samples(data)
        segments, _info = self.model.transcribe(audio, **TRANSCRIBE_OPTIONS)
        words: list[Word] = []
        for s in segments:
            words += keep_words(s.words or [])
        return {
            "model": self.settings.model,
            "revision": self.settings.revision,
            "seconds": round(len(audio) / RATE, 2),
            "text": " ".join(w.word for w in words),
            "words": [w.__dict__ for w in words],
        }
