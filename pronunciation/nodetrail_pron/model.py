"""The pinned phoneme recogniser: download once, check every file's SHA-256, run on CPU.

`facebook/wav2vec2-xlsr-53-espeak-cv-ft` (Apache-2.0 on its card, trained on Common Voice) outputs
eSpeak-style IPA phonemes per 20 ms frame. The service refuses to start without the full pin or
when a file differs from it, so the model cannot change silently. The weights are a PyTorch
pickle (`pytorch_model.bin`); transformers loads them with `weights_only`, and the SHA-256 pin
makes sure the file is the one that was read.
"""

import hashlib
import io
import json
import os
import urllib.request
import wave
from array import array
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

RATE = 16_000
FILES = ("config.json", "preprocessor_config.json", "vocab.json", "pytorch_model.bin")


@dataclass(frozen=True)
class Pin:
    repo: str
    revision: str  # a full 40-character commit
    sha256: dict[str, str]  # file -> SHA-256

    @classmethod
    def from_env(cls) -> "Pin":
        repo = os.environ.get("PRON_MODEL", "")
        revision = os.environ.get("PRON_REVISION", "")
        hashes = {f: os.environ.get(f"PRON_SHA256_{key(f)}", "") for f in FILES}
        missing = [
            n
            for n, v in (
                ("PRON_MODEL", repo),
                ("PRON_REVISION", revision),
                *((f"PRON_SHA256_{key(f)}", h) for f, h in hashes.items()),
            )
            if not v
        ]
        if missing:
            raise SystemExit(f"pronunciation: set {', '.join(missing)}")
        if len(revision) != 40:
            raise SystemExit("pronunciation: PRON_REVISION must be a full commit hash")
        return cls(repo, revision, hashes)

    def url(self, name: str) -> str:
        return f"https://huggingface.co/{self.repo}/resolve/{self.revision}/{name}"


def key(name: str) -> str:
    return name.split(".")[0].upper().replace("-", "_")  # pytorch_model.bin -> PYTORCH_MODEL


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


Download = Callable[[str, Path], None]


def _download(url: str, dest: Path) -> None:
    tmp = dest.with_suffix(dest.suffix + ".part")
    with urllib.request.urlopen(url, timeout=600) as r, tmp.open("wb") as f:
        while block := r.read(1 << 20):
            f.write(block)
    tmp.replace(dest)


def fetch(pin: Pin, cache: Path, download: Download = _download) -> Path:
    folder = cache / pin.revision
    folder.mkdir(parents=True, exist_ok=True)
    for name in FILES:
        path = folder / name
        if not path.exists():
            download(pin.url(name), path)
        got = sha256(path)
        if got != pin.sha256[name]:
            raise SystemExit(
                f"pronunciation: {name} has SHA-256 {got}, expected {pin.sha256[name]}"
            )
    return folder


class BadAudio(ValueError):
    pass


def read_wav(data: bytes) -> list[float]:
    """Samples in [-1, 1] of a 16 kHz mono 16-bit PCM WAV (what the API stores)."""
    try:
        with wave.open(io.BytesIO(data), "rb") as w:
            if (w.getnchannels(), w.getsampwidth(), w.getframerate()) != (1, 2, RATE):
                raise BadAudio("expected 16 kHz mono 16-bit PCM WAV")
            frames = w.readframes(w.getnframes())
    except (wave.Error, EOFError) as exc:
        raise BadAudio(str(exc)) from None
    pcm: array[int] = array("h")
    pcm.frombytes(frames[: len(frames) // 2 * 2])
    return [s / 32768 for s in pcm]


class Recogniser:
    """Log-probabilities per 20 ms frame over the model's phone tokens."""

    def __init__(self, folder: Path) -> None:
        import torch
        from transformers import Wav2Vec2ForCTC

        torch.set_num_threads(max(1, min(4, os.cpu_count() or 1)))
        self._torch = torch
        model: Any = Wav2Vec2ForCTC.from_pretrained(folder)
        self.model: Any = model.eval()
        self.vocab: dict[str, int] = json.loads((folder / "vocab.json").read_text(encoding="utf-8"))
        self.blank: int = int(self.model.config.pad_token_id)

    def __call__(self, samples: list[float]) -> list[list[float]]:
        torch = self._torch
        x = torch.tensor(samples, dtype=torch.float32)
        x = (x - x.mean()) / torch.sqrt(x.var() + 1e-7)  # the feature extractor's normalisation
        with torch.inference_mode():
            logits = self.model(x.unsqueeze(0)).logits[0]
        return torch.log_softmax(logits, dim=-1).tolist()  # type: ignore[no-any-return]
