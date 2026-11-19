"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { englishClient } from "@/lib/english/client";
import { highlight } from "@/lib/reading/review";
import {
  paragraphsOf,
  type Answer,
  type AnswerResult,
  type Question,
  type ReadingText,
} from "@/lib/reading/practice";
import { vi } from "@/messages/vi";
import { Problem } from "@/components/english/problem";
import { TraceNote } from "@/components/english/trace-note";
import { useLearner } from "@/components/english/use-learner";

const t = vi.english.readingPractice;

function Prompt({ q }: { q: Question }) {
  if (q.kind === "tfng") return <p lang="en">{q.statement}</p>;
  if (q.kind === "mcq") return <p lang="en">{q.stem}</p>;
  if (q.kind === "completion") return <p lang="en">{q.sentence}</p>;
  return <p>{t.headingsPrompt}</p>;
}

/** One text and its questions, one at a time (specs/listening-reading/step-4.3.md). */
export function ReadingPractice({ slug }: { slug: string }) {
  const { learner, error: learnerError, retry } = useLearner();
  const [text, setText] = useState<ReadingText | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [index, setIndex] = useState(0);
  const [typed, setTyped] = useState("");
  const [choice, setChoice] = useState<number | string | null>(null);
  const [headings, setHeadings] = useState<Record<string, number>>({});
  const [result, setResult] = useState<AnswerResult | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!learner) return;
    let live = true;
    englishClient()
      .readingText(learner, slug)
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
  const q = text.items[index];
  const done = index >= text.items.length;
  const paragraphs = paragraphsOf(text.passage);

  async function submit(answer: Answer) {
    if (!q || !learner) return;
    setBusy(true);
    try {
      setResult(await englishClient().answerReading(learner, q.id, answer));
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }
  function next() {
    setResult(null);
    setTyped("");
    setChoice(null);
    setHeadings({});
    setIndex((i) => i + 1);
  }

  const marked = result ? highlight(text.passage, result.evidence) : null;
  return (
    <section className="en-card nt-review" data-testid="reading-practice">
      <h1 lang="en">{text.title}</h1>
      <p className="en-muted">{t.draftNote}</p>
      <p>
        <Link className="en-button ghost small" href={`/doc/${slug}/thi`}>
          {vi.english.readingTest.start}
        </Link>{" "}
        <span className="en-muted">{vi.english.readingTest.startHint}</span>
      </p>
      <h2>{t.passage}</h2>
      <div lang="en" className="nt-review-passage">
        {marked
          ? marked.map((s, i) =>
              s.evidence ? (
                <mark key={i}>{s.text}</mark>
              ) : (
                <span key={i}>{s.text}</span>
              ),
            )
          : paragraphs.map((p, i) => (
              <p key={i}>
                <span className="en-muted">[{i + 1}] </span>
                {p}
              </p>
            ))}
      </div>
      {done ? (
        <p className="en-feedback is-right">
          {t.finished} <Link href="/doc">{t.back}</Link>
        </p>
      ) : (
        <article data-testid="reading-question">
          <h2>
            {t.question} {index + 1}/{text.items.length} · {t.kinds[q.kind]}
          </h2>
          <Prompt q={q} />
          {q.kind === "tfng" && (
            <div className="nt-actions">
              {["TRUE", "FALSE", "NOT GIVEN"].map((v) => (
                <button
                  key={v}
                  type="button"
                  className={`en-button small ${choice === v ? "" : "ghost"}`}
                  disabled={busy || result !== null}
                  onClick={() => {
                    setChoice(v);
                    void submit(v);
                  }}
                >
                  {v}
                </button>
              ))}
            </div>
          )}
          {q.kind === "mcq" && (
            <div className="nt-actions" lang="en">
              {q.options.map((o, i) => (
                <button
                  key={i}
                  type="button"
                  className={`en-button small ${choice === i ? "" : "ghost"}`}
                  disabled={busy || result !== null}
                  onClick={() => {
                    setChoice(i);
                    void submit(i);
                  }}
                >
                  {"ABCD"[i]}. {o}
                </button>
              ))}
            </div>
          )}
          {q.kind === "completion" && (
            <form
              onSubmit={(e) => {
                e.preventDefault();
                if (typed.trim()) void submit(typed.trim());
              }}
            >
              <label>
                {t.maxWords(q.maxWords)}{" "}
                <input
                  lang="en"
                  value={typed}
                  maxLength={60}
                  disabled={busy || result !== null}
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
          )}
          {q.kind === "headings" && (
            <div>
              <ol lang="en">
                {q.headings.map((h, i) => (
                  <li key={i}>{h}</li>
                ))}
              </ol>
              {q.paragraphs.map((p) => (
                <label key={p} className="en-heading-pick">
                  {t.paragraph(p + 1)}{" "}
                  <select
                    value={headings[String(p)] ?? ""}
                    disabled={busy || result !== null}
                    onChange={(e) =>
                      setHeadings((h) => ({
                        ...h,
                        [String(p)]: Number(e.target.value),
                      }))
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
              <button
                type="button"
                className="en-button small"
                disabled={
                  busy ||
                  result !== null ||
                  q.paragraphs.some((p) => headings[String(p)] === undefined)
                }
                onClick={() => void submit(headings)}
              >
                {t.check}
              </button>
            </div>
          )}
          {result && (
            <div role="status">
              <p
                className={`en-feedback ${result.correct ? "is-right" : "is-wrong"}`}
              >
                {result.correct ? t.right : t.wrong} {t.key}:{" "}
                <strong lang="en">{result.key}</strong>
              </p>
              {result.evidence.length > 0 && (
                <p className="en-muted">{t.evidence}</p>
              )}
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
