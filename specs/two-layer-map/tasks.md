# Tasks: two maps and one recommendation engine

Spec: `spec.md`, approved by the owner 18 Nov 2026.

**Owner's decisions (18 Nov 2026):**
- [x] Approve the design in `spec.md`
- [x] The target: **overall band 7.0**. Exam date not given: **assumed July 2027** (SPEC's "summer 2027"), set in
  `data/maps/ielts-competencies.yaml` for the owner to change
- [x] The proposed links: "seem reasonable"; they stay Bronze ("đề xuất") until a teacher checks a sample
- [ ] Whether calibrated band-model criteria may become evidence: not answered; the proposed default holds (only
  after the phase 2 gate)
- [x] The daily balance: reviews at most about a third of the day's list; at most two foundation activities in a row

**Build (agent), in order:**
- [x] M1 `data/maps/ielts-competencies.yaml`, its checker, vocabulary band nodes from FSRS
- [ ] M2 `engine/recommend.py`, traces, unit tests, the simulation gate (at least 90% picks the right foundation)
- [ ] M3 `GET /today` and the home page "Hôm nay" on it
- [ ] M4 the two-map page

**Owner's hands-on work:**
- [ ] Follow the daily list for two weeks; note each day whether it was the right thing to do
