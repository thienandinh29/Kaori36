"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { Problem } from "@/components/english/problem";
import { useLearner } from "@/components/english/use-learner";
import { englishClient } from "@/lib/english/client";
import type { Part, Result } from "@/lib/speaking/exam";
import { vi } from "@/messages/vi";
import { makeExaminer } from "./examiner";

const t = vi.english.speakingTest;

function playOne(url: string, signal: AbortSignal): Promise<void> {
  return new Promise((resolve) => {
    const audio = new Audio(url);
    const done = () => {
      audio.pause();
      signal.removeEventListener("abort", done);
      resolve();
    };
    audio.addEventListener("ended", done, { once: true });
    audio.addEventListener("error", done, { once: true });
    signal.addEventListener("abort", done, { once: true });
    audio.play().catch(done);
  });
}

/** A sitting replayed: each question with the learner's answer; no score, no feedback yet. */
export function ExamResult({ sittingId }: { sittingId: string }) {
  const router = useRouter();
  const { learner, error: learnerError, retry } = useLearner();
  const [result, setResult] = useState<Result | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [playing, setPlaying] = useState(false);
  const stop = useRef<AbortController | null>(null);

  useEffect(() => {
    if (!learner) return;
    let live = true;
    englishClient()
      .speakingResult(learner, sittingId)
      .then((r) => live && setResult(r))
      .catch((e: unknown) => live && setError(e));
    return () => {
      live = false;
      stop.current?.abort();
    };
  }, [learner, sittingId]);

  if (learnerError) return <Problem error={learnerError} onRetry={retry} />;
  if (error) return <Problem error={error} />;
  if (!result || !learner)
    return <p className="en-muted">{vi.english.loading}</p>;
  const client = englishClient();

  async function playAll() {
    const controller = new AbortController();
    stop.current = controller;
    setPlaying(true);
    const examiner = await makeExaminer(1);
    for (const q of result!.questions) {
      if (controller.signal.aborted) break;
      if (!q.answer?.audio) continue;
      await examiner.say(q.text, controller.signal);
      await playOne(
        client.speakingAudioUrl(learner!, q.answer.id),
        controller.signal,
      );
    }
    setPlaying(false);
  }

  async function remove() {
    if (!window.confirm(t.confirmDelete)) return;
    try {
      await client.deleteSpeakingTest(learner!, sittingId);
      router.push("/noi/thi");
    } catch (e) {
      setError(e);
    }
  }

  const parts: Part[] = [1, 2, 3];
  const deleteAt = result.questions.find((q) => q.answer?.delete_after)?.answer
    ?.delete_after;
  return (
    <section className="en-card nt-exam" data-testid="exam-result">
      <h1>{t.resultTitle}</h1>
      <p>
        <strong lang="en">{result.title}</strong> ·{" "}
        {new Date(result.started_at).toLocaleString("vi-VN")}
        {result.finished_at === null && ` · ${t.unfinished}`}
      </p>
      <p className="en-muted">{t.resultIntro}</p>
      {result.questions.some((q) => q.answer?.transcript === "done") && (
        <p className="en-muted small">{t.transcriptNote}</p>
      )}
      <p className="en-muted">
        {result.keep
          ? t.keptNote
          : deleteAt &&
            `${t.deleteAt} ${new Date(deleteAt).toLocaleString("vi-VN")}.`}
      </p>
      <div className="nt-actions">
        {playing ? (
          <button
            type="button"
            className="en-button"
            onClick={() => stop.current?.abort()}
          >
            {t.stopPlay}
          </button>
        ) : (
          <button
            type="button"
            className="en-button"
            disabled={!result.questions.some((q) => q.answer?.audio)}
            onClick={() => void playAll()}
          >
            {t.playAll}
          </button>
        )}
        <Link className="en-button secondary" href="/noi/thi">
          {t.again}
        </Link>
      </div>
      {parts.map((part) => (
        <div key={part} className="nt-exam-part">
          <h2>{t.part(part)}</h2>
          {part === 2 && (
            <p lang="en" className="en-muted">
              {result.cue_card.task} {result.cue_card.points.join("; ")};{" "}
              {result.cue_card.explain}
            </p>
          )}
          <ol>
            {result.questions
              .filter((q) => q.part === part)
              .map((q) => (
                <li key={q.id} data-testid="exam-answer">
                  <p lang="en">{q.text}</p>
                  {q.answer === null ? (
                    <p className="en-muted">{t.notAnswered}</p>
                  ) : (
                    <>
                      {q.answer.audio ? (
                        <audio
                          controls
                          preload="none"
                          src={client.speakingAudioUrl(learner, q.answer.id)}
                        />
                      ) : (
                        <p className="en-muted">{t.gone}</p>
                      )}
                      {q.answer.transcript === "done" && (
                        <div className="nt-exam-transcript">
                          <p className="en-muted small">{t.transcript}</p>
                          <p lang="en">{q.answer.text}</p>
                        </div>
                      )}
                      {q.answer.transcript === "waiting" && (
                        <p className="en-muted small">{t.transcribing}</p>
                      )}
                      {q.answer.transcript === "failed" && (
                        <p className="en-muted small">{t.transcriptFailed}</p>
                      )}
                      <p className="en-muted small">
                        {t.seconds(q.answer.seconds)}
                        {q.answer.problems
                          .map((p) => t.problems[p])
                          .filter(Boolean)
                          .map((p) => ` · ${p}`)
                          .join("")}
                      </p>
                    </>
                  )}
                </li>
              ))}
          </ol>
        </div>
      ))}
      <div className="nt-actions">
        <button
          type="button"
          className="en-button ghost"
          onClick={() => void remove()}
        >
          {t.delete}
        </button>
        <Link href="/noi/thi">{t.back}</Link>
      </div>
    </section>
  );
}
