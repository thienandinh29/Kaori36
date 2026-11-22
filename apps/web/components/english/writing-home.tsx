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

/**
 * Type a Task 2 question, checked by the server (2.10); tick the parts it asks for, proposed by
 * code from its wording (2.11b); then write on it or sit it as an exam.
 */
function OwnPrompt({ learner }: { learner: string }) {
  const router = useRouter();
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [why, setWhy] = useState<string | null>(null);
  const [checked, setChecked] = useState<WritingPrompt | null>(null);
  const [kept, setKept] = useState<string[]>([]);

  async function check() {
    if (busy) return;
    setBusy(true);
    setWhy(null);
    try {
      const result = await englishClient().checkOwnPrompt(learner, text);
      if (!result.ok || !result.prompt) {
        setWhy(result.reason_vi);
      } else {
        setChecked(result.prompt);
        setKept(result.prompt.parts.map((p) => p.text));
      }
    } catch (e: unknown) {
      setWhy(problemText(e));
    }
    setBusy(false);
  }

  function go(exam: boolean) {
    if (!checked || kept.length === 0) return;
    // the order of the question, whatever order the boxes were ticked in
    const parts = checked.parts
      .map((p) => p.text)
      .filter((t) => kept.includes(t));
    saveOwnPrompt(sessionStore(), checked.prompt, parts);
    router.push(`/viet/${OWN_SLUG}${exam ? "?thi=1" : ""}`);
  }

  function toggle(part: string) {
    setKept((k) =>
      k.includes(part) ? k.filter((x) => x !== part) : [...k, part],
    );
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
          onChange={(e) => {
            setText(e.target.value);
            setChecked(null); // a changed question is checked again
          }}
        />
      </label>
      {why && (
        <p className="en-problem" role="alert">
          {why}
        </p>
      )}
      {checked === null ? (
        <div className="en-actions">
          <button
            type="button"
            className="en-button"
            disabled={!ready}
            onClick={check}
          >
            {busy ? w.ownChecking : w.ownCheck}
          </button>
        </div>
      ) : (
        <>
          <fieldset className="en-parts" data-testid="own-parts">
            <legend>{w.ownPartsTitle}</legend>
            <p className="en-muted">{w.ownPartsNote}</p>
            {checked.parts.map((p) => (
              <label key={p.text} className="en-check">
                <input
                  type="checkbox"
                  checked={kept.includes(p.text)}
                  onChange={() => toggle(p.text)}
                />
                <span lang="en">{p.text}</span>
                {p.position && <span> {w.partPosition}</span>}
              </label>
            ))}
            {kept.length === 0 && (
              <p className="en-problem" role="alert">
                {w.ownPartsNone}
              </p>
            )}
          </fieldset>
          <div className="en-actions">
            <button
              type="button"
              className="en-button"
              disabled={kept.length === 0}
              onClick={() => go(false)}
            >
              {w.ownWrite}
            </button>
            <button
              type="button"
              className="en-button secondary"
              disabled={kept.length === 0}
              onClick={() => go(true)}
            >
              {w.exam}
            </button>
          </div>
        </>
      )}
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
