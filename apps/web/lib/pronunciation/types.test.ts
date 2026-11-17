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
      },
    ]);
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
});
