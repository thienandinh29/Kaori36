"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { englishClient } from "@/lib/english/client";
import { paragraphsOf } from "@/lib/reading/practice";
import {
  REJECT_REASONS,
  highlight,
  keyText,
  shortcut,
  type PassageReview,
  type RejectReason,
  type ReviewTexts,
} from "@/lib/reading/review";
import { vi } from "@/messages/vi";
import { Problem } from "@/components/english/problem";
import { Question } from "@/components/reading/review-question";
import { DataError } from "@/lib/decode";

const t = vi.english.readingReview;
const MAX_SECONDS = 600; // the API caps a decision's time; longer means the owner stepped away

/** Review one passage at a time (specs/listening-reading/step-4.2f.md). */
export function ReviewByPassage({ learner }: { learner: string }) {
  const [texts, setTexts] = useState<ReviewTexts | null>(null);
  const [review, setReview] = useState<PassageReview | null>(null);
  const [index, setIndex] = useState(0);
  const [rejecting, setRejecting] = useState(false);
  const [reason, setReason] = useState<RejectReason>("wrong_key");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [forbidden, setForbidden] = useState(false);
  const shownAt = useRef(0); // set when a question is shown (an effect, not render)

  const loadTexts = useCallback(async () => {
    const list = await englishClient().reviewTexts(learner);
    setTexts(list);
    return list;
  }, [learner]);

  const open = useCallback(
    async (slug: string) => {
      const r = await englishClient().reviewText(learner, slug);
      setReview(r);
      setIndex(0);
      setRejecting(false);
      setNote("");
    },
    [learner],
  );

  useEffect(() => {
    let live = true;
    englishClient()
      .reviewTexts(learner)
      .then((list) => {
        if (live) setTexts(list);
      })
      .catch((e: unknown) => {
        if (!live) return;
        if (e instanceof DataError && e.status === 403) setForbidden(true);
        else setError(e);
      });
    return () => {
      live = false;
    };
  }, [learner]);

  useEffect(() => {
    shownAt.current = Date.now();
  }, [review, index]);

  const item = review?.items[index];

  const decide = useCallback(
    async (decision: "approve" | "reject") => {
      if (!review || !item || busy) return;
      setBusy(true);
      setMessage(null);
      const seconds = Math.min(
        MAX_SECONDS,
        Math.round((Date.now() - shownAt.current) / 1000),
      );
      try {
        await englishClient().decideReading(learner, item.id, {
          decision,
          ...(decision === "reject" ? { reason } : {}),
          ...(note.trim() ? { note: note.trim() } : {}),
          seconds,
        });
        const rest = review.items.filter((i) => i.id !== item.id);
        setRejecting(false);
        setNote("");
        if (rest.length > 0) {
          setReview({ ...review, items: rest });
          setIndex((i) => Math.min(i, rest.length - 1));
          setMessage(t.done);
        } else {
          setMessage(t.textDone);
          const list = await loadTexts();
          const next = list.texts.find((x) => x.slug !== review.slug);
          if (next) await open(next.slug);
          else setReview(null);
        }
      } catch (e) {
        setError(e);
      } finally {
        setBusy(false);
      }
    },
    [busy, item, learner, loadTexts, note, open, reason, review],
  );

  useEffect(() => {
    if (!review) return;
    function onKey(e: KeyboardEvent) {
      const target = e.target as HTMLElement | null;
      if (target && ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName))
        return; // typing a note
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      const action = shortcut(e.key, rejecting);
      if (!action) return;
      e.preventDefault();
      const n = review!.items.length;
      switch (action.type) {
        case "approve":
          void decide("approve");
          break;
        case "reject":
          setRejecting(true);
          break;
        case "reason":
          setReason(action.reason);
          break;
        case "confirm":
          void decide("reject");
          break;
        case "cancel":
          setRejecting(false);
          break;
        case "skip":
          setIndex((i) => (i + 1) % n);
          break;
        case "back":
          setIndex((i) => (i - 1 + n) % n);
          break;
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [decide, rejecting, review]);

  if (forbidden) return <p className="en-badge draft">{t.ownerOnly}</p>;
  if (error) return <Problem error={error} />;
  if (!texts) return <p className="en-muted">{vi.english.loading}</p>;

  if (!review || !item) {
    return (
      <div data-testid="review-texts">
        <p className="en-muted">
          {t.stats(
            texts.stats.decisions,
            texts.stats.medianSeconds,
            texts.stats.overturned,
          )}{" "}
          {texts.stats.decisions > 0 && t.statsNote}
        </p>
        {message && (
          <p className="en-feedback is-right" role="status">
            {message}
          </p>
        )}
        <h2>{t.textsTitle}</h2>
        {texts.texts.length === 0 ? (
          <p className="en-muted">{t.textsEmpty}</p>
        ) : (
          <ul className="nt-review-texts">
            {texts.texts.map((x) => (
              <li key={x.slug}>
                <button
                  type="button"
                  className="en-button ghost"
                  onClick={() => void open(x.slug).catch(setError)}
                >
                  <span lang="en">{x.title}</span> · {x.agreed} {t.agreed} ·{" "}
                  {x.flagged} {t.flagged}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    );
  }

  const paragraphs = paragraphsOf(review.passage);
  const disagrees =
    !item.agreed && item.checkerAnswer !== null
      ? item.checkerAnswer
      : !item.agreed
        ? t.checkerNone
        : null;

  return (
    <article data-testid="review-passage" className="nt-review-by-passage">
      <p className="en-muted">
        <button
          type="button"
          className="en-button ghost small"
          onClick={() => {
            setReview(null);
            void loadTexts().catch(setError);
          }}
        >
          {t.backToTexts}
        </button>{" "}
        <span lang="en">{review.title}</span> ·{" "}
        {t.progress(index + 1, review.items.length)}
      </p>
      <div className="nt-review-passage" lang="en">
        {paragraphs.map((p, n) => (
          <p key={n}>
            <strong>
              {t.paragraph} {n}.
            </strong>{" "}
            {highlight(p, item.evidence).map((s, i) =>
              s.evidence ? (
                <mark key={i}>{s.text}</mark>
              ) : (
                <span key={i}>{s.text}</span>
              ),
            )}
          </p>
        ))}
      </div>
      <section data-testid="review-item" aria-live="polite">
        <p className="en-muted">
          {item.id} · {t.skill}: {item.skill}
          {!item.agreed && (
            <>
              {" "}
              · <span className="en-badge draft">{t.flaggedBadge}</span>
            </>
          )}
        </p>
        <Question item={item} />
        <p>
          <strong>{t.key}:</strong> <span lang="en">{keyText(item)}</span>
        </p>
        {disagrees !== null && (
          <p className="en-feedback is-wrong">
            <strong>{t.checkerSays}:</strong> <span lang="en">{disagrees}</span>
          </p>
        )}
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
          <fieldset>
            <legend>{t.reasonPrompt}</legend>
            {REJECT_REASONS.map((r, i) => (
              <label key={r}>
                <input
                  type="radio"
                  name="reason"
                  checked={reason === r}
                  onChange={() => setReason(r)}
                />{" "}
                {i + 1}. {t.reasons[r]}
              </label>
            ))}
          </fieldset>
        )}
        <div className="nt-actions">
          {rejecting ? (
            <>
              <button
                type="button"
                className="en-button"
                disabled={busy}
                onClick={() => void decide("reject")}
              >
                {t.confirmReject} (Enter)
              </button>
              <button
                type="button"
                className="en-button ghost"
                onClick={() => setRejecting(false)}
              >
                {t.cancel} (Esc)
              </button>
            </>
          ) : (
            <>
              <button
                type="button"
                className="en-button"
                disabled={busy}
                onClick={() => void decide("approve")}
              >
                {t.approve} (A)
              </button>
              <button
                type="button"
                className="en-button ghost"
                disabled={busy}
                onClick={() => setRejecting(true)}
              >
                {t.reject} (R)
              </button>
              <button
                type="button"
                className="en-button ghost"
                onClick={() => setIndex((i) => (i + 1) % review.items.length)}
              >
                {t.skip} (S)
              </button>
            </>
          )}
        </div>
        {message && (
          <p className="en-feedback is-right" role="status">
            {message}
          </p>
        )}
        <p className="en-muted">{t.keysHint}</p>
      </section>
    </article>
  );
}
