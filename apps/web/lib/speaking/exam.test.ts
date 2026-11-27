import { describe, expect, it } from "vitest";
import { DataError } from "@/lib/decode";
import {
  LINES,
  clock,
  cueText,
  examSpeed,
  ms,
  parseOverview,
  parseResult,
  parseSitting,
  progress,
  readingSeconds,
  script,
  voiceChunks,
  type ExamTest,
} from "./exam";

const q = (id: string, part: 1 | 2 | 3, seconds: number) => ({
  id,
  part,
  text: `Question ${id}?`,
  seconds,
});

const TEST: ExamTest = {
  id: "t01",
  title: "Home",
  draft: true,
  part1_topics: ["home", "music", "mornings"],
  cue_card: {
    task: "Describe a journey.",
    points: ["where", "how", "who"],
    explain: "and explain why.",
  },
  part3_theme: "travel",
  questions: [
    q("p1-1-1", 1, 40),
    q("p1-1-2", 1, 40),
    q("p1-2-1", 1, 40),
    q("p1-3-1", 1, 40),
    q("p2-long", 2, 120),
    q("p2-closing", 2, 30),
    q("p3-1", 3, 60),
    q("p3-2", 3, 60),
  ],
  timing: { part1: 40, prepare: 60, long_turn: 120, closing: 30, part3: 60 },
};

describe("the examiner's script", () => {
  it("asks every question once, in order, with the part 2 minute to prepare", () => {
    const steps = script(TEST);
    const asked = steps.flatMap((s) =>
      s.kind === "ask" ? [s.question.id] : [],
    );
    expect(asked).toEqual(TEST.questions.map((x) => x.id));
    const kinds = steps.map((s) => s.kind);
    expect(kinds[0]).toBe("say");
    expect(kinds.at(-1)).toBe("end");
    const cue = kinds.indexOf("cue");
    expect(kinds.slice(cue, cue + 4)).toEqual(["cue", "prepare", "say", "ask"]);
    const prep = steps.find((s) => s.kind === "prepare");
    expect(prep).toEqual({ kind: "prepare", part: 2, seconds: 60 });
  });

  it("introduces each Part 1 topic before its questions and does not re-read the cue card", () => {
    const steps = script(TEST);
    const music = steps.findIndex(
      (s) => s.kind === "say" && s.text === LINES.topic("music"),
    );
    const next = steps[music + 1];
    expect(next?.kind === "ask" && next.question.id).toBe("p1-2-1");
    const long = steps.find(
      (s) => s.kind === "ask" && s.question.id === "p2-long",
    );
    expect(long?.kind === "ask" && long.speak).toBe(false);
    expect(
      steps.some((s) => s.kind === "say" && s.text === LINES.part3("travel")),
    ).toBe(true);
  });

  it("refuses a test whose questions and topics disagree", () => {
    const missing = {
      ...TEST,
      questions: TEST.questions.filter((x) => x.id !== "p2-long"),
    };
    expect(() => script(missing)).toThrow(DataError);
    const orphan = {
      ...TEST,
      questions: [...TEST.questions, q("p1-4-1", 1, 40)],
    };
    expect(() => script(orphan)).toThrow(DataError);
  });

  it("reads the cue card with its points", () => {
    expect(cueText(TEST.cue_card)).toBe(
      "Describe a journey. You should say: where; how; who; and explain why.",
    );
  });

  it("says where the learner is", () => {
    const steps = script(TEST);
    expect(progress(steps, 0)).toEqual({ part: 1, question: 1, total: 8 });
    const p3 = steps.findIndex(
      (s) => s.kind === "ask" && s.question.id === "p3-1",
    );
    expect(progress(steps, p3)).toEqual({ part: 3, question: 7, total: 8 });
    expect(progress(steps, steps.length - 1).part).toBe(3);
  });
});

