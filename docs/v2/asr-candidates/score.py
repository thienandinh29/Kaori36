"""Score ASR results: WER per set, verbatim keeping of learner errors, fillers kept, speed, memory."""
import json, re, sys, unicodedata

FILLERS = {"um", "uh", "er", "erm", "hmm", "mm", "ah"}
# The learner's error in each sentence of the "errors" set, in order (err-0 ... err-19): kept or hidden?
MARKERS = [r"\bshe go\b", r"\bi buy\b", r"\bhe don't\b", r"\bhave went\b", r"\bis many\b",
           r"\b(am|i'm) agree\b", r"\btwo cat\b", r"\bcan speaks\b", r"\bam study\b", r"\bmore hotter\b",
           r"\bdidn't went\b", r"\binteresting in\b", r"\bwe was\b", r"\bmany student\b", r"\bto meet\b",
           r"\bif i will\b", r"\bsuggested me\b", r"\bsince five\b", r"\bchildrens\b", r"\bmost good\b"]


def norm(s):
    s = unicodedata.normalize("NFC", s).lower().replace("-", " ")
    s = re.sub(r"[^\w\s']", " ", s)
    return s.split()


def edits(a, b):
    d = list(range(len(b) + 1))
    for i in range(1, len(a) + 1):
        prev, d[0] = d[0], i
        for j in range(1, len(b) + 1):
            prev, d[j] = d[j], min(d[j] + 1, d[j - 1] + 1, prev + (a[i - 1] != b[j - 1]))
    return d[-1]


def score(path):
    r = json.load(open(path))
    out = {"model": r["model"] + (" +prompt" if r.get("prompt") else ""), "load_s": round(r["load_s"], 1),
           "peak_rss_mb": round(r["peak_rss_mb"])}
    rows = r["rows"]
    audio = sum(x["sec"] for x in rows)
    out["rtf"] = round(sum(x["secs"] for x in rows) / audio, 3)
    for st in ("read", "read-noisy", "errors"):
        xs = [x for x in rows if x["set"] == st]
        e = sum(edits(norm(x["ref"]), norm(x["hyp"])) for x in xs)
        n = sum(len(norm(x["ref"])) for x in xs)
        out[f"wer_{st}"] = round(e / n, 3)
    errs = [x for x in rows if x["set"] == "errors"]
    kept = [x for x in errs if norm(x["ref"]) == norm(x["hyp"])]
    out["errors_verbatim"] = f"{len(kept)}/{len(errs)}"
    out["errors_changed"] = [(x["ref"], x["hyp"]) for x in errs if norm(x["ref"]) != norm(x["hyp"])]
    hidden = []
    for x in errs:
        i = int(x["file"].split("-")[1])
        if not re.search(MARKERS[i], " ".join(norm(x["hyp"]))):
            hidden.append((x["ref"], x["hyp"]))
    out["errors_kept"] = f"{len(errs) - len(hidden)}/{len(errs)}"
    out["errors_hidden"] = hidden
    fl = [x for x in rows if x["set"] == "fillers"]
    ref_f = sum(sum(w in FILLERS for w in norm(x["ref"])) for x in fl)
    hyp_f = sum(sum(w in FILLERS for w in norm(x["hyp"])) for x in fl)
    out["fillers_kept"] = f"{hyp_f}/{ref_f}"
    out["timestamps"] = all(x.get("timed_words", 0) > 0 for x in rows if x["hyp"].strip())
    return out


if __name__ == "__main__":
    for p in sys.argv[1:]:
        s = score(p)
        print({k: v for k, v in s.items() if k not in ("errors_changed", "errors_hidden")})
