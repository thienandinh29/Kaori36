import { describe, expect, it } from "vitest";
import { parsePrompts, parseRecording, parseRecordings } from "./types";

const row = {
  id: "r1",
  prompt_id: "p01",
  keep: false,
  seconds: 2.4,
  status: "stored",
  created_at: "2026-11-17T09:00:00+00:00",
  delete_after: "2026-11-18T09:00:00+00:00",
};

describe("pronunciation decoders (step 3.3a)", () => {
  it("reads a recording's raw scores and keeps a missing competitor as null", () => {
    const d = parseRecording({
      ...row,
      status: "analysed",
      failed: false,
      analysis: {
        recognised: ["aɪ"],
        targets: [
          {
            sound: "final-t",
            word: "put",
            phone: "t",
            gop: -1.25,
            competitor: null,
            start_ms: 300,
            end_ms: 360,
          },
        ],
      },
    });
    expect(d.targets).toEqual([
      {
        sound: "final-t",
        word: "put",
        phone: "t",
        gop: -1.25,
        competitor: null,
        start_ms: 300,
        end_ms: 360,
      },
    ]);
    expect(d.labels).toEqual({});
    expect(d.marks).toEqual([]);
  });

  it("reads the owner's labels by target index and refuses unknown labels", () => {
    const base = { ...row, failed: false, analysis: null };
    expect(
      parseRecording({
        ...base,
        labels: [
          { target: 0, label: "wrong" },
          { target: 2, label: "unsure" },
        ],
      }).labels,
    ).toEqual({ 0: "wrong", 2: "unsure" });
    expect(() =>
      parseRecording({ ...base, labels: [{ target: 0, label: "maybe" }] }),
    ).toThrow();
  });

  it("gives no scores before analysis", () => {
    expect(
      parseRecording({ ...row, failed: false, analysis: null }).targets,
    ).toEqual([]);
  });

  it("refuses an unknown status or a non-numeric score", () => {
    expect(() => parseRecordings([{ ...row, status: "judged" }])).toThrow();
    expect(() =>
      parseRecording({
        ...row,
        status: "analysed",
        failed: false,
        analysis: {
          targets: [
            {
              sound: "x",
              word: "y",
              phone: "t",
              gop: "high",
              competitor: null,
            },
          ],
        },
      }),
    ).toThrow();
  });

  it("reads the not-sure sounds, none when absent (step 3.6a)", () => {
    const base = { ...row, failed: false, analysis: null };
    expect(parseRecording(base).unsure).toEqual([]);
    expect(parseRecording({ ...base, unsure: [1, 2] }).unsure).toEqual([1, 2]);
    expect(() => parseRecording({ ...base, unsure: ["1"] })).toThrow();
  });
  it("reads marks as target indexes", () => {
    expect(
      parseRecording({ ...row, failed: false, analysis: null, marks: [0, 3] })
        .marks,
    ).toEqual([0, 3]);
    expect(() =>
      parseRecording({ ...row, failed: false, analysis: null, marks: ["0"] }),
    ).toThrow();
  });

  it("reads pronunciation progress, with no data as null", () => {
    const d = parsePrompts({
      can_record: true,
      consent: "voice-v1",
      sounds: [],
      prompts: [],
      progress: [
        {
          node: "th",
          name_vi: "Âm th",
          p_known: null,
          known: false,
          measured: false,
        },
        {
          node: "final-consonants",
          name_vi: "Phụ âm cuối",
          p_known: 0.41,
          known: false,
          measured: true,
        },
      ],
    });
    expect(d.progress.map((n) => [n.node, n.p_known, n.measured])).toEqual([
      ["th", null, false],
      ["final-consonants", 0.41, true],
    ]);
  });
});
