# Plan: UI v2 in the web app

- **Tokens and fonts:** `app/theme.css` (CSS variables, light only), fonts via `next/font/google` (`Baloo_2`,
  `Be_Vietnam_Pro`, subsets latin + vietnamese, self-hosted at build; no new npm package). `english.css` moves onto the
  tokens.
- **Sena:** `components/sena/sena.tsx` renders the SVG from typed pose parts (port of `outputs/design/ui-v2/shared/sena.js`);
  motion in `components/sena/sena.css`.
- **Pure layout:** `lib/english/trail.ts`: depth by `needs`, rows (split when too many for the width), barycentre
  ordering, positions, edge paths, level labels, ring arcs, bands and totals. Unit tests in `trail.test.ts`.
- **Roadmap:** `components/english/trail-map.tsx` (SVG), `skyline.tsx`, `milestone-panel.tsx`; `roadmap-view.tsx`
  composes them with the existing "Vì sao?" `TraceNote`.
- **Shell and feedback:** new header and phone tab bar in `shell.tsx`; Sena in `home.tsx` and `feedback.tsx`.
- **Checks:** lint, typecheck, Vitest, Prettier; screenshots of `/lo-trinh` at 1440 and 390 against a stack when one
  is available (none in the cloud session: the map is checked with the prototype data in a Vitest layout test).
