import { describe, expect, it } from "vitest";
import { DataError } from "@/lib/decode";
import {
  compareRows,
  parsePractice,
  parseStartedTry,
  pending,
  type Try,
} from "./practice";

const answer = (over: Record<string, unknown> = {}) => ({
  id: "a1",
  seconds: 40,
  problems: [],
  audio: true,
  delete_after: null,
  transcript: "done",
  text: "I think so.",
  words: [],
  measures: {
    words: 30,
    speaking_seconds: 20,
    short: false,
    speech_rate: 90,
    articulation_rate: 110,
    pauses: {
      count: 4,
      per_minute: 12,
      between_clauses: 3,
      inside_clause: 1,
      long: 0,
      longest_seconds: 1.1,
    },
    fillers: { count: 1 },
    longest_run: { words: 8, seconds: 4 },
    asked_seconds: 60,
    share_of_time: 0.33,
  },
  language: null,
  ...over,
});

const view = (tries: unknown[], over: Record<string, unknown> = {}) => ({
  id: "t1",
  keep: false,
  test_id: "t01",
  title: "Home",
  question: { id: "p3-1", part: 3, text: "Why?" },
  cue_card: null,
  theme: "travel",
  words: ["tourism", "traffic", "pollution", "crowded", "transport"],
  tries,
  max_tries: 3,
  next_seconds: 45,
  ...over,
});

const t = (n: number, a: unknown) => ({
  id: `t${n}`,
  try_no: n,
  asked_seconds: [60, 45, 30][n - 1],
  finished: true,
  counts_as_evidence: n === 1,
  answer: a,
});

describe("practice decoders", () => {
  it("reads a started try and a practice with its tries", () => {
    expect(
      parseStartedTry({ id: "s", keep: true, try_no: 2, asked_seconds: 45 }),
    ).toEqual({ id: "s", keep: true, try_no: 2, asked_seconds: 45 });
    const p = parsePractice(view([t(1, answer()), t(2, null)]));
    expect(p.tries.map((x) => x.try_no)).toEqual([1, 2]);
    expect(p.tries[0]?.counts_as_evidence).toBe(true);
    expect(p.tries[1]?.answer).toBeNull();
    expect(p.next_seconds).toBe(45);
    expect(p.words).toHaveLength(5);
  });

  it("reads a Part 2 cue card and no next try when the tries are used", () => {
    const p = parsePractice(
      view([t(1, answer()), t(2, answer()), t(3, answer())], {
        question: { id: "p2-long", part: 2, text: "Describe a journey." },
        cue_card: {
          task: "Describe a journey.",
          points: ["a", "b", "c"],
          explain: "and why.",
        },
        theme: null,
        next_seconds: null,
      }),
    );
    expect(p.cue_card?.points).toEqual(["a", "b", "c"]);
    expect(p.next_seconds).toBeNull();
    expect(p.theme).toBeNull();
  });

  it("refuses a repeat that counts as evidence, a bad part and a malformed answer", () => {
    const repeat = { ...t(2, answer()), counts_as_evidence: true };
    expect(() => parsePractice(view([t(1, answer()), repeat]))).toThrow(
      DataError,
    );
    expect(() =>
      parsePractice(
        view([t(1, answer())], { question: { id: "x", part: 4, text: "?" } }),
      ),
    ).toThrow(DataError);
    expect(() =>
      parsePractice(view([t(1, answer({ transcript: "done", text: null }))])),
    ).toThrow(DataError);
    expect(() => parsePractice(view([t(1, null)], { max_tries: "3" }))).toThrow(
      DataError,
    );
  });
});

describe("the numbers side by side", () => {
  const tries = (...a: unknown[]): Try[] =>
    parsePractice(view(a.map((x, i) => t(i + 1, x)))).tries;

  it("lists one value per try, in order, with no verdict", () => {
    const faster = answer({
      measures: {
        ...answer().measures,
        speech_rate: 120,
        pauses: { ...answer().measures.pauses, per_minute: 6 },
        longest_run: { words: 15, seconds: 7 },
        share_of_time: 0.8,
      },
    });
    const rows = compareRows(tries(answer(), faster));
    expect(rows.map((r) => r.key)).toEqual([
      "speechRate",
      "pausesPerMinute",
      "longestRun",
      "shareOfTime",
    ]);
    expect(rows[0]?.values).toEqual([90, 120]);
    expect(rows[1]?.values).toEqual([12, 6]);
    expect(rows[2]?.values).toEqual([8, 15]);
    expect(rows[3]?.values).toEqual([0.33, 0.8]);
    expect(JSON.stringify(rows)).not.toMatch(/better|worse|improv|score|band/i);
  });

  it("leaves a gap where a try has no numbers yet", () => {
    const waiting = answer({
      transcript: "waiting",
      text: null,
      measures: null,
    });
    const rows = compareRows(tries(answer(), waiting, null));
    expect(rows[0]?.values).toEqual([90, null, null]);
    const noWords = answer({
      measures: { ...answer().measures, words: 0, speech_rate: null },
    });
    expect(compareRows(tries(noWords))[0]?.values).toEqual([null]);
  });

  it("says when a try is still waiting for its transcript or numbers", () => {
    const waiting = answer({
      transcript: "waiting",
      text: null,
      measures: null,
    });
    const unmeasured = answer({ measures: null });
    expect(pending(tries(answer()))).toBe(false);
    expect(pending(tries(answer(), waiting))).toBe(true);
    expect(pending(tries(unmeasured))).toBe(true);
    expect(
      pending(
        tries(answer({ transcript: "none", text: null, measures: null })),
      ),
    ).toBe(false);
    expect(pending(tries(null))).toBe(false);
  });
});
