import type { ReviewItem } from "@/lib/reading/review";

/** The question as the learner sees it, plus its options or headings. */
export function Question({ item }: { item: Pick<ReviewItem, "question"> }) {
  const q = item.question;
  const text =
    (q.statement as string | undefined) ??
    (q.stem as string | undefined) ??
    (q.sentence as string | undefined) ??
    "";
  const options = Array.isArray(q.options) ? (q.options as string[]) : null;
  const headings = Array.isArray(q.headings) ? (q.headings as string[]) : null;
  return (
    <div lang="en">
      {text && <p>{text}</p>}
      {options && (
        <ol type="A">
          {options.map((o, i) => (
            <li key={i}>{o}</li>
          ))}
        </ol>
      )}
      {headings && (
        <ol start={0}>
          {headings.map((h, i) => (
            <li key={i}>{h}</li>
          ))}
        </ol>
      )}
    </div>
  );
}
