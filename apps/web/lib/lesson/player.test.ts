import { describe, expect, it } from "vitest";
import { DataError } from "@/lib/decode";
import { parseAction, parseCheckpointResult, parseLesson } from "./decode";
import {
  initial,
  marks,
  nextStop,
  reduce,
  screenAt,
  steps,
  subtitleDefaults,
  timeX,
} from "./player";
import type { LessonView } from "./types";

const raw = {
  node: "present-perfect-vs-past",
  course: "english-ielts",
  level: "B1",
  status: "sample",
  title_en: "T",
  title_vi: "T",
  noncommercial: false,
  sources: [],
  scenes: [
    {
      id: "notice",
      kind: "notice",
      misconceptions: [],
      actions: [
        {
          do: "show_example",
          id: "a",
          en: "I lived in Hue.",
          vi: "x",
          target: "lived",
        },
        { do: "say", en: "Look.", vi: "Nhìn." },
        { do: "spotlight", example: "a" },
        {
          do: "board_timeline",
          points: [],
          spans: [{ label: "Hue", start: -4, end: -2, open: false }],
        },
        { do: "pause" },
      ],
    },
    {
      id: "check",
      kind: "activate",
      misconceptions: ["past-simple-with-since"],
      actions: [
        { do: "board_clear" },
        { do: "ask", checkpoint: "c1" },
        { do: "say", en: "Done.", vi: "Xong." },
      ],
    },
  ],
  checkpoints: [
    { id: "c1", en: "Still true?", vi: "Còn đúng?", options: ["Yes", "No"] },
  ],
};
const lesson: LessonView = parseLesson(raw);

describe("decoding", () => {
  it("reads every action and refuses unknown ones and leaked keys", () => {
    expect(steps(lesson)).toHaveLength(8);
    expect(() => parseAction({ do: "dance" })).toThrow(DataError);
    expect(() =>
      parseLesson({
        ...raw,
        checkpoints: [{ ...raw.checkpoints[0], correct: "Yes" }],
      }),
    ).toThrow(DataError);
    expect(() => parseLesson({ ...raw, checkpoints: [] })).toThrow(DataError); // ask without checkpoint
    expect(() => parseLesson({ ...raw, level: "D1" })).toThrow(DataError);
    expect(
      parseCheckpointResult({
        correct: false,
        key: "Yes",
        explain_vi: "x",
        misconception_vi: null,
      }).misconception_vi,
    ).toBeNull();
  });
});

describe("playback", () => {
  it("stops only where the learner listens, thinks or answers", () => {
    let s = reduce(lesson, initial(), { type: "start" });
    expect(s).toEqual({ status: "playing", index: 1 }); // the example appeared, Sena speaks
    expect(screenAt(lesson, s.index).examples.map((e) => e.id)).toEqual(["a"]);
    s = reduce(lesson, s, { type: "next" });
    const at = screenAt(lesson, s.index);
    expect(at.pause && at.spotlight === "a" && at.board.length === 1).toBe(
      true,
    );
    s = reduce(lesson, s, { type: "next" });
    const ask = screenAt(lesson, s.index);
    expect(ask.ask).toBe("c1");
    expect(ask.board).toEqual([]); // cleared
    expect(ask.examples).toEqual([]); // a new scene
    expect(ask.subtitle).toBeNull(); // the question card replaces the last words
    s = reduce(lesson, s, { type: "next" });
    s = reduce(lesson, s, { type: "next" });
    expect(s.status).toBe("done");
  });

  it("goes back a stop, pauses, resumes and jumps to a scene", () => {
    let s = reduce(lesson, initial(), { type: "start" });
    s = reduce(lesson, s, { type: "next" });
    expect(reduce(lesson, s, { type: "previous" }).index).toBe(1);
    const paused = reduce(lesson, s, { type: "pause" });
    expect(paused.status).toBe("paused");
    expect(reduce(lesson, paused, { type: "resume" }).status).toBe("playing");
    expect(reduce(lesson, s, { type: "scene", id: "check" }).index).toBe(
      nextStop(lesson, 5),
    );
  });
});

describe("subtitles and the board", () => {
  it("defaults by level: Vietnamese only at A1, both above", () => {
    expect(subtitleDefaults("A1")).toEqual({ en: false, vi: true });
    expect(subtitleDefaults("B1")).toEqual({ en: true, vi: true });
  });
  it("marks target phrases as whole words in any case", () => {
    expect(
      marks("She has lived here; Has lived?", ["has lived"]).filter(
        (m) => m.mark,
      ),
    ).toHaveLength(2);
    expect(marks("unlived", ["lived"])).toEqual([
      { text: "unlived", mark: false },
    ]);
  });
  it("places times on the timeline from past to future", () => {
    expect([timeX(-4), timeX(0), timeX(4), timeX(9)]).toEqual([0, 0.5, 1, 1]);
  });
});
