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
  heard: string | null;
  dropped: boolean;
}
export interface SayResult {
  ok: boolean;
  problems: string[];
  phones: PhoneResult[];
  heard: string[];
}

function list(v: unknown): unknown[] {
  if (!Array.isArray(v)) throw new DataError("contract");
  return v;
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
      if (typeof x.gop !== "number") throw new DataError("contract");
      return {
        phone: string(x.phone),
        gop: x.gop,
        heard: x.heard === null ? null : string(x.heard),
        dropped: bool(x.dropped),
      };
    }),
    heard: r.heard === undefined ? [] : list(r.heard).map(string),
  };
}

/**
 * A rough 0–100 reading of a phone's score (log posterior ratio; 0 is the best). Raw, not a mark:
 * nothing is right or wrong until the pronunciation gate (specs/pronunciation).
 */
export function closeness(gop: number): number {
  return Math.max(0, Math.min(100, Math.round(100 * Math.exp(gop / 3))));
}
