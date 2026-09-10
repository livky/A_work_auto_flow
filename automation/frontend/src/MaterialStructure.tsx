import { useEffect, useRef, useState } from "react";
import type {
  Scope,
  TreeNode,
  TreePage,
  Result,
} from "./generated/material-query";
import {
  FixedReferences,
  ResultStatus,
  type MaterialRequest,
} from "./MaterialPacket";

const nodeKinds: Record<string, string> = {
  owner: "归属对象",
  layer: "层级",
  storage: "存储位置",
  source: "原始材料",
  detail: "技术内容",
  event: "过程记录",
  experience: "复用经验",
  map: "知识地图",
  document: "研究文稿",
  document_section: "章节",
};
const storageRoles = {
  canonical: "规范存储",
  source_reference: "来源引用",
  projection: "派生投影",
  temporary: "临时结果",
};

export function MaterialStructure({
  request,
  scope,
  onChoose,
}: {
  request: MaterialRequest;
  scope: Scope;
  onChoose: (node: TreeNode | null, ownerId?: string) => void;
}) {
  const [view, setView] = useState<"logical" | "storage">("logical");
  const [pages, setPages] = useState<Record<string, TreePage>>({});
  const [expanded, setExpanded] = useState<string[]>([]);
  const [busy, setBusy] = useState<string[]>([]);
  const [result, setResult] = useState<Result<TreePage> | null>(null);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState<TreeNode | null>(null);
  const generation = useRef(0);
  // Navigation lists only server-authorized owners. Its root must remain usable
  // while the query itself has an explicit empty or narrower owner selection.
  const scopeKey = JSON.stringify({
    ...scope,
    owner_ids: null,
    levels: null,
    include_refs: [],
    source_ids: null,
  });
  async function load(
    parent: TreeNode | null,
    cursor: string | null = null,
    token = generation.current,
  ) {
    const key = parent?.node_id || "$root";
    setBusy((values) => [...values, key]);
    try {
      const response = await request<TreePage>("materials/structure", {
        scope: JSON.parse(scopeKey),
        parent_ref: parent?.ref || null,
        parent_node_id: parent?.node_id || null,
        cursor,
        limit: 40,
        view,
      });
      if (generation.current !== token) return;
      setResult(response);
      if (response.value)
        setPages((previous) => ({
          ...previous,
          [key]: {
            ...response.value!,
            nodes: cursor
              ? [...(previous[key]?.nodes || []), ...response.value!.nodes]
              : response.value!.nodes,
          },
        }));
    } catch (cause) {
      if (generation.current === token) setError(String(cause));
    } finally {
      if (generation.current === token)
        setBusy((values) => values.filter((value) => value !== key));
    }
  }
  useEffect(() => {
    const token = ++generation.current;
    setPages({});
    setBusy([]);
    setExpanded([]);
    setSelected(null);
    setError("");
    setResult(null);
    void load(null, null, token);
    return () => {
      generation.current++;
    };
    // scopeKey is the canonical serialized navigation request.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scopeKey, view, request]);
  function renderBranch(parent: TreeNode | null, ownerId?: string) {
    const key = parent?.node_id || "$root";
    const page = pages[key];
    return (
      <>
        <ul className="material-tree">
          {page?.nodes.map((node) => (
            <li key={node.node_id}>
              <div className="tree-row">
                {node.has_children && (
                  <button
                    className="tree-toggle"
                    aria-label={`${expanded.includes(node.node_id) ? "收起" : "展开"}${node.title}`}
                    aria-expanded={expanded.includes(node.node_id)}
                    onClick={() => {
                      if (expanded.includes(node.node_id))
                        setExpanded((values) =>
                          values.filter((value) => value !== node.node_id),
                        );
                      else {
                        setExpanded((values) => [...values, node.node_id]);
                        if (!pages[node.node_id]) void load(node);
                      }
                    }}
                  >
                    {expanded.includes(node.node_id) ? "−" : "+"}
                  </button>
                )}
                <button
                  className="tree-label"
                  aria-pressed={selected?.node_id === node.node_id}
                  onClick={() => {
                    setSelected(node);
                    onChoose(
                      node,
                      node.kind === "owner" ? node.node_id : ownerId,
                    );
                  }}
                >
                  {node.title}
                  <small>
                    {node.layer || nodeKinds[node.kind] || node.kind}
                  </small>
                </button>
              </div>
              {expanded.includes(node.node_id) &&
                renderBranch(
                  node,
                  node.kind === "owner" ? node.node_id : ownerId,
                )}
            </li>
          ))}
        </ul>
        {busy.includes(key) ? (
          <p role="status">正在读取结构…</p>
        ) : (
          page?.next_cursor && (
            <button onClick={() => void load(parent, page.next_cursor)}>
              更多结构条目
            </button>
          )
        )}
      </>
    );
  }
  return (
    <aside className="material-structure" aria-label="材料结构">
      <h2>材料结构</h2>
      <label>
        结构视图
        <select
          aria-label="结构视图"
          value={view}
          onChange={(event) => setView(event.target.value as typeof view)}
        >
          <option value="logical">逻辑分层</option>
          <option value="storage">登记的存储路径</option>
        </select>
      </label>
      <button
        onClick={() => {
          setSelected(null);
          onChoose(null);
        }}
      >
        全局获准范围
      </button>
      {error && <p role="alert">{error}</p>}
      {selected && (
        <details open>
          <summary>所选位置</summary>
          <p>{selected.title}</p>
          <p>{storageRoles[selected.storage_role]}</p>
          {selected.registered_path && <code>{selected.registered_path}</code>}
          {selected.ref && <FixedReferences refs={[selected.ref]} />}
        </details>
      )}
      {renderBranch(null)}
      <ResultStatus result={result?.status !== "ok" ? result : null} />
    </aside>
  );
}
