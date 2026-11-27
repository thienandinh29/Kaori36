import { describe, expect, it } from "vitest";
import { DataError } from "@/lib/decode";
import { dayMark, parseWeek } from "./week";

const day = (date: string, answers: number, today = false, future = false) => ({
  date,
  answers,
  studied: answers > 0,
  today,
  future,
});
const body = {
  days: [
    day("2026-11-23", 4),
    day("2026-11-24", 0),
    day("2026-11-25", 0, true),
    day("2026-11-26", 0, false, true),
    day("2026-11-27", 0, false, true),
    day("2026-11-28", 0, false, true),
    day("2026-11-29", 0, false, true),
  ],
  studied_days: 1,
};

describe("the week's study days", () => {
  it("decodes seven days and the count", () => {
    const w = parseWeek(body);
    expect(w.studiedDays).toBe(1);
    expect(w.days.map(dayMark)).toEqual([
      "studied",
      "missed",
      "later", // today, nothing yet: still to come, not missed
      "later",
      "later",
      "later",
      "later",
    ]);
  });
  it("refuses a week that is not seven days", () => {
    expect(() => parseWeek({ ...body, days: body.days.slice(1) })).toThrow(
      DataError,
    );
    expect(() =>
      parseWeek({
        ...body,
        days: [{ ...body.days[0], studied: 1 }, ...body.days.slice(1)],
      }),
    ).toThrow(DataError);
  });
});
