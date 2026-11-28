// Guided practice (specs/speaking/step-5.4b.md): strict decoders and the numbers side by side. Pure.
import { DataError, record, string } from "@/lib/decode";
import { parseAnswered, type Answered, type CueCard, type Part } from "./exam";

export interface Try {
  id: string;
  try_no: number;
  asked_seconds: number;
  finished: boolean;
  /** Only the first try counts as evidence of fluency; repeats are practice. */
  counts_as_evidence: boolean;
  answer: Answered | null;
}
export interface Practice {
  /** The first try's id: the practice's own id. */
  id: string;
  keep: boolean;
  test_id: string;
  title: string;
  question: { id: string; part: Part; text: string };
  cue_card: CueCard | null;
  theme: string | null;
  /** Topic words for the idea-building screen (Part 2 and 3 only). */
  words: string[];
  tries: Try[];
  max_tries: number;
  /** The time the next try would have; null when the tries are used or the last is unanswered. */
  next_seconds: number | null;
}
export interface StartedTry {
  id: string;
  keep: boolean;
  try_no: number;
  asked_seconds: number;
}

function list(value: unknown): unknown[] {
  if (!Array.isArray(value)) throw new DataError("contract");
  return value;
}
function num(value: unknown): number {
  if (typeof value !== "number" || !Number.isFinite(value) || value < 0)
    throw new DataError("contract");
  return value;
}
function flag(value: unknown): boolean {
  if (typeof value !== "boolean") throw new DataError("contract");
  return value;
}
function maybeString(value: unknown): string | null {
  return value === null || value === undefined ? null : string(value);
}
function part(value: unknown): Part {
  if (value !== 1 && value !== 2 && value !== 3)
    throw new DataError("contract");
  return value;
}

export function parseStartedTry(value: unknown): StartedTry {
  const s = record(value);
  return {
    id: string(s.id),
    keep: flag(s.keep),
    try_no: num(s.try_no),
    asked_seconds: num(s.asked_seconds),
  };
}

export function parsePractice(value: unknown): Practice {
  const p = record(value);
  const q = record(p.question);
  let cue: CueCard | null = null;
  if (p.cue_card !== null && p.cue_card !== undefined) {
    const c = record(p.cue_card);
    cue = {
      task: string(c.task),
      points: list(c.points).map(string),
      explain: string(c.explain),
    };
  }
  const tries = list(p.tries).map((x) => {
    const t = record(x);
    return {
      id: string(t.id),
      try_no: num(t.try_no),
      asked_seconds: num(t.asked_seconds),
      finished: flag(t.finished),
      counts_as_evidence: flag(t.counts_as_evidence),
      answer: t.answer === null ? null : parseAnswered(t.answer),
    };
  });
  const next = p.next_seconds === null ? null : num(p.next_seconds);
  // the first try, and only the first, counts as evidence
  if (tries.some((t) => t.counts_as_evidence !== (t.try_no === 1)))
    throw new DataError("contract");
  return {
    id: string(p.id),
    keep: flag(p.keep),
    test_id: string(p.test_id),
    title: string(p.title),
    question: { id: string(q.id), part: part(q.part), text: string(q.text) },
    cue_card: cue,
    theme: maybeString(p.theme),
    words: list(p.words).map(string),
    tries,
    max_tries: num(p.max_tries),
    next_seconds: next,
  };
}

export interface Row {
  key: "speechRate" | "pausesPerMinute" | "longestRun" | "shareOfTime";
  /** One value per try, in order; null where a try has no numbers (yet). */
  values: (number | null)[];
}

/**
 * The numbers of each try side by side: speech rate, pauses a minute, the longest fluent run and
 * the share of the time asked. Plain numbers: no arrows, no better or worse (step 5.4b).
 */
export function compareRows(tries: readonly Try[]): Row[] {
  const get = (f: (m: NonNullable<Answered["measures"]>) => number | null) =>
    tries.map((t) => {
      const m = t.answer?.measures;
      return m && m.words > 0 ? f(m) : null;
    });
  return [
    { key: "speechRate", values: get((m) => m.speech_rate) },
    { key: "pausesPerMinute", values: get((m) => m.pauses.per_minute) },
    { key: "longestRun", values: get((m) => m.longest_run.words) },
    { key: "shareOfTime", values: get((m) => m.share_of_time) },
  ];
}

/** Whether any try is still waiting for its transcript, numbers or checks (the page polls). */
export function pending(tries: readonly Try[]): boolean {
  return tries.some((t) => {
    const a = t.answer;
    if (!a) return false;
    if (a.transcript === "waiting") return true;
    return a.transcript === "done" && a.measures === null;
  });
}
