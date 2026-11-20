import type { GrammarIssue } from "@/lib/english/types";

/** The sentence with the error's span marked. */
export function Marked({ issue }: { issue: GrammarIssue }) {
  const from = issue.start - issue.sentence_start;
  const to = from + issue.end - issue.start;
  return (
    <p lang="en" className="en-issue-sentence">
      {issue.sentence.slice(0, from)}
      <mark>{issue.sentence.slice(from, to)}</mark>
      {issue.sentence.slice(to)}
    </p>
  );
}
