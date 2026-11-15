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
