"use client";
import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { englishClient } from "@/lib/english/client";
import { highlight } from "@/lib/reading/review";
import {
  paragraphsOf,
  type Answer,
  type Question,
} from "@/lib/reading/practice";
import {
  answered,
  clock,
  remaining,
  submission,
  type Given,
  type StartedTest,
  type TestResult,
} from "@/lib/reading/test";
import { vi } from "@/messages/vi";
import { Problem } from "@/components/english/problem";
import { useLearner } from "@/components/english/use-learner";

const t = vi.english.readingTest;
const p = vi.english.readingPractice;

export function Prompt({ q }: { q: Question }) {
  if (q.kind === "tfng") return <p lang="en">{q.statement}</p>;
  if (q.kind === "mcq") return <p lang="en">{q.stem}</p>;
  if (q.kind === "completion") return <p lang="en">{q.sentence}</p>;
  return <p>{p.headingsPrompt}</p>;
}

/** A controlled answer input: it records the choice and never grades (nothing shows before submitting). */
export function Input({
  q,
  value,
  disabled,
  onChange,
}: {
  q: Question;
  value: Answer | undefined;
  disabled: boolean;
  onChange: (a: Answer) => void;
}) {
  if (q.kind === "tfng")
    return (
      <div className="nt-actions" role="radiogroup" aria-label={q.statement}>
        {["TRUE", "FALSE", "NOT GIVEN"].map((v) => (
          <button
            key={v}
            type="button"
            role="radio"
            aria-checked={value === v}
            className={`en-button small ${value === v ? "" : "ghost"}`}
            disabled={disabled}
            onClick={() => onChange(v)}
          >
            {v}
          </button>
        ))}
      </div>
    );
  if (q.kind === "mcq")
    return (
      <div
        className="nt-actions"
        role="radiogroup"
        aria-label={q.stem}
        lang="en"
      >
        {q.options.map((o, i) => (
          <button
            key={i}
            type="button"
            role="radio"
            aria-checked={value === i}
            className={`en-button small ${value === i ? "" : "ghost"}`}
            disabled={disabled}
            onClick={() => onChange(i)}
          >
            {"ABCD"[i]}. {o}
          </button>
        ))}
      </div>
    );
  if (q.kind === "completion")
    return (
      <label>
        {p.maxWords(q.maxWords)}{" "}
        <input
          lang="en"
          maxLength={60}
          disabled={disabled}
          value={typeof value === "string" ? value : ""}
          onChange={(e) => onChange(e.target.value)}
        />
      </label>
    );
  const chosen = typeof value === "object" ? value : {};
  return (
    <div>
      <ol lang="en">
        {q.headings.map((h, i) => (
          <li key={i}>{h}</li>
        ))}
      </ol>
      {q.paragraphs.map((n) => (
        <label key={n} className="en-heading-pick">
          {p.paragraph(n + 1)}{" "}
          <select
            disabled={disabled}
            value={chosen[String(n)] ?? ""}
            onChange={(e) =>
              onChange({ ...chosen, [String(n)]: Number(e.target.value) })
            }
          >
            <option value="">—</option>
            {q.headings.map((_, i) => (
              <option key={i} value={i}>
                {i + 1}
              </option>
            ))}
          </select>
        </label>
      ))}
    </div>
  );
}

export function shown(q: Question, a: unknown): string {
  if (a === null || a === undefined) return t.blank;
  if (q.kind === "mcq" && typeof a === "number")
    return `${"ABCD"[a]}. ${q.options[a] ?? ""}`;
  if (q.kind === "headings" && typeof a === "object")
    return Object.entries(a as Record<string, number>)
      .map(([n, h]) => `${p.paragraph(Number(n) + 1)}: ${h + 1}`)
      .join(", ");
  return String(a);
}

