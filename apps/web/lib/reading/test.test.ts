import { describe, expect, it } from "vitest";
import { DataError } from "@/lib/decode";
import type { Question } from "./practice";
import {
  answered,
  clock,
  parseStartedTest,
  parseTestResult,
  remaining,
  submission,
} from "./test";

const tfng: Question = {
  id: "t",
  kind: "tfng",
  skill: "detail",
  statement: "S.",
};
const heads: Question = {
  id: "h",
  kind: "headings",
  skill: "main_idea",
  headings: ["a", "b", "c"],
  paragraphs: [0, 1],
};
const fill: Question = {
  id: "c",
  kind: "completion",
  skill: "detail",
  sentence: "A ___.",
  maxWords: 1,
};

describe("timed Reading tests (step 4.3b)", () => {
  it("decodes a started test and a result, strictly", () => {
    const started = parseStartedTest({
      test_id: "0b7e3c1e-0000-4000-8000-000000000001",
      limit_seconds: 1200,
      started_at: "2026-11-20T09:00:00Z",
      slug: "bees",
      title: "Bees",
      passage: "P.",
      items: [{ id: "t", kind: "tfng", skill: "detail", statement: "S." }],
    });
    expect(started).toMatchObject({
      testId: expect.any(String),
      limitSeconds: 1200,
    });
    const result = parseTestResult({
      correct: 1,
      total: 2,
      answered: 1,
      over_time: false,
      seconds: 754,
      items: [
        {
          id: "t",
          answer: "TRUE",
          correct: true,
          key: "TRUE",
          evidence: ["E."],
          at_seconds: 95,
        },
        {
          id: "h",
          answer: null,
          correct: false,
          key: "1: 2",
          evidence: [],
          at_seconds: null,
        },
      ],
    });
    expect(result.items[1]).toMatchObject({ answer: null, atSeconds: null });
    expect(() =>
      parseTestResult({
        correct: 1,
        total: 1,
        answered: 1,
        over_time: "no",
        seconds: 1,
        items: [],
      }),
    ).toThrow(DataError);
  });
  it("formats the clock and counts down from the local start", () => {
    expect(clock(754)).toBe("12:34");
    expect(clock(5)).toBe("0:05");
    expect(clock(-3)).toBe("0:00");
    expect(remaining(0, 1200, 61_500)).toBe(1139);
    expect(remaining(0, 1200, 2_000_000)).toBe(0);
  });
  it("sends only answered questions; headings need every paragraph", () => {
    expect(answered(heads, { "0": 1 })).toBe(false);
    expect(answered(heads, { "0": 1, "1": 2 })).toBe(true);
    expect(answered(fill, "  ")).toBe(false);
    expect(answered(tfng, undefined)).toBe(false);
    expect(
      submission([tfng, heads, fill], {
        t: { answer: "FALSE", atSeconds: 40 },
        h: { answer: { "0": 1 }, atSeconds: 50 },
        c: { answer: " honey ", atSeconds: 60 },
      }),
    ).toEqual({
      t: { answer: "FALSE", at_seconds: 40 },
      c: { answer: "honey", at_seconds: 60 },
    });
  });
});
