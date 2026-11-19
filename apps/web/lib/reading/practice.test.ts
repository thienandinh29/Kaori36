import { describe, expect, it } from "vitest";
import { DataError } from "@/lib/decode";
import { paragraphsOf, parseAnswer, parseText, parseTexts } from "./practice";

const trace = {
  kind: "bkt_update",
  concept_slug: "reading-detail",
  at: "2026-12-01T09:00:00Z",
  prior: 0.2,
  posterior: 0.5,
  evidence: {},
  rule: "reading.answer",
  rule_vi: "Đọc: trả lời đúng",
  alternatives: [],
};

describe("reading practice decoding", () => {
  it("decodes texts, questions of every kind and answers", () => {
    expect(
      parseTexts({
        texts: [{ slug: "bees", title: "Bees", questions: 3, words: 48 }],
      }),
    ).toEqual([{ slug: "bees", title: "Bees", questions: 3, words: 48 }]);
    const text = parseText({
      slug: "bees",
      title: "Bees",
      passage: "A.\n\nB.",
      items: [
        { id: "t", kind: "tfng", skill: "detail", statement: "A colony." },
        {
          id: "m",
          kind: "mcq",
          skill: "detail",
          stem: "What?",
          options: ["a", "b", "c"],
        },
        {
          id: "c",
          kind: "completion",
          skill: "detail",
          sentence: "A ___.",
          max_words: 1,
        },
        {
          id: "h",
          kind: "headings",
          skill: "main_idea",
          headings: ["x", "y", "z"],
          paragraphs: [0, 1],
        },
      ],
    });
    expect(text.items.map((i) => i.kind)).toEqual([
      "tfng",
      "mcq",
      "completion",
      "headings",
    ]);
    expect(
      parseAnswer({
        correct: false,
        score: 0.5,
        key: "TRUE",
        evidence: ["A."],
        competency: "reading-detail",
        trace,
      }),
    ).toMatchObject({ correct: false, key: "TRUE" });
  });
  it("refuses unknown kinds and leaked shapes", () => {
    expect(() =>
      parseText({
        slug: "b",
        title: "B",
        passage: "x",
        items: [{ id: "q", kind: "essay", skill: "d" }],
      }),
    ).toThrow(DataError);
    expect(() =>
      parseAnswer({
        correct: "yes",
        score: 1,
        key: "x",
        evidence: [],
        competency: "c",
        trace,
      }),
    ).toThrow(DataError);
  });
  it("numbers paragraphs as the headings questions do", () => {
    expect(paragraphsOf("One.\n\n  Two.\n \nThree.")).toEqual([
      "One.",
      "Two.",
      "Three.",
    ]);
  });
});
