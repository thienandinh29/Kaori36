# ruff: noqa: RUF001
"""TSL and BSL added to the list (specs/vocabulary-import/step-tsl-bsl.md).

No network and no model: small files in the official formats, a fake model and a fake checker.
"""

import json
from collections.abc import Sequence
from pathlib import Path

import pytest
import yaml  # type: ignore[import-untyped]

from app.competencies.bands import band_of
from app.competencies.model import VOCAB_BANDS
from app.vocabulary import definition_check as dc
from app.vocabulary import headwords as hw
from app.vocabulary import importer as imp
from app.vocabulary.importer import EntryOut
from app.vocabulary.wordlist import Word, WordList, load_wordlist

from .test_import import AUTHORED, xlsx

SFI = [
    ["Lemma", "Wordlist", "WL_SFI_Rank", "SFI"],
    ["the", "", "", "87.0"],
    ["habit", "", "", "60.0"],
    ["kick", "", "", "55.0"],
    ["harbour", "", "", "50.0"],
    ["airport", "", "", "56.0"],  # as frequent as NGSL B1: B1
    ["refund", "", "", "40.0"],
    ["invoice", "", "", "38.0"],
    ["memo", "", "", "30.0"],
    ["merger", "", "", "35.0"],
    ["equity", "", "", "33.0"],
    ["dividend", "", "", "31.0"],
    ["audit", "", "", "34.0"],
]


@pytest.fixture
def files(tmp_path: Path) -> Path:
    f, e = hw.FILES, hw.EXTRA_FILES
    (tmp_path / f["ngsl_stats"]).write_text(
        "Lemma,SFI Rank,SFI,U\nthe,1,87,1\nhabit,600,60,1\nkick,1500,55,1\nharbour,2500,50,1\n"
    )
    xlsx(tmp_path / f["sfi_31k"], SFI)
    (tmp_path / e["tsl_stats"]).write_text(
        "Word,TSL Rank,SFI,U\nairport,1,60,1\nrefund,2,59,1\nkick,3,58,1\ninvoice,4,57,1\n"
        "memo,5,56,1\nmini,6,50,1\nresume,7,49,1\n"
    )
    xlsx(
        tmp_path / e["tsl_definitions"],
        [
            ["Word", "Definition"],
            ["airport", "a place where planes take off and land"],
            ["refund", "money given back to you"],
            ["kick", "to hit with your foot"],
            ["invoice", "a list of goods sent and what they cost"],
            ["memo", "a short memo to people at work"],  # gives the word away: the model writes one
            ["mini", "small"],
        ],
    )
    (tmp_path / e["tsl_forms"]).write_text(
        "## comment\r\nrefund,refunds,refunded\r\ninvoice,invoices\r\nmemo,memos\r\n"
    )
    (tmp_path / e["bsl_stats"]).write_text(
        "Word,BSL Rank,Band,SFI,U\nrefund,1,1,60,1\nmerger,2,1,59,1\nequity,3,1,58,1\n"
        "dividend,4,1,57,1\naudit,5,1,56,1\nnon,6,1,55,1\n",
        encoding="latin-1",
    )
    (tmp_path / e["bsl_forms"]).write_text("merger,mergers\r\naudit,audits,audited\r\n")
    return tmp_path


def test_extra_headwords_levels_sources_and_what_is_dropped(files: Path) -> None:
    words, dropped = hw.read_extra(files, known={"kick", "habit"})
    by = {w.lemma: w for w in words}
    assert [w.lemma for w in words] == [
        "airport", "refund", "invoice", "memo", "resume", "merger", "equity", "dividend", "audit",
    ]  # fmt: skip
    assert by["refund"].source == "tsl"  # in both lists: the TSL's, with its definition
    assert by["airport"].level == "B1"  # at least NGSL B1's frequency
    assert {by[w].level for w in ("refund", "invoice")} == {"B2"}  # the more frequent half
    assert by["memo"].level == "C1" and by["resume"].level == "C1"  # rarer half / no figure
    assert (
        not by["refund"].needs_definition and by["refund"].definition == "money given back to you"
    )
    assert by["memo"].needs_definition  # its own definition used the word
    assert by["resume"].needs_definition  # no definition in the file
    assert all(by[w].needs_definition for w in ("merger", "equity", "dividend", "audit"))
    assert by["merger"].forms == ("merger", "mergers")
    assert {(d.lemma, d.reason) for d in dropped} == {
        ("mini", "a prefix, not a word"),
        ("non", "a prefix, not a word"),
    }


