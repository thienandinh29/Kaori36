"use client";
import { useEffect, useState } from "react";
import type { Milestone } from "@/lib/english/types";
import {
  NARROW,
  WIDE,
  arcPath,
  knownMissing,
  milestoneShare,
  ringSegments,
  splitName,
  trailLayout,
} from "@/lib/english/trail";
import { vi } from "@/messages/vi";
import { Sena } from "@/components/sena/sena";

const t = vi.english.roadmap;

function useNarrow(): boolean {
  const [narrow, setNarrow] = useState(false);
  useEffect(() => {
    const q = window.matchMedia("(max-width: 760px)");
    const on = () => setNarrow(q.matches);
    on();
    q.addEventListener("change", on);
    return () => q.removeEventListener("change", on);
  }, []);
  return narrow;
}

// Seeded so the contour paper looks the same on every visit.
function contours(width: number, height: number): string[] {
  let seed = 7;
  const rnd = () => (seed = (seed * 9301 + 49297) % 233280) / 233280;
  const out: string[] = [];
  for (let k = -2; k * 56 < height + 120; k++) {
    const y0 = height - 20 - k * 56;
    let d = `M-430 ${y0}`;
    for (let x = -420; x <= width + 420; x += 60)
      d += ` Q${x + 30} ${(y0 + (rnd() - 0.5) * 34).toFixed(1)} ${x + 60} ${(y0 + (rnd() - 0.5) * 20).toFixed(1)}`;
    out.push(d);
  }
  return out;
}

// The paper behind a name, about as wide as its longest line.
const tagW = (lines: string[]) =>
  Math.min(172, Math.max(...lines.map((l) => l.length)) * 9 + 18);

/** The course as a trail: milestones as rings (indigo known, hatched missing), Sena on the next one. */
export function TrailMap({
  milestones,
  selected,
  here,
  onSelect,
}: {
  milestones: Milestone[];
  selected: string | null;
  here: string | null;
  onSelect: (slug: string) => void;
}) {
  const narrow = useNarrow();
  const o = narrow ? NARROW : WIDE;
  const L = trailLayout(milestones, o);
  const at = new Map(L.nodes.map((n) => [n.slug, n]));
  const hereNode = here ? at.get(here) : undefined;
  const ringR = L.r * 0.8;
  const ringW = L.r * 0.22;
  return (
    <svg
      className="nt-trail"
      viewBox={`0 0 ${L.width} ${L.height}`}
      role="group"
      aria-label={t.mapTitle}
    >
      <defs>
        <pattern
          id="nt-hatch"
          width="6"
          height="6"
          patternUnits="userSpaceOnUse"
          patternTransform="rotate(45)"
        >
          <rect width="6" height="6" fill="var(--nt-gap-soft)" />
          <rect width="2" height="6" fill="var(--nt-gap)" />
        </pattern>
      </defs>
      <g className="nt-contours" aria-hidden="true">
        {contours(L.width, L.height).map((d, i) => (
          <path key={i} d={d} strokeWidth={i % 4 === 0 ? 1.6 : 0.8} />
        ))}
      </g>
      <g aria-hidden="true">
        {L.levels.map((l) => (
          <text key={l.level} className="nt-alt" x={8} y={l.y}>
            {l.level}
          </text>
        ))}
      </g>
      <g aria-hidden="true">
        {L.edges.map((e) => (
          <path
            key={`${e.from}>${e.to}`}
            d={e.d}
            className={`nt-edge${selected && (e.to === selected || e.from === selected) ? " is-on" : ""}`}
          />
        ))}
      </g>
      {milestones.map((m) => {
        const n = at.get(m.slug);
        if (!n) return null;
        const [known] = knownMissing(milestoneShare(m));
        const name = splitName(m.name_vi);
        const choose = () => onSelect(m.slug);
        return (
          <g
            key={m.slug}
            className={`nt-node${m.slug === selected ? " is-selected" : ""}`}
            tabIndex={0}
            role="button"
            aria-pressed={m.slug === selected}
            aria-label={`${m.name_vi}, ${m.level}, ${t.known.toLowerCase()} ${known}%`}
            onClick={choose}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                choose();
              }
            }}
          >
            <circle className="nt-disc" cx={n.x} cy={n.y} r={L.r} />
            {ringSegments(m.hidden).map((s) => (
              <g key={s.slug}>
                <path
                  d={arcPath(n.x, n.y, ringR, ...s.track)}
                  stroke="url(#nt-hatch)"
                  strokeWidth={ringW}
                  fill="none"
                />
                {s.fill && (
                  <path
                    d={arcPath(n.x, n.y, ringR, ...s.fill)}
                    className={`nt-fill is-${s.band}`}
                    strokeWidth={ringW}
                    fill="none"
                  />
                )}
              </g>
            ))}
            <text className="nt-pct" x={n.x} y={n.y + 7}>
              {known}%
            </text>
            <text className="nt-lv" x={n.x} y={n.y + 24}>
              {m.level}
            </text>
            <rect
              className="nt-tag"
              x={n.x - tagW(name) / 2}
              y={n.y + L.r + 6}
              width={tagW(name)}
              height={name.length === 2 ? 44 : 24}
              rx={8}
            />
            {name.map((line, i) => (
              <text
                key={i}
                className="nt-name"
                x={n.x}
                y={n.y + L.r + 24 + i * 20}
              >
                {line}
              </text>
            ))}
          </g>
        );
      })}
      {hereNode && (
        <g className="nt-here" aria-hidden="true">
          {narrow ? (
            // phones: Sena stands on top of the milestone, no room for a tag beside it
            <foreignObject
              x={hereNode.x - 32}
              y={hereNode.y - L.r - 76}
              width={64}
              height={80}
            >
              <Sena pose="idle" label={`${t.here}. ${t.senaHere}`} />
            </foreignObject>
          ) : (
            <>
              <foreignObject
                x={hereNode.x - L.r - 92}
                y={hereNode.y - 82}
                width={80}
                height={100}
              >
                <Sena pose="idle" label={t.senaHere} />
              </foreignObject>
              <rect
                x={hereNode.x - L.r - 100}
                y={hereNode.y + 14}
                width={96}
                height={26}
                rx={13}
                className="nt-here-tag"
              />
              <text
                x={hereNode.x - L.r - 52}
                y={hereNode.y + 32}
                className="nt-here-text"
              >
                {t.here}
              </text>
            </>
          )}
        </g>
      )}
    </svg>
  );
}
