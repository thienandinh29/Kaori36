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
/** The reasons a "wrong" verdict may give, per content type (the server checks the same). */
export const REASONS_BY_TYPE: Record<string, readonly string[]> = {
  reading_item: REASONS,
  grammar_item: ["wrong_key", "two_answers", "unclear", "other"],
  vocab_entry: [
    "definition",
    "example",
    "collocation",
    "form",
    "gloss",
    "ipa",
    "other",
  ],
  speech_target: [],
};
export type Reason = string;

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
export interface GrammarView {
  contentType: "grammar_item";
  contentId: string;
  prompt: string;
  options: string[];
  key: number | null;
}
export interface VocabView {
  contentType: "vocab_entry";
  contentId: string;
  lemma: string;
  pos: string;
  level: string;
  ipa: string | null;
  definition: string;
  vi: string | null;
  examples: string[];
  collocations: string[];
  forms: string[];
}
export interface SpeechView {
  contentType: "speech_target";
  contentId: string;
  sentence: string | null;
  word: string;
  ipa: string | null;
  soundVi: string | null;
  startMs: number;
  endMs: number;
}
export type View =
  ReadingView | TextView | GrammarView | VocabView | SpeechView;
export interface Next {
  total: number;
  done: number;
  unavailable: number;
  item: View | null;
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
function maybe(value: unknown): string | null {
  return value === null || value === undefined ? null : string(value);
}
function ms(value: unknown): number {
  if (typeof value !== "number" || !Number.isFinite(value) || value < 0)
    throw new DataError("contract");
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
    else if (kind === "grammar_item")
      item = {
        contentType: kind,
        contentId: string(r.content_id),
        prompt: string(r.prompt),
        options: list(r.options).map(string),
        key: r.key === null ? null : count(r.key),
      };
    else if (kind === "vocab_entry")
      item = {
        contentType: kind,
        contentId: string(r.content_id),
        lemma: string(r.lemma),
        pos: string(r.pos),
        level: string(r.level),
        ipa: maybe(r.ipa),
        definition: string(r.definition),
        vi: maybe(r.vi),
        examples: list(r.examples).map(string),
        collocations: list(r.collocations).map(string),
        forms: list(r.forms).map(string),
      };
    else if (kind === "speech_target")
      item = {
        contentType: kind,
        contentId: string(r.content_id),
        sentence: maybe(r.sentence),
        word: string(r.word),
        ipa: maybe(r.ipa),
        soundVi: maybe(r.sound_vi),
        startMs: ms(r.start_ms),
        endMs: ms(r.end_ms),
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
  // ":" stays as it is (pronunciation ids are "<recording>:<n>"): the proxy refuses encoded segments.
  const itemPath = (batch: string, contentId: string) =>
    `batches/${encodeURIComponent(batch)}/items/${encodeURIComponent(contentId).replace(/%3A/g, ":")}`;
  return {
    /** A recording to play: fetched with the token header, never as a plain URL. */
    audio: async (batch: string, contentId: string): Promise<Blob> => {
      let response: Response;
      try {
        response = await fetcher(
          `/api/backend/review/${itemPath(batch, contentId)}/audio`,
          {
            headers: { "X-Reviewer-Token": token },
            cache: "no-store",
            signal: AbortSignal.timeout(25000),
          },
        );
      } catch {
        throw new DataError("network");
      }
      if (!response.ok) throw new DataError("failed", response.status);
      return response.blob();
    },
    me: async () => parseMe(await request("me")),
    next: async (batch: string) =>
      parseNext(await request(`batches/${encodeURIComponent(batch)}/next`)),
    label: (batch: string, contentId: string, body: PortalLabel) =>
      request(itemPath(batch, contentId), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      }),
  };
}
