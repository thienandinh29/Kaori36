# ruff: noqa: RUF001
"""The NGSL/NAWL import (specs/vocabulary-import): parsing, levels, checks, IPA rule, merge, review.

No network and no model: small files in the official formats and a fake model reply.
"""

import json
import zipfile
from collections.abc import Sequence
from pathlib import Path
from xml.sax.saxutils import escape

import pytest
import yaml  # type: ignore[import-untyped]

from app.vocabulary import headwords as hw
from app.vocabulary import importer as imp
from app.vocabulary.importer import EntryOut
from app.vocabulary.wordlist import WordList, load_wordlist

ROOT = Path(__file__).resolve().parents[4]
AUTHORED = load_wordlist(ROOT / "data" / "vocabulary" / "core-seed.yaml")


def xlsx(path: Path, rows: list[list[str]]) -> None:
    """A minimal workbook with shared strings, the shape of the official files."""
    strings = [c for r in rows for c in r]
    cells = []
    for i, r in enumerate(rows, start=1):
        row = "".join(
            f'<c r="{"ABCD"[j]}{i}" t="s"><v>{strings.index(c)}</v></c>' for j, c in enumerate(r)
        )
        cells.append(f'<row r="{i}">{row}</row>')
    ns = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
    shared = "".join(f"<si><t>{escape(s)}</t></si>" for s in strings)
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("xl/sharedStrings.xml", f"<sst {ns}>{shared}</sst>")
        z.writestr(
            "xl/worksheets/sheet1.xml",
            f"<worksheet {ns}><sheetData>{''.join(cells)}</sheetData></worksheet>",
        )


@pytest.fixture
def files(tmp_path: Path) -> Path:
    f = hw.FILES
    (tmp_path / f["ngsl_stats"]).write_text(
        "Lemma,SFI Rank,SFI,Adjusted Frequency per Million (U)\n"
        "the,1,87.85,60910\nhabit,600,60.1,90\nkick,1500,55.0,40\nset,1800,54,30\n"
        "harbour,2500,50.0,10\nimportant,300,62.0,200\n"
    )
    xlsx(
        tmp_path / f["ngsl_definitions"],
        [
            ["Word", "Definitons"],
            ["the", "used before a noun that is already known"],
            ["habit", "the usual way of behaving; something often repeated"],
            ["kick", "to hit something with your foot"],
            ["set", "a set of things"],  # gives the word away: dropped
            ["harbour", "a place on the coast where ships stay"],
            ["important", "having great value or effect"],  # in the authored list
            ["blog", "a website where someone writes regularly"],  # no frequency rank
        ],
    )
    (tmp_path / f["ngsl_forms"]).write_text(
        "## a comment line\r\nhabit,habits\r\nkick,kicks,kicked,kicking\r\n"
    )
    (tmp_path / f["nawl_definitions"]).write_text(
        "﻿Meanings,English Definition,POS,J Translation\n"
        "acidic,containing acid,adj,酸性の\n"
        "accelerate,to become faster,verb,加速する\n"
        "aerosol,a can that sprays liquid,n,エアロゾル\n"
        "anti,against,prefix,反\n"
        "habit,repeated behaviour,n,習慣\n",
        encoding="utf-8",
    )
    (tmp_path / f["nawl_forms"]).write_bytes(
        "acidic\r\naccelerate,accelerates,accelerated,accelerating\r\naerosol,aerosols\r\n".encode(
            "latin-1"
        )
    )
    xlsx(
        tmp_path / f["sfi_31k"],
        [
            ["Lemma", "Wordlist", "WL_SFI_Rank", "SFI"],
            ["accelerate", "", "", "45.0"],
            ["acidic", "", "", "40.0"],
        ],
    )
    return tmp_path


