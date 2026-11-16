// The new-word flow (specs/vocabulary, flashcards): flashcards first, then each word typed from
// memory. Pure helpers, tested in flashcards.test.ts.
import type { VocabEntry } from "./types";

export interface RecallTask {
  entry: VocabEntry;
  /** Only the first try counts for the schedule; a retry is checked, never scheduled. */
  first: boolean;
}

export function splitSession(entries: readonly VocabEntry[]): {
  reviews: VocabEntry[];
  fresh: VocabEntry[];
} {
  return {
    reviews: entries.filter((e) => !e.is_new),
    fresh: entries.filter((e) => e.is_new && e.card !== null),
  };
}

export function recallQueue(fresh: readonly VocabEntry[]): RecallTask[] {
  return fresh.map((entry) => ({ entry, first: true }));
}

/** The queue after an attempt on its head: a wrong word goes to the end, as a retry. */
export function afterAttempt(
  queue: readonly RecallTask[],
  correct: boolean,
): RecallTask[] {
  const [head, ...rest] = queue;
  if (!head) return [];
  return correct ? rest : [...rest, { entry: head.entry, first: false }];
}
