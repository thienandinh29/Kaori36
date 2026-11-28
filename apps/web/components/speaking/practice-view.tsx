"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { Problem } from "@/components/english/problem";
import { useLearner } from "@/components/english/use-learner";
import { englishClient } from "@/lib/english/client";
import {
  CONSENT,
  SPEED_KEY,
  clock,
  examSpeed,
  ms,
  type CueCard,
} from "@/lib/speaking/exam";
import {
  compareRows,
  pending,
  type Practice,
  type Try,
} from "@/lib/speaking/practice";
import { vi } from "@/messages/vi";
import { AnswerView } from "./exam-result";
import { makeExaminer, recordAnswer, toWav, wait } from "./examiner";

const t = vi.english.speakingPractice;
const PREPARE_SECONDS = 60; // Part 2, first try only (the strict test's own minute)
const POLL_MS = 3000;
const POLL_LIMIT = 40; // about two minutes: the worker is a separate process

type Phase = "ready" | "prepare" | "recording" | "saving";

/** Help for building an answer, shown before speaking and never during it (strict-mode rule). */
function Ideas({ practice }: { practice: Practice }) {
  const part = practice.question.part;
  if (part === 1) return null;
  const shape = part === 3 ? [...t.shape, ...t.shapePart3] : t.shape;
  return (
    <div className="nt-exam-cue" data-testid="ideas">
      <p>
        <strong>{t.ideasTitle}</strong>
      </p>
      <p className="en-muted small">{t.shapeTitle}</p>
      <ol>
        {shape.map((s) => (
          <li key={s}>{s}</li>
        ))}
      </ol>
      <p className="en-muted small">{t.openersTitle}</p>
      <ul>
        {t.openers.map((o) => (
          <li key={o}>{o}</li>
        ))}
      </ul>
      {practice.words.length > 0 && (
        <>
          <p className="en-muted small">
            {t.wordsTitle}: <span lang="en">{practice.words.join(", ")}</span>
          </p>
          <p className="en-muted small">{t.wordsNote}</p>
        </>
      )}
      <p className="en-muted small">{t.noScript}</p>
    </div>
  );
}

function Cue({
  card,
  notes,
  onNotes,
}: {
  card: CueCard;
  notes: string;
  onNotes: (v: string) => void;
}) {
  return (
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
          rows={3}
          value={notes}
          onChange={(e) => onNotes(e.target.value)}
        />
      </label>
    </div>
  );
}

