"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { englishClient } from "@/lib/english/client";
import type { Today } from "@/lib/english/today";
import { vi } from "@/messages/vi";
import { TraceNote } from "./trace-note";

const t = vi.english.today;

/**
 * "Hôm nay": the recommendation engine's list for today (specs/two-layer-map/spec.md, M3), fixed for
 * the day with what was practised today marked and a rough time per activity (step-m5.md).
 * Each activity has its reason ("Vì sao?"). Nothing here praises speed or streaks.
 */
export function TodayList({ learner }: { learner: string }) {
  const [today, setToday] = useState<Today | null>(null);
  useEffect(() => {
    let live = true;
    englishClient()
      .today(learner)
      .then((x) => live && setToday(x))
      .catch(() => undefined); // optional: the rest of the home page still works
    return () => {
      live = false;
    };
  }, [learner]);
  if (!today || today.activities.length === 0) return null;
  const total = today.activities.length;
  return (
    <section className="en-card" data-testid="today-list">
      <div className="en-today-head">
        <h2>{t.title}</h2>
        <span className="en-today-count" data-testid="today-count">
          {t.progress(today.doneCount, total)}
        </span>
      </div>
      <p className="en-muted">
        {t.target(today.target.overall, today.target.examDate)}
      </p>
      <ol className="en-today">
        {today.activities.map((a) => (
          <li
            key={`${a.kind}:${a.target}`}
            className={a.done ? "is-done" : undefined}
          >
            <span className="en-muted">{t.kinds[a.kind]}</span>{" "}
            <strong>{a.nameVi}</strong>
            {a.via && (
              <span className="en-muted">
                {" "}
                · {t.via} {today.names[a.via] ?? a.via}
              </span>
            )}{" "}
            <span className="en-today-meta">
              <span className="en-muted">{t.minutes(a.minutes)}</span>
              {a.done && <span className="en-today-done">{t.done}</span>}
            </span>{" "}
            <Link
              className={`en-button small${a.done ? " secondary" : ""}`}
              href={a.href}
            >
              {t.go}
            </Link>
            <TraceNote trace={a.trace} names={today.names} />
          </li>
        ))}
      </ol>
      {today.doneCount === total && <p>{t.allDone}</p>}
      <p className="en-muted">{t.fixed}</p>
      {today.target.linksStatus === "proposed" && (
        <p className="en-muted">{t.proposed}</p>
      )}
    </section>
  );
}
