"""PRON-001: the recordings. Run from apps/api with the voice service at $TTS (default port 18030).

Two sets, each word said 5 times: (1) from the voice's own British phonemes, with the TRAP vowel swapped for /ɛ/;
(2) natural speech from text, real minimal pairs (bad/bed, man/men, ...). Writes WAVs and cases.json to $OUT.
"""
# ruff: noqa: RUF001
import json
import os

import httpx

from app.evalkit.pron_bench import pad, read_wav, resample, write_wav

T = os.environ.get("TTS", "http://127.0.0.1:18030")
OUT = os.environ.get("OUT", "/tmp/pron-001")
os.makedirs(OUT, exist_ok=True)
CARRIER = (["s", "ˈeɪ", " "], [" ", "ə", "ɡ", "ˈɛ", "n"])
WORDS = ["bad", "man", "black", "hat", "had", "that", "cat", "map", "back", "sad"]
PAIRS = [("bad", "bed", ["b", "æ", "d"]), ("man", "men", ["m", "æ", "n"]), ("had", "head", ["h", "æ", "d"]),
         ("sad", "said", ["s", "æ", "d"]), ("pan", "pen", ["p", "æ", "n"]), ("pat", "pet", ["p", "æ", "t"]),
         ("lad", "led", ["l", "æ", "d"]), ("tan", "ten", ["t", "æ", "n"]), ("mat", "met", ["m", "æ", "t"]),
         ("band", "bend", ["b", "æ", "n", "d"])]  # fmt: skip


def save(name: str, wav: bytes) -> None:
    x, rate = read_wav(wav)
    with open(f"{OUT}/{name}", "wb") as f:
        f.write(write_wav(pad(resample(x, rate))))


cases = []
with httpx.Client(timeout=120) as c:
    ipa = c.post(f"{T}/phonemize", json={"words": WORDS}).json()["ipa"]
    for w in WORDS:
        p = ipa[w]
        trap = "æ" if "æ" in p else "a"
        canon = ["æ" if ch == trap else ch for ch in p if ch not in "ˈˌ"]
        for kind, spoken in (("right", p), ("swapped", p.replace(trap, "ɛ", 1))):
            for r in range(5):
                name = f"{w}-{kind}-{r}.wav"
                phonemes = [*CARRIER[0], *spoken, *CARRIER[1]]
                save(name, c.post(f"{T}/speak-phonemes", json={"phonemes": phonemes}).content)
                cases.append({"set": "phonemes", "word": w, "kind": kind, "file": name,
                              "canonical": ["s", "eɪ", *canon, "ə", "ɡ", "ɛ", "n"],
                              "target": 2 + canon.index("æ")})  # fmt: skip
    for right, wrong, ph in PAIRS:
        for kind, word in (("right", right), ("swapped", wrong)):
            for r in range(5):
                name = f"text-{right}-{kind}-{r}.wav"
                save(name, c.post(f"{T}/speak", json={"text": f"Say {word} again."}).content)
                cases.append({"set": "text", "word": right, "kind": kind, "file": name,
                              "canonical": ["s", "eɪ", *ph, "ə", "ɡ", "ɛ", "n"],
                              "target": 2 + ph.index("æ")})  # fmt: skip
with open(f"{OUT}/cases.json", "w", encoding="utf-8") as f:
    json.dump(cases, f, ensure_ascii=False)
print(len(cases), "recordings in", OUT)
