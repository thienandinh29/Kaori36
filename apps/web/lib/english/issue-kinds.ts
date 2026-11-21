import type { GrammarIssue } from "./types";

/**
 * What kind of error an issue is (step 2.9): a spelling slip is not a grammar error, and the list
 * must not call it one. From LanguageTool's category; the model's suggestions stay apart.
 */
export type IssueKind =
  "grammar" | "word" | "spelling" | "punctuation" | "casing" | "other" | "ai";

export const KIND_ORDER: readonly IssueKind[] = [
  "grammar",
  "word",
  "spelling",
  "punctuation",
  "casing",
  "other",
  "ai",
];

const BY_CATEGORY: Record<string, IssueKind> = {
  GRAMMAR: "grammar",
  CONFUSED_WORDS: "word",
  TYPOS: "spelling",
  PUNCTUATION: "punctuation",
  CASING: "casing",
};

export function issueKind(issue: GrammarIssue): IssueKind {
  if (issue.source === "llm") return "ai";
  return BY_CATEGORY[issue.category] ?? "other";
}

/** The issues grouped by kind, in KIND_ORDER, each group in text order; empty kinds left out. */
export function groupByKind(
  issues: readonly GrammarIssue[],
): { kind: IssueKind; issues: GrammarIssue[] }[] {
  const groups = new Map<IssueKind, GrammarIssue[]>();
  for (const i of [...issues].sort((a, b) => a.start - b.start)) {
    const k = issueKind(i);
    groups.set(k, [...(groups.get(k) ?? []), i]);
  }
  return KIND_ORDER.filter((k) => groups.has(k)).map((kind) => ({
    kind,
    issues: groups.get(kind)!,
  }));
}
