"use client";
// The examiner's voice and the answer recorder for the Speaking test (specs/speaking/step-5.4a.md).
import {
  canSpeak,
  pickVoice,
  serverAudio,
  serverVoiceAvailable,
} from "@/lib/english/speech";
import { toServerWav } from "@/lib/pronunciation/wav";
import { ms, readingSeconds, voiceChunks } from "@/lib/speaking/exam";

export type VoiceMode = "server" | "browser" | "none";

export interface Examiner {
  mode: VoiceMode;
  /** Resolves when the line has been spoken (or shown long enough), or at once when aborted. */
  say(text: string, signal: AbortSignal): Promise<void>;
}

/** Waits `millis`, or less when the signal aborts. */
export function wait(millis: number, signal: AbortSignal): Promise<void> {
  return new Promise((resolve) => {
    if (signal.aborted) return resolve();
    const done = () => {
      window.clearTimeout(timer);
      signal.removeEventListener("abort", done);
      resolve();
    };
    const timer = window.setTimeout(done, millis);
    signal.addEventListener("abort", done, { once: true });
  });
}

function playUrl(
  url: string,
  signal: AbortSignal,
  guard: number,
): Promise<void> {
  return new Promise((resolve) => {
    const audio = new Audio(url);
    const done = () => {
      window.clearTimeout(timer);
      audio.pause();
      signal.removeEventListener("abort", done);
      resolve();
    };
    const timer = window.setTimeout(done, guard);
    audio.addEventListener("ended", done, { once: true });
    audio.addEventListener("error", done, { once: true });
    signal.addEventListener("abort", done, { once: true });
    audio.play().catch(done);
  });
}

async function browserVoice(): Promise<SpeechSynthesisVoice | null> {
  if (!canSpeak(window)) return null;
  const synth = window.speechSynthesis;
  let voices = synth.getVoices();
  if (voices.length === 0)
    voices = await new Promise<SpeechSynthesisVoice[]>((resolve) => {
      const t = window.setTimeout(() => resolve(synth.getVoices()), 1500);
      synth.addEventListener(
        "voiceschanged",
        () => {
          window.clearTimeout(t);
          resolve(synth.getVoices());
        },
        { once: true },
      );
    });
  return (pickVoice(voices, true) as SpeechSynthesisVoice | null) ?? null;
}

/**
 * The self-hosted voice when the server has one, else the browser's English voice, else none (the
 * line is shown on screen for its reading time). `speed` < 1 is for automated tests: no voice, and
 * every wait shortened.
 */
export async function makeExaminer(speed: number): Promise<Examiner> {
  const silent: Examiner = {
    mode: "none",
    say: (text, signal) => wait(ms(readingSeconds(text), speed), signal),
  };
  if (speed < 1) return silent;
  if (await serverVoiceAvailable())
    return {
      mode: "server",
      async say(text, signal) {
        for (const chunk of voiceChunks(text)) {
          if (signal.aborted) return;
          let url: string;
          try {
            url = URL.createObjectURL(await serverAudio(chunk, "normal"));
          } catch {
            await silent.say(chunk, signal);
            continue;
          }
          try {
            await playUrl(url, signal, ms(readingSeconds(chunk) * 3 + 5, 1));
          } finally {
            URL.revokeObjectURL(url);
          }
        }
      },
    };
  const voice = await browserVoice();
  if (!voice) return silent;
  return {
    mode: "browser",
    say(text, signal) {
      return new Promise((resolve) => {
        const synth = window.speechSynthesis;
        const u = new SpeechSynthesisUtterance(text);
        u.voice = voice;
        u.lang = voice.lang;
        const done = () => {
          window.clearTimeout(timer);
          signal.removeEventListener("abort", stop);
          resolve();
        };
        const stop = () => {
          synth.cancel();
          done();
        };
        // Some browsers never fire "end": give up after twice the reading time.
        const timer = window.setTimeout(
          stop,
          ms(readingSeconds(text) * 2 + 3, 1),
        );
        u.onend = done;
        u.onerror = done;
        signal.addEventListener("abort", stop, { once: true });
        synth.cancel();
        synth.speak(u);
      });
    },
  };
}

/** Records from the open stream until `limit` ms pass, `stop` is called, or the signal aborts. */
export function recordAnswer(
  stream: MediaStream,
  limit: number,
  signal: AbortSignal,
  onStopReady: (stop: () => void) => void,
): Promise<Blob> {
  return new Promise((resolve) => {
    const chunks: Blob[] = [];
    const rec = new MediaRecorder(stream);
    const stop = () => {
      if (rec.state === "recording") rec.stop();
    };
    const timer = window.setTimeout(stop, limit);
    rec.ondataavailable = (e) => {
      if (e.data.size) chunks.push(e.data);
    };
    rec.onstop = () => {
      window.clearTimeout(timer);
      signal.removeEventListener("abort", stop);
      resolve(new Blob(chunks, { type: rec.mimeType }));
    };
    signal.addEventListener("abort", stop, { once: true });
    onStopReady(stop);
    rec.start();
  });
}

/** The server's WAV (16 kHz mono) of a recorded blob, cut at `maxSeconds`. */
export async function toWav(
  blob: Blob,
  maxSeconds: number,
): Promise<ArrayBuffer> {
  const ctx = new AudioContext();
  try {
    const audio = await ctx.decodeAudioData(await blob.arrayBuffer());
    const channels = Array.from({ length: audio.numberOfChannels }, (_, i) =>
      audio.getChannelData(i),
    );
    return toServerWav(channels, audio.sampleRate, maxSeconds);
  } finally {
    void ctx.close();
  }
}
