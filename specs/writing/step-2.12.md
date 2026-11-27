# Step 2.12: a band closer to the examiner's (descriptor caps, a model per criterion)

Owner's request, 27 Nov 2026: "grade the point closer to the reality". **Specified, not built.** No band is shown today
(`data/writing/scorer.yaml`, `calibration: null`), and nothing here changes that until the owner's examiner-banded essays
exist (`dolater.md`, Phase 2). This step adds two things that can then be measured against the pinned scorer
(`step-2.3.md`) on the same splits, and keeps whichever is better.

## Why
- The pinned scorer is a single network trained on labels of unknown provenance (`docs/v2/writing-scorer-candidates.md`).
  It gives one number per criterion with no reason a learner can check, and the current feature baseline (5 features,
  one ridge model for the overall band) does not look at what examiners look at criterion by criterion.
- Examiners mark four criteria from public band descriptors, and the overall band comes from those four. Some descriptor
  lines work as **ceilings**: a response that addresses only part of the task cannot get a high Task Response, however
  good its language. A score that ignores these ceilings can be far off on exactly the essays a learner most needs to hear
  about.
- With 50–100 banded essays, a small model on features chosen from the descriptors is the realistic competitor: fine-tuning
  a transformer on so few essays overfits, and the spec keeps the number away from an LLM.

## 2.12a: descriptor caps
A cap is a rule: *if a finding holds, the criterion's band is at most c*. Caps are pure functions in
`app/writing/caps.py`, unit-tested, each returning the rule that fired and its evidence (a quote or a count) for "Vì sao?".
- **Source of each cap:** the public IELTS Writing Task 2 band descriptors (the current, revised version). Each rule in
  `data/writing/caps.yaml` records the criterion, the cap, and **the descriptor line it comes from, copied from the
  published page**, with the page and the date it was read. The agent drafts the file; the values below are proposals to
  check against that page, not facts.
- **Proposed rules** (status `proposed` in the file until measured):

  | Finding | Comes from | Criterion | Proposed cap | Applied to the band? |
  |---|---|---|---|---|
  | No paragraph breaks (one block of text) | code (blank-line split) | CC | 5.0 | yes, after measurement |
  | A part of the question not answered (`part_missing`, 2.11b) | the model's structure, checked by code | TR | 5.0 | **no**: shown as "có thể bị giới hạn", see the rule below |
  | No position anywhere (`position_missing`) | the model's structure | TR | 4.0 | **no** |
  | Position flips (`position_changed`) | the model's structure | TR | 6.0 | **no** |

- **Not caps, on purpose:** "có thể chưa được phát triển" stays a hint (2.11b); under 250 words is a feature, not a cap
  (the descriptors penalise length in Task Response without one fixed ceiling); low prompt overlap stays "a warning, never
  a judgement" (`guardrails.py`) and is a feature only.
