# Step 2.7 — Guardrails before any band: padding, memorised templates, the prompt

From the owner's deep research (20 Nov 2026, Bronze; numbers to be checked against the papers): scorers reward length
and fluent boilerplate. In one adversarial study, doubling an essay raised about 80% of essays by at least one point;
memorised openers ("One of the most conspicuous trends of today's world…") are a known way to inflate automated scores
and are common in Vietnamese exam preparation; scorers that never read the prompt over-reward fluent off-topic essays.

## What the code checks (`apps/api/app/writing/guardrails.py`, pure, tested)
1. **Repeated text:** words inside a run of 8 words already seen earlier in the essay; sentences of 5+ words said twice.
2. **Memorised phrases:** word for word, ignoring case and punctuation, from `data/writing/templates.yaml` (26 phrases,
   draft, authored by the agent: a teacher should review the list).
3. **Prompt words:** the share of the prompt's content words (stop words removed, crude stemming) the essay uses. Below
   0.15, with at least 5 content words in the prompt, the essay "may be off topic". A warning only: an essay can
   paraphrase the prompt, so this is never a judgement and never withholds anything.

`own_words` = words − repeated − templated. **Padded** = more than 15% of the words are repeated or templated.

## Effects
- The band (when one is shown) uses `own_words` for the length rule; a padded Task 2 essay gets no band, and the page
  says why ("nhiều đoạn … không phải lời của bạn").
- The result keeps `words` as written and adds `guard` (an additive field of the essay result).
- "Sửa trước" (step 2.6) shows these first: off topic, then padded, else the memorised phrases found.
- The measures show "Từ của bạn" when it differs from the word count.
- Not changed: grammar evidence, feedback, the competency rules (they still read `words`; to revisit when the rules
  are reviewed).

## Thresholds
8 words, 5 words, 15% and 0.15 are a first proposal, not measured on examiner-scored essays (Bronze). They are
deliberately lenient: an ordinary essay with one opener is not padded.

## Checks
`tests/writing/test_guardrails.py` (ordinary essay, doubled essay, short repeated sentence, templates with case and
apostrophes, off-topic and short prompts); `tests/test_writing_service.py` (a doubled essay gets no band through the
worker); Vitest for the priorities; Playwright (a repeated, templated essay: named first, own words shown).
