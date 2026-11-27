# ruff: noqa: RUF001  (the prompt shows the IPA stress mark)
"""Import NGSL 1.2 and NAWL 1.2, then TSL 1.2 and BSL 1.20, into the vocabulary list.

Specs: specs/vocabulary-import/spec.md and step-tsl-bsl.md.

    python -m app.vocabulary.importer download   # the official files, checked against sources.json
    python -m app.vocabulary.importer run        # model + espeak, resumable; list + report
    python -m app.vocabulary.importer extra      # TSL and BSL, added to the list; never rewrites it
    python -m app.vocabulary.importer sample     # 50 random entries for the owner to mark
    python -m app.vocabulary.importer score      # precision of the marked sample, into the report

The model writes only what the lists do not have (Vietnamese meaning, example, topic, collocation,
part of speech for the NGSL, a British IPA); code checks every entry with the rules of the authored
list and drops what fails. IPA is kept only when espeak-ng agrees (app/vocabulary/ipa.py).
"""

import argparse
import asyncio
import hashlib
import json
import os
import random
import sys
import threading
import urllib.request
from collections import Counter
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

import yaml  # type: ignore[import-untyped]
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.config import REPO_ROOT
from app.llm.gateway import Attempt, Gateway, GenerationLimits
from app.vocabulary import definition_check as dc
from app.vocabulary import headwords as hw
from app.vocabulary.ipa import agree
from app.vocabulary.wordlist import Word, WordList, load_wordlist, occurrences

OUT = REPO_ROOT / "data-sa" / "vocabulary"
WORK = REPO_ROOT / "data" / "private" / "vocab-import"  # downloads and model replies, git-ignored
AUTHORED = REPO_ROOT / "data" / "vocabulary" / "core-seed.yaml"
BATCH = 40
PARALLEL = 4
TASK = "vocab_import"
PosOut = Literal["noun", "verb", "adjective", "adverb", "preposition", "conjunction", "other"]

SYSTEM = """You write learner-dictionary entries for Vietnamese learners of English (IELTS).
For each headword you get its definition in easy English; keep to THAT meaning.
Return for every headword, in the same order:
- lemma: the headword exactly as given
- pos: its part of speech in that meaning (noun, verb, adjective, adverb, preposition, conjunction),
  or "other" for pronouns, determiners, articles, auxiliaries, numbers and interjections
- vi: a short Vietnamese meaning (natural Vietnamese with full diacritics, at most 8 words)
- example: one natural sentence (6-20 words, IELTS-style, no names of real people) that contains the
  headword exactly once, as the headword or one of its inflected forms
- answer: the exact form of the headword used in the example
- topic: one of the topic slugs given, or null when none fits well
- collocation: a short common phrase (2-5 words) with the headword, or null
- collocation_word: the form of the headword in that phrase, or null
- ipa: the British (RP) pronunciation as in a learner's dictionary, between slashes, with the
  primary stress mark ˈ before the stressed syllable (for example /dɪˈsɪʒən/)
Do not invent meanings that differ from the definition given."""
# TSL and BSL (step-tsl-bsl.md): some headwords come without a definition. A separate constant, so
# the NGSL/NAWL prompt (and the replies cached under its hash) stays exactly as it was.
EXTRA_SYSTEM = (
    SYSTEM
    + """
Some headwords are marked [write a definition] instead of having one. For those, also return
- definition: the meaning a business or office learner needs most, in easy English, at most 15
  words, without the headword or any form of it
and base the Vietnamese meaning and the example on that definition."""
)
DEFINITION_MAX_WORDS = 15


class EntryOut(BaseModel):
    model_config = ConfigDict(extra="ignore")
    lemma: str
    pos: PosOut
    vi: str = Field(min_length=1, max_length=80)
    example: str
    answer: str
    topic: str | None = None
    collocation: str | None = None
    collocation_word: str | None = None
    ipa: str | None = None
    definition: str | None = None  # only for headwords without one (TSL/BSL)


class BatchOut(BaseModel):
    entries: list[EntryOut]


@dataclass
class Usage:
    calls: int = 0
    failed_attempts: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0


