"use client";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { DataError } from "@/lib/decode";
import { englishClient } from "@/lib/english/client";
import { browserStore } from "@/lib/english/learner";
import {
  OWN_ID,
  clearTest,
  ownParts,
  ownPrompt,
  promptIdFor,
  savedTest,
  saveTest,
} from "@/lib/english/own-prompt";
import { sessionStore } from "@/lib/english/session-store";
import type { WritingPrompt, WritingTest } from "@/lib/english/types";
import { clock, remaining } from "@/lib/reading/test";
import {
  MAX_CHARS,
  TASK_MIN_WORDS,
  canSubmit,
  consentGiven,
  countWords,
  rememberConsent,
} from "@/lib/english/writing";
import { vi } from "@/messages/vi";
import { ChartFigureView } from "./chart-figure";
import { Problem, problemText } from "./problem";
import { useLearner } from "./use-learner";
import { promptTypeLabel } from "./writing-home";

const t = vi.english;
const w = t.writing;

export function submitProblem(error: unknown): string {
  if (error instanceof DataError && error.code === "failed") {
    if (error.status === 429) return w.dailyLimit;
    if (error.status === 404) return w.badPrompt;
    if (error.status === 422) return w.rejected;
  }
  return problemText(error);
}

/**
 * The editor: live word count, the consent notice before the first submission. `promptId` is the
 * page slug (`de-cua-ban` for the learner's own question); `exam` runs the 40-minute test (2.10).
 */
