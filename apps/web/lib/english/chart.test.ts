import { describe, expect, it } from "vitest";
import { DataError } from "@/lib/decode";
import {
  chartMax,
  formatValue,
  niceMax,
  pieSlices,
  slicePath,
  slot,
  yTicks,
} from "./chart";
import { parseEssay, parseWritingPrompt } from "./decode";
import type { ChartFigure } from "./types";

const LINE: ChartFigure = {
  title: "Internet",
  alt_vi: "Biểu đồ đường về internet.",
  chart_type: "line",
  categories: ["2000", "2010", "2020"],
  series: [
    { name: "A", values: [5, 40, 85] },
    { name: "B", values: [2, 22, 70] },
  ],
  unit: "%",
  x_label: "Year",
  y_label: "%",
};
const PIE: ChartFigure = {
  ...LINE,
  chart_type: "pie",
  categories: ["Housing", "Food", "Other"],
  series: [{ name: "Share", values: [50, 30, 20] }],
};

describe("chart geometry", () => {
  it("picks a round top for the axis", () => {
    expect([0, 3, 85, 120, 420, 1].map(niceMax)).toEqual([
      1, 5, 100, 200, 500, 1,
    ]);
    expect(chartMax(LINE)).toBe(100);
    expect(yTicks(100)).toEqual([0, 20, 40, 60, 80, 100]);
  });
  it("centres categories in their slots", () => {
    expect([0, 1, 2].map((i) => slot(i, 3, 300))).toEqual([50, 150, 250]);
  });
  it("turns a pie into slices that add up to a full circle", () => {
    const s = pieSlices(PIE);
    expect(s.map((x) => x.share)).toEqual([50, 30, 20]);
    expect(s[0].start).toBe(0);
    expect(s[2].end).toBeCloseTo(2 * Math.PI);
    expect(slicePath(s[0], 110, 110, 100)).toContain("A 100 100 0 0 1");
    const whole = pieSlices({
      ...PIE,
      series: [{ name: "x", values: [1, 0, 0] }],
    });
    expect(slicePath(whole[0], 110, 110, 100)).toContain("A 100 100 0 1 1");
  });
  it("formats values with their unit", () => {
    expect(formatValue(85, "%")).toBe("85%");
    expect(formatValue(12.5, "hours")).toBe("12.5 hours");
    expect(formatValue(3, "")).toBe("3");
  });
});

describe("Task 1 prompts and results", () => {
  const prompt = {
    id: "t1-x",
    task: 1,
    type: "chart",
    level: "B2",
    status: "draft",
    prompt: "The graph below shows internet access.",
    figure: LINE,
  };
  it("reads a chart prompt, and a Task 2 prompt without one", () => {
    expect(parseWritingPrompt(prompt).figure?.series).toHaveLength(2);
    const t2 = {
      ...prompt,
      id: "t2-x",
      task: 2,
      type: "opinion",
      figure: null,
    };
    expect(parseWritingPrompt(t2).figure).toBeNull();
    expect(parseWritingPrompt({ ...t2, figure: undefined }).figure).toBeNull();
  });
  it.each([
    ["a Task 1 prompt with no figure", { ...prompt, figure: null }],
    ["a Task 2 prompt with a figure", { ...prompt, task: 2 }],
    [
      "a series that is too short",
      { ...prompt, figure: { ...LINE, series: [{ name: "A", values: [1] }] } },
    ],
    [
      "an unknown chart type",
      { ...prompt, figure: { ...LINE, chart_type: "radar" } },
    ],
    [
      "a negative pie value",
      {
        ...prompt,
        figure: { ...PIE, series: [{ name: "s", values: [1, -1, 2] }] },
      },
    ],
    [
      "a value that is not a number",
      {
        ...prompt,
        figure: { ...LINE, series: [{ name: "A", values: [1, "x", 3] }] },
      },
    ],
  ])("rejects %s", (_, bad) => {
    expect(() => parseWritingPrompt(bad)).toThrow(DataError);
  });
  it("reads the checks the code made, and older results without them", () => {
    const base = {
      id: "0b9d2f4e-1c2a-4d3b-8e5f-6a7b8c9d0e1f",
      prompt: null,
      text: "x",
      status: "done",
      submitted_at: "2026-11-20T03:00:00Z",
      failure_vi: null,
      result: {
        words: 10,
        sentences: 1,
        paragraphs: 1,
        min_words: 150,
        long_enough: false,
        avg_sentence_words: 10,
        longest_sentence_words: 10,
        linking: {},
        linking_groups_used: 0,
        task: 1,
        task1: {
          numbers: [{ text: "90%", supported: false }],
          features: [
            {
              kind: "max",
              series: "A",
              category: "2020",
              text: "A peaks",
              covered: false,
            },
          ],
          overview: true,
        },
      },
    };
    const r = parseEssay(base).result;
    expect(r?.task).toBe(1);
    expect(r?.task1?.numbers[0]).toEqual({ text: "90%", supported: false });
    const old = {
      ...base,
      result: { ...base.result, task: undefined, task1: undefined },
    };
    expect(parseEssay(old).result?.task1).toBeUndefined();
  });
});
