# Tasks: Listening and Reading (phase 4)

**Plan with checkpoints: `plan.md` (approved by the owner, 18 Nov 2026).** The decisions below are answered there: Simple
English Wikipedia and OpenStax as text sources; free Ernie as the checker through `reading_check`; the Piper voice; the NGSL
word list.

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
- [x] 4.3 Reading practice, competency evidence (`step-4.3.md`, built 19 Nov; serves nothing until CP1 texts and Silver questions exist)
- [x] 4.3d part 1 (CP4b first, 23 Nov): a test taken outside the app, pasted, read back, confirmed, marked from the official
      key, wrong answers explained with the trap list (`step-4.3d.md`); part 2 (vocabulary cards, summary across tests) next
- [ ] 4.3d part 2 also: position and pacing (passage 1–3, "đoán"/"không kịp" marks, the pacing line; `step-4.3d.md`)
- [ ] 4.3e skill tags and time per question, four PRs (`step-4.3e.md`): (1) tags in CP4b's generation call, the blind pick, tags
      for pasted tests; (2) per-skill lines in the summaries; (3) time and answer changes in the timed test (`0041`); (4) the
      teacher's 50 labels on the portal
- [ ] 4.3d (CP4b) why the wrong answer tempted you, three PRs (`spec.md`): (1) migration, generation, code checks, planted test,
      run; (2) learner pages and the flag; (3) "Theo dạng câu hỏi" and the Hôm nay link
- [ ] CP4c exam details (timer warnings, highlighting, side by side, one-play Listening), when the owner chooses
- [ ] 4.4 Listening audio and items
- [ ] 4.5 gate report

**4.1 built (15 Nov 2026):** `specs/listening-reading/step-4.1.md`; `app/texts/` (bank loader tied to verified sources, level
features, CLI). No texts are shipped: the owner adds them once a source is verified.

**4.2a built (15 Nov 2026):** `specs/listening-reading/step-4.2a.md`; `app/reading/items.py` (four question types, checks
against the passage, answer-key grading). 4.2b (generation, blind verification, review queue) waits on the verifier decision.
