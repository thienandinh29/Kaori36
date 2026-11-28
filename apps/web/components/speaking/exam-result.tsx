"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { Problem } from "@/components/english/problem";
import { useLearner } from "@/components/english/use-learner";
import { englishClient } from "@/lib/english/client";
import type {
  Answered,
  Language,
  Measures,
  Part,
  Result,
  Summary,
} from "@/lib/speaking/exam";
import { vi } from "@/messages/vi";
import { makeExaminer } from "./examiner";

const t = vi.english.speakingTest;

/** The numbers of one answer, said plainly: counts only, no verdict (step 5.2). */
function MeasuresLine({ m }: { m: Measures }) {
  if (m.words === 0) return null;
  const parts = [
    m.speech_rate === null ? null : t.measuresRate(m.speech_rate),
    t.measuresPauses(
      m.pauses.count,
      m.pauses.between_clauses,
      m.pauses.inside_clause,
      m.pauses.long,
    ),
    t.measuresFillers(m.fillers),
    t.measuresRun(m.longest_run.words, m.longest_run.seconds),
    m.share_of_time === null ? null : t.measuresShare(m.share_of_time),
  ].filter((x): x is string => x !== null);
  return (
    <p className="en-muted small" data-testid="exam-measures">
      {parts.join(" · ")}
      {m.short && <> · {t.measuresShort}</>}
    </p>
  );
}

/** What the checks found in one answer, said as hints: never errors, never a score (step 5.3a). */
function LanguageBlock({
  language,
  onPlay,
}: {
  language: Language;
  /** Plays the answer's recording between two moments; absent when the audio is gone. */
  onPlay?: (from: number, to: number) => void;
}) {
  if (language.state === "short")
    return <p className="en-muted small">{t.languageShort}</p>;
  if (language.state === "failed")
    return <p className="en-muted small">{t.languageFailed}</p>;
  const { guard, vocabulary: v, hints } = language;
  const warnings = [
    guard.templates.length > 0
      ? t.guardTemplates(guard.templates.join("; "))
      : null,
    guard.repeated_words > 0 ? t.guardRepeated(guard.repeated_words) : null,
    guard.off_topic ? t.guardOffTopic : null,
  ].filter((x): x is string => x !== null);
  const vocab = [
    v.mtld === null ? t.vocabTooShort : t.vocabDiversity(v.mtld),
    v.beyond_b1_share === null ? null : t.vocabBeyond(v.beyond_b1_share),
    v.unknown_share === null || v.unknown_share === 0
      ? null
      : t.vocabUnknown(v.unknown_share),
    v.repeated.length > 0
      ? t.vocabRepeated(
          v.repeated.map((r) => `${r.word} (${r.count})`).join(", "),
        )
      : null,
  ].filter((x): x is string => x !== null);
  return (
    <div className="nt-exam-language" data-testid="exam-language">
      {warnings.length > 0 && (
        <div data-testid="exam-guard">
          <p className="en-muted small">
            <strong>{t.languageGuard}</strong>
          </p>
          {warnings.map((w) => (
            <p key={w} className="en-muted small">
              {w}
            </p>
          ))}
        </div>
      )}
      <p className="en-muted small">
        <strong>{t.hintsTitle}</strong>
      </p>
      {hints === null ? (
        <p className="en-muted small">{t.hintsNotChecked}</p>
      ) : hints.length === 0 ? (
        <p className="en-muted small">{t.hintsNone}</p>
      ) : (
        <ul className="nt-exam-hints" data-testid="exam-hints">
          {hints.map((h, i) => (
            <li key={`${h.text}-${i}`}>
              <span lang="en">
                {h.suggestion
                  ? t.hintSuggest(h.text, h.suggestion)
                  : `“${h.text}”`}
              </span>{" "}
              <span className="en-muted small">
                {h.kind === "ending" ? t.hintEnding : h.message_en}
              </span>{" "}
              {h.start_s !== null && h.end_s !== null && onPlay && (
                <button
                  type="button"
                  className="en-button ghost small"
                  onClick={() => onPlay(h.start_s!, h.end_s!)}
                >
                  {t.hintPlay}
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
      {hints !== null && <p className="en-muted small">{t.hintsNote}</p>}
      <p className="en-muted small" data-testid="exam-vocab">
        <strong>{t.vocabTitle}:</strong> {vocab.join(" · ")}
      </p>
    </div>
  );
}

/** One answer: its recording, transcript, numbers and checks, with the audio the hints can play. */
function AnswerView({ answer, url }: { answer: Answered; url: string }) {
  const audio = useRef<HTMLAudioElement | null>(null);
  const play = (from: number, to: number) => {
    const el = audio.current;
    if (!el) return;
    el.currentTime = Math.max(0, from - 0.3);
    void el.play();
    window.setTimeout(
      () => el.pause(),
      Math.max(800, (to - from + 0.6) * 1000),
    );
  };
  return (
    <>
      {answer.audio ? (
        <audio ref={audio} controls preload="none" src={url} />
      ) : (
        <p className="en-muted">{t.gone}</p>
      )}
      {answer.transcript === "done" && (
        <div className="nt-exam-transcript">
          <p className="en-muted small">{t.transcript}</p>
          <p lang="en">{answer.text}</p>
        </div>
      )}
      {answer.measures && <MeasuresLine m={answer.measures} />}
      {answer.language && (
        <LanguageBlock
          language={answer.language}
          onPlay={answer.audio ? play : undefined}
        />
      )}
      {answer.transcript === "waiting" && (
        <p className="en-muted small">{t.transcribing}</p>
      )}
      {answer.transcript === "failed" && (
        <p className="en-muted small">{t.transcriptFailed}</p>
      )}
      <p className="en-muted small">
        {t.seconds(answer.seconds)}
        {answer.problems
          .map((p) => t.problems[p])
          .filter(Boolean)
          .map((p) => ` · ${p}`)
          .join("")}
      </p>
    </>
  );
}

function SummaryBlock({ s }: { s: Summary }) {
  const parts = [
    s.speech_rate === null ? null : t.measuresRate(s.speech_rate),
    s.pauses_per_minute === null
      ? null
      : t.summaryPerMinute(s.pauses_per_minute),
    t.measuresPauses(
      s.between_clauses + s.inside_clause,
      s.between_clauses,
      s.inside_clause,
      s.long,
    ),
    t.measuresFillers(s.fillers),
    t.summaryLine(s.answers, s.words),
  ].filter((x): x is string => x !== null);
  return (
    <div className="nt-exam-transcript" data-testid="exam-summary">
      <p>
        <strong>{t.summaryTitle}</strong>
      </p>
      <p className="en-muted small">{parts.join(" · ")}</p>
      <p className="en-muted small">{t.measuresNote}</p>
    </div>
  );
}

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
      {result.summary && <SummaryBlock s={result.summary} />}
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
                    <AnswerView
                      answer={q.answer}
                      url={client.speakingAudioUrl(learner, q.answer.id)}
                    />
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
