"""Step 5.2 (specs/speaking/step-5.2.md): pauses from raw audio, placement, rates, clauses."""

import io
import math
import random
import wave

import pytest
import spacy

from app.pronunciation.quality import RATE
from app.speaking.clauses import clause_boundaries
from app.speaking.measures import (
    Pause,
    Word,
    is_filler,
    measure,
    pauses,
    place,
    pooled,
    speech_frames,
)

FRAME_S = 0.03


def wav(values: list[int]) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        clipped = (max(-32768, min(32767, v)) for v in values)
        w.writeframes(b"".join(v.to_bytes(2, "little", signed=True) for v in clipped))
    return buf.getvalue()


def tone(seconds: float, amp: float = 8000, freq: float = 220.0) -> list[int]:
    n = int(seconds * RATE)
    return [round(amp * math.sin(2 * math.pi * freq * i / RATE)) for i in range(n)]


def hiss(seconds: float, amp: int = 30, seed: int = 1) -> list[int]:
    rng = random.Random(seed)
    return [rng.randint(-amp, amp) for _ in range(int(seconds * RATE))]


def test_pauses_come_from_the_raw_audio_and_edges_are_not_pauses() -> None:
    # room 0.7 s, speech 1 s, gap 0.8 s, speech 1 s, gap 0.3 s (too short), speech 1 s, room 0.9 s
    audio = wav(
        hiss(0.7, seed=1) + tone(1.0) + hiss(0.8, seed=2) + tone(1.0) + hiss(0.3, seed=3)
        + tone(1.0) + hiss(0.9, seed=4)
    )  # fmt: skip
    found = pauses(speech_frames(audio))
    assert (
        len(found) == 1
    )  # only the 0.8 s gap: the 0.3 s one is too short, the edges are not pauses
    assert found[0].seconds == pytest.approx(0.8, abs=0.1)
    assert found[0].start == pytest.approx(1.7, abs=0.1)


def test_no_speech_or_bad_audio_gives_no_pauses() -> None:
    assert pauses(speech_frames(wav(hiss(2.0)))) == []
    assert speech_frames(b"not a wav") == [] and pauses([]) == []


def words(spec: list[tuple[str, float, float]]) -> list[Word]:
    return [Word(t, a, b) for t, a, b in spec]


WORDS = words(
    [
        ("Um,", 0.0, 0.4), ("I", 1.0, 1.1), ("think", 1.1, 1.5), ("it's", 1.5, 1.8),
        ("quite", 3.9, 4.2), ("small.", 4.2, 4.8), ("Yesterday", 5.6, 6.2), ("I", 6.2, 6.3),
        ("went", 6.3, 6.6), ("there", 6.6, 7.0),
    ]
)  # fmt: skip


def test_a_pause_is_placed_after_the_last_word_that_starts_before_its_middle() -> None:
    assert place(Pause(0.4, 1.0), WORDS) == 0  # after "Um,"
    assert place(Pause(1.8, 3.9), WORDS) == 3  # after "it's"
    assert place(Pause(4.8, 5.6), WORDS) == 5  # after "small."
    assert place(Pause(7.2, 8.0), WORDS) is None  # after the last word: not counted
    assert place(Pause(-1.0, -0.2), WORDS) is None  # before the first word


def test_measures_count_pauses_by_where_they_fall_and_never_judge() -> None:
    found = [Pause(0.4, 1.0), Pause(1.8, 3.9), Pause(4.8, 5.6)]
    boundaries = {0, 5}  # a clause ends after "Um," and after "small."
    m = measure(WORDS, found, boundaries, recording_seconds=8.0, asked_seconds=28)
    assert m["words"] == 10 and m["speaking_seconds"] == 7.0 and m["short"] is True
    assert m["speech_rate"] == pytest.approx(85.7, abs=0.1)  # 10 words in 7 s
    p = m["pauses"]
    assert (p["count"], p["between_clauses"], p["inside_clause"], p["long"]) == (3, 2, 1, 1)
    assert p["total_seconds"] == pytest.approx(0.6 + 2.1 + 0.8)
    assert p["longest_seconds"] == 2.1
    assert m["articulation_rate"] == pytest.approx(10 / (7.0 - 3.5) * 60, abs=0.1)
    assert m["fillers"]["count"] == 1  # "Um,"
    # runs between pauses: [Um,] [I think it's] [quite small.] [Yesterday I went there]
    assert m["longest_run"]["words"] == 4 and m["longest_run"]["seconds"] == pytest.approx(1.4)
    assert m["share_of_time"] == 0.25  # 7 s of speech in the 28 s asked
    assert not {"band", "score", "grade", "level"} & set(m)


