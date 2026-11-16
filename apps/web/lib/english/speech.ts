// Hearing English with the browser's own voice (specs/speech, step S1). Pure helpers, tested in speech.test.ts.

/** The fields of a SpeechSynthesisVoice that the choice depends on. */
export interface VoiceLike {
  name: string;
  lang: string;
  localService: boolean;
}

export const MAX_SPEAK_CHARS = 300;
export const RATES = { normal: 1, slow: 0.7 } as const;
export type Pace = keyof typeof RATES;

/** The text to speak, or null when there is nothing worth speaking or it is too long. */
export function speakable(text: string): string | null {
  const flat = text
    .normalize("NFC")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/^["“”']+|["“”']+$/g, "")
    .trim();
  if (!/[A-Za-z]/.test(flat) || flat.length > MAX_SPEAK_CHARS) return null;
  return flat;
}

const langOf = (v: VoiceLike) => v.lang.replace("_", "-").toLowerCase();

/**
 * The best English voice: British, then American, then any English; on-device before network.
 * `allowNetwork: false` (text from the learner's own work) refuses network voices, which receive the text.
 */
export function pickVoice(
  voices: readonly VoiceLike[],
  allowNetwork: boolean,
): VoiceLike | null {
  const rank = (v: VoiceLike) => {
    const lang = langOf(v);
    const accent = lang === "en-gb" ? 0 : lang === "en-us" ? 1 : 2;
    return accent * 2 + (v.localService ? 0 : 1);
  };
  const usable = voices.filter(
    (v) => langOf(v).startsWith("en") && (allowNetwork || v.localService),
  );
  if (usable.length === 0) return null;
  return [...usable].sort(
    (a, b) => rank(a) - rank(b) || a.name.localeCompare(b.name),
  )[0];
}

/** Whether this browser can speak at all (false on the server and in browsers without speech). */
export function canSpeak(scope: unknown): boolean {
  return (
    typeof scope === "object" &&
    scope !== null &&
    "speechSynthesis" in scope &&
    "SpeechSynthesisUtterance" in scope
  );
}

/** Whether the self-hosted voice (specs/speech, S2) answers, from GET /speech/status. Strict. */
export function parseSpeechStatus(value: unknown): boolean {
  if (
    typeof value !== "object" ||
    value === null ||
    typeof (value as { available?: unknown }).available !== "boolean"
  )
    return false;
  return (value as { available: boolean }).available;
}

type Fetch = typeof fetch;

/** The server voice's availability; any failure means "use the browser's voice". */
export async function serverVoiceAvailable(
  fetcher: Fetch = (...a) => fetch(...a),
): Promise<boolean> {
  try {
    const r = await fetcher("/api/backend/speech/status", {
      cache: "no-store",
      signal: AbortSignal.timeout(5000),
    });
    return r.ok && parseSpeechStatus(await r.json());
  } catch {
    return false;
  }
}

/** WAV audio of `text` from the server voice; throws when it cannot be had. */
export async function serverAudio(
  text: string,
  pace: Pace,
  fetcher: Fetch = (...a) => fetch(...a),
): Promise<Blob> {
  const r = await fetcher("/api/backend/speech", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, pace }),
    signal: AbortSignal.timeout(15000),
  });
  if (!r.ok || r.headers.get("content-type") !== "audio/wav")
    throw new Error(`speech ${r.status}`);
  return r.blob();
}
