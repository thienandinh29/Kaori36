"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import { Problem } from "@/components/english/problem";
import { useLearner } from "@/components/english/use-learner";
import { englishClient } from "@/lib/english/client";
import {
  SPEED_KEY,
  clock,
  examSpeed,
  ms,
  progress,
  script,
  type Overview,
  type Question,
  type Sitting,
} from "@/lib/speaking/exam";
import { vi } from "@/messages/vi";
import {
  makeExaminer,
  recordAnswer,
  toWav,
  wait,
  type VoiceMode,
} from "./examiner";

const t = vi.english.speakingTest;
// The test's own notice (speaking-v1: the voice policy plus the transcript kept with the sitting).
const CONSENT_KEY = "nodetrail_speaking_consent";
const MIC_CHECK_SECONDS = 3;

function stored(key: string): string | null {
  try {
    return window.localStorage.getItem(key);
  } catch {
    return null;
  }
}

/** The phase 3 quality check on three seconds of the microphone (nothing is stored). */
function MicCheck({ learner, speed }: { learner: string; speed: number }) {
  const [state, setState] = useState<"idle" | "busy" | "ok" | "no-mic">("idle");
  const [problems, setProblems] = useState<string[]>([]);

  async function run() {
    setState("busy");
    setProblems([]);
    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch {
      setState("no-mic");
      return;
    }
    try {
      const signal = new AbortController().signal;
      const blob = await recordAnswer(
        stream,
        Math.max(1200, ms(MIC_CHECK_SECONDS, speed)),
        signal,
        () => undefined,
      );
      const r = await englishClient().speakingMicCheck(
        learner,
        await toWav(blob, MIC_CHECK_SECONDS + 1),
      );
      setProblems(r.problems);
      setState(r.ok ? "ok" : "idle");
    } catch {
      setProblems(["format"]);
      setState("idle");
    } finally {
      stream.getTracks().forEach((track) => track.stop());
    }
  }

  const pron = vi.english.pronunciation.problems;
  return (
    <div className="nt-actions" data-testid="mic-check">
      <button
        type="button"
        className="en-button secondary small"
        disabled={state === "busy"}
        onClick={() => void run()}
      >
        {t.micCheck}
      </button>
      <span role="status" className="en-muted">
        {state === "busy" && t.micChecking}
        {state === "ok" && t.micOk}
        {state === "no-mic" && t.noMic}
        {problems.map((p) => pron[p] ?? p).join(" ")}
      </span>
    </div>
  );
}

type View =
  | { kind: "say"; text: string }
  | { kind: "prepare" }
  | { kind: "answer"; question: Question }
  | { kind: "saving" };

