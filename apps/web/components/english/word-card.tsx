import type { WordCard as Card } from "@/lib/english/types";

export function WordCard({ card }: { card: Card }) {
  return (
    <div className="en-word">
      <div className="en-word-top">
        <strong lang="en">{card.lemma}</strong>
        <span className="nt-chips">
          <span>{card.pos}</span>
          <span>{card.level}</span>
        </span>
      </div>
      <p lang="en">{card.definition}</p>
      {card.vi && <p className="en-word-vi">{card.vi}</p>}
      <p className="en-muted" lang="en">
        “{card.example}”
      </p>
    </div>
  );
}
