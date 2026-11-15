from pathlib import Path

import pytest
import yaml  # type: ignore[import-untyped]

from app.sources.candidates import Candidates
from app.texts import bank
from app.texts.bank import TextEntry, admit, load_bank
from app.texts.features import features

SENTENCES = [
    "The river runs past the old town every morning.",
    "Children walk to school along the quiet road.",
    "Farmers bring fresh bread and apples to the market.",
    "In winter the water is cold and the wind is strong.",
    "People sit by the fire and tell long stories.",
    "Spring brings warm rain and green fields again.",
    "The bridge was built by local workers many years ago.",
    "Everyone remembers the summer when the river dried up.",
    "Now the town is proud of its clean water and gardens.",
    "Visitors often stop to take photographs near the bridge.",
]
TEXT = " ".join(SENTENCES)  # 100+ words


def candidates() -> Candidates:
    base = {"url": "https://example.org/", "use": "reading", "believed_licence": "CC BY-SA 4.0"}
    return Candidates.model_validate(
        {
            "candidates": [
                {**base, "slug": "good", "name": "Good", "status": "verified",
                 "licence": "CC BY-SA 4.0", "checked_on": "2026-11-15",
                 "licence_page": "https://example.org/licence"},
                {**base, "slug": "nc", "name": "NC", "status": "verified",
                 "licence": "CC BY-NC 4.0", "checked_on": "2026-11-15",
                 "licence_page": "https://example.org/licence"},
                {**base, "slug": "todo", "name": "Todo", "status": "to_check"},
                {**base, "slug": "bad", "name": "Bad", "status": "rejected", "reason": "ND"},
            ]
        }
    )  # fmt: skip


def entry(**over: object) -> TextEntry:
    data = {
        "slug": "river-town", "title": "A river town", "source": "good",
        "url": "https://example.org/river", "retrieved_on": "2026-11-15", "text": TEXT,
    }  # fmt: skip
    return TextEntry.model_validate({**data, **over})


def test_text_from_verified_source_carries_its_licence_and_flags() -> None:
    t = admit(entry(), candidates())
    assert not isinstance(t, str)
    assert t.licence == "CC BY-SA 4.0" and t.share_alike and not t.non_commercial
    assert str(t.checked_on) == "2026-11-15"
    t2 = admit(entry(source="nc"), candidates())
    assert not isinstance(t2, str) and t2.non_commercial and not t2.share_alike


@pytest.mark.parametrize("source", ["todo", "bad", "missing"])
def test_unverified_rejected_and_unknown_sources_are_refused(source: str) -> None:
    result = admit(entry(source=source), candidates())
    assert isinstance(result, str) and source in result


def test_word_bounds_and_nfc() -> None:
    assert "words" in str(admit(entry(text="Too short."), candidates()))
    assert "words" in str(admit(entry(text="word " * 1300), candidates()))
    decomposed = TEXT + " Café time again today."
    t = admit(entry(text=decomposed), candidates())
    assert not isinstance(t, str) and "Café" in t.text


def write(folder: Path, name: str, **over: object) -> None:
    data = {
        "slug": "river-town", "title": "A river town", "source": "good",
        "url": "https://example.org/river", "retrieved_on": "2026-11-15", "text": TEXT,
    }  # fmt: skip
    (folder / name).write_text(yaml.safe_dump({**data, **over}), encoding="utf-8")


def test_load_refuses_duplicates_and_bad_files(tmp_path: Path) -> None:
    write(tmp_path, "a.yaml")
    write(tmp_path, "b.yaml", slug="other")  # same text, another slug
    write(tmp_path, "c.yaml", text=TEXT + " Extra closing line here.")  # same slug, other text
    write(tmp_path, "d.yaml", source="todo", slug="d-one")
    (tmp_path / "e.yaml").write_text("slug: 1\n", encoding="utf-8")
    loaded = load_bank(tmp_path, candidates())
    assert [t.entry.slug for t in loaded.texts] == ["river-town"]
    reasons = {r.where: r.reason for r in loaded.refused}
    assert "same text" in reasons["b.yaml"]
    assert "duplicate slug" in reasons["c.yaml"]
    assert "verified" in reasons["d.yaml"]
    assert "e.yaml" in reasons


def test_features_on_a_small_text() -> None:
    f = features("The cat sat. The cat ran away quickly!")
    assert (f.words, f.sentences, f.mean_sentence_words) == (8, 2, 4.0)
    assert f.long_word_share == 0.125  # "quickly"
    assert f.type_token_ratio == 0.75  # the, cat, sat, ran, away, quickly of 8
    assert f.unknown_share is None


def test_unknown_share_with_a_known_set_and_ttr_window() -> None:
    f = features("The cat sat. The cat ran.", known={"the", "cat", "sat"})
    assert f.unknown_share == pytest.approx(0.167, abs=0.001)  # "ran" of 6
    long = " ".join(f"w{i}" for i in range(100)) + " " + " ".join(["w0"] * 500) + "."
    assert features(long).type_token_ratio == 1.0  # only the first 100 words count


def test_empty_text_is_safe() -> None:
    f = features("", known=set())
    assert f.words == 0 and f.mean_sentence_words == 0.0 and f.unknown_share is None


def test_cli_prints_a_line_per_text_and_the_exit_code(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cand = tmp_path / "cand.yaml"
    cand.write_text(
        yaml.safe_dump(candidates().model_dump(mode="json", exclude_none=True)), encoding="utf-8"
    )
    folder = tmp_path / "texts"
    folder.mkdir()
    write(folder, "a.yaml")
    assert bank.main([str(folder), str(cand)]) == 0
    out = capsys.readouterr().out
    assert "river-town" in out and "CC BY-SA 4.0" in out and "share-alike" in out
    write(folder, "b.yaml", source="todo", slug="b-one")
    assert bank.main([str(folder), str(cand)]) == 1
    assert "REFUSED b.yaml" in capsys.readouterr().out


def test_the_repository_bank_loads() -> None:
    assert bank.main([]) == 0
