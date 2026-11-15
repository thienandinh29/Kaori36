import { describe, expect, it } from "vitest";
import type { HiddenNode, Level, Milestone } from "./types";
import {
  NARROW,
  WIDE,
  band,
  depths,
  knownMissing,
  milestoneShare,
  ringSegments,
  splitName,
  totals,
  trailLayout,
} from "./trail";

const h = (slug: string, p: number): HiddenNode => ({
  slug,
  name_vi: slug,
  p_known: p,
  known: p >= 0.9,
});
const m = (
  slug: string,
  level: Level,
  needs: string[],
  hidden: HiddenNode[] = [h(slug + "-a", 0.2)],
): Milestone => ({
  slug,
  name_vi: slug,
  level,
  status: "unknown",
  needs,
  hidden,
});

// The real course's shape (data/courses/english-ielts.yaml).
const COURSE: Milestone[] = [
  m("present-tenses", "A2", []),
  m("nouns-articles", "A2", []),
  m("past-and-future", "A2", ["present-tenses"]),
  m("comparison", "A2", ["present-tenses"]),
  m("perfect-tenses", "B1", ["past-and-future"]),
  m("conditionals-1-2", "B1", ["past-and-future"]),
  m("passive", "B1", ["past-and-future"]),
  m("narrative-tenses", "B2", ["perfect-tenses"]),
  m("conditional-3", "B2", ["conditionals-1-2", "narrative-tenses"]),
  m("conditionals-mixed", "C1", ["conditional-3"]),
];

describe("bands and numbers", () => {
  it("uses the API's known flag for strong, 0.5 for growing", () => {
    expect(band({ p_known: 0.95, known: true })).toBe("strong");
    expect(band({ p_known: 0.6, known: false })).toBe("growing");
    expect(band({ p_known: 0.49, known: false })).toBe("gap");
  });
  it("counts every hidden node once", () => {
    const t = totals([
      m("a", "A2", [], [h("x", 0.95), h("y", 0.6)]),
      m("b", "B1", [], [h("z", 0.1)]),
    ]);
    expect(t).toEqual({ strong: 1, growing: 1, gap: 1, all: 3 });
  });
  it("keeps known + missing at 100", () => {
    expect(knownMissing(0.295)).toEqual([30, 70]);
    expect(knownMissing(0.705)).toEqual([71, 29]);
    expect(knownMissing(2)).toEqual([100, 0]);
  });
  it("averages a milestone's hidden nodes", () => {
    expect(
      milestoneShare(m("a", "A2", [], [h("x", 0.4), h("y", 0.8)])),
    ).toBeCloseTo(0.6);
    expect(milestoneShare(m("a", "A2", [], []))).toBe(0);
  });
});

describe("trail layout", () => {
  it("finds the depth of each milestone from its needs", () => {
    const d = depths(COURSE);
    expect(d.get("present-tenses")).toBe(0);
    expect(d.get("past-and-future")).toBe(1);
    expect(d.get("conditional-3")).toBe(4);
    expect(d.get("conditionals-mixed")).toBe(5);
  });
  it("survives a cycle and a need outside the course", () => {
    const d = depths([
      m("a", "A2", ["b"]),
      m("b", "A2", ["a"]),
      m("c", "B1", ["nope"]),
    ]);
    expect([...d.values()].every((v) => v >= 0)).toBe(true);
    expect(d.get("c")).toBe(0);
  });
  it("places every milestone inside the canvas, deeper ones higher", () => {
    for (const o of [WIDE, NARROW]) {
      const L = trailLayout(COURSE, o);
      const at = new Map(L.nodes.map((n) => [n.slug, n]));
      L.nodes.forEach((n) => {
        expect(n.x - o.r).toBeGreaterThanOrEqual(0);
        expect(n.x + o.r).toBeLessThanOrEqual(o.width);
        expect(n.y - o.r).toBeGreaterThanOrEqual(0);
        expect(n.y + o.r + o.label).toBeLessThanOrEqual(L.height);
      });
      COURSE.forEach((c) =>
        c.needs.forEach((need) =>
          expect(at.get(c.slug)!.y).toBeLessThan(at.get(need)!.y),
        ),
      );
      expect(L.edges).toHaveLength(
        COURSE.reduce((s, c) => s + c.needs.length, 0),
      );
    }
  });
  it("keeps nodes on a line apart enough for their names", () => {
    for (const o of [WIDE, NARROW]) {
      const L = trailLayout(COURSE, o);
      const byY = new Map<number, number[]>();
      L.nodes.forEach((n) => {
        const k = Math.round(n.y / 40);
        byY.set(k, [...(byY.get(k) ?? []), n.x]);
      });
      byY.forEach((xs) => {
        xs.sort((a, b) => a - b);
        for (let i = 1; i < xs.length; i++)
          expect(xs[i] - xs[i - 1]).toBeGreaterThanOrEqual(2 * o.r + 30);
      });
    }
  });
  it("puts a row one wider than a phone line between the others, raised", () => {
    const L = trailLayout(COURSE, NARROW);
    const at = new Map(L.nodes.map((n) => [n.slug, n]));
    const [a, mid, b] = ["perfect-tenses", "conditionals-1-2", "passive"].map(
      (s) => at.get(s)!,
    );
    const xs = [a.x, mid.x, b.x].sort((p, q) => p - q);
    expect(mid.x === xs[1] || a.x === xs[1] || b.x === xs[1]).toBe(true);
    const ys = [a.y, mid.y, b.y].sort((p, q) => p - q);
    expect(ys[1] - ys[0]).toBeGreaterThanOrEqual(NARROW.stagger - 20);
    // nothing else of that depth sits straight above the raised one
    expect(at.get("narrative-tenses")!.x).not.toBe(xs[1]);
  });
  it("labels each level once, at its lowest line", () => {
    const L = trailLayout(COURSE, WIDE);
    expect(L.levels.map((l) => l.level)).toEqual(["A2", "B1", "B2", "C1"]);
  });
});

describe("rings and names", () => {
  it("splits a ring into one segment per hidden node, filled to p_known", () => {
    const segs = ringSegments([h("a", 0.5), h("b", 0)]);
    expect(segs).toHaveLength(2);
    const [a0, a1] = segs[0].track;
    expect(segs[0].fill![1] - segs[0].fill![0]).toBeCloseTo((a1 - a0) / 2);
    expect(segs[1].fill).toBeNull();
    expect(segs[0].track[1]).toBeLessThan(segs[1].track[0]);
  });
  it("uses a full circle for a single hidden node", () => {
    const [s] = ringSegments([h("a", 1)]);
    expect(s.track[1] - s.track[0]).toBeCloseTo(2 * Math.PI);
    expect(s.fill![1]).toBeLessThan(2 * Math.PI); // never a zero-length arc
  });
  it("splits long names near the middle", () => {
    expect(splitName("So sánh")).toEqual(["So sánh"]);
    expect(splitName("Câu điều kiện loại 1 và 2")).toEqual([
      "Câu điều kiện",
      "loại 1 và 2",
    ]);
  });
});
