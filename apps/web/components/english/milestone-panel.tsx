"use client";
import Link from "next/link";
import type { Milestone } from "@/lib/english/types";
import { band, knownMissing, milestoneShare } from "@/lib/english/trail";
import { percent, statusLabel } from "@/lib/english/view";
import { vi } from "@/messages/vi";
import { Sena } from "@/components/sena/sena";

const t = vi.english;

/** A milestone opened from the map or the skyline: its parts, what it needs, practice and the test. */
export function MilestonePanel({
  milestone: m,
  names,
  isNext,
  onClose,
}: {
  milestone: Milestone;
  names: Record<string, string>;
  isNext: boolean;
  onClose: () => void;
}) {
  const [known, missing] = knownMissing(milestoneShare(m));
  const mastered = m.status === "mastered";
  const waiting = m.waiting_for.map((n) => `«${names[n] ?? n}»`).join(", ");
  return (
    <div className="nt-panel-body">
      <button type="button" className="nt-btn ghost nt-close" onClick={onClose}>
        {t.roadmap.close}
      </button>
      <p className="nt-kicker">
        {t.roadmap.milestone} {m.level} ·{" "}
        {m.needs.length > 0
          ? `${t.roadmap.needs}: ${m.needs.map((n) => names[n] ?? n).join(", ")}`
          : t.roadmap.start}
      </p>
      <h2>{m.name_vi}</h2>
      <p className="nt-sum">
        <span className={`nt-status is-${m.status}`}>
          {statusLabel(m.status, t.roadmap.status)}
        </span>{" "}
        {t.roadmap.known} <b>{known}%</b>, {t.roadmap.missing} {missing}%.
        {isNext && <span className="nt-next"> {t.roadmap.next}</span>}
      </p>
      {m.locked && (
        <p className="nt-locked" role="note">
          <span aria-hidden>🔒</span> <b>{t.roadmap.locked}.</b>{" "}
          {t.roadmap.lockedWhy.replace("{names}", waiting)}
        </p>
      )}
      {mastered && (
        <div className="nt-sena-line">
          <Sena
            pose="heart"
            label={t.senaSays.mastered}
            className="nt-sena-sm"
          />
          <p>{t.run.mastered}</p>
        </div>
      )}
      <ul className="nt-parts" aria-label={t.roadmap.parts}>
        {m.hidden.map((h) => {
          const b = band(h);
          return (
            <li key={h.slug}>
              <div className="nt-part-top">
                <span>{h.name_vi}</span>
                <b>{percent(h.p_known)}%</b>
              </div>
              <div
                className="nt-meter"
                role="img"
                aria-label={`${t.roadmap.known} ${percent(h.p_known)}%`}
              >
                <i style={{ width: `${percent(h.p_known)}%` }} />
              </div>
              <div className="nt-part-foot">
                <span className={`nt-badge is-${b}`}>{t.roadmap.bands[b]}</span>
                {!m.locked && (
                  <Link href={`/on-tap/phan/${h.slug}`}>{t.run.practise}</Link>
                )}
              </div>
            </li>
          );
        })}
      </ul>
      <div className="nt-actions">
        <Link className="nt-btn primary" href={`/on-tap/cot-moc/${m.slug}`}>
          {m.locked ? t.roadmap.testToUnlock : t.run.takeTest}
        </Link>
      </div>
    </div>
  );
}
