import { describe, expect, it } from "vitest";
import { DataError } from "@/lib/decode";
import { inviteToken, parseJoined, parseLeftToday } from "./tester";

const joined = {
  learner_id: "11111111-1111-4111-8111-111111111111",
  label: "Mai",
  may_record: false,
  research_notice: "research-v1",
  research_consented: false,
};

describe("tester decoders", () => {
  it("reads who joined", () => {
    expect(parseJoined(joined)).toEqual(joined);
  });

  it("refuses a response that carries the session, or a malformed one", () => {
    expect(() => parseJoined({ ...joined, session: "x".repeat(43) })).toThrow(
      DataError,
    );
    expect(() => parseJoined({ ...joined, learner_id: "not-a-uuid" })).toThrow(
      DataError,
    );
    expect(() => parseJoined({ ...joined, may_record: "no" })).toThrow(
      DataError,
    );
    expect(() => parseJoined({ ...joined, label: 3 })).toThrow(DataError);
  });

  it("reads what is left today, and null for the owner", () => {
    expect(parseLeftToday({ mock_tests: 2, practice_tries: 17 })).toEqual({
      mock_tests: 2,
      practice_tries: 17,
    });
    expect(parseLeftToday(null)).toBeNull();
    expect(parseLeftToday(undefined)).toBeNull();
    expect(() => parseLeftToday({ mock_tests: -1, practice_tries: 3 })).toThrow(
      DataError,
    );
    expect(() =>
      parseLeftToday({ mock_tests: 1.5, practice_tries: 3 }),
    ).toThrow(DataError);
  });

  it("accepts only a 43-character URL-safe invite token", () => {
    const ok = "a".repeat(30) + "B_-0123456789".slice(0, 13);
    expect(inviteToken(ok)).toBe(ok);
    for (const bad of [
      "",
      "short",
      ok + "x",
      ok.slice(1) + "!",
      `${ok.slice(0, 42)}/`,
      "../x",
    ])
      expect(inviteToken(bad)).toBeNull();
  });
});
