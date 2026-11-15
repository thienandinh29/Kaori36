# Polish log (draft round, one pass per direction)

## Sena (shared/sena.js)
1. Hair cap sat too high and covered the forehead; the brown fur band under the bangs was missing. Rebuilt head proportions.
2. Hands for focus/oops/heart/think were hidden behind the head. Split arms into a back layer (sleeve) and a front layer (hand).
3. Earphone wires ran across the face outline. Moved them to hang from the earbuds to the collar.

## A · Đường mòn
1. Map scaled to width, so the A2 base of the trail was below the fold. Map now fits the viewport height; labels enlarged to stay ≥ 12 px.
2. Phone: map text rendered ~8 px. Added a narrow layout (own node positions, larger type); map comes right after "Hôm nay".
3. Edges ran through node names; Sena covered a node label; "30% + 71%" rounding. Edges end below the label, Sena moved, gap = 100 − known.
Left open: Sena still touches the "B2 Gần đỉnh" label at 1440 px.

## B · Bàn học
1. Skyline labels clipped ("Câu bị đông"). Added short milestone names to the shared data.
2. Skyline card left a large empty area beside the taller "Hôm nay" card. Chart height 230 → 360 px.
3. An edge that skipped a row ran behind another card. Long edges now run down the free column and enter from the side.

## C · Mandala
1. Selecting a milestone dimmed the rest of the course to 45% and the default view looked washed out. Removed dimming; selection = outline + prerequisite links.
2. B1+ sectors used only 170° so half the disc was empty. Widened to 200°; ring labels moved into the empty lower half.
3. "Hoàn thành" and "Thì kể chuyện" pills overlapped; links passed through Sena. Staggered label angles; links curve outside the core.

# Final: A + B's skyline (`NodeTrail-UI-v2.html`)
Round 1
1. Desktop map left wide empty bands and ~12 px labels. Rows compressed (viewBox 960 → 890) so the map scales up.
2. Sena still touched the "B2 Gần đỉnh" label. Sena moved beside "Hiện tại hoàn thành", level labels re-spaced.
3. Detail summary read "0 vững, 0 đang lên, 2 còn hổng". Only non-zero counts are named now.
Round 2
1. The contour paper stopped at the map's box, so the map looked framed. Contours bleed across the whole column.
2. "Kiểm tra cột mốc" wrapped to two lines. Buttons keep one line and wrap as a row instead.
3. Tablet (900 px): the closed side panel's shadow showed at the right edge. Shadow only when open; closed panel hidden.
Round 3
1. Right/wrong answers differed by colour only. Added "· bạn chọn" and "· đúng" text.
2. Phone sheet: "Đóng" pushed the content down, then overlapped the kicker. Close floats top-right with room kept.
3. Checked by script on 390 px: open the next step, answer wrong (Sena "oops" + explanation), close, open "So sánh"
   (fully known, Sena "heart"); no console errors.
Left open: the map heading sits just below the fold on a 390 × 844 phone (the "Hôm nay" block comes first by design).
