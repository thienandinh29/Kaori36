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
      tests: [
        {
          id: "t01",
          title: "Home",
          draft: true,
          questions: 18,
          practice: [{ id: "p3-1", part: 3, text: "Why?", seconds: 60 }],
        },
      ],
      practices: [
        {
          id: "g1",
          title: "Home",
          question: "Why?",
          started_at: "2026-11-28T09:00:00+00:00",
          tries: 2,
        },
      ],
      max_tries: 3,
      left_today: { mock_tests: 2, practice_tries: 17 },
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
    expect(o.left_today).toEqual({ mock_tests: 2, practice_tries: 17 });
    expect(o.past[0]?.finished_at).toBeNull();
    expect(o.tests[0]?.practice[0]).toEqual({
      id: "p3-1",
      part: 3,
      text: "Why?",
      seconds: 60,
    });
    expect(o.practices[0]?.tries).toBe(2);
    expect(o.max_tries).toBe(3);
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

describe("measures (step 5.2)", () => {
  const measures = {
    words: 40,
    speaking_seconds: 20.5,
    short: false,
    speech_rate: 117.1,
    articulation_rate: 130.2,
    pauses: {
      count: 4,
      per_minute: 11.7,
      between_clauses: 3,
      inside_clause: 1,
      long: 0,
      longest_seconds: 1.2,
      total_seconds: 3.0,
      unplaced: 0,
    },
    fillers: { count: 2 },
    longest_run: { words: 12, seconds: 5.1 },
    asked_seconds: 40,
    share_of_time: 0.51,
  };
  const base = {
    id: "s1",
    test_id: "t01",
    title: "Home",
    keep: false,
    started_at: "2026-11-28T09:00:00+00:00",
    finished_at: "2026-11-28T09:14:00+00:00",
    cue_card: {
      task: "Describe a journey.",
      points: ["a", "b", "c"],
      explain: "and why.",
    },
    part3_theme: "travel",
  };
  const answer = (over: Record<string, unknown>) => ({
    ...base,
    questions: [
      {
        id: "p1-1-1",
        part: 1,
        text: "Q?",
        answer: {
          id: "a1",
          seconds: 20,
          problems: [],
          audio: true,
          delete_after: null,
          transcript: "done",
          text: "Um, I went home.",
          words: [],
          measures,
          ...over,
        },
      },
    ],
    summary: null,
  });

  it("reads the numbers and the pooled summary", () => {
    const r = parseResult({
      ...answer({}),
      summary: {
        answers: 1,
        words: 40,
        speaking_seconds: 20.5,
        speech_rate: 117.1,
        pauses_per_minute: 11.7,
        between_clauses: 3,
        inside_clause: 1,
        long: 0,
        fillers: 2,
        longest_run_words: 12,
      },
    });
    const m = r.questions[0]!.answer!.measures!;
    expect(m.pauses.between_clauses).toBe(3);
    expect(m.fillers).toBe(2);
    expect(m.longest_run).toEqual({ words: 12, seconds: 5.1 });
    expect(r.summary?.longest_run_words).toBe(12);
    expect("band" in m || "score" in m).toBe(false);
  });

  it("accepts an answer without measures and refuses measures without a transcript", () => {
    expect(
      parseResult(answer({ measures: null })).questions[0]!.answer!.measures,
    ).toBeNull();
    expect(
      parseResult({ ...answer({ measures: undefined }) }).questions[0]!.answer!
        .measures,
    ).toBeNull();
    expect(() =>
      parseResult(answer({ transcript: "waiting", text: null })),
    ).toThrow(DataError);
  });

  it("refuses a malformed number", () => {
    expect(() =>
      parseResult(answer({ measures: { ...measures, speech_rate: "fast" } })),
    ).toThrow(DataError);
    expect(() =>
      parseResult(answer({ measures: { ...measures, fillers: 2 } })),
    ).toThrow(DataError);
  });

  it("keeps a null rate for an answer with no words", () => {
    const empty = {
      ...measures,
      words: 0,
      speech_rate: null,
      articulation_rate: null,
      short: true,
    };
    expect(
      parseResult(answer({ measures: empty })).questions[0]!.answer!.measures!
        .speech_rate,
    ).toBeNull();
  });
});

describe("language checks (step 5.3a)", () => {
  const checked = {
    skipped: null,
    guard: {
      templates: ["in this day and age"],
      template_words: 5,
      repeated_words: 0,
      repeated_sentences: [],
      prompt_overlap: 0.4,
      off_topic: false,
    },
    vocabulary: {
      words: 60,
      mtld: 48.2,
      beyond_b1_share: 0.1,
      unknown_share: 0.02,
      repeated: [{ word: "people", count: 4 }],
    },
    hints: [
      {
        kind: "ending",
        text: "cat",
        suggestion: "cats",
        message_en: "m",
        rule_id: "R",
        errant_type: null,
        start_s: 2.2,
        end_s: 2.8,
      },
      {
        kind: "grammar",
        text: "have",
        suggestion: "has",
        message_en: "Use has.",
        rule_id: "R",
        errant_type: "R:VERB:SVA",
        start_s: null,
        end_s: null,
      },
    ],
  };
  const withLanguage = (
    language: unknown,
    transcript = "done",
    text: string | null = "x",
  ) =>
    parseResult({
      id: "s1",
      test_id: "t01",
      title: "Home",
      keep: false,
      started_at: "2026-11-28T09:00:00+00:00",
      finished_at: null,
      cue_card: {
        task: "Describe a journey.",
        points: ["a", "b", "c"],
        explain: "and why.",
      },
      part3_theme: "travel",
      questions: [
        {
          id: "p1-1-1",
          part: 1,
          text: "Q?",
          answer: {
            id: "a1",
            seconds: 20,
            problems: [],
            audio: true,
            delete_after: null,
            transcript,
            text,
            words: [],
            measures: null,
            language,
          },
        },
      ],
      summary: null,
    }).questions[0]!.answer!.language;

  it("reads the checks, the hints and an ending apart from grammar", () => {
    const l = withLanguage(checked);
    expect(l?.state).toBe("checked");
    if (l?.state !== "checked") return;
    expect(l.guard.templates).toEqual(["in this day and age"]);
    expect(l.vocabulary.mtld).toBe(48.2);
    expect(l.hints?.map((h) => h.kind)).toEqual(["ending", "grammar"]);
    expect(l.hints?.[1]?.start_s).toBeNull();
  });

  it("reads short, failed and not-checked, and a LanguageTool that was not configured", () => {
    expect(withLanguage({ skipped: "short" })?.state).toBe("short");
    expect(withLanguage({ failed: "ValueError: x" })?.state).toBe("failed");
    expect(withLanguage(null)).toBeNull();
    const none = withLanguage({ ...checked, hints: null });
    expect(none?.state === "checked" && none.hints).toBeNull();
  });

  it("refuses an unknown kind, an unknown skip reason and checks without a transcript", () => {
    const bad = { ...checked, hints: [{ ...checked.hints[0], kind: "error" }] };
    expect(() => withLanguage(bad)).toThrow(DataError);
    expect(() => withLanguage({ skipped: "later" })).toThrow(DataError);
    expect(() => withLanguage(checked, "waiting", null)).toThrow(DataError);
    expect(() =>
      withLanguage({
        ...checked,
        vocabulary: { ...checked.vocabulary, words: "60" },
      }),
    ).toThrow(DataError);
  });
});
