// Listening practice from the Reading bank (specs/listening-reading/step-4.4b.md), decoded strictly.
import type { DecisionTrace } from "@/lib/contracts";
import { DataError, parseTrace, record, string } from "@/lib/decode";

export interface ListeningSummary {
  slug: string;
  title: string;
  dictation: number;
  gaps: number;
}
export interface ListeningTexts {
  /** False when the server voice is off: nothing can be practised. */
  available: boolean;
  texts: ListeningSummary[];
}
export interface ListeningItem {
  id: string;
  kind: "dictation" | "gap";
  /** The gap sentence with its blank; null for dictation (the sentence is only heard). */
  prompt: string | null;
}
export interface ListeningText {
  slug: string;
  title: string;
  items: ListeningItem[];
}
export type WordStatus = "right" | "wrong" | "missed" | "extra";
export interface WordMark {
  word: string;
  status: WordStatus;
}
export interface ListeningResult {
  correct: boolean;
  score: number;
  /** The missing word, or the whole sentence for dictation. */
  key: string;
  sentence: string;
  words: WordMark[];
  competency: string;
  trace: DecisionTrace;
}

/** How many times a sentence may be played before answering, as IELTS plays once. */
export const PLAYS = 3;

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

export function parseListeningTexts(value: unknown): ListeningTexts {
  const r = record(value);
  return {
    available: bool(r.available),
    texts: list(r.texts).map((t) => {
      const x = record(t);
      return {
        slug: string(x.slug),
        title: string(x.title),
        dictation: count(x.dictation),
        gaps: count(x.gaps),
      };
    }),
  };
}

export function parseListeningText(value: unknown): ListeningText {
  const r = record(value);
  return {
    slug: string(r.slug),
    title: string(r.title),
    items: list(r.items).map((i) => {
      const x = record(i);
      if (x.kind !== "dictation" && x.kind !== "gap")
        throw new DataError("contract");
      if (x.kind === "gap" && typeof x.prompt !== "string")
        throw new DataError("contract");
      return {
        id: string(x.id),
        kind: x.kind,
        prompt: x.prompt === null ? null : string(x.prompt),
      };
    }),
  };
}

const STATUSES: readonly WordStatus[] = ["right", "wrong", "missed", "extra"];

export function parseListeningResult(value: unknown): ListeningResult {
  const r = record(value);
  if (typeof r.score !== "number" || r.score < 0 || r.score > 1)
    throw new DataError("contract");
  return {
    correct: bool(r.correct),
    score: r.score,
    key: string(r.key),
    sentence: string(r.sentence),
    words: list(r.words).map((w) => {
      const x = record(w);
      const status = STATUSES.find((s) => s === x.status);
      if (!status) throw new DataError("contract");
      return { word: string(x.word), status };
    }),
    competency: string(r.competency),
    trace: parseTrace(r.trace),
  };
}

/** The share of words right, as a whole percentage. */
export function percent(score: number): number {
  return Math.round(score * 100);
}
