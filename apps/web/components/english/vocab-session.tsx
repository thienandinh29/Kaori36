"use client";
import { useEffect, useState } from "react";
import { englishClient } from "@/lib/english/client";
import type {
  Level,
  Question,
  VocabAnswer,
  VocabLevels,
  VocabSession as Session,
} from "@/lib/english/types";
import { emptyVocabReason, newWordsToday } from "@/lib/english/view";
import { vi } from "@/messages/vi";
import { Sena } from "@/components/sena/sena";
import { Problem } from "./problem";
import { QuestionCard } from "./question-card";
import { TraceNote } from "./trace-note";
import { useLearner } from "./use-learner";
import { VocabLevelPicker, VocabTopicPicker } from "./vocab-levels";
import { WordCard } from "./word-card";

const t = vi.english;
const LEVEL_KEY = "nodetrail_vocab_level";
const TOPIC_KEY = "nodetrail_vocab_topic";

function storedTopic(): string {
  try {
    return window.localStorage.getItem(TOPIC_KEY) ?? "";
  } catch {
    return "";
  }
}

/** Keep the chosen level when this topic has it, else the stored one, the suggestion, the first. */
function levelFor(l: VocabLevels, current: Level | null): Level | null {
  const has = (x: Level | null) => !!x && l.levels.some((v) => v.level === x);
  if (has(current)) return current;
  const stored = storedLevel(l);
  if (stored) return stored;
  if (has(l.suggested)) return l.suggested;
  return l.levels[0]?.level ?? null;
}

/** The level this browser chose before, if it is still one the list has. */
function storedLevel(levels: VocabLevels): Level | null {
  try {
    const saved = window.localStorage.getItem(LEVEL_KEY);
    return levels.levels.some((l) => l.level === saved)
      ? (saved as Level)
      : null;
  } catch {
    return null; // private mode: the suggestion is used
  }
}

