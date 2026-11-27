// This week's study days (specs/two-layer-map/step-m5.md), decoded strictly. A calendar, never a streak.
import { DataError, record, string } from "@/lib/decode";

export interface StudyDay {
  date: string;
  answers: number;
  studied: boolean;
  today: boolean;
  future: boolean;
}
export interface StudyWeek {
  days: StudyDay[];
  studiedDays: number;
}

export function parseWeek(value: unknown): StudyWeek {
  const d = record(value);
  if (
    !Array.isArray(d.days) ||
    d.days.length !== 7 ||
    typeof d.studied_days !== "number"
  )
    throw new DataError("contract");
  return {
    days: d.days.map((v) => {
      const x = record(v);
      if (
        typeof x.answers !== "number" ||
        typeof x.studied !== "boolean" ||
        typeof x.today !== "boolean" ||
        typeof x.future !== "boolean"
      )
        throw new DataError("contract");
      return {
        date: string(x.date),
        answers: x.answers,
        studied: x.studied,
        today: x.today,
        future: x.future,
      };
    }),
    studiedDays: d.studied_days,
  };
}

/** How a day is drawn: studied (filled), missed (empty ring), to come (dot). */
export function dayMark(day: StudyDay): "studied" | "missed" | "later" {
  if (day.studied) return "studied";
  return day.future || day.today ? "later" : "missed";
}
