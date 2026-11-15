# NodeTrail UI v2: design prototypes (owner chose A + B's chart, 2026-11-15)

Open the HTML files in a browser (they load fonts from Google Fonts; everything else is local).

| File | Direction | Idea |
|---|---|---|
| `A-duong-mon.html` | Đường mòn | The course is a trail climbing from A1 to C1; each milestone is a ring (indigo = known, hatched = gap); Sena stands where you are |
| `B-ban-hoc.html` | Bàn học | A calm study desk: a "skyline" of all 19 sub-skills shows what is strong and what is missing; the graph reads top-down |
| `NodeTrail-UI-v2.html` | **Chosen: A + B's skyline** | Trail map with mastery rings, Sena on the map, and the skyline of 19 sub-skills in the left rail (phone: below the map) |
| `C-mandala.html` | Mandala | The whole course as concentric rings, A2 at the core, C1 at the rim; known parts grow outward from the centre |

- `shared/sena.js`, `shared/sena.css`: Sena rebuilt from the owner's model sheet, 7 poses (idle, wave, focus, heart, oops, think, sleep),
  blink, breathing, tail and wave motion, all off under reduced motion. `shared/sena-sheet.html` shows the poses.
- `shared/course.js`: the real course graph from `data/courses/english-ielts.yaml`; **mastery numbers are illustrative**.
- `directions.md` (spec + six candidates), `polish-log.md`, `design-ledger.md`, `screens/` (1440 and 390 screenshots).

These are design prototypes, not app code. After the owner picks a direction, it is moved into `apps/web` as a design system
(tokens, components, Sena component) one PR at a time, following `docs/v2/web-handoff.md`.
