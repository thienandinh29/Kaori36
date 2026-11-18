"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { DataError } from "@/lib/decode";
import { keyText } from "@/lib/reading/review";
import {
  LEVELS,
  REASONS_BY_TYPE,
  TOKEN_KEY,
  pickToken,
  reviewClient,
  type Batch,
  type Level,
  type Me,
  type Next,
  type PortalLabel,
  type Reason,
  type ReadingView,
  type SpeechView,
  type Verdict,
  type View,
} from "@/lib/review/portal";
import { vi } from "@/messages/vi";
import { Problem } from "@/components/english/problem";
import { Question } from "@/components/reading/review-page";

const t = vi.english.reviewPortal;

function readStored(): string | null {
  try {
    return sessionStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}
function store(token: string) {
  try {
    sessionStorage.setItem(TOKEN_KEY, token);
  } catch {
    // The page still works for this visit without storage.
  }
}

/** Step 1 input: choices for TFNG and multiple choice, free text otherwise. */
function AnswerInput({
  item,
  value,
  onChange,
}: {
  item: ReadingView;
  value: string;
  onChange: (v: string) => void;
}) {
  const options = Array.isArray(item.question.options)
    ? (item.question.options as string[]).map((_, i) => "ABCD"[i] ?? String(i))
    : null;
  const choices =
    item.kind === "tfng" ? ["TRUE", "FALSE", "NOT GIVEN"] : options;
  if (choices)
    return (
      <div className="nt-actions" role="radiogroup" aria-label={t.yourAnswer}>
        {choices.map((c) => (
          <button
            key={c}
            type="button"
            role="radio"
            aria-checked={value === c}
            className={`en-button small ${value === c ? "" : "ghost"}`}
            onClick={() => onChange(c)}
          >
            {c}
          </button>
        ))}
      </div>
    );
  return (
    <label>
      {t.yourAnswer}{" "}
      <input
        type="text"
        lang="en"
        maxLength={300}
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    </label>
  );
}

/**
 * A kept recording, fetched with the token header and played from memory; "this part" plays the
 * target sound with a little margin around it.
 */
function SpeechPlayer({
  token,
  batch,
  item,
}: {
  token: string;
  batch: string;
  item: SpeechView;
}) {
  const audio = useRef<HTMLAudioElement>(null);
  const [src, setSrc] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    let url: string | null = null;
    let live = true;
    reviewClient(token)
      .audio(batch, item.contentId)
      .then((blob) => {
        if (!live) return;
        url = URL.createObjectURL(blob);
        setSrc(url);
      })
      .catch(() => live && setFailed(true));
    return () => {
      live = false;
      if (url) URL.revokeObjectURL(url);
    };
  }, [token, batch, item.contentId]);
  function playPart() {
    const el = audio.current;
    if (!el) return;
    const start = Math.max(0, item.startMs - 250) / 1000;
    const end = (item.endMs + 250) / 1000;
    el.currentTime = start;
    const stop = () => {
      if (el.currentTime >= end) {
        el.pause();
        el.removeEventListener("timeupdate", stop);
      }
    };
    el.addEventListener("timeupdate", stop);
    void el.play();
  }
  if (failed) return <p className="en-feedback is-wrong">{t.audioFailed}</p>;
  if (!src) return <p className="en-muted">{vi.english.loading}</p>;
  return (
    <div>
      <audio ref={audio} src={src} controls preload="auto" />
      <div className="nt-actions">
        <button type="button" className="en-button small" onClick={playPart}>
          {t.playPart}
        </button>
      </div>
    </div>
  );
}

