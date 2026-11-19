// Saying a vocabulary word (specs/pronunciation/step-3.7.md), decoded strictly.
import { DataError, record, string } from "@/lib/decode";

export interface SayStatus {
  analysis: boolean;
  owner: boolean;
  consent: string;
}
export interface PhoneResult {
  phone: string;
  gop: number;
  /** 0-100, computed by the server (the same formula as `closeness`). */
  closeness: number;
  heard: string | null;
  dropped: boolean;
  how: string | null;
}
/** A sound low in 2 of the word's last 3 attempts (step 3.7b). */
export interface Guide {
  index: number;
  phone: string;
  times: number;
  of: number;
  heard: string | null;
  dropped: boolean;
  how: string | null;
  change: string | null;
  minimal: [string, string] | null;
}
export interface SayResult {
  ok: boolean;
  problems: string[];
  phones: PhoneResult[];
  heard: string[];
  guide: Guide[];
}
export interface FocusSound {
  phone: string;
  low: number;
  seen: number;
  share: number;
  heard: string | null;
  how: string | null;
  example: string | null;
}
export interface Focus {
  days: number;
  attempts: number;
  sounds: FocusSound[];
}

function list(v: unknown): unknown[] {
  if (!Array.isArray(v)) throw new DataError("contract");
  return v;
}
function num(v: unknown): number {
  if (typeof v !== "number" || !Number.isFinite(v))
    throw new DataError("contract");
  return v;
}
function opt(v: unknown): string | null {
  return v === null || v === undefined ? null : string(v);
}
function bool(v: unknown): boolean {
  if (typeof v !== "boolean") throw new DataError("contract");
  return v;
}

export function parseSayStatus(value: unknown): SayStatus {
  const r = record(value);
  return {
    analysis: bool(r.analysis),
    owner: bool(r.owner),
    consent: string(r.consent),
  };
}

export function parseSayResult(value: unknown): SayResult {
  const r = record(value);
  return {
    ok: bool(r.ok),
    problems: list(r.problems).map(string),
    phones: list(r.phones).map((p) => {
      const x = record(p);
      const gop = num(x.gop);
      return {
        phone: string(x.phone),
        gop,
        closeness:
          x.closeness === undefined ? closeness(gop) : num(x.closeness),
        heard: opt(x.heard),
        dropped: bool(x.dropped),
        how: opt(x.how),
      };
    }),
    heard: r.heard === undefined ? [] : list(r.heard).map(string),
    guide: r.guide === undefined ? [] : list(r.guide).map(guide),
  };
}

function guide(value: unknown): Guide {
  const x = record(value);
  const pair =
    x.minimal === null || x.minimal === undefined
      ? null
      : list(x.minimal).map(string);
  if (pair !== null && pair.length !== 2) throw new DataError("contract");
  return {
    index: num(x.index),
    phone: string(x.phone),
    times: num(x.times),
    of: num(x.of),
    heard: opt(x.heard),
    dropped: bool(x.dropped),
    how: opt(x.how),
    change: opt(x.change),
    minimal: pair as [string, string] | null,
  };
}

export function parseFocus(value: unknown): Focus {
  const r = record(value);
  return {
    days: r.days === undefined ? 30 : num(r.days),
    attempts: r.attempts === undefined ? 0 : num(r.attempts),
    sounds: list(r.sounds).map((v) => {
      const x = record(v);
      return {
        phone: string(x.phone),
        low: num(x.low),
        seen: num(x.seen),
        share: num(x.share),
        heard: opt(x.heard),
        how: opt(x.how),
        example: opt(x.example),
      };
    }),
  };
}

/** The colour of a closeness: red (0) through amber to green (100). */
export function hue(c: number): number {
  return Math.round(Math.max(0, Math.min(100, c)) * 1.2);
}

/**
 * A rough 0–100 reading of a phone's score (log posterior ratio; 0 is the best). Raw, not a mark:
 * nothing is right or wrong until the pronunciation gate (specs/pronunciation).
 */
export function closeness(gop: number): number {
  return Math.max(0, Math.min(100, Math.round(100 * Math.exp(gop / 3))));
}
