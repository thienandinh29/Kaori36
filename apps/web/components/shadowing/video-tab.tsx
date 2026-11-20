"use client";
import { useEffect, useRef, useState } from "react";
import { clock, loopSpan, videoId } from "@/lib/shadowing/youtube";
import { vi } from "@/messages/vi";
import { Recorder, type Take } from "./recorder";

const t = vi.english.shadowing;
const SPEEDS = [1, 0.75, 0.5] as const;

/** The parts of YouTube's IFrame Player API this page uses. */
interface YtPlayer {
  getCurrentTime(): number;
  seekTo(seconds: number, allowSeekAhead: boolean): void;
  playVideo(): void;
  setPlaybackRate(rate: number): void;
  destroy(): void;
}
interface YtNamespace {
  Player: new (
    el: HTMLElement,
    options: {
      host: string;
      videoId: string;
      width: string;
      height: string;
      playerVars: Record<string, number>;
      events: { onReady: () => void; onError: () => void };
    },
  ) => YtPlayer;
}
declare global {
  interface Window {
    YT?: YtNamespace;
    onYouTubeIframeAPIReady?: () => void;
  }
}

let loading: Promise<YtNamespace> | null = null;
/** YouTube's official player script, loaded once (the only way to play a video within its terms). */
function youtube(): Promise<YtNamespace> {
  if (window.YT?.Player) return Promise.resolve(window.YT);
  loading ??= new Promise((resolve, reject) => {
    window.onYouTubeIframeAPIReady = () =>
      window.YT ? resolve(window.YT) : reject(new Error("youtube"));
    const s = document.createElement("script");
    s.src = "https://www.youtube.com/iframe_api";
    s.onerror = () => {
      loading = null;
      reject(new Error("youtube"));
    };
    document.head.appendChild(s);
  });
  return loading;
}

/** Shadow any YouTube video: pick a span, loop it, slow it, record yourself (step 4.4d). */
export function VideoTab() {
  const [link, setLink] = useState("");
  const [id, setId] = useState<string | null>(null);
  const [bad, setBad] = useState(false);
  const [failed, setFailed] = useState(false);
  const [a, setA] = useState<number | null>(null);
  const [b, setB] = useState<number | null>(null);
  const [looping, setLooping] = useState(false);
  const [speed, setSpeed] = useState<number>(1);
  const [take, setTake] = useState<Take | null>(null);
  // The player's controls work only after YouTube says it is ready; before, a tap set nothing.
  const [ready, setReady] = useState(false);
  const box = useRef<HTMLDivElement | null>(null);
  const player = useRef<YtPlayer | null>(null);

  useEffect(() => {
    if (!id || !box.current) return;
    let live = true;
    const el = document.createElement("div");
    box.current.replaceChildren(el);
    youtube()
      .then((YT) => {
        if (!live) return;
        player.current = new YT.Player(el, {
          host: "https://www.youtube-nocookie.com",
          videoId: id,
          width: "100%",
          height: "100%",
          playerVars: { playsinline: 1, rel: 0 },
          events: {
            onReady: () => live && setReady(true),
            onError: () => setFailed(true),
          },
        });
      })
      .catch(() => live && setFailed(true));
    return () => {
      live = false;
      player.current?.destroy();
      player.current = null;
    };
  }, [id]);

  const span = loopSpan(a, b);
  useEffect(() => {
    if (!looping || !span) return;
    const timer = window.setInterval(() => {
      const p = player.current;
      if (p && p.getCurrentTime() >= span.to) p.seekTo(span.from, true);
    }, 200);
    return () => window.clearInterval(timer);
  }, [looping, span]);

  function open() {
    const v = videoId(link);
    setBad(v === null);
    setFailed(false);
    setA(null);
    setB(null);
    setLooping(false);
    setSpeed(1);
    setTake(null);
    setReady(false);
    setId(v);
  }
  const now = () => player.current?.getCurrentTime() ?? null;

  return (
    <div data-testid="shadowing-video">
      <p className="en-muted">{t.videoIntro}</p>
      <form
        className="nt-listen-form"
        onSubmit={(e) => {
          e.preventDefault();
          open();
        }}
      >
        <label>
          {t.link}
          <input
            type="url"
            inputMode="url"
            value={link}
            maxLength={300}
            placeholder="https://youtu.be/…"
            onChange={(e) => setLink(e.target.value)}
          />
        </label>
        <button
          type="submit"
          className="en-button small"
          disabled={!link.trim()}
        >
          {t.open}
        </button>
      </form>
      {bad && <p className="en-feedback is-wrong">{t.badLink}</p>}
      {failed && <p className="en-feedback is-wrong">{t.playerFailed}</p>}
      {id && (
        <>
          <div className="nt-video" ref={box} data-testid="shadowing-player" />
          <div className="nt-actions">
            <button
              type="button"
              className="en-button small ghost"
              disabled={!ready}
              onClick={() => setA(now())}
            >
              {t.setA}
            </button>
            <button
              type="button"
              className="en-button small ghost"
              disabled={!ready}
              onClick={() => setB(now())}
            >
              {t.setB}
            </button>
            <button
              type="button"
              className="en-button small"
              disabled={!ready || !span}
              onClick={() => {
                if (!looping && span) {
                  player.current?.seekTo(span.from, true);
                  player.current?.playVideo();
                }
                setLooping((x) => !x);
              }}
            >
              {looping ? t.stopLoop : t.loop}
            </button>
          </div>
          <p className="en-muted" role="status">
            {span ? t.span(clock(span.from), clock(span.to)) : t.noSpan}
          </p>
          <div className="nt-actions" role="group" aria-label={t.speed}>
            <span>{t.speed}</span>
            {SPEEDS.map((s) => (
              <button
                key={s}
                type="button"
                aria-pressed={speed === s}
                disabled={!ready}
                className={`en-button small ${speed === s ? "" : "ghost"}`}
                onClick={() => {
                  setSpeed(s);
                  player.current?.setPlaybackRate(s);
                }}
              >
                {s}×
              </button>
            ))}
          </div>
          <Recorder onTake={setTake} />
          {take && (
            <div role="status" data-testid="shadowing-take">
              <p>
                {t.yours}: <audio controls src={take.url} />
              </p>
              <p className="en-muted">
                {t.yours}: {t.timing(take.timing.seconds, take.timing.pauses)}
              </p>
              <p className="en-muted">{t.measuresNote}</p>
            </div>
          )}
        </>
      )}
    </div>
  );
}
