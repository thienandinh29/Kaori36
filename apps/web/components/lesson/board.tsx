import type { BoardItem } from "@/lib/lesson/player";
import { timeX } from "@/lib/lesson/player";
import { vi } from "@/messages/vi";

const t = vi.english.lesson;
const W = 320;
const PAD = 16;
const x = (at: number) => PAD + timeX(at) * (W - 2 * PAD);

function Timeline({
  item,
}: {
  item: Extract<BoardItem, { kind: "timeline" }>;
}) {
  const rows = item.spans.length + (item.points.length ? 1 : 0);
  const h = 44 + rows * 26;
  return (
    <svg
      className="nt-board-timeline"
      viewBox={`0 0 ${W} ${h}`}
      role="img"
      aria-label={[
        ...item.spans.map((s) => `${s.label}${s.open ? " →" : ""}`),
        ...item.points.map((p) => p.label),
      ].join(", ")}
    >
      <line x1={PAD} x2={W - PAD} y1={h - 24} y2={h - 24} className="axis" />
      <line x1={x(0)} x2={x(0)} y1={8} y2={h - 18} className="now" />
      <text x={x(0)} y={h - 6} textAnchor="middle" className="now-label">
        {t.now}
      </text>
      <text x={PAD} y={h - 6} className="end-label">
        {t.past}
      </text>
      <text x={W - PAD} y={h - 6} textAnchor="end" className="end-label">
        {t.future}
      </text>
      {item.spans.map((s, i) => {
        const y = 14 + i * 26;
        return (
          <g key={`s${i}`}>
            <rect
              x={x(s.start)}
              y={y}
              width={Math.max(4, x(s.end) - x(s.start))}
              height={12}
              rx={6}
              className={s.open ? "span open" : "span"}
            />
            {s.open && (
              <path
                d={`M ${x(s.end)} ${y - 2} l 10 8 l -10 8 z`}
                className="span open"
              />
            )}
            <text x={x(s.start)} y={y - 2} className="span-label">
              {s.label}
            </text>
          </g>
        );
      })}
      {item.points.map((p, i) => (
        <g key={`p${i}`}>
          <circle cx={x(p.at)} cy={h - 24} r={5} className="point" />
          <text
            x={x(p.at)}
            y={h - 32}
            textAnchor="middle"
            className="span-label"
          >
            {p.label}
          </text>
        </g>
      ))}
    </svg>
  );
}

/** The lesson's board: form tables, timelines and short lines, drawn from data (never free drawing). */
export function Board({ items }: { items: BoardItem[] }) {
  if (!items.length) return null;
  return (
    <section className="nt-board" aria-label={t.board}>
      {items.map((item, i) =>
        item.kind === "table" ? (
          <table key={i} className="nt-board-table" lang="en">
            <tbody>
              {item.rows.map((row, r) => (
                <tr key={r}>
                  {row.map((cell, c) => (
                    <td key={c}>{cell}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        ) : item.kind === "timeline" ? (
          <Timeline key={i} item={item} />
        ) : (
          <p key={i} className="nt-board-text" lang="en">
            {item.text}
          </p>
        ),
      )}
    </section>
  );
}
