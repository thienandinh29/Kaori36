"use client";
import Link from "next/link";
import { useEffect, useMemo, useReducer, useState } from "react";
import { englishClient } from "@/lib/english/client";
import { narrate, stopNarration } from "@/lib/lesson/narrate";
import {
  initial,
  marks,
  reduce,
  screenAt,
  steps,
  subtitleDefaults,
  type PlayerEvent,
  type PlayerState,
} from "@/lib/lesson/player";
import type { CheckpointResult, LessonView } from "@/lib/lesson/types";
import { vi } from "@/messages/vi";
import { Sena } from "@/components/sena/sena";
import { Problem } from "@/components/english/problem";
import { SpeakButton } from "@/components/english/speak-button";
import { useLearner } from "@/components/english/use-learner";
import { Board } from "./board";

const t = vi.english.lesson;
const SUBTITLE_KEY = "nodetrail_lesson_subtitles";

function Marked({ text, targets }: { text: string; targets: string[] }) {
  return (
    <>
      {marks(text, targets).map((m, i) =>
        m.mark ? <mark key={i}>{m.text}</mark> : <span key={i}>{m.text}</span>,
      )}
    </>
  );
}

function storedSubtitles(level: LessonView["level"]): {
  en: boolean;
  vi: boolean;
} {
  try {
    const raw = window.localStorage.getItem(`${SUBTITLE_KEY}_${level}`);
    if (raw) {
      const v = JSON.parse(raw) as unknown;
      if (
        v &&
        typeof v === "object" &&
        typeof (v as { en?: unknown }).en === "boolean" &&
        typeof (v as { vi?: unknown }).vi === "boolean"
      )
        return v as { en: boolean; vi: boolean };
    }
  } catch {
    // private mode: the level's defaults
  }
  return subtitleDefaults(level);
}

/** Loads a lesson for this learner and plays it (specs/grammar-lessons). */
export function LessonPage({ node }: { node: string }) {
  const { learner, error: learnerError, retry } = useLearner();
  const [lesson, setLesson] = useState<LessonView | null>(null);
  const [error, setError] = useState<unknown>(null);
  useEffect(() => {
    if (!learner) return;
    let live = true;
    englishClient()
      .lesson(learner, node)
      .then((l) => live && setLesson(l))
      .catch((e: unknown) => live && setError(e));
    return () => {
      live = false;
    };
  }, [learner, node]);
  if (learnerError) return <Problem error={learnerError} onRetry={retry} />;
  if (error) return <Problem error={error} />;
  if (!lesson || !learner)
    return <p className="en-muted">{vi.english.loading}</p>;
  return <LessonPlayer lesson={lesson} learner={learner} />;
}

