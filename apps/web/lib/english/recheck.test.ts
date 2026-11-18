import { describe, expect, it } from "vitest";
import { DataError } from "@/lib/decode";
import { parseRecheck, parseRecheckResult } from "./recheck";

describe("FORGET-001 re-check decoding", () => {
  it("reads a question or none", () => {
    expect(parseRecheck({ question: null })).toBeNull();
    expect(
      parseRecheck({
        question: {
          id: "r1",
          node: "articles-basic",
          node_name_vi: "Mạo từ",
          prompt: "I saw ___ elephant.",
          options: ["a", "an"],
          draft: true,
        },
      }),
    ).toEqual({
      id: "r1",
      node: "articles-basic",
      nodeNameVi: "Mạo từ",
      prompt: "I saw ___ elephant.",
      options: ["a", "an"],
      draft: true,
    });
    expect(() => parseRecheck({ question: { id: "r1" } })).toThrow(DataError);
  });
  it("reads a result strictly", () => {
    expect(parseRecheckResult({ correct: false, key: "an" })).toEqual({
      correct: false,
      key: "an",
    });
    expect(() => parseRecheckResult({ correct: "no", key: "an" })).toThrow(
      DataError,
    );
  });
});
