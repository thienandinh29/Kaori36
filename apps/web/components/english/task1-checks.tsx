import type { EssayResult } from "@/lib/english/types";
import { vi } from "@/messages/vi";

const w = vi.english.writing;

/** What the code found when it checked the report against the chart (specs/writing/step-2.5.md). */
export function Task1Checks({ result }: { result: EssayResult }) {
  const t = result.task1;
  if (!t) return null;
  const unsupported = t.numbers.filter((n) => !n.supported);
  const missed = t.features.filter((f) => !f.covered);
  return (
    <section className="en-card" data-testid="task1-checks">
      <h2>{w.task1Title}</h2>
      <p className="en-muted">{w.task1Note}</p>
      <h3>{w.task1Numbers}</h3>
      {unsupported.length === 0 ? (
        <p>{w.task1NumbersOk}</p>
      ) : (
        <ul>
          {unsupported.map((n, i) => (
            <li key={i} data-testid="unsupported-number">
              <strong>{n.text}</strong>: {w.task1NotFound}
            </li>
          ))}
        </ul>
      )}
      <h3>{w.task1Features}</h3>
      {missed.length === 0 ? (
        <p>{w.task1FeaturesOk}</p>
      ) : (
        <ul>
          {missed.map((f, i) => (
            <li key={i} lang="en">
              {f.text}
            </li>
          ))}
        </ul>
      )}
      <p>{t.overview ? w.task1OverviewYes : w.task1OverviewNo}</p>
    </section>
  );
}
