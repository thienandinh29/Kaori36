// Sena's voice in a lesson (specs/grammar-lessons): the server voice when it answers, else the browser's.
// Lesson text is public, so a browser network voice is allowed. Resolves true when the sentence was
// heard to the end, false when nothing could speak it (the learner reads the subtitle and goes on).
import {
  RATES,
  canSpeak,
  pickVoice,
  serverAudio,
  serverVoiceAvailable,
  speakable,
  type Pace,
} from "@/lib/english/speech";

let server: Promise<boolean> | null = null;
const cache = new Map<string, string>();
let current: { stop: () => void } | null = null;
// Skipping ahead cancels the sentence's audio request too: a burst of unfinished requests would
// hold the browser's connections (answers then wait) and load the voice service for nothing.
let pending: AbortController | null = null;

export function stopNarration(): void {
  pending?.abort();
  pending = null;
  current?.stop();
  current = null;
}

export async function narrate(text: string, pace: Pace): Promise<boolean> {
  stopNarration();
  const words = speakable(text);
  if (!words) return false;
  server ??= serverVoiceAvailable();
  if (await server) {
    const controller = new AbortController();
    pending = controller;
    try {
      const key = `${pace}|${words}`;
      let url = cache.get(key);
      if (!url) {
        const blob = await serverAudio(words, pace, (input, init) =>
          fetch(input, {
            ...init,
            signal: AbortSignal.any(
              [init?.signal, controller.signal].filter(
                (x): x is AbortSignal => !!x,
              ),
            ),
          }),
        );
        url = URL.createObjectURL(blob);
        cache.set(key, url);
      }
      if (controller.signal.aborted) return false; // skipped while it loaded
      const audio = new Audio(url);
      return await new Promise<boolean>((resolve) => {
        current = {
          stop: () => {
            audio.pause();
            resolve(false);
          },
        };
        audio.onended = () => resolve(true);
        audio.onerror = () => resolve(false);
        audio.play().catch(() => resolve(false));
      });
    } catch {
      if (controller.signal.aborted) return false; // skipped, not failed
      // the server voice failed: the browser's voice below
    } finally {
      if (pending === controller) pending = null;
    }
  }
  if (!canSpeak(window)) return false;
  const synth = window.speechSynthesis;
  const voice = pickVoice(
    synth.getVoices(),
    true,
  ) as SpeechSynthesisVoice | null;
  if (!voice) return false;
  return new Promise<boolean>((resolve) => {
    const u = new SpeechSynthesisUtterance(words);
    u.voice = voice;
    u.lang = voice.lang;
    u.rate = RATES[pace];
    u.onend = () => resolve(true);
    u.onerror = () => resolve(false);
    current = {
      stop: () => {
        synth.cancel();
        resolve(false);
      },
    };
    synth.cancel();
    synth.speak(u);
  });
}