export function LessonPlayer({
  lesson,
  learner,
}: {
  lesson: LessonView;
  learner: string;
}) {
  const [state, dispatch] = useReducer(
    (s: PlayerState, e: PlayerEvent) => reduce(lesson, s, e),
    undefined,
    initial,
  );
  const [subs, setSubs] = useState(() =>
    typeof window === "undefined"
      ? subtitleDefaults(lesson.level)
      : storedSubtitles(lesson.level),
  );
  const [muted, setMuted] = useState(false); // nothing could speak: the learner reads and taps "Tiếp"
  const [answers, setAnswers] = useState<Record<string, CheckpointResult>>({});
  const [busy, setBusy] = useState(false);
  const all = useMemo(() => steps(lesson), [lesson]);
  const targets = useMemo(
    () =>
      lesson.scenes.flatMap((s) =>
        s.actions.flatMap((a) => (a.do === "show_example" ? [a.target] : [])),
      ),
    [lesson],
  );
  const screen = state.index >= 0 ? screenAt(lesson, state.index) : null;
  const step = state.index >= 0 ? all[state.index] : undefined;
  // Sena speaks each `say` while playing; when she finishes, the lesson moves on by itself.
  useEffect(() => {
    if (state.status !== "playing" || step?.action.do !== "say") return;
    let cancelled = false;
    void narrate(step.action.en, "normal").then((heard) => {
      if (cancelled) return;
      if (heard) dispatch({ type: "next" });
      else setMuted(true);
    });
    return () => {
      cancelled = true;
      stopNarration();
    };
  }, [state.status, state.index, step]);

  useEffect(() => () => stopNarration(), []);

  function toggle(which: "en" | "vi") {
    const next = { ...subs, [which]: !subs[which] };
    setSubs(next);
    try {
      window.localStorage.setItem(
        `${SUBTITLE_KEY}_${lesson.level}`,
        JSON.stringify(next),
      );
    } catch {
      // remembered for this page only
    }
  }

  async function answer(checkpoint: string, option: string) {
    setBusy(true);
    try {
      const r = await englishClient().lessonCheckpoint(
        learner,
        lesson.node,
        checkpoint,
        option,
      );
      setAnswers((a) => ({ ...a, [checkpoint]: r }));
    } finally {
      setBusy(false);
    }
  }

  const label =
    lesson.status === "sample"
      ? t.sample
      : lesson.status === "draft"
        ? t.draft
        : null;
  const checkpoint = screen?.ask
    ? lesson.checkpoints.find((c) => c.id === screen.ask)
    : undefined;
  const result = checkpoint ? answers[checkpoint.id] : undefined;
  const waitingForAnswer = !!checkpoint && !result;
  const sayingNow = step?.action.do === "say" ? step.action : null;

  return (
    <article className="en-card nt-lesson" data-testid="lesson">
      <header className="nt-lesson-head">
        <p className="en-muted">{lesson.level}</p>
        <h1>{lesson.title_vi}</h1>
        <p className="en-muted" lang="en">
          {lesson.title_en}
        </p>
        {label && <p className="en-badge draft nt-lesson-label">{label}</p>}
        <progress
          className="nt-lesson-progress"
          aria-label={t.progress}
          max={all.length}
          value={
            state.status === "done" ? all.length : Math.max(0, state.index + 1)
          }
        />
      </header>

      {state.status === "idle" ? (
        <div className="nt-lesson-start">
          <Sena pose="idle" label={lesson.title_vi} />
          <button
            type="button"
            className="en-button"
            autoFocus
            onClick={() => dispatch({ type: "start" })}
          >
            {t.start}
          </button>
          <Link
            className="en-button ghost"
            href={`/on-tap/phan/${lesson.node}`}
          >
            {t.skip}
          </Link>
        </div>
      ) : state.status === "done" ? (
        <div className="nt-lesson-done">
          <Sena pose="idle" label={t.done} />
          <p>{t.done}</p>
          <div className="nt-actions">
            <Link className="en-button" href={`/on-tap/phan/${lesson.node}`}>
              {t.practise}
            </Link>
            <Link className="en-button ghost" href="/lo-trinh">
              {t.back}
            </Link>
          </div>
        </div>
      ) : (
        screen && (
          <>
            <div className="nt-lesson-stage">
              <Board items={screen.board} />
              {screen.examples.map((e) => (
                <div
                  key={e.id}
                  className={`nt-example${screen.spotlight === e.id ? " is-spotlit" : ""}`}
                >
                  <p lang="en">
                    <Marked text={e.en} targets={[e.target]} />{" "}
                    <SpeakButton text={e.en} />
                  </p>
                  <p className="en-muted">{e.vi}</p>
                </div>
              ))}
              {checkpoint && (
                <div
                  className="nt-checkpoint"
                  role="group"
                  aria-label={t.answerPrompt}
                >
                  <p lang="en">
                    <b>{checkpoint.en}</b> <SpeakButton text={checkpoint.en} />
                  </p>
                  {subs.vi && <p className="en-muted">{checkpoint.vi}</p>}
                  <div className="nt-options">
                    {checkpoint.options.map((o) => (
                      <button
                        key={o}
                        type="button"
                        className={`en-option${result?.key === o ? " is-key" : ""}`}
                        disabled={busy || !!result}
                        onClick={() => void answer(checkpoint.id, o)}
                        lang="en"
                      >
                        {o}
                      </button>
                    ))}
                  </div>
                  {result && (
                    <div
                      className={`en-feedback ${result.correct ? "is-right" : "is-wrong"}`}
                      role="status"
                    >
                      <strong>{result.correct ? t.right : t.wrong}</strong>
                      {!result.correct && (
                        <p>
                          {t.answerWas}: <b lang="en">{result.key}</b>
                        </p>
                      )}
                      <p>{result.explain_vi}</p>
                      {result.misconception_vi && !result.correct && (
                        <p className="en-muted">{result.misconception_vi}</p>
                      )}
                    </div>
                  )}
                  <p className="en-muted nt-check-note">{t.checkNote}</p>
                </div>
              )}
              {screen.pause && <p className="nt-think">{t.think}</p>}
            </div>

            <div className="nt-subtitles" aria-live="polite">
              {screen.subtitle && subs.en && (
                <p className="nt-sub-en" lang="en">
                  <Marked text={screen.subtitle.en} targets={targets} />
                </p>
              )}
              {screen.subtitle && subs.vi && (
                <p className="nt-sub-vi">{screen.subtitle.vi}</p>
              )}
              {muted && <p className="en-muted">{t.noVoice}</p>}
            </div>

            <div className="nt-lesson-controls">
              <button
                type="button"
                className="en-button ghost"
                onClick={() => dispatch({ type: "previous" })}
              >
                {t.previous}
              </button>
              {state.status === "paused" ? (
                <button
                  type="button"
                  className="en-button ghost"
                  onClick={() => dispatch({ type: "resume" })}
                >
                  {t.resume}
                </button>
              ) : (
                <button
                  type="button"
                  className="en-button ghost"
                  onClick={() => dispatch({ type: "pause" })}
                >
                  {t.pause}
                </button>
              )}
              {sayingNow && (
                <>
                  <button
                    type="button"
                    className="en-button ghost"
                    onClick={() => void narrate(sayingNow.en, "normal")}
                  >
                    {t.replay}
                  </button>
                  <button
                    type="button"
                    className="en-button ghost"
                    onClick={() => void narrate(sayingNow.en, "slow")}
                  >
                    {t.slow}
                  </button>
                </>
              )}
              <button
                type="button"
                className="en-button"
                disabled={waitingForAnswer}
                onClick={() => {
                  stopNarration();
                  dispatch({ type: "next" });
                }}
              >
                {t.next}
              </button>
            </div>
            <div
              className="nt-subtitle-toggles"
              role="group"
              aria-label={t.subtitles}
            >
              <span className="en-muted">{t.subtitles}:</span>
              <label>
                <input
                  type="checkbox"
                  checked={subs.en}
                  onChange={() => toggle("en")}
                />{" "}
                {t.subtitleEn}
              </label>
              <label>
                <input
                  type="checkbox"
                  checked={subs.vi}
                  onChange={() => toggle("vi")}
                />{" "}
                {t.subtitleVi}
              </label>
              <Link className="nt-skip" href={`/on-tap/phan/${lesson.node}`}>
                {t.skip}
              </Link>
            </div>
          </>
        )
      )}

      {lesson.sources.length > 0 && (
        <footer className="en-muted nt-lesson-sources">
          {t.sources}:{" "}
          {lesson.sources
            .map((s) => `${s.candidate} ${s.chapter} (${s.licence})`)
            .join("; ")}
        </footer>
      )}
    </article>
  );
}
