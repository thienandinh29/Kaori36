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

/** Choose the topic new words come from; "Tất cả" is every topic (specs/vocabulary, topics). */
export function VocabTopicPicker({
  levels,
  topic,
  onChoose,
}: {
  levels: Levels;
  topic: string;
  onChoose: (topic: string) => void;
}) {
  if (levels.topics.length === 0) return null;
  const all = { slug: "", name_vi: t.topicAll, words: 0, started: 0 };
  return (
    <div className="nt-levels nt-topics" role="group" aria-label={t.topicPick}>
      <p className="en-muted">{t.topicPick}</p>
      <div className="nt-levels-row">
        {[all, ...levels.topics].map((x) => (
          <button
            key={x.slug || "all"}
            type="button"
            aria-pressed={x.slug === topic}
            className={x.slug === topic ? "is-chosen" : undefined}
            onClick={() => onChoose(x.slug)}
          >
            <strong>{x.name_vi}</strong>
            {x.slug && (
              <small>
                {t.levelStarted
                  .replace("{started}", String(x.started))
                  .replace("{words}", String(x.words))}
              </small>
            )}
          </button>
        ))}
      </div>
    </div>
  );
}
