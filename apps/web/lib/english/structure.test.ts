import { describe, expect, it } from "vitest";
import { DataError } from "@/lib/decode";
import { parseEssayResult, parseStructure, parseWritingPrompt } from "./decode";
import {
  answeredText,
  answersText,
  developmentText,
  findingText,
} from "./structure";

const STRUCTURE = {
  parts: [
    { text: "the causes", position: false, answered: true },
    { text: "the solutions", position: false, answered: false },
    { text: "your own opinion", position: true, answered: null },
  ],
  introduction: { stance: "first", quote: "I agree with this view" },
  conclusion: { stance: null, quote: null },
  body: [
    {
      paragraph: 2,
      main_idea: "Cars cause most of the traffic",
      answers: [1],
      development: "none",
    },
  ],
  body_paragraphs: 2,
  dropped: 1,
  findings: [
    {
      kind: "part_missing",
      criterion: "tr",
      level: "hint",
      part: 2,
      paragraph: null,
      quotes: [],
    },
    {
      kind: "undeveloped",
      criterion: "tr",
      level: "hint",
      part: null,
      paragraph: 2,
      quotes: ["Cars cause most of the traffic"],
    },
  ],
  model: "m",
};

describe("structure checks (step 2.11b)", () => {
  it("reads the structure and says each finding in Vietnamese", () => {
    const s = parseStructure(STRUCTURE);
    expect(s.parts[2]).toEqual({
      text: "your own opinion",
      position: true,
      answered: null,
    });
    expect(s.conclusion.stance).toBeNull();
    expect(findingText(s.findings[0], s)).toContain("the solutions");
    expect(findingText(s.findings[1], s)).toContain("Đoạn 2");
    expect(developmentText(null)).toContain("chưa chắc");
    expect(developmentText("example")).toBe("có ví dụ");
    expect(answersText([1, 2])).toBe("trả lời phần 1, 2");
    expect(answersText([])).toContain("chưa gắn");
    expect(answeredText(null)).toBe("chưa chắc");
    expect(answeredText(false)).toContain("chưa thấy");
  });

  it("refuses a broken structure", () => {
    expect(() =>
      parseStructure({ ...STRUCTURE, findings: [{ kind: "made_up" }] }),
    ).toThrow(DataError);
    expect(() =>
      parseStructure({
        ...STRUCTURE,
        parts: [{ text: "x", position: false, answered: "yes" }],
      }),
    ).toThrow(DataError);
  });

  it("is absent before step 2.11b and on Task 1, null with a reason otherwise", () => {
    const base = {
      words: 10,
      sentences: 2,
      paragraphs: 1,
      min_words: 250,
      long_enough: false,
      avg_sentence_words: 5,
      longest_sentence_words: 6,
      linking: {},
      linking_groups_used: 0,
      version: 2,
      grammar: null,
      grammar_unavailable_vi: "x",
    };
    expect(parseEssayResult(base).structure).toBeUndefined();
    const short = parseEssayResult({
      ...base,
      structure: null,
      structure_unavailable_vi: "Cần ít nhất 3 đoạn",
    });
    expect(short.structure).toBeNull();
    expect(short.structureUnavailableVi).toContain("3 đoạn");
    const full = parseEssayResult({ ...base, structure: STRUCTURE });
    expect(full.structure?.dropped).toBe(1);
  });

  it("reads a prompt's parts, and none from before step 2.11b", () => {
    const p = {
      id: "t2-x",
      task: 2,
      type: "opinion",
      level: "B1",
      status: "draft",
      prompt: "Do you agree?",
      figure: null,
    };
    expect(parseWritingPrompt(p).parts).toEqual([]);
    const withParts = parseWritingPrompt({
      ...p,
      parts: [{ text: "how far you agree or disagree", position: true }],
    });
    expect(withParts.parts[0].position).toBe(true);
  });
});
