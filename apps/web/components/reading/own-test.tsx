"use client";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { englishClient } from "@/lib/english/client";
import { browserStore } from "@/lib/english/learner";
import { DataError } from "@/lib/decode";
import {
  MAX_KEY_CHARS,
  MAX_PASSAGE_CHARS,
  MAX_QUESTIONS_CHARS,
  OWN_CONSENT,
  OWN_CONSENT_KEY,
  confirmable,
  pending,
  trapName,
  type OwnKind,
  type OwnMark,
  type OwnQuestion,
  type OwnTest,
  type OwnTestSummary,
} from "@/lib/reading/own";
import { vi } from "@/messages/vi";
import { Problem } from "@/components/english/problem";
import { useLearner } from "@/components/english/use-learner";

const t = vi.english.readingOwn;
const KINDS: OwnKind[] = ["tfng", "ynng", "mcq", "completion", "unsupported"];
const POLL_MS = 2000;

function consentGiven(): boolean {
  try {
    return browserStore()?.getItem(OWN_CONSENT_KEY) === OWN_CONSENT;
  } catch {
    return false;
  }
}
function rememberConsent() {
  try {
    browserStore()?.setItem(OWN_CONSENT_KEY, OWN_CONSENT);
  } catch {
    /* the notice is asked again next time */
  }
}
function forbidden(e: unknown): boolean {
  return e instanceof DataError && e.status === 403;
}

/** Feedback on a Reading test taken outside the app (specs/listening-reading/step-4.3d.md). */
export function OwnTestPage() {
  const { learner, error: learnerError, retry } = useLearner();
  const [history, setHistory] = useState<OwnTestSummary[] | null>(null);
  const [test, setTest] = useState<OwnTest | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const refreshHistory = useCallback(
    (id: string) =>
      englishClient()
        .ownTests(id)
        .then(setHistory)
        .catch((e: unknown) => setError(e)),
    [],
  );
  useEffect(() => {
    if (learner) void refreshHistory(learner);
  }, [learner, refreshHistory]);

  // While the server reads or explains, ask again every two seconds.
  useEffect(() => {
    if (!learner || !test || !pending(test.status)) return;
    const timer = setTimeout(() => {
      englishClient()
        .ownTest(learner, test.id)
        .then(setTest)
        .catch((e: unknown) => setError(e));
    }, POLL_MS);
    return () => clearTimeout(timer);
  }, [learner, test]);

  if (learnerError) return <Problem error={learnerError} onRetry={retry} />;
  if (forbidden(error))
    return (
      <section className="en-card">
        <h1>{t.title}</h1>
        <p className="en-muted">{t.ownerOnly}</p>
      </section>
    );
  if (error) return <Problem error={error} />;
  if (!learner || !history)
    return <p className="en-muted">{vi.english.loading}</p>;

  const open = (id: string) =>
    englishClient()
      .ownTest(learner, id)
      .then(setTest)
      .catch((e: unknown) => setError(e));
  const remove = async (id: string) => {
    await englishClient().deleteOwnTest(learner, id);
    setTest(null);
    setNotice(t.deleted);
    await refreshHistory(learner);
  };

  return (
    <div data-testid="own-test">
      <section className="en-card">
        <h1>{t.title}</h1>
        <p className="en-muted">{t.intro}</p>
        <p className="en-muted">{t.kindsNote}</p>
        {notice && <p role="status">{notice}</p>}
      </section>
      {!test && (
        <PasteForm
          learner={learner}
          onSent={(id) => {
            setNotice(null);
            void open(id);
          }}
          onError={setError}
        />
      )}
      {test && pending(test.status) && (
        <section className="en-card" role="status">
          <p>{t.working[test.status] ?? t.working.queued}</p>
        </section>
      )}
      {test && test.status === "failed" && (
        <section className="en-card" role="alert">
          <p>{t.failed}</p>
          {test.failureVi && <p>{test.failureVi}</p>}
        </section>
      )}
      {test && test.status === "parsed" && (
        <ConfirmList
          // A new list from the server (its problems after a confirm) starts the edits afresh.
          key={JSON.stringify(test.questions)}
          test={test}
          onConfirm={(qs) =>
            englishClient()
              .confirmOwnTest(learner, test.id, qs)
              .then((x) => {
                setTest(x);
                void refreshHistory(learner);
              })
              .catch((e: unknown) => setError(e))
          }
        />
      )}
      {test?.result && <Result test={test} />}
      {test && (
        <section className="en-card nt-actions">
          <button
            type="button"
            className="en-button secondary"
            onClick={() => {
              setTest(null);
              void refreshHistory(learner);
            }}
          >
            {t.another}
          </button>
          <button
            type="button"
            className="en-button ghost"
            onClick={() => void remove(test.id)}
          >
            {t.delete}
          </button>
        </section>
      )}
      <section className="en-card">
        <h2>{t.history}</h2>
        {history.length === 0 ? (
          <p className="en-muted">{t.noHistory}</p>
        ) : (
          <ul>
            {history.map((h) => (
              <li key={h.id}>
                <span lang="en">{h.opening}…</span>{" "}
                <span className="en-muted">
                  · {new Date(h.submittedAt).toLocaleDateString("vi-VN")}
                  {h.total !== null && h.correct !== null
                    ? ` · ${t.score(h.correct, h.total)}`
                    : ""}
                </span>{" "}
                <button
                  type="button"
                  className="en-button small ghost"
                  onClick={() => void open(h.id)}
                >
                  {t.open}
                </button>
              </li>
            ))}
          </ul>
        )}
        <p>
          <Link href="/doc">{vi.english.readingPractice.back}</Link>
        </p>
      </section>
    </div>
  );
}

