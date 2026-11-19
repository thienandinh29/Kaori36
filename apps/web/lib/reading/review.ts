// The owner's review queue for Reading questions (specs/listening-reading/step-4.2c.md), decoded strictly.
import { DataError, record, string } from "@/lib/decode";

export type ReviewStatus =
  "needs_review" | "verified" | "approved" | "rejected";
export const REVIEW_STATUSES: readonly ReviewStatus[] = [
  "needs_review",
  "verified",
  "approved",
  "rejected",
];
export type RejectReason =
  "wrong_key" | "not_answerable" | "two_answers" | "unclear" | "other";
export const REJECT_REASONS: readonly RejectReason[] = [
  "wrong_key",
  "not_answerable",
  "two_answers",
  "unclear",
  "other",
];

export interface ReviewItem {
  id: string;
  text: string;
  kind: string;
  skill: string;
  /** The learner's view of the question (no key). */
  question: Record<string, unknown>;
  /** The key as stored: "true", an option index, accepted answers, or paragraph -> heading. */
  key: unknown;
  evidence: string[];
  checkerAnswer: string | null;
  checkerModel: string | null;
  note: string | null;
  /** null when the text is missing or changed: approval is then refused. */
  passage: string | null;
}
export interface ReviewQueue {
  counts: Record<ReviewStatus, number>;
  items: ReviewItem[];
}

function optional(value: unknown): string | null {
  return value === null || value === undefined ? null : string(value);
}
function list(value: unknown): unknown[] {
  if (!Array.isArray(value)) throw new DataError("contract");
  return value;
}

export function parseQueue(value: unknown): ReviewQueue {
  const d = record(value);
  const c = record(d.counts);
  const counts = Object.fromEntries(
    REVIEW_STATUSES.map((s) => {
      const n = c[s];
      if (typeof n !== "number") throw new DataError("contract");
      return [s, n];
    }),
  ) as Record<ReviewStatus, number>;
  return {
    counts,
    items: list(d.items).map((v) => {
      const r = record(v);
      return {
        id: string(r.id),
        text: string(r.text),
        kind: string(r.kind),
        skill: string(r.skill),
        question: record(r.question),
        key: r.key,
        evidence: list(r.evidence).map(string),
        checkerAnswer: optional(r.checker_answer),
        checkerModel: optional(r.checker_model),
        note: optional(r.note),
        passage: optional(r.passage),
      };
    }),
  };
}

export type Segment = { text: string; evidence: boolean };

/** The passage split so that every evidence sentence found in it is marked (whitespace-tolerant). */
export function highlight(
  passage: string,
  evidence: readonly string[],
): Segment[] {
  const marks: [number, number][] = [];
  for (const quote of evidence) {
    const words = quote.trim().split(/\s+/).filter(Boolean);
    if (words.length === 0) continue;
    const pattern = new RegExp(
      words.map((w) => w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("\\s+"),
    );
    const m = pattern.exec(passage);
    if (m) marks.push([m.index, m.index + m[0].length]);
  }
  marks.sort((a, b) => a[0] - b[0]);
  const out: Segment[] = [];
  let at = 0;
  for (const [start, end] of marks) {
    if (start < at) continue; // overlapping quotes: keep the first
    if (start > at)
      out.push({ text: passage.slice(at, start), evidence: false });
    out.push({ text: passage.slice(start, end), evidence: true });
    at = end;
  }
  if (at < passage.length)
    out.push({ text: passage.slice(at), evidence: false });
  return out;
}

/** The key as the owner reads it: TFNG words, an option letter, accepted answers, or paragraph:heading pairs. */
export function keyText(
  item: Pick<ReviewItem, "kind" | "key" | "question">,
): string {
  const k = item.key;
  if (item.kind === "tfng" && typeof k === "string")
    return k === "not_given" ? "NOT GIVEN" : k.toUpperCase();
  if (item.kind === "mcq" && typeof k === "number") {
    const options = item.question.options;
    const text = Array.isArray(options) ? String(options[k] ?? "") : "";
    return `${"ABCD"[k] ?? k}. ${text}`;
  }
  if (Array.isArray(k)) return k.map(String).join(" / ");
  if (k && typeof k === "object")
    return Object.entries(k as Record<string, unknown>)
      .map(([p, h]) => `${p}:${String(h)}`)
      .join(", ");
  return String(k);
}

// --- Review by passage (specs/listening-reading/step-4.2f.md) ---

export interface ReviewText {
  slug: string;
  title: string;
  agreed: number;
  flagged: number;
}
export interface ReviewStats {
  decisions: number;
  medianSeconds: number | null;
  overturned: number;
}
export interface ReviewTexts {
  texts: ReviewText[];
  stats: ReviewStats;
}
export interface PassageItem extends Omit<ReviewItem, "passage"> {
  /** The blind checker agreed with the key. */
  agreed: boolean;
}
export interface PassageReview {
  slug: string;
  title: string;
  passage: string;
  items: PassageItem[];
}

function count(value: unknown): number {
  if (typeof value !== "number" || !Number.isInteger(value) || value < 0)
    throw new DataError("contract");
  return value;
}

export function parseReviewTexts(value: unknown): ReviewTexts {
  const d = record(value);
  const s = record(d.stats);
  const median = s.median_seconds;
  if (median !== null && typeof median !== "number")
    throw new DataError("contract");
  return {
    texts: list(d.texts).map((v) => {
      const r = record(v);
      return {
        slug: string(r.slug),
        title: string(r.title),
        agreed: count(r.agreed),
        flagged: count(r.flagged),
      };
    }),
    stats: {
      decisions: count(s.decisions),
      medianSeconds: median,
      overturned: count(s.overturned),
    },
  };
}

export function parsePassageReview(value: unknown): PassageReview {
  const d = record(value);
  return {
    slug: string(d.slug),
    title: string(d.title),
    passage: string(d.passage),
    items: list(d.items).map((v) => {
      const r = record(v);
      if (typeof r.agreed !== "boolean") throw new DataError("contract");
      const [item] = parseQueue({
        counts: { needs_review: 0, verified: 0, approved: 0, rejected: 0 },
        items: [{ ...r, passage: null }],
      }).items;
      const { passage: _passage, ...rest } = item!;
      void _passage;
      return { ...rest, agreed: r.agreed };
    }),
  };
}

/** What a key press means on the review page (pure, so it is tested without a browser). */
export type ReviewAction =
  | { type: "approve" }
  | { type: "reject" }
  | { type: "reason"; reason: RejectReason }
  | { type: "confirm" }
  | { type: "cancel" }
  | { type: "skip" }
  | { type: "back" };

export function shortcut(key: string, rejecting: boolean): ReviewAction | null {
  if (rejecting) {
    const n = Number(key);
    if (Number.isInteger(n) && n >= 1 && n <= REJECT_REASONS.length)
      return { type: "reason", reason: REJECT_REASONS[n - 1]! };
    if (key === "Enter") return { type: "confirm" };
    if (key === "Escape") return { type: "cancel" };
    return null;
  }
  switch (key.length === 1 ? key.toLowerCase() : key) {
    case "a":
      return { type: "approve" };
    case "r":
      return { type: "reject" };
    case "s":
    case "ArrowRight":
      return { type: "skip" };
    case "ArrowLeft":
      return { type: "back" };
    default:
      return null;
  }
}