/** Today's vocabulary: due words first, new words taught before they are asked (specs/web-english, 5). */
export function VocabSession() {
  const { learner, error: learnerError, retry } = useLearner();
  const [session, setSession] = useState<Session | null>(null);
  const [index, setIndex] = useState(0);
  const [taught, setTaught] = useState(false);
  const [answer, setAnswer] = useState<VocabAnswer | null>(null);
  const [typed, setTyped] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [version, setVersion] = useState(0);
  const [levels, setLevels] = useState<VocabLevels | null>(null);
  const [chosen, setChosen] = useState<Level | null>(null);
  // Read once in the browser (null on the server); the pickers only render after a client fetch.
  const [topic, setTopic] = useState<string | null>(() =>
    typeof window === "undefined" ? null : storedTopic(),
  );

  useEffect(() => {
    if (!learner || topic === null) return;
    let live = true;
    englishClient()
      .vocabLevels(learner, topic || undefined)
      .then((l) => {
        if (!live) return;
        if (topic && !l.topics.some((x) => x.slug === topic)) {
          setTopic(""); // a topic that no longer exists: every topic
          return;
        }
        setLevels(l);
        setChosen((c) => levelFor(l, c));
      })
      .catch((e: unknown) => live && setError(e));
    return () => {
      live = false;
    };
  }, [learner, topic, version]);

  useEffect(() => {
    if (!learner || !chosen || topic === null) return;
    let live = true;
    englishClient()
      .vocabSession(learner, chosen, topic || undefined)
      .then((s) => {
        if (!live) return;
        setSession(s);
        setIndex(0);
        setTaught(false);
        setAnswer(null);
        setError(null);
      })
      .catch((e: unknown) => live && setError(e));
    return () => {
      live = false;
    };
  }, [learner, chosen, topic, version]);

  function chooseTopic(next: string) {
    try {
      window.localStorage.setItem(TOPIC_KEY, next);
    } catch {
      // remembered for this page only
    }
    setTopic(next);
  }

  function choose(level: Level) {
    try {
      window.localStorage.setItem(LEVEL_KEY, level);
    } catch {
      // remembered for this page only
    }
    setChosen(level);
  }

  if (learnerError) return <Problem error={learnerError} onRetry={retry} />;
  if (error && !session)
    return <Problem error={error} onRetry={() => setVersion((n) => n + 1)} />;
  if (!learner || !session) return <p className="en-muted">{t.loading}</p>;

  const entry = session.entries[index];
  const header = (
    <section className="en-card nt-vocab-head">
      <h1>{t.vocab.title}</h1>
      <p className="nt-chips">
        <span>
          {session.due} {t.vocab.due}
        </span>
        <span>
          {newWordsToday(session.new_left_today, session.new_available)}{" "}
          {t.vocab.newLeft}
        </span>
      </p>
      {levels && topic !== null && (
        <VocabTopicPicker
          levels={levels}
          topic={topic}
          onChoose={chooseTopic}
        />
      )}
      {levels && chosen && (
        <VocabLevelPicker levels={levels} chosen={chosen} onChoose={choose} />
      )}
      {session.entries.length > 0 && (
        <ol className="nt-dots" aria-label={t.vocab.progress}>
          {session.entries.map((e, i) => (
            <li
              key={e.item.id}
              className={i < index ? "is-done" : i === index ? "is-now" : ""}
            />
          ))}
        </ol>
      )}
    </section>
  );
  if (!entry)
    return (
      <>
        {header}
        <p className="en-card">
          {session.entries.length
            ? t.vocab.done
            : emptyVocabReason(
                  session.new_left_today,
                  session.new_available,
                ) === "done"
              ? t.vocab.empty
              : t.vocab.noMoreAtLevel.replace("{level}", chosen ?? "")}
        </p>
      </>
    );

  async function submit(value: string) {
    setBusy(true);
    setError(null);
    try {
      setAnswer(
        await englishClient().vocabAnswer(learner!, entry.item.id, value),
      );
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }
  function next() {
    setIndex((i) => i + 1);
    setTaught(false);
    setAnswer(null);
    setTyped("");
  }

  if (entry.is_new && entry.card && !taught)
    return (
      <>
        {header}
        <section className="en-card nt-flash">
          <span className="en-badge next">{t.vocab.newWord}</span>
          <WordCard card={entry.card} />
          <button
            type="button"
            className="en-button"
            autoFocus
            onClick={() => setTaught(true)}
          >
            {t.vocab.gotIt}
          </button>
        </section>
      </>
    );

  if (answer)
    return (
      <>
        {header}
        <section className="en-card">
          <div
            className={`en-feedback has-sena ${answer.correct ? "is-right" : "is-wrong"}`}
            role="status"
          >
            <Sena
              pose={answer.correct ? "idle" : "oops"}
              label={answer.correct ? t.senaSays.right : t.senaSays.wrong}
            />
            <div>
              <strong>{answer.correct ? t.vocab.right : t.vocab.wrong}</strong>
              {!answer.correct && (
                <p>
                  {t.vocab.answerWas}: <b lang="en">{answer.accepted}</b>
                </p>
              )}
            </div>
          </div>
          <WordCard card={answer.card} />
          <p className="en-muted">
            {t.vocab.comesBack}:{" "}
            {new Date(answer.due_at).toLocaleDateString("vi-VN")}
          </p>
          <TraceNote trace={answer.trace} names={{}} />
          <button type="button" className="en-button" autoFocus onClick={next}>
            {t.vocab.next}
          </button>
        </section>
      </>
    );

  const item = entry.item;
  if (item.options) {
    const question: Question = {
      item_id: item.id,
      prompt: item.prompt,
      options: item.options,
      draft: false,
      number: index + 1,
      total: session.entries.length,
    };
    return (
      <>
        {header}
        {error != null && <Problem error={error} />}
        <QuestionCard
          key={item.id}
          question={question}
          instruction={item.instruction_vi}
          busy={busy}
          onAnswer={submit}
        />
      </>
    );
  }
  return (
    <>
      {header}
      {error != null && <Problem error={error} />}
      <form
        className="en-card en-question"
        onSubmit={(e) => {
          e.preventDefault();
          if (typed.trim()) void submit(typed);
        }}
      >
        <p className="en-instruction">{item.instruction_vi}</p>
        <p className="en-prompt" lang="en">
          {item.prompt}
        </p>
        <label className="en-typed">
          <span className="en-muted">
            {t.vocab.hint} “{item.hint}”
          </span>
          <input
            value={typed}
            onChange={(e) => setTyped(e.target.value)}
            placeholder={t.vocab.typeHere}
            autoFocus
            autoComplete="off"
            autoCorrect="off"
            autoCapitalize="none"
            spellCheck={false}
            lang="en"
            maxLength={100}
            aria-label={t.vocab.typeHere}
          />
        </label>
        <button
          type="submit"
          className="en-button"
          disabled={busy || !typed.trim()}
        >
          {t.submit}
        </button>
      </form>
    </>
  );
}
