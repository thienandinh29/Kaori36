"use client";
import type { Milestone } from "@/lib/english/types";
import { KNOWN_LINE, band, totals } from "@/lib/english/trail";
import { percent } from "@/lib/english/view";
import { vi } from "@/messages/vi";

const t = vi.english.roadmap;
const BANDS = ["strong", "growing", "gap"] as const;

/** One bar per hidden node, grouped by milestone: indigo up to p_known, hatched above (still missing). */
export function Skyline({
  milestones,
  selected,
  onSelect,
}: {
  milestones: Milestone[];
  selected: string | null;
  onSelect: (slug: string) => void;
}) {
  const T = totals(milestones);
  const line = `${(1 - KNOWN_LINE) * 100}%`;
  return (
    <section className="nt-sky" aria-labelledby="nt-sky-h">
      <h2 id="nt-sky-h">{t.skyTitle}</h2>
      <p className="nt-sub">{t.skyHint}</p>
      <div className="nt-totals">
        {BANDS.map((b) => (
          <div key={b}>
            <b>
              <i className={`nt-sw is-${b}`} aria-hidden="true" />
              {T[b]}
            </b>
            <span>
              {t.bands[b]}
              <br />
              {t.partsOf} {T.all} {t.partsWord}
            </span>
          </div>
        ))}
      </div>
      <div className="nt-chart" role="group" aria-label={t.skyLabel}>
        <div className="nt-axis" aria-hidden="true">
          <span style={{ top: 0 }}>100</span>
          <span style={{ top: line }}>{percent(KNOWN_LINE)}</span>
          <div className="nt-line" style={{ top: line }} title={t.knownLine} />
          <span style={{ top: "50%" }}>50</span>
          <span style={{ top: "100%" }}>0</span>
        </div>
        {milestones.map((m) => (
          <button
            key={m.slug}
            type="button"
            className="nt-grp"
            style={{ flexGrow: Math.max(1, m.hidden.length) }}
            aria-pressed={m.slug === selected}
            aria-label={`${m.name_vi}: ${m.hidden
              .map((h) => `${h.name_vi} ${percent(h.p_known)}%`)
              .join(", ")}`}
            onClick={() => onSelect(m.slug)}
          >
            <span className="nt-bars">
              {m.hidden.map((h) => (
                <span
                  key={h.slug}
                  className="nt-bar"
                  title={`${h.name_vi}: ${percent(h.p_known)}%`}
                >
                  <i
                    className={`is-${band(h)}`}
                    style={{ height: `${percent(h.p_known)}%` }}
                  />
                </span>
              ))}
            </span>
            <span className="nt-grp-lv">{m.level}</span>
          </button>
        ))}
      </div>
    </section>
  );
}
