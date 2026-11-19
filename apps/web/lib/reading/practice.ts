// Reading practice (specs/listening-reading/step-4.3.md, plan CP4), decoded strictly.
import type { DecisionTrace } from "@/lib/contracts";
import { DataError, parseTrace, record, string } from "@/lib/decode";

export interface TextSummary {
  slug: string;
  title: string;
  questions: number;
  words: number;
}
export type Question =
  | { id: string; kind: "tfng"; skill: string; statement: string }
  | { id: string; kind: "mcq"; skill: string; stem: string; options: string[] }
  | {
      id: string;
      kind: "completion";
      skill: string;
      sentence: string;
      maxWords: number;
    }
  | {
      id: string;
      kind: "headings";
      skill: string;
      headings: string[];
      paragraphs: number[];
    };
export interface ReadingText {
  slug: string;
  title: string;
  passage: string;
  items: Question[];
}
export interface AnswerResult {
  correct: boolean;
  score: number;
  key: string;
  evidence: string[];
  competency: string;
  trace: DecisionTrace;
}
export type Answer = string | number | Record<string, number>;

function list(v: unknown): unknown[] {
  if (!Array.isArray(v)) throw new DataError("contract");
  return v;
}
function int(v: unknown): number {
  if (typeof v !== "number" || !Number.isInteger(v) || v < 0)
    throw new DataError("contract");
  return v;
}

export function parseTexts(value: unknown): TextSummary[] {
  return list(record(value).texts).map((t) => {
    const r = record(t);
    return {
      slug: string(r.slug),
      title: string(r.title),
      questions: int(r.questions),
      words: int(r.words),
    };
  });
}

function question(value: unknown): Question {
  const r = record(value);
  const base = { id: string(r.id), skill: string(r.skill) };
  switch (r.kind) {
    case "tfng":
      return { ...base, kind: "tfng", statement: string(r.statement) };
    case "mcq":
      return {
        ...base,
        kind: "mcq",
        stem: string(r.stem),
        options: list(r.options).map(string),
      };
    case "completion":
      return {
        ...base,
        kind: "completion",
        sentence: string(r.sentence),
        maxWords: int(r.max_words),
      };
    case "headings":
      return {
        ...base,
        kind: "headings",
        headings: list(r.headings).map(string),
        paragraphs: list(r.paragraphs).map(int),
      };
    default:
      throw new DataError("contract");
  }
}

export function parseText(value: unknown): ReadingText {
  const r = record(value);
  return {
    slug: string(r.slug),
    title: string(r.title),
    passage: string(r.passage),
    items: list(r.items).map(question),
  };
}

export function parseAnswer(value: unknown): AnswerResult {
  const r = record(value);
  if (typeof r.correct !== "boolean" || typeof r.score !== "number")
    throw new DataError("contract");
  return {
    correct: r.correct,
    score: r.score,
    key: string(r.key),
    evidence: list(r.evidence).map(string),
    competency: string(r.competency),
    trace: parseTrace(r.trace),
  };
}

/** The passage's paragraphs (blank-line separated), as the headings questions number them. */
export function paragraphsOf(passage: string): string[] {
  return passage
    .split(/\n\s*\n/)
    .map((p) => p.trim())
    .filter(Boolean);
}
