import { describe, expect, it } from "vitest";
import { fixFirst, patterns, styleFor } from "./priorities";
import type { EssayResult, FeedbackPoint, GrammarIssue } from "./types";

let id = 0;
function issue(
  start: number,
  node: string | null,
  extra: Partial<GrammarIssue> = {},
): GrammarIssue {
  id += 1;
  return {
    id,
    sentence: "They goes to school.",
    sentence_start: start,
    start,
    end: start + 4,
    text: "goes",
    suggestion: "go",
    category: "GRAMMAR",
    errant_type: "R:VERB:SVA",
    node,
    node_vi: node ? `Nút ${node}` : null,
    explain_vi: "Chủ ngữ số nhiều đi với động từ không thêm -s.",
    evidence: false,
    source: "languagetool",
    ...extra,
  };
}
const point = (text: string): FeedbackPoint => ({
  kind: "issue",
  point_vi: text,
  quotes: ["x"],
});
const strength = (text: string): FeedbackPoint => ({
  kind: "strength",
  point_vi: text,
  quotes: ["x"],
});

function result(over: Partial<EssayResult> = {}): EssayResult {
  return {
    words: 260,
    sentences: 12,
    paragraphs: 4,
    min_words: 250,
    long_enough: true,
    avg_sentence_words: 20,
    longest_sentence_words: 30,
    linking: {},
    linking_groups_used: 2,
    task: 2,
    grammar: { issues: [] },
    feedback: {
      criteria: {
        tr: [strength("good position"), point("tr-1"), point("tr-2")],
        cc: [point("cc-1")],
        lr: [point("lr-1"), point("lr-2")],
        gra: [point("gra-1")],
      },
      dropped: 0,
    },
    ...over,
  } as EssayResult;
}

describe("fix first (step 2.6)", () => {
  it("puts task response, then word choice, then cohesion first, and keeps two patterns", () => {
    const issues = [issue(5, "sva"), issue(50, "articles"), issue(80, "sva"), issue(90, "articles"),
      issue(120, "sva"), issue(150, "plural")]; // prettier-ignore
    const out = fixFirst(result({ grammar: { issues } }));
    expect(out.map((p) => (p.kind === "feedback" ? p.point.point_vi : p.kind === "pattern" ? `${p.key}×${p.count}` : p.kind)))
      .toEqual(["tr-1", "lr-1", "cc-1", "sva×3", "articles×2"]); // prettier-ignore
  });

  it("fills the slots with more feedback when there are no repeated errors", () => {
    const out = fixFirst(result({ grammar: { issues: [issue(5, "sva")] } }));
    expect(out).toHaveLength(5);
    expect(out.every((p) => p.kind === "feedback")).toBe(true);
    expect(out.map((p) => p.kind === "feedback" && p.point.point_vi)).toEqual([
      "tr-1", "lr-1", "cc-1", "gra-1", "tr-2",
    ]); // prettier-ignore
  });

  it("gives patterns the room when feedback is missing, never more than five items", () => {
    const issues = ["a", "b", "c", "d", "e", "f"].flatMap((n, k) => [
      issue(k * 10, n),
      issue(k * 10 + 5, n),
    ]);
    const out = fixFirst(result({ feedback: null, grammar: { issues } }));
    expect(out).toHaveLength(5);
    expect(out.every((p) => p.kind === "pattern")).toBe(true);
  });

  it("checks a Task 1 essay's numbers and overview before anything else", () => {
    const out = fixFirst(
      result({
        task: 1,
        task1: { numbers: [{ text: "45%", supported: false }, { text: "10%", supported: true }], features: [], overview: false },
      }),
    ); // prettier-ignore
    expect(out.slice(0, 2)).toEqual([
      { kind: "number", text: "45%" },
      { kind: "overview" },
    ]);
    expect(out).toHaveLength(5);
  });

  it("groups by grammar node, else error type, and never counts AI suggestions", () => {
    const g = patterns([
      issue(10, null, { errant_type: "M:DET" }),
      issue(20, null, { errant_type: "M:DET" }),
      issue(30, "sva", { source: "llm" }),
      issue(40, "sva", { source: "llm" }),
    ]);
    expect(g.map((p) => [p.key, p.count])).toEqual([["M:DET", 2]]);
  });

  it("corrects directly up to B1 and lets B2 and above fix it themselves", () => {
    expect(styleFor(null)).toBe("direct");
    expect(styleFor("B1")).toBe("direct");
    expect(styleFor("B2")).toBe("indirect");
    expect(styleFor("C1")).toBe("indirect");
  });
});