def test_an_empty_or_unpaused_answer_is_handled() -> None:
    empty = measure([], [], set(), recording_seconds=3.0, asked_seconds=40)
    assert empty["words"] == 0 and empty["speech_rate"] is None and empty["short"] is True
    smooth = measure(WORDS, [], set(), recording_seconds=8.0)
    assert smooth["pauses"]["count"] == 0 and smooth["longest_run"]["words"] == 10
    assert smooth["pauses"]["per_minute"] == 0.0 and smooth["share_of_time"] is None
    one = measure(words([("Yes.", 0.2, 0.6)]), [Pause(1.0, 2.0)], set(), 3.0)
    assert one["pauses"]["unplaced"] == 1 and one["pauses"]["count"] == 0


def test_fillers_ignore_punctuation_and_case_and_not_other_words() -> None:
    assert all(is_filler(w) for w in ("Um,", "UH", "er.", "erm", "hmm"))
    assert not any(is_filler(w) for w in ("umbrella", "like", "you", "know", "errand"))


def test_pooled_sums_words_and_time_across_answers() -> None:
    a = measure(WORDS, [Pause(1.8, 3.9)], {5}, 8.0)
    b = measure(words([("Hello", 0.0, 0.5), ("there", 0.5, 1.0)]), [], set(), 2.0)
    total = pooled([a, b, measure([], [], set(), 1.0)])  # the empty answer adds nothing
    assert total is not None
    assert (total["answers"], total["words"]) == (2, 12)
    assert total["speaking_seconds"] == 8.0 and total["speech_rate"] == 90.0
    assert total["pauses_per_minute"] == 7.5 and total["inside_clause"] == 1
    assert total["longest_run_words"] == 6  # "quite small. Yesterday I went there" after the pause
    assert pooled([]) is None


@pytest.fixture(scope="module")
def nlp():  # type: ignore[no-untyped-def]
    return spacy.load("en_core_web_sm")


def cut(sentence: str, nlp) -> set[int]:  # type: ignore[no-untyped-def]
    return clause_boundaries(sentence.split(), nlp)


def test_clauses_start_at_a_joining_conjunction_or_a_separate_clause(nlp) -> None:  # type: ignore[no-untyped-def]
    # "I like music and I play piano": "and" joins two clauses, so a clause ends after "music"
    assert 2 in cut("I like music and I play piano", nlp)
    # "apples and oranges": "and" joins nouns, so there is no clause boundary
    assert 2 not in cut("I like apples and oranges", nlp)
    # a separate finite clause with its own subject starts a clause
    assert 3 in cut("Well I think so Yesterday I went home", nlp)
    assert {1, 5} <= cut("I think that it is good but I am not sure", nlp)


def test_the_recognisers_punctuation_is_not_used(nlp) -> None:  # type: ignore[no-untyped-def]
    # a full stop the recogniser puts at a long pause must not turn a hesitation into a boundary
    assert cut("I usually go to her. Mark it on Saturday with my sister.", nlp) == set()
    plain = cut("I stayed home because it rained", nlp)
    assert cut("I stayed home. because it rained", nlp) == plain == {2}
    assert cut("I stayed, home because, it rained", nlp) == plain


def test_clauses_start_at_subordinators_and_wh_words(nlp) -> None:  # type: ignore[no-untyped-def]
    assert 2 in cut("I stayed home because it rained", nlp)  # a clause ends before "because"
    assert 3 in cut("This is the man who called me", nlp)  # and before a relative pronoun
    assert 1 not in cut("I want to go home", nlp)  # "to" before a verb starts no clause


def test_fillers_are_transparent(nlp) -> None:  # type: ignore[no-untyped-def]
    inside = ["my", "hometown", "is", "uh", "quite", "small"]
    assert clause_boundaries(inside, nlp) == set()  # a pause beside "uh" is inside the clause
    assert clause_boundaries(["Um,", "uh,", "so"], nlp) >= {0, 1}  # before the clause begins
    assert clause_boundaries(["Um", "I", "think", "so"], nlp) == {0}
    assert clause_boundaries(["so", "Um", "uh"], nlp) == set()  # only fillers follow


def test_clause_boundaries_are_safe_on_tiny_input(nlp) -> None:  # type: ignore[no-untyped-def]
    assert clause_boundaries([], nlp) == set() and clause_boundaries(["Yes."], nlp) == set()
    assert clause_boundaries(["Um,", "yes"], lambda text: []) == {0}  # no parser: only fillers
