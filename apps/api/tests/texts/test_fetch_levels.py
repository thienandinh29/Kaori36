"""CP1: text fetching (no network) and the feature-vs-label score."""

from datetime import date

import pytest

from app.texts.bank import TextEntry
from app.texts.fetch import paragraphs, simple_wiki, slugify, trim
from app.texts.levels import known_up_to, ranks, score, sheet_rows, spearman

SENTENCE = "Bees collect nectar from flowers and turn it into honey inside the hive."  # 14 words


def test_paragraphs_keep_prose_only_and_drop_captions_and_empty_references() -> None:
    raw = (
        "== History ==\n\n"
        f"{SENTENCE} They store it ().\n\n"
        "Figure: A bee on a flower.\n\n"
        "Short line.\n\n"
        "- a list item without a full stop"
    )
    assert paragraphs(raw) == [f"{SENTENCE} They store it."]


def test_trim_keeps_whole_paragraphs_inside_the_word_range() -> None:
    p = SENTENCE  # 14 words
    assert trim([p] * 5, low=40, high=60) == "\n\n".join([p] * 4)  # 56 words; a fifth would pass 60
    assert trim([p] * 2, low=40, high=60) is None  # too short


def test_simple_wiki_records_the_exact_revision_and_skips_short_or_missing_pages() -> None:
    pages = {
        "Honey bee": {
            "title": "Honey bee",
            "extract": "\n\n".join([SENTENCE] * 12),
            "revisions": [{"revid": 123}],
        },
        "Tiny": {"title": "Tiny", "extract": SENTENCE, "revisions": [{"revid": 1}]},
        "Nope": {"title": "Nope", "missing": True},
    }

    def get(url: str) -> dict[str, object]:
        title = next(t for t in pages if f"titles={t.replace(' ', '+')}" in url)
        return {"query": {"pages": [pages[title]]}}

    entries, skipped = simple_wiki(["Honey bee", "Tiny", "Nope"], get, pause=0)
    assert [e["slug"] for e in entries] == ["sw-honey-bee"]
    assert entries[0]["url"].endswith("oldid=123") and entries[0]["source"] == "simple-wikipedia"
    assert skipped == ["Tiny: under 150 words of prose", "Nope: no such page"]
    assert slugify("Café – Ünïcode!") == "cafe-unicode"  # noqa: RUF001 (an en dash, on purpose)


def test_spearman_with_ties_and_degenerate_cases() -> None:
    assert ranks([3.0, 1.0, 3.0]) == [2.5, 1.0, 2.5]
    assert spearman([1, 2, 3, 4], [10, 20, 30, 40]) == 1.0
    assert spearman([1, 2, 3, 4], [4, 3, 2, 1]) == -1.0
    assert spearman([1, 1, 1], [1, 2, 3]) is None and spearman([1, 2], [1, 2]) is None


def test_the_sheet_and_the_score() -> None:
    forms = {"bee": ["A2", "bees"], "honey": ["B1"], "nectar": ["C1"]}
    known = known_up_to(forms)
    assert {"bee", "bees", "honey"} <= known and "nectar" not in known
    entry = TextEntry(slug="t", title="T", source="simple-wikipedia", url="https://example.org/t",
                      retrieved_on=date(2026, 11, 18), text=" ".join([SENTENCE] * 8))  # fmt: skip
    row = sheet_rows([entry], known)[0]
    assert row["level"] == "" and 0 < row["unknown_share"] < 1
    rows = [
        {"level": lv, "mean_sentence_words": str(m), "words": "200", "long_word_share": "0.1",
         "type_token_ratio": "0.5", "unknown_share": "None"}
        for lv, m in [("A2", 8), ("B1", 12), ("B2", 18), ("C1", 25), ("", 30)]
    ]  # fmt: skip
    out = score(rows)
    assert out["labelled"] == 4 and out["unlabelled"] == 1
    assert out["spearman"]["mean_sentence_words"] == {"rho": 1.0, "n": 4}
    assert out["spearman"]["words"]["rho"] is None  # no spread
    assert out["spearman"]["unknown_share"]["n"] == 0
    assert out["levels"]["B2"] == 1


@pytest.mark.parametrize("bad", ["X1", "b3", "?"])
def test_unknown_labels_are_not_counted(bad: str) -> None:
    rows = [{"level": bad, "words": "1", "mean_sentence_words": "1", "long_word_share": "0",
             "type_token_ratio": "0", "unknown_share": "0"}]  # fmt: skip
    assert score(rows)["labelled"] == 0


