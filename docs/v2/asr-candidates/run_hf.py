"""Measure a transformers ASR model (Moonshine or wav2vec2 CTC) on the test audio, inside the pronunciation image."""
import json, resource, sys, time, wave
import numpy as np
import torch
from transformers import AutoProcessor

model_id, out = sys.argv[1], sys.argv[2]
torch.set_num_threads(4)
cases = json.load(open("/data/audio/cases.json"))


def load(path):
    with wave.open(path, "rb") as w:
        return np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype("float32") / 32768


t0 = time.time()
proc = AutoProcessor.from_pretrained(model_id, cache_dir="/data/hf")
ctc = "wav2vec2" in model_id
if ctc:
    from transformers import Wav2Vec2ForCTC
    model = Wav2Vec2ForCTC.from_pretrained(model_id, cache_dir="/data/hf").eval()
else:
    from transformers import MoonshineForConditionalGeneration
    model = MoonshineForConditionalGeneration.from_pretrained(model_id, cache_dir="/data/hf").eval()
load_s = time.time() - t0
rows = []
for c in cases:
    x = load(f"/data/audio/{c['file']}.wav")
    t = time.time()
    inputs = proc(x, sampling_rate=16000, return_tensors="pt")
    with torch.inference_mode():
        if ctc:
            ids = model(**inputs).logits.argmax(-1)
            dec = proc.batch_decode(ids, output_word_offsets=True)
            text, timed = dec.text[0], len(dec.word_offsets[0])
        else:
            limit = int(len(x) / 16000 * 13) + 10  # tokens per second, as the card suggests
            gen = model.generate(**inputs, max_new_tokens=limit)
            text, timed = proc.batch_decode(gen, skip_special_tokens=True)[0], 0
    rows.append({**c, "hyp": text, "secs": time.time() - t, "timed_words": timed})
json.dump({"model": model_id, "load_s": load_s,
           "peak_rss_mb": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, "rows": rows},
          open(out, "w"), indent=1)
print(model_id, "done", round(load_s, 1), "s load")
