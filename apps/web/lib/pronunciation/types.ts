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
export type RecordingStatus = "stored" | "analysed" | "failed";
const STATUSES: readonly RecordingStatus[] = ["stored", "analysed", "failed"];

export interface RecordingRow {
  id: string;
  prompt_id: string;
  keep: boolean;
  seconds: number;
  status: RecordingStatus;
  created_at: string;
  delete_after: string | null;
}
/** One target sound in a recording (step 3.3a): scores only, no right/wrong verdict yet. */
export interface TargetScore {
  sound: string;
  word: string;
  phone: string;
  gop: number;
  competitor: string | null;
  start_ms: number;
  end_ms: number;
}
export type Label = "right" | "wrong" | "unsure";
const LABELS: readonly Label[] = ["right", "wrong", "unsure"];
export interface RecordingDetail {
  id: string;
  status: RecordingStatus;
  keep: boolean;
  failed: boolean;
  targets: TargetScore[];
  /** The owner's label per target index (step 3.3b). */
  labels: Record<number, Label>;
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

function status(value: unknown): RecordingStatus {
  const s = string(value);
  if (!(STATUSES as readonly string[]).includes(s))
    throw new DataError("contract");
  return s as RecordingStatus;
}
function num(value: unknown): number {
  if (typeof value !== "number" || !Number.isFinite(value))
    throw new DataError("contract");
  return value;
}

function labels(value: unknown): Record<number, Label> {
  const out: Record<number, Label> = {};
  for (const item of value === undefined ? [] : list(value)) {
    const r = record(item);
    const label = string(r.label);
    if (!(LABELS as readonly string[]).includes(label))
      throw new DataError("contract");
    out[num(r.target)] = label as Label;
  }
  return out;
}

export function parseRecording(value: unknown): RecordingDetail {
  const d = record(value);
  const analysis =
    d.analysis === null || d.analysis === undefined ? null : record(d.analysis);
  return {
    id: string(d.id),
    status: status(d.status),
    keep: flag(d.keep),
    failed: flag(d.failed),
    targets: analysis
      ? list(analysis.targets).map((t) => {
          const r = record(t);
          return {
            sound: string(r.sound),
            word: string(r.word),
            phone: string(r.phone),
            gop: num(r.gop),
            start_ms: num(r.start_ms),
            end_ms: num(r.end_ms),
            competitor: optional(r.competitor),
          };
        })
      : [],
    labels: labels(d.labels),
  };
}

export function parseRecordings(value: unknown): RecordingRow[] {
  return list(value).map((v) => {
    const r = record(v);
    return {
      id: string(r.id),
      prompt_id: string(r.prompt_id),
      keep: flag(r.keep),
      seconds: num(r.seconds),
      status: status(r.status),
      created_at: string(r.created_at),
      delete_after: optional(r.delete_after),
    };
  });
}
