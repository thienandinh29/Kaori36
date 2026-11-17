# Tasks: Pronunciation (phase 3)

**Owner's decisions, before 3.1 starts:**
- [x] The voice policy (owner, 17 Nov 2026: the strict policy, as proposed): on-machine processing, delete after analysis by default, opt-in to keep, consent notice wording and version,
      a delete button (and whether a privacy review is needed before anyone else records)
- [x] The recognition model (owner, 17 Nov 2026: approved; the card is re-read before pinning in 3.2): read the card of `facebook/wav2vec2-xlsr-53-espeak-cv-ft` (and anything else you prefer), its training
      data's terms, and approve a pinned revision
- [x] New dependency for 3.2: `torchaudio` (owner, 17 Nov 2026: approved, in the pronunciation service only) (CTC forced alignment); PyTorch CPU is already in the scorer service
- [x] The target sounds list (owner, 17 Nov 2026: test all groups; `data/pronunciation/sounds.yaml`)
- [x] Where it runs (owner, 17 Nov 2026: one heavy compose profile at a time, a GPU notebook for heavy evaluation): the Docker VM has about 4 GB (measured); which services run together, or a GPU notebook for the heavy ones

**Owner's hands-on work:**
- [ ] Record 50–100 sentences of your own (and willing Vietnamese speakers' later), then label every marked phone right or wrong
- [ ] Choose thresholds on one half, check false alarms on the other, per target sound
- [ ] Write the Vietnamese tip for each target sound and record a model pronunciation of each prompt
- [ ] Add the pronunciation nodes to the roadmap

**Build (agent), in order:**
- [x] 3.1 recording, quality gate, consent, deletion (`step-3.1.md`; owner only until a privacy review)
- [x] 3.2 recognition service, alignment, GOP, evaluation on speechocean762 (built: the service, `step-3.2.md`;
      3.2b: the evaluation, sentence r 0.593, phone AUC 0.855)
- [ ] 3.3 target sounds, prompts, thresholds, false-alarm measurement
- [ ] 3.4 roadmap nodes, observation parameters, marks in the UI
- [ ] 3.5 optional fine-tuning
- [ ] Gate report in `docs/v2/pronunciation-eval.md`

**The owner's idea (16 Nov 2026): repeat each new word.** After a new word is taught in vocabulary, the learner says it
and phase 3's scoring checks each target sound (option C, chosen over browser or plain speech recognition).
- Built in phase 3, after 3.1–3.4, on top of the same per-sound scoring; uses the listen buttons already there (Piper).
- Optional at first, labelled "chưa kiểm chứng", and never blocking: a learner may skip it (no microphone, a quiet place).
- A blocking "must repeat correctly before the next word" mode is allowed only after the gate (false alarms ≤ 10% on the
  owner's labelled recordings), and only as a setting the learner turns on.
