// Strict decoding of the lesson API (specs/grammar-lessons): an unknown action is a contract error.
import { DataError, record, string } from "@/lib/decode";
import type {
  Action,
  CefrLevel,
  CheckpointResult,
  CheckpointView,
  LessonSummary,
  LessonView,
  Scene,
} from "./types";

const LEVELS: readonly CefrLevel[] = ["A1", "A2", "B1", "B2", "C1"];
const STATUSES = ["sample", "draft", "reviewed"] as const;

function list(value: unknown): unknown[] {
  if (!Array.isArray(value)) throw new DataError("contract");
  return value;
}
function texts(value: unknown): string[] {
  return list(value).map(string);
}
function num(value: unknown): number {
  if (typeof value !== "number" || !Number.isFinite(value))
    throw new DataError("contract");
  return value;
}
function flag(value: unknown): boolean {
  if (typeof value !== "boolean") throw new DataError("contract");
  return value;
}
function oneOf<T extends string>(value: unknown, allowed: readonly T[]): T {
  const s = string(value);
  if (!(allowed as readonly string[]).includes(s))
    throw new DataError("contract");
  return s as T;
}

export function parseAction(value: unknown): Action {
  const d = record(value);
  switch (d.do) {
    case "say":
      return { do: "say", en: string(d.en), vi: string(d.vi) };
    case "show_example":
      return {
        do: "show_example",
        id: string(d.id),
        en: string(d.en),
        vi: string(d.vi),
        target: string(d.target),
      };
    case "spotlight":
      return { do: "spotlight", example: string(d.example) };
    case "board_table":
      return { do: "board_table", rows: list(d.rows).map(texts) };
    case "board_timeline":
      return {
        do: "board_timeline",
        points: list(d.points).map((p) => {
          const r = record(p);
          return { label: string(r.label), at: num(r.at) };
        }),
        spans: list(d.spans).map((s) => {
          const r = record(s);
          return {
            label: string(r.label),
            start: num(r.start),
            end: num(r.end),
            open: flag(r.open),
          };
        }),
      };
    case "board_write":
      return { do: "board_write", text: string(d.text) };
    case "board_clear":
      return { do: "board_clear" };
    case "ask":
      return { do: "ask", checkpoint: string(d.checkpoint) };
    case "pause":
      return { do: "pause" };
    default:
      throw new DataError("contract");
  }
}

function parseScene(value: unknown): Scene {
  const d = record(value);
  return {
    id: string(d.id),
    kind: string(d.kind),
    misconceptions: texts(d.misconceptions),
    actions: list(d.actions).map(parseAction),
  };
}

function parseCheckpoint(value: unknown): CheckpointView {
  const d = record(value);
  if ("correct" in d || "key" in d) throw new DataError("contract"); // a key must never arrive
  return {
    id: string(d.id),
    en: string(d.en),
    vi: string(d.vi),
    options: texts(d.options),
  };
}

export function parseLesson(value: unknown): LessonView {
  const d = record(value);
  const lesson: LessonView = {
    node: string(d.node),
    course: string(d.course),
    level: oneOf(d.level, LEVELS),
    status: oneOf(d.status, STATUSES),
    title_en: string(d.title_en),
    title_vi: string(d.title_vi),
    noncommercial: flag(d.noncommercial),
    sources: list(d.sources).map((s) => {
      const r = record(s);
      return {
        candidate: string(r.candidate),
        chapter: string(r.chapter),
        licence: string(r.licence),
      };
    }),
    scenes: list(d.scenes).map(parseScene),
    checkpoints: list(d.checkpoints).map(parseCheckpoint),
  };
  const asked = new Set(lesson.checkpoints.map((c) => c.id));
  for (const s of lesson.scenes)
    for (const a of s.actions)
      if (a.do === "ask" && !asked.has(a.checkpoint))
        throw new DataError("contract");
  return lesson;
}

export function parseLessonSummaries(value: unknown): LessonSummary[] {
  return list(value).map((v) => {
    const d = record(v);
    return {
      node: string(d.node),
      level: oneOf(d.level, LEVELS),
      status: oneOf(d.status, STATUSES),
      title_en: string(d.title_en),
      title_vi: string(d.title_vi),
    };
  });
}

export function parseCheckpointResult(value: unknown): CheckpointResult {
  const d = record(value);
  const why = d.misconception_vi;
  return {
    correct: flag(d.correct),
    key: string(d.key),
    explain_vi: string(d.explain_vi),
    misconception_vi: why === null || why === undefined ? null : string(why),
  };
}
