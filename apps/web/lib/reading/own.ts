// A Reading test taken outside the app (specs/listening-reading/step-4.3d.md), decoded strictly.
import { DataError, record, string } from "@/lib/decode";

/** The notice version the learner accepts; the API refuses any other (app/reading/own_test.py). */
export const OWN_CONSENT = "reading-own-v1";
export const OWN_CONSENT_KEY = "nodetrail_reading_own_consent";
export const MAX_PASSAGE_CHARS = 14000;
export const MAX_QUESTIONS_CHARS = 8000;
export const MAX_KEY_CHARS = 2000;

export type OwnKind = "tfng" | "ynng" | "mcq" | "completion" | "unsupported";
/** The learner's own mark on an answer: "đoán" (guessed) or "không kịp" (ran out of time). */
export type SelfMark = "guessed" | "no_time";
export const SELF_MARKS: readonly SelfMark[] = ["guessed", "no_time"];
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
  mark: SelfMark | null;
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
  selfMark: SelfMark | null;
}
export interface OwnResult {
  correct: number;
  total: number;
  answered: number;
  unsupported: number[];
  marks: OwnMark[];
  evidence: number;
  explained: boolean;
  position: number | null;
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
function selfMark(v: unknown): SelfMark | null {
  if (v === null || v === undefined) return null;
  if (!SELF_MARKS.includes(v as SelfMark)) throw new DataError("contract");
  return v as SelfMark;
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
    mark: selfMark(r.mark),
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
    selfMark: selfMark(r.self_mark),
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
    position: optInt(r.position),
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
    mark: q.mark,
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

// --- The summary across pasted tests (part 2) ---

export interface Share {
  k: number;
  n: number;
  low: number | null;
  high: number | null;
}
export interface KindSummary {
  kind: OwnKind;
  answers: number;
  wrong: number;
  enough: boolean;
  right: Share;
  topTrap: { trap: string; count: number; of: number } | null;
}
export type PacingStatus = "not_enough" | "maybe_time" | "counts_only";
export interface Pacing {
  status: PacingStatus;
  tests: number;
  late: { wrong: number; n: number };
  rest: { wrong: number; n: number };
  lateWrongMarked: number;
}
export interface OwnSummary {
  tests: number;
  answers: number;
  byKind: KindSummary[];
  pacing: Pacing;
}

const PACING: readonly PacingStatus[] = [
  "not_enough",
  "maybe_time",
  "counts_only",
];

function optNumber(v: unknown): number | null {
  if (v === null || v === undefined) return null;
  if (typeof v !== "number" || v < 0 || v > 1) throw new DataError("contract");
  return v;
}
function share(v: unknown): Share {
  const r = record(v);
  return {
    k: int(r.k),
    n: int(r.n),
    low: optNumber(r.low),
    high: optNumber(r.high),
  };
}
function wrongOf(v: unknown): { wrong: number; n: number } {
  const r = record(v);
  return { wrong: int(r.wrong), n: int(r.n) };
}

export function parseOwnSummary(value: unknown): OwnSummary {
  const r = record(value);
  const p = record(r.pacing);
  if (!PACING.includes(p.status as PacingStatus))
    throw new DataError("contract");
  return {
    tests: int(r.tests),
    answers: int(r.answers),
    byKind: list(r.by_kind).map((v) => {
      const k = record(v);
      const top =
        k.top_trap === null || k.top_trap === undefined
          ? null
          : record(k.top_trap);
      return {
        kind: kind(k.kind),
        answers: int(k.answers),
        wrong: int(k.wrong),
        enough: bool(k.enough),
        right: share(k.right),
        topTrap: top
          ? { trap: string(top.trap), count: int(top.count), of: int(top.of) }
          : null,
      };
    }),
    pacing: {
      status: p.status as PacingStatus,
      tests: int(p.tests),
      late: wrongOf(p.late),
      rest: wrongOf(p.rest),
      lateWrongMarked: int(p.late_wrong_marked),
    },
  };
}

/** A share as the page says it: "7/10 (35–93%)", the interval rounded to whole percent. */
export function shareText(s: Share): string {
  const base = `${s.k}/${s.n}`;
  if (s.low === null || s.high === null) return base;
  return `${base} (${Math.round(s.low * 100)}–${Math.round(s.high * 100)}%)`;
}

// --- Words from the passage (part 2, "Vocabulary") ---

export interface PassageWord {
  headword: string;
  form: string; // as written in the sentence: the card's answer
  level: string | null; // null: not in NGSL/NAWL
  sentence: string;
  deciding: boolean; // in a sentence that decided a wrong answer
  definition: string | null;
  vi: string | null;
  saved: boolean;
}
export interface PassageWords {
  level: string;
  levelSource: "level_test" | "default";
  words: PassageWord[];
}

export function parsePassageWords(value: unknown): PassageWords {
  const r = record(value);
  if (r.level_source !== "level_test" && r.level_source !== "default")
    throw new DataError("contract");
  return {
    level: string(r.level),
    levelSource: r.level_source,
    words: list(r.words).map((v) => {
      const w = record(v);
      return {
        headword: string(w.headword),
        form: string(w.form),
        level: optString(w.level),
        sentence: string(w.sentence),
        deciding: bool(w.deciding),
        definition: optString(w.definition),
        vi: optString(w.vi),
        saved: bool(w.saved),
      };
    }),
  };
}

/** The words the learner may still keep (not saved yet), deciding-sentence words ticked first. */
export function defaultPicks(words: PassageWord[]): string[] {
  return words.filter((w) => w.deciding && !w.saved).map((w) => w.form);
}

/** What keeping words did: new cards, and words that were already saved. */
export function parseKept(value: unknown): { added: number; already: number } {
  const r = record(value);
  return { added: int(r.added), already: int(r.already) };
}
