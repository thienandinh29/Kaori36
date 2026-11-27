"use client";
import { useEffect, useState } from "react";
import { englishClient } from "@/lib/english/client";
import { dayMark, type StudyWeek } from "@/lib/english/week";
import { vi } from "@/messages/vi";

const t = vi.english.week;

/**
 * This week's study days (specs/two-layer-map/step-m5.md): a calendar, never a streak.
 * Nothing counts days in a row, nothing is lost by missing a day, and Sena says nothing here.
 */
export function WeekStrip({ learner }: { learner: string }) {
  const [week, setWeek] = useState<StudyWeek | null>(null);
  useEffect(() => {
    let live = true;
    englishClient()
      .week(learner)
      .then((w) => live && setWeek(w))
      .catch(() => undefined); // optional: the rest of the home page still works
    return () => {
      live = false;
    };
  }, [learner]);
  if (!week) return null;
  return (
    <section className="en-card en-week" data-testid="week-strip">
      <ol className="en-week-days" aria-label={t.label}>
        {week.days.map((d, i) => {
          const mark = dayMark(d);
          const state =
            mark === "studied"
              ? t.studied(d.answers)
              : mark === "missed"
                ? t.missed
                : t.later;
          return (
            <li
              key={d.date}
              className={`en-week-day is-${mark}${d.today ? " is-today" : ""}`}
              aria-current={d.today ? "date" : undefined}
            >
              <span className="en-week-name">{t.days[i]}</span>
              <span
                className="en-week-mark"
                aria-label={`${t.days[i]}: ${state}${d.today ? `, ${t.today}` : ""}`}
                role="img"
              >
                {mark === "studied" ? "✓" : ""}
              </span>
            </li>
          );
        })}
      </ol>
      <p className="en-week-count">{t.count(week.studiedDays)}</p>
    </section>
  );
}
