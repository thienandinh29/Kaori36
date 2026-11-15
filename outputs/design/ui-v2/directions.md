# NodeTrail UI v2: spec and directions

## Shared spec (what every direction says, not how it looks)
- **Who:** Vietnamese self-learners (first: the owner, IELTS 6.5 by summer 2027). Phone first, laptop second, tablet in between.
- **Main message:** the whole course is one knowledge graph; you see at a glance what you have nailed and what is still a gap, and the
  engine tells you the one next step and why.
- **Feeling:** warm, light, a study companion; calm enough to focus; never gamified (no streaks, timers, speed rewards).
- **Content (same in all three):** the real English course graph (`data/courses/english-ielts.yaml`: 10 milestones, 19 hidden nodes,
  A1–C1, real prerequisite edges); mastery values are illustrative and labelled so; today's next step with its "Vì sao?" reason;
  6 reviews due; level estimate "B1 (ước lượng)"; one quiz question with Sena reacting.
- **Mastery bands:** Vững ≥ 85%, Đang lên 50–84%, Còn hổng < 50%. Colour is never the only signal: hatching + text.
- **Sena:** rebuilt from the owner's model sheet (`shared/sena.js`), 7 poses. Praise ("heart") only for real mastery; a right answer
  gets a smile and the number moving, not a heart.
- **Format:** one responsive HTML per direction, checked at 1440 and 390.
- **Colour reasoning (all three):** sampled from the mascot sheet: fur brown #886244, skin #EAD6C2, hair #231D1A, sweater cream
  #F1EDE9, knit tan #C7A27E, tablet indigo #4339CA. Indigo (the only cool colour on Sena) carries "known"; the warm browns carry
  the page, so the product and its mascot read as one family.

## Six candidates
| # | Logic and source | Borrowed rules | Lead material | Skeleton | One bold thing | Form from content |
|---|---|---|---|---|---|---|
| 1 | Roulette: App #6 "Topo Outdoor" (second 05) | contour lines, a walked trail, altitude = progress | the graph drawn as a trail climbing CEFR "altitudes" | map full-bleed; bottom sheet for a node | Sena stands on the map at the node you study now | NodeTrail is a trail; prerequisites go uphill |
| 2 | Designer: Otl Aicher | strict grid, one colour per level band, pictogram clarity | small-multiple bars per hidden node ("skyline") | 3-column study desk: today / graph / mastery | a skyline of 19 bars where gaps are hatched holes | mastery is part-of-whole per milestone |
| 3 | Designer: Kohei Sugiura | information mandala, rings, everything around a centre | radial graph: levels as rings, Sena at the centre | one big circular map + side rail | the course as a mandala, filled arcs = known | A1 is the core; you grow outward |
| 4 | Reference: Duolingo learning path (2022) | one winding column, chunky round nodes | path nodes | single scrolling column | — | rejected: hides the graph's branching, which is the point |
| 5 | Reference: Apple Fitness rings | concentric progress rings | three rings per milestone | card grid of rings | — | merged into #1 (rings on map nodes) |
| 6 | Roulette: East Asia #6 "Hong Kong street signs" | dense stacked signage | — | — | — | rejected: noise works against focus |

Built in full: **A = #1 Đường mòn**, **B = #2 Bàn học**, **C = #3 Mandala**. Only A uses a strong metaphor (one allowed).
Test for A: remove the trail, is it clearer? Partly: so the trail stays a background (contours), nodes and edges stay a plain DAG.
