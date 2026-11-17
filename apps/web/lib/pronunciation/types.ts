// Pronunciation API shapes (specs/pronunciation/step-3.1.md), decoded strictly.
import { DataError, record, string } from "@/lib/decode";

export type QualityProblem =
  | "format"
  | "too_short"
  | "too_long"
  | "too_quiet"
  | "clipped"
  | "too_noisy"
  | "no_speech";
const PROBLEMS: readonly QualityProblem[] = [
  "format",
  "too_short",
  "too_long",
  "too_quiet",
  "clipped",
  "too_noisy",
  "no_speech",
];

export interface Sound {
  id: string;
  group: string;
  ipa: string;
  name_vi: string;
}
export interface Prompt {
  id: string;
  level: string;
  targets: string[];
  text: string;
}
export interface PronunciationPrompts {
  can_record: boolean;
  consent: string;
  sounds: Sound[];
  prompts: Prompt[];
}
export interface RecordingResult {
  ok: boolean;
  problems: QualityProblem[];
  id: string | null;
  delete_after: string | null;
}
export interface RecordingRow {
  id: string;
  prompt_id: string;
  keep: boolean;
  seconds: number;
  created_at: string;
  delete_after: string | null;
}

function list(value: unknown): unknown[] {
  if (!Array.isArray(value)) throw new DataError("contract");
  return value;
}
function flag(value: unknown): boolean {
  if (typeof value !== "boolean") throw new DataError("contract");
  return value;
}
function optional(value: unknown): string | null {
  return value === null || value === undefined ? null : string(value);
}

export function parsePrompts(value: unknown): PronunciationPrompts {
  const d = record(value);
  return {
    can_record: flag(d.can_record),
    consent: string(d.consent),
    sounds: list(d.sounds).map((s) => {
      const r = record(s);
      return {
        id: string(r.id),
        group: string(r.group),
        ipa: string(r.ipa),
        name_vi: string(r.name_vi),
      };
    }),
    prompts: list(d.prompts).map((p) => {
      const r = record(p);
      return {
        id: string(r.id),
        level: string(r.level),
        targets: list(r.targets).map(string),
        text: string(r.text),
      };
    }),
  };
}

export function parseRecordingResult(value: unknown): RecordingResult {
  const d = record(value);
  const q = record(d.quality);
  const problems = list(q.problems).map((p) => {
    const s = string(p);
    if (!(PROBLEMS as readonly string[]).includes(s))
      throw new DataError("contract");
    return s as QualityProblem;
  });
  return {
    ok: flag(q.ok),
    problems,
    id: optional(d.id),
    delete_after: optional(d.delete_after),
  };
}

export function parseRecordings(value: unknown): RecordingRow[] {
  return list(value).map((v) => {
    const r = record(v);
    if (typeof r.seconds !== "number") throw new DataError("contract");
    return {
      id: string(r.id),
      prompt_id: string(r.prompt_id),
      keep: flag(r.keep),
      seconds: r.seconds,
      created_at: string(r.created_at),
      delete_after: optional(r.delete_after),
    };
  });
}