describe("timing", () => {
  it("runs in real time unless a test sets a valid speed", () => {
    expect(examSpeed(null)).toBe(1);
    expect(examSpeed("0.02")).toBe(0.02);
    for (const bad of ["0", "-1", "2", "fast", ""])
      expect(examSpeed(bad)).toBe(1);
    expect(ms(40, 1)).toBe(40_000);
    expect(ms(40, 0.01)).toBe(400);
    expect(ms(1, 0.01)).toBe(200); // never shorter than a fifth of a second
  });

  it("formats the clock and estimates reading time", () => {
    expect(clock(0)).toBe("0:00");
    expect(clock(65)).toBe("1:05");
    expect(clock(119.2)).toBe("2:00");
    expect(readingSeconds("one two")).toBe(2);
    expect(readingSeconds(Array(25).fill("w").join(" "))).toBe(10);
  });
});

describe("voice chunks", () => {
  it("keeps short lines whole and splits long ones at sentence ends", () => {
    expect(voiceChunks("Hello. How are you?")).toEqual(["Hello. How are you?"]);
    expect(voiceChunks("One two. Three four. Five.", 12)).toEqual([
      "One two.",
      "Three four.",
      "Five.",
    ]);
    expect(voiceChunks(LINES.part2).every((c) => c.length <= 300)).toBe(true);
    expect(voiceChunks("x".repeat(400))[0]).toHaveLength(300);
  });
});

describe("decoders", () => {
  it("reads a sitting and refuses a bad part", () => {
    const s = parseSitting({ id: "s1", keep: false, test: TEST });
    expect(s.test.questions).toHaveLength(8);
    const bad = { ...TEST, questions: [{ ...TEST.questions[0], part: 4 }] };
    expect(() => parseSitting({ id: "s1", keep: false, test: bad })).toThrow(
      DataError,
    );
  });

  it("reads the overview and a result with and without answers", () => {
    const o = parseOverview({
      can_record: true,
      consent: "voice-v1",
      tests: [{ id: "t01", title: "Home", draft: true, questions: 18 }],
      past: [
        {
          id: "s1",
          test_id: "t01",
          title: "Home",
          keep: false,
          started_at: "2026-11-27T09:00:00+00:00",
          finished_at: null,
          answers: 3,
          with_audio: 0,
        },
      ],
    });
    expect(o.past[0]?.finished_at).toBeNull();
    const r = parseResult({
      id: "s1",
      test_id: "t01",
      title: "Home",
      keep: true,
      started_at: "2026-11-27T09:00:00+00:00",
      finished_at: "2026-11-27T09:14:00+00:00",
      cue_card: TEST.cue_card,
      part3_theme: "travel",
      questions: [
        { id: "p1-1-1", part: 1, text: "Q?", answer: null },
        {
          id: "p1-1-2",
          part: 1,
          text: "Q2?",
          answer: {
            id: "a1",
            seconds: 12.5,
            problems: ["too_quiet"],
            audio: true,
            delete_after: null,
            transcript: "done",
            text: "Um, I goes",
            words: [{ word: "Um,", start: 0.5, end: 0.9 }],
          },
        },
      ],
    });
    expect(r.questions[1]?.answer?.problems).toEqual(["too_quiet"]);
    expect(r.questions[1]?.answer?.text).toBe("Um, I goes");
    // a "done" transcript without text, or text while waiting, is refused
    const answered = (transcript: string, text: string | null) => ({
      ...r,
      questions: [
        {
          id: "p1-1-2",
          part: 1,
          text: "Q2?",
          answer: { ...r.questions[1]!.answer!, transcript, text },
        },
      ],
    });
    expect(() => parseResult(answered("done", null))).toThrow(DataError);
    expect(() => parseResult(answered("waiting", "x"))).toThrow(DataError);
    expect(() => parseResult(answered("later", null))).toThrow(DataError);
    expect(
      parseResult(answered("waiting", null)).questions[0]?.answer?.transcript,
    ).toBe("waiting");
    expect(() =>
      parseResult({ ...r, questions: [{ id: "x", part: 1, text: "Q" }] }),
    ).toThrow(DataError);
  });
});
