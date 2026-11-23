import { describe, expect, it } from "vitest";
import {
  confirmBody,
  confirmable,
  parseOwnTest,
  pending,
  trapName,
  type OwnQuestion,
} from "./own";
import { vi } from "@/messages/vi";

const t = vi.english.readingOwn;
const q = (over: Partial<OwnQuestion> = {}): OwnQuestion => ({
  number: 1,
  kind: "tfng",
  text: "The Thames was declared dead in 1957.",
  options: [],
  maxWords: null,
  key: "TRUE",
  answer: "FALSE",
  problems: [],
  ...over,
});

describe("a pasted Reading test (step 4.3d)", () => {
  it("decodes the server's view strictly", () => {
    const view = parseOwnTest({
      id: "a",
      status: "done",
      passage: "p",
      progress_test: false,
      failure_vi: null,
      questions: [
        {
          number: 1,
          kind: "mcq",
          text: "Seals are",
          options: ["x", "y"],
          max_words: null,
          key: "B",
          answer: null,
          problems: [],
        },
      ],
      result: {
        correct: 0,
        total: 1,
        answered: 0,
        unsupported: [],
        evidence: 0,
        explained: true,
        marks: [
          {
            number: 1,
            kind: "mcq",
            answer: null,
            answer_text: null,
            correct: false,
            trap: null,
            key: "B. y",
            explanation: {
              key_quotes: ["seals are often seen"],
              why_key_vi: "Vì bài nói vậy.",
              why_wrong_vi: null,
              wrong_quotes: [],
            },
            explanation_vi: null,
          },
        ],
      },
    });
    expect(view.questions[0].answer).toBeNull();
    expect(view.result?.marks[0].explanation?.keyQuotes).toEqual([
      "seals are often seen",
    ]);
    expect(() => parseOwnTest({ id: "a", status: "lost" })).toThrow();
  });

  it("polls only while the server works", () => {
    expect(pending("parsing")).toBe(true);
    expect(pending("marked")).toBe(true);
    expect(pending("parsed")).toBe(false);
    expect(pending("done")).toBe(false);
  });

  it("confirms only a list with something to mark and no open problem", () => {
    expect(confirmable([q()])).toBe(true);
    expect(confirmable([q({ problems: ["x"] })])).toBe(false);
    expect(confirmable([q({ kind: "unsupported", problems: ["x"] })])).toBe(
      false,
    );
    expect(
      confirmable([q(), q({ number: 2, kind: "unsupported", problems: [] })]),
    ).toBe(true);
    expect(confirmBody([q({ maxWords: 2 })])).toEqual([
      {
        number: 1,
        kind: "tfng",
        text: q().text,
        options: [],
        max_words: 2,
        key: "TRUE",
      },
    ]);
  });

  it("names the trap in Vietnamese", () => {
    expect(trapName("false_for_not_given", t.traps, t.answerNames)).toBe(
      "Nhầm SAI với KHÔNG CÓ THÔNG TIN",
    );
    expect(trapName("word_match", t.traps, t.answerNames)).toBe(
      "Lặp từ trong bài nhưng sai nghĩa",
    );
    expect(trapName(null, t.traps, t.answerNames)).toBeNull();
    expect(trapName("made_up", t.traps, t.answerNames)).toBeNull();
  });
});
