"use client";
import { useEffect, useRef, useState } from "react";
import { englishClient } from "@/lib/english/client";
import { paceRatio, type Timing } from "@/lib/shadowing/measure";
import type { ShadowText, ShadowTexts } from "@/lib/shadowing/texts";
import { vi } from "@/messages/vi";
import { Problem } from "@/components/english/problem";
import { measure, Recorder, type Take } from "./recorder";

const t = vi.english.shadowing;

/** Shadow the bank's sentences with the server voice (step 4.4d). */
export function BankTab({ learner }: { learner: string }) {
  const [texts, setTexts] = useState<ShadowTexts | null>(null);
  const [slug, setSlug] = useState<string | null>(null);
  const [text, setText] = useState<ShadowText | null>(null);
  const [index, setIndex] = useState(0);
  const [model, setModel] = useState<Timing | null>(null);
  const [take, setTake] = useState<Take | null>(null);
  const [error, setError] = useState<unknown>(null);
  const audio = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    let live = true;
    englishClient()
      .shadowTexts(learner)
      .then((x) => {
        if (!live) return;
        setTexts(x);
        setSlug(x.texts[0]?.slug ?? null);
      })
      .catch((e: unknown) => live && setError(e));
    return () => {
      live = false;
    };
  }, [learner]);

  useEffect(() => {
    if (!slug) return;
    let live = true;
    englishClient()
      .shadowText(learner, slug)
      .then((x) => {
        if (!live) return;
        setText(x);
        setIndex(0);
        setTake(null);
        setModel(null);
      })
      .catch((e: unknown) => live && setError(e));
    return () => {
      live = false;
    };
  }, [learner, slug]);

  if (error) return <Problem error={error} />;
  if (!texts) return <p className="en-muted">{vi.english.loading}</p>;
  if (!texts.available)
    return <p className="en-feedback is-wrong">{t.noVoice}</p>;
  const sentence = text?.sentences[index];

  function play(pace: "normal" | "slow") {
    if (!sentence) return;
    audio.current?.pause();
    const src = englishClient().listeningAudioUrl(sentence.id, pace);
    const el = new Audio(src);
    audio.current = el;
    void el.play().catch(() => undefined);
    // The model's timing, once per sentence and at normal pace (what the learner matches).
    if (pace === "normal" && !model)
      void fetch(src)
        .then((r) => r.blob())
        .then(measure)
        .then(setModel)
        .catch(() => undefined);
  }
  function go(step: number) {
    audio.current?.pause();
    setTake(null);
    setModel(null);
    setIndex((i) => i + step);
  }
  const ratio = take && model ? paceRatio(take.timing, model) : null;

  return (
    <div data-testid="shadowing-bank">
      <p className="en-muted">{t.voiceNote}</p>
      <label className="nt-pick">
        {t.pickText}{" "}
        <select value={slug ?? ""} onChange={(e) => setSlug(e.target.value)}>
          {texts.texts.map((x) => (
            <option key={x.slug} value={x.slug} lang="en">
              {x.title}
            </option>
          ))}
        </select>
      </label>
      {text && sentence && (
        <article data-testid="shadowing-sentence">
          <h2>{t.sentence(index + 1, text.sentences.length)}</h2>
          <p lang="en" className="nt-shadow-text">
            {sentence.text}
          </p>
          <div className="nt-actions">
            <button
              type="button"
              className="en-button small"
              onClick={() => play("normal")}
            >
              {t.listen}
            </button>
            <button
              type="button"
              className="en-button small ghost"
              onClick={() => play("slow")}
            >
              {t.slow}
            </button>
          </div>
          <Recorder onTake={setTake} />
          {take && (
            <div role="status" data-testid="shadowing-take">
              <p>
                {t.yours}: <audio controls src={take.url} />
              </p>
              <p className="en-muted">
                {t.yours}: {t.timing(take.timing.seconds, take.timing.pauses)}
                {model && (
                  <>
                    {" "}
                    · {t.model}: {t.timing(model.seconds, model.pauses)}
                  </>
                )}
              </p>
              {ratio !== null && <p>{t.pace(ratio)}</p>}
              <p className="en-muted">{t.measuresNote}</p>
            </div>
          )}
          <div className="nt-actions">
            <button
              type="button"
              className="en-button small ghost"
              disabled={index === 0}
              onClick={() => go(-1)}
            >
              {t.prev}
            </button>
            <button
              type="button"
              className="en-button small ghost"
              disabled={index + 1 >= text.sentences.length}
              onClick={() => go(1)}
            >
              {t.next}
            </button>
          </div>
        </article>
      )}
    </div>
  );
}
