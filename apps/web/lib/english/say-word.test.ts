import { describe, expect, it } from "vitest";
import { DataError } from "@/lib/decode";
import {
  closeness,
  hue,
  parseFocus,
  parseSayResult,
  parseSayStatus,
} from "./say-word";

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
    expect(r.phones[1]).toMatchObject({
      phone: "z",
      gop: -7,
      closeness: 10,
      heard: "s",
      dropped: true,
      how: null,
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

describe("guidance and focus (step 3.7b)", () => {
  it("reads a guide with its minimal pair, and the focus list", () => {
    const r = parseSayResult({
      ok: true,
      problems: [],
      phones: [
        {
          phone: "ɔː",
          gop: -1.5,
          closeness: 61,
          heard: "ɑː",
          dropped: false,
          how: "o dài",
        },
      ],
      heard: [],
      guide: [
        {
          index: 0,
          phone: "ɔː",
          times: 2,
          of: 3,
          heard: "ɑː",
          dropped: false,
          how: "o dài",
          change: "tròn môi",
          minimal: ["caught", "cart"],
        },
      ],
    });
    expect(r.phones[0]!.closeness).toBe(61);
    expect(r.guide[0]!.minimal).toEqual(["caught", "cart"]);
    expect(() =>
      parseSayResult({ ...r, guide: [{ ...r.guide[0], minimal: ["one"] }] }),
    ).toThrow(DataError);
    const f = parseFocus({
      days: 30,
      attempts: 5,
      sounds: [
        {
          phone: "θ",
          low: 3,
          seen: 4,
          share: 0.75,
          heard: "t",
          how: "lưỡi",
          example: "think",
        },
      ],
    });
    expect(f.sounds[0]).toMatchObject({ phone: "θ", heard: "t" });
  });

  it("colours red to green", () => {
    expect([hue(0), hue(50), hue(100), hue(140)]).toEqual([0, 60, 120, 120]);
  });
});