def head(lemma: str, definition: str = "", source: hw.Source = "bsl") -> hw.Headword:
    return hw.Headword(lemma, source, "B2", definition, (lemma, lemma + "s"))


def entry(lemma: str, **over: object) -> EntryOut:
    data: dict[str, object] = {
        "lemma": lemma,
        "pos": "noun",
        "vi": "nghĩa",
        "example": f"The board talked about the {lemma} at length this morning.",
        "answer": lemma,
        "definition": "when two companies join and become one company",
    }
    return EntryOut.model_validate(data | over)


@pytest.mark.parametrize(
    "definition",
    [
        None,
        "",
        "two mergers make one",  # a form of the word
        "a word that is described here with far more than fifteen words in total for this test",
    ],
)
def test_a_model_definition_must_exist_be_short_and_not_give_the_word_away(
    definition: str | None,
) -> None:
    word, why = imp.build_word(head("merger"), entry("merger", definition=definition), set())
    assert word is None and why is not None and "definition" in why


def test_a_list_definition_is_never_replaced_by_the_models() -> None:
    word, _ = imp.build_word(
        head("refund", "money given back to you", "tsl"), entry("refund"), set()
    )
    assert word is not None and word.definition == "money given back to you"
    assert word.origin == "tsl"


def test_the_prompt_marks_missing_definitions_and_leaves_ngsl_prompts_unchanged() -> None:
    text = imp.prompt([head("merger"), head("refund", "money given back to you", "tsl")], ["work"])
    assert "- merger [write a definition]" in text
    assert "- refund: money given back to you" in text
    assert imp.EXTRA_SYSTEM.startswith(imp.SYSTEM)  # the NGSL/NAWL cache keys stay valid


def word(lemma: str, pos: str = "noun", definition: str = "a thing that is used in a test") -> Word:
    return Word.model_validate(
        {
            "lemma": lemma,
            "pos": pos,
            "level": "B2",
            "origin": "bsl",
            "definition": definition,
            "examples": [{"text": f"This is the {lemma} we need.", "answer": lemma}],
        }
    )


POOL = [word(w) for w in ("merger", "equity", "dividend", "audit", "asset")] + [
    word("hire", "verb")
]


def test_a_question_has_the_word_and_three_others_of_its_part_of_speech_same_every_time() -> None:
    q = dc.question(0, POOL[0], POOL)
    assert "merger" in q.options and len(set(q.options)) == 4
    assert "hire" not in q.options  # another part of speech
    assert dc.question(0, POOL[0], list(reversed(POOL))) == q  # deterministic: the cache hits
    assert "merger" not in dc.prompt([q]).split("Definition:")[1].split("\n")[0]
    with pytest.raises(ValueError):
        dc.question(0, POOL[0], POOL[:2])


def test_verdicts_keep_no_reply_apart_from_a_negative_answer() -> None:
    q = dc.question(7, POOL[0], POOL)
    other = next(o for o in q.options if o != "merger")
    assert dc.verdict(q, "Merger.") == "right"
    assert dc.verdict(q, other) == "wrong"
    assert dc.verdict(q, "?") == "cannot_tell"
    assert dc.verdict(q, "takeover") == "cannot_tell"  # not one of the four
    assert dc.verdict(q, None) == "no_reply"
    assert dc.verdicts([q], None) == {"merger": "no_reply"}
    assert dc.verdicts([q], dc.Reply(answers=[])) == {"merger": "no_reply"}
    assert dc.verdicts([q], dc.Reply(answers=[dc.Answer(id=7, word="merger")])) == {
        "merger": "right"
    }


def test_tsl_and_bsl_words_have_their_own_bands() -> None:
    assert band_of("B2", "tsl") == "vocab-tsl" and band_of("C1", "bsl") == "vocab-bsl"
    assert band_of("B2", "ngsl") == "vocab-b2"
    assert {"vocab-tsl", "vocab-bsl"} <= set(VOCAB_BANDS)


