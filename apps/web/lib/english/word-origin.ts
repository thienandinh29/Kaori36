import type { WordCard } from "./types";
import { vi } from "@/messages/vi";

const t = vi.english.vocab;

/** How a word's labels read: imported words say where they come from and what is estimated. */
export function originLabels(card: Pick<WordCard, "origin" | "level" | "ipa">) {
  const imported = card.origin !== "authored";
  return {
    level: imported ? `${card.level} · ${t.levelEstimated}` : card.level,
    ipaTitle: imported ? t.ipaAuto : t.ipaTitle,
    source:
      card.origin === "tsl"
        ? t.importedTsl
        : card.origin === "bsl"
          ? t.importedBsl
          : imported
            ? t.importedFrom.replace("{list}", card.origin.toUpperCase())
            : null,
  };
}