@dataclass
class Report:
    sources: dict[str, str] = field(default_factory=dict)  # file -> SHA-256
    read: int = 0
    kept: int = 0
    by_level: dict[str, int] = field(default_factory=dict)
    by_source: dict[str, int] = field(default_factory=dict)
    dropped: dict[str, int] = field(default_factory=dict)  # reason -> count
    dropped_words: dict[str, list[str]] = field(default_factory=dict)  # reason -> lemmas
    ipa_compared: int = 0
    ipa_agreed: int = 0
    ipa_missing_from_model: int = 0
    usage: Usage = field(default_factory=Usage)
    review: dict[str, Any] | None = None


# --- downloads ----------------------------------------------------------------------------------


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def download(
    work: Path,
    manifest: Path,
    fetch: Callable[[str, Path], None] | None = None,
    files: Sequence[str] = tuple(hw.FILES.values()),
) -> None:
    """Fetch the official files once; a later run refuses a file that changed upstream."""
    work.mkdir(parents=True, exist_ok=True)
    pinned: dict[str, str] = json.loads(manifest.read_text()) if manifest.exists() else {}
    get = fetch or _fetch
    for name in files:
        path = work / name
        if not path.exists():
            get(hw.BASE_URL + name, path)
        digest = sha256(path)
        if name in pinned and pinned[name] != digest:
            raise SystemExit(
                f"{name} changed upstream (SHA-256 {digest}); check it, then update {manifest.name}"
            )
        pinned[name] = digest
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps(pinned, indent=2, sort_keys=True) + "\n")


def _fetch(url: str, dest: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "nodetrail-vocab-import"})
    with urllib.request.urlopen(request, timeout=120) as r:
        dest.write_bytes(r.read())


# --- checking one model entry -------------------------------------------------------------------


def build_word(h: hw.Headword, e: EntryOut, topics: set[str]) -> tuple[Word | None, str | None]:
    """The checked entry, or the reason it is dropped. IPA is added later, only on agreement."""
    if e.lemma.strip().lower() != h.lemma:
        return None, "the model answered for another word"
    pos = h.pos or e.pos
    if pos == "other":
        return None, "function word (not practised)"
    definition = h.definition or " ".join((e.definition or "").split())
    if h.needs_definition and (
        not 5 <= len(definition) <= 120
        or len(definition.split()) > DEFINITION_MAX_WORDS
        or any(occurrences(form, definition) for form in h.forms)
    ):
        return None, "the model's definition is missing, too long or gives the word away"
    if h.pos and e.pos != h.pos:
        return None, "the model changed the list's part of speech"
    answer = e.answer.strip()
    if answer.lower() not in h.forms:
        return None, "the example uses a form not in the list's word family"
    if not 6 <= len(e.example.split()) <= 25:
        return None, "the example is not 6-25 words long"
    if occurrences(answer, e.example) != 1:
        return None, "the example does not contain the word exactly once"
    data: dict[str, Any] = {
        "lemma": h.lemma,
        "pos": pos,
        "level": h.level,
        "origin": h.source,
        "topic": e.topic if e.topic in topics else None,
        "definition": definition,
        "vi": " ".join(e.vi.split()),
        "examples": [{"text": " ".join(e.example.split()), "answer": answer}],
    }
    blank = (e.collocation_word or "").strip()
    if (
        e.collocation
        and blank.lower() in h.forms
        and e.collocation.strip().lower() != blank.lower()
    ):
        data["collocations"] = [{"phrase": " ".join(e.collocation.split()), "blank": blank}]
    try:
        return Word.model_validate(data), None
    except ValidationError as exc:
        if "collocations" in data:  # a bad collocation loses the collocation, not the word
            del data["collocations"]
            try:
                return Word.model_validate(data), None
            except ValidationError:
                pass
        return None, "fails the word-list rules: " + exc.errors()[0]["msg"][:60]


def with_ipa(word: Word, model_ipa: str | None, espeak_ipa: str | None) -> Word:
    if model_ipa and espeak_ipa and agree(model_ipa, espeak_ipa):
        ipa = "/" + model_ipa.strip().strip("/").strip() + "/"
        try:
            return word.model_copy(
                update={"ipa": Word.model_validate({**word.model_dump(), "ipa": ipa}).ipa}
            )
        except ValidationError:
            return word
    return word


# --- the model ----------------------------------------------------------------------------------


