import type {
  MaterialGraph,
  MaterialNode,
  MaterialEdge,
} from "./generated/contracts";
export type Node = MaterialNode;
export type Edge = MaterialEdge;
export type Mode = "radial" | "groups" | "evidence";
/** Filter before traversal/clustering so a hidden raw record cannot bridge two
 * visible materials. Native navigation is an explicit compatibility choice. */
export function layerGraph(graph: MaterialGraph, levels: string[]) {
  const nodes = graph.nodes.filter((node) =>
    levels.includes(node.level || "native"),
  );
  const ids = new Set(nodes.map((node) => node.id));
  return {
    ...graph,
    nodes,
    edges: graph.edges.filter(
      (edge) => ids.has(edge.source) && ids.has(edge.target),
    ),
  };
}
export const evidenceTypes = new Set([
  "supports",
  "input",
  "contradicts",
  "background",
  "depends_on",
  "produces",
  "contains",
]);
export function selectGraph(
  graph: MaterialGraph,
  center: string,
  hops: number,
  excluded: string[],
  mode: Mode,
  types: string[],
  offset = 0,
  checked: string[] = [],
) {
  const blocked = new Set(excluded);
  const nodes = new Map(
    graph.nodes.filter((n) => !blocked.has(n.id)).map((n) => [n.id, n]),
  );
  const edges = graph.edges.filter(
    (e) =>
      nodes.has(e.source) &&
      nodes.has(e.target) &&
      (!types.length || types.includes(e.type)) &&
      (mode !== "evidence" || evidenceTypes.has(e.type)),
  );
  let ids = new Set(nodes.keys());
  // Checkbox selection supplies multiple roots. An empty/removed root set must
  // not accidentally expand back to all materials when a selection was made.
  const roots = checked.length
    ? checked.filter((id) => nodes.has(id))
    : center && nodes.has(center)
      ? [center]
      : [];
  if (checked.length || roots.length) {
    const neighbors = new Map<string, Set<string>>();
    for (const e of edges) {
      if (!neighbors.has(e.source)) neighbors.set(e.source, new Set());
      if (!neighbors.has(e.target)) neighbors.set(e.target, new Set());
      neighbors.get(e.source)!.add(e.target);
      neighbors.get(e.target)!.add(e.source);
    }
    ids = new Set(roots);
    let frontier = roots;
    for (let d = 0; d < hops; d++) {
      const next = new Set<string>();
      for (const id of frontier)
        for (const n of neighbors.get(id) || []) if (!ids.has(n)) next.add(n);
      next.forEach((n) => ids.add(n));
      frontier = [...next];
    }
  }
  const order = [...ids].sort(
    (a, b) =>
      Number(roots.includes(b)) - Number(roots.includes(a)) ||
      a.localeCompare(b),
  );
  const visible = new Set(order.slice(offset, offset + 300));
  const shownEdges = edges.filter(
    (e) => visible.has(e.source) && visible.has(e.target),
  );
  const { file_stats: _stats, boundary: _boundary, ...safeGraph } = graph;
  return {
    ...safeGraph,
    nodes: [...visible].map((id) => nodes.get(id)!),
    edges: shownEdges.slice(0, 1000),
    omitted_nodes: ids.size - visible.size,
    omitted_edges: Math.max(0, shownEdges.length - 1000),
    selection: { center, checked, hops, excluded, mode, types, offset },
  };
}
export function topicGroups(graph: MaterialGraph) {
  const ids = new Set(
    graph.nodes
      .filter(
        (n) =>
          ["algorithm", "research", "project"].includes(n.kind) &&
          !n.id.startsWith("FILE-"),
      )
      .map((n) => n.id),
  );
  return [...ids].map((id) => ({
    id,
    name: graph.nodes.find((n) => n.id === id)!.title,
    members: [
      ...new Set(
        graph.edges
          .filter((e) => e.type === "belongs_to" && e.target === id)
          .map((e) => e.source),
      ),
    ],
  }));
}
export function summary(graph: MaterialGraph, question: string) {
  return [
    "# 材料关系摘要",
    `问题：${question}`,
    `生成时间：${graph.generated_at}`,
    `投影指纹：${graph.fingerprint}`,
    "\n## 材料",
    ...graph.nodes.map(
      (n) =>
        `- ${n.id} | ${n.title} | ${n.path} | 定位 ${n.locator || "未提供"} | ${n.fingerprint} | 复核 ${n.review.status || "not-reviewed"} | 执行 ${n.execution_status || "未提供"} | 范围 ${n.scope || "未提供"} | 风险 ${n.risks.join("、") || "未报告"}`,
    ),
    "\n## 关系",
    ...graph.edges.map(
      (e) =>
        `- ${e.source} → ${e.target} [${e.type}] ${e.candidate ? "候选" : e.derived ? "派生" : "已记录"}；${e.origin}；${e.locator}；${JSON.stringify({ score: e.score, model_id: e.model_id, seed_locator: e.seed_locator, match_locator: e.match_locator, version_matches: e.version_matches })}`,
    ),
    "\n## 范围与缺口",
    JSON.stringify({
      selection: graph.selection,
      coverage: graph.coverage,
      errors: graph.errors,
      omitted_nodes: graph.omitted_nodes,
      omitted_edges: graph.omitted_edges,
    }),
    "请核对版本、适用范围和反证，保留预算与排除项，再读取必要原文。",
  ].join("\n");
}
