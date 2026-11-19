"use client";
import { useEffect, useRef, useState } from "react";
import { englishClient } from "@/lib/english/client";
import {
  closeness,
  type SayResult,
  type SayStatus,
} from "@/lib/english/say-word";
import { toServerWav } from "@/lib/pronunciation/wav";
import { vi } from "@/messages/vi";
import { useLearner } from "./use-learner";

const t = vi.english.sayWord;
const CONSENT_KEY = "nodetrail_say_consent";
const MAX_MS = 5000;

function consented(): boolean {
  try {
    return localStorage.getItem(CONSENT_KEY) === "voice-v1";
  } catch {
    return false;
  }
}

/**
 * Say the word aloud (step 3.7): everyone can record and compare with the model by ear (nothing
 * leaves the browser); the owner, with the pronunciation service on, also sees each sound's raw
 * score. The audio sent for analysis is never stored.
 */
export function SayWord({ lemma, pos }: { lemma: string; pos: string }) {
  const { learner } = useLearner();
  const [status, setStatus] = useState<SayStatus | null>(null);
  // Read once on first render; it only matters after a take exists (never in the server's HTML).
  const [agreed, setAgreed] = useState(consented);
  const [recording, setRecording] = useState(false);
  const [take, setTake] = useState<{ url: string; wav: ArrayBuffer } | null>(
    null,
  );
  const [result, setResult] = useState<SayResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [noMic, setNoMic] = useState(false);
  const recorder = useRef<MediaRecorder | null>(null);
  const timer = useRef<number | null>(null);

  useEffect(() => {
    if (!learner) return;
    let live = true;
    englishClient()
      .sayStatus(learner)
      .then((s) => live && setStatus(s))
      .catch(() => live && setStatus(null));
    return () => {
      live = false;
    };
  }, [learner]);
  useEffect(
    () => () => {
      if (timer.current) window.clearTimeout(timer.current);
      if (take) URL.revokeObjectURL(take.url);
    },
    [take],
  );

  async function start() {
    setResult(null);
    setNoMic(false);
    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch {
      setNoMic(true);
      return;
    }
    const chunks: Blob[] = [];
    const rec = new MediaRecorder(stream);
    rec.ondataavailable = (e) => {
      if (e.data.size) chunks.push(e.data);
    };
    rec.onstop = () => {
      stream.getTracks().forEach((track) => track.stop());
      setRecording(false);
      void (async () => {
        const ctx = new AudioContext();
        try {
          const audio = await ctx.decodeAudioData(
            await new Blob(chunks, { type: rec.mimeType }).arrayBuffer(),
          );
          const channels = Array.from(
            { length: audio.numberOfChannels },
            (_, i) => audio.getChannelData(i),
          );
          const wav = toServerWav(channels, audio.sampleRate);
          setTake({
            wav,
            url: URL.createObjectURL(new Blob([wav], { type: "audio/wav" })),
          });
        } catch {
          setResult({ ok: false, problems: ["format"], phones: [], heard: [] });
        } finally {
          void ctx.close();
        }
      })();
    };
    recorder.current = rec;
    rec.start();
    setRecording(true);
    timer.current = window.setTimeout(
      () => rec.state === "recording" && rec.stop(),
      MAX_MS,
    );
  }
  function stop() {
    if (timer.current) window.clearTimeout(timer.current);
    if (recorder.current?.state === "recording") recorder.current.stop();
  }
  async function analyse() {
    if (!take || !learner || !status) return;
    setBusy(true);
    try {
      setResult(
        await englishClient().sayWord(
          learner,
          `${lemma}:${pos}`,
          status.consent,
          take.wav,
        ),
      );
    } catch {
      setResult({
        ok: false,
        problems: ["not_analysed"],
        phones: [],
        heard: [],
      });
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="nt-say" data-testid="say-word">
      <div className="nt-actions">
        {recording ? (
          <button type="button" className="en-button small" onClick={stop}>
            {t.stop}
          </button>
        ) : (
          <button
            type="button"
            className="en-button small ghost"
            onClick={() => void start()}
          >
            {t.say}
          </button>
        )}
        {recording && (
          <span className="en-muted" role="status">
            {t.recording}
          </span>
        )}
      </div>
      {noMic && <p className="en-feedback is-wrong">{t.noMic}</p>}
      {take && (
        <div>
          <p>
            {t.yours}: <audio controls src={take.url} />
          </p>
          {status?.analysis &&
            (agreed ? (
              <button
                type="button"
                className="en-button small"
                disabled={busy}
                onClick={() => void analyse()}
              >
                {busy ? vi.english.loading : t.analyse}
              </button>
            ) : (
              <div className="en-feedback">
                <p>{t.consent}</p>
                <button
                  type="button"
                  className="en-button small"
                  onClick={() => {
                    try {
                      localStorage.setItem(CONSENT_KEY, "voice-v1");
                    } catch {
                      /* the choice holds for this page only */
                    }
                    setAgreed(true);
                  }}
                >
                  {t.agree}
                </button>
              </div>
            ))}
          {status && !status.analysis && (
            <p className="en-muted">
              {status.owner ? t.serviceOff : t.compare}
            </p>
          )}
        </div>
      )}
      {result && (
        <div role="status" data-testid="say-result">
          {result.ok ? (
            <>
              <ul className="nt-phones" lang="en-fonipa">
                {result.phones.map((p, i) => (
                  <li key={i} className={p.dropped ? "is-dropped" : ""}>
                    <strong>{p.phone}</strong>
                    <span>{p.dropped ? t.dropped : `${closeness(p.gop)}`}</span>
                    {p.heard && !p.dropped && (
                      <small>
                        {t.heard} {p.heard}
                      </small>
                    )}
                  </li>
                ))}
              </ul>
              <p className="en-muted">{t.rawNote}</p>
            </>
          ) : (
            <p className="en-feedback is-wrong">
              {result.problems.map((p) => t.problems[p] ?? p).join(" ")}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
