import { describe, expect, it } from "vitest";
import { DataError } from "@/lib/decode";
import { encodeWav, resample, toMono, toServerWav } from "./wav";
import { parseRecordingResult } from "./types";

describe("browser recording to server WAV", () => {
  it("mixes channels to mono", () => {
    expect(
      Array.from(toMono([new Float32Array([1, 0]), new Float32Array([0, 1])])),
    ).toEqual([0.5, 0.5]);
  });
  it("resamples 48 kHz to 16 kHz by averaging", () => {
    const out = resample(
      new Float32Array([0.3, 0.3, 0.3, 0.6, 0.6, 0.6]),
      48000,
      16000,
    );
    expect(out).toHaveLength(2);
    expect(out[0]).toBeCloseTo(0.3);
    expect(out[1]).toBeCloseTo(0.6);
  });
  it("writes a 16 kHz mono 16-bit PCM header and clips samples", () => {
    const buf = encodeWav(new Float32Array([0, 1, -1, 2]));
    const v = new DataView(buf);
    expect(String.fromCharCode(...new Uint8Array(buf, 0, 4))).toBe("RIFF");
    expect([
      v.getUint16(22, true),
      v.getUint32(24, true),
      v.getUint16(34, true),
    ]).toEqual([1, 16000, 16]);
    expect(v.getUint32(40, true)).toBe(8);
    expect([
      v.getInt16(46, true),
      v.getInt16(48, true),
      v.getInt16(50, true),
    ]).toEqual([32767, -32768, 32767]);
  });
  it("cuts a recording at 15 seconds", () => {
    const wav = toServerWav([new Float32Array(16000 * 20)], 16000);
    expect(new DataView(wav).getUint32(40, true)).toBe(16000 * 15 * 2);
  });
  it("decodes the quality result strictly", () => {
    expect(
      parseRecordingResult({
        quality: { ok: false, problems: ["too_noisy"] },
        id: null,
        delete_after: null,
      }).problems,
    ).toEqual(["too_noisy"]);
    expect(() =>
      parseRecordingResult({
        quality: { ok: false, problems: ["bad_accent"] },
        id: null,
      }),
    ).toThrow(DataError);
  });
});
