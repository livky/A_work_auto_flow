import type {
  MaterialGraph,
  MaterialNode,
  MaterialEdge,
} from "./generated/contracts";
export type VisualGroup = { id: string; name: string; members: string[] };

/** Visual aggregates are ephemeral. They never enter exports or the evidence
 * store. Overlapping memberships remain on the source groups; a deterministic
 * first group supplies each material's position to avoid duplicating facts. */
export function aggregateView(
  graph: MaterialGraph,
  groups: VisualGroup[],
  expanded: string[],
) {
  const membership = new Map<string, VisualGroup>();
  for (const group of groups)
    for (const id of group.members)
      if (!membership.has(id)) membership.set(id, group);
  const buckets = new Map<string, MaterialNode[]>();
  const names = new Map(groups.map((g) => [g.id, g.name]));
  for (const node of graph.nodes) {
    const key = membership.get(node.id)?.id || `kind:${node.kind}`;
    if (!buckets.has(key)) buckets.set(key, []);
    buckets.get(key)!.push(node);
    if (!names.has(key)) names.set(key, node.kind);
  }
  const nodes: MaterialNode[] = [];
  const mapped = new Map<string, string>();
  const virtual = new Map<string, { key: string; members: string[] }>();
  for (const [key, members] of buckets) {
    if (expanded.includes(key) || members.length === 1) {
      nodes.push(...members);
      members.forEach((n) => mapped.set(n.id, n.id));
    } else {
      const id = `VIEW-GROUP:${key}`;
      virtual.set(id, { key, members: members.map((n) => n.id) });
      nodes.push({
        ...members[0],
        id,
        title: `${names.get(key)} · ${members.length}`,
        kind: "visual-group",
        risks: [...new Set(members.flatMap((n) => n.risks))],
        path: "",
        fingerprint: "",
        review: {},
      });
      members.forEach((n) => mapped.set(n.id, id));
    }
  }
  const edges: MaterialEdge[] = [];
  const aggregates = new Map<string, MaterialEdge>();
  for (const edge of graph.edges) {
    const source = mapped.get(edge.source)!,
      target = mapped.get(edge.target)!;
    if (source === target) continue;
    if (source === edge.source && target === edge.target) {
      edges.push(edge);
      continue;
    }
    const key = JSON.stringify([source, target, edge.type, edge.candidate]);
    const previous = aggregates.get(key);
    if (previous) previous.count = Number(previous.count) + 1;
    else
      aggregates.set(key, {
        ...edge,
        id: `VIEW-EDGE:${aggregates.size}`,
        source,
        target,
        derived: true,
        origin: "仅展示聚合；展开主题后逐条查看原始依据",
        count: 1,
      });
  }
  edges.push(...aggregates.values());
  return { graph: { ...graph, nodes, edges }, virtual };
}
