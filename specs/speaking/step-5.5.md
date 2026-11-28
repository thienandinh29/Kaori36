# Step 5.5: opening Speaking to testers (invite links, limits, the tester report)

Spec: `spec.md` ("Limits and privacy", "The phase gate"). Owner's go-ahead: 28 Nov 2026 ("build 5.5"), with four decisions made
the same day: **invite link per tester**; **build it, keep it shut** until the owner's privacy review; **3 mock tests and 20 practice
tries a day**; **a report of counts plus the testers' own numbers**. The phase gate it serves: per-user limits working, and at
least 5 of 10 testers still using it after 2 weeks.

## What changes for a tester
1. The owner makes a tester and an invite link from a command; the link works once, for 7 days.
2. The tester opens `/vao/{token}`, reads what is recorded and kept (the notice of `speaking-v1`) and an optional research
   notice, and presses a button. **The button, not the page load, uses the link**: messengers preview links and would spend it.
3. They are signed in on that browser for 30 days (an HttpOnly cookie; the server keeps only a hash) and can use `/noi/thi` and
   `/noi/luyen` like the owner, within the limits below. Nothing else in the app changes.
4. The owner can switch a tester off at once; their sessions end. Deleting their own sittings keeps working for them.

## Rules
- **Recording stays owner-only until the owner has done the privacy review** (`SPEC.md`, Privacy). The tester system is built and
  tested, but `TESTERS_MAY_RECORD` is off by default: a signed-in tester then sees the owner-only notice. One switch, set by the
  owner.
- **Limits, per tester per Vietnam day** (`app/speaking/limits.yaml`): 3 mock tests started and 20 practice tries started
  (assumptions; the owner is unlimited). A refused start says so and when to come back. Speaking makes no model call, so the limit
  protects the owner's recogniser, not money; the service-wide daily cost cap (`LLM_DAILY_COST_CAP_USD`) will apply to 5.3b's calls.
- **A tester's identity is the session, not the learner id.** A learner id that belongs to a tester is refused without that
  tester's valid session; any other id behaves as before.
- **The research notice is separate and optional.** The report holds a tester's own numbers only if that tester accepted notice
  `research-v1`. **Its wording is a draft for the owner to set**; until the owner approves it the page labels it so.

## The tester report (`python -m app.testers.cli report`)
For the owner, written to git-ignored `data/private/`; never audio, never a transcript, never what a tester said.
- Per tester: label, first and last day active, days active, mock tests started, practice tries started.
- **Retention (the gate):** testers whose first day was at least 14 days ago, and how many were active on or after day 14; the share
  with an exact 95% interval. Fewer than 10 testers: the interval is wide and the report says so.
- **Numbers, consenting testers only:** per week, the answers counted, the median speech rate and the median pauses a minute of
  the answers that count as evidence (strict mock answers and first tries; repeats are practice).
- N-of-1 per tester; no comparison between testers is claimed.

## How it is built
- **Migration 0051 (additive):** `testers` (learner, owner's label, revoked, research notice), `tester_invites` and `tester_sessions`
  (hashes of the tokens only).
- `app/testers/store.py` (create, invite, redeem, session, revoke, consent, counts), `limits.py`, `report.py` (pure), `cli.py`.
- **API:** `POST /testers/redeem`, `GET /testers/me`, `POST /testers/research-consent`, with the session in `X-Tester-Session`.
  The web proxy keeps the session in a cookie and sets it on redeem; the browser never reads it.
- Speaking service: who may record is `owner`, or a signed-in tester while the switch is on; the limits apply to testers only.
- **Web:** `/vao/{token}`, the daily-limit message.

## What is measured
Unit tests: token hashing, one-time use and expiry, session binding and revocation, the switch, the limits and the Vietnam day,
the report (retention and its interval, consent gating, evidence-only numbers). A browser test of joining and of a refused start.
**Not claimed:** that the sign-in is hardened beyond an unguessable one-time link over HTTPS; that the research notice is
sufficient (the owner's wording); anything about the testers' speech.

## Not in this step
Passwords, email, payment, teacher or class views; opening beyond invited testers.

## Tasks
- [x] T1 Migration 0051; `store.py`, `limits.py`; tests
- [x] T2 The Speaking service: who may record, the switch, the limits; the routes; tests
- [x] T3 `report.py` and the CLI; tests
- [x] T4 The proxy (session cookie) and `/vao/{token}`; the limit message; Vitest; Playwright
- [x] T5 Run for real; docs

## Built (28 Nov 2026)
- Migration `0051_testers.sql`; `app/testers/` (`store.py`, `limits.py`, `report.py`, `cli.py`: `add --label`, `invite --tester`,
  `list`, `revoke`, `report`); `app/speaking/limits.yaml`; `app/api/testers.py`; the Speaking service takes the session
  (`X-Tester-Session`) on every route; `TESTERS_MAY_RECORD` (default false, in `docker-compose.yml`); web `/vao/{token}`
  (`components/speaking/tester-join.tsx`), the proxy's HttpOnly cookie `nodetrail_tester`, `lib/speaking/tester.ts`, the
  allowance line on `/noi/thi` and `/noi/luyen`, and the 429 message.
- **Choices made in building:** the invite is spent by a button (POST), not by loading the page; the session cookie is set by the
  web proxy and removed from the JSON body, so the browser's scripts never hold it; a tester can always delete their own
  sittings (with their session); a tester who is revoked loses their sessions at once; the limits count sittings started in the
  Vietnam day (a refused start leaves nothing behind); the report holds numbers only for testers who ticked the optional research
  notice, and never audio, text or words; the research notice's wording is **a draft** and the page says so.
- **Run for real** (API, web proxy, database): a tester made with the CLI, the link redeemed through the proxy (HttpOnly cookie
  set, the session absent from the body, a second use refused), recording refused while the switch is off, then with the switch on
  three mock tests accepted and the fourth refused ("đã thi thử đủ 3 bài"), the same learner id without the cookie refused, and
  the report written. Not run: a tester on a second device or HTTPS (the `Secure` cookie flag is set only on https).
- **Checks:** Python tests for the store, the report and the flow through the routes; Vitest for the decoders and the overview;
  4 Playwright tests of the join page (mocked API) next to the existing Speaking tests.
- **Not measured / not claimed:** that the research notice is sufficient (the owner's wording and the privacy review come first);
  the 3-and-20 limits against real use; retention (no testers yet).
