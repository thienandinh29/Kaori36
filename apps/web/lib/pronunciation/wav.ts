// Turning a browser recording into what the server expects (specs/pronunciation/step-3.1.md):
// 16 kHz, mono, 16-bit PCM WAV. Pure and tested; the browser's own resampler is used when present.
export const RATE = 16000;
export const MAX_SECONDS = 15;

/** The average of the channels. */
export function toMono(channels: Float32Array[]): Float32Array {
  if (channels.length === 0) return new Float32Array(0);
  if (channels.length === 1) return channels[0]!;
  const out = new Float32Array(channels[0]!.length);
  for (const ch of channels)
    for (let i = 0; i < out.length; i++)
      out[i]! += (ch[i] ?? 0) / channels.length;
  return out;
}

/** Resample by averaging each output step's input span (a box filter, enough for speech at 16 kHz). */
export function resample(
  data: Float32Array,
  from: number,
  to: number,
): Float32Array {
  if (from === to) return data;
  const ratio = from / to;
  const out = new Float32Array(Math.floor(data.length / ratio));
  for (let i = 0; i < out.length; i++) {
    const start = Math.floor(i * ratio);
    const end = Math.max(start + 1, Math.floor((i + 1) * ratio));
    let sum = 0;
    for (let j = start; j < end && j < data.length; j++) sum += data[j]!;
    out[i] = sum / (end - start);
  }
  return out;
}

/** 16-bit PCM WAV bytes of mono samples in [-1, 1] (clipped). */
export function encodeWav(samples: Float32Array, rate = RATE): ArrayBuffer {
  const buffer = new ArrayBuffer(44 + samples.length * 2);
  const v = new DataView(buffer);
  const text = (offset: number, s: string) => {
    for (let i = 0; i < s.length; i++) v.setUint8(offset + i, s.charCodeAt(i));
  };
  text(0, "RIFF");
  v.setUint32(4, 36 + samples.length * 2, true);
  text(8, "WAVE");
  text(12, "fmt ");
  v.setUint32(16, 16, true); // PCM header size
  v.setUint16(20, 1, true); // PCM
  v.setUint16(22, 1, true); // mono
  v.setUint32(24, rate, true);
  v.setUint32(28, rate * 2, true); // bytes per second
  v.setUint16(32, 2, true); // bytes per frame
  v.setUint16(34, 16, true); // bits per sample
  text(36, "data");
  v.setUint32(40, samples.length * 2, true);
  for (let i = 0; i < samples.length; i++) {
    const s = Math.max(-1, Math.min(1, samples[i]!));
    v.setInt16(44 + i * 2, s < 0 ? s * 0x8000 : s * 0x7fff, true);
  }
  return buffer;
}

/** A decoded recording as WAV for the server: mono, 16 kHz, at most `maxSeconds` (a read sentence: 15). */
export function toServerWav(
  channels: Float32Array[],
  sampleRate: number,
  maxSeconds: number = MAX_SECONDS,
): ArrayBuffer {
  const mono = resample(toMono(channels), sampleRate, RATE);
  return encodeWav(mono.subarray(0, Math.floor(maxSeconds * RATE)));
}
