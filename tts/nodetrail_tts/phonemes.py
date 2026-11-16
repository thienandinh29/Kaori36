"""British IPA from espeak-ng, the engine inside Piper (specs/vocabulary-import, step 5).

The import compares this with the model's transcription and shows IPA only when both agree; the
GPL engine stays in this service and the API reads its output over HTTP.
"""

from collections.abc import Callable

VOICE = "en-gb-x-rp"  # Received Pronunciation, the accent of British learner dictionaries

Phonemize = Callable[[str], str]


def espeak() -> Phonemize:
    from piper import espeakbridge
    from piper.phonemize_espeak import ESPEAK_DATA_DIR

    espeakbridge.initialize(str(ESPEAK_DATA_DIR))
    espeakbridge.set_voice(VOICE)

    def phonemize(word: str) -> str:
        return "".join(phonemes for phonemes, _, _ in espeakbridge.get_phonemes(word))

    return phonemize