def prompt(batch: Sequence[hw.Headword], topics: Sequence[str]) -> str:
    lines = [f"Topic slugs: {', '.join(topics)}", "", "Headwords:"]
    for h in batch:
        pos = f" [{h.pos}]" if h.pos else ""
        if h.needs_definition:  # never true for the NGSL/NAWL, so their prompts are unchanged
            lines.append(f"- {h.lemma}{pos} [write a definition]")
        else:
            lines.append(f"- {h.lemma}{pos}: {h.definition}")
    return "\n".join(lines)


class Model:
    """Batches through the gateway; every reply is saved so a stopped run resumes for free."""

    def __init__(
        self,
        gateway: Gateway,
        cache: Path,
        prices: tuple[float, float],
        cap_usd: float,
        tier: str = "free",
    ) -> None:
        self.gateway, self.cache, self.tier = gateway, cache, tier
        self.price_in, self.price_out = prices
        self.cap = cap_usd
        self.usage = Usage()
        self._lock = threading.Lock()  # batches run in parallel threads
        cache.mkdir(parents=True, exist_ok=True)

    def _cost(self, a: Attempt) -> float:
        out = a.output_tokens + a.thoughts_tokens
        return (a.input_tokens * self.price_in + out * self.price_out) / 1_000_000

    def entries(
        self, batch: Sequence[hw.Headword], topics: Sequence[str], system: str = SYSTEM
    ) -> list[EntryOut] | None:
        key = hashlib.sha256((system + prompt(batch, topics)).encode()).hexdigest()[:16]
        path = self.cache / f"{key}.json"
        if path.exists():
            return BatchOut.model_validate_json(path.read_text(encoding="utf-8")).entries
        if self.usage.cost_usd >= self.cap:
            return None  # stopped at the cap: run again (with a higher --max-usd) to continue
        attempts: list[Attempt] = []
        gateway = Gateway(
            self.gateway.routing,
            self.gateway.adapters,
            observe_attempt=attempts.append,
            task_limits={TASK: GenerationLimits(16384, 0)},
            request_timeout=180,
            total_timeout=400,
        )
        try:
            done = asyncio.run(
                gateway.complete_with_metadata(
                    TASK,
                    self.tier,
                    system,
                    [{"role": "user", "content": prompt(batch, topics)}],
                    BatchOut,
                )
            )
        except Exception as exc:  # recorded; the batch is retried on the next run
            print(f"batch {batch[0].lemma}..: {type(exc).__name__}: {exc}", file=sys.stderr)
            return []
        finally:
            with self._lock:
                for a in attempts:
                    if a.error_code:
                        print(f"  attempt {a.number}: {a.status} {a.error_code}", file=sys.stderr)
                    self.usage.input_tokens += a.input_tokens
                    self.usage.output_tokens += a.output_tokens + a.thoughts_tokens
                    self.usage.cost_usd += self._cost(a)
                    self.usage.failed_attempts += a.status != "success"
                self.usage.calls += len(attempts)
        assert isinstance(done.value, BatchOut)
        path.write_text(done.value.model_dump_json(), encoding="utf-8")
        return done.value.entries


class Checker:
    """The blind definition check through the gateway (`vocab_check`, never DeepSeek's family).

    Replies are cached like the model's, so a rerun asks only what is still unanswered.
    """

    def __init__(self, cache: Path, max_calls: int = 60) -> None:
        self.cache = cache
        self.max_calls = max_calls  # free models: a cap on calls, not on money
        self.calls = 0
        self.failed = 0
        cache.mkdir(parents=True, exist_ok=True)

    def ask(self, batch: Sequence[dc.Question]) -> dc.Reply | None:  # pragma: no cover - model
        key = hashlib.sha256((dc.SYSTEM + dc.prompt(batch)).encode()).hexdigest()[:16]
        path = self.cache / f"{key}.json"
        if path.exists():
            return dc.Reply.model_validate_json(path.read_text(encoding="utf-8"))
        if self.calls >= self.max_calls:
            return None
        from app.llm.gateway import (
            GatewayError,
            complete_with_metadata,
            gateway_scope,
            verification_scope,
        )
        from app.llm.providers import default_gateway

        base = default_gateway()
        gateway = Gateway(base.routing, base.adapters, request_timeout=120, total_timeout=300)
        self.calls += 1
        try:
            with gateway_scope(gateway), verification_scope("deepseek"):
                out = asyncio.run(
                    complete_with_metadata(
                        dc.TASK,
                        "free",
                        dc.SYSTEM,
                        [{"role": "user", "content": dc.prompt(batch)}],
                        dc.Reply,
                    )
                )
        except GatewayError as exc:  # no reply: nothing decided, retried on the next run
            self.failed += 1
            print(f"check {batch[0].lemma}..: {exc}", file=sys.stderr)
            return None
        if not isinstance(out.value, dc.Reply):
            self.failed += 1
            return None
        path.write_text(out.value.model_dump_json(), encoding="utf-8")
        return out.value


