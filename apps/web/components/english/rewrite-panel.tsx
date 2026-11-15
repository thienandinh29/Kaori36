"use client";
import { useState } from "react";
import { DataError } from "@/lib/decode";
import { englishClient } from "@/lib/english/client";
import type { CheckState, Essay, Rewrite } from "@/lib/english/types";
import { vi } from "@/messages/vi";
import { problemText } from "./problem";

const w = vi.english.writing;

/** Paragraphs as the API splits them: separated by blank lines. */
export function paragraphsOf(text: string): string[] {
  return text
    .trim()
    .split(/\n\s*\n/)
    .map((p) => p.trim())
    .filter((p) => /[A-Za-z0-9]/.test(p));
}

export function pendingRewrite(essay: Essay): boolean {
  return essay.rewrites.some(
    (r) => r.status === "queued" || r.status === "working",
  );
}

function rewriteProblem(error: unknown): string {
  if (error instanceof DataError && error.code === "failed") {
    if (error.status === 403) return w.rewriteNotOpen;
    if (error.status === 429) return w.rewriteLimit;
  }
  return problemText(error);
}

const CHECK_TEXT: Record<CheckState, string> = {
  passed: w.checkPassed,
  failed: w.checkFailed,
  not_run: w.checkNotRun,
};

function SavePhrase({
  learner,
  rewriteId,
  change,
}: {
  learner: string;
  rewriteId: string;
  change: number;
}) {
  const [state, setState] = useState<"idle" | "busy" | "saved" | "error">(
    "idle",
  );
  const [message, setMessage] = useState("");
  if (state === "saved")
    return <span className="en-muted">{w.phraseSaved}</span>;
  return (
    <>
      <button
        type="button"
        className="en-link"
        disabled={state === "busy"}
        onClick={async () => {
          setState("busy");
          try {
            await englishClient().savePhrase(learner, rewriteId, change);
            setState("saved");
          } catch (e: unknown) {
            setState("error");
            setMessage(
              e instanceof DataError && e.status === 409
                ? w.phraseExists
                : e instanceof DataError && e.status === 422
                  ? w.phraseTooLong
                  : problemText(e),
            );
          }
        }}
      >
        {w.savePhrase}
      </button>
      {state === "error" && <span className="en-problem"> {message}</span>}
    </>
  );
}

function RewriteView({ learner, r }: { learner: string; r: Rewrite }) {
  if (r.status === "queued" || r.status === "working")
    return <p className="en-muted">{w.rewriting}</p>;
  if (r.status !== "done" || r.result === null)
    return <p className="en-problem">{r.reason_vi ?? w.rewriteFailed}</p>;
  const res = r.result;
  return (
    <div className="en-rewrite" data-testid="rewrite">
      <p lang="en">{res.rewrite}</p>
      <ul className="en-changes">
        {res.changes.map((c, i) => (
          <li key={i}>
            <span lang="en">
              <del>{c.original || "—"}</del> → <ins>{c.revised || "—"}</ins>
            </span>
            {c.why_vi && <p>{c.why_vi}</p>}
            {c.revised && (
              <SavePhrase learner={learner} rewriteId={r.id} change={i} />
            )}
          </li>
        ))}
      </ul>
      <p className="en-muted">
        {w.checksRan}: LanguageTool {CHECK_TEXT[res.checks.languagetool]};{" "}
        {w.checkScorer} {CHECK_TEXT[res.checks.scorer]}; {w.checkCefr}{" "}
        {CHECK_TEXT[res.checks.cefr]}.
      </p>
    </div>
  );
}

/** "Viết lại đoạn này ở band …" (specs/writing/step-2.4.md, point 4). */
export function RewritePanel({
  learner,
  essay,
  onRequested,
}: {
  learner: string;
  essay: Essay;
  onRequested: () => void;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const paragraphs = paragraphsOf(essay.text);
  return (
    <section className="en-card" data-testid="rewrites">
      <h2>{w.rewriteTitle}</h2>
      <p className="en-muted">{w.rewriteNote}</p>
      <ol className="en-paragraphs">
        {paragraphs.map((p, i) => {
          const mine = essay.rewrites.filter((r) => r.paragraph === i);
          return (
            <li key={i}>
              <p lang="en" className="en-clamp">
                {p}
              </p>
              {mine.map((r) => (
                <RewriteView key={r.id} learner={learner} r={r} />
              ))}
              <button
                type="button"
                className="en-button secondary"
                disabled={busy}
                onClick={async () => {
                  setBusy(true);
                  setError(null);
                  try {
                    await englishClient().requestRewrite(learner, essay.id, i);
                    onRequested();
                  } catch (e: unknown) {
                    setError(e);
                  } finally {
                    setBusy(false);
                  }
                }}
              >
                {w.rewriteThis}
              </button>
            </li>
          );
        })}
      </ol>
      {error !== null && (
        <p className="en-problem" role="alert">
          {rewriteProblem(error)}
        </p>
      )}
    </section>
  );
}
