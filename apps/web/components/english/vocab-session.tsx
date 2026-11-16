"use client";
import { useEffect, useState } from "react";
import { englishClient } from "@/lib/english/client";
import {
  afterAttempt,
  recallQueue,
  splitSession,
  type RecallTask,
} from "@/lib/english/flashcards";
import type {
  Level,
  Question,
  VocabAnswer,
  VocabCheck,
  VocabItem,
  VocabLevels,
  VocabSession as Session,
  WordCard as WordCardData,
} from "@/lib/english/types";
import { emptyVocabReason, newWordsToday } from "@/lib/english/view";
import { vi } from "@/messages/vi";
import { Sena } from "@/components/sena/sena";
import { Problem } from "./problem";
import { QuestionCard } from "./question-card";
import { TraceNote } from "./trace-note";
import { useLearner } from "./use-learner";
import { VocabLevelPicker, VocabTopicPicker } from "./vocab-levels";
import { SpeakButton } from "./speak-button";
import { WordCard } from "./word-card";
import { originLabels } from "@/lib/english/word-origin";

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

/**
 * Today's vocabulary: due words first; then the new words as flashcards, then each one typed
 * from memory (specs/vocabulary, flashcards). Only the first try at a word is scheduled.
 */
export function VocabSession() {
  const { learner, error: learnerError, retry } = useLearner();
  const [session, setSession] = useState<Session | null>(null);
  const [index, setIndex] = useState(0);
  const [card, setCard] = useState(0);
  const [flipped, setFlipped] = useState(false);
  const [queue, setQueue] = useState<RecallTask[] | null>(null);
  const [recalled, setRecalled] = useState<VocabAnswer | VocabCheck | null>(
    null,
  );
  const [firstRight, setFirstRight] = useState(0);
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
        setCard(0);
        setFlipped(false);
        setQueue(null);
        setRecalled(null);
        setFirstRight(0);
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

  const { reviews, fresh } = splitSession(session.entries);
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
    </section>
  );

  const entry = reviews[index]; // reviews first, one question each, as before

  async function submit(value: string) {
    setBusy(true);
    setError(null);
    try {
      setAnswer(
        await englishClient().vocabAnswer(learner!, entry!.item.id, value),
      );
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }
  function next() {
    setIndex((i) => i + 1);
    setAnswer(null);
    setTyped("");
  }

  // --- reviews (due words) -----------------------------------------------------------
  if (entry) {
    if (answer)
      return (
        <>
          {header}
          <Verdict
            correct={answer.correct}
            accepted={answer.accepted}
            card={answer.card}
            dueAt={answer.due_at}
            onNext={next}
          >
            <TraceNote trace={answer.trace} names={{}} />
          </Verdict>
        </>
      );
    return (
      <>
        {header}
        {error != null && <Problem error={error} />}
        <Ask
          key={entry.item.id}
          item={entry.item}
          number={index + 1}
          total={reviews.length}
          busy={busy}
          typed={typed}
          setTyped={setTyped}
          onAnswer={submit}
        />
      </>
    );
  }

  // --- nothing at all ------------------------------------------------------------------
  if (fresh.length === 0)
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

  // --- new words, step 1: flashcards ---------------------------------------------------
  if (queue === null) {
    const current = fresh[card]!;
    const last = card === fresh.length - 1;
    return (
      <>
        {header}
        <section className="en-card nt-flash" data-testid="flashcard">
          <p className="en-muted">
            {t.vocab.cardsTitle
              .replace("{i}", String(card + 1))
              .replace("{n}", String(fresh.length))}
          </p>
          {card === 0 && !flipped && (
            <p className="en-muted">{t.vocab.cardsIntro}</p>
          )}
          {flipped ? (
            <WordCard card={current.card!} />
          ) : (
            <div className="nt-card-front">
              <strong lang="en">{current.card!.lemma}</strong>
              {current.card!.ipa && (
                <span
                  className="nt-ipa"
                  lang="en-fonipa"
                  title={originLabels(current.card!).ipaTitle}
                >
                  {current.card!.ipa}
                </span>
              )}
              <SpeakButton text={current.card!.lemma} />
              <span className="nt-card-vi">
                {current.card!.vi ?? t.vocab.noVi}
              </span>
              <span className="nt-chips">
                <span>{current.card!.pos}</span>
                <span>{originLabels(current.card!).level}</span>
              </span>
              <p className="nt-card-example" lang="en">
                “{current.card!.example}”{" "}
                <SpeakButton text={current.card!.example} />
              </p>
            </div>
          )}
          <div className="nt-actions">
            <button
              type="button"
              className="en-button ghost"
              aria-pressed={flipped}
              onClick={() => setFlipped((f) => !f)}
            >
              {flipped ? t.vocab.flipBack : t.vocab.flip}
            </button>
            <button
              type="button"
              className="en-button"
              autoFocus
              onClick={() => {
                setFlipped(false);
                if (last) {
                  setQueue(recallQueue(fresh));
                  setTyped("");
                } else setCard((c) => c + 1);
              }}
            >
              {last ? t.vocab.startRecall : t.vocab.nextCard}
            </button>
          </div>
        </section>
      </>
    );
  }

  // --- new words, step 2: write each word from memory ----------------------------------
  const task = queue[0];
  if (!task)
    return (
      <>
        {header}
        <section className="en-card" role="status">
          <div className="en-feedback has-sena is-right">
            <Sena pose="heart" label={t.senaSays.right} />
            <p>
              {t.vocab.batchDone
                .replace(/\{n\}/g, String(fresh.length))
                .replace("{k}", String(firstRight))}
            </p>
          </div>
        </section>
      </>
    );

  async function attempt(value: string) {
    setBusy(true);
    setError(null);
    try {
      const client = englishClient();
      const result = task!.first
        ? await client.vocabAnswer(learner!, task!.entry.item.id, value)
        : await client.vocabCheck(task!.entry.item.id, value);
      if (task!.first && result.correct) setFirstRight((k) => k + 1);
      setRecalled(result);
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }

  if (recalled)
    return (
      <>
        {header}
        <Verdict
          correct={recalled.correct}
          accepted={recalled.accepted}
          card={recalled.card}
          dueAt={"due_at" in recalled ? recalled.due_at : null}
          onNext={() => {
            setQueue(afterAttempt(queue, recalled.correct));
            setRecalled(null);
            setTyped("");
          }}
        />
      </>
    );

  return (
    <>
      {header}
      {error != null && <Problem error={error} />}
      <p className="en-muted nt-recall-head">
        <b>{t.vocab.recallTitle}</b> ·{" "}
        {t.vocab.recallLeft.replace("{n}", String(queue.length))}
        {!task.first && <span className="nt-retry"> {t.vocab.retryNote}</span>}
      </p>
      <Ask
        key={`${task.entry.item.id}-${task.first}-${queue.length}`}
        item={task.entry.item}
        number={fresh.length - queue.length + 1}
        total={fresh.length}
        busy={busy}
        typed={typed}
        setTyped={setTyped}
        onAnswer={attempt}
      />
    </>
  );
}

/** The verdict after an answer: right or wrong, the key, the word, and when it comes back. */
function Verdict({
  correct,
  accepted,
  card,
  dueAt,
  onNext,
  children,
}: {
  correct: boolean;
  accepted: string;
  card: WordCardData;
  dueAt: string | null;
  onNext: () => void;
  children?: React.ReactNode;
}) {
  return (
    <section className="en-card">
      <div
        className={`en-feedback has-sena ${correct ? "is-right" : "is-wrong"}`}
        role="status"
      >
        <Sena
          pose={correct ? "idle" : "oops"}
          label={correct ? t.senaSays.right : t.senaSays.wrong}
        />
        <div>
          <strong>{correct ? t.vocab.right : t.vocab.wrong}</strong>
          {!correct && (
            <p>
              {t.vocab.answerWas}: <b lang="en">{accepted}</b>
            </p>
          )}
        </div>
      </div>
      <WordCard card={card} />
      {dueAt && (
        <p className="en-muted">
          {t.vocab.comesBack}: {new Date(dueAt).toLocaleDateString("vi-VN")}
        </p>
      )}
      {children}
      <button type="button" className="en-button" autoFocus onClick={onNext}>
        {t.vocab.next}
      </button>
    </section>
  );
}

/** One question: multiple choice when it has options, typed otherwise (with the first letter). */
function Ask({
  item,
  number,
  total,
  busy,
  typed,
  setTyped,
  onAnswer,
}: {
  item: VocabItem;
  number: number;
  total: number;
  busy: boolean;
  typed: string;
  setTyped: (v: string) => void;
  onAnswer: (value: string) => void;
}) {
  if (item.options) {
    const question: Question = {
      item_id: item.id,
      prompt: item.prompt,
      options: item.options,
      draft: false,
      number,
      total,
    };
    return (
      <QuestionCard
        question={question}
        instruction={item.instruction_vi}
        busy={busy}
        onAnswer={onAnswer}
      />
    );
  }
  return (
    <form
      className="en-card en-question"
      onSubmit={(e) => {
        e.preventDefault();
        if (typed.trim()) onAnswer(typed);
      }}
    >
      <p className="en-instruction">{item.instruction_vi}</p>
      <p className="en-prompt" lang={item.kind === "recall" ? undefined : "en"}>
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
        {vi.english.submit}
      </button>
    </form>
  );
}
