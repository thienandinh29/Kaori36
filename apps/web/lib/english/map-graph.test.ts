import { describe, expect, it } from "vitest";
import type { Maps } from "./maps";
import { buildGraph, layout, weakest } from "./map-graph";

const f = (
  node: string,
  kind: "requires" | "helps",
  p: number | null,
  live = true,
) => ({
  node,
  kind,
  nameVi: node,
  live,
  href: live ? `/x/${node}` : null,
  p,
  evidence: p === null ? 0 : 3,
  status: (p === null
    ? "unmeasured"
    : p >= 0.9
      ? "known"
      : p >= 0.8
        ? "growing"
        : "weak") as "unmeasured" | "weak" | "growing" | "known",
});

const MAPS: Maps = {
  minEvidence: 3,
  target: { overall: 7, examDate: "2027-07-01", linksStatus: "proposed" },
  skills: [
    {
      skill: "reading",
      competencies: [
        {
          slug: "reading-detail",
          nameVi: "Đọc chi tiết",
          available: true,
          p: 0.4,
          evidence: 3,
          status: "weak",
          links: [
            f("vocab-b2", "requires", 0.3),
            f("past-simple", "requires", 0.6),
            f("nawl", "helps", 0.1),
          ],
        },
      ],
    },
    {
      skill: "writing",
      competencies: [
        {
          slug: "writing-task1",
          nameVi: "Viết Task 1",
          available: true,
          p: null,
          evidence: 0,
          status: "unmeasured",
          links: [
            f("past-simple", "requires", 0.6),
            f("hedging", "helps", null, false),
          ],
        },
      ],
    },
  ],
};

describe("the skill map as a graph", () => {
  it("shares a foundation between competencies and keeps link kinds", () => {
    const { nodes, edges } = buildGraph(MAPS);
    expect(nodes.filter((n) => n.id === "past-simple")).toHaveLength(1);
    expect(edges.map((e) => [e.id, e.kind])).toContainEqual([
      "nawl->reading-detail",
      "helps",
    ]);
    expect(edges).toHaveLength(5);
    expect(nodes.find((n) => n.id === "hedging")?.status).toBe("not_live");
  });

  it("marks the weakest required foundation under 0.8, never a 'helps' one", () => {
    expect(weakest(MAPS.skills[0]!.competencies[0]!)?.node).toBe("vocab-b2");
    const { nodes } = buildGraph(MAPS);
    const roots = nodes
      .filter((n) => n.rootCause)
      .map((n) => n.id)
      .sort();
    expect(roots).toEqual(["past-simple", "vocab-b2"]); // nawl is lower but only helps
  });

  it("filters by skill and lays foundations left of competencies", () => {
    const { nodes, edges } = buildGraph(MAPS, "writing");
    expect(nodes.map((n) => n.id).sort()).toEqual([
      "hedging",
      "past-simple",
      "writing-task1",
    ]);
    const pos = layout(nodes, edges);
    expect(pos["past-simple"]!.x).toBeLessThan(pos["writing-task1"]!.x);
  });
});

it("never names an unmeasured foundation the root cause", () => {
  const c = {
    ...MAPS.skills[0]!.competencies[0]!,
    links: [{ ...f("vocab-b2", "requires", 0), status: "unmeasured" as const }],
  };
  expect(weakest(c)).toBeNull();
});
