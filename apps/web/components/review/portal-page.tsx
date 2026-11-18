"use client";
import { useCallback, useEffect, useState } from "react";
import { DataError } from "@/lib/decode";
import { keyText } from "@/lib/reading/review";
import {
  LEVELS,
  REASONS,
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
  type Verdict,
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

/** The private reviewer portal (specs/validation/step-v2.md). */
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
  const [reason, setReason] = useState<Reason>("wrong_key");
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

  const item = next?.item ?? null;
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
      ) : item.contentType === "text_level" ? (
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
          <label className="nt-review-note">
            {t.note}
            <input
              type="text"
              maxLength={500}
              value={note}
              onChange={(e) => setNote(e.target.value)}
            />
          </label>
          <button
            type="button"
            className="en-button"
            disabled={busy || level === null}
            onClick={() => level && void save({ level, ...trimmed })}
          >
            {t.save}
          </button>
        </article>
      ) : (
        <article data-testid="review-item">
          <h2>{t.passage}</h2>
          <p lang="en" className="nt-review-passage">
            {item.passage}
          </p>
          <h2>{t.question}</h2>
          <Question item={item} />
          <p className="en-muted">{t.step1}</p>
          <AnswerInput item={item} value={answer} onChange={setAnswer} />
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
                  {keyText(item)}
                </span>
              </p>
              <p className="en-muted">{t.step2}</p>
              <div
                className="nt-actions"
                role="radiogroup"
                aria-label={t.step2}
              >
                {(["right", "wrong", "unsure"] as const).map((v) => (
                  <button
                    key={v}
                    type="button"
                    role="radio"
                    aria-checked={verdict === v}
                    className={`en-button small ${verdict === v ? "" : "ghost"}`}
                    onClick={() => setVerdict(v)}
                  >
                    {t.verdicts[v]}
                  </button>
                ))}
              </div>
              {verdict === "wrong" && (
                <label>
                  {t.reasonPrompt}{" "}
                  <select
                    value={reason}
                    onChange={(e) => setReason(e.target.value as Reason)}
                  >
                    {REASONS.map((r) => (
                      <option key={r} value={r}>
                        {t.reasons[r]}
                      </option>
                    ))}
                  </select>
                </label>
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
              <button
                type="button"
                className="en-button"
                disabled={busy || verdict === null}
                onClick={() =>
                  verdict &&
                  void save({
                    answer: answer.trim(),
                    verdict,
                    ...(verdict === "wrong" ? { reason } : {}),
                    ...trimmed,
                  })
                }
              >
                {t.save}
              </button>
            </>
          )}
        </article>
      )}
    </section>
  );
}
