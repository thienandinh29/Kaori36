import {
  PALETTE,
  chartMax,
  formatValue,
  pieSlices,
  slicePath,
  slot,
  yTicks,
} from "@/lib/english/chart";
import type { ChartFigure } from "@/lib/english/types";

const W = 560;
const H = 300;
const M = { top: 16, right: 16, bottom: 52, left: 52 };
const PW = W - M.left - M.right;
const PH = H - M.top - M.bottom;

function Legend({ names }: { names: string[] }) {
  return (
    <ul className="en-legend">
      {names.map((n, i) => (
        <li key={n}>
          <span style={{ background: PALETTE[i % PALETTE.length] }} /> {n}
        </li>
      ))}
    </ul>
  );
}

function Axes({ chart, top }: { chart: ChartFigure; top: number }) {
  return (
    <>
      {yTicks(top).map((t) => {
        const y = M.top + PH - (t / top) * PH;
        return (
          <g key={t}>
            <line x1={M.left} x2={W - M.right} y1={y} y2={y} stroke="#e5e7eb" />
            <text x={M.left - 6} y={y + 4} textAnchor="end" fontSize="11">
              {t}
            </text>
          </g>
        );
      })}
      {chart.categories.map((c, i) => (
        <text
          key={c}
          x={M.left + slot(i, chart.categories.length, PW)}
          y={H - M.bottom + 16}
          textAnchor="middle"
          fontSize="11"
        >
          {c}
        </text>
      ))}
      {chart.x_label && (
        <text x={M.left + PW / 2} y={H - 8} textAnchor="middle" fontSize="12">
          {chart.x_label}
        </text>
      )}
      {chart.y_label && (
        <text
          transform={`translate(12 ${M.top + PH / 2}) rotate(-90)`}
          textAnchor="middle"
          fontSize="12"
        >
          {chart.y_label}
        </text>
      )}
    </>
  );
}

function Line({ chart }: { chart: ChartFigure }) {
  const top = chartMax(chart);
  const n = chart.categories.length;
  return (
    <svg viewBox={`0 0 ${W} ${H}`} role="presentation">
      <Axes chart={chart} top={top} />
      {chart.series.map((s, k) => {
        const pts = s.values.map(
          (v, i) => `${M.left + slot(i, n, PW)},${M.top + PH - (v / top) * PH}`,
        );
        const color = PALETTE[k % PALETTE.length];
        return (
          <g key={s.name}>
            <polyline
              points={pts.join(" ")}
              fill="none"
              stroke={color}
              strokeWidth="2.5"
            />
            {pts.map((p) => {
              const [x, y] = p.split(",");
              return <circle key={p} cx={x} cy={y} r="3.5" fill={color} />;
            })}
          </g>
        );
      })}
    </svg>
  );
}

function Bars({ chart }: { chart: ChartFigure }) {
  const top = chartMax(chart);
  const n = chart.categories.length;
  const m = chart.series.length;
  const group = PW / n;
  const bar = (group * 0.75) / m;
  return (
    <svg viewBox={`0 0 ${W} ${H}`} role="presentation">
      <Axes chart={chart} top={top} />
      {chart.series.map((s, k) =>
        s.values.map((v, i) => {
          const h = (v / top) * PH;
          return (
            <rect
              key={`${s.name}-${i}`}
              x={M.left + i * group + group * 0.125 + k * bar}
              y={M.top + PH - h}
              width={bar - 2}
              height={h}
              fill={PALETTE[k % PALETTE.length]}
            />
          );
        }),
      )}
    </svg>
  );
}

function Pie({ chart }: { chart: ChartFigure }) {
  const slices = pieSlices(chart);
  return (
    <div className="en-pie">
      <svg viewBox="0 0 220 220" role="presentation">
        {slices.map((s, i) => (
          <path
            key={s.label}
            d={slicePath(s, 110, 110, 100)}
            fill={PALETTE[i % PALETTE.length]}
            stroke="#fff"
            strokeWidth="1.5"
          />
        ))}
      </svg>
      <ul className="en-legend">
        {slices.map((s, i) => (
          <li key={s.label}>
            <span style={{ background: PALETTE[i % PALETTE.length] }} />{" "}
            {s.label}: {formatValue(s.share, "%")}
          </li>
        ))}
      </ul>
    </div>
  );
}

function Table({ chart }: { chart: ChartFigure }) {
  return (
    <table className="en-table">
      <thead>
        <tr>
          <th />
          {chart.categories.map((c) => (
            <th key={c}>{c}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {chart.series.map((s) => (
          <tr key={s.name}>
            <th scope="row">{s.name}</th>
            {s.values.map((v, i) => (
              <td key={i}>{formatValue(v, "")}</td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

/** The chart of a Task 1 prompt, drawn from its data as plain SVG (no library). */
export function ChartFigureView({ chart }: { chart: ChartFigure }) {
  const body =
    chart.chart_type === "line" ? (
      <Line chart={chart} />
    ) : chart.chart_type === "bar" ? (
      <Bars chart={chart} />
    ) : chart.chart_type === "pie" ? (
      <Pie chart={chart} />
    ) : (
      <Table chart={chart} />
    );
  return (
    <figure className="en-figure" data-testid="chart" aria-label={chart.alt_vi}>
      <figcaption>
        <strong>{chart.title}</strong>
        {chart.unit && chart.chart_type !== "pie" && ` (${chart.unit})`}
      </figcaption>
      {body}
      {(chart.chart_type === "line" || chart.chart_type === "bar") && (
        <Legend names={chart.series.map((s) => s.name)} />
      )}
    </figure>
  );
}
