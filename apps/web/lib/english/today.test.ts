import { describe, expect, it } from "vitest";
import { DataError } from "@/lib/decode";
import { parseToday } from "./today";

const trace = {
  kind: "next_item",
  concept_slug: "vocab-b2",
  at: "2026-12-01T08:00:00Z",
  prior: 0.1,
  posterior: null,
  evidence: {},
  rule: "recommend.fallback_shared_foundation",
  rule_vi: "Học Từ vựng B2",
  alternatives: [],
};
const body = (href: string) => ({
  activities: [
    {
      kind: "learn_foundation",
      target: "vocab-b2",
      name_vi: "Từ vựng B2",
      via: null,
      href,
      trace,
    },
  ],
  notes: [],
  names: { "vocab-b2": "Từ vựng B2" },
  target: { overall: 7, exam_date: "2027-07-01", links_status: "proposed" },
});

describe("today's list", () => {
  it("decodes the engine's list", () => {
    const t = parseToday(body("/tu-vung"));
    expect(t.activities[0]).toMatchObject({
      kind: "learn_foundation",
      nameVi: "Từ vựng B2",
      href: "/tu-vung",
    });
    expect(t.target).toEqual({
      overall: 7,
      examDate: "2027-07-01",
      linksStatus: "proposed",
    });
  });
  it("refuses links that leave the site", () => {
    expect(() => parseToday(body("https://evil.example"))).toThrow(DataError);
    expect(() => parseToday(body("//evil.example"))).toThrow(DataError);
  });
});
