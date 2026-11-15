# Spec: UI v2 in the web app (trail map, skyline, Sena)

The owner chose this design on 2026-11-15 ("chọn A + biểu đồ của B"); prototype and screenshots in
`outputs/design/ui-v2/` (`NodeTrail-UI-v2.html`, `direction-approved.md`). This spec moves it into `apps/web`.

## What the learner gets
1. **One look and feel** for every English page: warm paper, ink text, indigo for "known", tan hatching for "gap"
   (colours sampled from Sena), Baloo 2 headings and Be Vietnam Pro text, both with Vietnamese glyphs.
2. **Sena as a component** drawn from the owner's model sheet, 7 poses (idle, wave, focus, heart, oops, think, sleep),
   with quiet motion that stops under `prefers-reduced-motion`.
3. **Roadmap = the whole course as a graph** (`/lo-trinh`, heading stays "Lộ trình của bạn"):
   - a trail map climbing from the first milestones (bottom) to the last (top), rows by prerequisite depth, edges for
     `needs`; each milestone is a ring split into its hidden nodes: indigo = known part (`p_known`), hatched = missing;
   - Sena stands on the milestone that holds `learn_next`;
   - a **skyline**: one bar per hidden node grouped by milestone, filled to `p_known`, a line at the engine's
     "known" threshold (0.9), and totals: known / growing (0.5–0.9) / gap (< 0.5);
   - choosing a milestone (map, skyline or keyboard) opens its panel: hidden nodes with bars and links to practise,
     the milestone test, what it needs; side panel on wide screens, bottom sheet on phones.
4. **Feedback with Sena:** after an answer, Sena shows "oops" on a wrong answer and a smile on a right one; "heart"
   only on the run result that says the node is mastered.
5. **Shell:** top bar with Sena's face on wide screens; a bottom tab bar on phones (≥ 44 px targets).

## Rules kept (docs/v2/web-handoff.md)
Strings in `messages/vi.ts` (+ `en.ts`); TypeScript strict; API read through the existing decoders, no API change;
no streaks, timers or speed praise; the level is an estimate; colour never the only signal (hatching, text, numbers);
keyboard reachable with visible focus; e2e texts unchanged ("Lộ trình của bạn", "Luyện ngay", …).

## Out of scope (later PRs)
Restyling the level test, vocabulary and writing pages beyond the shared tokens; the contest explorer (`/kham-pha`).
