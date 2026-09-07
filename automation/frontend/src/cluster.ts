import Graph from "graphology";
import louvain from "graphology-communities-louvain";
import type { MaterialGraph } from "./generated/contracts";
// 固定种子、稳定输入次序；聚类仅表示当前选择中的连接结构，不修改业务归属。
export function cluster(input: MaterialGraph, semantic: boolean) {
  let seed = 173;
  const rng = () => {
    seed = (1664525 * seed + 1013904223) >>> 0;
    return seed / 4294967296;
  };
  const graph = new Graph({ type: "undirected", multi: false });
  const nodes = [...input.nodes].sort((a, b) => a.id.localeCompare(b.id));
  const byId = new Map(nodes.map((n) => [n.id, n]));
  for (const n of nodes) graph.addNode(n.id);
  for (const e of [...input.edges].sort((a, b) => a.id.localeCompare(b.id))) {
    if (
      ["belongs_to", "contains"].includes(e.type) ||
      e.source === e.target ||
      !graph.hasNode(e.source) ||
      !graph.hasNode(e.target)
    )
      continue;
    if (semantic !== e.candidate) continue;
    if (!graph.hasEdge(e.source, e.target))
      graph.addEdge(e.source, e.target, {
        weight: semantic ? Math.max(0.01, e.score ?? 1) : 1,
      });
  }
  const groups = graph.size
    ? louvain(graph, { rng, resolution: 1, randomWalk: false })
    : Object.fromEntries(nodes.map((n, i) => [n.id, i]));
  const grouped = new Map<number, string[]>();
  for (const n of nodes) {
    const id = Number(groups[n.id]);
    if (!grouped.has(id)) grouped.set(id, []);
    grouped.get(id)!.push(n.id);
  }
  const clusters = [...grouped.entries()].map(([id, members]) => {
    const words = new Map<string, number>();
    members
      .map((id) => byId.get(id)!)
      .forEach((n) =>
        n.keywords.forEach((w) => words.set(w, (words.get(w) || 0) + 1)),
      );
    const title =
      [...words]
        .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
        .slice(0, 3)
        .map((x) => x[0])
        .join(" / ") || `结构分组 ${id + 1}`;
    return { id: String(id), title, members };
  });
  const bridges = input.edges
    .filter(
      (e) =>
        groups[e.source] !== undefined &&
        groups[e.target] !== undefined &&
        groups[e.source] !== groups[e.target] &&
        !["contains", "belongs_to"].includes(e.type),
    )
    .slice(0, 20);
  const gaps = clusters.filter((c) => c.members.length > 1).slice(0, 8);
  // Rank sparsely connected pairs within a bounded eight-community sample.
  // Missing links are an investigation prompt, never a discovered fact.
  const connections = new Map<string, number>();
  const pairKey = (a: string, b: string) => [a, b].sort().join("|");
  for (const edge of input.edges) {
    if (
      ["contains", "belongs_to"].includes(edge.type) ||
      edge.candidate !== semantic
    )
      continue;
    const a = String(groups[edge.source]),
      b = String(groups[edge.target]);
    if (a !== b) {
      const key = pairKey(a, b);
      connections.set(key, (connections.get(key) || 0) + 1);
    }
  }
  const pairs = gaps
    .flatMap((a, i) =>
      gaps.slice(i + 1).map((b) => ({
        a,
        b,
        links: connections.get(pairKey(a.id, b.id)) || 0,
      })),
    )
    .sort(
      (a, b) =>
        a.links - b.links ||
        pairKey(a.a.id, a.b.id).localeCompare(pairKey(b.a.id, b.b.id)),
    )
    .slice(0, 7);
  return {
    clusters,
    bridges,
    questions: pairs.map(({ a, b, links }) => ({
      title: `“${a.title}”与“${b.title}”是否涉及共同问题？（当前跨组连接 ${links}）`,
      refs: [a.members[0], b.members[0]],
      observed_links: links,
    })),
    method: "Louvain; resolution=1; seed=173",
    semantic,
    fingerprint: input.fingerprint,
    generated_at: new Date().toISOString(),
    coverage: {
      nodes: input.nodes.length,
      edges: input.edges.length,
      selection: input.selection,
      omitted_nodes: input.omitted_nodes || 0,
    },
    note: "主题组合仅为待核对问题，连接缺失也可能来自过滤或未登记。",
  };
}
export type ClusterResult = ReturnType<typeof cluster>;
