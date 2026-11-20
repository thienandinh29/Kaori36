"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { englishClient } from "@/lib/english/client";
import type { ErrorPatterns as Patterns } from "@/lib/english/types";
import { vi } from "@/messages/vi";

const w = vi.english.writing;

/** "Lỗi bạn hay lặp lại": errors in two or more essays (specs/writing/step-2.8.md). */
export function ErrorPatterns({ learner }: { learner: string }) {
  const [data, setData] = useState<Patterns | null>(null);
  useEffect(() => {
    let live = true;
    englishClient()
      .errorPatterns(learner)
      .then((d) => live && setData(d))
      .catch(() => undefined); // an extra card: the page works without it
    return () => {
      live = false;
    };
  }, [learner]);
  if (!data || data.essays < 2) return null;
  return (
    <section className="en-card" data-testid="error-patterns">
      <h2>{w.patternsTitle}</h2>
      <p className="en-muted">
        {w.patternsNote
          .replace("{n}", String(data.essays))
          .replace("{d}", String(data.days))}
      </p>
      {data.patterns.length === 0 ? (
        <p>{w.patternsNone}</p>
      ) : (
        <ul className="en-fix-first">
          {data.patterns.map((p) => (
            <li key={p.key}>
              <strong>{p.name_vi ?? w.fixOtherError}</strong>{" "}
              <span className="en-badge">
                {w.patternsCount
                  .replace("{e}", String(p.errors))
                  .replace("{n}", String(p.essays))}
              </span>
              <p className="en-muted">
                {p.in_latest ? w.patternsStill : w.patternsNotLatest}
              </p>
              <q lang="en">{p.example}</q>
              {p.node && (
                <p>
                  <Link className="en-link" href={`/on-tap/phan/${p.node}`}>
                    {w.patternsPractise}
                  </Link>
                </p>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
