"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { englishClient } from "@/lib/english/client";
import type { TextSummary } from "@/lib/reading/practice";
import { vi } from "@/messages/vi";
import { Problem } from "@/components/english/problem";
import { useLearner } from "@/components/english/use-learner";

const t = vi.english.readingPractice;

/** The texts with questions ready (specs/listening-reading/step-4.3.md). */
export function ReadingList() {
  const { learner, error: learnerError, retry } = useLearner();
  const [texts, setTexts] = useState<TextSummary[] | null>(null);
  const [error, setError] = useState<unknown>(null);
  useEffect(() => {
    if (!learner) return;
    let live = true;
    englishClient()
      .readingTexts(learner)
      .then((x) => live && setTexts(x))
      .catch((e: unknown) => live && setError(e));
    return () => {
      live = false;
    };
  }, [learner]);
  if (learnerError) return <Problem error={learnerError} onRetry={retry} />;
  if (error) return <Problem error={error} />;
  if (!texts) return <p className="en-muted">{vi.english.loading}</p>;
  return (
    <section className="en-card" data-testid="reading-list">
      <h1>{t.title}</h1>
      <p className="en-muted">{t.intro}</p>
      {texts.length === 0 ? (
        <p className="en-muted">{t.none}</p>
      ) : (
        <ul>
          {texts.map((x) => (
            <li key={x.slug}>
              <Link href={`/doc/${x.slug}`} lang="en">
                {x.title}
              </Link>{" "}
              <span className="en-muted">
                · {t.counts(x.questions, x.words)}
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
