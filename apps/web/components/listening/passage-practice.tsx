"use client";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { englishClient } from "@/lib/english/client";
import {
  PASSAGE_PLAYS,
  passageAnswers,
  type PassageResult,
  type PassageView,
} from "@/lib/listening/passages";
import { paragraphsOf, type Answer } from "@/lib/reading/practice";
import { vi } from "@/messages/vi";
import { Problem } from "@/components/english/problem";
import { useLearner } from "@/components/english/use-learner";
import { Input, Prompt, shown } from "@/components/reading/reading-test";

const t = vi.english.listeningPassage;

/** Listen to a whole passage, answer its approved questions, then read it (step 4.4c). */
export function PassagePractice({ slug }: { slug: string }) {
  const { learner, error: learnerError, retry } = useLearner();
  const [view, setView] = useState<PassageView | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [given, setGiven] = useState<Record<string, Answer>>({});
  const [part, setPart] = useState<number | null>(null);
  const [plays, setPlays] = useState(0);
  const [result, setResult] = useState<PassageResult | null>(null);
  const [busy, setBusy] = useState(false);
  const audio = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    if (!learner) return;
    let live = true;
    englishClient()
      .listeningPassage(learner, slug)
      .then((v) => live && setView(v))
      .catch((e: unknown) => live && setError(e));
    return () => {
      live = false;
      audio.current?.pause();
    };
  }, [learner, slug]);

  if (learnerError) return <Problem error={learnerError} onRetry={retry} />;
  if (error) return <Problem error={error} />;
  if (!view || !learner)
    return <p className="en-muted">{vi.english.loading}</p>;
  const v = view;

  /** Play the parts one after another, as one recording. */
  function playFrom(n: number) {
    audio.current?.pause();
    if (n >= v.parts) {
      setPart(null);
      return;
    }
    const el = new Audio(englishClient().passageAudioUrl(v.slug, n, "normal"));
    audio.current = el;
    setPart(n);
    // Fetch the next part while this one plays (a part takes about a second to voice): the
    // browser keeps it in its cache, so the next one starts without a gap.
    if (n + 1 < v.parts)
      new Audio(
        englishClient().passageAudioUrl(v.slug, n + 1, "normal"),
      ).load();
    el.onended = () => playFrom(n + 1);
    el.onerror = () => playFrom(n + 1);
    void el.play().catch(() => setPart(null));
  }
  function stop() {
    audio.current?.pause();
    setPart(null);
  }
  async function submit() {
    if (!learner) return;
    stop();
    setBusy(true);
    try {
      setResult(
        await englishClient().submitPassage(
          learner,
          v.slug,
          passageAnswers(v.items, given),
        ),
      );
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }
  const byId = new Map(result?.items.map((r) => [r.id, r]));

  return (
    <section className="en-card" data-testid="listening-passage">
      <p>
        <Link className="en-link" href="/nghe">
          {t.back}
        </Link>
      </p>
      <h1 lang="en">{v.title}</h1>
      <p className="en-muted">{t.intro}</p>
      {!result && (
        <div className="nt-actions">
          {part === null ? (
            <button
              type="button"
              className="en-button"
              disabled={plays >= PASSAGE_PLAYS}
              onClick={() => {
                setPlays((x) => x + 1);
                playFrom(0);
              }}
            >
              {plays === 0 ? t.play : t.playAgain(PASSAGE_PLAYS - plays)}
            </button>
          ) : (
            <>
              <button type="button" className="en-button ghost" onClick={stop}>
                {t.stop}
              </button>
              <span className="en-muted" role="status">
                {t.playing(part + 1, v.parts)}
              </span>
            </>
          )}
        </div>
      )}
      <ol className="en-fix-first">
        {v.items.map((q) => {
          const r = byId.get(q.id);
          return (
            <li key={q.id} data-testid="passage-question">
              <Prompt q={q} />
              <Input
                q={q}
                value={given[q.id]}
                disabled={result !== null}
                onChange={(a) => setGiven((g) => ({ ...g, [q.id]: a }))}
              />
              {r && (
                <p
                  className={`en-feedback ${r.correct ? "is-right" : "is-wrong"}`}
                >
                  {r.correct ? t.right : t.wrong} {t.yours}:{" "}
                  {shown(q, r.answer)} · {t.key}: <strong>{r.key}</strong>
                </p>
              )}
            </li>
          );
        })}
      </ol>
      {!result ? (
        <button
          type="button"
          className="en-button"
          disabled={busy}
          onClick={() => void submit()}
        >
          {busy ? vi.english.loading : t.submit}
        </button>
      ) : (
        <>
          <p role="status" data-testid="passage-score">
            {t.score(result.correct, result.total, result.answered)}
          </p>
          <h2>{t.transcript}</h2>
          {paragraphsOf(result.transcript).map((para, i) => (
            <p key={i} lang="en">
              {para}
            </p>
          ))}
        </>
      )}
    </section>
  );
}
