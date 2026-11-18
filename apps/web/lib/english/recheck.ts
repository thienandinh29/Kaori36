// FORGET-001: delayed grammar re-checks (specs/forget-001/spec.md), decoded strictly.
import { DataError, record, string } from "@/lib/decode";

export interface RecheckQuestion {
  id: string;
  node: string;
  nodeNameVi: string;
  prompt: string;
  options: string[];
  draft: boolean;
}
export interface RecheckResult {
  correct: boolean;
  key: string;
}

export function parseRecheck(value: unknown): RecheckQuestion | null {
  const d = record(value);
  if (d.question === null) return null;
  const q = record(d.question);
  if (!Array.isArray(q.options) || typeof q.draft !== "boolean")
    throw new DataError("contract");
  return {
    id: string(q.id),
    node: string(q.node),
    nodeNameVi: string(q.node_name_vi),
    prompt: string(q.prompt),
    options: q.options.map(string),
    draft: q.draft,
  };
}

export function parseRecheckResult(value: unknown): RecheckResult {
  const d = record(value);
  if (typeof d.correct !== "boolean") throw new DataError("contract");
  return { correct: d.correct, key: string(d.key) };
}
