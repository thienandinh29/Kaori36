"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { englishClient } from "@/lib/english/client";
import type { Estimate, Maps } from "@/lib/english/maps";
import { vi } from "@/messages/vi";
import { Problem } from "./problem";
import { useLearner } from "./use-learner";

const t = vi.english.maps;

function Bar({ e }: { e: Estimate }) {
  const pct = e.p === null ? 0 : Math.round(e.p * 100);
  return (
    <span className={`en-mapbar is-${e.status}`} aria-hidden="true">
      <span style={{ width: `${pct}%` }} />
    </span>
  );
}

function Status({ e, unit }: { e: Estimate; unit: string }) {
  return (
    <span className={`en-badge map-${e.status}`}>
      {t.status[e.status]}
      {e.p !== null &&
        e.status !== "unmeasured" &&
        ` · ${Math.round(e.p * 100)}%`}
      {e.evidence > 0 && ` · ${t.basedOn(e.evidence, unit)}`}
    </span>
  );
}

/** Both maps: each IELTS competency with the foundations under it (specs/two-layer-map, M4). */
export function TwoMaps() {
  const { learner, error: learnerError, retry } = useLearner();
  const [maps, setMaps] = useState<Maps | null>(null);
  const [error, setError] = useState<unknown>(null);
  useEffect(() => {
    if (!learner) return;
    let live = true;
    englishClient()
      .maps(learner)
      .then((m) => live && setMaps(m))
      .catch((e: unknown) => live && setError(e));
    return () => {
      live = false;
    };
  }, [learner]);
  if (learnerError) return <Problem error={learnerError} onRetry={retry} />;
  if (error) return <Problem error={error} />;
  if (!maps) return <p className="en-muted">{vi.english.loading}</p>;
  return (
    <section className="en-card" data-testid="two-maps">
      <h1>{t.title}</h1>
      <p className="en-muted">{t.intro(maps.minEvidence)}</p>
      {maps.target.linksStatus === "proposed" && (
        <p className="en-muted">{t.proposed}</p>
      )}
      {maps.skills.map((s) => (
        <section key={s.skill} className="en-mapskill">
          <h2>{t.skills[s.skill] ?? s.skill}</h2>
          {s.competencies.map((c) => (
            <article
              key={c.slug}
              className="en-mapcomp"
              data-testid={`comp-${c.slug}`}
            >
              <h3>{c.nameVi}</h3>
              <Bar e={c} />
              <Status e={c} unit={t.essays} />
              {!c.available && <p className="en-muted">{t.notYet}</p>}
              <ul className="en-mapfound">
                {c.links.map((f) => (
                  <li key={f.node}>
                    <span className="en-muted">{t.kinds[f.kind]}</span>{" "}
                    {f.href ? (
                      <Link href={f.href}>{f.nameVi}</Link>
                    ) : (
                      <span>{f.nameVi}</span>
                    )}{" "}
                    {f.live ? (
                      <>
                        <Bar e={f} />
                        <Status e={f} unit={t.answers} />
                      </>
                    ) : (
                      <span className="en-badge draft">{t.notLive}</span>
                    )}
                  </li>
                ))}
              </ul>
            </article>
          ))}
        </section>
      ))}
    </section>
  );
}