class FakeModel(imp.Model):
    def __init__(self) -> None:
        self.usage = imp.Usage()
        self.systems: set[str] = set()

    def entries(
        self, batch: Sequence[hw.Headword], topics: Sequence[str], system: str = imp.SYSTEM
    ) -> list[EntryOut]:
        self.systems.add(system)
        return [
            EntryOut(
                lemma=h.lemma,
                pos="noun",
                vi="nghĩa",
                answer=h.forms[0],
                ipa="/ˈtest/",
                example=f"Everyone at the office talked about the {h.forms[0]} today.",
                definition=f"definition number {i} written for this test"
                if h.needs_definition
                else None,
            )
            for i, h in enumerate(batch)
        ]


class FakeChecker(imp.Checker):
    """Answers by lemma: a word, "?", "WRONG" (another option) or None (no answer for it)."""

    def __init__(self, answers: dict[str, str | None]) -> None:
        self.answers, self.calls, self.failed = answers, 0, 0

    def ask(self, batch: Sequence[dc.Question]) -> dc.Reply | None:
        self.calls += 1
        out = []
        for q in batch:
            a = self.answers.get(q.lemma, q.lemma)
            if a is None:
                continue
            if a == "WRONG":
                a = next(o for o in q.options if o != q.lemma)
            out.append(dc.Answer(id=q.id, word=a))
        return dc.Reply(answers=out)


def existing(out: Path) -> None:
    """An NGSL/NAWL import already in place (the extra step only adds to it)."""
    out.mkdir()
    base = [
        word(w).model_copy(update={"origin": "ngsl"}) for w in ("habit", "kick", "harbour", "tide")
    ]
    imp.write_list(out, base, AUTHORED)


def test_extra_adds_checked_words_and_never_touches_the_existing_ones(
    files: Path, tmp_path: Path
) -> None:
    out = tmp_path / "out"
    existing(out)
    before = (out / "core-seed.yaml").read_text(encoding="utf-8")
    model = FakeModel()
    report = imp.run_extra(
        files,
        out,
        model,
        FakeChecker({"equity": "WRONG", "dividend": "?", "audit": None}),
        lambda ws: {w: "tˈɛst" for w in ws},
        AUTHORED,
    )
    assert model.systems == {imp.EXTRA_SYSTEM}
    listed = load_wordlist(out / "core-seed.yaml")
    lemmas = {w.lemma for w in listed.words}
    assert {"habit", "kick", "harbour", "tide"} <= lemmas  # copied unchanged
    for w in ("habit", "kick", "harbour", "tide"):
        old = next(x for x in WordList.model_validate(yaml.safe_load(before)).words if x.lemma == w)
        assert listed.get(old.key) == old
    assert {"airport", "refund", "invoice", "memo", "resume", "merger"} <= lemmas
    assert not {"equity", "dividend", "audit"} & lemmas  # wrong, cannot tell, no reply
    assert report.check == {"right": 3, "wrong": 1, "cannot_tell": 1, "no_reply": 1}
    assert report.unfinished == 1 and report.model_definitions == 3  # memo, resume, merger
    assert report.dropped["blind check: wrong"] == 1
    assert report.dropped["blind check: cannot tell"] == 1
    assert report.by_source == {"tsl": 5, "bsl": 1}
    assert report.checker_calls == 1
    saved = json.loads((out / imp.EXTRA_REPORT).read_text(encoding="utf-8"))
    assert saved["kept"] == 6 and saved["read"] == 11  # 9 words + 2 prefixes
    assert (
        "Business Service List by Browne, C. and Culligan, B."
        in (out / "core-seed.yaml").read_text(encoding="utf-8")[:900]
    )

    # A rerun is complete on its own: the word that got no reply is asked again and now kept.
    again = imp.run_extra(
        files, out, FakeModel(), FakeChecker({"equity": "WRONG", "dividend": "?"}),
        lambda ws: {}, AUTHORED,
    )  # fmt: skip
    assert again.kept == 7 and again.unfinished == 0
    assert "audit" in {w.lemma for w in load_wordlist(out / "core-seed.yaml").words}


def test_extra_needs_the_ngsl_import_first(files: Path, tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        imp.run_extra(
            files, tmp_path / "none", FakeModel(), FakeChecker({}), lambda ws: {}, AUTHORED
        )