/** One try: the question, the help (before speaking only), the timer, the recording, the upload. */
function TryRunner({
  learner,
  practice,
  current,
  speed,
  onDone,
}: {
  learner: string;
  practice: Practice;
  current: Try;
  speed: number;
  onDone: () => void;
}) {
  const [phase, setPhase] = useState<Phase>("ready");
  const [deadline, setDeadline] = useState<number | null>(null);
  const [notes, setNotes] = useState("");
  const [problem, setProblem] = useState<"mic" | "save" | null>(null);
  const [now, setNow] = useState(() => Date.now());
  const stop = useRef<() => void>(() => undefined);
  const skip = useRef<AbortController | null>(null);
  const abort = useRef(new AbortController());
  const question = practice.question;

  useEffect(() => {
    const id = window.setInterval(() => setNow(Date.now()), 250);
    const controller = abort.current;
    return () => {
      window.clearInterval(id);
      controller.abort();
    };
  }, []);

  async function begin() {
    setProblem(null);
    const signal = abort.current.signal;
    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch {
      setProblem("mic");
      return;
    }
    try {
      if (question.part === 2 && current.try_no === 1) {
        const millis = ms(PREPARE_SECONDS, speed);
        setPhase("prepare");
        setDeadline(Date.now() + millis);
        skip.current = new AbortController();
        const either = AbortSignal.any([signal, skip.current.signal]);
        await wait(millis, either);
        setDeadline(null);
      }
      if (question.part !== 2) {
        const examiner = await makeExaminer(speed);
        await examiner.say(question.text, signal);
      }
      if (signal.aborted) return;
      const millis = ms(current.asked_seconds, speed);
      setPhase("recording");
      setDeadline(Date.now() + millis);
      const blob = await recordAnswer(stream, millis, signal, (s) => {
        stop.current = s;
      });
      setDeadline(null);
      if (signal.aborted) return;
      setPhase("saving");
      try {
        const client = englishClient();
        const wav = await toWav(blob, current.asked_seconds + 4);
        await client.speakingAnswer(learner, current.id, question.id, wav);
        await client.finishSpeakingTest(learner, current.id);
      } catch {
        setProblem("save");
        setPhase("ready");
        return;
      }
      onDone();
    } finally {
      stream.getTracks().forEach((track) => track.stop());
    }
  }

  const left = deadline === null ? null : (deadline - now) / 1000 / speed;

  return (
    <section className="en-card nt-exam" data-testid="practice-runner">
      <h1>{t.tryTitle(current.try_no, current.asked_seconds)}</h1>
      <p lang="en">
        <strong>{question.text}</strong>
      </p>
      {phase === "ready" && <Ideas practice={practice} />}
      {practice.cue_card && phase !== "saving" && (
        <Cue card={practice.cue_card} notes={notes} onNotes={setNotes} />
      )}
      {phase === "ready" && (
        <div className="nt-actions">
          <button
            type="button"
            className="en-button"
            onClick={() => void begin()}
          >
            {t.startSpeak(current.asked_seconds)}
          </button>
        </div>
      )}
      {phase === "prepare" && (
        <div className="nt-exam-now" role="status" aria-live="polite">
          <p>
            {t.prepare}: <strong>{left === null ? "" : clock(left)}</strong>
          </p>
          <button
            type="button"
            className="en-button secondary"
            onClick={() => skip.current?.abort()}
          >
            {t.skipPrep}
          </button>
        </div>
      )}
      {phase === "recording" && (
        <div className="nt-exam-now" role="status" aria-live="polite">
          <p>
            <span className="nt-exam-dot" aria-hidden /> {t.recording} ·{" "}
            {t.left} <strong>{left === null ? "" : clock(left)}</strong>
          </p>
          <button
            type="button"
            className="en-button"
            onClick={() => stop.current()}
          >
            {t.done}
          </button>
        </div>
      )}
      {phase === "saving" && <p role="status">{t.saving}</p>}
      {problem === "mic" && <p className="en-feedback is-wrong">{t.noMic}</p>}
      {problem === "save" && (
        <p className="en-feedback is-wrong">{t.saveFailed}</p>
      )}
    </section>
  );
}

const fmt = (key: string, v: number): string =>
  key === "shareOfTime"
    ? `${Math.round(v * 100)}%`
    : String(Math.round(v * 10) / 10);

