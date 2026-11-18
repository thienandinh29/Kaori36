"use client";
import { useEffect, useState } from "react";
import { englishClient } from "@/lib/english/client";
import { DataError } from "@/lib/decode";
import {
  REJECT_REASONS,
  REVIEW_STATUSES,
  highlight,
  keyText,
  type RejectReason,
  type ReviewItem,
  type ReviewQueue,
  type ReviewStatus,
} from "@/lib/reading/review";
import { vi } from "@/messages/vi";
import { Problem } from "@/components/english/problem";
import { useLearner } from "@/components/english/use-learner";

const t = vi.english.readingReview;

/** The question as the learner sees it, plus its options or headings. */
function Question({ item }: { item: ReviewItem }) {
  const q = item.question;
  const text =
    (q.statement as string | undefined) ??
    (q.stem as string | undefined) ??
    (q.sentence as string | undefined) ??
    "";
  const options = Array.isArray(q.options) ? (q.options as string[]) : null;
  const headings = Array.isArray(q.headings) ? (q.headings as string[]) : null;
  return (
    <div lang="en">
      {text && <p>{text}</p>}
      {options && (
        <ol type="A">
          {options.map((o, i) => (
            <li key={i}>{o}</li>
          ))}
        </ol>
      )}
      {headings && (
        <ol start={0}>
          {headings.map((h, i) => (
            <li key={i}>{h}</li>
          ))}
        </ol>
      )}
    </div>
  );
}

/** The owner's review queue for generated Reading questions (specs/listening-reading/step-4.2c.md). */
export function ReadingReviewPage() {
  const { learner, error: learnerError, retry } = useLearner();
  const [status, setStatus] = useState<ReviewStatus>("needs_review");
  const [queue, setQueue] = useState<ReviewQueue | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [forbidden, setForbidden] = useState(false);
  const [index, setIndex] = useState(0);
  const [rejecting, setRejecting] = useState(false);
  const [reason, setReason] = useState<RejectReason>("wrong_key");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(false);

  const [version, setVersion] = useState(0); // bumped after a decision, to reload

  useEffect(() => {
    if (!learner) return;
    let live = true;
    englishClient()
      .readingReview(learner, status)
      .then((q) => {
        if (!live) return;
        setQueue(q);
        setIndex(0);
      })
      .catch((e: unknown) => {
        if (!live) return;
        if (e instanceof DataError && e.status === 403) setForbidden(true);
        else setError(e);
      });
    return () => {
      live = false;
    };
  }, [learner, status, version]);

  if (learnerError) return <Problem error={learnerError} onRetry={retry} />;
  if (forbidden)
    return (
      <section className="en-card" data-testid="reading-review">
        <h1>{t.title}</h1>
        <p className="en-badge draft">{t.ownerOnly}</p>
      </section>
    );
  if (error) return <Problem error={error} />;
  if (!queue || !learner)
    return <p className="en-muted">{vi.english.loading}</p>;
  const item = queue.items[index];
  const decidable = status === "needs_review" || status === "verified";

  async function decide(decision: "approve" | "reject") {
    if (!item) return;
    setBusy(true);
    setSaved(false);
    try {
      await englishClient().decideReading(learner!, item.id, {
        decision,
        ...(decision === "reject" ? { reason } : {}),
        ...(note.trim() ? { note: note.trim() } : {}),
      });
      setSaved(true);
      setRejecting(false);
      setNote("");
      setVersion((v) => v + 1);
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="en-card nt-review" data-testid="reading-review">
      <h1>{t.title}</h1>
      <p className="en-muted">{t.intro}</p>
      <div className="nt-actions" role="tablist">
        {REVIEW_STATUSES.map((s) => (
          <button
            key={s}
            type="button"
            role="tab"
            aria-selected={s === status}
            className={`en-button ${s === status ? "" : "ghost"} small`}
            onClick={() => setStatus(s)}
          >
            {t.statuses[s]} ({queue.counts[s]})
          </button>
        ))}
      </div>
      {saved && (
        <p className="en-feedback is-right" role="status">
          {t.done}
        </p>
      )}
      {!item ? (
        <p className="en-muted">{t.empty}</p>
      ) : (
        <article data-testid="review-item">
          <p className="en-muted">
            {item.id} · {t.skill}: {item.skill} · {index + 1}/
            {queue.items.length}
          </p>
          <h2>{t.passage}</h2>
          {item.passage === null ? (
            <p className="en-feedback is-wrong">{t.passageMissing}</p>
          ) : (
            <p lang="en" className="nt-review-passage">
              {highlight(item.passage, item.evidence).map((s, i) =>
                s.evidence ? (
                  <mark key={i}>{s.text}</mark>
                ) : (
                  <span key={i}>{s.text}</span>
                ),
              )}
            </p>
          )}
          <h2>{t.question}</h2>
          <Question item={item} />
          <p>
            <strong>{t.key}:</strong> <span lang="en">{keyText(item)}</span>
          </p>
          <p>
            <strong>{t.checker}:</strong>{" "}
            <span lang="en">{item.checkerAnswer ?? t.checkerNone}</span>
            {item.checkerModel ? ` (${item.checkerModel})` : ""}
          </p>
          {item.note && <p className="en-muted">{item.note}</p>}
          {decidable && (
            <>
              <label className="nt-review-note">
                {t.note}
                <input
                  type="text"
                  maxLength={500}
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                />
              </label>
              {rejecting && (
                <label>
                  {t.reasonPrompt}{" "}
                  <select
                    value={reason}
                    onChange={(e) => setReason(e.target.value as RejectReason)}
                  >
                    {REJECT_REASONS.map((r) => (
                      <option key={r} value={r}>
                        {t.reasons[r]}
                      </option>
                    ))}
                  </select>
                </label>
              )}
              <div className="nt-actions">
                <button
                  type="button"
                  className="en-button"
                  disabled={busy || item.passage === null}
                  onClick={() => void decide("approve")}
                >
                  {t.approve}
                </button>
                <button
                  type="button"
                  className="en-button ghost"
                  disabled={busy}
                  onClick={() =>
                    rejecting ? void decide("reject") : setRejecting(true)
                  }
                >
                  {t.reject}
                </button>
              </div>
            </>
          )}
          {queue.items.length > 1 && (
            <button
              type="button"
              className="en-button ghost small"
              onClick={() => setIndex((i) => (i + 1) % queue.items.length)}
            >
              {t.next}
            </button>
          )}
        </article>
      )}
    </section>
  );
}