function PasteForm({
  learner,
  onSent,
  onError,
}: {
  learner: string;
  onSent: (id: string) => void;
  onError: (e: unknown) => void;
}) {
  const [passage, setPassage] = useState("");
  const [questions, setQuestions] = useState("");
  const [key, setKey] = useState("");
  const [answers, setAnswers] = useState("");
  const [progressTest, setProgressTest] = useState(false);
  const [askConsent] = useState(() => !consentGiven());
  const [consent, setConsent] = useState(() => consentGiven());
  const [busy, setBusy] = useState(false);
  const ready =
    passage.trim() && questions.trim() && key.trim() && consent && !busy;
  const send = async () => {
    setBusy(true);
    try {
      const id = await englishClient().submitOwnTest(learner, {
        passage,
        questions,
        key,
        answers,
        progressTest,
      });
      rememberConsent();
      onSent(id);
    } catch (e) {
      onError(e);
    } finally {
      setBusy(false);
    }
  };
  return (
    <section className="en-card">
      <label className="en-field">
        {t.passage}
        <textarea
          lang="en"
          rows={10}
          maxLength={MAX_PASSAGE_CHARS}
          value={passage}
          onChange={(e) => setPassage(e.target.value)}
        />
      </label>
      <label className="en-field">
        {t.questions}
        <textarea
          lang="en"
          rows={8}
          maxLength={MAX_QUESTIONS_CHARS}
          value={questions}
          onChange={(e) => setQuestions(e.target.value)}
        />
      </label>
      <label className="en-field">
        {t.key}
        <span className="en-muted"> {t.keyHint}</span>
        <textarea
          lang="en"
          rows={3}
          maxLength={MAX_KEY_CHARS}
          value={key}
          onChange={(e) => setKey(e.target.value)}
        />
      </label>
      <label className="en-field">
        {t.answers}
        <span className="en-muted"> {t.answersHint}</span>
        <textarea
          lang="en"
          rows={3}
          maxLength={MAX_KEY_CHARS}
          value={answers}
          onChange={(e) => setAnswers(e.target.value)}
        />
      </label>
      <label>
        <input
          type="checkbox"
          checked={progressTest}
          onChange={(e) => setProgressTest(e.target.checked)}
        />{" "}
        {t.progressTest}
      </label>
      {progressTest && <p className="en-muted">{t.progressNote}</p>}
      {askConsent && (
        <div className="en-consent">
          <strong>{t.consentTitle}</strong>
          <p>{t.consent}</p>
          <label>
            <input
              type="checkbox"
              checked={consent}
              onChange={(e) => setConsent(e.target.checked)}
            />{" "}
            {t.consentAccept}
          </label>
        </div>
      )}
      <button
        type="button"
        className="en-button"
        disabled={!ready}
        onClick={() => void send()}
      >
        {busy ? t.sending : t.submit}
      </button>
    </section>
  );
}

