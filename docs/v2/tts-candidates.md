# Text-to-speech candidates (speech step S2)

For the owner's decision before a self-hosted voice is built (`specs/speech/spec.md`, S2). Read on 15 Nov 2026 from each model's
Hugging Face API and card, the packages' PyPI metadata and the projects' licence files. **These are the publishers' claims**;
the owner reads each licence page before choosing, as for every source in this project.

## The two serious candidates

| | **Kokoro-82M** (`hexgrad/Kokoro-82M`, rev `f3ff3571791e`) | **Piper** (`rhasspy/piper-voices`, rev `e9ab671f2a0e`) |
|---|---|---|
| Weights licence | Apache-2.0 (card) | Repository MIT; **each voice has its own dataset licence** (below) |
| Size | 82M parameters; 355 MB of weights in the repository (the model plus 54 voices) | One small ONNX file per voice and quality |
| British voices | 8 (4 female, 4 male). Its own grades: `bf_emma` B- (hours of data); `bf_isabella` C; the rest D | `en_GB`: alan, alba, aru, cori, jenny_dioco, northern_english_male, semaine, southern_english_female, vctk |
| Training data | "Permissive/non-copyrighted audio": public domain, Apache/MIT audio, CC BY audio (listed), and **synthetic audio from closed TTS models of large providers**. A few hundred hours | Per voice, below |
| Code licence | `kokoro` and `misaki` packages: Apache-2.0. **But English needs `misaki[en]`, which requires `phonemizer-fork` (GPL-3.0+) and `espeakng-loader` (the espeak-ng library, GPL-3.0)** | The current `piper-tts` package (1.8.0, maintained as `OHF-Voice/piper1-gpl`): **GPL-3.0-or-later**. The original `rhasspy/piper` code was MIT |
| Runs on | CPU (PyTorch) | CPU (onnxruntime), very light |

### Piper's British voices, by the dataset licence on each voice's model card

| Voice | Dataset licence | Use? |
|---|---|---|
| `cori` (high, medium) | LibriVox, **public domain**; about 24 h, one female speaker | Best on licence |
| `alba` (medium) | CC BY 4.0 (University of Edinburgh) | Yes, with attribution |
| `northern_english_male`, `southern_english_female` | CC BY-SA 4.0 (OpenSLR 83) | ShareAlike: the audio is fine to serve; read what it asks before redistributing the voice |
| `semaine` | **CC BY-NC-SA 4.0** | NonCommercial: flag; not for a paid tier |
| `alan`, `jenny_dioco` | "See URL" | Not until the owner has read the URL |
| `aru`, `vctk` | Not read yet | Read first |

## Rejected (from their cards)
- `coqui/XTTS-v2`: Coqui Public Model License (non-commercial).
- `SWivid/F5-TTS`: weights CC BY-NC 4.0.
- `facebook/mms-tts-eng`: CC BY-NC 4.0.

## Possible, but not first choices
- `parler-tts/parler-tts-mini-v1`: Apache-2.0, trained on MLS English and LibriTTS-R. 3.5 GB, the voice is described in words;
  heavy for the laptop.
- `microsoft/speecht5_tts`: MIT, 585 MB, needs a speaker embedding (from another dataset); lower quality than the two above.
- `myshell-ai/MeloTTS-English`: MIT, 208 MB; its card's metadata lists the wrong language, so read carefully before trusting it.

## What GPL means here (not legal advice)
Both candidates bring GPL-3.0 code for turning text into phonemes. Run as **its own container that the app calls over HTTP**,
like LanguageTool, the GPL code stays inside that service and the project's Apache code does not link to it. The usual reading
is that this keeps them separate programs; the obligation is then to offer the service's source when distributing its image.
The owner decides whether that is acceptable. (The pronunciation spec already avoids espeak-ng in the product for the same
reason.)

## Recommendation
1. **Kokoro with `bf_emma`** for quality and one consistent British voice; accept the GPL phonemizer inside its own container.
   Open point: its training used synthetic audio from closed commercial TTS models, which some providers' terms restrict; the
   card says it is fine to deploy, and the owner weighs that.
2. **Piper with `cori`** if the cleanest data licence matters most: public-domain training audio, a very light CPU model; the
   engine itself is GPL-3.0 now, in its own container.
Either way: cache audio by (text, voice), label it "giọng đọc máy", and keep the browser voice (S1) as the fallback.

## Decided (16 Nov 2026)
The owner asked the agent to choose: **Piper with `en_GB-cori-high`**, built as `tts/` (`specs/speech/spec.md`, S2).
- Why: public-domain training data; a light runtime (onnxruntime, no PyTorch) that fits the laptop (about 200 MB in the
  container); one clear British voice.
- GPL-3.0: accepted inside its own container (`tts/` is licensed GPL-3.0-or-later; see `NOTICE`).
- Open for the owner: read the voice's model card and LibriVox's public-domain statement yourself; switch to another voice
  later by changing the pin in `docker-compose.yml`.
