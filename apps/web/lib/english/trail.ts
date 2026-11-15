// Pure layout and numbers for the roadmap's trail map and skyline (specs/ui-v2).
// No DOM here: everything is tested in trail.test.ts.
import type { HiddenNode, Level, Milestone } from "./types";

/** Below the engine's "known" (0.9, the API's `known` flag) but at least this: growing. */
export const GROWING_FROM = 0.5;
/** The engine's ASSUMED_KNOWN; drawn as the line on the skyline. */
export const KNOWN_LINE = 0.9;

export type Band = "strong" | "growing" | "gap";

export function band(h: Pick<HiddenNode, "p_known" | "known">): Band {
  if (h.known) return "strong";
  return h.p_known >= GROWING_FROM ? "growing" : "gap";
}

const clamp01 = (p: number) => Math.max(0, Math.min(1, p));

/** A milestone's share known: the mean of its hidden nodes (0 when it has none). */
export function milestoneShare(m: Pick<Milestone, "hidden">): number {
  if (m.hidden.length === 0) return 0;
  return m.hidden.reduce((s, h) => s + clamp01(h.p_known), 0) / m.hidden.length;
}

export type Totals = Record<Band, number> & { all: number };

export function totals(milestones: Pick<Milestone, "hidden">[]): Totals {
  const t: Totals = { strong: 0, growing: 0, gap: 0, all: 0 };
  milestones.forEach((m) =>
    m.hidden.forEach((h) => {
      t[band(h)] += 1;
      t.all += 1;
    }),
  );
  return t;
}

/** Whole percentages that add up: known + missing = 100. */
export function knownMissing(share: number): [number, number] {
  const known = Math.round(clamp01(share) * 100);
  return [known, 100 - known];
}

/** Depth by prerequisites: 0 without `needs` (or needs outside the course), else 1 + the deepest need. */
export function depths(
  milestones: Pick<Milestone, "slug" | "needs">[],
): Map<string, number> {
  const bySlug = new Map(milestones.map((m) => [m.slug, m]));
  const memo = new Map<string, number>();
  const visit = (slug: string, seen: Set<string>): number => {
    const hit = memo.get(slug);
    if (hit !== undefined) return hit;
    const m = bySlug.get(slug);
    if (!m || seen.has(slug)) return -1; // unknown slug or a cycle: treat as a root
    seen.add(slug);
    const d =
      1 +
      Math.max(-1, ...m.needs.map((n) => visit(n, seen)).filter((x) => x >= 0));
    seen.delete(slug);
    memo.set(slug, d);
    return d;
  };
  milestones.forEach((m) => visit(m.slug, new Set()));
  return memo;
}

export interface TrailNode {
  slug: string;
  x: number;
  y: number;
}
export interface TrailEdge {
  from: string;
  to: string;
  d: string;
}
export interface TrailLevel {
  level: Level;
  y: number;
}
export interface TrailLayout {
  width: number;
  height: number;
  r: number;
  nodes: TrailNode[];
  edges: TrailEdge[];
  levels: TrailLevel[];
}

export interface TrailOptions {
  width: number;
  /** Most milestones on one line; a deeper row with more is split into lines. */
  perLine: number;
  lineGap: number;
  r: number;
  /** Room under a node for its two-line name. */
  label: number;
  /** Left gutter for the level labels. */
  gutter: number;
  /**
   * When a row has exactly one milestone more than `perLine`, it goes between the others, raised by this
   * much, instead of on a line of its own (0: never). Keeps a row's milestones side by side on phones.
   */
  stagger: number;
}

export const WIDE: TrailOptions = {
  width: 700,
  perLine: 3,
  lineGap: 175,
  r: 50,
  label: 48,
  gutter: 90,
  stagger: 0,
};
export const NARROW: TrailOptions = {
  width: 400,
  perLine: 2,
  lineGap: 190,
  r: 44,
  label: 48,
  gutter: 0,
  stagger: 130,
};

/**
 * The trail: the first milestones at the bottom, the deepest at the top. Milestones in a row are ordered by
 * the mean x of what they need, so edges cross less; a row wider than `perLine` becomes several lines.
 */
