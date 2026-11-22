import {
  answeredText,
  answersText,
  developmentText,
  findingText,
} from "@/lib/english/structure";
import type { EssayResult } from "@/lib/english/types";
import { vi } from "@/messages/vi";

const w = vi.english.writing;

/**
 * The essay's structure (specs/writing/step-2.11.md, 2.11b): the parts of the question, the
 * position, each body paragraph's main idea, and the code's findings. Every quote shown was
 * checked to be in its paragraph; nothing here moves mastery.
 */
export function StructureChecks({ result }: { result: EssayResult }) {
  if (result.structure === undefined) return null; // Task 1, or analysed before 2.11b
  if (result.structure === null)
    return result.structureUnavailableVi ? (
      <section className="en-card">
        <h2>{w.structureTitle}</h2>
        <p className="en-muted">{result.structureUnavailableVi}</p>
      </section>
    ) : null;
  const s = result.structure;
  const hasPosition = s.parts.some((p) => p.position);
  return (
    <section className="en-card" data-testid="structure-checks">
      <h2>{w.structureTitle}</h2>
      <p className="en-muted">{w.structureNote}</p>
      {s.findings.length === 0 ? (
        <p>{w.structureNoFindings}</p>
      ) : (
        <ul>
          {s.findings.map((f, i) => (
            <li key={i} data-testid="structure-finding" data-kind={f.kind}>
              <span
                className={f.level === "issue" ? "en-badge" : "en-badge next"}
              >
                {f.level === "issue" ? w.findingIssue : w.findingHint}
              </span>{" "}
              {findingText(f, s)}
              {f.quotes.map((q) => (
                <q key={q} lang="en">
                  {q}
                </q>
              ))}
            </li>
          ))}
        </ul>
      )}
      <h3>{w.structureParts}</h3>
      <ol>
        {s.parts.map((p, i) => (
          <li key={i} data-answered={String(p.answered)}>
            <span lang="en">{p.text}</span>
            {p.position && <> {w.partPosition}</>}:{" "}
            <strong>{answeredText(p.answered)}</strong>
          </li>
        ))}
      </ol>
      {hasPosition && (
        <>
          <h3>{w.structurePosition}</h3>
          <ul>
            {(
              [
                [w.structureIntro, s.introduction],
                [w.structureConclusion, s.conclusion],
              ] as const
            ).map(([label, pos]) => (
              <li key={label}>
                {label}:{" "}
                {pos.stance === null ? (
                  w.structureUnsure
                ) : pos.quote ? (
                  <q lang="en">{pos.quote}</q>
                ) : (
                  w.structureNoPosition
                )}
              </li>
            ))}
          </ul>
        </>
      )}
      {s.body.length > 0 && (
        <>
          <h3>{w.structureOutline}</h3>
          <ul>
            {s.body.map((b) => (
              <li key={b.paragraph}>
                <strong>
                  {w.structureParagraph.replace("{n}", String(b.paragraph))}
                </strong>
                : <q lang="en">{b.main_idea}</q>
                {" · "}
                {answersText(b.answers)}
                {" · "}
                {developmentText(b.development)}
              </li>
            ))}
          </ul>
        </>
      )}
      {s.dropped > 0 && (
        <p className="en-muted">
          {w.structureDropped.replace("{n}", String(s.dropped))}
        </p>
      )}
    </section>
  );
}
