"use client";
import { useEffect, useState } from "react";
import { englishClient } from "@/lib/english/client";
import {
  dictionaryQuery,
  type DictionaryResult,
} from "@/lib/english/dictionary";
import { vi } from "@/messages/vi";
import { Problem } from "./problem";
import { WordCard } from "./word-card";

const t = vi.english.dictionary;
const WAIT_MS = 250; // search once typing pauses

/** Dictionary search over NodeTrail's word list (specs/vocabulary/step-dictionary.md). */
export function Dictionary() {
  const [text, setText] = useState("");
  const [found, setFound] = useState<DictionaryResult | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [attempt, setAttempt] = useState(0);
  const query = dictionaryQuery(text);
  useEffect(() => {
    if (!query) return;
    const abort = new AbortController();
    const timer = setTimeout(() => {
      englishClient()
        .dictionary(query, abort.signal)
        .then((r) => {
          setFound(r);
          setError(null);
        })
        .catch((e: unknown) => {
          if (!abort.signal.aborted) setError(e);
        });
    }, WAIT_MS);
    return () => {
      clearTimeout(timer);
      abort.abort();
    };
  }, [query, attempt]);
  const shown = query ? found : null;
  return (
    <>
      <section className="en-card">
        <h1>{t.title}</h1>
        <p className="en-muted">{t.intro}</p>
        <form role="search" onSubmit={(e) => e.preventDefault()}>
          <label className="en-dict-label" htmlFor="dictionary-query">
            {t.label}
          </label>
          <input
            id="dictionary-query"
            className="en-dict-input"
            type="search"
            value={text}
            maxLength={40}
            autoComplete="off"
            spellCheck={false}
            placeholder={t.placeholder}
            onChange={(e) => setText(e.target.value)}
          />
        </form>
        <p className="en-muted">{t.scope}</p>
      </section>
      {query && error != null && (
        <Problem error={error} onRetry={() => setAttempt((n) => n + 1)} />
      )}
      {shown && !error && (
        <section className="en-card" aria-live="polite">
          {shown.draft && (
            <p className="en-muted">
              <span className="en-badge draft">{vi.english.draft}</span>{" "}
              {t.draft}
            </p>
          )}
          <p className="en-muted" data-testid="dictionary-count">
            {shown.total === 0
              ? t.none
              : t.count(shown.results.length, shown.total)}
          </p>
          <div className="en-dict-results">
            {shown.results.map((card) => (
              <WordCard key={card.key} card={card} />
            ))}
          </div>
        </section>
      )}
    </>
  );
}
