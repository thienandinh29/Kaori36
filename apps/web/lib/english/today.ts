// Today's list (specs/two-layer-map/spec.md, M3; step-m5.md: fixed for the day, done marks), decoded strictly.
import type { DecisionTrace } from "@/lib/contracts";
import { DataError, parseTrace, record, string } from "@/lib/decode";

export type TodayKind =
  "review" | "diagnostic" | "learn_foundation" | "practise_competency";
const KINDS: readonly string[] = [
  "review",
  "diagnostic",
  "learn_foundation",
  "practise_competency",
];

export interface TodayActivity {
  kind: TodayKind;
  target: string;
  nameVi: string;
  via: string | null;
  href: string;
  trace: DecisionTrace;
  /** Practised today (step M5): from today's answers, never "mastered". */
  done: boolean;
  /** A rough estimate, not measured. */
  minutes: number;
}
export interface Today {
  /** The learner's day (Vietnam time): the plan is fixed for it. */
  day: string;
  doneCount: number;
  activities: TodayActivity[];
  names: Record<string, string>;
  target: { overall: number; examDate: string; linksStatus: string };
}

export function parseToday(value: unknown): Today {
  const d = record(value);
  if (!Array.isArray(d.activities)) throw new DataError("contract");
  const t = record(d.target);
  if (typeof t.overall !== "number") throw new DataError("contract");
  const names = record(d.names);
  if (typeof d.done_count !== "number") throw new DataError("contract");
  return {
    day: string(d.day),
    doneCount: d.done_count,
    activities: d.activities.map((v) => {
      const a = record(v);
      const kind = string(a.kind);
      const href = string(a.href);
      // Only in-app links: the list never sends the learner off the site.
      if (
        !KINDS.includes(kind) ||
        !href.startsWith("/") ||
        href.startsWith("//") ||
        typeof a.done !== "boolean" ||
        typeof a.minutes !== "number"
      )
        throw new DataError("contract");
      return {
        kind: kind as TodayKind,
        target: string(a.target),
        nameVi: string(a.name_vi),
        via: a.via == null ? null : string(a.via),
        href,
        trace: parseTrace(a.trace),
        done: a.done,
        minutes: a.minutes,
      };
    }),
    names: Object.fromEntries(
      Object.entries(names).map(([k, v]) => [k, string(v)]),
    ),
    target: {
      overall: t.overall,
      examDate: string(t.exam_date),
      linksStatus: string(t.links_status),
    },
  };
}
