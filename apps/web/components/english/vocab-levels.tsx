"use client";
import type { Level, VocabLevels as Levels } from "@/lib/english/types";
import { vi } from "@/messages/vi";

const t = vi.english.vocab;

/** Choose the level new words come from (specs/vocabulary, levels). Due reviews come first anyway. */
export function VocabLevelPicker({
  levels,
  chosen,
  onChoose,
}: {
  levels: Levels;
  chosen: Level;
  onChoose: (level: Level) => void;
}) {
  return (
    <div className="nt-levels" role="group" aria-label={t.levelPick}>
      <p className="en-muted">{t.levelPick}</p>
      <div className="nt-levels-row">
        {levels.levels.map((l) => {
          const left = l.words - l.started;
          return (
            <button
              key={l.level}
              type="button"
              aria-pressed={l.level === chosen}
              className={l.level === chosen ? "is-chosen" : undefined}
              onClick={() => onChoose(l.level)}
            >
              <strong>{l.level}</strong>
              {l.level === levels.suggested && (
                <small className="nt-levels-tag">{t.levelSuggested}</small>
              )}
              <small>
                {left > 0
                  ? t.levelLeft.replace("{n}", String(left))
                  : t.levelAllStarted}
              </small>
              <small>
                {t.levelStarted
                  .replace("{started}", String(l.started))
                  .replace("{words}", String(l.words))}
              </small>
            </button>
          );
        })}
      </div>
    </div>
  );
}
