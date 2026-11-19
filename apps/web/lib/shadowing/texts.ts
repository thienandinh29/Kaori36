// Shadowing sentences from the Reading bank (step 4.4d), decoded strictly.
import { DataError, record, string } from "@/lib/decode";

export interface ShadowTexts {
  available: boolean;
  texts: { slug: string; title: string; sentences: number }[];
}
export interface ShadowText {
  slug: string;
  title: string;
  sentences: { id: string; text: string }[];
}

function list(v: unknown): unknown[] {
  if (!Array.isArray(v)) throw new DataError("contract");
  return v;
}

export function parseShadowTexts(value: unknown): ShadowTexts {
  const r = record(value);
  if (typeof r.available !== "boolean") throw new DataError("contract");
  return {
    available: r.available,
    texts: list(r.texts).map((t) => {
      const x = record(t);
      if (typeof x.sentences !== "number") throw new DataError("contract");
      return {
        slug: string(x.slug),
        title: string(x.title),
        sentences: x.sentences,
      };
    }),
  };
}

export function parseShadowText(value: unknown): ShadowText {
  const r = record(value);
  return {
    slug: string(r.slug),
    title: string(r.title),
    sentences: list(r.sentences).map((s) => {
      const x = record(s);
      return { id: string(x.id), text: string(x.text) };
    }),
  };
}
