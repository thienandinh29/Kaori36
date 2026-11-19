# Speech recognition candidates (phase 5, Speaking)

For the owner's decision before step 5.1 (`specs/speaking/tasks.md`: "the recognition model and its size, after reading its
card and measuring speed and memory on your machine"). Read and measured on 19 Nov 2026. Licences are **the publishers'
claims** on each model's Hugging Face card; the owner reads each card before choosing, as for every source in this project.
Scripts and every number: `docs/v2/asr-candidates/` (`make_audio.py`, `run_fw.py`, `run_hf.py`, `score.py`, `results.json`).

## What Speaking needs from a recogniser (from `specs/speaking/spec.md`)
1. **Word timestamps**: speech rate, pauses and the longest fluent run are computed from them.
2. **Verbatim text**: grammar feedback runs on the transcript, so a recogniser that writes *We were* when the learner said
   *We was* hides exactly the error to be taught. The Whisper card itself warns that it may produce "texts that are not
   actually spoken", because it also predicts likely words.
3. **Fillers kept** (*um*, *uh*): the spec counts them.
4. **Runs on our machine**: the owner's Docker VM was measured at about 4 GB, shared with the database, API, web and, when
   on, LanguageTool and the pronunciation model (about 1.9 GB).

## How it was measured
50 recordings (153 s) from the self-hosted voice: the 12 read-aloud prompts clean and with noise at 10 dB SNR; 20 sentences
with typical Vietnamese-learner errors (*She go to school*, *I am agree*, *We was very tired*, *Childrens like…*); 6 with
fillers. "Learner errors kept" checks, for each error sentence, that its specific error is still in the transcript (a
pattern per sentence, `score.MARKERS`; a misheard name or "I am" written "I'm" does not count as hiding it). All on this
container's 4 CPUs; faster-whisper int8, transformers float32.

**Limits, stated first.** One native British synthetic voice, so nothing here says how a model handles a Vietnamese accent,
real background noise or real hesitation; and 20 error sentences only separate large differences (16/20 has a 95% interval of
58–92%, 13/20 of 43–82%). Speed and memory are this container's; the owner's laptop will differ. Step 5.1 measures word
error rate on the owner's own 20 recordings with typed references, which is the real test.

## Results
| Model (licence on its card) | WER read | WER noisy | Learner errors kept | Fillers kept | Speed (× real time) | Peak RAM | Word times |
|---|---|---|---|---|---|---|---|
| Whisper tiny.en (Apache-2.0) | 0.8% | 12.9% | 13/20 | 1/9 | 0.12 | 0.3 GB | yes |
| Whisper base.en (Apache-2.0) | 0.0% | 3.2% | 11/20 | 5/9 | 0.18 | 0.4 GB | yes |
| ↳ with a verbatim prompt | **20.2%** | 18.5% | 13/20 | 5/9 | 1.05 | 0.6 GB | yes |
| distil-small.en (MIT) | 0.0% | 5.6% | 13/20 | 5/9 | 0.35 | 0.7 GB | yes |
| Whisper small.en (Apache-2.0) | 0.8% | 4.0% | 13/20 | 6/9 | 0.46 | 1.0 GB | yes |
| ↳ **with a verbatim prompt** | **0.8%** | **4.8%** | **16/20** | **8/9** | **0.47** | **0.9 GB** | yes |
| Whisper large-v3-turbo (MIT) | 0.0% | 0.8% | 15/20 | 6/9 | 1.21 | 2.2 GB | yes |
| ↳ with a verbatim prompt | 0.0% | 0.8% | 15/20 | 8/9 | 1.23 | 2.0 GB | yes |
| Moonshine tiny (MIT) | 2.4% | 16.9% | 12/20 | 3/9 | 0.03 | 0.5 GB | **no** |
| Moonshine base (MIT) | 0.0% | 11.3% | 9/20 | 5/9 | 0.04 | 0.6 GB | **no** |
| wav2vec2-large-960h-lv60-self (Apache-2.0) | 3.2% | 13.7% | 16/20 | 5/9 | 0.13 | 1.7 GB | yes (CTC) |

Whisper runs through faster-whisper (CTranslate2, MIT; the `Systran/faster-whisper-*` conversions list MIT). The verbatim
prompt is an example in the style wanted back (*"Umm, so, uh, I goes to school yesterday and he don't like it. We was, um,
very tired, and my friend have two cat."*).

## What the numbers say
- **Every model hides some learner errors.** The Whisper family "corrects" 4 to 9 of 20 (*two cat* → *cats*, *can speaks* →
  *speak*, *We was* → *were*, *Many student* → *students*). wav2vec2, which has no language model, keeps as many as the best
  Whisper setup but makes more plain mistakes under noise.
- **The prompt helps a model that is big enough.** small.en kept 13/20 errors and 6/9 fillers without it, 16/20 and 8/9 with
  it, at the same accuracy. On base.en the same prompt broke recognition: on the silence after a sentence it **invented
  text** from its internet training data ("Thanks for watching, and I'll see you in the next video", "See you next time!").
  In a Speaking feature, invented words would be checked for grammar as if the learner had said them.
- **Moonshine is the fastest but gives no word timestamps**, which the fluency measures need.
- **large-v3-turbo is the most accurate under noise** but needs about 2 GB and ran slower than real time here; on a 4 GB VM
  shared with the other services it does not fit.

## Not measured
- `nvidia/parakeet-tdt-0.6b-v2` (CC BY 4.0, trained on about 120,000 hours of English including LibriSpeech, Fisher, VCTK):
  needs the NeMo toolkit (several GB of dependencies). Worth a look if Whisper's corrections prove too costly.
- Training data: Whisper's card says 680,000 hours "collected from the internet" without a list; Moonshine's says 200,000 hours
  from the internet plus open datasets listed in its paper; distil-whisper is trained on Whisper's own pseudo-labels;
  wav2vec2-960h on LibriSpeech (public-domain audiobooks). The owner reads each card.

## Recommendation
**Whisper small.en through faster-whisper, int8, with a verbatim prompt**, and three guards built in step 5.1:
1. **Trim silence before recognition** (voice activity detection), and drop any words that fall outside detected speech.
   That is where the invented text appeared.
2. **Label grammar flags from speech as hints** ("gợi ý"), never as errors, until step 5.1 has measured on the owner's own
   recordings how many errors the recogniser hides and invents. These numbers say it hides about 1 in 5 at best.
3. **Measure on the owner's laptop** before deciding: about 1 GB and about half real time here; the laptop may be slower.

A possible later safeguard, not part of this decision: where Whisper and a model without a language model (wav2vec2, or the
phoneme recogniser phase 3 already runs) disagree on a word, mark that word uncertain and give no grammar feedback on it.

## Decisions for the owner
| Decision | Options | Recommended |
|---|---|---|
| The recogniser | small.en + prompt (about 1 GB); large-v3-turbo (2 GB, only on a bigger machine); wav2vec2 (keeps errors, weaker on noise, 1.7 GB) | small.en + prompt |
| Read the cards | `openai/whisper-small.en` (Apache-2.0), `Systran/faster-whisper-small.en` (MIT) | Read both before 5.1 |
| Grammar feedback on speech | Shown as errors / shown as hints until measured | Hints until step 5.1 measures it |
| Where it runs | The owner's laptop (measure first) / a rented machine later | The laptop, after measuring |