/** A timed test on one text (specs/listening-reading/step-4.3b.md). */
export function ReadingTest({ slug }: { slug: string }) {
  const { learner, error: learnerError, retry } = useLearner();
  const [test, setTest] = useState<StartedTest | null>(null);
  const [startMs, setStartMs] = useState(0);
  const [nowMs, setNowMs] = useState(0);
  const [given, setGiven] = useState<Given>({});
  const [result, setResult] = useState<TestResult | null>(null);
  const [timeUp, setTimeUp] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const sent = useRef(false);

  useEffect(() => {
    if (!learner) return;
    let live = true;
    englishClient()
      .startReadingTest(learner, slug)
      .then((x) => {
        if (!live) return;
        const now = Date.now();
        setTest(x);
        setStartMs(now);
        setNowMs(now);
      })
      .catch((e: unknown) => live && setError(e));
    return () => {
      live = false;
    };
  }, [learner, slug]);

  const send = useCallback(
    async (auto: boolean) => {
      if (!test || !learner || sent.current) return;
      sent.current = true;
      try {
        const r = await englishClient().submitReadingTest(
          learner,
          test.testId,
          submission(test.items, given),
        );
        setTimeUp(auto);
        setResult(r);
      } catch (e) {
        sent.current = false;
        setError(e);
      }
    },
    [given, learner, test],
  );

  const left = test ? remaining(startMs, test.limitSeconds, nowMs) : 1;
  const latest = useRef(send);
  useEffect(() => {
    latest.current = send;
  }, [send]);
  // The clock ticks once a second; at 0 the timer itself submits (no feedback before then).
  useEffect(() => {
    if (!test || result) return;
    const id = window.setInterval(() => {
      const now = Date.now();
      setNowMs(now);
      if (remaining(startMs, test.limitSeconds, now) === 0)
        void latest.current(true);
    }, 1000);
    return () => window.clearInterval(id);
  }, [result, startMs, test]);

  if (learnerError) return <Problem error={learnerError} onRetry={retry} />;
  if (error) return <Problem error={error} />;
  if (!test) return <p className="en-muted">{vi.english.loading}</p>;
  const paragraphs = paragraphsOf(test.passage);
  const done = test.items.filter((q) =>
    answered(q, given[q.id]?.answer),
  ).length;
  const evidence = result
    ? result.items.flatMap((i) => (i.correct ? [] : i.evidence))
    : [];

  return (
    <section className="en-card nt-reading-test" data-testid="reading-test">
      <h1 lang="en">{test.title}</h1>
      {!result && (
        <p className="nt-test-clock" role="timer" aria-live="off">
          {t.left} <strong>{clock(left)}</strong> ·{" "}
          {t.answeredCount(done, test.items.length)}
        </p>
      )}
      {result && (
        <div role="status" data-testid="reading-test-result">
          <h2>{t.score(result.correct, result.total)}</h2>
          {timeUp && <p className="en-muted">{t.timeUp}</p>}
          {result.overTime && (
            <p className="en-feedback is-wrong">{t.overTime}</p>
          )}
          <p className="en-muted">
            {t.took(clock(result.seconds))}. {t.noBand}
          </p>
        </div>
      )}
      <div className="nt-reading-test-body">
        <div className="nt-review-passage" lang="en">
          {paragraphs.map((para, n) => (
            <p key={n}>
              <strong>{p.paragraph(n + 1)}.</strong>{" "}
              {highlight(para, evidence).map((s, i) =>
                s.evidence ? (
                  <mark key={i}>{s.text}</mark>
                ) : (
                  <span key={i}>{s.text}</span>
                ),
              )}
            </p>
          ))}
        </div>
        <ol className="nt-test-questions">
          {test.items.map((q, i) => {
            const r = result?.items.find((x) => x.id === q.id);
            return (
              <li key={q.id} data-testid="reading-test-question">
                <p className="en-muted">
                  {i + 1}. {p.kinds[q.kind]}
                </p>
                <Prompt q={q} />
                {!result ? (
                  <Input
                    q={q}
                    value={given[q.id]?.answer}
                    disabled={false}
                    onChange={(a) =>
                      setGiven((g) => ({
                        ...g,
                        [q.id]: {
                          answer: a,
                          atSeconds: Math.floor((Date.now() - startMs) / 1000),
                        },
                      }))
                    }
                  />
                ) : (
                  r && (
                    <p
                      className={`en-feedback ${r.correct ? "is-right" : "is-wrong"}`}
                    >
                      {r.correct ? p.right : p.wrong} {t.yours}:{" "}
                      <span lang="en">{shown(q, r.answer)}</span>
                      {r.atSeconds !== null && ` (${t.at(clock(r.atSeconds))})`}
                      . {p.key}: <strong lang="en">{r.key}</strong>
                    </p>
                  )
                )}
              </li>
            );
          })}
        </ol>
      </div>
      {!result ? (
        <button
          type="button"
          className="en-button"
          onClick={() => {
            const blank = test.items.length - done;
            if (blank === 0 || window.confirm(t.confirmEarly(blank)))
              void send(false);
          }}
        >
          {t.submit}
        </button>
      ) : (
        <div className="nt-actions">
          <Link className="en-button ghost" href={`/doc/${slug}`}>
            {t.practice}
          </Link>
          <Link className="en-button ghost" href="/doc">
            {p.back}
          </Link>
        </div>
      )}
    </section>
  );
}
