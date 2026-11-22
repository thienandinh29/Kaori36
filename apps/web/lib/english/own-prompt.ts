import type { KeyValueStore } from "./learner";
import type { WritingTest } from "./types";

/** The page slug for writing on the learner's own Task 2 question (specs/writing/step-2.10.md). */
export const OWN_SLUG = "de-cua-ban";
/** The API's prompt id for an own question. */
export const OWN_ID = "own";

const OWN_KEY = "nodetrail_own_prompt";
const TEST_KEY = "nodetrail_writing_test";
const PARTS_KEY = "nodetrail_own_parts";

/** The prompt id the API expects for a page slug. */
export function promptIdFor(slug: string): string {
  return slug === OWN_SLUG ? OWN_ID : slug;
}

/**
 * The question and the parts the learner kept (step 2.11b); `parts` null keeps every part the
 * server proposes.
 */
export function saveOwnPrompt(
  store: KeyValueStore | null,
  text: string,
  parts: string[] | null = null,
): void {
  try {
    store?.setItem(OWN_KEY, text);
    store?.setItem(PARTS_KEY, parts === null ? "" : JSON.stringify(parts));
  } catch {
    // the editor then asks for the question again
  }
}

/** The parts kept for the saved question, or null for all of them. */
export function ownParts(store: KeyValueStore | null): string[] | null {
  try {
    const raw = store?.getItem(PARTS_KEY);
    if (!raw) return null;
    const v: unknown = JSON.parse(raw);
    if (!Array.isArray(v) || v.length === 0) return null;
    return v.every((x) => typeof x === "string") ? v : null;
  } catch {
    return null;
  }
}

export function ownPrompt(store: KeyValueStore | null): string | null {
  try {
    const v = store?.getItem(OWN_KEY) ?? null;
    return v && v.trim() ? v : null;
  } catch {
    return null;
  }
}

/**
 * The exam in progress for this prompt, kept so a reload continues the same test (the server's
 * clock stays the truth); a test for another prompt or question is not reused.
 */
export function savedTest(
  store: KeyValueStore | null,
  promptId: string,
  own: string | null,
): WritingTest | null {
  try {
    const raw = store?.getItem(TEST_KEY);
    if (!raw) return null;
    const t = JSON.parse(raw) as WritingTest & { own: string | null };
    if (t.prompt_id !== promptId || (t.own ?? null) !== (own ?? null))
      return null;
    return t;
  } catch {
    return null;
  }
}

export function saveTest(
  store: KeyValueStore | null,
  test: WritingTest,
  own: string | null,
): void {
  try {
    store?.setItem(TEST_KEY, JSON.stringify({ ...test, own }));
  } catch {
    // a reload then starts a new test
  }
}

export function clearTest(store: KeyValueStore | null): void {
  try {
    store?.setItem(TEST_KEY, "");
  } catch {
    // nothing to clear
  }
}
