// Timed Reading tests (specs/listening-reading/step-4.3b.md), decoded strictly; time helpers are pure.
import { DataError, record, string } from "@/lib/decode";
import {
  parseText,
  type Answer,
  type Question,
  type ReadingText,
} from "./practice";

export interface StartedTest extends ReadingText {
  testId: string;
  limitSeconds: number;
}
export interface TestResultItem {
  id: string;
  answer: unknown;
  correct: boolean;
  key: string;
  evidence: string[];
  atSeconds: number | null;
}
export interface TestResult {
  correct: number;
  total: number;
  answered: number;
  overTime: boolean;
  seconds: number;
  items: TestResultItem[];
}
/** What the learner has chosen so far, and when (seconds into the test). */
export type Given = Record<string, { answer: Answer; atSeconds: number }>;

function count(v: unknown): number {
  if (typeof v !== "number" || !Number.isInteger(v) || v < 0)
    throw new DataError("contract");
  return v;
}

export function parseStartedTest(value: unknown): StartedTest {
  const r = record(value);
  return {
    ...parseText(value),
    testId: string(r.test_id),
    limitSeconds: count(r.limit_seconds),
  };
}

export function parseTestResult(value: unknown): TestResult {
  const r = record(value);
  if (typeof r.over_time !== "boolean" || !Array.isArray(r.items))
    throw new DataError("contract");
  return {
    correct: count(r.correct),
    total: count(r.total),
    answered: count(r.answered),
    overTime: r.over_time,
    seconds: count(r.seconds),
    items: r.items.map((v) => {
      const i = record(v);
      if (typeof i.correct !== "boolean" || !Array.isArray(i.evidence))
        throw new DataError("contract");
      return {
        id: string(i.id),
        answer: i.answer ?? null,
        correct: i.correct,
        key: string(i.key),
        evidence: i.evidence.map(string),
        atSeconds: i.at_seconds === null ? null : count(i.at_seconds),
      };
    }),
  };
}

/** 754 -> "12:34"; never negative. */
export function clock(seconds: number): string {
  const s = Math.max(0, Math.floor(seconds));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

/** Seconds left, from the local start time; the server decides what is over time. */
export function remaining(
  startMs: number,
  limitSeconds: number,
  nowMs: number,
): number {
  return Math.max(0, limitSeconds - Math.floor((nowMs - startMs) / 1000));
}

/** Whether a question has an answer worth sending (a headings question needs every paragraph). */
export function answered(q: Question, a: Answer | undefined): boolean {
  if (a === undefined) return false;
  if (q.kind === "headings")
    return (
      typeof a === "object" &&
      q.paragraphs.every((p) => typeof a[String(p)] === "number")
    );
  if (q.kind === "completion") return typeof a === "string" && a.trim() !== "";
  return true;
}

/** The submission body: only answered questions, as the API expects. */
export function submission(items: Question[], given: Given) {
  const out: Record<string, { answer: Answer; at_seconds: number }> = {};
  for (const q of items) {
    const g = given[q.id];
    if (g && answered(q, g.answer))
      out[q.id] = {
        answer: typeof g.answer === "string" ? g.answer.trim() : g.answer,
        at_seconds: g.atSeconds,
      };
  }
  return out;
}
