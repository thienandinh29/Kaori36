// The reviewer portal (specs/validation/step-v2.md): token handling, strict decoding, the API calls.
import { DataError, record, string } from "@/lib/decode";

/** The token's shape: secrets.token_urlsafe(32) on the server. */
export const TOKEN = /^[A-Za-z0-9_-]{43}$/;
export const TOKEN_KEY = "nodetrail_reviewer";
export const LEVELS = ["A1", "A2", "B1", "B2", "C1"] as const;
export type Level = (typeof LEVELS)[number];
export type Verdict = "right" | "wrong" | "unsure";
export const REASONS = [
  "wrong_key",
  "not_answerable",
  "two_answers",
  "unclear",
  "other",
] as const;
export type Reason = (typeof REASONS)[number];

export interface Batch {
  id: string;
  name: string;
  contentType: string;
  total: number;
  done: number;
}
export interface Me {
  name: string;
  role: string;
  batches: Batch[];
}
export interface ReadingView {
  contentType: "reading_item";
  contentId: string;
  kind: string;
  skill: string;
  passage: string;
  question: Record<string, unknown>;
  key: unknown;
}
export interface TextView {
  contentType: "text_level";
  contentId: string;
  text: string;
}
export interface Next {
  total: number;
  done: number;
  unavailable: number;
  item: ReadingView | TextView | null;
}
export type PortalLabel =
  | {
      answer?: string;
      verdict: Verdict;
      reason?: Reason;
      note?: string;
    }
  | { level: Level | "unsure"; note?: string };

/**
 * The token from a link `/kiem-duyet#<token>`, else the one kept for this tab.
 * Returns the token and whether the address bar should be cleared.
 */
export function pickToken(
  hash: string,
  stored: string | null,
): { token: string | null; clear: boolean } {
  const fromLink = hash.replace(/^#/, "");
  if (TOKEN.test(fromLink)) return { token: fromLink, clear: true };
  return {
    token: stored && TOKEN.test(stored) ? stored : null,
    clear: fromLink !== "",
  };
}

function count(value: unknown): number {
  if (typeof value !== "number" || !Number.isInteger(value) || value < 0)
    throw new DataError("contract");
  return value;
}
function list(value: unknown): unknown[] {
  if (!Array.isArray(value)) throw new DataError("contract");
  return value;
}

export function parseMe(value: unknown): Me {
  const d = record(value);
  return {
    name: string(d.name),
    role: string(d.role),
    batches: list(d.batches).map((b) => {
      const r = record(b);
      return {
        id: string(r.id),
        name: string(r.name),
        contentType: string(r.content_type),
        total: count(r.total),
        done: count(r.done),
      };
    }),
  };
}

export function parseNext(value: unknown): Next {
  const d = record(value);
  let item: Next["item"] = null;
  if (d.item !== null) {
    const r = record(d.item);
    const kind = string(r.content_type);
    if (kind === "reading_item")
      item = {
        contentType: kind,
        contentId: string(r.content_id),
        kind: string(r.kind),
        skill: string(r.skill),
        passage: string(r.passage),
        question: record(r.question),
        key: r.key,
      };
    else if (kind === "text_level")
      item = {
        contentType: kind,
        contentId: string(r.content_id),
        text: string(r.text),
      };
    else throw new DataError("contract");
  }
  return {
    total: count(d.total),
    done: count(d.done),
    unavailable: count(d.unavailable),
    item,
  };
}

type Fetch = typeof fetch;

export function reviewClient(
  token: string,
  fetcher: Fetch = (...a) => fetch(...a),
) {
  async function request(path: string, init: RequestInit = {}) {
    let response: Response;
    try {
      response = await fetcher(`/api/backend/review/${path}`, {
        ...init,
        headers: {
          ...(init.headers as Record<string, string> | undefined),
          "X-Reviewer-Token": token,
        },
        cache: "no-store",
        signal: AbortSignal.timeout(25000),
      });
    } catch {
      throw new DataError("network");
    }
    if (!response.ok)
      throw new DataError(
        response.status === 503 ? "configuration" : "failed",
        response.status,
      );
    try {
      return (await response.json()) as unknown;
    } catch {
      throw new DataError("contract");
    }
  }
  return {
    me: async () => parseMe(await request("me")),
    next: async (batch: string) =>
      parseNext(await request(`batches/${encodeURIComponent(batch)}/next`)),
    label: (batch: string, contentId: string, body: PortalLabel) =>
      request(
        `batches/${encodeURIComponent(batch)}/items/${encodeURIComponent(contentId)}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        },
      ),
  };
}
