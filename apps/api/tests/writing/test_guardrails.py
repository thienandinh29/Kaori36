"""Step 2.7: padding, memorised templates and prompt words, before any band."""

from pathlib import Path

from app.writing.guardrails import (
    check,
    load_templates,
    prompt_overlap,
    repeated,
    templates_found,
)

TEMPLATES = load_templates(
    Path(__file__).resolve().parents[4] / "data" / "writing" / "templates.yaml"
)
PROMPT = (
    "Some people think that governments should ban plastic bags in supermarkets. "
    "To what extent do you agree or disagree?"
)
ESSAY = (
    "Plastic bags are cheap, but they pollute rivers and harm animals for many years. "
    "A ban in supermarkets would push shoppers to bring their own bags. "
    "Governments in several countries have already tried this with good results."
)


def test_an_ordinary_essay_passes_every_check() -> None:
    g = check(ESSAY, PROMPT, TEMPLATES)
    assert (g.repeated_words, g.template_words, g.padded, g.off_topic) == (0, 0, False, False)
    assert g.own_words == g.words
    assert g.prompt_overlap is not None and g.prompt_overlap >= 0.5
    assert {"plastic", "supermarket", "govern"} <= set(g.prompt_words_used) | {"govern"}


def test_a_doubled_essay_is_padding_and_its_copy_does_not_count() -> None:
    g = check(ESSAY + "\n\n" + ESSAY, PROMPT, TEMPLATES)
    assert g.padded and g.repeated_words == g.words // 2
    assert g.own_words == g.words - g.repeated_words
    assert len(g.repeated_sentences) == 3


def test_a_short_sentence_said_twice_is_ordinary() -> None:
    words, sents = repeated("I agree. Cars pollute the air in cities. I agree.")
    assert (words, sents) == (0, [])


def test_memorised_openers_are_found_whatever_the_case_or_apostrophe() -> None:
    text = (
        "One of the most conspicuous trends of today\N{RIGHT SINGLE QUOTATION MARK}s world "
        "is shopping online. "
        "IT IS AN UNDENIABLE FACT THAT bags pollute rivers."
    )
    n, found = templates_found(text, TEMPLATES)
    assert len(found) == 2 and n == 16
    assert check(text, PROMPT, TEMPLATES).padded  # mostly templates


def test_an_essay_on_another_topic_is_flagged_and_a_short_prompt_is_not_judged() -> None:
    other = "Tourism brings money to small towns, and visitors enjoy local food and festivals."
    g = check(other, PROMPT, TEMPLATES)
    assert g.off_topic and g.prompt_overlap == 0.0
    assert prompt_overlap(other, "Discuss both views.") == (None, [])
