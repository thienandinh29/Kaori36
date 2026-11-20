import type {
  Criterion,
  EssayResult,
  FeedbackPoint,
  GrammarIssue,
  Level,
} from "./types";

/** How many items "Sửa trước" shows at most (specs/writing/step-2.6.md). */
export const MAX_ITEMS = 5;
const MAX_FEEDBACK = 3;
const MIN_PATTERNS = 2;
/** Task Response first, then word choice: what Vietnamese learners rank highest (step 2.6). */
export const CRITERION_ORDER: readonly Criterion[] = ["tr", "lr", "cc", "gra"];

export type Priority =
  | { kind: "number"; text: string }
  | { kind: "overview" }
  | { kind: "feedback"; criterion: Criterion; point: FeedbackPoint }
  | { kind: "pattern"; key: string; count: number; issues: GrammarIssue[] };

/** LanguageTool errors grouped by grammar node (else ERRANT type); a group seen twice is a pattern. */
export function patterns(
  issues: readonly GrammarIssue[],
): Extract<Priority, { kind: "pattern" }>[] {
  const groups = new Map<string, GrammarIssue[]>();
  for (const i of [...issues].sort((a, b) => a.start - b.start)) {
    if (i.source !== "languagetool") continue; // AI suggestions are never a pattern
    const key = i.node ?? i.errant_type;
    if (!key) continue;
    groups.set(key, [...(groups.get(key) ?? []), i]);
  }
  return [...groups.entries()]
    .filter(([, g]) => g.length >= 2)
    .map(([key, g]) => ({
      kind: "pattern" as const,
      key,
      count: g.length,
      issues: g,
    }))
    .sort(
      (a, b) => b.count - a.count || a.issues[0]!.start - b.issues[0]!.start,
    );
}

/** The model's "issue" points in criterion order: the first of each criterion, then the rest. */
function feedbackPoints(result: EssayResult): Priority[] {
  const fb = result.feedback;
  if (!fb) return [];
  const per = CRITERION_ORDER.map((c) =>
    fb.criteria[c]
      .filter((p) => p.kind === "issue")
      .map((point) => ({
        kind: "feedback" as const,
        criterion: c,
        point,
      })),
  );
  const firsts = per.flatMap((x) => x.slice(0, 1));
  const rest = per.flatMap((x) => x.slice(1));
  return [...firsts, ...rest];
}

/** "Sửa trước": at most five things to fix first, most important first (step 2.6). */
export function fixFirst(result: EssayResult): Priority[] {
  const out: Priority[] = [];
  if (result.task === 1 && result.task1) {
    for (const n of result.task1.numbers)
      if (!n.supported) out.push({ kind: "number", text: n.text });
    if (!result.task1.overview) out.push({ kind: "overview" });
  }
  const feedback = feedbackPoints(result);
  const found = patterns(result.grammar?.issues ?? []);
  const room = Math.max(MAX_ITEMS - out.length, 0);
  // Feedback first (at most 3), but always room for the two most frequent patterns when there are any.
  let nFeedback = Math.min(feedback.length, MAX_FEEDBACK);
  nFeedback = Math.max(
    0,
    Math.min(nFeedback, room - Math.min(MIN_PATTERNS, found.length)),
  );
  const nPatterns = Math.min(found.length, room - nFeedback);
  // Fewer patterns than slots: more feedback points fill them.
  nFeedback = Math.min(feedback.length, room - nPatterns);
  out.push(...feedback.slice(0, nFeedback), ...found.slice(0, nPatterns));
  return out.slice(0, MAX_ITEMS);
}

export type Style = "direct" | "indirect";

/** Direct corrections up to B1 (or without a level test), the error type only from B2 (step 2.6). */
export function styleFor(level: Level | null | undefined): Style {
  return level === "B2" || level === "C1" ? "indirect" : "direct";
}
