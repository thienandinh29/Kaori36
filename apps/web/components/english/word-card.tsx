import type { WordCard as Card } from "@/lib/english/types";
import { originLabels } from "@/lib/english/word-origin";
import { SpeakButton } from "./speak-button";

export function WordCard({ card }: { card: Card }) {
  const labels = originLabels(card);
  return (
    <div className="en-word">
      <div className="en-word-top">
        <strong lang="en">{card.lemma}</strong>
        {card.ipa && (
          <span className="nt-ipa" lang="en-fonipa" title={labels.ipaTitle}>
            {card.ipa}
          </span>
        )}
        <SpeakButton text={card.lemma} />
        <span className="nt-chips">
          <span>{card.pos}</span>
          <span>{labels.level}</span>
        </span>
      </div>
      <p lang="en">{card.definition}</p>
      {card.vi && <p className="en-word-vi">{card.vi}</p>}
      <p className="en-muted" lang="en">
        “{card.example}” <SpeakButton text={card.example} />
      </p>
      {labels.source && <p className="en-muted nt-source">{labels.source}</p>}
    </div>
  );
}
