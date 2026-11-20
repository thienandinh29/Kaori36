import { describe, expect, it } from "vitest";
import {
  parsePassageList,
  parsePassageResult,
  parsePassageView,
  passageAnswers,
} from "./passages";

const tfng = {
  id: "a-tfng-1",
  kind: "tfng",
  skill: "detail",
  statement: "Bees sleep.",
};
const done = {
  id: "a-mcq-1",
  kind: "mcq",
  skill: "detail",
  stem: "Why?",
  options: ["A", "B"],
};

describe("listening to a passage (step 4.4c)", () => {
  it("refuses a view that carries the passage or a headings question", () => {
    const view = { slug: "a", title: "A", parts: 3, items: [tfng] };
    expect(parsePassageView(view).parts).toBe(3);
    expect(() => parsePassageView({ ...view, passage: "the text" })).toThrow();
    const headings = {
      id: "h",
      kind: "headings",
      skill: "main_idea",
      headings: ["x"],
      paragraphs: [0],
    };
    expect(() => parsePassageView({ ...view, items: [headings] })).toThrow();
  });

  it("decodes the list and checks the result's counts", () => {
    const l = parsePassageList({ available: true, texts: [
      { slug: "a", title: "A", questions: 2, parts: 9, read_before: true },
    ] }); // prettier-ignore
    expect(l.texts[0]!.readBefore).toBe(true);
    const item = {
      id: "a-tfng-1",
      answer: "TRUE",
      correct: true,
      key: "TRUE",
      evidence: ["x"],
    };
    const r = {
      correct: 1,
      total: 1,
      answered: 1,
      items: [item],
      transcript: "Bees.",
    };
    expect(parsePassageResult(r).transcript).toBe("Bees.");
    expect(() => parsePassageResult({ ...r, correct: 2 })).toThrow();
  });

  it("sends answered questions only, trimmed", () => {
    expect(
      passageAnswers([tfng, done] as never, {
        "a-tfng-1": " TRUE ",
        "a-mcq-1": 0,
      }),
    ).toEqual({
      "a-tfng-1": "TRUE",
      "a-mcq-1": 0,
    });
    expect(passageAnswers([tfng] as never, { "a-tfng-1": "  " })).toEqual({});
  });
});