def test_headwords_levels_and_what_is_dropped(files: Path) -> None:
    words, dropped = hw.read(files)
    by = {w.lemma: w for w in words}
    assert by["the"].level == "A1" and by["habit"].level == "A2" and by["kick"].level == "B1"
    assert by["harbour"].level == "B2" and by["kick"].forms == (
        "kick",
        "kicks",
        "kicked",
        "kicking",
    )
    assert by["harbour"].forms == ("harbour",)  # no forms row: the headword alone
    # NAWL: the more frequent half B2, the rest C1; no frequency figure -> C1
    assert (by["accelerate"].level, by["acidic"].level, by["aerosol"].level) == ("B2", "B2", "C1")
    assert by["aerosol"].pos == "noun" and by["accelerate"].pos == "verb"
    reasons = {d.lemma: d.reason for d in dropped}
    assert reasons["set"] == "the definition contains the word itself"
    assert reasons["blog"] == "no frequency rank"
    assert "not practised" in reasons["anti"] and reasons["habit"] == "already in the NGSL"


def test_level_bands_are_the_owners() -> None:
    assert [hw.ngsl_level(r) for r in (1, 500, 501, 1200, 1201, 2000, 2001, 2809)] == [
        "A1",
        "A1",
        "A2",
        "A2",
        "B1",
        "B1",
        "B2",
        "B2",
    ]
    assert hw.nawl_levels(["a", "b", "c"], {"a": 3.0, "b": 2.0}) == {
        "a": "B2",
        "b": "B2",
        "c": "C1",
    }


KICK = hw.Headword(
    "kick", "ngsl", "B1", "to hit something with your foot", ("kick", "kicks", "kicked", "kicking")
)


def entry(**over: object) -> EntryOut:
    base: dict[str, object] = {
        "lemma": "kick",
        "pos": "verb",
        "vi": "đá",
        "answer": "kicked",
        "example": "He kicked the ball into the goal.",
        "topic": "health",
        "collocation": "kick a ball",
        "collocation_word": "kick",
        "ipa": "/kɪk/",
    }
    return EntryOut.model_validate({**base, **over})


TOPICS = {t.slug for t in AUTHORED.topics}


def test_a_good_entry_becomes_a_word_marked_as_imported() -> None:
    word, why = imp.build_word(KICK, entry(), TOPICS)
    assert why is None and word is not None
    assert (word.origin, word.level, word.topic, word.ipa) == ("ngsl", "B1", "health", None)
    assert word.collocations[0].phrase == "kick a ball"
    assert word.definition == KICK.definition  # from the list, never from the model


@pytest.mark.parametrize(
    ("over", "reason"),
    [
        ({"lemma": "punch"}, "another word"),
        ({"pos": "other"}, "function word"),
        ({"answer": "kickboxing", "example": "He loves kickboxing on Sunday mornings."}, "family"),
        ({"example": "He kicked it."}, "6-25 words"),
        ({"example": "He kicked the ball and kicked it again."}, "exactly once"),
    ],
)
def test_bad_entries_are_dropped_with_a_reason(over: dict[str, object], reason: str) -> None:
    word, why = imp.build_word(KICK, entry(**over), TOPICS)
    assert word is None and why is not None and reason in why


def test_a_bad_collocation_or_topic_is_left_out_but_the_word_is_kept() -> None:
    word, _ = imp.build_word(KICK, entry(collocation="kick", topic="space-travel"), TOPICS)
    assert word is not None and word.collocations == () and word.topic is None
    word, _ = imp.build_word(
        KICK, entry(collocation="a big punch", collocation_word="kick"), TOPICS
    )
    assert word is not None and word.collocations == ()


def test_the_nawl_part_of_speech_cannot_be_changed_by_the_model() -> None:
    nawl = hw.Headword("accelerate", "nawl", "B2", "to become faster", ("accelerate",), "verb")
    e = entry(
        lemma="accelerate",
        pos="noun",
        answer="accelerate",
        example="Prices accelerate quickly when supply is short.",
    )
    assert imp.build_word(nawl, e, TOPICS)[1] == "the model changed the list's part of speech"


def test_ipa_only_when_espeak_agrees_never_filled_by_the_model() -> None:
    word, _ = imp.build_word(KICK, entry(), TOPICS)
    assert word is not None
    assert imp.with_ipa(word, "/kɪk/", "kˈɪk").ipa == "/kɪk/"
    assert imp.with_ipa(word, "/kiːk/", "kˈɪk").ipa is None  # disagreement: no IPA at all
    assert imp.with_ipa(word, None, "kˈɪk").ipa is None  # espeak alone is not enough either
    assert imp.with_ipa(word, "/kɪk/", None).ipa is None


