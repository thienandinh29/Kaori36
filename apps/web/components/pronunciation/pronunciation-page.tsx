"use client";
import { useEffect, useRef, useState } from "react";
import { englishClient } from "@/lib/english/client";
import { MAX_SECONDS, toServerWav } from "@/lib/pronunciation/wav";
import type {
  PronunciationPrompts,
  RecordingResult,
  RecordingRow,
} from "@/lib/pronunciation/types";
import { vi } from "@/messages/vi";
import { Problem } from "@/components/english/problem";
import { SpeakButton } from "@/components/english/speak-button";
import { useLearner } from "@/components/english/use-learner";

const t = vi.english.pronunciation;
const CONSENT_KEY = "nodetrail_voice_consent";

type Take = { wav: ArrayBuffer; url: string };

/** Reads the decoded channels of a recorded blob; the browser's decoder does the format work. */
async function decode(blob: Blob): Promise<Take> {
  const ctx = new AudioContext();
  try {
    const audio = await ctx.decodeAudioData(await blob.arrayBuffer());
    const channels = Array.from({ length: audio.numberOfChannels }, (_, i) =>
      audio.getChannelData(i),
    );
    const wav = toServerWav(channels, audio.sampleRate);
    return {
      wav,
      url: URL.createObjectURL(new Blob([wav], { type: "audio/wav" })),
    };
  } finally {
    void ctx.close();
  }
}

