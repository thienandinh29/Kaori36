"use client";
import { useEffect, useState } from "react";
import { englishClient } from "@/lib/english/client";
import type { RecheckQuestion, RecheckResult } from "@/lib/english/recheck";
import { vi } from "@/messages/vi";

const t = vi.english.recheck;

/**
 * FORGET-001: one delayed question on a node NodeTrail calls known (specs/forget-001/spec.md).
 * It never changes mastery; it only measures whether "known" lasts a week.
 */
export function RecheckCard({ learner }: { learner: string }) {
  const [question, setQuestion] = useState<RecheckQuestion | null>(null);
  const [result, setResult] = useState<RecheckResult | null>(null);
  const [chosen, setChosen] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    let live = true;
    englishClient()
      .recheckNext(learner)
      .then((q) => live && setQuestion(q))
      .catch(() => undefined); // optional on the home page
    return () => {
      live = false;
    };
  }, [learner]);
  if (!question) return null;

  async function answer(option: string) {
    if (!question) return;
    setBusy(true);
    setChosen(option);
    try {
      setResult(
        await englishClient().recheckAnswer(learner, question.id, option),
      );
    } catch {
      setFailed(true);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="en-card" data-testid="recheck-card">
      <h2>{t.title}</h2>
      <p className="en-muted">
        {t.intro} <strong>{question.nodeNameVi}</strong>
        {question.draft && <span className="en-badge draft">{t.draft}</span>}
      </p>
      <p lang="en">{question.prompt}</p>
      <div className="nt-actions">
        {question.options.map((o) => (
          <button
            key={o}
            type="button"
            lang="en"
            className={`en-button small ${chosen === o ? "" : "ghost"}`}
            disabled={busy || result !== null}
            onClick={() => void answer(o)}
          >
            {o}
          </button>
        ))}
      </div>
      {result && (
        <p
          className={`en-feedback ${result.correct ? "is-right" : "is-wrong"}`}
          role="status"
        >
          {result.correct ? t.right : t.wrong}{" "}
          {!result.correct && (
            <>
              {t.key}: <strong lang="en">{result.key}</strong>
            </>
          )}
        </p>
      )}
      {failed && <p className="en-feedback is-wrong">{t.failed}</p>}
      <p className="en-muted">{t.why}</p>
    </section>
  );
}
