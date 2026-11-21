import { describe, expect, it } from "vitest";
import { groupByKind, issueKind } from "./issue-kinds";
import type { GrammarIssue } from "./types";

function issue(
  start: number,
  category: string,
  source: GrammarIssue["source"] = "languagetool",
): GrammarIssue {
  return {
    id: start,
    sentence: "x",
    sentence_start: 0,
    start,
    end: start + 1,
    text: "x",
    suggestion: null,
    category,
    errant_type: null,
    node: null,
    node_vi: null,
    explain_vi: null,
    evidence: false,
    source,
  };
}

describe("issue kinds (step 2.9)", () => {
  it("never calls a spelling slip a grammar error", () => {
    expect(issueKind(issue(0, "TYPOS"))).toBe("spelling");
    expect(issueKind(issue(0, "GRAMMAR"))).toBe("grammar");
    expect(issueKind(issue(0, "PUNCTUATION"))).toBe("punctuation");
    expect(issueKind(issue(0, "CONFUSED_WORDS"))).toBe("word");
    expect(issueKind(issue(0, "CASING"))).toBe("casing");
    expect(issueKind(issue(0, "STYLE"))).toBe("other");
    expect(issueKind(issue(0, "AI", "llm"))).toBe("ai");
  });

  it("groups in a fixed order, each group in text order, empty kinds left out", () => {
    const groups = groupByKind([
      issue(30, "TYPOS"),
      issue(5, "TYPOS"),
      issue(12, "AI", "llm"),
      issue(20, "GRAMMAR"),
    ]);
    expect(groups.map((g) => g.kind)).toEqual(["grammar", "spelling", "ai"]);
    expect(groups[1]!.issues.map((i) => i.start)).toEqual([5, 30]);
  });

  it("eight spelling errors are eight spelling errors", () => {
    const groups = groupByKind(
      Array.from({ length: 8 }, (_, n) => issue(n, "TYPOS")),
    );
    expect(groups).toHaveLength(1);
    expect(groups[0]!.kind).toBe("spelling");
    expect(groups[0]!.issues).toHaveLength(8);
  });
});
