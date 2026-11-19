"use client";
import Link from "next/link";
import { useMemo, useState } from "react";
import {
  Background,
  Controls,
  Handle,
  MarkerType,
  Position,
  ReactFlow,
  type Edge,
  type Node,
  type NodeProps,
} from "@xyflow/react";
import type { Maps } from "@/lib/english/maps";
import {
  GRAPH_NODE,
  buildGraph,
  layout,
  type GraphNode,
} from "@/lib/english/map-graph";
import { vi } from "@/messages/vi";

const t = vi.english.maps;
const SKILL_HREF: Record<string, string> = {
  reading: "/doc",
  listening: "/nghe",
  writing: "/viet",
};

type SkillNode = Node<GraphNode & { selected: boolean }, "skill">;

function SkillNodeView({ data }: NodeProps<SkillNode>) {
  const pct = data.p === null ? null : Math.round(data.p * 100);
  return (
    <div
      className={`nt-gnode is-${data.kind} map-${data.status}${data.rootCause ? " is-root" : ""}${data.selected ? " is-selected" : ""}`}
    >
      <Handle type="target" position={Position.Left} />
      <strong title={data.label}>{data.label}</strong>
      <span className="nt-gnode-meta">
        {data.status === "not_live" ? t.notLive : t.status[data.status]}
        {pct !== null && data.status !== "unmeasured" && ` · ${pct}%`}
        {data.rootCause && ` · ${t.root}`}
      </span>
      <Handle type="source" position={Position.Right} />
    </div>
  );
}
const nodeTypes = { skill: SkillNodeView };

/** The skill map as one graph, with a filter per skill and a details panel (M4 graph view). */
export function SkillGraph({ maps }: { maps: Maps }) {
  // One skill at a time reads well even on a phone; "Tất cả" shows the whole map.
  const [skill, setSkill] = useState<string | null>(
    maps.skills[0]?.skill ?? null,
  );
  const [picked, setPicked] = useState<string | null>(null);
  const graph = useMemo(() => buildGraph(maps, skill), [maps, skill]);
  const pos = useMemo(() => layout(graph.nodes, graph.edges), [graph]);
  const nodes = useMemo<SkillNode[]>(
    () =>
      graph.nodes.map((n) => ({
        id: n.id,
        type: "skill",
        position: pos[n.id]!,
        width: GRAPH_NODE.width,
        height: GRAPH_NODE.height,
        data: { ...n, selected: n.id === picked },
        ariaLabel: `${n.label}: ${n.status === "not_live" ? t.notLive : t.status[n.status]}`,
      })),
    [graph, pos, picked],
  );
  const edges = useMemo<Edge[]>(
    () =>
      graph.edges.map((e) => {
        const on =
          picked !== null && (e.source === picked || e.target === picked);
        return {
          id: e.id,
          source: e.source,
          target: e.target,
          type: "smoothstep",
          markerEnd: { type: MarkerType.ArrowClosed, width: 12, height: 12 },
          style: {
            strokeWidth: on ? 2.5 : 1.3,
            strokeDasharray: e.kind === "helps" ? "5 4" : undefined,
            opacity: picked === null || on ? 1 : 0.25,
          },
          ariaLabel: `${t.kinds[e.kind]}: ${e.source} → ${e.target}`,
        };
      }),
    [graph, picked],
  );
  const node = graph.nodes.find((n) => n.id === picked) ?? null;
  const linked = node
    ? graph.edges
        .filter((e) => e.source === node.id || e.target === node.id)
        .map((e) => ({
          kind: e.kind,
          other: graph.nodes.find(
            (n) => n.id === (e.source === node.id ? e.target : e.source),
          )!,
        }))
    : [];
  const practise = node
    ? node.kind === "foundation"
      ? node.href
      : (SKILL_HREF[node.skill ?? ""] ?? null)
    : null;

  return (
    <div data-testid="skill-graph">
      <div className="nt-actions" role="group" aria-label={t.filter}>
        {[null, ...maps.skills.map((s) => s.skill)].map((s) => (
          <button
            key={s ?? "all"}
            type="button"
            aria-pressed={skill === s}
            className={`en-button small ${skill === s ? "" : "ghost"}`}
            onClick={() => {
              setSkill(s);
              setPicked(null);
            }}
          >
            {s === null ? t.all : (t.skills[s] ?? s)}
          </button>
        ))}
      </div>
      <p className="en-muted">{t.legend}</p>
      <div className="nt-skill-graph" role="region" aria-label={t.title}>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={nodeTypes}
          fitView
          fitViewOptions={{ padding: 0.08 }}
          minZoom={0.2}
          maxZoom={1.6}
          nodesDraggable={false}
          nodesConnectable={false}
          onNodeClick={(_, n) => setPicked((p) => (p === n.id ? null : n.id))}
          onPaneClick={() => setPicked(null)}
          onKeyDown={(event) => {
            if (
              (event.key === "Enter" || event.key === " ") &&
              event.target instanceof HTMLElement
            ) {
              const id = event.target
                .closest(".react-flow__node")
                ?.getAttribute("data-id");
              if (id) {
                event.preventDefault();
                setPicked((p) => (p === id ? null : id));
              }
            }
          }}
          ariaLabelConfig={{
            "controls.zoomIn.ariaLabel": vi.graph.zoomIn,
            "controls.zoomOut.ariaLabel": vi.graph.zoomOut,
            "controls.fitView.ariaLabel": vi.graph.fit,
            "controls.ariaLabel": vi.graph.controls,
            "node.a11yDescription.default": vi.graph.instructions,
            "node.a11yDescription.keyboardDisabled": vi.graph.instructions,
            "edge.a11yDescription.default": vi.graph.edgeInstructions,
            "node.a11yDescription.ariaLiveMessage": () => vi.graph.selected,
            "handle.ariaLabel": vi.graph.edge,
          }}
        >
          <Background gap={20} size={1} />
          <Controls showInteractive={false} />
        </ReactFlow>
      </div>
      {node ? (
        <article
          className="nt-graph-panel"
          data-testid="graph-panel"
          role="status"
        >
          <h2>{node.label}</h2>
          <p>
            {node.status === "not_live" ? t.notLive : t.status[node.status]}
            {node.p !== null &&
              node.status !== "unmeasured" &&
              ` · ${Math.round(node.p * 100)}%`}
            {node.evidence > 0 &&
              ` · ${t.basedOn(node.evidence, node.kind === "competency" ? t.essays : t.answers)}`}
          </p>
          {node.rootCause && (
            <p className="en-feedback is-wrong">{t.rootHint}</p>
          )}
          {node.kind === "competency" && !node.available && (
            <p className="en-muted">{t.notYet}</p>
          )}
          <ul className="en-mapfound">
            {linked.map(({ kind, other }) => (
              <li key={other.id}>
                <span className="en-muted">
                  {node.kind === "competency" ? t.kinds[kind] : t.feeds[kind]}
                </span>{" "}
                <button
                  type="button"
                  className="en-link"
                  onClick={() => setPicked(other.id)}
                >
                  {other.label}
                </button>{" "}
                <span className={`en-badge map-${other.status}`}>
                  {other.status === "not_live"
                    ? t.notLive
                    : t.status[other.status]}
                </span>
              </li>
            ))}
          </ul>
          {practise && (
            <Link className="en-button small" href={practise}>
              {t.practise}
            </Link>
          )}
        </article>
      ) : (
        <p className="en-muted">{t.pick}</p>
      )}
    </div>
  );
}
