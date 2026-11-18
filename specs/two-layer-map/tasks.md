# Tasks: two maps and one recommendation engine

Spec: `spec.md` (design only; nothing is built until the owner approves it).

**Owner's decisions, before M1:**
- [ ] Approve or change the design in `spec.md`
- [ ] The target: band per skill (or overall) and the exam date
- [ ] Review the proposed links (which foundations each competency `requires`)
- [ ] Whether calibrated band-model criteria may become evidence (proposed: only after the phase 2 gate)
- [ ] The daily balance (review cap, foundation activities in a row)

**Build (agent), in order:**
- [ ] M1 `data/courses/ielts-competencies.yaml`, its checker, vocabulary band nodes from FSRS
- [ ] M2 `engine/recommend.py`, traces, unit tests, the simulation gate (at least 90% picks the right foundation)
- [ ] M3 `GET /today` and the home page "Hôm nay" on it
- [ ] M4 the two-map page

**Owner's hands-on work:**
- [ ] Follow the daily list for two weeks; note each day whether it was the right thing to do