class FakeModel(imp.Model):
    def __init__(self, cache: Path) -> None:
        self.cache, self.usage, self.calls = cache, imp.Usage(), 0

    def entries(
        self, batch: Sequence[hw.Headword], topics: Sequence[str], system: str = imp.SYSTEM
    ) -> list[EntryOut]:
        self.calls += 1
        out = []
        for h in batch:
            form = h.forms[0]
            out.append(
                EntryOut(
                    lemma=h.lemma,
                    pos="other" if h.lemma == "the" else h.pos or "noun",
                    vi="nghĩa",
                    answer=form,
                    topic=None,
                    ipa="/ˈtest/",
                    example=f"Everyone in the class talked about the {form} today.",
                )
            )
        return out


def test_a_run_writes_a_loadable_list_and_an_honest_report(files: Path, tmp_path: Path) -> None:
    out = tmp_path / "out"
    model = FakeModel(tmp_path / "cache")
    report = imp.run(files, out, model, lambda ws: {w: "tˈɛst" for w in ws}, AUTHORED)
    data = yaml.safe_load((out / "core-seed.yaml").read_text(encoding="utf-8"))
    imported = WordList.model_validate(data)
    assert {w.lemma for w in imported.words} == {
        "habit",
        "kick",
        "harbour",
        "accelerate",
        "acidic",
        "aerosol",
    }
    assert imported.status == "draft" and all(w.origin != "authored" for w in imported.words)
    assert "CC BY-SA 4.0" in (out / "core-seed.yaml").read_text(encoding="utf-8")
    saved = json.loads((out / "import-report.json").read_text(encoding="utf-8"))
    assert saved["kept"] == 6 and report.read == 12  # 7 NGSL rows + 5 NAWL rows
    assert saved["dropped"]["already in the authored list"] == 1
    assert saved["dropped"]["function word (not practised)"] == 1
    assert saved["ipa_agreed"] == 6 and saved["ipa_compared"] == 6


def test_an_ngsl_rerun_keeps_the_tsl_and_bsl_words(files: Path, tmp_path: Path) -> None:
    out = tmp_path / "out"
    model = FakeModel(tmp_path / "cache")
    imp.run(files, out, model, lambda ws: {}, AUTHORED)
    listed = load_wordlist(out / "core-seed.yaml")
    refund = listed.words[0].model_copy(
        update={"lemma": "refund", "origin": "tsl", "definition": "money given back to you"}
    )
    refund = refund.model_copy(
        update={"examples": (refund.examples[0].model_copy(
            update={"text": "They asked for a refund last week.", "answer": "refund"}),)}
    )  # fmt: skip
    imp.write_list(out, [*listed.words, refund], AUTHORED)
    imp.run(files, out, FakeModel(tmp_path / "cache"), lambda ws: {}, AUTHORED)
    again = load_wordlist(out / "core-seed.yaml")
    assert "refund" in {w.lemma for w in again.words}
    assert json.loads((out / "import-report.json").read_text())["kept"] == 6  # NGSL/NAWL only


