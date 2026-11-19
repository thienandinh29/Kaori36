import { describe, expect, it } from "vitest";
import { DataError } from "@/lib/decode";
import { closeness, parseSayResult, parseSayStatus } from "./say-word";

describe("saying a word (step 3.7)", () => {
  it("reads the status and a result with a dropped sound", () => {
    expect(
      parseSayStatus({ analysis: true, owner: true, consent: "voice-v1" }),
    ).toEqual({ analysis: true, owner: true, consent: "voice-v1" });
    const r = parseSayResult({
      ok: true,
      problems: [],
      phones: [
        { phone: "tʃ", gop: -0.1, heard: null, dropped: false },
        { phone: "z", gop: -7, heard: "s", dropped: true },
      ],
      heard: ["tʃ", "uː", "s"],
    });
    expect(r.phones[1]).toEqual({
      phone: "z",
      gop: -7,
      heard: "s",
      dropped: true,
    });
    expect(
      parseSayResult({ ok: false, problems: ["too_quiet"], phones: [] }),
    ).toMatchObject({ ok: false, heard: [] });
    expect(() =>
      parseSayResult({ ok: true, problems: [], phones: [{}] }),
    ).toThrow(DataError);
  });

  it("turns a raw score into a 0-100 closeness, never a mark", () => {
    expect(closeness(0)).toBe(100);
    expect(closeness(-3)).toBe(37);
    expect(closeness(-30)).toBe(0);
    expect(closeness(2)).toBe(100);
  });
});
