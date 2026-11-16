# ruff: noqa: RUF001, RUF003
"""IPA agreement (specs/vocabulary-import, step 5): notation folds, substance never does."""

import pytest

from app.vocabulary.ipa import agree, shape


@pytest.mark.parametrize(
    ("dictionary", "espeak"),
    [
        ("/ɪmˈpɔːtənt/", "ɪmpˈɔːtənt"),  # stress before the syllable vs before the vowel
        ("/rɪˈdjuːs/", "ɹɪdjˈuːs"),  # ɹ is r
        ("/ˈbenɪfɪt/", "bˈɛnɪfˌɪt"),  # ɛ is e; secondary stress ignored
        ("/əˈfekt/", "ɐfˈɛkt"),  # ɐ is ə
        ("/tʃuːz/", "tʃˈuːz"),  # one syllable: the mark is optional
        ("/ˌedʒuˈkeɪʃən/", "ˌɛdʒuːkˈeɪʃən"),  # weak u written with or without length
        ("/ˈlɪtərəsi/", "lˈɪtəɹəsɪ"),  # the final happY vowel
        ("/vɒlənˈtɪə/", "vˌɒləntˈiə"),  # espeak writes the NEAR vowel iə
        ("/ˈbʌtn̩/", "bˈʌtən"),  # syllabic n
    ],
)
def test_the_same_pronunciation_in_two_notations_agrees(dictionary: str, espeak: str) -> None:
    assert agree(dictionary, espeak)


@pytest.mark.parametrize(
    ("a", "b"),
    [
        ("/ɪkˈspɔːt/", "ˈɪkspɔːt"),  # verb vs noun stress
        ("/ɪnˈvaɪrənmənt/", "ɛnvˈaɪɹənmənt"),  # a different vowel
        ("/ˈɪnkʌm/", "ˈɪŋkʌm"),  # a different consonant
        ("/kəˈmjuːnəti/", "kəmjˈuːnɪtɪ"),  # ə vs ɪ in a weak syllable is still a difference
        ("/ˈdɪsəplɪn/", "dˈɪsɪplˌɪn"),
    ],
)
def test_a_different_sound_or_stress_disagrees(a: str, b: str) -> None:
    assert not agree(a, b)


def test_unmarked_stress_on_a_long_word_and_junk_never_agree() -> None:
    assert not agree("/kəmpjuːtə/", "kəmpjˈuːtɐ")  # stress not marked: cannot be compared
    assert shape("") is None and shape("/ab1/") is None and shape("ˈaˈb") is None
    assert not agree("", "")
