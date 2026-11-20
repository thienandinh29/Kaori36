"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { englishClient } from "@/lib/english/client";
import type { PassageList } from "@/lib/listening/passages";
import type { ListeningTexts } from "@/lib/listening/practice";
import { vi } from "@/messages/vi";
import { Problem } from "@/components/english/problem";
import { useLearner } from "@/components/english/use-learner";

const t = vi.english.listening;
const p = vi.english.listeningPassage;

/** The texts with listening exercises (specs/listening-reading/step-4.4b.md). */
export function ListeningList() {
  const { learner, error: learnerError, retry } = useLearner();
  const [data, setData] = useState<ListeningTexts | null>(null);
  const [passages, setPassages] = useState<PassageList | null>(null);
  const [error, setError] = useState<unknown>(null);
  useEffect(() => {
    if (!learner) return;
    let live = true;
    englishClient()
      .listeningTexts(learner)
      .then((x) => live && setData(x))
      .catch((e: unknown) => live && setError(e));
    englishClient()
      .listeningPassages(learner)
      .then((x) => live && setPassages(x))
      .catch(() => undefined); // an extra list: dictation still works without it
    return () => {
      live = false;
    };
  }, [learner]);
  if (learnerError) return <Problem error={learnerError} onRetry={retry} />;
  if (error) return <Problem error={error} />;
  if (!data) return <p className="en-muted">{vi.english.loading}</p>;
  return (
    <section className="en-card" data-testid="listening-list">
      <h1>{t.title}</h1>
      <p className="en-muted">{t.intro}</p>
      {!data.available ? (
        <p className="en-feedback is-wrong">{t.noVoice}</p>
      ) : (
        <>
          {passages && passages.texts.length > 0 && (
            <div data-testid="listening-passages">
              <h2>{p.listTitle}</h2>
              <p className="en-muted">{p.listNote}</p>
              <ul>
                {passages.texts.map((x) => (
                  <li key={x.slug}>
                    <Link href={`/nghe/bai/${x.slug}`} lang="en">
                      {x.title}
                    </Link>{" "}
                    <span className="en-muted">
                      · {p.counts(x.questions)}
                      {x.readBefore && ` · ${p.readBefore}`}
                    </span>
                  </li>
                ))}
              </ul>
              <h2>{p.sentencesTitle}</h2>
            </div>
          )}
          {data.texts.length === 0 ? (
            <p className="en-muted">{t.none}</p>
          ) : (
            <>
              <p className="en-muted">{t.voiceNote}</p>
              <ul>
                {data.texts.map((x) => (
                  <li key={x.slug}>
                    <Link href={`/nghe/${x.slug}`} lang="en">
                      {x.title}
                    </Link>{" "}
                    <span className="en-muted">
                      · {t.counts(x.dictation, x.gaps)}
                    </span>
                  </li>
                ))}
              </ul>
            </>
          )}
        </>
      )}
    </section>
  );
}
