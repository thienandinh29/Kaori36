# Spec: hearing English (text to speech)

The owner's request (15 Nov 2026): a button that speaks a word, a phrase or a sentence. Two steps: the browser's own voice now,
a self-hosted model later. The button stays the same; only where the audio comes from changes.

## S1: the browser's voice (built in this step)
- A "Nghe" button (and "Nghe chậm", rate 0.7) next to English text: a word card's word and example; a saved phrase when it is
  shown as new, and the answer after grading. **Never on text the learner must produce** (a gap-fill's hidden answer, a question
  that is still open), so hearing it never gives the answer away.
- Uses the browser's `speechSynthesis`. Voice choice (`lib/english/speech.ts`, pure, tested): English only; British first, then
  American, then any English; on-device voices before network ones.
- **Privacy:** some browser voices are network services that receive the text. Word-list content (public) may use them; text
  from the learner's own essays (saved phrases) uses **on-device voices only**, and the button is hidden when there is none.
- No English voice, no `speechSynthesis`, or text over 300 characters: no button (nothing broken, nothing promised).
- Labelled "Giọng đọc máy" in the button's title: a machine voice, not a model of pronunciation.
- No route, no API change, no dependency, no migration.

## S2: a self-hosted voice (decision first, `docs/v2/tts-candidates.md`)
A small text-to-speech model in its own container (like LanguageTool), `POST /speak {text, voice}` → audio, cached by
(text, voice), CPU only. Needed for Listening (phase 4) and for one voice for everyone. **Before building:** the owner reads the
licence of the code, of each voice's weights and of their training data, and any GPL component (e.g. espeak-ng) is weighed.
Candidates and what their cards say are in `docs/v2/tts-candidates.md`.

## Acceptance (S1)
Vitest: voice ranking (British, American, other English, on-device first, network refused for private text, none), text
preparation (NFC, whitespace, quotes, empty, too long). The button renders nothing without `speechSynthesis` (unit-tested
helper), and the existing browser tests still pass.
