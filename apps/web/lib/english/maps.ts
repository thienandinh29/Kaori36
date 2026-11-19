// The two maps (specs/two-layer-map/spec.md, M4), decoded strictly.
import { DataError, record, string } from "@/lib/decode";

export type Status = "unmeasured" | "weak" | "growing" | "known";
const STATUSES: readonly string[] = ["unmeasured", "weak", "growing", "known"];

export interface Estimate {
  p: number | null;
  evidence: number;
  status: Status;
}
export interface Foundation extends Estimate {
  node: string;
  kind: "requires" | "helps";
  nameVi: string;
  live: boolean;
  href: string | null;
}
export interface Competency extends Estimate {
  slug: string;
  nameVi: string;
  available: boolean;
  links: Foundation[];
}
export interface Maps {
  skills: { skill: string; competencies: Competency[] }[];
  minEvidence: number;
  target: { overall: number; examDate: string; linksStatus: string };
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
function estimate(r: Record<string, unknown>): Estimate {
  const status = string(r.status);
  if (!STATUSES.includes(status)) throw new DataError("contract");
  const p = r.p === null ? null : num(r.p);
  if (p !== null && (p < 0 || p > 1)) throw new DataError("contract");
  return { p, evidence: num(r.evidence), status: status as Status };
}
function inApp(v: unknown): string | null {
  if (v === null) return null;
  const href = string(v);
  if (!href.startsWith("/") || href.startsWith("//"))
    throw new DataError("contract");
  return href;
}

export function parseMaps(value: unknown): Maps {
  const d = record(value);
  const t = record(d.target);
  return {
    skills: list(d.skills).map((s) => {
      const sr = record(s);
      return {
        skill: string(sr.skill),
        competencies: list(sr.competencies).map((c) => {
          const cr = record(c);
          if (typeof cr.available !== "boolean")
            throw new DataError("contract");
          return {
            slug: string(cr.slug),
            nameVi: string(cr.name_vi),
            available: cr.available,
            ...estimate(cr),
            links: list(cr.links).map((l) => {
              const lr = record(l);
              const kind = string(lr.kind);
              if (
                (kind !== "requires" && kind !== "helps") ||
                typeof lr.live !== "boolean"
              )
                throw new DataError("contract");
              return {
                node: string(lr.node),
                kind,
                nameVi: string(lr.name_vi),
                live: lr.live,
                href: inApp(lr.href),
                ...estimate(lr),
              };
            }),
          };
        }),
      };
    }),
    minEvidence: num(d.min_evidence),
    target: {
      overall: num(t.overall),
      examDate: string(t.exam_date),
      linksStatus: string(t.links_status),
    },
  };
}