def test_the_learner_sees_one_list_and_authored_entries_win(tmp_path: Path) -> None:
    authored_dir, imported_dir = tmp_path / "data", tmp_path / "data-sa"
    authored_dir.mkdir()
    imported_dir.mkdir()
    (authored_dir / "core-seed.yaml").write_text(
        (ROOT / "data" / "vocabulary" / "core-seed.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    first = AUTHORED.words[0]
    extra = [
        {**first.model_dump(exclude_defaults=True), "origin": "ngsl", "vi": "khác"},  # same lemma
        *[
            {
                "lemma": w,
                "pos": "noun",
                "level": "B2",
                "origin": "nawl",
                "definition": "a thing we use",
                "vi": "vật",
                "examples": [{"text": f"We bought a {w} yesterday.", "answer": w}],
            }
            for w in ("gadget", "widget", "gizmo", "doohickey")
        ],
    ]
    (imported_dir / "core-seed.yaml").write_text(
        yaml.safe_dump(
            {
                "slug": "core-seed",
                "title_vi": "x",
                "title_en": "x",
                "status": "draft",
                "topics": [t.model_dump() for t in AUTHORED.topics],
                "words": extra,
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    merged = load_wordlist(authored_dir / "core-seed.yaml", imported_dir)
    assert len(merged.words) == len(AUTHORED.words) + 4
    assert merged.get(first.key) == first  # the authored entry wins
    assert merged.title_vi == AUTHORED.title_vi and merged.status == "draft"
    assert load_wordlist(authored_dir / "core-seed.yaml", tmp_path / "nowhere") == AUTHORED


def test_download_pins_the_files_and_refuses_a_changed_one(tmp_path: Path) -> None:
    work, manifest = tmp_path / "work", tmp_path / "out" / "sources.json"

    def fake(url: str, dest: Path) -> None:
        dest.write_bytes(url.encode())

    imp.download(work, manifest, fake)
    pinned = json.loads(manifest.read_text())
    assert set(pinned) == set(hw.FILES.values())
    (work / hw.FILES["ngsl_stats"]).write_bytes(b"changed upstream")
    with pytest.raises(SystemExit, match="changed upstream"):
        imp.download(work, manifest)


def test_the_owners_sample_and_its_score(files: Path, tmp_path: Path) -> None:
    out = tmp_path / "out"
    imp.run(files, out, FakeModel(tmp_path / "c"), lambda ws: {}, AUTHORED)
    path = imp.sample(out, "core-seed", n=4)
    rows = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert len(rows) == 4 and all(r["correct"] is None for r in rows)
    for i, r in enumerate(rows):
        r["correct"] = i != 0
    path.write_text(yaml.safe_dump(rows, allow_unicode=True), encoding="utf-8")
    review = imp.score(out)
    assert (review["correct"], review["marked"]) == (3, 4) and review["low95"] < 0.75 < review[
        "high95"
    ]
    assert json.loads((out / "import-report.json").read_text())["review"]["correct"] == 3


def test_a_resumed_run_adds_its_usage_to_the_first_runs(files: Path, tmp_path: Path) -> None:
    out = tmp_path / "out"
    first = FakeModel(tmp_path / "c")
    first.usage = imp.Usage(2, 0, 100, 200, 0.5)
    imp.run(files, out, first, lambda ws: {}, AUTHORED)
    second = FakeModel(tmp_path / "c")
    second.usage = imp.Usage(1, 1, 10, 20, 0.25)
    report = imp.run(files, out, second, lambda ws: {}, AUTHORED)
    assert report.usage == imp.Usage(3, 1, 110, 220, 0.75)


def test_the_committed_import_loads_merges_and_matches_its_report() -> None:
    folder = ROOT / "data-sa" / "vocabulary"
    imported = load_wordlist(folder / "core-seed.yaml")
    report = json.loads((folder / "import-report.json").read_text(encoding="utf-8"))
    base = [w for w in imported.words if w.origin in ("ngsl", "nawl")]
    extra = [w for w in imported.words if w.origin in imp.EXTRA]
    assert len(base) == report["kept"] and imported.status == "draft"
    assert len(base) + len(extra) == len(imported.words)
    assert sum(w.ipa is not None for w in base) == report["ipa_agreed"]
    assert "CC BY-SA 4.0" in (folder / "core-seed.yaml").read_text(encoding="utf-8")[:600]
    pinned = set(json.loads((folder / "sources.json").read_text()))
    assert set(hw.FILES.values()) <= pinned <= set(hw.FILES.values()) | set(hw.EXTRA_FILES.values())
    if extra:  # TSL and BSL added (step-tsl-bsl.md): the list matches its own report
        extra_report = json.loads((folder / imp.EXTRA_REPORT).read_text(encoding="utf-8"))
        assert len(extra) == extra_report["kept"]
        assert sum(w.ipa is not None for w in extra) == extra_report["ipa_agreed"]
    merged = load_wordlist(ROOT / "data" / "vocabulary" / "core-seed.yaml", folder)
    assert len(merged.words) == len(AUTHORED.words) + len(imported.words)  # no lemma twice
    assert merged.words[: len(AUTHORED.words)] == AUTHORED.words
