import type { KeyValueStore } from "./learner";
import type { WritingTest } from "./types";

/** The page slug for writing on the learner's own Task 2 question (specs/writing/step-2.10.md). */
export const OWN_SLUG = "de-cua-ban";
/** The API's prompt id for an own question. */
export const OWN_ID = "own";

const OWN_KEY = "nodetrail_own_prompt";
const TEST_KEY = "nodetrail_writing_test";

/** The prompt id the API expects for a page slug. */
export function promptIdFor(slug: string): string {
  return slug === OWN_SLUG ? OWN_ID : slug;
}

export function saveOwnPrompt(store: KeyValueStore | null, text: string): void {
  try {
    store?.setItem(OWN_KEY, text);
  } catch {
    // the editor then asks for the question again
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