/** The test itself: the examiner's script with the real timing; nothing is judged while speaking. */
function ExamRunner({
  learner,
  sitting,
  speed,
}: {
  learner: string;
  sitting: Sitting;
  speed: number;
}) {
  const router = useRouter();
  const steps = useMemo(() => script(sitting.test), [sitting]);
  const [index, setIndex] = useState(0);
  const [view, setView] = useState<View>({ kind: "say", text: "" });
  const [voice, setVoice] = useState<VoiceMode | null>(null);
  const [deadline, setDeadline] = useState<number | null>(null);
  const [now, setNow] = useState(() => Date.now());
  const [showCue, setShowCue] = useState(false);
  const [notes, setNotes] = useState("");
  const [failed, setFailed] = useState(0);
  const [noMic, setNoMic] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const stopAnswer = useRef<() => void>(() => undefined);
  const abort = useRef(new AbortController());
  const started = useRef(false);
  const alive = useRef(true);

  useEffect(() => {
    const id = window.setInterval(() => setNow(Date.now()), 250);
    return () => window.clearInterval(id);
  }, []);

  async function upload(blob: Blob, q: Question): Promise<boolean> {
    try {
      const wav = await toWav(blob, q.seconds + 4);
      await englishClient().speakingAnswer(learner, sitting.id, q.id, wav);
      return true;
    } catch {
      return false;
    }
  }

  async function run() {
    const signal = abort.current.signal;
    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch {
      setNoMic(true);
      return;
    }
    const examiner = await makeExaminer(speed);
    setVoice(examiner.mode);
    const pending: Promise<boolean>[] = [];
    try {
      for (let i = 0; i < steps.length && !signal.aborted; i++) {
        setIndex(i);
        const step = steps[i]!;
        if (step.kind === "say") {
          setView({ kind: "say", text: step.text });
          await examiner.say(step.text, signal);
        } else if (step.kind === "cue") {
          setShowCue(true);
          setView({ kind: "say", text: step.text });
          await examiner.say(step.text, signal);
        } else if (step.kind === "prepare") {
          const millis = ms(step.seconds, speed);
          setView({ kind: "prepare" });
          setDeadline(Date.now() + millis);
          await wait(millis, signal);
          setDeadline(null);
        } else if (step.kind === "ask") {
          if (step.speak) {
            setView({ kind: "say", text: step.question.text });
            await examiner.say(step.question.text, signal);
          }
          if (signal.aborted) break;
          const millis = ms(step.question.seconds, speed);
          setView({ kind: "answer", question: step.question });
          setDeadline(Date.now() + millis);
          const blob = await recordAnswer(stream, millis, signal, (stop) => {
            stopAnswer.current = stop;
          });
          setDeadline(null);
          if (step.question.id === "p2-long") setShowCue(false);
          pending.push(upload(blob, step.question));
        }
      }
    } finally {
      stream.getTracks().forEach((track) => track.stop());
    }
    setView({ kind: "saving" });
    const saved = await Promise.all(pending);
    const lost = saved.filter((ok) => !ok).length;
    try {
      await englishClient().finishSpeakingTest(learner, sitting.id);
    } catch (e) {
      setError(e);
      return;
    }
    if (lost > 0) setFailed(lost);
    else router.push(`/noi/thi/${sitting.id}`);
  }

  useEffect(() => {
    alive.current = true;
    const controller = abort.current;
    if (!started.current) {
      started.current = true;
      void run();
    }
    return () => {
      alive.current = false;
      // A real unmount stops the test; React's development double mount does not.
      window.setTimeout(() => {
        if (!alive.current) controller.abort();
      }, 0);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function stopTest() {
    if (window.confirm(t.confirmStop)) abort.current.abort();
  }

  if (noMic) return <p className="en-feedback is-wrong">{t.noMic}</p>;
  if (error) return <Problem error={error} />;
  if (failed > 0)
    return (
      <section className="en-card" data-testid="exam-saved">
        <p className="en-feedback is-wrong">{t.saveFailed(failed)}</p>
        <Link className="en-button" href={`/noi/thi/${sitting.id}`}>
          {t.resultTitle}
        </Link>
      </section>
    );

  const where = progress(steps, index);
  const left = deadline === null ? null : (deadline - now) / 1000 / speed;
  const card = sitting.test.cue_card;
  return (
    <section className="en-card nt-exam" data-testid="exam">
      <div className="nt-exam-head">
        <strong>{t.part(where.part)}</strong>
        <span className="en-muted">
          {t.progress(where.question, where.total)}
        </span>
        {view.kind !== "saving" && (
          <button
            type="button"
            className="en-button ghost small"
            onClick={stopTest}
          >
            {t.stop}
          </button>
        )}
      </div>

      {showCue && (
        <div className="nt-exam-cue" data-testid="cue-card">
          <p className="en-muted">{t.cueTitle}</p>
          <p lang="en">
            <strong>{card.task}</strong>
          </p>
          <p className="en-muted">{t.youShouldSay}</p>
          <ul lang="en">
            {card.points.map((p) => (
              <li key={p}>{p}</li>
            ))}
          </ul>
          <p lang="en">{card.explain}</p>
          <label className="nt-exam-notes">
            {t.notes}
            <textarea
              rows={4}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
            />
          </label>
        </div>
      )}

      <div className="nt-exam-now" role="status" aria-live="polite">
        {view.kind === "say" && (
          <>
            <p className="en-muted">{t.listening}</p>
            {voice === "none" && (
              <p className="nt-exam-line" lang="en">
                {view.text}
              </p>
            )}
          </>
        )}
        {view.kind === "prepare" && (
          <p>
            {t.prepare}: <strong>{left === null ? "" : clock(left)}</strong>
          </p>
        )}
        {view.kind === "answer" && (
          <>
            {voice === "none" && view.question.id !== "p2-long" && (
              <p className="nt-exam-line" lang="en">
                {view.question.text}
              </p>
            )}
            <p>
              <span className="nt-exam-dot" aria-hidden /> {t.recording} ·{" "}
              {t.left} <strong>{left === null ? "" : clock(left)}</strong>
            </p>
            <button
              type="button"
              className="en-button"
              onClick={() => stopAnswer.current()}
            >
              {t.done}
            </button>
          </>
        )}
        {view.kind === "saving" && <p>{t.saving}</p>}
      </div>
      {voice === "none" && <p className="en-muted small">{t.noVoice}</p>}
    </section>
  );
}

/** The Speaking examiner test (specs/speaking/step-5.4a.md), owner only: choose a test, sit it, replay it. */
export function ExamPage() {
  const { learner, error: learnerError, retry } = useLearner();
  const [overview, setOverview] = useState<Overview | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [consented, setConsented] = useState(
    () =>
      typeof window !== "undefined" && stored(CONSENT_KEY) === "speaking-v1",
  );
  const [keep, setKeep] = useState(false);
  const [sitting, setSitting] = useState<Sitting | null>(null);
  const [busy, setBusy] = useState(false);
  const [speed] = useState(() =>
    typeof window === "undefined" ? 1 : examSpeed(stored(SPEED_KEY)),
  );

  useEffect(() => {
    if (!learner) return;
    let live = true;
    englishClient()
      .speakingTests(learner)
      .then((o) => live && setOverview(o))
      .catch((e: unknown) => live && setError(e));
    return () => {
      live = false;
    };
  }, [learner]);

  if (learnerError) return <Problem error={learnerError} onRetry={retry} />;
  if (error) return <Problem error={error} />;
  if (!overview || !learner)
    return <p className="en-muted">{vi.english.loading}</p>;
  if (sitting)
    return <ExamRunner learner={learner} sitting={sitting} speed={speed} />;

  async function start(testId: string) {
    setBusy(true);
    try {
      setSitting(
        await englishClient().startSpeakingTest(
          learner!,
          testId,
          overview!.consent,
          keep,
        ),
      );
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="en-card nt-exam" data-testid="speaking-test">
      <h1>{t.title}</h1>
      <p className="en-muted">{t.intro}</p>
      {!overview.can_record ? (
        <p className="en-badge draft">{t.ownerOnly}</p>
      ) : !consented ? (
        <div className="nt-pron-consent">
          <p>{t.consent}</p>
          <label>
            <input
              type="checkbox"
              onChange={(e) => {
                if (!e.target.checked) return;
                setConsented(true);
                try {
                  window.localStorage.setItem(CONSENT_KEY, overview.consent);
                } catch {
                  // asked again next time
                }
              }}
            />{" "}
            {t.consentAgree}
          </label>
        </div>
      ) : (
        <>
          <MicCheck learner={learner} speed={speed} />
          <label className="nt-pron-keep">
            <input
              type="checkbox"
              checked={keep}
              onChange={(e) => setKeep(e.target.checked)}
            />{" "}
            {t.keep}
          </label>
          <h2>{t.tests}</h2>
          <ul className="nt-exam-tests">
            {overview.tests.map((x) => (
              <li key={x.id}>
                <span>
                  <strong lang="en">{x.title}</strong>{" "}
                  {x.draft && (
                    <span className="en-badge draft">{vi.english.draft}</span>
                  )}{" "}
                  <span className="en-muted">{t.questions(x.questions)}</span>
                </span>
                <button
                  type="button"
                  className="en-button small"
                  disabled={busy}
                  onClick={() => void start(x.id)}
                >
                  {t.start}
                </button>
              </li>
            ))}
          </ul>
        </>
      )}
      {overview.can_record && (
        <>
          <h2>{t.past}</h2>
          {overview.past.length === 0 ? (
            <p className="en-muted">{t.noPast}</p>
          ) : (
            <ul className="nt-exam-past" data-testid="past-tests">
              {overview.past.map((p) => (
                <li key={p.id}>
                  <Link href={`/noi/thi/${p.id}`}>
                    <span lang="en">{p.title}</span> ·{" "}
                    {new Date(p.started_at).toLocaleString("vi-VN")}
                  </Link>{" "}
                  <span className="en-muted">
                    {t.answered(p.answers)}
                    {p.finished_at === null && ` · ${t.unfinished}`}
                    {p.answers > 0 && p.with_audio === 0 && ` · ${t.audioGone}`}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </section>
  );
}
