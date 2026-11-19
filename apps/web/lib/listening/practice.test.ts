import { describe, expect, it } from "vitest";
import { DataError } from "@/lib/decode";
import {
  parseListeningResult,
  parseListeningText,
  parseListeningTexts,
  percent,
} from "./practice";

const trace = {
  kind: "bkt_update",
  concept_slug: "listening-dictation",
  at: "2026-11-20T09:00:00Z",
  prior: 0.2,
  posterior: 0.5,
  evidence: {},
  rule: "listening.answer",
  rule_vi: "Nghe chép chính tả: đúng",
  alternatives: [],
};

describe("listening decoders (step 4.4b)", () => {
  it("reads the texts and whether the voice is on", () => {
    expect(
      parseListeningTexts({
        available: true,
        texts: [{ slug: "bees", title: "Honey bees", dictation: 2, gaps: 1 }],
      }),
    ).toEqual({
      available: true,
      texts: [{ slug: "bees", title: "Honey bees", dictation: 2, gaps: 1 }],
    });
    expect(parseListeningTexts({ available: false, texts: [] }).available).toBe(
      false,
    );
    expect(() => parseListeningTexts({ texts: [] })).toThrow(DataError);
  });

  it("keeps dictation without text and requires a gap's prompt", () => {
    const text = parseListeningText({
      slug: "bees",
      title: "Honey bees",
      items: [
        { id: "bees-dictation-1", kind: "dictation", prompt: null },
        { id: "bees-gap-1", kind: "gap", prompt: "Bees ___ nectar." },
      ],
    });
    expect(text.items.map((i) => i.prompt)).toEqual([null, "Bees ___ nectar."]);
    expect(() =>
      parseListeningText({
        slug: "b",
        title: "B",
        items: [{ id: "b-gap-1", kind: "gap", prompt: null }],
      }),
    ).toThrow(DataError);
    expect(() =>
      parseListeningText({
        slug: "b",
        title: "B",
        items: [{ id: "b-x-1", kind: "essay", prompt: null }],
      }),
    ).toThrow(DataError);
  });

  it("reads a marked dictation and refuses unknown word marks", () => {
    const result = {
      correct: false,
      score: 0.8,
      key: "Bees live in hives.",
      sentence: "Bees live in hives.",
      words: [
        { word: "bees", status: "right" },
        { word: "hives", status: "missed" },
      ],
      competency: "listening-dictation",
      trace,
    };
    const r = parseListeningResult(result);
    expect(r.words[1]).toEqual({ word: "hives", status: "missed" });
    expect(percent(r.score)).toBe(80);
    expect(() =>
      parseListeningResult({
        ...result,
        words: [{ word: "x", status: "maybe" }],
      }),
    ).toThrow(DataError);
    expect(() => parseListeningResult({ ...result, score: 2 })).toThrow(
      DataError,
    );
  });
});
