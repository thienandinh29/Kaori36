"""The pinned voice: download once, check the SHA-256, speak to WAV bytes, remember recent results.

The voice files come from one commit of `rhasspy/piper-voices`; the service refuses to start without
the pin or when a file does not match it, so the voice cannot change silently.
"""

import hashlib
import io
import os
import urllib.request
import wave
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

Pace = Literal["normal", "slow"]
LENGTH_SCALE: dict[Pace, float] = {"normal": 1.0, "slow": 1 / 0.7}  # slow: 0.7x the speed
REPO = "rhasspy/piper-voices"


@dataclass(frozen=True)
class Pin:
    voice: str  # e.g. en_GB-cori-high
    path: str  # the voice's folder in the repository, e.g. en/en_GB/cori/high
    revision: str  # a full 40-character commit
    model_sha256: str
    config_sha256: str

    @classmethod
    def from_env(cls) -> "Pin":
        keys = ("voice", "path", "revision", "model_sha256", "config_sha256")
        values = {k: os.environ.get(f"TTS_{k.upper()}", "") for k in keys}
        missing = [k for k, v in values.items() if not v]
        if missing:
            raise SystemExit(f"tts: set TTS_{', TTS_'.join(m.upper() for m in missing)}")
        if len(values["revision"]) != 40:
            raise SystemExit("tts: TTS_REVISION must be a full commit hash")
        return cls(**values)

    def url(self, name: str) -> str:
        return f"https://huggingface.co/{REPO}/resolve/{self.revision}/{self.path}/{name}"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def verify(path: Path, expected: str) -> None:
    got = sha256(path)
    if got != expected:
        raise SystemExit(f"tts: {path.name} has SHA-256 {got}, expected {expected}")


Download = Callable[[str, Path], None]


def _download(url: str, dest: Path) -> None:
    tmp = dest.with_suffix(dest.suffix + ".part")
    with urllib.request.urlopen(url, timeout=120) as r, tmp.open("wb") as f:
        while block := r.read(1 << 20):
            f.write(block)
    tmp.replace(dest)


def fetch(pin: Pin, cache: Path, download: Download = _download) -> Path:
    """The model file in `cache`, downloaded on first use; both files checked against the pin."""
    folder = cache / pin.revision
    folder.mkdir(parents=True, exist_ok=True)
    model = folder / f"{pin.voice}.onnx"
    config = folder / f"{pin.voice}.onnx.json"
    for path, digest in ((model, pin.model_sha256), (config, pin.config_sha256)):
        if not path.exists():
            download(pin.url(path.name), path)
        verify(path, digest)
    return model


class Cache:
    """The last `size` results, so a word heard again is not synthesised again."""

    def __init__(self, size: int) -> None:
        self.size = size
        self._items: OrderedDict[tuple[str, Pace], bytes] = OrderedDict()

    def get(self, key: tuple[str, Pace]) -> bytes | None:
        value = self._items.get(key)
        if value is not None:
            self._items.move_to_end(key)
        return value

    def put(self, key: tuple[str, Pace], value: bytes) -> None:
        self._items[key] = value
        self._items.move_to_end(key)
        while len(self._items) > self.size:
            self._items.popitem(last=False)


class Speaker:
    """Text to WAV bytes with one Piper voice, behind a small cache."""

    def __init__(self, model: Path, cache_size: int = 512) -> None:
        from piper import PiperVoice  # imported here so tests run without the engine loaded

        self._voice = PiperVoice.load(model)
        self.cache = Cache(cache_size)

    def __call__(self, text: str, pace: Pace) -> bytes:
        hit = self.cache.get((text, pace))
        if hit is not None:
            return hit
        from piper import SynthesisConfig

        buf = io.BytesIO()
        with wave.open(buf, "wb") as w:
            self._voice.synthesize_wav(
                text, w, syn_config=SynthesisConfig(length_scale=LENGTH_SCALE[pace])
            )
        audio = buf.getvalue()
        self.cache.put((text, pace), audio)
        return audio

    def phonemes(self, phonemes: list[str], pace: Pace) -> bytes:
        """Exact phonemes (the voice's own symbols) to WAV; ValueError for an unknown symbol."""
        import numpy as np
        from piper import SynthesisConfig

        symbols = [c for p in phonemes for c in p]
        unknown = sorted({c for c in symbols if c not in self._voice.config.phoneme_id_map})
        if unknown:
            raise ValueError(f"phonemes the voice does not know: {unknown}")
        ids = self._voice.phonemes_to_ids(symbols)
        samples = self._voice.phoneme_ids_to_audio(
            ids, SynthesisConfig(length_scale=LENGTH_SCALE[pace])
        )
        pcm = (np.clip(np.asarray(samples), -1, 1) * 32767).astype("<i2").tobytes()
        buf = io.BytesIO()
        with wave.open(buf, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(self._voice.config.sample_rate)
            w.writeframes(pcm)
        return buf.getvalue()
