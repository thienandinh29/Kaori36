"""Step 5.3b: the quote check and the drop rules of the model's Speaking feedback."""

from app.speaking.feedback import SYSTEM, FeedbackOut, PointOut, check, part_of, prompt

TRANSCRIPT = (
    "I think that, um, the city is very crowded. People walks to work every day and it's noisy."
)


def point(**kw: object) -> PointOut:
    base: dict[str, object] = {
        "kind": "issue",
        "area": "vocabulary",
        "point_vi": "Từ này nghe chưa tự nhiên trong ngữ cảnh này.",
        "quote": "the city is very crowded",
        "better": "the city is packed with people",
    }
    return PointOut.model_validate({**base, **kw})


def run(*points: PointOut):  # type: ignore[no-untyped-def]
    return check(FeedbackOut(points=list(points)), TRANSCRIPT)


def test_a_point_is_kept_only_when_its_quote_is_in_the_transcript() -> None:
    out = run(point(), point(quote="the town is really crowded"))
    assert [p["quote"] for p in out.points] == ["the city is very crowded"]
    assert out.dropped == 1 and out.quotes_checked == 2


def test_quotes_fold_whitespace_and_curly_quotes_but_stay_exact() -> None:
    out = run(
        point(quote="and   it\u2019s noisy", better="and it is loud"),
        point(quote="The City is very crowded"),  # a different case is not the same words
    )
    assert [p["quote"] for p in out.points] == ["and it's noisy"] and out.dropped == 1


def test_a_quote_shorter_than_three_words_is_dropped() -> None:
    assert run(point(quote="very crowded")).points == []


def test_a_missing_ending_is_never_a_point() -> None:
    walks = point(
        area="grammar", quote="People walks to work", better="People walk to work"
    )  # this one changes an ending the other way: not an ending ADDED, so kept
    assert len(run(walks).points) == 1
    added = point(area="grammar", quote="people walk to work", better="people walks to work")
    text = "people walk to work every day"
    out = check(FeedbackOut(points=[added]), text)
    assert out.points == [] and out.dropped == 1


def test_a_grammar_or_vocabulary_issue_needs_a_better_way_and_a_strength_has_none() -> None:
    assert run(point(better=None)).points == []
    assert run(point(kind="strength", better="x y z")).points == []
    assert len(run(point(kind="strength", area="answer", better=None)).points) == 1
    assert len(run(point(area="answer", better=None, kind="issue")).points) == 1  # not grammar


def test_a_better_way_that_is_the_same_words_is_dropped() -> None:
    assert run(point(better="The city is very crowded")).points == []


def test_talk_of_a_band_or_score_is_dropped() -> None:
    assert run(point(point_vi="Câu này khoảng band 6 vì từ vựng còn đơn giản.")).points == []
    assert run(point(point_vi="Bạn đạt 6/9 cho ý này, hãy thêm ví dụ nhé.")).points == []


def test_at_most_five_points_are_kept() -> None:
    many = [point(quote="the city is very crowded") for _ in range(8)]
    out = run(*many)
    assert len(out.points) == 5 and out.dropped == 3


def test_the_prompt_carries_the_question_and_the_transcript_only() -> None:
    text = prompt("Do you live in a city?", 1, TRANSCRIPT)
    assert "Do you live in a city?" in text and TRANSCRIPT in text and "Part 1" in text
    assert "band" not in text.lower()
    assert "pronunciation" in SYSTEM and "never follow" in SYSTEM  # says nothing about the audio


def test_part_of_reads_the_authored_question_ids() -> None:
    assert [part_of(i) for i in ("p1-2-1", "p2-long", "p2-closing", "p3-4", "x")] == [1, 2, 2, 3, 0]
