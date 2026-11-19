"""Experiment: score /æ/ against /ɛ/ only (and TRAP vs DRESS phone groups) instead of every phone."""
import json, math, sys
from pathlib import Path
from nodetrail_pron.align import align, gop
from nodetrail_pron.model import Pin, Recogniser, fetch, read_wav

folder = fetch(Pin.from_env(), Path("/models"))
model = Recogniser(folder)
v, blank = model.vocab, model.blank
TRAP = [p for p in ("æ", "a", "aː") if p in v]
DRESS = [p for p in ("ɛ", "e", "eː") if p in v]
def lse(xs): m = max(xs); return m + math.log(sum(math.exp(x - m) for x in xs))
out = []
for c in json.load(open("/data/cases.json")):
    lp = model(read_wav(open(f"/data/{c['file']}", "rb").read()))
    segs = align(lp, [v[p] for p in c["canonical"]], blank)
    seg = segs[c["target"]]
    g = gop(lp, segs, blank)[c["target"]]
    frames = range(seg.start, seg.end)
    a = sum(lp[f][v["æ"]] - lp[f][v["ɛ"]] for f in frames) / len(frames)
    b = sum(lse([lp[f][v[p]] for p in TRAP]) - lse([lp[f][v[p]] for p in DRESS]) for f in frames) / len(frames)
    # frame-max variant: the strongest evidence in the segment
    bmax = max(lse([lp[f][v[p]] for p in TRAP]) - lse([lp[f][v[p]] for p in DRESS]) for f in frames)
    out.append({**{k: c[k] for k in ("set", "word", "kind")}, "gop": g.gop,
                "competitor": g.competitor is not None and g.gop < 0, "a": a, "b": b, "bmax": bmax})
json.dump(out, open("/data/scores.json", "w"))
print(len(out), "scored; trap", TRAP, "dress", DRESS)
