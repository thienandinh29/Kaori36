"""The test audio for the speech recognition study (docs/v2/asr-candidates.md).

Run from apps/api with the voice service at $TTS (default port 18030); writes WAVs and cases.json to $OUT.
"""
import json
import os

import httpx
import yaml  # type: ignore[import-untyped]

from app.evalkit.pron_bench import pad, read_wav, resample, with_noise, write_wav

T = os.environ.get("TTS", "http://127.0.0.1:18030")
OUT = os.environ.get("OUT", "/tmp/claude-0/asr/audio")
os.makedirs(OUT, exist_ok=True)
PROMPTS = [p["text"] for p in yaml.safe_load(open("../../data/pronunciation/prompts.yaml"))["prompts"]]
ERRORS = [  # typical Vietnamese-learner errors; score.MARKERS holds the error in each, in this order
    "She go to school by bus every day.", "Yesterday I buy a new phone.", "He don't like spicy food.",
    "I have went to Da Nang last summer.", "There is many people in the market.", "I am agree with this idea.",
    "My sister have two cat.", "He can speaks English very well.", "I am study at university now.",
    "The weather is more hotter than last year.", "I didn't went to class yesterday.",
    "She is very interesting in music.", "We was very tired after the trip.", "Many student live in dormitory.",
    "I look forward to meet you.", "If I will have time, I will call you.", "He suggested me to go home.",
    "I have lived here since five years.", "Childrens like playing games.",
    "This is the most good restaurant in town.",
]
FILLERS = [
    "Um, I think the city is, uh, very crowded.", "Well, uh, I usually study in the evening.",
    "Um, my hometown is, um, quite small.", "I, uh, I like reading books.",
    "So, um, the main reason is money.", "Uh, I would say, um, it depends.",
]
cases = []
with httpx.Client(timeout=120) as c:

    def make(name: str, text: str, noise: float | None = None) -> float:
        x, rate = read_wav(c.post(f"{T}/speak", json={"text": text}).content)
        y = pad(resample(x, rate))
        if noise is not None:
            y = with_noise(y, noise, seed=len(cases))
        with open(f"{OUT}/{name}.wav", "wb") as f:
            f.write(write_wav(y))
        return len(y) / 16000

    for i, t in enumerate(PROMPTS):
        cases.append({"set": "read", "file": f"read-{i}", "ref": t, "sec": make(f"read-{i}", t)})
        cases.append({"set": "read-noisy", "file": f"noisy-{i}", "ref": t, "sec": make(f"noisy-{i}", t, 10.0)})
    for i, t in enumerate(ERRORS):
        cases.append({"set": "errors", "file": f"err-{i}", "ref": t, "sec": make(f"err-{i}", t)})
    for i, t in enumerate(FILLERS):
        cases.append({"set": "fillers", "file": f"fill-{i}", "ref": t, "sec": make(f"fill-{i}", t)})
with open(f"{OUT}/cases.json", "w") as f:
    json.dump(cases, f, indent=1)
print(len(cases), "recordings")
