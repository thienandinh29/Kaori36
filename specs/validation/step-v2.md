# Step V2: the reviewer portal (plan and tasks)

Spec: `spec.md` ("The reviewer portal"). Builds on V1 (`step-v1.md`). Outside reviewers label content through a
private link, without an account and without seeing the code, any score, or anyone else's labels.

## Cut for this step (proposed)
- **In:** the portal itself, plus two queues for an English teacher:
  - Reading questions (`reading_item` / `item_ok`);
  - text levels (`text_level` / `cefr_level`).
- **Moved to V2b:**
  - pronunciation, because playing your kept recordings to a reviewer needs its own audio route and a voice-policy
    check;
  - vocabulary, grammar items and essay bands, which are the same pattern with other views.

## What is built
- **Migration `0027_review_portal.sql`** (additive):
  - `reviewer_tokens`: only the SHA-256 of each token is stored, never the token, and it can be revoked;
  - `review_batches`: a named, fixed sample for one role, holding the item ids in a shuffled order, each item's
    stratum, and the population counts (so V3 can weight the strata);
  - `labels.detail` (jsonb): for example, the reviewer's own answer and their reason.
- **Sampling, `app/validation/sampling.py`** (pure, tested). A stratified sample with a seed:
  - every item the checker disagreed on, up to the size;
  - the rest filled at random from the items it agreed on;
  - then shuffled, so the strata are not visible in the order.

  Text levels: every text in the bank.
- **CLI** (`app.validation.cli`), each printing what it made:
  - `issue-token --reviewer ID` shows the link **once**;
  - `revoke-token --reviewer ID`;
  - `make-batch --content reading_item|text_level --size 50 --seed 1 --name …`.
- **API** (`app/services/review_portal.py`, `app/api/review_portal.py`). Every call carries the `X-Reviewer-Token`
  header; a missing, unknown or revoked token gets 401.
  - `GET /review/me`: the reviewer's name and role, and their batches with progress.
  - `GET /review/batches/{id}/next`: the next item this reviewer has not labelled. The view holds only what is
    needed: the passage and the learner's view of the question plus its key; or a text. It never holds the item's
    status, the checker's answer, or other labels.
  - `POST /review/batches/{id}/items/{content_id}`: stores the label with role = the reviewer's role (so it is Gold),
    with `detail`.
    - Reading: `{answer, verdict: right|wrong|unsure, reason?, note?}`; a "wrong" verdict needs a reason.
    - Text level: `{level: A1…C1|unsure, note?}`.
- **The owner's review on `/duyet-doc`** now also writes an `owner_developer` label (Bronze), as the spec says.
- **Web, `/kiem-duyet`:**
  - The link is `/kiem-duyet#<token>`. The fragment never reaches a server or a log. The page moves the token to
    session storage and clears it from the address bar.
  - The proxy forwards the token only on `review/` paths, and only if it has the token's shape.
  - **Reading items take two steps:**
    1. The reviewer answers the question from the passage, without the key.
    2. The key is shown, and they judge: đúng / sai (with a reason) / không chắc.

    This is the same blind check the model does, so the two can be compared.
  - **Text levels:** read the text, then pick A1–C1 or "không chắc".
  - Vietnamese strings are in `vi`, with an `en` copy.

## Tasks
- [x] T1 Migration `0027`.
- [x] T2 `sampling.py` with unit tests.
- [x] T3 Portal service and routes, with database tests:
  - token checks;
  - only the reviewer's role's batches;
  - the next item skips what is done;
  - the view leaks no status or labels;
  - labels are Gold, and are replaced on a second answer.
- [x] T4 CLI `issue-token`, `revoke-token`, `make-batch`.
- [x] T5 `/duyet-doc` decisions write owner labels.
- [x] T6 Web page, proxy rule, i18n; Vitest for the pure helpers; a Playwright test.
- [x] T7 MAP, `dolater.md`, the spec's status.
