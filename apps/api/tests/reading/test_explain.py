"""Explanations of the bank's Reading questions: code's checks (CP4b, bank step 1)."""

from app.reading.explain import ExplainOut, OptionOut, check, fingerprint, prompt
from app.reading.items import Completion, Mcq, Tfng

PASSAGE = (
    "The River Thames flows through London. By 1957 it was declared biologically dead.\n\n"
    "A cleanup programme began in the 1960s. Seals are often seen near the estuary today."
)
TF = Tfng(
    id="t-tfng-1",
    text="t",
    skill="detail",
    statement="The Thames was declared dead in 1957.",
    key="true",
    evidence=("By 1957 it was declared biologically dead.",),
)
NG = Tfng(id="t-tfng-2", text="t", skill="detail", statement="The government paid for the "
          "cleanup.", key="not_given")  # fmt: skip
MCQ = Mcq(id="t-mcq-1", text="t", skill="detail", stem="Seals are often seen",
          options=("in central London.", "near the estuary.", "in the 1950s."), key=1,
          evidence=("Seals are often seen near the estuary today.",))  # fmt: skip
GAP = Completion(id="t-c-1", text="t", skill="detail", sentence="A cleanup ___ began in the 1960s.",
                 accepted=("programme",), max_words=1,
                 evidence=("A cleanup programme began in the 1960s.",))  # fmt: skip
WHY = "Bài đọc nói rõ con sông bị tuyên bố là đã chết về mặt sinh học vào năm 1957."


def out(**over: object) -> ExplainOut:
    base: dict[str, object] = {
        "key_quotes": ["By 1957 it was declared biologically dead"],
        "why_key_vi": WHY,
        "skills": ["scan_detail", "paraphrase"],
    }
    return ExplainOut.model_validate(base | over)


def test_a_true_key_explained_from_its_deciding_sentence_is_kept() -> None:
    kept, problems = check(out(), PASSAGE, TF)
    assert problems == [] and kept is not None
    assert kept.skills == ("scan_detail", "paraphrase") and kept.options == ()
    assert kept.to_json()["key_quotes"] == ["By 1957 it was declared biologically dead"]


def test_code_refuses_made_up_quotes_other_sentences_english_and_bad_tags() -> None:
    _, p = check(out(key_quotes=["words that are not in it"]), PASSAGE, TF)
    assert any("not in the passage" in x for x in p)
    _, p = check(out(key_quotes=["Seals are often seen near the estuary"]), PASSAGE, TF)
    assert "key: the quote is not the question's deciding sentence" in p
    _, p = check(out(why_key_vi="The passage says it clearly in the second sentence."), PASSAGE, TF)
    assert "key: not in Vietnamese" in p
    _, p = check(out(why_key_vi="Đúng."), PASSAGE, TF)
    assert any("characters" in x for x in p)
    _, p = check(out(skills=["guessing"]), PASSAGE, TF)
    assert "skill tag 'guessing' is not on the list" in p
    _, p = check(out(skills=[]), PASSAGE, TF)
    assert "0 skill tags (needs 1-3)" in p


def test_not_given_must_say_what_the_passage_does_not_state() -> None:
    related = ["A cleanup programme began in the 1960s"]
    _, p = check(out(key_quotes=related, why_key_vi="Chương trình làm sạch bắt đầu từ thập niên "
                     "1960, đó là tất cả."), PASSAGE, NG)  # fmt: skip
    assert "key: a NOT GIVEN explanation must say what the passage does not state" in p
    kept, p = check(out(key_quotes=related, why_key_vi="Bài chỉ nói chương trình bắt đầu từ thập "
                        "niên 1960, không nói ai trả tiền."), PASSAGE, NG)  # fmt: skip
    assert p == [] and kept is not None  # the closest sentence need not be the evidence
    for said in ("không hề nói", "không được đề cập", "không có thông tin"):  # a real reply's words
        _, p = check(out(key_quotes=related, why_key_vi=f"Bài {said} về việc ai trả tiền cho "
                         "chương trình."), PASSAGE, NG)  # fmt: skip
        assert p == [], said


def test_every_wrong_option_gets_a_listed_trap_and_the_key_none() -> None:
    key = {"key_quotes": ["Seals are often seen near the estuary"],
           "why_key_vi": "Bài đọc nói hải cẩu thường được thấy gần cửa sông."}  # fmt: skip
    london = OptionOut(option=0, trap="wrong_part", quotes=["flows through London"],
                       why_vi="Bài có nhắc London nhưng không nói hải cẩu ở đó.")  # fmt: skip
    fifties = OptionOut(option=2, trap="not_stated", quotes=[],
                        why_vi="Bài không nói gì về hải cẩu trong thập niên 1950.")  # fmt: skip
    kept, p = check(out(**key, options=[fifties, london]), PASSAGE, MCQ)
    assert p == [] and kept is not None and [o.option for o in kept.options] == [0, 2]
    _, p = check(out(**key, options=[london]), PASSAGE, MCQ)
    assert "options not explained: [2]" in p
    keyed = OptionOut(option=1, trap="opposite", why_vi="Đây là đáp án nhưng bị gắn bẫy sai.")
    _, p = check(out(**key, options=[london, fifties, keyed]), PASSAGE, MCQ)
    assert "the key is given a trap" in p
    odd = fifties.model_copy(update={"trap": "tricky"})
    _, p = check(out(**key, options=[london, odd]), PASSAGE, MCQ)
    assert "option 2: trap 'tricky' is not on the list" in p
    lettered = london.model_copy(update={"why_vi": "Đáp án A sai vì bài không nói hải cẩu ở đó."})
    _, p = check(out(**key, options=[lettered, fifties]), PASSAGE, MCQ)
    assert "option 0: names an option by letter" in p  # learners see the options shuffled


def test_completion_and_the_prompt_and_fingerprint() -> None:
    kept, p = check(out(key_quotes=["A cleanup programme began in the 1960s"],
                        why_key_vi="Câu trong bài dùng đúng từ programme cho chỗ trống này."),
                    PASSAGE, GAP)  # fmt: skip
    assert p == [] and kept is not None
    text = prompt(PASSAGE, MCQ)
    assert "<<<PASSAGE" in text and "one entry for EACH wrong option (0, 2)" in text
    assert "Key: option 1" in text and "fng_logic" in text
    assert "an empty list" in prompt(PASSAGE, TF)
    assert fingerprint(TF) != fingerprint(TF.model_copy(update={"statement": "Changed words."}))
    assert fingerprint(TF) == fingerprint(TF.model_copy(update={"status": "approved"}))
