"use client";
import { useEffect, useRef, useState } from "react";
import { MAX_SECONDS } from "@/lib/pronunciation/wav";
import { timing, type Timing } from "@/lib/shadowing/measure";
import { vi } from "@/messages/vi";

const t = vi.english.shadowing;

/** Decoded samples of any audio the browser can play (the first channel). */
export async function measure(blob: Blob): Promise<Timing> {
  const ctx = new AudioContext();
  try {
    const audio = await ctx.decodeAudioData(await blob.arrayBuffer());
    return timing(audio.getChannelData(0), audio.sampleRate);
  } finally {
    void ctx.close();
  }
}

export interface Take {
  url: string;
  timing: Timing;
}

/**
 * Record the learner in the browser only: the recording is never uploaded, and it is forgotten when
 * the next one starts or the page closes (step 4.4d).
 */
export function Recorder({
  onTake,
  disabled = false,
}: {
  onTake: (take: Take | null) => void;
  disabled?: boolean;
}) {
  const [recording, setRecording] = useState(false);
  const [noMic, setNoMic] = useState(false);
  const recorder = useRef<MediaRecorder | null>(null);
  const timer = useRef<number | null>(null);
  const url = useRef<string | null>(null);

  useEffect(
    () => () => {
      if (timer.current) window.clearTimeout(timer.current);
      if (recorder.current?.state === "recording") recorder.current.stop();
      if (url.current) URL.revokeObjectURL(url.current);
    },
    [],
  );

  async function start() {
    setNoMic(false);
    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch {
      setNoMic(true);
      return;
    }
    if (url.current) URL.revokeObjectURL(url.current);
    url.current = null;
    onTake(null);
    const chunks: Blob[] = [];
    const rec = new MediaRecorder(stream);
    rec.ondataavailable = (e) => {
      if (e.data.size) chunks.push(e.data);
    };
    rec.onstop = () => {
      stream.getTracks().forEach((track) => track.stop());
      setRecording(false);
      const blob = new Blob(chunks, { type: rec.mimeType });
      const href = URL.createObjectURL(blob);
      url.current = href;
      void measure(blob)
        .then((m) => onTake({ url: href, timing: m }))
        .catch(() => onTake({ url: href, timing: { seconds: 0, pauses: 0 } }));
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

  return (
    <div className="nt-recorder">
      {recording ? (
        <button type="button" className="en-button small" onClick={stop}>
          {t.stop}
        </button>
      ) : (
        <button
          type="button"
          className="en-button small"
          disabled={disabled}
          onClick={() => void start()}
        >
          {t.record}
        </button>
      )}
      {recording && (
        <span className="en-muted" role="status">
          {" "}
          {t.recording}
        </span>
      )}
      {noMic && <p className="en-feedback is-wrong">{t.noMic}</p>}
    </div>
  );
}
