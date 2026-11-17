import { describe, expect, it } from "vitest";
import { parseRecording, parseRecordings } from "./types";

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

  it("reads marks as target indexes", () => {
    expect(
      parseRecording({ ...row, failed: false, analysis: null, marks: [0, 3] })
        .marks,
    ).toEqual([0, 3]);
    expect(() =>
      parseRecording({ ...row, failed: false, analysis: null, marks: ["0"] }),
    ).toThrow();
  });
});
