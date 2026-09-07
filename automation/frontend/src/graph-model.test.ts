import { describe, it, expect } from "vitest";
import { selectGraph, summary } from "./graph-model";
import { cluster } from "./cluster";
import { aggregateView } from "./group-view";
import type { MaterialGraph } from "./generated/contracts";
// 夹具按测试调用现场创建，不发布任何材料数据实例。
export function fixture(count = 6): MaterialGraph {
  const nodes = Array.from({ length: count }, (_, i) => ({
    id: `N${i}`,
    title: `材料${i}`,
    kind: "material",
    path: `test/${i}.md`,
    fingerprint: "abc",
    keywords: ["温度"],
    review: {},
    risks: [],
  }));
  const edges = nodes.slice(1).map((n, i) => ({
    id: `E${i}`,
    source: nodes[i].id,
    target: n.id,
    type: "references",
    origin: `test/${i}.md`,
    locator: "line 1",
    candidate: false,
    derived: false,
    original_source: nodes[i].id,
    original_target: n.id,
    display_source: nodes[i].id,
    display_target: n.id,
  }));
  return {
    schema_version: 1,
    fingerprint: "snapshot",
    generated_at: "synthetic",
    nodes,
    edges,
    errors: [],
    coverage: { synthetic: true },
  };
}
describe("关系选择与候选", () => {
  it("勾选单个或多个材料只展示其关联，清空后恢复全图", () => {
    const graph = fixture(8);
    const single = selectGraph(graph, "", 1, [], "radial", [], 0, ["N0"]);
    expect(single.nodes.map((n) => n.id).sort()).toEqual(["N0", "N1"]);
    const multiple = selectGraph(graph, "", 1, [], "radial", [], 0, [
      "N0",
      "N6",
    ]);
    expect(multiple.nodes.map((n) => n.id).sort()).toEqual([
      "N0",
      "N1",
      "N5",
      "N6",
      "N7",
    ]);
    expect(multiple.selection.checked).toEqual(["N0", "N6"]);
    expect(summary(single, "")).not.toContain("N6 |");
    expect(selectGraph(graph, "", 1, [], "radial", []).nodes).toHaveLength(8);
  });
  it("勾选根节点遵守跳数、排除和关系类型，不回退为全部材料", () => {
    const graph = fixture();
    expect(
      selectGraph(graph, "", 2, [], "radial", [], 0, ["N0"]).nodes,
    ).toHaveLength(3);
    expect(
      selectGraph(graph, "", 2, ["N1"], "radial", [], 0, ["N0"]).nodes.map(
        (n) => n.id,
      ),
    ).toEqual(["N0"]);
    expect(
      selectGraph(graph, "", 2, ["N0"], "radial", [], 0, ["N0"]).nodes,
    ).toEqual([]);
    expect(
      selectGraph(graph, "", 2, [], "evidence", [], 0, ["N0"]).nodes.map(
        (n) => n.id,
      ),
    ).toEqual(["N0"]);
  });
  it("折叠和展开保留底层事实，多重归属不会复制原节点", () => {
    const graph = fixture();
    const before = JSON.stringify(graph);
    const groups = [
      { id: "A", name: "主题甲", members: ["N0", "N1", "N2"] },
      { id: "B", name: "主题乙", members: ["N2", "N3", "N4"] },
    ];
    const folded = aggregateView(graph, groups, []);
    expect(folded.graph.nodes.length).toBeLessThan(graph.nodes.length);
    expect(folded.virtual.get("VIEW-GROUP:A")?.members).toContain("N2");
    const expanded = aggregateView(graph, groups, ["A", "B"]);
    expect(new Set(expanded.graph.nodes.map((n) => n.id)).size).toBe(
      graph.nodes.length,
    );
    expect(expanded.graph.edges).toEqual(graph.edges);
    expect(JSON.stringify(graph)).toBe(before);
    expect(summary(graph, "")).not.toContain("VIEW-GROUP:");
  });
  it("排除节点不会作为隐藏中介扩展，摘要只导出可见选择", () => {
    const selected = selectGraph(fixture(), "N0", 2, ["N1"], "radial", []);
    expect(selected.nodes.map((n) => n.id)).toEqual(["N0"]);
    expect(summary(selected, "检查")).not.toContain("N0 → N1");
  });
  it("反证保留在证据链，相似候选不作为证据链", () => {
    const graph = fixture();
    graph.edges[0].type = "contradicts";
    graph.edges[1].type = "similar";
    graph.edges[1].candidate = true;
    const selected = selectGraph(graph, "", 1, [], "evidence", []);
    expect(selected.edges.map((e) => e.type)).toEqual(["contradicts"]);
  });
  it("固定输入聚类可重复；主题归属不制造证据关系", () => {
    const graph = fixture();
    graph.edges[2].type = "belongs_to";
    expect(cluster(graph, false).clusters).toEqual(
      cluster(graph, false).clusters,
    );
    expect(graph.edges[2].type).toBe("belongs_to");
  });
  it("一万材料十万稀疏关系保持有界可见图", () => {
    const graph = fixture(10_000);
    const template = graph.edges[0];
    graph.edges = Array.from({ length: 100_000 }, (_, i) => ({
      ...template,
      id: `E${i}`,
      source: `N${i % 10_000}`,
      target: `N${(i + 1 + Math.floor(i / 10_000)) % 10_000}`,
    }));
    const start = performance.now();
    const selected = selectGraph(graph, "N0", 2, [], "radial", []);
    expect(selected.nodes.length).toBeLessThanOrEqual(300);
    expect(selected.edges.length).toBeLessThanOrEqual(1000);
    expect(performance.now() - start).toBeLessThan(3000);
  });
});
