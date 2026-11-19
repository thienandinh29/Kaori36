"use client";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { englishClient } from "@/lib/english/client";
import {
  PLAYS,
  percent,
  type ListeningResult,
  type ListeningText,
} from "@/lib/listening/practice";
import { vi } from "@/messages/vi";
import { Problem } from "@/components/english/problem";
import { TraceNote } from "@/components/english/trace-note";
import { useLearner } from "@/components/english/use-learner";

const t = vi.english.listening;

/** One text's dictation and gap-fill, one sentence at a time (step 4.4b). */
export function ListeningPractice({ slug }: { slug: string }) {
  const { learner, error: learnerError, retry } = useLearner();
  const [text, setText] = useState<ListeningText | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [index, setIndex] = useState(0);
  const [typed, setTyped] = useState("");
  const [plays, setPlays] = useState(0);
  const [audioFailed, setAudioFailed] = useState(false);
  const [result, setResult] = useState<ListeningResult | null>(null);
  const [busy, setBusy] = useState(false);
  const audio = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    if (!learner) return;
    let live = true;
    englishClient()
      .listeningText(learner, slug)
      .then((x) => live && setText(x))
      .catch((e: unknown) => live && setError(e));
    return () => {
      live = false;
    };
  }, [learner, slug]);

  if (learnerError) return <Problem error={learnerError} onRetry={retry} />;
  if (error) return <Problem error={error} />;
  if (!text || !learner)
    return <p className="en-muted">{vi.english.loading}</p>;
  const item = text.items[index];
  const done = index >= text.items.length;
  const left = PLAYS - plays;

  function play(pace: "normal" | "slow") {
    if (!item) return;
    // After answering, replays are free: the learner checks what they heard.
    if (!result && left <= 0) return;
    audio.current?.pause();
    const el = new Audio(englishClient().listeningAudioUrl(item.id, pace));
    audio.current = el;
    setAudioFailed(false);
    el.play()
      .then(() => {
        if (!result) setPlays((n) => n + 1);
      })
      .catch(() => setAudioFailed(true));
  }

  async function submit() {
    if (!item || !learner || !typed.trim()) return;
    setBusy(true);
    try {
      setResult(
        await englishClient().answerListening(learner, item.id, typed.trim()),
      );
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }
  function next() {
    audio.current?.pause();
    setResult(null);
    setTyped("");
    setPlays(0);
    setAudioFailed(false);
    setIndex((i) => i + 1);
  }

  return (
    <section className="en-card nt-review" data-testid="listening-practice">
      <h1 lang="en">{text.title}</h1>
      <p className="en-muted">{t.voiceNote}</p>
      {done || !item ? (
        <p className="en-feedback is-right">
          {t.finished} <Link href="/nghe">{t.back}</Link>
        </p>
      ) : (
        <article data-testid="listening-item">
          <h2>
            {t.item} {index + 1}/{text.items.length} · {t.kinds[item.kind]}
          </h2>
          <div className="nt-actions">
            <button
              type="button"
              className="en-button small"
              disabled={!result && left <= 0}
              onClick={() => play("normal")}
            >
              {t.play}
            </button>
            <button
              type="button"
              className="en-button small ghost"
              disabled={!result && left <= 0}
              onClick={() => play("slow")}
            >
              {t.slow}
            </button>
            {!result && (
              <span className="en-muted" role="status">
                {left > 0 ? t.playsLeft(left) : t.noPlays}
              </span>
            )}
          </div>
          {audioFailed && (
            <p className="en-feedback is-wrong">{t.audioFailed}</p>
          )}
          {item.prompt && (
            <p lang="en" data-testid="listening-prompt">
              {item.prompt}
            </p>
          )}
          <form
            className="nt-listen-form"
            onSubmit={(e) => {
              e.preventDefault();
              void submit();
            }}
          >
            <label>
              {item.kind === "dictation" ? t.typeSentence : t.typeWord}{" "}
              <input
                lang="en"
                value={typed}
                maxLength={item.kind === "dictation" ? 400 : 40}
                disabled={busy || result !== null}
                autoComplete="off"
                autoCorrect="off"
                spellCheck={false}
                onChange={(e) => setTyped(e.target.value)}
              />
            </label>{" "}
            <button
              type="submit"
              className="en-button small"
              disabled={busy || result !== null || !typed.trim()}
            >
              {t.check}
            </button>
          </form>
          {result && (
            <div role="status" data-testid="listening-result">
              <p
                className={`en-feedback ${result.correct ? "is-right" : "is-wrong"}`}
              >
                {result.correct ? t.right : t.wrong}{" "}
                {item.kind === "dictation"
                  ? t.score(percent(result.score))
                  : `${t.key}: `}
                {item.kind === "gap" && <strong lang="en">{result.key}</strong>}
              </p>
              {result.words.length > 0 && (
                <>
                  <p lang="en" className="nt-dictation-words">
                    {result.words.map((w, i) => (
                      <span
                        key={i}
                        className={`nt-word is-${w.status}`}
                        title={t.status[w.status]}
                      >
                        {w.word}
                      </span>
                    ))}
                  </p>
                  <p className="en-muted">{t.legend}</p>
                </>
              )}
              <p>
                {t.sentence}: <span lang="en">{result.sentence}</span>
              </p>
              <TraceNote trace={result.trace} names={{}} />
              <button type="button" className="en-button" onClick={next}>
                {index + 1 < text.items.length ? t.next : t.finish}
              </button>
            </div>
          )}
        </article>
      )}
    </section>
  );
}