/** Step 3.1 (specs/pronunciation/step-3.1.md): read a sentence aloud; only the recording's quality is checked. */
export function PronunciationPage() {
  const { learner, error: learnerError, retry } = useLearner();
  const [data, setData] = useState<PronunciationPrompts | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [index, setIndex] = useState(0);
  const [consented, setConsented] = useState(() => {
    try {
      return (
        typeof window !== "undefined" &&
        window.localStorage.getItem(CONSENT_KEY) === "voice-v1"
      );
    } catch {
      return false;
    }
  });
  const [keep, setKeep] = useState(false);
  const [recording, setRecording] = useState(false);
  const [take, setTake] = useState<Take | null>(null);
  const [result, setResult] = useState<RecordingResult | null>(null);
  const [rows, setRows] = useState<RecordingRow[]>([]);
  const [busy, setBusy] = useState(false);
  const [noMic, setNoMic] = useState(false);
  const recorder = useRef<MediaRecorder | null>(null);
  const timer = useRef<number | null>(null);

  useEffect(() => {
    if (!learner) return;
    let live = true;
    const client = englishClient();
    client
      .pronunciationPrompts(learner)
      .then((d) => {
        if (!live) return;
        setData(d);
        if (d.can_record)
          void client.recordings(learner).then((r) => live && setRows(r));
      })
      .catch((e: unknown) => live && setError(e));
    return () => {
      live = false;
    };
  }, [learner]);

  useEffect(
    () => () => void (timer.current && window.clearTimeout(timer.current)),
    [],
  );

  if (learnerError) return <Problem error={learnerError} onRetry={retry} />;
  if (error) return <Problem error={error} />;
  if (!data || !learner)
    return <p className="en-muted">{vi.english.loading}</p>;
  const prompt = data.prompts[index % data.prompts.length]!;
  const sounds = prompt.targets.map(
    (id) => data.sounds.find((s) => s.id === id)?.name_vi ?? id,
  );

  async function start() {
    setResult(null);
    setTake(null);
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
    rec.ondataavailable = (e) => e.data.size && chunks.push(e.data);
    rec.onstop = () => {
      stream.getTracks().forEach((track) => track.stop());
      setRecording(false);
      void decode(new Blob(chunks, { type: rec.mimeType }))
        .then(setTake)
        .catch(() =>
          setResult({
            ok: false,
            problems: ["format"],
            id: null,
            delete_after: null,
          }),
        );
    };
    recorder.current = rec;
    rec.start();
    setRecording(true);
    timer.current = window.setTimeout(
      () => rec.state === "recording" && rec.stop(),
      MAX_SECONDS * 1000,
    );
  }

  function stop() {
    if (timer.current) window.clearTimeout(timer.current);
    if (recorder.current?.state === "recording") recorder.current.stop();
  }

  async function send() {
    if (!take) return;
    setBusy(true);
    try {
      const client = englishClient();
      const r = await client.sendRecording(
        learner!,
        prompt.id,
        data!.consent,
        keep,
        take.wav,
      );
      setResult(r);
      if (r.id) setRows(await client.recordings(learner!));
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }

  async function remove(id: string) {
    await englishClient().deleteRecording(learner!, id);
    setRows((r) => r.filter((x) => x.id !== id));
  }

  return (
    <>
      <section className="en-card nt-pron" data-testid="pronunciation">
        <h1>{t.title}</h1>
        <p className="en-muted">{t.intro}</p>
        <div className="nt-pron-prompt">
          <p className="en-muted">
            {t.sentence} · {prompt.level}
          </p>
          <p className="nt-pron-text" lang="en">
            {prompt.text} <SpeakButton text={prompt.text} />
          </p>
          <p className="en-muted">
            {t.targets}: {sounds.join(" · ")}
          </p>
        </div>

        {!data.can_record ? (
          <p className="en-badge draft">{t.ownerOnly}</p>
        ) : !consented ? (
          <div className="nt-pron-consent">
            <p>{t.consent}</p>
            <label>
              <input
                type="checkbox"
                onChange={(e) => {
                  if (!e.target.checked) return;
                  setConsented(true);
                  try {
                    window.localStorage.setItem(CONSENT_KEY, data.consent);
                  } catch {
                    // asked again next time
                  }
                }}
              />{" "}
              {t.consentAgree}
            </label>
          </div>
        ) : (
          <>
            <label className="nt-pron-keep">
              <input
                type="checkbox"
                checked={keep}
                onChange={(e) => setKeep(e.target.checked)}
              />{" "}
              {t.keep}
            </label>
            <div className="nt-actions">
              {recording ? (
                <button type="button" className="en-button" onClick={stop}>
                  {t.stop}
                </button>
              ) : (
                <button
                  type="button"
                  className="en-button"
                  onClick={() => void start()}
                >
                  {take ? t.again : t.record}
                </button>
              )}
              {take && !recording && (
                <button
                  type="button"
                  className="en-button ghost"
                  disabled={busy}
                  onClick={() => void send()}
                >
                  {t.send}
                </button>
              )}
              <button
                type="button"
                className="en-button ghost"
                onClick={() => {
                  setIndex((i) => i + 1);
                  setTake(null);
                  setResult(null);
                }}
              >
                {t.next}
              </button>
            </div>
            {recording && <p className="nt-pron-live">{t.recording}</p>}
            {noMic && <p className="en-feedback is-wrong">{t.noMic}</p>}
            {take && (
              <p>
                {t.yours}: <audio controls src={take.url} />
              </p>
            )}
            {result && (
              <div
                className={`en-feedback ${result.ok ? "is-right" : "is-wrong"}`}
                role="status"
              >
                {result.ok ? (
                  <p>
                    {t.ok}{" "}
                    {result.delete_after
                      ? `${t.okUntil} ${new Date(result.delete_after).toLocaleString("vi-VN")}.`
                      : t.kept}
                  </p>
                ) : (
                  result.problems.map((p) => (
                    <p key={p}>{t.problems[p] ?? p}</p>
                  ))
                )}
              </div>
            )}
          </>
        )}
      </section>
      {data.can_record && (
        <section className="en-card">
          <h2>{t.list}</h2>
          {rows.length === 0 ? (
            <p className="en-muted">{t.none}</p>
          ) : (
            <ul className="nt-pron-rows">
              {rows.map((r) => (
                <li key={r.id}>
                  <span>
                    {r.prompt_id} · {r.seconds.toFixed(1)} {t.seconds}
                    {r.delete_after
                      ? ` · ${t.okUntil} ${new Date(r.delete_after).toLocaleString("vi-VN")}`
                      : ` · ${t.kept}`}
                  </span>
                  <button
                    type="button"
                    className="en-button ghost small"
                    onClick={() => void remove(r.id)}
                  >
                    {t.delete}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>
      )}
    </>
  );
}
