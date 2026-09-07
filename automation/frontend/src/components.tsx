import { useEffect, useMemo, useRef, useState } from "react";
import cytoscape, { type Core } from "cytoscape";
import type { MaterialGraph } from "./generated/contracts";
import type { Mode } from "./graph-model";
import { aggregateView, type VisualGroup } from "./group-view";
import { relationNames } from "./api";
export function Modal({
  title,
  children,
  close,
}: {
  title: string;
  children: React.ReactNode;
  close: () => void;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    ref.current?.showModal();
  }, []);
  return (
    <dialog ref={ref} onCancel={close}>
      <div className="row spread">
        <h2>{title}</h2>
        <button onClick={close}>关闭</button>
      </div>
      {children}
    </dialog>
  );
}
export function GraphPanel({
  graph,
  mode,
  center,
  positions,
  onSelect,
  onPositions,
  groups = [],
}: {
  graph: MaterialGraph;
  mode: Mode;
  center: string;
  positions: Record<string, { x: number; y: number }>;
  onSelect: (id: string, edge: boolean) => void;
  onPositions: (p: Record<string, { x: number; y: number }>) => void;
  groups?: VisualGroup[];
}) {
  const [expanded, setExpanded] = useState<string[]>([]);
  const grouped = useMemo(
    () => aggregateView(graph, groups, expanded),
    [graph, groups, expanded],
  );
  const display = mode === "groups" ? grouped.graph : graph;
  const ref = useRef<HTMLDivElement>(null);
  const cy = useRef<Core | null>(null);
  const selectRef = useRef(onSelect);
  selectRef.current = onSelect;
  const saveRef = useRef(onPositions);
  saveRef.current = onPositions;
  useEffect(() => {
    if (!ref.current) return;
    const kinds = [...new Set(display.nodes.map((n) => n.kind))].sort();
    const counts: Record<string, number> = {};
    const elements: cytoscape.ElementDefinition[] = display.nodes.map((n) => {
      const index = counts[n.kind] || 0;
      counts[n.kind] = index + 1;
      const angle =
        ((kinds.indexOf(n.kind) + (index % 8) / 10) * 2 * Math.PI) /
        Math.max(kinds.length, 1);
      const radius = 220 + Math.floor(index / 8) * 95;
      return {
        data: {
          id: n.id,
          label: n.title.length > 22 ? n.title.slice(0, 22) + "…" : n.title,
          kind: n.kind,
          risk: n.risks.length > 0,
        },
        position:
          positions[n.id] ||
          (n.id === center
            ? { x: 0, y: 0 }
            : { x: Math.cos(angle) * radius, y: Math.sin(angle) * radius }),
      };
    });
    elements.push(
      ...display.edges.map((e) => ({
        data: {
          id: e.id,
          source: e.source,
          target: e.target,
          candidate: e.candidate,
          type: e.type,
          label: `${relationNames[e.type] || e.type}${e.count ? ` × ${e.count}` : ""}`,
        },
      })),
    );
    const instance = cytoscape({
      container: ref.current,
      elements,
      minZoom: 0.15,
      maxZoom: 3,
      style: [
        {
          selector: "node",
          style: {
            label: "data(label)",
            "font-size": 11,
            color: "#24444a",
            "background-color": "#43958b",
            width: 24,
            height: 24,
            "text-valign": "bottom",
            "text-margin-y": 7,
            "text-background-color": "#f7faf9",
            "text-background-opacity": 0.8,
            "text-background-padding": "3px",
          },
        },
        {
          selector: 'node[kind="claim"]',
          style: { shape: "diamond", "background-color": "#b88733" },
        },
        {
          selector: 'node[kind="report"]',
          style: { shape: "rectangle", "background-color": "#637faa" },
        },
        {
          selector: "node[?risk]",
          style: { "border-width": 3, "border-color": "#b54937" },
        },
        {
          selector: "edge",
          style: {
            width: 1.2,
            "line-color": "#9aafb0",
            "target-arrow-color": "#9aafb0",
            "target-arrow-shape": "triangle",
            "curve-style": "bezier",
            opacity: 0.65,
          },
        },
        {
          selector: "edge[?candidate]",
          style: {
            "line-style": "dashed",
            "line-color": "#a28aba",
            "target-arrow-shape": "none",
          },
        },
        {
          selector: 'edge[type="contradicts"]',
          style: { "line-color": "#b54937", "target-arrow-color": "#b54937" },
        },
        {
          selector: 'node[kind="visual-group"]',
          style: {
            shape: "round-rectangle",
            width: 70,
            height: 42,
            "background-color": "#5978a0",
          },
        },
        {
          selector: "edge:selected",
          style: {
            label: "data(label)",
            "font-size": 11,
            "text-background-color": "#ffffff",
            "text-background-opacity": 1,
            width: 3,
          },
        },
        {
          selector: "node:selected",
          style: {
            "border-width": 3,
            "border-color": "#1f454f",
            "line-color": "#1f454f",
            width: 30,
            height: 30,
          },
        },
      ],
      layout: {
        name: mode === "evidence" ? "breadthfirst" : "preset",
        directed: true,
        padding: 50,
      } as cytoscape.LayoutOptions,
    });
    cy.current = instance;
    instance.on("tap", "node", (event) => {
      const group = mode === "groups" && grouped.virtual.get(event.target.id());
      if (group) setExpanded((old) => [...old, group.key]);
      else selectRef.current(event.target.id(), false);
    });
    instance.on("tap", "edge", (event) => {
      if (event.target.id().startsWith("VIEW-EDGE:")) {
        const keys = [event.target.source().id(), event.target.target().id()]
          .map((id) => grouped.virtual.get(id)?.key)
          .filter((key): key is string => !!key);
        setExpanded((old) => [...new Set([...old, ...keys])]);
      } else selectRef.current(event.target.id(), true);
    });
    instance.on("dragfree", "node", () => {
      const all: Record<string, { x: number; y: number }> = {};
      instance.nodes().forEach((n) => {
        all[n.id()] = n.position();
      });
      saveRef.current(all);
    });
    const resize = new ResizeObserver(() => instance.resize());
    resize.observe(ref.current);
    return () => {
      resize.disconnect();
      instance.destroy();
    };
    // 位置只在数据/布局变化时应用；拖动不会重建画布。
  }, [display, mode, center, grouped]);
  return (
    <section className="canvas-wrap">
      <div className="canvas-tools">
        {mode === "groups" && (
          <button onClick={() => setExpanded([])}>折叠所有分组</button>
        )}
        <button onClick={() => cy.current?.fit(undefined, 45)}>适应画面</button>
        <button
          onClick={() => cy.current?.zoom((cy.current?.zoom() || 1) * 1.2)}
        >
          ＋
        </button>
        <button
          onClick={() => cy.current?.zoom((cy.current?.zoom() || 1) / 1.2)}
        >
          －
        </button>
      </div>
      {mode === "groups" && (
        <details className="group-controls">
          <summary>展开分组（{grouped.virtual.size}）</summary>
          {[...grouped.virtual].map(([id, group]) => (
            <button
              key={id}
              onClick={() => setExpanded((old) => [...old, group.key])}
            >
              {display.nodes.find((n) => n.id === id)?.title}
            </button>
          ))}
          <p>
            重叠成员按首个分组定位；全部归属保留在材料与主题列表。导出包含当前范围的原始节点和关系。
          </p>
        </details>
      )}
      <div
        className="graph-canvas"
        ref={ref}
        aria-label="材料关系图"
        role="img"
      />
      <p className="legend">
        ● 材料　◆ 结论　■ 报告　红框：风险　虚线：候选　箭头：起点引用或关联终点
      </p>
    </section>
  );
}
