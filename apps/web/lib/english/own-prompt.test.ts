import { describe, expect, it } from "vitest";
import type { KeyValueStore } from "./learner";
import {
  OWN_ID,
  OWN_SLUG,
  clearTest,
  ownPrompt,
  promptIdFor,
  savedTest,
  saveOwnPrompt,
  saveTest,
} from "./own-prompt";
import type { WritingTest } from "./types";

function store(): KeyValueStore {
  const m = new Map<string, string>();
  return {
    getItem: (k) => m.get(k) ?? null,
    setItem: (k, v) => void m.set(k, v),
  };
}

const test: WritingTest = {
  id: "t1",
  prompt_id: OWN_ID,
  prompt: {
    id: OWN_ID,
    task: 2,
    type: "opinion",
    level: "B2",
    status: "draft",
    prompt: "Q?",
    figure: null,
  },
  started_at: "2026-11-21T03:00:00Z",
  time_limit_s: 2400,
};

describe("own question and exam storage (step 2.10)", () => {
  it("maps the page slug to the API id", () => {
    expect(promptIdFor(OWN_SLUG)).toBe(OWN_ID);
    expect(promptIdFor("t2-plastic-ban")).toBe("t2-plastic-ban");
  });

  it("keeps the question for the editor, and nothing blank", () => {
    const s = store();
    expect(ownPrompt(s)).toBeNull();
    saveOwnPrompt(s, "  ");
    expect(ownPrompt(s)).toBeNull();
    saveOwnPrompt(s, "Do you agree?");
    expect(ownPrompt(s)).toBe("Do you agree?");
    expect(ownPrompt(null)).toBeNull();
  });

  it("reuses a started exam only for the same prompt and question", () => {
    const s = store();
    saveTest(s, test, "Q?");
    expect(savedTest(s, OWN_ID, "Q?")?.id).toBe("t1");
    expect(savedTest(s, OWN_ID, "Another question?")).toBeNull();
    expect(savedTest(s, "t2-plastic-ban", null)).toBeNull();
    clearTest(s);
    expect(savedTest(s, OWN_ID, "Q?")).toBeNull();
  });

  it("survives broken storage", () => {
    const broken: KeyValueStore = {
      getItem: () => {
        throw new Error("blocked");
      },
      setItem: () => {
        throw new Error("blocked");
      },
    };
    expect(ownPrompt(broken)).toBeNull();
    expect(savedTest(broken, OWN_ID, null)).toBeNull();
    expect(() => saveTest(broken, test, null)).not.toThrow();
  });
});
