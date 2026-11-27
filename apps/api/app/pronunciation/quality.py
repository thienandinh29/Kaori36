"""Is this recording usable? (specs/pronunciation, step 3.1)

Checked before anything else, so a bad recording gets advice ("quá ồn", "quá nhỏ"), never a
judgement of the learner's sounds. Standard library only: the browser sends 16 kHz mono 16-bit WAV.

Levels are in dBFS over 30 ms frames. The speech level is a high percentile of the frame levels,
the noise floor a low one; their difference is a rough signal-to-noise ratio, enough to tell a
quiet room from a noisy one. The thresholds are deliberately lenient; they are tuned on real
recordings in step 3.3.
"""

import io
import math
import wave
from array import array
from dataclasses import dataclass, field
from typing import Literal

RATE = 16_000
MIN_SECONDS, MAX_SECONDS = 1.0, 15.0
FRAME = RATE * 30 // 1000  # 30 ms
QUIET_DB = -40.0  # speech level below this: too quiet
NOISY_SNR_DB = 15.0  # speech this close to the noise floor: too noisy
CLIP_SHARE = 0.005  # more than 0.5% of samples at full scale: distorted
MIN_SPEECH_SECONDS = 0.5  # louder than the floor by 10 dB for at least this long
FULL_SCALE = 32_700

Problem = Literal[
    "format", "too_short", "too_long", "too_quiet", "clipped", "too_noisy", "no_speech"
]


class BadAudio(ValueError):
    """Not a 16 kHz mono 16-bit PCM WAV."""


@dataclass(frozen=True)
class Quality:
    ok: bool
    problems: tuple[Problem, ...] = ()
    seconds: float = 0.0
    speech_db: float | None = None
    noise_db: float | None = None
    snr_db: float | None = None
    speech_seconds: float = 0.0
    notes: list[str] = field(default_factory=list)


def samples(data: bytes) -> array[int]:
    """The 16-bit samples of a 16 kHz mono PCM WAV; anything else is refused."""
    try:
        with wave.open(io.BytesIO(data), "rb") as w:
            if (w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getcomptype()) != (
                1, 2, RATE, "NONE"):  # fmt: skip
                raise BadAudio("expected 16 kHz mono 16-bit PCM WAV")
            frames = w.readframes(w.getnframes())
    except (wave.Error, EOFError) as exc:
        raise BadAudio(str(exc)) from None
    out: array[int] = array("h")
    out.frombytes(frames[: len(frames) // 2 * 2])  # WAV is little-endian, as are our servers
    return out


def _db(rms: float) -> float:
    return 20 * math.log10(max(rms, 1e-9) / 32_768)


def _percentile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, max(0, round(q * (len(ordered) - 1))))]


def check(
    data: bytes,
    min_seconds: float = MIN_SECONDS,
    min_speech: float = MIN_SPEECH_SECONDS,
    max_seconds: float = MAX_SECONDS,
) -> Quality:
    """`min_seconds` and `min_speech` are lower for a single word (step 3.7) than a sentence;
    `max_seconds` is higher for a Speaking answer (step 5.4a) than a read sentence."""
    try:
        x = samples(data)
    except BadAudio:
        return Quality(False, ("format",))
    seconds = len(x) / RATE
    if seconds < min_seconds:
        return Quality(False, ("too_short",), round(seconds, 2))
    if seconds > max_seconds:
        return Quality(False, ("too_long",), round(seconds, 2))
    levels = []
    for start in range(0, len(x) - FRAME + 1, FRAME):
        frame = x[start : start + FRAME]
        levels.append(_db(math.sqrt(sum(s * s for s in frame) / FRAME)))
    speech, noise = _percentile(levels, 0.9), _percentile(levels, 0.1)
    snr = speech - noise
    voiced = sum(1 for level in levels if level > noise + 10 and level > QUIET_DB) * FRAME / RATE
    clipped = sum(1 for s in x if abs(s) >= FULL_SCALE) / len(x)
    problems: list[Problem] = []
    if speech < QUIET_DB:
        problems.append("too_quiet")
    if clipped > CLIP_SHARE:
        problems.append("clipped")
    if speech >= QUIET_DB and snr < NOISY_SNR_DB:
        problems.append("too_noisy")
    if not problems and voiced < min_speech:
        problems.append("no_speech")
    return Quality(
        ok=not problems,
        problems=tuple(problems),
        seconds=round(seconds, 2),
        speech_db=round(speech, 1),
        noise_db=round(noise, 1),
        snr_db=round(snr, 1),
        speech_seconds=round(voiced, 2),
    )


TRIM_BELOW_PEAK_DB = 30.0  # frames this far under the loudest are silence at the edges
TRIM_MARGIN = 0.25  # seconds kept around the speech


def _wav(x: array[int]) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(x.tobytes())
    return buf.getvalue()


def trim(data: bytes, margin: float = TRIM_MARGIN) -> bytes:
    """The recording without the silence before and after the speech (step 3.7c): a learner who
    waits before saying one word, or after, no longer makes it "too quiet". Unreadable audio is
    returned as it is (the check refuses it)."""
    try:
        x = samples(data)
    except BadAudio:
        return data
    levels = [
        _db(math.sqrt(sum(s * s for s in x[i : i + FRAME]) / FRAME))
        for i in range(0, len(x) - FRAME + 1, FRAME)
    ]
    if not levels:
        return data
    floor = max(levels) - TRIM_BELOW_PEAK_DB
    loud = [i for i, level in enumerate(levels) if level > floor and level > QUIET_DB - 10]
    if not loud:
        return data
    keep = round(margin * RATE)
    start = max(0, loud[0] * FRAME - keep)
    end = min(len(x), (loud[-1] + 1) * FRAME + keep)
    return _wav(x[start:end])


def pad(data: bytes, seconds: float) -> bytes:
    """Silence added evenly to both ends up to `seconds`, so the aligner always has some context."""
    x = samples(data)
    short = round(seconds * RATE) - len(x)
    if short <= 0:
        return data
    before = array("h", bytes(short // 2 * 2))
    after = array("h", bytes((short - short // 2) * 2))
    return _wav(before + x + after)