def espeak_ipa(tts_url: str, words: Sequence[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for i in range(0, len(words), 100):
        body = json.dumps({"words": list(words[i : i + 100])}).encode()
        request = urllib.request.Request(
            tts_url.rstrip("/") + "/phonemize", body, {"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(request, timeout=60) as r:
            out.update(json.loads(r.read())["ipa"])
    return out


# --- the run ------------------------------------------------------------------------------------


def run(
    work: Path,
    out: Path,
    model: Model,
    phonemes: Callable[[Sequence[str]], dict[str, str]],
    authored: WordList,
    limit: int | None = None,
) -> Report:
    manifest = out / "sources.json"
    report = Report(sources=json.loads(manifest.read_text()) if manifest.exists() else {})
    heads, dropped = hw.read(work)
    report.read = len(heads) + len(dropped)  # every headword in the official files
    authored_lemmas = {w.lemma for w in authored.words}
    for h in heads:
        if h.lemma in authored_lemmas:
            dropped.append(hw.Dropped(h.lemma, h.source, "already in the authored list"))
    heads = [h for h in heads if h.lemma not in authored_lemmas][:limit]
    topics = [t.slug for t in authored.topics]
    sounds = phonemes([h.lemma for h in heads])
    kept: list[Word] = []
    unfinished = 0
    batches = [heads[i : i + BATCH] for i in range(0, len(heads), BATCH)]
    # A few batches at a time: the cap may be passed by at most the batches already running.
    with ThreadPoolExecutor(PARALLEL) as pool:
        replies = list(pool.map(lambda b: model.entries(b, topics), batches))
    for batch, entries in zip(batches, replies, strict=True):
        if not entries:
            unfinished += len(batch)
            continue
        by_lemma = {e.lemma.strip().lower(): e for e in entries}
        for h in batch:
            e = by_lemma.get(h.lemma)
            if e is None:
                dropped.append(hw.Dropped(h.lemma, h.source, "missing from the model's reply"))
                continue
            word, why = build_word(h, e, set(topics))
            if word is None:
                dropped.append(hw.Dropped(h.lemma, h.source, why or "?"))
                continue
            if e.ipa:
                report.ipa_compared += 1
            else:
                report.ipa_missing_from_model += 1
            word = with_ipa(word, e.ipa, sounds.get(h.lemma))
            report.ipa_agreed += word.ipa is not None
            kept.append(word)
    if unfinished:
        print(
            f"{unfinished} headwords not done yet (cost cap or failed batches): run again",
            file=sys.stderr,
        )
    report.kept = len(kept)
    report.by_level = dict(sorted(Counter(w.level for w in kept).items()))
    report.by_source = dict(Counter(w.origin for w in kept))
    for d in dropped:
        report.dropped[d.reason] = report.dropped.get(d.reason, 0) + 1
        report.dropped_words.setdefault(d.reason, []).append(d.lemma)
    previous = load_report(out)
    before = Usage(**previous["usage"]) if previous else Usage()  # an earlier, stopped run
    report.usage = Usage(
        before.calls + model.usage.calls,
        before.failed_attempts + model.usage.failed_attempts,
        before.input_tokens + model.usage.input_tokens,
        before.output_tokens + model.usage.output_tokens,
        round(before.cost_usd + model.usage.cost_usd, 6),
    )
    if len(kept) >= 4:  # the list needs four words for a meaning question
        lemmas = {w.lemma for w in kept}
        added = [
            w for w in imported_words(out, authored) if w.origin in EXTRA and w.lemma not in lemmas
        ]
        write_list(out, [*kept, *added], authored)  # TSL/BSL words survive an NGSL/NAWL rerun
    report.review = previous.get("review") if previous else None
    (out / "import-report.json").write_text(
        json.dumps(asdict(report), indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return report


EXTRA = ("tsl", "bsl")


def imported_words(out: Path, authored: WordList) -> list[Word]:
    """The words already in the imported file (none before the first run)."""
    path = out / f"{authored.slug}.yaml"
    return list(load_wordlist(path).words) if path.exists() else []


def write_list(out: Path, words: list[Word], authored: WordList) -> None:
    data = {
        "slug": authored.slug,
        "title_vi": authored.title_vi,
        "title_en": authored.title_en,
        "status": "draft",
        "topics": [t.model_dump() for t in authored.topics],
        "words": [w.model_dump(exclude_defaults=True) for w in words],
    }
    WordList.model_validate(data)  # the file must load before it is written
    header = (
        "# Imported from NGSL 1.2 and NAWL 1.2 (specs/vocabulary-import), then TSL 1.2\n"
        "# and BSL 1.20 (step-tsl-bsl.md); generated, do not edit. New General Service List\n"
        "# and New Academic Word List by Browne, C., Culligan, B., and Phillips, J.; TOEIC\n"
        "# Service List and Business Service List by Browne, C. and Culligan, B.; all\n"
        "# CC BY-SA 4.0, https://www.newgeneralservicelist.com. This file is CC BY-SA 4.0 too\n"
        "# (see ../LICENSE.md). Headwords and definitions are from the lists, except for BSL\n"
        "# words (and TSL words without a usable definition): a model wrote those definitions,\n"
        "# kept only when another model, blind, picked the word from it among four. Levels are\n"
        "# estimated from frequency; Vietnamese, examples, topics, collocations and IPA (kept\n"
        "# only where espeak-ng agreed) were written by a model: a draft.\n"
    )
    out.mkdir(parents=True, exist_ok=True)
    body = yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=100)
    (out / f"{authored.slug}.yaml").write_text(header + body, encoding="utf-8")


def load_report(out: Path) -> dict[str, Any] | None:
    path = out / "import-report.json"
    if not path.exists():
        return None
    report: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return report


# --- TSL and BSL, added to the list (step-tsl-bsl.md) ---------------------------------------------

EXTRA_REPORT = "import-report-tsl-bsl.json"


@dataclass
class ExtraReport:
    sources: dict[str, str] = field(default_factory=dict)
    read: int = 0  # TSL and BSL headwords not already in the list
    kept: int = 0
    unfinished: int = 0  # not done yet: cost cap, failed batches, or a check with no reply
    by_level: dict[str, int] = field(default_factory=dict)
    by_source: dict[str, int] = field(default_factory=dict)
    model_definitions: int = 0  # kept words whose definition the model wrote (blind-checked)
    check: dict[str, int] = field(default_factory=dict)  # right, wrong, cannot_tell, no_reply
    checker_calls: int = 0
    checker_failed: int = 0
    dropped: dict[str, int] = field(default_factory=dict)
    dropped_words: dict[str, list[str]] = field(default_factory=dict)
    ipa_compared: int = 0
    ipa_agreed: int = 0
    usage: Usage = field(default_factory=Usage)


def run_extra(
    work: Path,
    out: Path,
    model: Model,
    checker: "Checker",
    phonemes: Callable[[Sequence[str]], dict[str, str]],
    authored: WordList,
    limit: int | None = None,
) -> ExtraReport:
    """Every TSL/BSL word is rebuilt on each run from cached replies, so the result is complete
    and a rerun is free; the NGSL/NAWL words in the file are copied unchanged."""
    manifest = out / "sources.json"
    report = ExtraReport(sources=json.loads(manifest.read_text()) if manifest.exists() else {})
    base = [w for w in imported_words(out, authored) if w.origin not in EXTRA]
    if not base:
        raise SystemExit("run the NGSL/NAWL import first: TSL and BSL are added to its list")
    known = {w.lemma for w in authored.words} | {w.lemma for w in base}
    heads, dropped = hw.read_extra(work, known)
    report.read = len(heads) + len(dropped)
    heads = heads[:limit]
    topics = [t.slug for t in authored.topics]
    sounds = phonemes([h.lemma for h in heads])
    batches = [heads[i : i + BATCH] for i in range(0, len(heads), BATCH)]
    with ThreadPoolExecutor(PARALLEL) as pool:
        replies = list(pool.map(lambda b: model.entries(b, topics, EXTRA_SYSTEM), batches))
    built: list[tuple[hw.Headword, Word]] = []
    for batch, entries in zip(batches, replies, strict=True):
        if not entries:
            report.unfinished += len(batch)
            continue
        by_lemma = {e.lemma.strip().lower(): e for e in entries}
        for h in batch:
            e = by_lemma.get(h.lemma)
            if e is None:
                dropped.append(hw.Dropped(h.lemma, h.source, "missing from the model's reply"))
                continue
            word, why = build_word(h, e, set(topics))
            if word is None:
                dropped.append(hw.Dropped(h.lemma, h.source, why or "?"))
                continue
            report.ipa_compared += bool(e.ipa)
            built.append((h, with_ipa(word, e.ipa, sounds.get(h.lemma))))
    # The blind check of the model's definitions, against three other words of this run.
    pool_words = [w for _, w in built]
    questions = [
        dc.question(i, w, pool_words) for i, (h, w) in enumerate(built) if h.needs_definition
    ]
    results: dict[str, dc.Verdict] = {}
    for i in range(0, len(questions), dc.BATCH):
        part = questions[i : i + dc.BATCH]
        results |= dc.verdicts(part, checker.ask(part))
    counts = dc.CheckCounts()
    kept: list[Word] = []
    for h, w in built:
        if h.needs_definition:
            v = results[w.lemma]
            counts.add(v)
            if v == "no_reply":  # nothing decided: out of the list, asked again next run
                report.unfinished += 1
                continue
            if v != "right":
                dropped.append(hw.Dropped(h.lemma, h.source, f"blind check: {v.replace('_', ' ')}"))
                continue
            report.model_definitions += 1
        kept.append(w)
    if report.unfinished:
        print(f"{report.unfinished} words not done yet: run again", file=sys.stderr)
    report.kept = len(kept)
    report.ipa_agreed = sum(w.ipa is not None for w in kept)
    report.by_level = dict(sorted(Counter(w.level for w in kept).items()))
    report.by_source = dict(Counter(w.origin for w in kept))
    report.check = asdict(counts)
    report.checker_calls, report.checker_failed = checker.calls, checker.failed  # this run
    for d in dropped:
        report.dropped[d.reason] = report.dropped.get(d.reason, 0) + 1
        report.dropped_words.setdefault(d.reason, []).append(d.lemma)
    previous = _load(out / EXTRA_REPORT)
    before = Usage(**previous["usage"]) if previous else Usage()
    report.usage = Usage(
        before.calls + model.usage.calls,
        before.failed_attempts + model.usage.failed_attempts,
        before.input_tokens + model.usage.input_tokens,
        before.output_tokens + model.usage.output_tokens,
        round(before.cost_usd + model.usage.cost_usd, 6),
    )
    write_list(out, [*base, *kept], authored)
    (out / EXTRA_REPORT).write_text(
        json.dumps(asdict(report), indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return report


def _load(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return data


# --- word forms for the lesson narration check (specs/grammar-lessons) --------------------------


def write_forms(work: Path, out: Path) -> Path:
    """`forms.yaml`: headword -> [level, form, form, ...] for every NGSL/NAWL headword."""
    index = hw.form_index(work)
    data = {h: [e.level, *e.forms[1:]] for h, e in sorted(index.items())}
    path = out / "forms.yaml"
    path.write_text(
        "# Headwords of NGSL 1.2 (with its supplementary list) and NAWL 1.2 with their inflected\n"
        "# forms and the level estimated from frequency (specs/vocabulary-import). Used to check\n"
        "# that a lesson's narration is graded English (specs/grammar-lessons). CC BY-SA 4.0,\n"
        "# Browne, Culligan and Phillips; made by `python -m app.vocabulary.importer forms`.\n"
        + yaml.dump(
            data,
            Dumper=yaml.SafeDumper,
            allow_unicode=True,
            sort_keys=False,
            default_flow_style=None,
            width=120,
        ),
        encoding="utf-8",
    )
    return path


# --- the owner's check --------------------------------------------------------------------------


def sample(out: Path, slug: str, n: int = 50, seed: int = 20261116) -> Path:
    words = load_wordlist(out / f"{slug}.yaml").words
    chosen = random.Random(seed).sample(list(words), min(n, len(words)))
    rows = [
        {
            "lemma": w.lemma,
            "pos": w.pos,
            "level": w.level,
            "definition": w.definition,
            "vi": w.vi,
            "example": w.examples[0].text,
            "topic": w.topic,
            "ipa": w.ipa,
            "correct": None,
            "note": "",
        }
        for w in chosen
    ]
    path = out / "review-sample.yaml"
    path.write_text(
        "# The owner's check (specs/vocabulary-import, the gate): set `correct` to true when the\n"
        "# Vietnamese, the example, the topic and the IPA (when shown) are all right; else false\n"
        "# and say why in `note`. Then: python -m app.vocabulary.importer score\n"
        + yaml.safe_dump(rows, allow_unicode=True, sort_keys=False, width=100),
        encoding="utf-8",
    )
    return path


def score(out: Path) -> dict[str, Any]:
    from app.evalkit.stats import rate

    rows = yaml.safe_load((out / "review-sample.yaml").read_text(encoding="utf-8"))
    marked = [r for r in rows if r.get("correct") is not None]
    r = rate(sum(bool(x["correct"]) for x in marked), len(marked))
    review = {
        "marked": len(marked),
        "of": len(rows),
        "correct": r.k,
        "precision": r.point,
        "low95": r.low,
        "high95": r.high,
        "summary": str(r),
    }
    report = load_report(out) or {}
    report["review"] = review
    (out / "import-report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return review


# --- command line -------------------------------------------------------------------------------


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.vocabulary.importer")
    parser.add_argument("command", choices=["download", "run", "extra", "sample", "score", "forms"])
    parser.add_argument("--work", type=Path, default=WORK)
    parser.add_argument("--out", type=Path, default=OUT)
    parser.add_argument("--tts-url", default=os.environ.get("TTS_URL") or "http://localhost:8030")
    parser.add_argument("--max-usd", type=float, default=1.0, help="stop starting batches here")
    parser.add_argument("--limit", type=int, default=None, help="only the first N headwords")
    parser.add_argument("--max-checks", type=int, default=60, help="extra: blind-check calls")
    args = parser.parse_args(argv)
    if args.command == "download":
        download(args.work, args.out / "sources.json")
        print(f"downloaded to {args.work}")
        return 0
    if args.command == "forms":
        download(args.work, args.out / "sources.json")
        print(write_forms(args.work, args.out))
        return 0
    if args.command == "sample":
        print(sample(args.out, load_wordlist(AUTHORED).slug))
        return 0
    if args.command == "score":
        print(score(args.out)["summary"])
        return 0
    from app.config import Settings
    from app.llm.providers import default_gateway

    settings = Settings()
    if args.command == "extra":
        names = [*hw.FILES.values(), *hw.EXTRA_FILES.values()]
        download(args.work, args.out / "sources.json", files=names)
        extra = run_extra(
            args.work,
            args.out,
            Model(
                default_gateway(),
                args.work / "replies",
                (settings.llm_price_input_per_mtok, settings.llm_price_output_per_mtok),
                args.max_usd,
            ),
            Checker(args.work / "checks", args.max_checks),
            lambda ws: espeak_ipa(args.tts_url, ws),
            load_wordlist(AUTHORED),
            args.limit,
        )
        summary = {k: v for k, v in asdict(extra).items() if k != "dropped_words"}
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        return 0
    download(args.work, args.out / "sources.json")
    model = Model(
        default_gateway(),
        args.work / "replies",
        (settings.llm_price_input_per_mtok, settings.llm_price_output_per_mtok),
        args.max_usd,
    )
    report = run(
        args.work,
        args.out,
        model,
        lambda ws: espeak_ipa(args.tts_url, ws),
        load_wordlist(AUTHORED),
        args.limit,
    )
    print(
        json.dumps(
            {k: v for k, v in asdict(report).items() if k != "dropped_words"},
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
