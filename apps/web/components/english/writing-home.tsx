"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { englishClient } from "@/lib/english/client";
import { OWN_SLUG, saveOwnPrompt } from "@/lib/english/own-prompt";
import { sessionStore } from "@/lib/english/session-store";
import type { EssaySummary, WritingPrompt } from "@/lib/english/types";
import { vi } from "@/messages/vi";
import { Sena } from "@/components/sena/sena";
import { ErrorPatterns } from "./error-patterns";
import { Problem, problemText } from "./problem";
import { useLearner } from "./use-learner";

const t = vi.english;
const w = t.writing;

export function promptTypeLabel(type: string): string {
  return w.types[type] ?? type;
}

/** Type a Task 2 question, checked by the server, then write on it or sit it as an exam (2.10). */
function OwnPrompt({ learner }: { learner: string }) {
  const router = useRouter();
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [why, setWhy] = useState<string | null>(null);

  async function go(exam: boolean) {
    if (busy) return;
    setBusy(true);
    setWhy(null);
    try {
      const check = await englishClient().checkOwnPrompt(learner, text);
      if (!check.ok || !check.prompt) {
        setWhy(check.reason_vi);
        setBusy(false);
        return;
      }
      saveOwnPrompt(sessionStore(), check.prompt.prompt);
      router.push(`/viet/${OWN_SLUG}${exam ? "?thi=1" : ""}`);
    } catch (e: unknown) {
      setWhy(problemText(e));
      setBusy(false);
    }
  }

  const ready = text.trim().length > 0 && !busy;
  return (
    <section className="en-card" data-testid="own-prompt">
      <h2>{w.ownTitle}</h2>
      <p className="en-muted">{w.ownNote}</p>
      <label className="en-essay">
        <span>{w.ownLabel}</span>
        <textarea
          lang="en"
          rows={3}
          value={text}
          placeholder={w.ownPlaceholder}
          onChange={(e) => setText(e.target.value)}
        />
      </label>
      {why && (
        <p className="en-problem" role="alert">
          {why}
        </p>
      )}
      <div className="en-actions">
        <button
          type="button"
          className="en-button"
          disabled={!ready}
          onClick={() => go(false)}
        >
          {busy ? w.ownChecking : w.ownWrite}
        </button>
        <button
          type="button"
          className="en-button secondary"
          disabled={!ready}
          onClick={() => go(true)}
        >
          {w.exam}
        </button>
      </div>
    </section>
  );
}

/** Prompts to write on, and the learner's essays (specs/writing/step-2.1.md). */
export function WritingHome() {
  const { learner, error: learnerError, retry } = useLearner();
  const [prompts, setPrompts] = useState<WritingPrompt[] | null>(null);
  const [essays, setEssays] = useState<EssaySummary[] | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [version, setVersion] = useState(0);

  useEffect(() => {
    if (!learner) return;
    let live = true;
    const client = englishClient();
    Promise.all([client.writingPrompts(learner), client.essays(learner)])
      .then(([p, e]) => {
        if (!live) return;
        setPrompts(p);
        setEssays(e);
        setError(null);
      })
      .catch((e: unknown) => live && setError(e));
    return () => {
      live = false;
    };
  }, [learner, version]);

  if (learnerError) return <Problem error={learnerError} onRetry={retry} />;
  if (error)
    return <Problem error={error} onRetry={() => setVersion((n) => n + 1)} />;
  if (!prompts || !essays) return <p className="en-muted">{t.loading}</p>;
  const promptText = new Map(prompts.map((p) => [p.id, p.prompt]));

  return (
    <>
      <section className="en-card nt-intro">
        <div className="nt-intro-head">
          <Sena
            pose="idle"
            label={t.senaSays.right}
            className="nt-intro-sena"
          />
          <div>
            <h1>{w.title}</h1>
            <p className="en-muted">{w.intro}</p>
          </div>
        </div>
      </section>
      {learner && <ErrorPatterns learner={learner} />}
      {learner && <OwnPrompt learner={learner} />}
      <section className="en-card">
        <h2>{w.prompts}</h2>
        {prompts.length === 0 && <p className="en-muted">{w.noPrompts}</p>}
        <ul className="en-essays nt-prompts">
          {prompts.map((p) => (
            <li key={p.id}>
              <div className="en-actions">
                <span className="en-badge next">
                  {w.task} {p.task} · {p.level}
                </span>
                <span className="en-muted">{promptTypeLabel(p.type)}</span>
                {p.status === "draft" && (
                  <span className="en-badge">{t.draft}</span>
                )}
              </div>
              <p lang="en">{p.prompt}</p>
              <div className="en-actions">
                <Link className="en-button" href={`/viet/${p.id}`}>
                  {w.write}
                </Link>
                {p.task === 2 && (
                  <Link className="en-link" href={`/viet/${p.id}?thi=1`}>
                    {w.exam}
                  </Link>
                )}
              </div>
            </li>
          ))}
        </ul>
      </section>
      <section className="en-card">
        <h2>{w.yours}</h2>
        {essays.length === 0 && <p className="en-muted">{w.none}</p>}
        <ul className="en-essays">
          {essays.map((e) => (
            <li key={e.id} data-essay-id={e.id}>
              <p lang="en" className="en-clamp">
                {e.own_prompt ?? promptText.get(e.prompt_id) ?? e.prompt_id}
              </p>
              {(e.own_prompt || e.timed) && (
                <p className="en-actions">
                  {e.own_prompt && (
                    <span className="en-badge">{w.ownBadge}</span>
                  )}
                  {e.timed && <span className="en-badge">{w.examBadge}</span>}
                </p>
              )}
              <p className="en-muted">
                <span className={`nt-state is-${e.status}`}>
                  {w.status[e.status]}
                </span>{" "}
                {new Date(e.submitted_at).toLocaleString("vi-VN")}
                {e.words !== null && ` · ${e.words} ${w.words}`}
              </p>
              <Link className="en-link" href={`/bai-viet/${e.id}`}>
                {w.open}
              </Link>
            </li>
          ))}
        </ul>
      </section>
    </>
  );
}