function ConfirmList({
  test,
  onConfirm,
}: {
  test: OwnTest;
  onConfirm: (qs: OwnQuestion[]) => Promise<void>;
}) {
  const [qs, setQs] = useState<OwnQuestion[]>(test.questions);
  const [busy, setBusy] = useState(false);
  const edit = (number: number, change: Partial<OwnQuestion>) =>
    // An edit clears code's problems for that question: the server checks it again on confirm.
    setQs((all) =>
      all.map((q) =>
        q.number === number ? { ...q, ...change, problems: [] } : q,
      ),
    );
  const ok = confirmable(qs);
  return (
    <section className="en-card" data-testid="own-confirm">
      <h2>{t.checkTitle}</h2>
      <p className="en-muted">{t.checkIntro}</p>
      <ol className="en-own-list">
        {qs.map((q) => (
          <li key={q.number} data-testid={`own-q-${q.number}`}>
            <strong>
              {vi.english.readingPractice.question} {q.number}
            </strong>
            <label className="en-field">
              {t.kindLabel}{" "}
              <select
                value={q.kind}
                onChange={(e) =>
                  edit(q.number, { kind: e.target.value as OwnKind })
                }
              >
                {KINDS.map((k) => (
                  <option key={k} value={k}>
                    {t.kinds[k]}
                  </option>
                ))}
              </select>
            </label>
            <label className="en-field">
              {t.textLabel}
              <textarea
                lang="en"
                rows={2}
                value={q.text}
                onChange={(e) => edit(q.number, { text: e.target.value })}
              />
            </label>
            {q.kind === "mcq" && (
              <label className="en-field">
                {t.optionsLabel}
                <textarea
                  lang="en"
                  rows={4}
                  value={q.options.join("\n")}
                  onChange={(e) =>
                    edit(q.number, {
                      options: e.target.value
                        .split("\n")
                        .map((o) => o.trim())
                        .filter(Boolean),
                    })
                  }
                />
              </label>
            )}
            {q.kind === "completion" && (
              <label className="en-field">
                {t.maxWordsLabel}{" "}
                <input
                  type="number"
                  min={1}
                  max={3}
                  value={q.maxWords ?? ""}
                  onChange={(e) =>
                    edit(q.number, {
                      maxWords: e.target.value ? Number(e.target.value) : null,
                    })
                  }
                />
              </label>
            )}
            {q.kind !== "unsupported" && (
              <label className="en-field">
                {t.keyLabel}{" "}
                <input
                  lang="en"
                  maxLength={200}
                  value={q.key ?? ""}
                  onChange={(e) =>
                    edit(q.number, { key: e.target.value || null })
                  }
                />
              </label>
            )}
            <p className="en-muted">
              {t.yourAnswer}: <span lang="en">{q.answer ?? t.blank}</span>
            </p>
            {q.problems.length > 0 && (
              <div role="alert">
                <p>{t.unreadable}</p>
                <ul>
                  {q.problems.map((p) => (
                    <li key={p}>{p}</li>
                  ))}
                </ul>
              </div>
            )}
            <button
              type="button"
              className="en-button small ghost"
              onClick={() =>
                setQs((all) => all.filter((x) => x.number !== q.number))
              }
            >
              {t.remove}
            </button>
          </li>
        ))}
      </ol>
      {!ok && <p className="en-muted">{t.fixFirst}</p>}
      <button
        type="button"
        className="en-button"
        disabled={!ok || busy}
        onClick={() => {
          setBusy(true);
          void onConfirm(qs).finally(() => setBusy(false));
        }}
      >
        {busy ? t.confirming : t.confirm}
      </button>
    </section>
  );
}

function Result({ test }: { test: OwnTest }) {
  const r = test.result;
  if (!r) return null;
  return (
    <section className="en-card" data-testid="own-result">
      <h2>{t.score(r.correct, r.total)}</h2>
      <p className="en-muted">{t.noBand}</p>
      {r.unsupported.length > 0 && (
        <p className="en-muted">{t.unsupportedCount(r.unsupported.length)}</p>
      )}
      <p className="en-muted">{t.evidence(r.evidence)}</p>
      {test.progressTest && <p className="en-muted">{t.progressNote}</p>}
      <ol className="en-own-list">
        {r.marks.map((m) => (
          <MarkView key={m.number} m={m} explained={r.explained} />
        ))}
      </ol>
    </section>
  );
}

function MarkView({ m, explained }: { m: OwnMark; explained: boolean }) {
  const trap = trapName(m.trap, t.traps, t.answerNames);
  const e = m.explanation;
  return (
    <li data-testid={`own-mark-${m.number}`}>
      <p>
        <strong>
          {vi.english.readingPractice.question} {m.number}:{" "}
          {m.correct ? t.right : t.wrong}
        </strong>
      </p>
      <p>
        {t.yourAnswer}:{" "}
        <span lang="en">{m.answerText ?? m.answer ?? t.blank}</span>
        {" · "}
        {t.officialKey}: <span lang="en">{m.key}</span>
      </p>
      {!m.correct && trap && (
        <p>
          {t.trap}: <strong>{trap}</strong>
        </p>
      )}
      {!m.correct && e && (
        <div className="en-own-explain">
          <p className="en-muted">{t.unchecked}</p>
          {e.whyWrongVi && (
            <>
              <p>
                <strong>{t.whyWrong}</strong>
              </p>
              <p>{e.whyWrongVi}</p>
              {e.wrongQuotes.map((q) => (
                <blockquote key={q} lang="en">
                  {q}
                </blockquote>
              ))}
            </>
          )}
          <p>
            <strong>{t.whyKey}</strong>
          </p>
          <p>{e.whyKeyVi}</p>
          {e.keyQuotes.map((q) => (
            <blockquote key={q} lang="en">
              {q}
            </blockquote>
          ))}
        </div>
      )}
      {!m.correct && !e && (
        <p className="en-muted">
          {explained
            ? (m.explanationVi ?? t.noExplanation)
            : t.working.explaining}
        </p>
      )}
    </li>
  );
}
