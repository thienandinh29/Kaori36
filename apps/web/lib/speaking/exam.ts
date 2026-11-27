// The examiner test (specs/speaking/step-5.4a.md): strict decoders and the examiner's script, pure and tested.
import { DataError, record, string } from "@/lib/decode";

export type Part = 1 | 2 | 3;

export interface Question {
  id: string;
  part: Part;
  text: string;
  seconds: number;
}
export interface CueCard {
  task: string;
  points: string[];
  explain: string;
}
export interface Timing {
  part1: number;
  prepare: number;
  long_turn: number;
  closing: number;
  part3: number;
}
export interface ExamTest {
  id: string;
  title: string;
  draft: boolean;
  part1_topics: string[];
  cue_card: CueCard;
  part3_theme: string;
  questions: Question[];
  timing: Timing;
}
export interface Sitting {
  id: string;
  keep: boolean;
  test: ExamTest;
}
export interface PastSitting {
  id: string;
  test_id: string;
  title: string;
  keep: boolean;
  started_at: string;
  finished_at: string | null;
  answers: number;
  with_audio: number;
}
export interface Overview {
  can_record: boolean;
  consent: string;
  tests: { id: string; title: string; draft: boolean; questions: number }[];
  past: PastSitting[];
}
export type TranscriptState = "done" | "waiting" | "failed" | "none";
export interface TimedWord {
  word: string;
  start: number;
  end: number;
}
export interface Answered {
  id: string;
  seconds: number;
  problems: string[];
  audio: boolean;
  delete_after: string | null;
  /** Step 5.1: the machine transcript, labelled as such on the page. */
  transcript: TranscriptState;
  text: string | null;
  words: TimedWord[];
}
export interface Result {
  id: string;
  test_id: string;
  title: string;
  keep: boolean;
  started_at: string;
  finished_at: string | null;
  cue_card: CueCard;
  part3_theme: string;
  questions: {
    id: string;
    part: Part;
    text: string;
    answer: Answered | null;
  }[];
}
export interface MicCheck {
  ok: boolean;
  problems: string[];
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
function maybe(value: unknown): string | null {
  return value === null || value === undefined ? null : string(value);
}
function part(value: unknown): Part {
  if (value !== 1 && value !== 2 && value !== 3)
    throw new DataError("contract");
  return value;
}
const strings = (value: unknown) => list(value).map(string);
const STATES: readonly TranscriptState[] = [
  "done",
  "waiting",
  "failed",
  "none",
];
function transcriptState(value: unknown): TranscriptState {
  const s = string(value);
  if (!(STATES as readonly string[]).includes(s))
    throw new DataError("contract");
  return s as TranscriptState;
}

function cueCard(value: unknown): CueCard {
  const c = record(value);
  return {
    task: string(c.task),
    points: strings(c.points),
    explain: string(c.explain),
  };
}

export function parseTest(value: unknown): ExamTest {
  const t = record(value);
  const timing = record(t.timing);
  return {
    id: string(t.id),
    title: string(t.title),
    draft: flag(t.draft),
    part1_topics: strings(t.part1_topics),
    cue_card: cueCard(t.cue_card),
    part3_theme: string(t.part3_theme),
    questions: list(t.questions).map((q) => {
      const x = record(q);
      return {
        id: string(x.id),
        part: part(x.part),
        text: string(x.text),
        seconds: num(x.seconds),
      };
    }),
    timing: {
      part1: num(timing.part1),
      prepare: num(timing.prepare),
      long_turn: num(timing.long_turn),
      closing: num(timing.closing),
      part3: num(timing.part3),
    },
  };
}

export function parseSitting(value: unknown): Sitting {
  const s = record(value);
  return { id: string(s.id), keep: flag(s.keep), test: parseTest(s.test) };
}

export function parseOverview(value: unknown): Overview {
  const o = record(value);
  return {
    can_record: flag(o.can_record),
    consent: string(o.consent),
    tests: list(o.tests).map((x) => {
      const t = record(x);
      return {
        id: string(t.id),
        title: string(t.title),
        draft: flag(t.draft),
        questions: num(t.questions),
      };
    }),
    past: list(o.past).map((x) => {
      const p = record(x);
      return {
        id: string(p.id),
        test_id: string(p.test_id),
        title: string(p.title),
        keep: flag(p.keep),
        started_at: string(p.started_at),
        finished_at: maybe(p.finished_at),
        answers: num(p.answers),
        with_audio: num(p.with_audio),
      };
    }),
  };
}

export function parseResult(value: unknown): Result {
  const r = record(value);
  return {
    id: string(r.id),
    test_id: string(r.test_id),
    title: string(r.title),
    keep: flag(r.keep),
    started_at: string(r.started_at),
    finished_at: maybe(r.finished_at),
    cue_card: cueCard(r.cue_card),
    part3_theme: string(r.part3_theme),
    questions: list(r.questions).map((x) => {
      const q = record(x);
      let answer: Answered | null = null;
      if (q.answer !== null) {
        const a = record(q.answer);
        answer = {
          id: string(a.id),
          seconds: num(a.seconds),
          problems: strings(a.problems),
          audio: flag(a.audio),
          delete_after: maybe(a.delete_after),
          transcript: transcriptState(a.transcript),
          text: maybe(a.text),
          words: list(a.words).map((w) => {
            const x = record(w);
            return {
              word: string(x.word),
              start: num(x.start),
              end: num(x.end),
            };
          }),
        };
        if ((answer.transcript === "done") !== (answer.text !== null))
          throw new DataError("contract");
      }
      return {
        id: string(q.id),
        part: part(q.part),
        text: string(q.text),
        answer,
      };
    }),
  };
}

export function parseMicCheck(value: unknown): MicCheck {
  const m = record(value);
  return { ok: flag(m.ok), problems: strings(m.problems) };
}

export function parseAnswerSaved(value: unknown): { id: string } {
  return { id: string(record(value).id) };
}

/** One step of the examiner's script. The examiner's own lines are NodeTrail's wording. */
export type Step =
  | { kind: "say"; part: Part; text: string }
  | { kind: "cue"; part: 2; text: string }
  | { kind: "prepare"; part: 2; seconds: number }
  | { kind: "ask"; part: Part; question: Question; speak: boolean }
  | { kind: "end" };

export const LINES = {
  part1:
    "Hello. In this first part of the test, I'd like to ask you some questions about yourself.",
  topic: (topic: string) => `Let's talk about ${topic}.`,
  part2:
    "Now I'm going to give you a topic, and I'd like you to talk about it for one to two minutes. Before you talk, you have one minute to think about what you are going to say. You can make some notes if you wish. Here is your topic.",
  start:
    "Remember, you have one to two minutes for this. I'll stop you when the time is up. Please start speaking now.",
  thanks: "Thank you.",
  part3: (theme: string) =>
    `We've been talking about ${theme}. Now I'd like to ask you some more general questions related to this.`,
  end: "Thank you. That is the end of the speaking test.",
} as const;

/** The cue card read aloud: the task, the points, and what to explain. */
export function cueText(card: CueCard): string {
  return `${card.task} You should say: ${card.points.join("; ")}; ${card.explain}`;
}

/** The whole test in the examiner's order. Refuses a test whose questions do not match its topics. */
export function script(test: ExamTest): Step[] {
  const byId = new Map(test.questions.map((q) => [q.id, q]));
  const need = (id: string) => {
    const q = byId.get(id);
    if (!q) throw new DataError("contract");
    return q;
  };
  const steps: Step[] = [{ kind: "say", part: 1, text: LINES.part1 }];
  test.part1_topics.forEach((topic, i) => {
    steps.push({ kind: "say", part: 1, text: LINES.topic(topic) });
    for (const q of test.questions)
      if (q.part === 1 && q.id.startsWith(`p1-${i + 1}-`))
        steps.push({ kind: "ask", part: 1, question: q, speak: true });
  });
  steps.push(
    { kind: "say", part: 2, text: LINES.part2 },
    { kind: "cue", part: 2, text: cueText(test.cue_card) },
    { kind: "prepare", part: 2, seconds: test.timing.prepare },
    { kind: "say", part: 2, text: LINES.start },
    { kind: "ask", part: 2, question: need("p2-long"), speak: false },
    { kind: "say", part: 2, text: LINES.thanks },
    { kind: "ask", part: 2, question: need("p2-closing"), speak: true },
    { kind: "say", part: 3, text: LINES.part3(test.part3_theme) },
  );
  for (const q of test.questions)
    if (q.part === 3)
      steps.push({ kind: "ask", part: 3, question: q, speak: true });
  steps.push({ kind: "say", part: 3, text: LINES.end }, { kind: "end" });
  const asked = steps.filter((s) => s.kind === "ask").length;
  if (asked !== test.questions.length) throw new DataError("contract");
  return steps;
}

export const SPEED_KEY = "nodetrail_exam_speed";

/** A speed factor for automated tests only (0 < x ≤ 1); anything else means real time. */
export function examSpeed(stored: string | null): number {
  const x = stored === null ? NaN : Number(stored);
  return Number.isFinite(x) && x > 0 && x <= 1 ? x : 1;
}

/** Milliseconds for `seconds` at the given speed. */
export function ms(seconds: number, speed: number): number {
  return Math.max(200, Math.round(seconds * 1000 * speed));
}

/** How long to show an examiner line when no voice can read it: about 2.5 words a second. */
export function readingSeconds(text: string): number {
  return Math.max(2, text.split(/\s+/).filter(Boolean).length / 2.5);
}

/** A line split at sentence or clause ends into pieces the voice accepts (at most `max` characters). */
export function voiceChunks(text: string, max = 300): string[] {
  const parts = text.split(/(?<=[.?!;:])\s+/).filter(Boolean);
  const out: string[] = [];
  for (const part of parts) {
    const last = out.at(-1);
    if (last !== undefined && last.length + 1 + part.length <= max)
      out[out.length - 1] = `${last} ${part}`;
    else out.push(part.length <= max ? part : part.slice(0, max));
  }
  return out;
}

/** "1:05" from seconds. */
export function clock(seconds: number): string {
  const s = Math.max(0, Math.ceil(seconds));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

/** The progress line during the test: the part, and the question being asked (or the last one). */
export function progress(
  steps: Step[],
  index: number,
): { part: Part; question: number; total: number } {
  const total = steps.filter((s) => s.kind === "ask").length;
  const upTo = steps.slice(0, index + 1).filter((s) => s.kind === "ask").length;
  let part: Part = 1;
  for (let i = Math.min(index, steps.length - 1); i >= 0; i--) {
    const s = steps[i]!;
    if (s.kind !== "end") {
      part = s.part;
      break;
    }
  }
  return { part, question: Math.max(1, upTo), total };
}
