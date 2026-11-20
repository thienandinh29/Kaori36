// Listening to a Reading passage, then its approved questions (specs/listening-reading/step-4.4c.md).
import { DataError, record, string } from "@/lib/decode";
import { question, type Answer, type Question } from "@/lib/reading/practice";

/** How many times the whole passage may be played: IELTS plays once, practice allows twice. */
export const PASSAGE_PLAYS = 2;

export interface PassageSummary {
  slug: string;
  title: string;
  questions: number;
  parts: number;
  /** the learner answered its Reading questions: listening may be easier */
  readBefore: boolean;
}
export interface PassageList {
  available: boolean;
  texts: PassageSummary[];
}
/** What the page gets before answering: never the passage itself. */
export interface PassageView {
  slug: string;
  title: string;
  parts: number;
  items: Question[];
}
export interface PassageResultItem {
  id: string;
  answer: unknown;
  correct: boolean;
  key: string;
  evidence: string[];
}
export interface PassageResult {
  correct: number;
  total: number;
  answered: number;
  items: PassageResultItem[];
  transcript: string;
}

function list(v: unknown): unknown[] {
  if (!Array.isArray(v)) throw new DataError("contract");
  return v;
}
function count(v: unknown): number {
  if (typeof v !== "number" || !Number.isInteger(v) || v < 0)
    throw new DataError("contract");
  return v;
}
function bool(v: unknown): boolean {
  if (typeof v !== "boolean") throw new DataError("contract");
  return v;
}

export function parsePassageList(value: unknown): PassageList {
  const r = record(value);
  return {
    available: bool(r.available),
    texts: list(r.texts).map((x) => {
      const t = record(x);
      return {
        slug: string(t.slug),
        title: string(t.title),
        questions: count(t.questions),
        parts: count(t.parts),
        readBefore: bool(t.read_before),
      };
    }),
  };
}

export function parsePassageView(value: unknown): PassageView {
  const r = record(value);
  if ("passage" in r) throw new DataError("contract"); // the text must not arrive before answering
  const items = list(r.items).map(question);
  if (items.some((q) => q.kind === "headings")) throw new DataError("contract");
  return {
    slug: string(r.slug),
    title: string(r.title),
    parts: count(r.parts),
    items,
  };
}

export function parsePassageResult(value: unknown): PassageResult {
  const r = record(value);
  const items = list(r.items).map((x) => {
    const i = record(x);
    return {
      id: string(i.id),
      answer: i.answer ?? null,
      correct: bool(i.correct),
      key: string(i.key),
      evidence: list(i.evidence).map(string),
    };
  });
  const out = {
    correct: count(r.correct),
    total: count(r.total),
    answered: count(r.answered),
    items,
    transcript: string(r.transcript),
  };
  if (
    out.correct > out.answered ||
    out.answered > out.total ||
    items.length !== out.total
  )
    throw new DataError("contract");
  return out;
}

/** The submission body: answered questions only (a blank gives no evidence). */
export function passageAnswers(
  items: Question[],
  given: Record<string, Answer>,
): Record<string, Answer> {
  const out: Record<string, Answer> = {};
  for (const q of items) {
    const a = given[q.id];
    if (a === undefined) continue;
    if (typeof a === "string") {
      if (a.trim()) out[q.id] = a.trim();
    } else out[q.id] = a;
  }
  return out;
}