export function EssayEditor({
  promptId: slug,
  exam = false,
}: {
  promptId: string;
  exam?: boolean;
}) {
  const promptId = promptIdFor(slug);
  const router = useRouter();
  const { learner, error: learnerError, retry } = useLearner();
  const [prompt, setPrompt] = useState<WritingPrompt | null | undefined>();
  const [own, setOwn] = useState<string | null>(null);
  const [kept, setKept] = useState<string[] | null>(null);
  const [test, setTest] = useState<WritingTest | null>(null);
  const [nowMs, setNowMs] = useState(() => Date.now());
  const [loadError, setLoadError] = useState<unknown>(null);
  const [version, setVersion] = useState(0);
  const [text, setText] = useState("");
  // Read once on the first client render; the page shows "loading" until the learner exists.
  const [consent, setConsent] = useState(() => consentGiven(browserStore()));
  const [askedConsent] = useState(() => !consentGiven(browserStore()));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    if (!learner) return;
    let live = true;
    const client = englishClient();
    const store = sessionStore();
    const question = promptId === OWN_ID ? ownPrompt(store) : null;
    // the parts the learner ticked for an own question (step 2.11b); null keeps them all
    const keptParts = question === null ? null : ownParts(store);
    const load: Promise<WritingPrompt | null> =
      promptId === OWN_ID
        ? question === null
          ? Promise.resolve(null)
          : client.checkOwnPrompt(learner, question).then((c) => c.prompt)
        : client
            .writingPrompts(learner)
            .then((ps) => ps.find((p) => p.id === promptId) ?? null);
    load
      .then(async (found) => {
        if (!live) return;
        const p =
          found && keptParts
            ? {
                ...found,
                parts: found.parts.filter((x) => keptParts.includes(x.text)),
              }
            : found;
        setOwn(question);
        setKept(keptParts);
        if (p && exam && p.task === 2) {
          // A reload continues the same test; the server's start time stays the truth.
          const t =
            savedTest(store, promptId, question) ??
            (await client.startWritingTest(
              learner,
              promptId,
              question,
              keptParts,
            ));
          if (!live) return;
          saveTest(store, t, question);
          setTest(t);
        }
        setPrompt(p);
        setLoadError(null);
      })
      .catch((e: unknown) => live && setLoadError(e));
    return () => {
      live = false;
    };
  }, [learner, promptId, exam, version]);

  // The exam clock ticks once a second; it never submits on its own (late is marked, not lost).
  useEffect(() => {
    if (!test) return;
    const id = window.setInterval(() => setNowMs(Date.now()), 1000);
    return () => window.clearInterval(id);
  }, [test]);

  if (learnerError) return <Problem error={learnerError} onRetry={retry} />;
  if (loadError)
    return (
      <Problem error={loadError} onRetry={() => setVersion((n) => n + 1)} />
    );
  if (!learner || prompt === undefined)
    return <p className="en-muted">{t.loading}</p>;
  if (prompt === null)
    return (
      <p className="en-problem">
        {promptId === OWN_ID ? w.ownMissing : w.badPrompt}
      </p>
    );
  if (exam && prompt.task === 2 && !test)
    return <p className="en-muted">{w.examStarting}</p>;
  const left = test
    ? remaining(Date.parse(test.started_at), test.time_limit_s, nowMs)
    : null;

  const words = countWords(text);
  const min = TASK_MIN_WORDS[prompt.task];
  const tooLong = text.normalize("NFC").trim().length > MAX_CHARS;

  async function submit() {
    if (!learner || !prompt || busy) return;
    setBusy(true);
    setError(null);
    try {
      rememberConsent(browserStore());
      const id = await englishClient().submitEssay(learner, promptId, text, {
        own,
        ownParts: kept,
        testId: test?.id ?? null,
      });
      if (test) clearTest(sessionStore());
      router.push(`/bai-viet/${id}`);
    } catch (e: unknown) {
      setError(e);
      setBusy(false);
    }
  }

  return (
    <section className="en-card">
      <div className="en-actions">
        <span className="en-badge next">
          {w.task} {prompt.task} · {prompt.level}
        </span>
        <span className="en-muted">{promptTypeLabel(prompt.type)}</span>
        {prompt.status === "draft" && promptId !== OWN_ID && (
          <span className="en-badge">{t.draft}</span>
        )}
        {promptId === OWN_ID && <span className="en-badge">{w.ownBadge}</span>}
        {test && <span className="en-badge next">{w.examBadge}</span>}
      </div>
      {test && left !== null && (
        <>
          <p className="en-muted">{w.examNote}</p>
          <p className="nt-test-clock" role="timer" data-testid="exam-clock">
            {left > 0 ? (
              <>
                {w.examLeft} <strong>{clock(left)}</strong>
              </>
            ) : (
              <strong>{w.examOver}</strong>
            )}
          </p>
        </>
      )}
      <p lang="en" className="en-prompt">
        {prompt.prompt}
      </p>
      {prompt.parts.length > 0 && (
        <div data-testid="prompt-parts">
          <p className="en-muted">{w.promptParts}</p>
          <ul>
            {prompt.parts.map((part) => (
              <li key={part.text}>
                <span lang="en">{part.text}</span>
                {part.position && <span> {w.partPosition}</span>}
              </li>
            ))}
          </ul>
        </div>
      )}
      {prompt.figure && <ChartFigureView chart={prompt.figure} />}
      <label className="en-essay">
        <span>{w.editor}</span>
        <textarea
          lang="en"
          spellCheck={false}
          value={text}
          placeholder={w.placeholder}
          onChange={(e) => setText(e.target.value)}
          rows={14}
        />
      </label>
      <p className="en-muted" aria-live="polite" data-testid="word-count">
        <strong>{words}</strong> {w.words} ·{" "}
        {words >= min ? w.enough : `${w.atLeast} ${min} ${w.words}`}
      </p>
      {tooLong && <p className="en-problem">{w.tooLong}</p>}
      {askedConsent && (
        <div className="en-consent">
          <strong>{w.consentTitle}</strong>
          <p>{w.consent}</p>
          <label>
            <input
              type="checkbox"
              checked={consent}
              onChange={(e) => setConsent(e.target.checked)}
            />{" "}
            {w.consentAccept}
          </label>
        </div>
      )}
      {error !== null && (
        <p className="en-problem" role="alert">
          {submitProblem(error)}
        </p>
      )}
      <button
        type="button"
        className="en-button"
        disabled={busy || !canSubmit(text, consent)}
        onClick={submit}
      >
        {busy ? w.sending : w.submit}
      </button>
    </section>
  );
}
