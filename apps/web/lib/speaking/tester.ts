// An invited tester joining (specs/speaking/step-5.5.md): strict decoders. The session is never here:
// the proxy keeps it in an HttpOnly cookie and takes it out of the response.
import { DataError, record, string } from "@/lib/decode";

export interface Joined {
  learner_id: string;
  label: string;
  /** False until the owner has done the privacy review: the tester is signed in but cannot record. */
  may_record: boolean;
  research_notice: string;
  research_consented: boolean;
}

export interface LeftToday {
  mock_tests: number;
  practice_tries: number;
}

function flag(value: unknown): boolean {
  if (typeof value !== "boolean") throw new DataError("contract");
  return value;
}
function count(value: unknown): number {
  if (typeof value !== "number" || !Number.isInteger(value) || value < 0)
    throw new DataError("contract");
  return value;
}

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;

export function parseJoined(value: unknown): Joined {
  const j = record(value);
  const learner = string(j.learner_id);
  if (!UUID.test(learner)) throw new DataError("contract");
  if ("session" in j) throw new DataError("contract"); // the browser must never be given it
  return {
    learner_id: learner,
    label: string(j.label),
    may_record: flag(j.may_record),
    research_notice: string(j.research_notice),
    research_consented: flag(j.research_consented),
  };
}

/** What a tester has left today; null for the owner (no limits) and when nothing is limited. */
export function parseLeftToday(value: unknown): LeftToday | null {
  if (value === null || value === undefined) return null;
  const l = record(value);
  return {
    mock_tests: count(l.mock_tests),
    practice_tries: count(l.practice_tries),
  };
}

/** The invite token of a `/vao/{token}` link: 43 URL-safe characters, or null. */
export function inviteToken(value: string): string | null {
  return /^[A-Za-z0-9_-]{43}$/.test(value) ? value : null;
}