/** The private reviewer portal (specs/validation/step-v2.md, step-v2b.md). */
export function ReviewPortalPage() {
  // Rendered on the client only (portal-client.tsx), so the address bar can be read at once.
  const [{ token, clear }] = useState(() =>
    pickToken(window.location.hash, readStored()),
  );
  const [me, setMe] = useState<Me | null>(null);
  const [batch, setBatch] = useState<Batch | null>(null);
  const [next, setNext] = useState<Next | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [invalid, setInvalid] = useState(false);
  const [answer, setAnswer] = useState("");
  const [revealed, setRevealed] = useState(false);
  const [verdict, setVerdict] = useState<Verdict | null>(null);
  const [reason, setReason] = useState<Reason>("");
  const [level, setLevel] = useState<Level | "unsure" | null>(null);
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (clear)
      window.history.replaceState(
        null,
        "",
        window.location.pathname + window.location.search,
      );
    if (token) store(token);
  }, [token, clear]);

  const fail = useCallback((e: unknown) => {
    if (e instanceof DataError && e.status === 401) setInvalid(true);
    else setError(e);
  }, []);

  const loadMe = useCallback(() => {
    if (!token) return;
    reviewClient(token).me().then(setMe).catch(fail);
  }, [token, fail]);
  useEffect(loadMe, [loadMe]);

  const loadNext = useCallback(
    (b: Batch) => {
      if (!token) return;
      setAnswer("");
      setRevealed(false);
      setVerdict(null);
      setLevel(null);
      setReason("");
      setNote("");
      reviewClient(token).next(b.id).then(setNext).catch(fail);
    },
    [token, fail],
  );

  if (token === null || invalid)
    return (
      <section className="en-card" data-testid="review-portal">
        <h1>{t.title}</h1>
        <p className="en-feedback is-wrong">{t.invalid}</p>
      </section>
    );
  if (error) return <Problem error={error} />;
  if (!me) return <p className="en-muted">{vi.english.loading}</p>;

  async function save(body: PortalLabel) {
    if (!batch || !next?.item || !token) return;
    setBusy(true);
    setSaved(false);
    try {
      await reviewClient(token).label(batch.id, next.item.contentId, body);
      setSaved(true);
      loadNext(batch);
    } catch (e) {
      fail(e);
    } finally {
      setBusy(false);
    }
  }
  const trimmed = note.trim() ? { note: note.trim() } : {};

  if (!batch)
    return (
      <section className="en-card" data-testid="review-portal">
        <h1>{t.title}</h1>
        <p>
          {t.hello} {me.name}.
        </p>
        <p className="en-muted">{t.intro}</p>
        <h2>{t.batches}</h2>
        {me.batches.length === 0 ? (
          <p className="en-muted">{t.noBatches}</p>
        ) : (
          <ul>
            {me.batches.map((b) => (
              <li key={b.id}>
                {b.name}: {b.done}/{b.total} {t.progress}{" "}
                <button
                  type="button"
                  className="en-button small"
                  onClick={() => {
                    setBatch(b);
                    setSaved(false);
                    loadNext(b);
                  }}
                >
                  {t.open}
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>
    );

  const item: View | null = next?.item ?? null;
  const reasons = item ? (REASONS_BY_TYPE[item.contentType] ?? []) : [];
  const blind =
    item?.contentType === "reading_item" ||
    item?.contentType === "grammar_item";
  const noteInput = (
    <label className="nt-review-note">
      {t.note}
      <input
        type="text"
        maxLength={500}
        value={note}
        onChange={(e) => setNote(e.target.value)}
      />
    </label>
  );
  // The verdict, with a reason when "wrong" (none for a sound), then save.
  const judge = (
    <>
      <div className="nt-actions" role="radiogroup" aria-label={t.verdictLabel}>
        {(["right", "wrong", "unsure"] as const).map((v) => (
          <button
            key={v}
            type="button"
            role="radio"
            aria-checked={verdict === v}
            className={`en-button small ${verdict === v ? "" : "ghost"}`}
            onClick={() => {
              setVerdict(v);
              if (v === "wrong" && reasons.length && !reason)
                setReason(reasons[0]);
            }}
          >
            {t.verdicts[v]}
          </button>
        ))}
      </div>
      {verdict === "wrong" && reasons.length > 0 && (
        <label>
          {t.reasonPrompt}{" "}
          <select value={reason} onChange={(e) => setReason(e.target.value)}>
            {reasons.map((r) => (
              <option key={r} value={r}>
                {t.reasons[r]}
              </option>
            ))}
          </select>
        </label>
      )}
      {noteInput}
      <button
        type="button"
        className="en-button"
        disabled={busy || verdict === null}
        onClick={() =>
          verdict &&
          void save({
            ...(blind ? { answer: answer.trim() } : {}),
            verdict,
            ...(verdict === "wrong" && reasons.length > 0 ? { reason } : {}),
            ...trimmed,
          })
        }
      >
        {t.save}
      </button>
    </>
  );
  // Step 1 then step 2, for questions with a key: the reviewer answers before seeing it.
  const blindSteps = (keyLabel: string | null, choices: React.ReactNode) => (
    <>
      <p className="en-muted">{t.step1}</p>
      {choices}
      {!revealed ? (
        <button
          type="button"
          className="en-button"
          disabled={answer.trim() === ""}
          onClick={() => setRevealed(true)}
        >
          {t.reveal}
        </button>
      ) : (
        <>
          <p>
            <strong>{t.key}:</strong>{" "}
            <span lang="en" data-testid="review-key">
              {keyLabel ?? t.noKey}
            </span>
          </p>
          <p className="en-muted">{t.step2}</p>
          {judge}
        </>
      )}
    </>
  );

  let content: React.ReactNode = null;
  if (item?.contentType === "text_level")
    content = (
      <article data-testid="review-text">
        <p lang="en" className="nt-review-passage">
          {item.text}
        </p>
        <p>{t.levelPrompt}</p>
        <div
          className="nt-actions"
          role="radiogroup"
          aria-label={t.levelPrompt}
        >
          {([...LEVELS, "unsure"] as const).map((l) => (
            <button
              key={l}
              type="button"
              role="radio"
              aria-checked={level === l}
              className={`en-button small ${level === l ? "" : "ghost"}`}
              onClick={() => setLevel(l)}
            >
              {l === "unsure" ? t.unsure : l}
            </button>
          ))}
        </div>
        {noteInput}
        <button
          type="button"
          className="en-button"
          disabled={busy || level === null}
          onClick={() => level && void save({ level, ...trimmed })}
        >
          {t.save}
        </button>
      </article>
    );
  else if (item?.contentType === "reading_item")
    content = (
      <article data-testid="review-item">
        <h2>{t.passage}</h2>
        <p lang="en" className="nt-review-passage">
          {item.passage}
        </p>
        <h2>{t.question}</h2>
        <Question item={item} />
        {blindSteps(
          keyText(item),
          <AnswerInput item={item} value={answer} onChange={setAnswer} />,
        )}
      </article>
    );
  else if (item?.contentType === "grammar_item") {
    const letters = item.options.map((_, i) => "ABCDEF"[i] ?? String(i));
    content = (
      <article data-testid="review-grammar">
        <h2>{t.question}</h2>
        <p lang="en">{item.prompt}</p>
        <ol type="A" lang="en">
          {item.options.map((o, i) => (
            <li key={i}>{o}</li>
          ))}
        </ol>
        {blindSteps(
          item.key === null
            ? null
            : `${letters[item.key]}. ${item.options[item.key]}`,
          <div
            className="nt-actions"
            role="radiogroup"
            aria-label={t.yourAnswer}
          >
            {letters.map((c) => (
              <button
                key={c}
                type="button"
                role="radio"
                aria-checked={answer === c}
                className={`en-button small ${answer === c ? "" : "ghost"}`}
                onClick={() => setAnswer(c)}
              >
                {c}
              </button>
            ))}
          </div>,
        )}
      </article>
    );
  } else if (item?.contentType === "vocab_entry")
    content = (
      <article data-testid="review-vocab">
        <h2 lang="en">
          {item.lemma}{" "}
          <small className="en-muted">
            {item.pos} · {item.level}
            {item.ipa ? ` · ${item.ipa}` : ""}
          </small>
        </h2>
        <dl>
          <dt>{t.vocab.definition}</dt>
          <dd lang="en">{item.definition}</dd>
          {item.vi && (
            <>
              <dt>{t.vocab.gloss}</dt>
              <dd>{item.vi}</dd>
            </>
          )}
          {[
            [t.vocab.examples, item.examples],
            [t.vocab.collocations, item.collocations],
            [t.vocab.forms, item.forms],
          ].map(([label, lines]) =>
            (lines as string[]).length ? (
              <div key={label as string}>
                <dt>{label as string}</dt>
                {(lines as string[]).map((line, i) => (
                  <dd key={i} lang="en">
                    {line}
                  </dd>
                ))}
              </div>
            ) : null,
          )}
        </dl>
        <p className="en-muted">{t.vocab.prompt}</p>
        {judge}
      </article>
    );
  else if (item?.contentType === "speech_target" && token)
    content = (
      <article data-testid="review-speech">
        {item.sentence && (
          <p lang="en" className="nt-review-passage">
            {item.sentence}
          </p>
        )}
        <p>
          {t.speech.target}: <strong lang="en">{item.word}</strong>
          {item.ipa ? ` · /${item.ipa}/` : ""}
          {item.soundVi ? ` (${item.soundVi})` : ""}
        </p>
        <SpeechPlayer
          key={item.contentId}
          token={token}
          batch={batch.id}
          item={item}
        />
        <p className="en-muted">{t.speech.prompt}</p>
        {judge}
      </article>
    );

  return (
    <section className="en-card nt-review" data-testid="review-portal">
      <h1>{batch.name}</h1>
      <button
        type="button"
        className="en-button ghost small"
        onClick={() => {
          setBatch(null);
          setNext(null);
          loadMe();
        }}
      >
        {t.back}
      </button>
      {next && (
        <p className="en-muted">
          {next.done}/{next.total} {t.progress}
          {next.unavailable > 0 && ` · ${next.unavailable} ${t.unavailable}`}
        </p>
      )}
      {saved && (
        <p className="en-feedback is-right" role="status">
          {t.saved}
        </p>
      )}
      {!next ? (
        <p className="en-muted">{vi.english.loading}</p>
      ) : !item ? (
        next.done + next.unavailable < next.total || next.done === 0 ? (
          <p className="en-muted">{t.nothingNow}</p>
        ) : (
          <p className="en-feedback is-right">{t.finished}</p>
        )
      ) : (
        content
      )}
    </section>
  );
}
