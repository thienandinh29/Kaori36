// A Reading test taken outside the app (specs/listening-reading/step-4.3d.md), decoded strictly.
import { DataError, record, string } from "@/lib/decode";

/** The notice version the learner accepts; the API refuses any other (app/reading/own_test.py). */
export const OWN_CONSENT = "reading-own-v1";
export const OWN_CONSENT_KEY = "nodetrail_reading_own_consent";
export const MAX_PASSAGE_CHARS = 14000;
export const MAX_QUESTIONS_CHARS = 8000;
export const MAX_KEY_CHARS = 2000;

export type OwnKind = "tfng" | "ynng" | "mcq" | "completion" | "unsupported";
export type OwnStatus =
  "queued" | "parsing" | "parsed" | "marked" | "explaining" | "done" | "failed";

export interface OwnQuestion {
  number: number;
  kind: OwnKind;
  text: string;
  options: string[];
  maxWords: number | null;
  key: string | null;
  answer: string | null; // the learner's, read by code from what they pasted
  problems: string[];
}
export interface Explanation {
  keyQuotes: string[];
  whyKeyVi: string;
  whyWrongVi: string | null;
  wrongQuotes: string[];
}
export interface OwnMark {
  number: number;
  kind: OwnKind;
  answer: string | null;
  answerText: string | null;
  correct: boolean;
  trap: string | null;
  key: string;
  explanation: Explanation | null;
  explanationVi: string | null;
}
export interface OwnResult {
  correct: number;
  total: number;
  answered: number;
  unsupported: number[];
  marks: OwnMark[];
  evidence: number;
  explained: boolean;
}
export interface OwnTest {
  id: string;
  status: OwnStatus;
  passage: string;
  questions: OwnQuestion[];
  result: OwnResult | null;
  failureVi: string | null;
  progressTest: boolean;
}
export interface OwnTestSummary {
  id: string;
  status: OwnStatus;
  submittedAt: string;
  correct: number | null;
  total: number | null;
  opening: string;
}

const STATUSES: readonly OwnStatus[] = [
  "queued",
  "parsing",
  "parsed",
  "marked",
  "explaining",
  "done",
  "failed",
];
const KINDS: readonly OwnKind[] = [
  "tfng",
  "ynng",
  "mcq",
  "completion",
  "unsupported",
];

function list(v: unknown): unknown[] {
  if (!Array.isArray(v)) throw new DataError("contract");
  return v;
}
function int(v: unknown): number {
  if (typeof v !== "number" || !Number.isInteger(v) || v < 0)
    throw new DataError("contract");
  return v;
}
function bool(v: unknown): boolean {
  if (typeof v !== "boolean") throw new DataError("contract");
  return v;
}
function optString(v: unknown): string | null {
  return v === null || v === undefined ? null : string(v);
}
function optInt(v: unknown): number | null {
  return v === null || v === undefined ? null : int(v);
}
function status(v: unknown): OwnStatus {
  if (!STATUSES.includes(v as OwnStatus)) throw new DataError("contract");
  return v as OwnStatus;
}
function kind(v: unknown): OwnKind {
  if (!KINDS.includes(v as OwnKind)) throw new DataError("contract");
  return v as OwnKind;
}

function question(v: unknown): OwnQuestion {
  const r = record(v);
  return {
    number: int(r.number),
    kind: kind(r.kind),
    text: string(r.text),
    options: list(r.options ?? []).map(string),
    maxWords: optInt(r.max_words),
    key: optString(r.key),
    answer: optString(r.answer),
    problems: list(r.problems ?? []).map(string),
  };
}

function explanation(v: unknown): Explanation | null {
  if (v === null || v === undefined) return null;
  const r = record(v);
  return {
    keyQuotes: list(r.key_quotes).map(string),
    whyKeyVi: string(r.why_key_vi),
    whyWrongVi: optString(r.why_wrong_vi),
    wrongQuotes: list(r.wrong_quotes ?? []).map(string),
  };
}

function mark(v: unknown): OwnMark {
  const r = record(v);
  return {
    number: int(r.number),
    kind: kind(r.kind),
    answer: optString(r.answer),
    answerText: optString(r.answer_text),
    correct: bool(r.correct),
    trap: optString(r.trap),
    key: string(r.key),
    explanation: explanation(r.explanation),
    explanationVi: optString(r.explanation_vi),
  };
}

function result(v: unknown): OwnResult | null {
  if (v === null || v === undefined) return null;
  const r = record(v);
  return {
    correct: int(r.correct),
    total: int(r.total),
    answered: int(r.answered),
    unsupported: list(r.unsupported ?? []).map(int),
    marks: list(r.marks).map(mark),
    evidence: int(r.evidence),
    explained: bool(r.explained),
  };
}

export function parseOwnTest(value: unknown): OwnTest {
  const r = record(value);
  return {
    id: string(r.id),
    status: status(r.status),
    passage: string(r.passage),
    questions: list(r.questions).map(question),
    result: result(r.result),
    failureVi: optString(r.failure_vi),
    progressTest: bool(r.progress_test),
  };
}

export function parseOwnTests(value: unknown): OwnTestSummary[] {
  return list(value).map((v) => {
    const r = record(v);
    return {
      id: string(r.id),
      status: status(r.status),
      submittedAt: string(r.submitted_at),
      correct: optInt(r.correct),
      total: optInt(r.total),
      opening: string(r.opening),
    };
  });
}

/** Still being worked on by the server: the page polls until this is false. */
export function pending(s: OwnStatus): boolean {
  return (
    s === "queued" || s === "parsing" || s === "marked" || s === "explaining"
  );
}

/** What the confirm call sends: each kept question as the learner left it. */
export function confirmBody(questions: OwnQuestion[]): unknown[] {
  return questions.map((q) => ({
    number: q.number,
    kind: q.kind,
    text: q.text,
    options: q.options,
    max_words: q.maxWords,
    key: q.key,
  }));
}

/** A question can be confirmed when code found nothing wrong, or it is left out of the score. */
export function confirmable(questions: OwnQuestion[]): boolean {
  return (
    questions.some((q) => q.kind !== "unsupported") &&
    questions.every((q) => q.kind === "unsupported" || q.problems.length === 0)
  );
}

/** The trap's Vietnamese name: T/F/NG pairs and completion traps by code, MCQ from the list. */
export function trapName(
  trap: string | null,
  names: Record<string, string>,
  answerVi: Record<string, string>,
): string | null {
  if (!trap) return null;
  const pair =
    /^(true|false|yes|no|not_given)_for_(true|false|yes|no|not_given)$/.exec(
      trap,
    );
  if (pair)
    return names.pair
      .replace("{chosen}", answerVi[pair[1]] ?? pair[1])
      .replace("{key}", answerVi[pair[2]] ?? pair[2]);
  return names[trap] ?? null;
}

/** The share of correct answers, as the page says it. */
export function score(r: OwnResult): string {
  return `${r.correct}/${r.total}`;
}
