// Dictionary search over the word list (specs/vocabulary/step-dictionary.md), decoded strictly.
import { DataError, record } from "@/lib/decode";
import { parseWordCard } from "@/lib/english/decode";
import type { WordCard } from "@/lib/english/types";

export interface DictionaryResult {
  draft: boolean;
  total: number;
  results: WordCard[];
}

export function parseDictionary(value: unknown): DictionaryResult {
  const d = record(value);
  if (
    (d.status !== "draft" && d.status !== "reviewed") ||
    typeof d.total !== "number" ||
    !Array.isArray(d.results)
  )
    throw new DataError("contract");
  return {
    draft: d.status === "draft",
    total: d.total,
    results: d.results.map(parseWordCard),
  };
}

/** The query sent to the API: trimmed, at most 40 characters; empty means "do not search". */
export function dictionaryQuery(text: string): string {
  return text.normalize("NFC").trim().replace(/\s+/g, " ").slice(0, 40);
}