- **The contract decides what may touch the band.** `SPEC.md` says a band never comes from an LLM. 2.11b's findings are
  the model's descriptions checked by code, with no measured precision, so a cap built on them is not applied to the band:
  the result says the band "có thể bị giới hạn ở Task Response" with the finding's quotes. Applying them needs both a
  measured precision for 2.11b (teacher labels or 2.11c's blind check) and the owner's change to `SPEC.md`; neither is
  part of this step.
- **How a cap acts:** on that criterion's predicted band (2.12b) before the overall is formed. With only an overall model,
  a code cap acts as a feature, never as a clip of the overall.
- **A cap is kept only if it helps:** on the development folds, applying it must not raise MAE on the essays where it
  fires. A cap that hurts is reported and switched off, whatever the descriptor says.

## 2.12b: a model per criterion on descriptor features
- **Features** (pure functions, most already measured by 2.1, 2.2 and 2.11b), at most four per criterion, chosen on the
  development folds only:
  - **GRA:** grammar errors per 100 words, by kind (LanguageTool and ERRANT, step 2.2); share of error-free sentences;
    clauses per sentence and the share of complex sentences (already measured).
  - **LR:** lexical diversity (MTLD, length-robust, unlike type–token ratio); share of words beyond the NGSL core list;
    spelling and word-form errors per 100 words; repetition of the prompt's own words.
  - **CC:** paragraph count; variety of linking-word groups and their overuse (per 100 words, `linking-words.yaml`);
    the code caps of 2.12a as yes/no features.
  - **TR:** own words (`guardrails.own_words`); prompt overlap. 2.11b's findings are left out of the served model for the
    same reason as their caps; they may be tried in the evaluation and reported separately.
- **Model:** ridge regression per criterion (the existing pure `fit_ridge`, penalty chosen by cross-validation on the
  development folds), each calibrated to the band scale by isotonic regression, as the overall scorer is. An ordinal
  model is tried only if ridge leaves a visible pattern in the residuals by band.
- **The overall band** is formed from the four predicted criteria with the published rule: "The criteria are weighted
  equally and the score on the task is the average" (ielts.org, IELTS scoring in detail, read 27 Nov 2026). How the
  average of one task is rounded is not stated there (its rounding rule is for the overall test score), so the
  unrounded mean goes into the range, as the overall scorer's prediction does. It is compared with
  predicting the overall band directly.
- **Range:** as in step 2.3: the 10th–90th percentiles of cross-validated residuals, wider than 1.5 bands shown as "không
  chắc". The test report adds the share of test essays whose examiner band falls inside its range (target about 80%).

## What is compared, on the same splits (`app.evalkit.writing_score`)
1. The constant baseline. 2. The current feature baseline (5 features, overall). 3. The pinned scorer, calibrated.
4. 2.12b, overall from criteria, with the code caps. 5. The mean of 3 and 4.
Choice on the development folds only; the 30% test split is opened once, at the end, as in step 2.3. **The simpler model
wins when the QWK intervals overlap**: if 2.12b is as good as the network, no PyTorch service is needed to show a band.
The owner chooses; the choice and the numbers go into `scorer.yaml` (a new `method:` key; per-criterion calibration) and
`evals/writing/score-report.json`.

## Data it needs (the owner's, `data/private/writing/essays.jsonl`)
- One line per essay: `id`, `question`, `text`, `band`, and **optional** `tr`, `cc`, `lr`, `gra` (examiner bands per
  criterion), `marked_by` (`examiner` or `trained_rater`), `source`. `load_essays` reads the new fields; an essay without
  criterion bands counts for the overall comparison only. Bands from a website's own marking are not examiner bands and
  are refused unless `marked_by` says who marked them.
- **Per-criterion models need criterion bands on at least 40 essays**; below that the report says so and 2.12b is
  compared on the overall band only.

## Measured, and not claimed
- **Measured:** QWK with a bootstrap 95% interval, MAE, share within 0.5 band, overall and per criterion; range coverage on
  the test split; for each cap, how often it fired and MAE with and without it on those essays; length bias as in step 2.3.
- **Not claimed:** that the band matches an examiner for Vietnamese learners in general. The essays will be few, and
  published sample answers lean towards the bands chosen to illustrate a book (often 5.5–8); a learner below that range
  gets a wide range or "không chắc", and the report shows the band distribution of the set.
- **Learner-facing change:** none until a method meets the gate (`spec.md` point 13 and 8b). Then the result page shows
  the range and, under "Vì sao?", any cap that fired with its descriptor line and evidence. No migration is expected;
  if the stored result needs criterion bands, one is added at build time.

## Build note, part 1 (27 Nov 2026): caps and features
- **The descriptors were read** from the official PDF (`https://ielts.org/cdn/ielts-guides/ielts-writing-band-descriptors.pdf`,
  "Writing Task 2 Band Descriptors", updated May 2023, SHA-256 `e3c88943…68d1b`), after the owner's environment allowed
  ielts.org; the PDF is not committed (copyright), only its address, hash and the quoted lines. Its own rule for caps:
  "A script must fully fit the positive features of the descriptor at a particular level. Bolded text indicates negative
  features that will limit a rating." Which lines are bold was not checked (text extraction drops the font).
- **What changed from the proposal above, after reading:**
  - *Two paragraphs* is dropped: no line says how many paragraphs a band needs. Band 5 says "Paragraphing may be
    inadequate or missing", band 6 "Paragraphing may not always be logical"; only *no paragraphing* is a clear line.
  - *No position* caps at **4**, not 5: band 5 needs "The writer expresses a position", band 4 "A position is
    discernible, but the reader has to read carefully to find it". A position found only in the body fits band 4 at best.
  - *Part missing* stays at 5 (band 6: "The main parts of the prompt are addressed"; band 5: "…incompletely
    addressed"); *position flips* stays at 6 (band 7: "A clear and developed position is presented"; band 6: "the
    conclusions drawn may be unclear, unjustified or repetitive").
- **Built:** `data/writing/caps.yaml` (four rules, each with its quoted lines and the agent's reading, all `proposed`,
  none `applied`); `app/writing/caps.py`: the file is checked on load (a model rule can never be applied, a rule is
  applied only once `measured`, each rule quotes the band line it caps at), `fire` with evidence, `apply_caps` (applied
  code rules only, never raises a band), `notes` ("có thể bị giới hạn"), `cap_effect` (MAE with and without the cap where
  it fired, for the evaluation). One block of fewer than 120 words is not called unparagraphed (the length rules apply).
- **Built:** `app/writing/descriptor_features.py`: MTLD (forwards and backwards, none under 50 words), errors per 100
  words by kind (LanguageTool's category, as step 2.9 groups them; the model's suggestions never counted), the share of
  sentences without a grammar or word-choice error, word levels from the NGSL/NAWL form index with unknown words apart
  from advanced ones, prompt words per 100, linking variety, rate and the top linker's share; `CANDIDATES` per
  criterion. Nothing is wired into the app or the evaluation yet; nothing a learner sees changes.
- **Run for real:** the features on a 161-word sample essay written for the check, with the real form index and
  linking words (no LanguageTool in the sandbox, so no error counts): 0.09 s; MTLD 169, 4.4% of known words above B1,
  3% unknown, 6 linking groups; as one block it fires `no_paragraphing` (not applied). Limits seen: hyphenated words are
  split ("non-graduates" counts "non"), and some advanced words are missing from the list ("beneficiaries",
  "considerably", "workforce" count as unknown, not advanced). Whether any feature tracks examiner bands is not known
  until the owner's essays exist.

## Build order (each part runs for real before the next)
1. `caps.yaml` with the descriptor lines read from the published page; `caps.py` and its unit tests. **Built.**
2. The features of 2.12b as pure functions with unit tests (MTLD on known texts, linking overuse, error-free share). **Built.**
3. `writing_score` extended: the new fields, the per-criterion models, the five-way comparison, coverage; tested on
   synthetic essays (the report is then labelled synthetic).
4. Served path behind the calibration: `scoring.py` uses the method in `scorer.yaml`; nothing shows while it is `null`.
5. The owner's run on the real essays (`dolater.md`), then the choice.

Cost: no model calls. Roughly two pull requests (1–2, then 3–4).
