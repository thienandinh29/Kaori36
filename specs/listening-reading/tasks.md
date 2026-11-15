# Tasks: Listening and Reading (phase 4)

**Owner's decisions, before 4.1 starts:**
- [ ] Read the licence of each candidate text source on its own page and set its status in `data/sources/english-candidates.yaml`
      (including VOA Learning English, which is not listed yet), noting any ShareAlike or NonCommercial term
- [ ] A verifier of a different family from DeepSeek: which provider and key (the gateway refuses free OpenRouter models), and
      the daily cost cap for generation and verification
- [ ] Audio: text to speech (which voices, after reading each voice's model card), real recordings, or both
- [ ] A licensed CEFR word list for text levels (the same open decision as vocabulary and writing)

**Owner's hands-on work:**
- [ ] Review the generated items (about 10 an hour); plant errors in 50 items for the verifier test; label 50 items good or not
- [ ] Label 30 texts with a CEFR level; add the Reading and Listening skill nodes to the roadmap

**Build (agent), in order:**
- [ ] 4.1 text bank with licences and level features
- [ ] 4.2 Reading items, blind verification, review queue, planted-error test
- [ ] 4.3 Reading practice, skill nodes, evidence
- [ ] 4.4 Listening audio and items
- [ ] 4.5 gate report

**4.1 built (15 Nov 2026):** `specs/listening-reading/step-4.1.md`; `app/texts/` (bank loader tied to verified sources, level
features, CLI). No texts are shipped: the owner adds them once a source is verified.
