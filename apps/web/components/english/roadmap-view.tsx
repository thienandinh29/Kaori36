"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { englishClient } from "@/lib/english/client";
import type { Roadmap } from "@/lib/english/types";
import { vi } from "@/messages/vi";
import { MilestonePanel } from "./milestone-panel";
import { Problem } from "./problem";
import { Skyline } from "./skyline";
import { TraceNote } from "./trace-note";
import { TrailMap } from "./trail-map";
import { useLearner } from "./use-learner";

const t = vi.english;

export function useRoadmap(): {
  roadmap: Roadmap | null;
  error: unknown;
  reload: () => void;
} {
  const { learner, error: learnerError, retry } = useLearner();
  const [roadmap, setRoadmap] = useState<Roadmap | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [version, setVersion] = useState(0);
  useEffect(() => {
    if (!learner) return;
    let live = true;
    englishClient()
      .roadmap(learner)
      .then((r) => {
        if (!live) return;
        setRoadmap(r);
        setError(null);
      })
      .catch((e: unknown) => live && setError(e));
    return () => {
      live = false;
    };
  }, [learner, version]);
  return {
    roadmap,
    error: learnerError ?? error,
    reload: learnerError ? retry : () => setVersion((n) => n + 1),
  };
}

/** The whole course as one graph (specs/ui-v2): trail map, skyline, and the chosen milestone's panel. */
export function RoadmapView() {
  const { roadmap, error, reload } = useRoadmap();
  const { learner } = useLearner();
  const [lessons, setLessons] = useState<string[]>([]);
  useEffect(() => {
    if (!learner) return;
    let live = true;
    englishClient()
      .lessons(learner)
      .then((ls) => live && setLessons(ls.map((l) => l.node)))
      .catch(() => undefined); // no lessons: the map works as before
    return () => {
      live = false;
    };
  }, [learner]);
  const [selected, setSelected] = useState<string | null>(null);
  const [sheetOpen, setSheetOpen] = useState(false);
  useEffect(() => {
    if (!sheetOpen) return;
    const onKey = (e: KeyboardEvent) =>
      e.key === "Escape" && setSheetOpen(false);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [sheetOpen]);
  if (error) return <Problem error={error} onRetry={reload} />;
  if (!roadmap) return <p className="en-muted">{t.loading}</p>;
  const names: Record<string, string> = {};
  const parent: Record<string, string> = {};
  roadmap.milestones.forEach((m) => {
    names[m.slug] = m.name_vi;
    m.hidden.forEach((h) => {
      names[h.slug] = h.name_vi;
      parent[h.slug] = m.slug;
    });
  });
  const here =
    (roadmap.learn_next && parent[roadmap.learn_next]) ??
    roadmap.next_milestone ??
    null;
  const current = selected ?? here;
  const chosen = roadmap.milestones.find((m) => m.slug === current) ?? null;
  const choose = (slug: string) => {
    setSelected(slug);
    setSheetOpen(true);
  };
  return (
    <div className="nt-roadmap">
      <div className="nt-rail">
        <h1>{t.roadmap.title}</h1>
        {!roadmap.level_test && (
          <p>
            {t.roadmap.noTest} <Link href="/kiem-tra">{t.nav.levelTest}</Link>
          </p>
        )}
        {roadmap.learn_next && (
          <section className="nt-next-card">
            <small>{t.roadmap.learnNext}</small>
            <h2>{names[roadmap.learn_next] ?? roadmap.learn_next}</h2>
            <Link
              className="nt-btn primary"
              href={`/on-tap/phan/${roadmap.learn_next}`}
            >
              {t.run.practiseNow}
            </Link>
            {roadmap.learn_next_trace && (
              <TraceNote trace={roadmap.learn_next_trace} names={names} />
            )}
          </section>
        )}
        <Skyline
          milestones={roadmap.milestones}
          selected={current}
          onSelect={choose}
        />
      </div>
      <section className="nt-map" aria-labelledby="nt-map-h">
        <h2 id="nt-map-h">{t.roadmap.mapTitle}</h2>
        <p className="nt-sub">{t.roadmap.mapHint}</p>
        <TrailMap
          milestones={roadmap.milestones}
          selected={current}
          here={here}
          onSelect={choose}
        />
      </section>
      <div
        className={`nt-scrim${sheetOpen ? " is-open" : ""}`}
        onClick={() => setSheetOpen(false)}
        aria-hidden="true"
      />
      <aside
        className={`nt-panel${sheetOpen ? " is-open" : ""}`}
        aria-live="polite"
      >
        {chosen ? (
          <MilestonePanel
            milestone={chosen}
            names={names}
            isNext={chosen.slug === roadmap.next_milestone}
            onClose={() => setSheetOpen(false)}
            lessons={lessons}
          />
        ) : (
          <p className="en-muted">{t.roadmap.pick}</p>
        )}
      </aside>
    </div>
  );
}
