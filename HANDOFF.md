# HANDOFF — where the work stands

The state of the work for whoever picks it up next. **Update it at the end of every session or merged pull request**: overwrite
the sections below, do not append history (history goes in `PLAN.md`, "Log"). If this page disagrees with `PLAN.md`, `PLAN.md`
wins; fix this page.

**Last updated:** 27 Nov 2026, `main` at `6b6ca8b` (Wiktionary coverage, #147), plus the Reading diagnosis docs (this branch).

## Just finished
- **Reading 4.3d part 2, first half** (27 Nov, this branch, not merged): the passage's place and "đoán"/"không kịp" marks on the
  check step, the summary across pasted tests per question type and the pacing line on `/doc/bai-cua-ban`; migration `0041`.
  Tested with a mocked model and API; thresholds are assumptions until real tests exist.
- **Reading diagnosis specified** (27 Nov, docs only): pacing in 4.3d part 2 (`step-4.3d.md`, "Position and pacing"),
  skill tags and time per question (`step-4.3e.md`), and the research track DIAG-001 (a CDM on public data, after KT-001).
  SPEC's evidence rule gains: a pasted answer marked "không kịp" gives no evidence. From the owner's CDA research (Bronze).
- **Wiktionary coverage** (#147): measured only; the enrichment step is the owner's decision (`dolater.md`, section 5).
- **Reading 4.3d part 1** (#142, 23 Nov): paste a Reading test taken outside the app on `/doc/bai-cua-ban`; the model lists the
  questions, code reads the official key and the learner's answers, the learner confirms, code marks, each wrong answer is
  explained with CP4b's trap list and labelled "chưa kiểm chứng". Owners only; one BKT observation per answered question, once
  per test fingerprint; migration `0040`. Tested with a scripted model only.
- **Writing 2.11b** (#139): Task 2 structure checks (every part answered, position, a hint on undeveloped paragraphs).
- **Daily Reading blind checks** (#137, #141, #143, #144): item files on `main` now hold 251 verified, 14 needs_review,
  2 approved, 6 rejected, 36 dropped and 93 still unchecked questions.

## In progress
Nothing in code. The Reading diagnosis docs wait for review on `claude/compassionate-newton-d4dkru`.

## Next
1. **Owner first: try 4.3d on a real test** (`dolater.md`, section 1, ~40 min): one Cambridge Reading passage under exam
   conditions, pasted with its key and answers. Report how many questions were read wrongly, any wrong trap or explanation,
   and whether the three build choices in `specs/listening-reading/step-4.3d.md` ("Part 1 built") suit you. This is the only
   measure of the real model's parse accuracy.
2. **Agent: 4.3d part 2, second half**: vocabulary cards from the passage (`step-4.3d.md`, "Vocabulary").
   Spec-sized PR. Better after step 1, so part 2 builds on choices the owner has confirmed.
3. Then, in `PLAN.md` order: CP4b on the bank's own questions, with skill tags in the same call (`step-4.3e.md` part 1), CP4c exam details, CP2b planted test, the CP6 report, phase 5
   Speaking. The owner may reorder.

## Waiting on the owner (not on a build)
- **The baseline test on four skills**: the most time-critical item; every week before it is invisible to the progress study.
- ~20 web essays for the Writing feedback stability run (`specs/writing/step-2.11.md`, 2.11a; the 60% bar stays
  "proposed" until the owner has seen the result).
- A teacher (reviewer brief: `specs/validation/reviewer-brief.vi.md`); every phase gate waits on Gold labels.
- Decisions: the Speaking recogniser and consent wording; whether the machine voice is good enough for whole-passage Listening;
  licences (L2-ARCTIC, Simple English Wikipedia). Full list: `dolater.md`.

## Running on its own
The daily Reading blind-check batch (scheduled task, 03:13 UTC, up to 45 questions, US$0.10 cap) exports the item files and
merges its own data PR. It never touches the owner's review decisions.

## Known issues and risks right now
- The free checker fails often (15 of 59 calls on 24 Nov); unanswered questions stay unchecked and are retried.
- 4.3d explanations have no blind check yet (Gemini, after a planted test); keep the "chưa kiểm chứng" label.
- No phase gate is measured yet; all content is still draft until a teacher reviews it.

## Already decided, do not reopen
No Speaking band before the exam; target 7.0 overall; everything outside the English app is frozen (`AGENTS.md`, "English
only"); Cambridge material never enters the shared bank.
