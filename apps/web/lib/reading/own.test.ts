import { describe, expect, it } from "vitest";
import {
  confirmBody,
  confirmable,
  parseOwnSummary,
  parseOwnTest,
  pending,
  shareText,
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
  mark: null,
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
          mark: "no_time",
        },
      ],
      result: {
        correct: 0,
        total: 1,
        answered: 0,
        unsupported: [],
        evidence: 0,
        explained: true,
        position: 3,
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
            self_mark: "no_time",
          },
        ],
      },
    });
    expect(view.questions[0].answer).toBeNull();
    expect(view.questions[0].mark).toBe("no_time");
    expect(view.result?.position).toBe(3);
    expect(view.result?.marks[0].selfMark).toBe("no_time");
    expect(() =>
      parseOwnTest({
        id: "a",
        status: "parsed",
        passage: "p",
        progress_test: false,
        questions: [{ number: 1, kind: "tfng", text: "x", mark: "lazy" }],
        result: null,
      }),
    ).toThrow();
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
    expect(confirmBody([q({ maxWords: 2, mark: "guessed" })])).toEqual([
      {
        number: 1,
        kind: "tfng",
        text: q().text,
        options: [],
        max_words: 2,
        key: "TRUE",
        mark: "guessed",
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

  it("decodes the summary across tests and says a share with its interval", () => {
    const s = parseOwnSummary({
      tests: 3,
      answers: 30,
      by_kind: [
        {
          kind: "tfng",
          answers: 10,
          wrong: 3,
          enough: true,
          right: { k: 7, n: 10, low: 0.348, high: 0.933 },
          top_trap: { trap: "false_for_not_given", count: 2, of: 3 },
        },
      ],
      pacing: {
        status: "maybe_time",
        tests: 3,
        late: { wrong: 6, n: 12 },
        rest: { wrong: 3, n: 18 },
        late_wrong_marked: 4,
      },
      thresholds: {},
    });
    expect(s.byKind[0].topTrap?.count).toBe(2);
    expect(s.pacing.lateWrongMarked).toBe(4);
    expect(shareText(s.byKind[0].right)).toBe("7/10 (35–93%)");
    expect(shareText({ k: 0, n: 0, low: null, high: null })).toBe("0/0");
    expect(() =>
      parseOwnSummary({
        tests: 0,
        answers: 0,
        by_kind: [],
        pacing: { status: "sure" },
      }),
    ).toThrow();
  });
});
