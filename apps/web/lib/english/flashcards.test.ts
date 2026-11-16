import { describe, expect, it } from "vitest";
import { afterAttempt, recallQueue, splitSession } from "./flashcards";
import type { VocabEntry } from "./types";

const card = (key: string) => ({
  key,
  lemma: key,
  pos: "noun",
  level: "B1",
  ipa: null,
  definition: `meaning of ${key}`,
  vi: null,
  example: `An example with ${key}.`,
});
const entry = (key: string, isNew: boolean): VocabEntry => ({
  item: {
    id: `core-seed|${key}:noun|${isNew ? "recall" : "gapfill"}|0`,
    kind: isNew ? "recall" : "gapfill",
    instruction_vi: "x",
    prompt: "p",
    options: null,
    hint: key[0],
  },
  is_new: isNew,
  card: isNew ? card(key) : null,
  due_at: isNew ? null : "2026-11-16T00:00:00Z",
});

describe("the new-word flow", () => {
  it("keeps reviews apart from the new words, in order", () => {
    const { reviews, fresh } = splitSession([
      entry("a", false),
      entry("b", true),
      entry("c", true),
    ]);
    expect(reviews.map((e) => e.card)).toEqual([null]);
    expect(fresh.map((e) => e.card?.lemma)).toEqual(["b", "c"]);
  });

  it("counts only the first try and sends a missed word to the end", () => {
    let q = recallQueue([entry("b", true), entry("c", true)]);
    expect(q.map((t) => [t.entry.card?.lemma, t.first])).toEqual([
      ["b", true],
      ["c", true],
    ]);
    q = afterAttempt(q, false); // b wrong
    expect(q.map((t) => [t.entry.card?.lemma, t.first])).toEqual([
      ["c", true],
      ["b", false],
    ]);
    q = afterAttempt(q, true); // c right
    q = afterAttempt(q, false); // b wrong again: still a retry
    expect(q.map((t) => [t.entry.card?.lemma, t.first])).toEqual([
      ["b", false],
    ]);
    expect(afterAttempt(afterAttempt(q, true), true)).toEqual([]);
  });
});