export function trailLayout(
  milestones: Pick<Milestone, "slug" | "needs" | "level">[],
  o: TrailOptions,
): TrailLayout {
  const depth = depths(milestones);
  const maxDepth = Math.max(0, ...depth.values());
  const x = new Map<string, number>();
  // `raised`: a staggered milestone above the gap between this line's two middle ones
  const lines: { slugs: string[]; raised: string | null }[] = [];
  for (let d = 0; d <= maxDepth; d++) {
    const row = milestones.filter((m) => depth.get(m.slug) === d);
    const key = (m: (typeof row)[number]) => {
      const xs = m.needs
        .map((n) => x.get(n))
        .filter((v): v is number => v !== undefined);
      return xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : Number.NaN;
    };
    // keep the API's order for roots; order the rest by their needs' position
    const ordered =
      d === 0 ? row : [...row].sort((a, b) => (key(a) || 0) - (key(b) || 0));
    if (o.stagger > 0 && ordered.length === o.perLine + 1) {
      const span = o.width - o.gutter;
      const mid = Math.floor(ordered.length / 2);
      const base = ordered.filter((_, j) => j !== mid).map((m) => m.slug);
      base.forEach((s, j) =>
        x.set(s, o.gutter + ((j + 0.5) * span) / base.length),
      );
      const a = x.get(base[mid - 1]) ?? 0;
      const b = x.get(base[mid]) ?? o.width;
      x.set(ordered[mid].slug, (a + b) / 2);
      lines.push({ slugs: base, raised: ordered[mid].slug });
      continue;
    }
    for (let i = 0; i < ordered.length; i += o.perLine) {
      const slugs = ordered.slice(i, i + o.perLine).map((m) => m.slug);
      const span = o.width - o.gutter;
      if (slugs.length === 1 && d > 0) {
        // a milestone alone on its line sits above what it needs, so the trail bends instead of
        // stacking every lone milestone in the centre (where edges would run through nodes)
        const m = ordered[i];
        const k = key(m);
        const lo = o.gutter + o.r + 10;
        const hi = o.width - o.r - 10;
        x.set(
          slugs[0],
          Number.isNaN(k) ? o.gutter + span / 2 : Math.min(hi, Math.max(lo, k)),
        );
      } else {
        slugs.forEach((s, j) =>
          x.set(s, o.gutter + ((j + 0.5) * span) / slugs.length),
        );
      }
      lines.push({ slugs, raised: null });
    }
  }
  const top = o.r + 20;
  const bottom = o.r + o.label + 24;
  const extra = lines.filter((l) => l.raised).length * o.stagger;
  const height = top + (lines.length - 1) * o.lineGap + extra + bottom;
  const y = new Map<string, number>();
  let ly = height - bottom;
  lines.forEach((line) => {
    // a small zigzag so a straight column of nodes reads as a path
    line.slugs.forEach((s, j) => y.set(s, ly + (j % 2 ? 14 : 0)));
    if (line.raised) {
      ly -= o.stagger;
      y.set(line.raised, ly);
    }
    ly -= o.lineGap;
  });
  const nodes = milestones.map((m) => ({
    slug: m.slug,
    x: x.get(m.slug) ?? o.width / 2,
    y: y.get(m.slug) ?? height / 2,
  }));
  const pos = new Map(nodes.map((n) => [n.slug, n]));
  const edges: TrailEdge[] = [];
  milestones.forEach((m) =>
    m.needs.forEach((need) => {
      const a = pos.get(need);
      const b = pos.get(m.slug);
      if (!a || !b) return;
      const y1 = a.y - o.r - 2;
      const y2 = b.y + o.r + o.label;
      const mid = (y1 + y2) / 2;
      edges.push({
        from: need,
        to: m.slug,
        d: `M${r1(a.x)} ${r1(y1)} C${r1(a.x)} ${r1(mid)} ${r1(b.x)} ${r1(mid)} ${r1(b.x)} ${r1(y2)}`,
      });
    }),
  );
  // a level label where the level changes, at the lowest line of that level
  const levels: TrailLevel[] = [];
  let last: Level | null = null;
  lines.forEach((line) => {
    const lv = milestones.find((m) => m.slug === line.slugs[0])?.level;
    if (lv && lv !== last) {
      levels.push({ level: lv, y: (y.get(line.slugs[0]) ?? 0) + o.r });
      last = lv;
    }
  });
  return { width: o.width, height: r1(height), r: o.r, nodes, edges, levels };
}

const r1 = (v: number) => Math.round(v * 10) / 10;

/** An SVG arc on a circle, angles in radians clockwise from 12 o'clock. */
export function arcPath(
  cx: number,
  cy: number,
  r: number,
  a0: number,
  a1: number,
): string {
  const p = (a: number) => [cx + r * Math.sin(a), cy - r * Math.cos(a)];
  const [x0, y0] = p(a0);
  const [x1, y1] = p(a1);
  const large = a1 - a0 > Math.PI ? 1 : 0;
  return `M${r1(x0)} ${r1(y0)} A${r} ${r} 0 ${large} 1 ${r1(x1)} ${r1(y1)}`;
}

export interface RingSegment {
  slug: string;
  /** The whole segment (drawn hatched: missing). */
  track: [number, number];
  /** The known part, from the segment's start (null when nothing is known). */
  fill: [number, number] | null;
  band: Band;
}

/** One ring segment per hidden node; the known part is `p_known` of the segment. */
export function ringSegments(hidden: HiddenNode[], gap = 0.12): RingSegment[] {
  const k = hidden.length;
  if (k === 0) return [];
  const g = k > 1 ? gap : 0;
  const seg = (2 * Math.PI - g * k) / k;
  return hidden.map((h, i) => {
    const a0 = i * (seg + g) + g / 2;
    const a1 = a0 + seg;
    const p = clamp01(h.p_known);
    return {
      slug: h.slug,
      track: [a0, a1],
      fill: p > 0.005 ? [a0, a0 + seg * Math.min(p, 0.999)] : null,
      band: band(h),
    };
  });
}

/** A name on at most two lines, split at the space nearest the middle. */
export function splitName(name: string, max = 16): [string] | [string, string] {
  if (name.length <= max) return [name];
  const mid = name.length / 2;
  let best = -1;
  for (let i = 0; i < name.length; i++)
    if (
      name[i] === " " &&
      (best < 0 || Math.abs(i - mid) < Math.abs(best - mid))
    )
      best = i;
  return best < 0 ? [name] : [name.slice(0, best), name.slice(best + 1)];
}