/** The numbers of every try side by side: counts only, no arrows, no better or worse. */
function Comparison({ tries }: { tries: readonly Try[] }) {
  const rows = compareRows(tries);
  if (rows.every((r) => r.values.every((v) => v === null))) return null;
  return (
    <div className="nt-exam-transcript" data-testid="compare">
      <p>
        <strong>{t.compareTitle}</strong>
      </p>
      <table className="nt-exam-compare">
        <thead>
          <tr>
            <th />
            {tries.map((x) => (
              <th key={x.id}>{t.colTry(x.try_no)}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.key}>
              <th scope="row">{t.rows[r.key]}</th>
              {r.values.map((v, i) => (
                <td key={tries[i]!.id}>
                  {v === null ? t.noValue : fmt(r.key, v)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      <p className="en-muted small">{t.compareNote}</p>
    </div>
  );
}

/** A practised question (specs/speaking/step-5.4b.md): the try to speak, or the tries so far. */
export function PracticeView({ tryId }: { tryId: string }) {
  const router = useRouter();
  const { learner, error: learnerError, retry } = useLearner();
  const [practice, setPractice] = useState<Practice | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [polls, setPolls] = useState(0);
  const [busy, setBusy] = useState(false);
  const [speed] = useState(() =>
    typeof window === "undefined" ? 1 : examSpeed(stored(SPEED_KEY)),
  );

  const [tick, setTick] = useState(0); // bumped to read the practice again

  useEffect(() => {
    if (!learner) return;
    let live = true;
    englishClient()
      .speakingPractice(learner, tryId)
      .then((p) => live && setPractice(p))
      .catch((e: unknown) => live && setError(e));
    return () => {
      live = false;
    };
  }, [learner, tryId, tick]);

  useEffect(() => {
    if (!practice || polls >= POLL_LIMIT || !pending(practice.tries)) return;
    const id = window.setTimeout(() => {
      setPolls((n) => n + 1);
      setTick((n) => n + 1);
    }, POLL_MS);
    return () => window.clearTimeout(id);
  }, [practice, polls]);

  if (learnerError) return <Problem error={learnerError} onRetry={retry} />;
  if (error) return <Problem error={error} />;
  if (!practice || !learner)
    return <p className="en-muted">{vi.english.loading}</p>;

  const current = practice.tries.find((x) => x.id === tryId);
  if (current && current.answer === null && !current.finished)
    return (
      <TryRunner
        key={current.id}
        learner={learner}
        practice={practice}
        current={current}
        speed={speed}
        onDone={() => {
          setPolls(0);
          setTick((n) => n + 1);
        }}
      />
    );

  const last = practice.tries[practice.tries.length - 1];
  async function repeat() {
    if (!last) return;
    setBusy(true);
    try {
      const made = await englishClient().startSpeakingPractice(learner!, {
        testId: practice!.test_id,
        questionId: practice!.question.id,
        consent: CONSENT,
        keep: practice!.keep,
        previousId: last.id,
      });
      router.push(`/noi/luyen/${made.id}`);
    } catch (e) {
      setError(e);
      setBusy(false);
    }
  }

  async function remove() {
    if (!window.confirm(t.confirmDelete)) return;
    try {
      await englishClient().deleteSpeakingTest(learner!, practice!.id);
      router.push("/noi/luyen");
    } catch (e) {
      setError(e);
    }
  }

  const client = englishClient();
  return (
    <section className="en-card nt-exam" data-testid="practice-result">
      <h1>{t.title}</h1>
      <p>
        <span className="en-muted small">
          {t.part(practice.question.part)} · {practice.title}
        </span>
        <br />
        <strong lang="en">{practice.question.text}</strong>
      </p>
      <Comparison tries={practice.tries} />
      {pending(practice.tries) && <p className="en-muted small">{t.waiting}</p>}
      {practice.tries.map((x) => (
        <div key={x.id} className="nt-exam-part" data-testid="practice-try">
          <h2>{t.tryTitle(x.try_no, x.asked_seconds)}</h2>
          <p className="en-muted small">
            {x.counts_as_evidence ? t.firstTry : t.repeatTry}
          </p>
          {x.answer && (
            <AnswerView
              answer={x.answer}
              url={client.speakingAudioUrl(learner, x.answer.id)}
            />
          )}
        </div>
      ))}
      <div className="nt-actions">
        {practice.next_seconds !== null ? (
          <button
            type="button"
            className="en-button"
            disabled={busy}
            onClick={() => void repeat()}
          >
            {t.repeat(practice.next_seconds)}
          </button>
        ) : (
          practice.tries.length >= practice.max_tries && (
            <p className="en-muted">{t.usedUp}</p>
          )
        )}
        <Link className="en-button secondary" href="/noi/luyen">
          {t.another}
        </Link>
        <button
          type="button"
          className="en-button ghost"
          onClick={() => void remove()}
        >
          {t.delete}
        </button>
      </div>
    </section>
  );
}

function stored(key: string): string | null {
  try {
    return window.localStorage.getItem(key);
  } catch {
    return null;
  }
}
