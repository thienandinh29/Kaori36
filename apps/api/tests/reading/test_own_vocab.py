"""Words offered from a pasted Reading passage (step 4.3d part 2, "Vocabulary")."""

from app.config import REPO_ROOT
from app.reading import own_vocab as v

INDEX = v.FormIndex({
    "abandon": ("abandon", "B1"), "abandoned": ("abandon", "B1"), "estuary": ("estuary", "C1"),
    "species": ("species", "B2"), "river": ("river", "A1"), "seals": ("seal", "B2"),
    "the": ("the", "A1"), "programme": ("programme", "B1"), "began": ("begin", "A1"),
    "was": ("be", "A1"), "live": ("live", "A1"), "near": ("near", "A1"), "and": ("and", "A1"),
    "many": ("many", "A1"), "returned": ("return", "A2"),
})  # fmt: skip
PASSAGE = (
    "The river was abandoned by Smith in 1957. Seals live near the estuary.\n\n"
    "A programme began. Many species returned to the river, and the estuary recovered."
)


def test_the_form_index_maps_forms_to_headwords_at_their_lowest_level() -> None:
    index = v.build_form_index(REPO_ROOT / "data-sa" / "vocabulary" / "forms.yaml")
    assert index.get("Abandoned") == ("abandon", "B1")
    assert index.get("zzzz") is None


def test_words_above_the_level_with_their_first_sentence_and_no_names() -> None:
    got = v.words(PASSAGE, "B1", INDEX)
    by = {w.headword: w for w in got}
    # listed words by level, nearest the learner first; "recovered" is outside the lists, last
    assert [w.headword for w in got] == ["seal", "species", "estuary", "recovered"]
    assert by["estuary"].sentence == "Seals live near the estuary."  # the first occurrence
    assert by["seal"].form == "Seals" and by["seal"].level == "B2"
    assert "smith" not in by and "abandon" not in by  # a name; a word at the learner's level
    assert by["recovered"].level is None and by["recovered"].gloss is None


def test_a_deciding_sentence_adds_its_b1_words_and_comes_first() -> None:
    deciding = v.deciding_sentences(PASSAGE, ["a programme began"])
    assert deciding == {"A programme began."}
    got = v.words(PASSAGE, "B1", INDEX, deciding)
    assert got[0].headword == "programme" and got[0].deciding  # B1, kept for the wrong answer
    assert "begin" not in {w.headword for w in got}  # A1, even in a deciding sentence


def test_the_level_defaults_to_b1_and_glosses_come_from_the_list() -> None:
    assert v.learner_level(None) == ("B1", "default")
    assert v.learner_level("B2") == ("B2", "level_test")
    got = v.words(PASSAGE, "B2", INDEX, gloss=lambda h: v.Gloss("a place", "cửa sông") if h ==
                  "estuary" else None)  # fmt: skip
    assert [w.headword for w in got if w.level] == ["estuary"]  # only C1 is above B2
    assert got[0].to_json()["vi"] == "cửa sông"


def test_pick_keeps_only_offered_forms_and_long_sentences_are_skipped() -> None:
    offered = v.words(PASSAGE, "B1", INDEX)
    assert [w.form for w in v.pick(offered, ["SPECIES", "made-up"])] == ["species"]
    long = "The estuary " + "word " * 200 + "ends."
    assert v.words(long, "B1", INDEX) == []
