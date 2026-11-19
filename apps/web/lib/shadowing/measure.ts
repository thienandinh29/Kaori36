// Shadowing timing (specs/listening-reading/step-4.4d.md): pure measures from samples alone, no
// recogniser. They describe timing only (how long, how many pauses), never correctness.
export const FRAME_SECONDS = 0.02;
export const MIN_PAUSE_SECONDS = 0.25;

export interface Timing {
  /** From the first to the last voiced frame (leading and trailing silence trimmed). */
  seconds: number;
  /** Silences of at least MIN_PAUSE_SECONDS inside the speech. */
  pauses: number;
}

/** Root mean square energy per 20 ms frame. */
export function frameEnergy(samples: Float32Array, rate: number): number[] {
  const size = Math.max(1, Math.round(rate * FRAME_SECONDS));
  const out: number[] = [];
  for (let start = 0; start < samples.length; start += size) {
    let sum = 0;
    const end = Math.min(samples.length, start + size);
    for (let i = start; i < end; i++) sum += samples[i]! * samples[i]!;
    out.push(Math.sqrt(sum / (end - start)));
  }
  return out;
}

/** Speech span and pauses: a frame is voiced above a tenth of the loudest frame (and a floor). */
export function timing(samples: Float32Array, rate: number): Timing {
  const energy = frameEnergy(samples, rate);
  const peak = Math.max(0, ...energy);
  const threshold = Math.max(0.01, peak * 0.1);
  const voiced = energy.map((e) => e >= threshold);
  const first = voiced.indexOf(true);
  const last = voiced.lastIndexOf(true);
  if (first < 0) return { seconds: 0, pauses: 0 };
  const minFrames = Math.round(MIN_PAUSE_SECONDS / FRAME_SECONDS);
  let pauses = 0;
  let run = 0;
  for (let i = first; i <= last; i++) {
    if (voiced[i]) {
      if (run >= minFrames) pauses++;
      run = 0;
    } else run++;
  }
  return {
    seconds: Math.round((last - first + 1) * FRAME_SECONDS * 100) / 100,
    pauses,
  };
}

/** Your time as a share of the model's (1 = the same pace), or null without a model. */
export function paceRatio(yours: Timing, model: Timing): number | null {
  if (model.seconds <= 0 || yours.seconds <= 0) return null;
  return Math.round((yours.seconds / model.seconds) * 100) / 100;
}
