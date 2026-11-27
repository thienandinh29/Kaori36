# Lessons learned

Mistakes we made and what we do differently now, so the next session (human or agent) does not repeat them. Add an entry in the
same change that fixes the mistake: what happened, why, and the rule we keep now. Newest first within each section. A lesson
that becomes a product rule moves into `SPEC.md` (Contract); one about how we work moves into `AGENTS.md`; leave a one-line
pointer here.

## Data and pipelines
- **Test a parser on real pastes, not only our own format (27 Nov 2026).** The 4.3d key reader was tested only on the format
  we wrote (`1 TRUE 2 C`). On the owner's first real use it read nothing: `1.TRUE`, `1-TRUE`, `Q1:` and `Câu 1:` failed, and a
  header such as "Reading Passage 1, Questions 1–13" started the run at 13, so every answer after it was lost; answers that
  could not be read were taken as all blank. Now headers and prefixes are removed, more separators are read, the longest
  rising run wins, and unreadable answers are refused with a message. **Rule:** a parser of learner pastes is tested on the
  forms real sources print (book keys, typed lists) before it ships, and "read nothing" is an error, never an empty result.
  (`specs/listening-reading/step-4.3d.md`, "Fix")
- **A failed model call is not a judgement (22 Nov 2026).** When the free checker gave no usable reply (quota, provider error,
  unreadable output), new Reading questions were marked `needs_review` with no checker answer, so the owner's queue showed
  never-judged questions as if the checker doubted them (8 by 22 Nov). Now an unusable reply changes nothing: the question stays
  unchecked, is retried next run and is counted as `no_reply`. **Rule:** keep "no answer" apart from "a negative answer" in every
  pipeline. (`specs/listening-reading/step-4.2e.md`, "Fix")
- **Import must merge, not skip (21 Nov 2026).** Import left decided questions entirely alone, so a newer check made elsewhere
  never arrived and the next export wrote the older check back over `main`. Now import brings in only the checker's fields,
  never the owner's decision, and never an older check over a newer one. **Rule:** a sync between two copies decides per field
  who owns it; the owner's review decisions are never overwritten. (`step-4.2d.md`, "Fix")
- **Retries and re-runs must be idempotent (20 Nov 2026).** Analysing the same recording twice counted as two attempts, and a
  lost reply that was retried would count twice too. Now each recording carries a client-made id (`take`), unique per learner,
  word and take (migration 0037). **Rule:** anything that becomes evidence needs an idempotency key; the same idea guards
  pasted Reading tests by a fingerprint of passage and key (migration 0040). (`specs/pronunciation/step-3.7b.md`, "Fix")
- **Free models fail often.** In the 24 Nov batch 15 of 59 checker calls failed; on 25 Nov 6 of 45 questions got no reply.
  **Rule:** batches have a cap and are retried the next day; never plan a deadline on the free tier's throughput.
- **T/F/NG with key NOT GIVEN is the hard case.** Most flagged questions in every batch are NOT GIVEN keys the checker reads as
  TRUE or FALSE, or heading matches with paragraphs swapped. Review these first and carefully; they are where a teacher's
  label matters most.

## Models and truth
- **Code decides what code can decide (23 Nov 2026).** In Reading 4.3d the model only lists the pasted questions; code reads the
  official key and the learner's answers, and the learner confirms the list before marking. **Rule:** a model never grades and
  never reads a key; it explains, cites its source, and code checks the citation.
- **Not measured is said out loud.** The 4.3d build was tested with a scripted model; how often the real model reads a real
  Cambridge paste correctly is unknown until the owner's first tests. **Rule:** every report names what was not measured, and a
  number from simulated or synthetic data is called that.
- **The developer is not the ground truth (18 Nov 2026).** The owner's judgement on correct English is Bronze (learner feedback),
  never a gate's truth. Gates wait for a teacher, a trained rater or an expert dataset, even when that is slow.
- **Research reports are input, not truth (20 Nov 2026).** The owner's deep-research reports cited papers dated 2026–2027 or only
  by arXiv number, and named a different licence for Whisper small.en (MIT) than its model card (Apache-2.0). **Rule:** check
  every figure we act on in the primary source; record what was checked in `dolater.md`.

## How we work
- **Vitest green is not CI green.** A web change that passed Vitest alone failed in CI's Playwright run. **Rule:** for anything
  the learner sees, rebuild the stack and run Playwright before saying it is done; CI does not run Prettier, so run
  `pnpm format:check` yourself. (`AGENTS.md`, "Checks")
- **One plan, or the documents drift (20 Nov 2026).** The target was 7.0 in the owner's settings but 6.5 in an older plan.
  **Rule:** `PLAN.md` is the one plan; other pages point to it instead of copying it. If two documents disagree, say so and fix
  one of them in the same change.
- **Scope creep is the main risk (21 Nov 2026).** The contest's any-subject engine kept pulling work away from English. The owner
  froze it. **Rule:** build only on the English app; if a task seems to need frozen code, stop and ask.
- **Load less context (20 Nov 2026).** Loading `MAP.md` every session cost context for little gain; it is now read on demand.

## Environment (cloud sessions)
- **Wikimedia refuses the sandbox (HTTP 429).** Simple English Wikipedia is fetched on the owner's laptop.
- **The disk fills with Docker's build cache.** Run `docker builder prune -af` before anything else.
- **Docker is not always running.** Start it with `nohup dockerd >/tmp/dockerd.log 2>&1 &`.
- **Model keys are injected by the proxy.** Use `LLM_USE_ENV_PROXY=1` with placeholder keys; never ask for a key in chat.
