import { describe, expect, it } from "vitest";
import { DataError } from "@/lib/decode";
import { parseMaps } from "./maps";

const link = (over: Record<string, unknown> = {}) => ({
  node: "articles-basic",
  kind: "requires",
  name_vi: "Mạo từ",
  live: true,
  href: "/on-tap/phan/articles-basic",
  p: 0.2,
  evidence: 0,
  status: "unmeasured",
  ...over,
});
const body = (l = link()) => ({
  skills: [
    {
      skill: "writing",
      competencies: [
        {
          slug: "writing-grammar",
          name_vi: "Viết: ngữ pháp",
          available: true,
          p: 0.42,
          evidence: 3,
          status: "weak",
          links: [l],
        },
      ],
    },
  ],
  known: 0.9,
  root_cause_below: 0.8,
  min_evidence: 3,
  target: { overall: 7, exam_date: "2027-07-01", links_status: "proposed" },
});

describe("the two maps", () => {
  it("decodes competencies with their foundations", () => {
    const m = parseMaps(body());
    const c = m.skills[0].competencies[0];
    expect(c).toMatchObject({
      slug: "writing-grammar",
      p: 0.42,
      status: "weak",
    });
    expect(c.links[0]).toMatchObject({ live: true, status: "unmeasured" });
    expect(m.minEvidence).toBe(3);
  });
  it("accepts a foundation that is not live, without a link", () => {
    const m = parseMaps(body(link({ live: false, href: null, p: null })));
    expect(m.skills[0].competencies[0].links[0].href).toBeNull();
  });
  it("refuses unknown statuses, bad probabilities and off-site links", () => {
    expect(() => parseMaps(body(link({ status: "great" })))).toThrow(DataError);
    expect(() => parseMaps(body(link({ p: 1.5 })))).toThrow(DataError);
    expect(() => parseMaps(body(link({ href: "https://x.example" })))).toThrow(
      DataError,
    );
  });
});
