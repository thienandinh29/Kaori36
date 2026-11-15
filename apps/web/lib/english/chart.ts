// Geometry for the Task 1 chart (specs/writing/step-2.5.md): pure, so it is unit-tested.
import type { ChartFigure } from "./types";

export const PALETTE = [
  "#1f6f4a",
  "#c2410c",
  "#1d4ed8",
  "#a21caf",
  "#a16207",
  "#0f766e",
];

/** The top of the y axis: a round number at or above the largest value. */
export function niceMax(max: number): number {
  if (!(max > 0)) return 1;
  const exp = Math.floor(Math.log10(max));
  const base = 10 ** exp;
  for (const step of [1, 2, 2.5, 5, 10])
    if (step * base >= max) return step * base;
  return 10 * base;
}

export function yTicks(top: number, count = 5): number[] {
  return Array.from({ length: count + 1 }, (_, i) => (top * i) / count);
}

export function chartMax(chart: ChartFigure): number {
  return niceMax(Math.max(...chart.series.flatMap((s) => s.values)));
}

/** Position of category `i` of `n` along a width, centred in its slot. */
export function slot(i: number, n: number, size: number): number {
  return ((i + 0.5) * size) / n;
}

export interface Slice {
  label: string;
  value: number;
  share: number; // percent, one decimal
  start: number; // radians from 12 o'clock, clockwise
  end: number;
}

export function pieSlices(chart: ChartFigure): Slice[] {
  const values = chart.series[0].values;
  const total = values.reduce((a, b) => a + b, 0);
  let angle = 0;
  return chart.categories.map((label, i) => {
    const share = total ? (100 * values[i]) / total : 0;
    const start = angle;
    angle += total ? (2 * Math.PI * values[i]) / total : 0;
    return {
      label,
      value: values[i],
      share: Math.round(share * 10) / 10,
      start,
      end: angle,
    };
  });
}

/** SVG path of a pie slice centred at (cx, cy). */
export function slicePath(s: Slice, cx: number, cy: number, r: number): string {
  if (s.end - s.start >= 2 * Math.PI - 1e-9)
    return `M ${cx} ${cy - r} A ${r} ${r} 0 1 1 ${cx - 0.001} ${cy - r} Z`;
  const point = (a: number) =>
    `${(cx + r * Math.sin(a)).toFixed(2)} ${(cy - r * Math.cos(a)).toFixed(2)}`;
  const large = s.end - s.start > Math.PI ? 1 : 0;
  return `M ${cx} ${cy} L ${point(s.start)} A ${r} ${r} 0 ${large} 1 ${point(s.end)} Z`;
}

export function formatValue(v: number, unit: string): string {
  const n = Number.isInteger(v) ? String(v) : v.toFixed(1);
  return unit === "%" ? `${n}%` : unit ? `${n} ${unit}` : n;
}
