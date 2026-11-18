"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { englishClient } from "@/lib/english/client";
import type { Today } from "@/lib/english/today";
import { vi } from "@/messages/vi";
import { TraceNote } from "./trace-note";

const t = vi.english.today;

/**
 * "Hôm nay": the recommendation engine's list for today (specs/two-layer-map/spec.md, M3).
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
  return (
    <section className="en-card" data-testid="today-list">
      <h2>{t.title}</h2>
      <p className="en-muted">
        {t.target(today.target.overall, today.target.examDate)}
      </p>
      <ol className="en-today">
        {today.activities.map((a) => (
          <li key={`${a.kind}:${a.target}`}>
            <span className="en-muted">{t.kinds[a.kind]}</span>{" "}
            <strong>{a.nameVi}</strong>
            {a.via && (
              <span className="en-muted">
                {" "}
                · {t.via} {today.names[a.via] ?? a.via}
              </span>
            )}{" "}
            <Link className="en-button small" href={a.href}>
              {t.go}
            </Link>
            <TraceNote trace={a.trace} names={today.names} />
          </li>
        ))}
      </ol>
      {today.target.linksStatus === "proposed" && (
        <p className="en-muted">{t.proposed}</p>
      )}
    </section>
  );
}
