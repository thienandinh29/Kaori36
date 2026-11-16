import { describe, expect, it } from "vitest";
import {
  MAX_SPEAK_CHARS,
  canSpeak,
  parseSpeechStatus,
  pickVoice,
  serverAudio,
  serverVoiceAvailable,
  speakable,
  type VoiceLike,
} from "./speech";

const v = (name: string, lang: string, localService = true): VoiceLike => ({
  name,
  lang,
  localService,
});

describe("pickVoice", () => {
  it("prefers British, then American, then any English", () => {
    const us = v("US", "en-US");
    const au = v("AU", "en-AU");
    const gb = v("GB", "en_GB");
    expect(pickVoice([au, us, gb], true)).toBe(gb);
    expect(pickVoice([au, us], true)).toBe(us);
    expect(pickVoice([au, v("FR", "fr-FR")], true)).toBe(au);
  });

  it("prefers an on-device voice of the same accent", () => {
    const net = v("Google UK", "en-GB", false);
    const local = v("Hazel", "en-GB", true);
    expect(pickVoice([net, local], true)).toBe(local);
  });

  it("refuses network voices for private text", () => {
    const net = v("Google UK", "en-GB", false);
    const localUs = v("David", "en-US", true);
    expect(pickVoice([net, localUs], false)).toBe(localUs);
    expect(pickVoice([net], false)).toBeNull();
    expect(pickVoice([net], true)).toBe(net);
  });

  it("returns null without any English voice", () => {
    expect(pickVoice([], true)).toBeNull();
    expect(pickVoice([v("VI", "vi-VN")], true)).toBeNull();
  });
});

describe("speakable", () => {
  it("normalises whitespace, quotes and Unicode", () => {
    expect(speakable("  “a  piece of\ncake”  ")).toBe("a piece of cake");
    expect(speakable("café")).toBe("café");
  });

  it("refuses empty, letterless and over-long text", () => {
    expect(speakable("   ")).toBeNull();
    expect(speakable("— 123 —")).toBeNull();
    expect(speakable("a".repeat(MAX_SPEAK_CHARS + 1))).toBeNull();
    expect(speakable("a".repeat(MAX_SPEAK_CHARS))).not.toBeNull();
  });
});

describe("canSpeak", () => {
  it("needs both speechSynthesis and SpeechSynthesisUtterance", () => {
    expect(canSpeak(undefined)).toBe(false);
    expect(canSpeak({})).toBe(false);
    expect(canSpeak({ speechSynthesis: {} })).toBe(false);
    expect(
      canSpeak({ speechSynthesis: {}, SpeechSynthesisUtterance: class {} }),
    ).toBe(true);
  });
});

describe("the server voice", () => {
  it("reads the status strictly", () => {
    expect(parseSpeechStatus({ available: true, voice: "v" })).toBe(true);
    expect(parseSpeechStatus({ available: false, voice: null })).toBe(false);
    expect(parseSpeechStatus({ available: "yes" })).toBe(false);
    expect(parseSpeechStatus(null)).toBe(false);
  });

  it("treats any failure as unavailable", async () => {
    const ok = async () =>
      new Response(JSON.stringify({ available: true, voice: "v" }));
    expect(await serverVoiceAvailable(ok)).toBe(true);
    const down = async () => new Response(null, { status: 502 });
    expect(await serverVoiceAvailable(down)).toBe(false);
    const broken = async (): Promise<Response> => {
      throw new TypeError("network");
    };
    expect(await serverVoiceAvailable(broken)).toBe(false);
  });

  it("returns audio only when the server sends WAV", async () => {
    let sent = "";
    const wav = async (_: RequestInfo | URL, init?: RequestInit) => {
      sent = String(init?.body);
      return new Response(new Uint8Array([82, 73, 70, 70]), {
        headers: { "content-type": "audio/wav" },
      });
    };
    const blob = await serverAudio("important", "slow", wav);
    expect(blob.size).toBe(4);
    expect(JSON.parse(sent)).toEqual({ text: "important", pace: "slow" });
    const json = async () => new Response("{}");
    await expect(serverAudio("important", "normal", json)).rejects.toThrow();
  });
});
