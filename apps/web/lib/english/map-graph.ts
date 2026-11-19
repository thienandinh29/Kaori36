// The skill map as one graph (specs/two-layer-map, M4 graph view): IELTS competencies on the right,
// the foundations they need on the left, an edge per link ("cần" solid, "giúp" dashed). Pure.
import dagre from "@dagrejs/dagre";
import type { Competency, Foundation, Maps, Status } from "./maps";

export const GRAPH_NODE = { width: 190, height: 64 };
export const BELOW = 0.8; // the engine's root-cause bar (app/engine/recommend.py ROOT_CAUSE_BELOW)

export type GraphNode = {
  id: string;
  kind: "competency" | "foundation";
  label: string;
  status: Status | "not_live";
  p: number | null;
  evidence: number;
  skill: string | null; // competencies only
  href: string | null;
  available: boolean;
  /** The weakest `requires` foundation (under BELOW) of some competency: where a gap starts. */
  rootCause: boolean;
};
export interface GraphEdge {
  id: string;
  source: string; // the foundation
  target: string; // the competency
  kind: "requires" | "helps";
}

/**
 * The weakest live, measured `requires` foundation under BELOW, as the engine traces a gap; or
 * null. An unmeasured foundation is not a known weakness, so it is never named the root cause.
 */
export function weakest(c: Competency): Foundation | null {
  const candidates = c.links.filter(
    (f) =>
      f.kind === "requires" &&
      f.live &&
      f.status !== "unmeasured" &&
      f.p !== null &&
      f.p < BELOW,
  );
  return candidates.reduce<Foundation | null>(
    (low, f) => (low === null || (f.p ?? 1) < (low.p ?? 1) ? f : low),
    null,
  );
}

export function buildGraph(
  maps: Maps,
  skill: string | null = null,
): { nodes: GraphNode[]; edges: GraphEdge[] } {
  const nodes = new Map<string, GraphNode>();
  const edges: GraphEdge[] = [];
  const roots = new Set<string>();
  for (const s of maps.skills) {
    if (skill !== null && s.skill !== skill) continue;
    for (const c of s.competencies) {
      nodes.set(c.slug, {
        id: c.slug,
        kind: "competency",
        label: c.nameVi,
        status: c.status,
        p: c.p,
        evidence: c.evidence,
        skill: s.skill,
        href: null,
        available: c.available,
        rootCause: false,
      });
      const w = weakest(c);
      if (w) roots.add(w.node);
      for (const f of c.links) {
        if (!nodes.has(f.node))
          nodes.set(f.node, {
            id: f.node,
            kind: "foundation",
            label: f.nameVi,
            status: f.live ? f.status : "not_live",
            p: f.live ? f.p : null,
            evidence: f.evidence,
            skill: null,
            href: f.href,
            available: f.live,
            rootCause: false,
          });
        edges.push({
          id: `${f.node}->${c.slug}`,
          source: f.node,
          target: c.slug,
          kind: f.kind,
        });
      }
    }
  }
  for (const id of roots) {
    const n = nodes.get(id);
    if (n) n.rootCause = true;
  }
  return { nodes: [...nodes.values()], edges };
}

/** Left-to-right layout: foundations first, the competencies they feed after. */
export function layout(
  nodes: GraphNode[],
  edges: GraphEdge[],
): Record<string, { x: number; y: number }> {
  const g = new dagre.graphlib.Graph();
  g.setGraph({
    rankdir: "LR",
    nodesep: 18,
    ranksep: 90,
    marginx: 16,
    marginy: 16,
  });
  g.setDefaultEdgeLabel(() => ({}));
  for (const n of nodes) g.setNode(n.id, { ...GRAPH_NODE });
  for (const e of edges) g.setEdge(e.source, e.target);
  dagre.layout(g);
  const out: Record<string, { x: number; y: number }> = {};
  for (const n of nodes) {
    const p = g.node(n.id);
    out[n.id] = {
      x: p.x - GRAPH_NODE.width / 2,
      y: p.y - GRAPH_NODE.height / 2,
    };
  }
  return out;
}
