"""Measure one faster-whisper model on the test audio: text, word timestamps, time, peak memory."""
import json, resource, sys, time, wave
import numpy as np
from faster_whisper import WhisperModel


def load(path):
    with wave.open(path, "rb") as w:
        return np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype("float32") / 32768

model_id, out = sys.argv[1], sys.argv[2]
prompt = sys.argv[3] if len(sys.argv) > 3 else None
cases = json.load(open("/tmp/claude-0/asr/audio/cases.json"))
t0 = time.time()
model = WhisperModel(model_id, device="cpu", compute_type="int8", cpu_threads=4,
                     download_root="/tmp/claude-0/asr/hf")
load_s = time.time() - t0
rows = []
for c in cases:
    t = time.time()
    segs, info = model.transcribe(load(f"/tmp/claude-0/asr/audio/{c['file']}.wav"), language="en", beam_size=5,
                                  word_timestamps=True, condition_on_previous_text=False,
                                  initial_prompt=prompt, vad_filter=False)
    segs = list(segs)
    text = " ".join(s.text.strip() for s in segs)
    words = sum(len(s.words or []) for s in segs)
    rows.append({**c, "hyp": text, "secs": time.time() - t, "timed_words": words})
json.dump({"model": model_id, "prompt": prompt, "load_s": load_s,
           "peak_rss_mb": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, "rows": rows},
          open(out, "w"), indent=1)
print(model_id, "done", round(load_s, 1), "s load")
