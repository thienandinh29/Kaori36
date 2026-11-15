# Writing evaluation (phase 2 gate)

Where the owner's measurements go. **Only numbers and what they mean: never an essay's text** (essays stay in `data/private/`).
Each section says what is measured, how to run it, what to paste, and the target from `specs/writing/spec.md` point 13 or the step
specs. Fill the tables as you go; a missed target is recorded with its number, never hidden.

## 1. Error → node mapping (step 2.2)
Target: **≥ 90% correct on 100 mapped errors** (accuracy with an exact interval), coverage reported next to it.
```bash
uv run python -m app.writing.export_errors --learner <your-id> --out ../../data/private/writing/errors.csv
# fill `correct_node` by hand (empty = no node fits), then:
uv run python -m app.evalkit.writing_map ../../data/private/writing/errors.csv
```
| Date | Errors checked | Mapped | Accuracy (95%) | Coverage | Missed | Decision |
|---|---|---|---|---|---|---|
| | | | | | | |

When the target is met, `data/writing/error-map.yaml` may change from `draft` to `reviewed` (the owner's decision; it then counts for everyone).

## 2. Band scorer (step 2.3)
Target: **QWK ≥ 0.7 on the held-out 30%** and the robustness check passes. 50–100 essays with examiner bands in
`data/private/writing/essays.jsonl` (`{id, text, band}`), the model at `SCORER_URL`.
```bash
uv run python -m app.evalkit.writing_score develop ../../data/private/writing/essays.jsonl --scorer-url http://localhost:8020 --write-calibration
uv run python -m app.evalkit.writing_score test ../../data/private/writing/essays.jsonl --scorer-url http://localhost:8020   # once
```
| Method | QWK (95%) | MAE | Within 0.5 band | Length correlation |
|---|---|---|---|---|
| Constant (mean band) | | | | |
| Features (ridge) | | | | |
| JacobLinCool model (calibrated) | | | | |

Robustness (small edits move the band by at most 0.5): double spaces ___ / merged paragraphs ___. Gate met: ___.
If the feature baseline wins, serve it and drop the PyTorch service (`docs/v2/writing-scorer-candidates.md`).

## 3. Feedback faithfulness (step 2.4)
Does each feedback point say something true about the essay, shown by its quotes? **20 essays** by the owner, ideally written
by different people or on different prompts; judge blind to which model wrote them if a second model is ever compared.
```bash
uv run python -m app.writing.export_review feedback --learner <your-id> --out ../../data/private/writing/feedback.csv
# fill `supported` with y or n, then:
uv run python -m app.evalkit.writing_review feedback ../../data/private/writing/feedback.csv
```
| Date | Model | Essays | Points rated | Supported (95%) | Weakest criterion | Notes |
|---|---|---|---|---|---|---|
| | | | | | | |

Also from `result.feedback`: share of quotes that were real (`quotes_kept / quotes_checked`), points dropped, `duplicates`.
First live runs (15 Nov, `deepseek-flash`, 1 essay): quotes 18/18 and 17/17 real, but several points unsupported
(see `specs/writing/step-2.4.md`).

## 4. AI corrections (step 2.4)
Is the fix right, and was the sentence really wrong? **50 corrections** marked "gợi ý từ AI".
```bash
uv run python -m app.writing.export_review corrections --learner <your-id> --out ../../data/private/writing/corrections.csv
# fill `correct` with y or n, then:
uv run python -m app.evalkit.writing_review corrections ../../data/private/writing/corrections.csv
```
| Date | Rated | Precision (95%) | Lower bound | By type | Decision (count them or keep as hints) |
|---|---|---|---|---|---|
| | | | | | |

## 5. Cost and latency (steps 2.4, 2.5)
From `llm_calls`, per task, over the first week of use:
```sql
select task, count(*), round(avg(latency_ms)) as avg_ms,
       percentile_cont(0.95) within group (order by latency_ms) as p95_ms,
       round(sum(cost_usd)::numeric, 4) as usd
from llm_calls where learner_id = '<your-id>' group by task;
```
Set `LLM_PRICE_INPUT_PER_MTOK` / `LLM_PRICE_OUTPUT_PER_MTOK` to the real prices first, or the cost column is the deliberately high default.
| Task | Calls | Avg ms | p95 ms | US$ per essay |
|---|---|---|---|---|
| writing_feedback | | | | |
| writing_correct | | | | |
| writing_rewrite | | | | |

## 6. Task 1 checks (step 2.5)
For 10 of your own Task 1 reports: how many "không tìm thấy trong biểu đồ" flags were wrong (a correct number the code did not
support) and how many wrong numbers the code missed.
| Reports | Flags | Wrong flags | Missed wrong numbers | Key features reported not covered but actually covered |
|---|---|---|---|---|
| | | | | |

## 7. Recall of the grammar check (step 2.2)
In 10 of your essays, list the errors LanguageTool missed (it misses many agreement errors in mid-sentence).
| Essays | Errors you found | Found by LanguageTool | Found by the AI corrections | Missed by both |
|---|---|---|---|---|
| | | | | |

## Summary for the decision log
One paragraph in your own words: what the numbers say, what you will fix, and what you will leave.
