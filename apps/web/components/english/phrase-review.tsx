"use client";
import { useEffect, useState } from "react";
import { englishClient } from "@/lib/english/client";
import type { PhraseAnswer, PhraseSession } from "@/lib/english/types";
import { vi } from "@/messages/vi";
import { Problem } from "./problem";
import { SpeakButton } from "./speak-button";
import { useLearner } from "./use-learner";

const w = vi.english.writing;

/** Saved phrases from rewrites, reviewed as gap-fills and scheduled by FSRS (step 2.4b). */
export function PhraseReview() {
  const { learner } = useLearner();
  const [session, setSession] = useState<PhraseSession | null>(null);
  const [index, setIndex] = useState(0);
  const [typed, setTyped] = useState("");
  const [result, setResult] = useState<PhraseAnswer | null>(null);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    if (!learner) return;
    let live = true;
    englishClient()
      .phraseSession(learner)
      .then((s) => live && setSession(s))
      .catch((e: unknown) => live && setError(e));
    return () => {
      live = false;
    };
  }, [learner]);

  if (error) return <Problem error={error} />;
  if (!learner || !session || session.saved === 0) return null;
  const entry = session.entries[index];
  return (
    <section className="en-card" data-testid="phrase-review">
      <h2>{w.phrasesTitle}</h2>
      {!entry ? (
        <p className="en-muted">{w.phrasesDone}</p>
      ) : (
        <>
          {entry.is_new && entry.phrase && (
            <p>
              {w.phraseNew}: <strong lang="en">{entry.phrase}</strong>{" "}
              <SpeakButton text={entry.phrase} private />
            </p>
          )}
          <p lang="en">{entry.prompt}</p>
          <input
            lang="en"
            aria-label={w.phraseAnswer}
            value={typed}
            placeholder={`${entry.hint}…`}
            onChange={(e) => setTyped(e.target.value)}
            disabled={result !== null}
          />
          {result === null ? (
            <button
              type="button"
              className="en-button"
              disabled={!typed.trim()}
              onClick={async () => {
                try {
                  setResult(
                    await englishClient().answerPhrase(
                      learner,
                      entry.phrase_id,
                      typed,
                    ),
                  );
                } catch (e: unknown) {
                  setError(e);
                }
              }}
            >
              {vi.english.submit}
            </button>
          ) : (
            <>
              <p className={result.correct ? "en-praise" : undefined}>
                {result.correct
                  ? w.phraseRight
                  : `${w.phraseWrong} ${result.accepted}`}
              </p>
              <SpeakButton text={result.accepted} private />
              <button
                type="button"
                className="en-button"
                onClick={() => {
                  setIndex((n) => n + 1);
                  setTyped("");
                  setResult(null);
                }}
              >
                {vi.english.writing.phraseNext}
              </button>
            </>
          )}
        </>
      )}
    </section>
  );
}
