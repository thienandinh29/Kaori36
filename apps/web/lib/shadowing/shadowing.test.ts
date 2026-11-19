import { describe, expect, it } from "vitest";
import { paceRatio, timing } from "./measure";
import { clock, loopSpan, videoId } from "./youtube";

const RATE = 1000;
/** Tone (amplitude 0.5) and silence segments in seconds. */
function signal(parts: [boolean, number][]): Float32Array {
  const out: number[] = [];
  for (const [voiced, seconds] of parts)
    for (let i = 0; i < seconds * RATE; i++)
      out.push(voiced ? 0.5 * Math.sin(i / 3) : 0);
  return Float32Array.from(out);
}

describe("shadowing timing (step 4.4d)", () => {
  it("trims silence at both ends and counts pauses inside", () => {
    const t = timing(
      signal([
        [false, 0.5],
        [true, 1],
        [false, 0.4],
        [true, 1],
        [false, 0.1],
        [true, 0.5],
        [false, 1],
      ]),
      RATE,
    );
    expect(t.seconds).toBeCloseTo(3, 1);
    expect(t.pauses).toBe(1); // the 0.1 s gap is too short to be a pause
  });

  it("says nothing about silence and compares paces", () => {
    expect(timing(signal([[false, 2]]), RATE)).toEqual({
      seconds: 0,
      pauses: 0,
    });
    expect(
      paceRatio({ seconds: 3, pauses: 1 }, { seconds: 2, pauses: 0 }),
    ).toBe(1.5);
    expect(
      paceRatio({ seconds: 3, pauses: 0 }, { seconds: 0, pauses: 0 }),
    ).toBe(null);
  });
});

describe("YouTube links (step 4.4d)", () => {
  it.each([
    ["https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=42", "dQw4w9WgXcQ"],
    ["youtu.be/dQw4w9WgXcQ?si=abc", "dQw4w9WgXcQ"],
    ["https://m.youtube.com/shorts/dQw4w9WgXcQ", "dQw4w9WgXcQ"],
    ["https://www.youtube.com/embed/dQw4w9WgXcQ", "dQw4w9WgXcQ"],
    ["dQw4w9WgXcQ", "dQw4w9WgXcQ"],
  ])("reads %s", (link, id) => expect(videoId(link)).toBe(id));

  it.each([
    "https://evil.example/watch?v=dQw4w9WgXcQ",
    "https://www.youtube.com/watch?v=short",
    "javascript:alert(1)",
    "https://www.youtube.com/channel/UCabc",
    "",
  ])("refuses %s", (link) => expect(videoId(link)).toBeNull());

  it("orders a loop and refuses one too short", () => {
    expect(loopSpan(12, 5)).toEqual({ from: 5, to: 12 });
    expect(loopSpan(5, 5.2)).toBeNull();
    expect(loopSpan(null, 3)).toBeNull();
    expect(clock(75.9)).toBe("1:15");
  });
});
