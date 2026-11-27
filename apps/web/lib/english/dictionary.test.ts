import { describe, expect, it } from "vitest";
import { DataError } from "@/lib/decode";
import { dictionaryQuery, parseDictionary } from "./dictionary";

const card = {
  key: "table:noun",
  lemma: "table",
  pos: "noun",
  level: "A1",
  ipa: "/ˈteɪbəl/",
  origin: "ngsl",
  definition: "a piece of furniture with a flat top",
  vi: "cái bàn",
  example: "Put the book on the table.",
};

describe("dictionary search", () => {
  it("decodes the cards and the draft status", () => {
    const d = parseDictionary({ status: "draft", total: 3, results: [card] });
    expect(d.draft).toBe(true);
    expect(d.total).toBe(3);
    expect(d.results[0].lemma).toBe("table");
  });
  it("refuses an unknown status or a broken card", () => {
    expect(() =>
      parseDictionary({ status: "x", total: 0, results: [] }),
    ).toThrow(DataError);
    expect(() =>
      parseDictionary({
        status: "draft",
        total: 1,
        results: [{ ...card, ipa: "no slashes" }],
      }),
    ).toThrow(DataError);
  });
  it("cleans the query", () => {
    expect(dictionaryQuery("  cái   bàn ")).toBe("cái bàn");
    expect(dictionaryQuery("   ")).toBe("");
    expect(dictionaryQuery("a".repeat(60))).toHaveLength(40);
  });
});
