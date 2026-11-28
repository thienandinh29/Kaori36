"use client";
import { useEffect, useState } from "react";
import { problemText } from "@/components/english/problem";
import { useLearner } from "@/components/english/use-learner";
import { englishClient } from "@/lib/english/client";
import type { Feedback } from "@/lib/speaking/exam";
import { vi } from "@/messages/vi";

const t = vi.english.speakingFeedback;
const POLL_MS = 2000;
const POLL_LIMIT = 60; // two minutes

/** The model's feedback on one answer (specs/speaking/step-5.3b.md): a button after the notice, then
 *  the points with their quotes. Hints from an AI reading a machine transcript: never a score. */
export function FeedbackBlock({
  answerId,
  initial,
}: {
  answerId: string;
  initial: Feedback;
}) {
  const { learner } = useLearner();
  const [fb, setFb] = useState<Feedback>(initial);
  const [open, setOpen] = useState(false);
  const [agreed, setAgreed] = useState(false);
  const [sending, setSending] = useState(false);
  const [late, setLate] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const pending = fb.status === "queued" || fb.status === "working";
  useEffect(() => {
    if (!pending || !learner) return;
    let live = true;
    let n = 0;
    const timer = window.setInterval(() => {
      n += 1;
      if (n > POLL_LIMIT) {
        window.clearInterval(timer);
        if (live) setLate(true);
        return;
      }
      englishClient()
        .speakingFeedback(learner, answerId)
        .then((f) => live && setFb(f))
        .catch(() => undefined);
    }, POLL_MS);
    return () => {
      live = false;
      window.clearInterval(timer);
    };
  }, [pending, learner, answerId]);

  async function send() {
    if (!learner) return;
    setSending(true);
    setError(null);
    try {
      const client = englishClient();
      await client.requestSpeakingFeedback(learner, answerId, fb.consent);
      setFb(await client.speakingFeedback(learner, answerId));
      setOpen(false);
      setAgreed(false);
    } catch (e) {
      setError(problemText(e));
    } finally {
      setSending(false);
    }
  }

  if (fb.status === "done" && fb.points.length > 0)
    return (
      <div className="nt-exam-language" data-testid="speaking-feedback">
        <p>
          <strong>{t.title}</strong>
        </p>
        <p className="en-muted small">{t.label}</p>
        <ul className="nt-exam-hints">
          {fb.points.map((p, i) => (
            <li key={i}>
              <span className={`en-badge ${p.kind === "issue" ? "draft" : ""}`}>
                {p.kind === "issue" ? t.issue : t.strength} ·{" "}
                {t.areas[p.area] ?? p.area}
              </span>{" "}
              {p.point_vi}
              <br />
              <span lang="en" className="nt-quote">
                “{p.quote}”
              </span>
              {p.better && (
                <>
                  <br />
                  <span className="en-muted small">{t.better}: </span>
                  <span lang="en">{p.better}</span>
                </>
              )}
            </li>
          ))}
        </ul>
      </div>
    );
  if (pending)
    return (
      <p className="en-muted small" data-testid="feedback-waiting">
        {late ? t.tooLong : t.waiting}
      </p>
    );
  return (
    <div data-testid="feedback-ask">
      {fb.status === "failed" && fb.failed && (
        <p className="en-muted small" data-testid="feedback-failed">
          {fb.failed}
        </p>
      )}
      {fb.can_ask && !open && (
        <button
          type="button"
          className="en-button small secondary"
          onClick={() => setOpen(true)}
        >
          {fb.status === "failed" ? t.retry : t.button}
        </button>
      )}
      {fb.can_ask && open && (
        <div className="nt-pron-consent">
          <p>
            <strong>{t.noticeTitle}</strong>
          </p>
          <p className="en-badge draft">{t.noticeDraft}</p>
          <p>{t.noticeText}</p>
          <label>
            <input
              type="checkbox"
              checked={agreed}
              onChange={(e) => setAgreed(e.target.checked)}
            />{" "}
            {t.noticeAgree}
          </label>
          <div className="nt-actions">
            <button
              type="button"
              className="en-button small"
              disabled={!agreed || sending}
              onClick={() => void send()}
            >
              {t.send}
            </button>
          </div>
          {error && <p className="en-feedback is-wrong">{error}</p>}
        </div>
      )}
    </div>
  );
}