def test_ielts_length_passages_join_sections_and_keep_paragraphs_whole() -> None:
    from app.texts.fetch import page_text

    p = f"{SENTENCE} They store it."  # 17 words
    sections = ["\n\n".join([p] * 2), "\n\n".join([p] * 3)]
    # Joined: paragraphs run on across sections, whole ones only, up to the limit.
    assert page_text(sections, low=60, high=70, joined=True) == "\n\n".join([p] * 4)  # 68
    # The first bank's rule: one section alone must be long enough.
    assert page_text(sections, low=60, high=70, joined=False) is None  # 34 and 51 alone
    assert page_text(sections, low=40, high=70, joined=False) == "\n\n".join([p] * 3)


def test_author_date_citations_are_removed_and_other_brackets_kept() -> None:
    from app.texts.fetch import CITATION

    cases = {
        "Congress banned it (White 2012). Later": "Congress banned it. Later",
        "a varied life (Smith and Jones 2010a; Lee 2011).": "a varied life.",
        "as shown (Brown et al. 2003).": "as shown.",
        "Rome was founded (753 BCE) by": "Rome was founded (753 BCE) by",
        "the (United Nations) and": "the (United Nations) and",
    }
    assert {k: CITATION.sub("", k) for k in cases} == cases


# --- 20 Nov 2026: boxes and end matter left out of OpenStax passages (the owner's review) ---
_LONG = (
    "Radioactive elements decay at a steady rate, so the amount left in a rock tells us how long "
    "ago the rock became solid and stopped exchanging material with its surroundings."
)
_MODULE = f"""<document xmlns="http://cnx.rice.edu/cnxml"><title>Dating</title><content>
<para id="p1">{_LONG}</para>
<note id="n1" class="astronomy link-to-learning"><para id="p2">PBS provides an
<link url="https://openstax.org/l/x">evolution series excerpt</link> that explains how we use
radioactive elements to date Earth.</para></note>
<note id="n2" class="beyond-book"><title>Reading the evidence</title><para id="p3">Careful
excavation has revealed that the tower likely took more than thirty years to build for the town.
</para></note>
<para id="p4">When astronauts first flew to the Moon, one of their most important tasks was to
bring back lunar rocks for radioactive age-dating in laboratories on Earth.</para>
<section id="s1" class="summary"><title>Summary</title><para id="p5">{_LONG}</para></section>
</content></document>"""


def test_link_boxes_and_end_matter_are_not_part_of_a_passage() -> None:
    from app.sources.openstax import parse_module
    from app.texts.fetch import NOT_PASSAGE, not_passage

    def prose(drop: tuple[str, ...]) -> str:
        page = parse_module(_MODULE, module="m1", chapter_no=1, chapter="c", source_uri="u",
                            drop_classes=drop)  # fmt: skip
        return " ".join(b.text for b in page.blocks if b.kind == "text")

    kept = prose(NOT_PASSAGE)
    assert "PBS provides" not in kept and "Summary" not in kept
    assert "Careful excavation" in kept  # a titled feature box is prose and stays
    assert kept.count("Radioactive elements decay") == 1
    assert "PBS provides" in prose(())  # other callers keep everything, as before
    gone = not_passage(_MODULE.encode())
    assert any(p.startswith("PBS provides") for p in gone)


def test_cleaning_a_bank_passage_removes_only_those_paragraphs() -> None:
    from app.texts.fetch import clean

    first = " ".join(_LONG.split())
    caption = "PBS provides an evolution series excerpt that explains how we use radioactive " \
        "elements to date Earth."  # fmt: skip
    moon = (
        "When astronauts first flew to the Moon, one of their most important tasks was to "
        "bring back lunar rocks for radioactive age-dating in laboratories on Earth."
    )
    text, removed = clean(f"{first}\n\n{caption}\n\n{moon}", _MODULE.encode())
    assert removed == [caption] and text == f"{first}\n\n{moon}"
    # A paragraph the summary repeats from the body stays where the body has it: only the
    # paragraphs that come from nowhere but a dropped box or section are removed.
    assert clean(f"{first}\n\n{moon}", _MODULE.encode()) == (f"{first}\n\n{moon}", [])
