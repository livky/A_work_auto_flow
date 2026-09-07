import { useEffect, useState } from "react";
import { api, kindNames, relationNames } from "./api";
import { Modal } from "./components";
type Ref = {
  target?: string;
  path?: string;
  locator?: string;
  relation?: string;
  error?: string;
  version_matches?: boolean;
  group?: string;
  index?: number;
};
type EvidenceNode = {
  id: string;
  title: string;
  kind: string;
  statement: string;
  state: string;
  fingerprint: string;
  record_reason: string;
  scope: string | null;
  execution_status: string | null;
  review: { status?: string; reviewer?: string };
  review_history: unknown[];
  refs: Ref[];
  assets: Ref[];
  risks: string[];
  formal_errors: string[];
  reports: { id: string; path: string; chain: string[] }[];
};
type Payload = {
  observed_at: string;
  nodes: Record<string, EvidenceNode>;
  errors: string[];
  monitor: {
    events: unknown[];
    candidates: unknown[];
    invalid_since: Record<string, string>;
  } | null;
};
export function Evidence({
  revision,
  error,
}: {
  revision: number;
  error: (message: string) => void;
}) {
  const [data, setData] = useState<Payload | null>(null);
  const [selected, setSelected] = useState("");
  const [query, setQuery] = useState("");
  const [kind, setKind] = useState("");
  const [state, setState] = useState("");
  const [preview, setPreview] = useState<{
    path: string;
    text: string;
    truncated: boolean;
  } | null>(null);
  const load = () =>
    api<Payload>("state", undefined, true)
      .then(setData)
      .catch((e) => error(e.message));
  useEffect(() => {
    load();
  }, [revision]);
  const nodes = Object.values(data?.nodes || {});
  const node = data?.nodes[selected];
  async function source(index?: number, group?: string) {
    if (!node) return;
    try {
      setPreview(
        await api(
          `source?id=${encodeURIComponent(node.id)}&fingerprint=${node.fingerprint}${index === undefined ? "" : "&ref=" + index}${group ? "&group=" + group : ""}`,
          undefined,
          true,
        ),
      );
    } catch (e) {
      error(String(e));
    }
  }
  function refs(items: Ref[], assets = false) {
    return items.map((ref, i) => (
      <article className="proposal" key={i}>
        <strong>
          {assets
            ? ref.group === "inputs"
              ? "输入"
              : "产物"
            : relationNames[ref.relation || ""] || ref.relation}
        </strong>
        <p className="id">{ref.target || ref.path}</p>
        <p>{ref.locator || "定位未提供"}</p>
        <p className={ref.error || !ref.version_matches ? "risk" : "muted"}>
          {ref.error ||
            (ref.version_matches ? "当前指纹一致" : "指纹未固定或已变化")}
        </p>
        <button
          onClick={() =>
            source(assets ? ref.index : i, assets ? ref.group : undefined)
          }
        >
          预览来源
        </button>
      </article>
    ));
  }
  return (
    <>
      <div className="page-heading">
        <div>
          <p className="eyebrow">证据 / 来源与复核</p>
          <h1>查看依据，检查影响</h1>
        </div>
        <button onClick={load}>刷新证据</button>
      </div>
      <div className="metrics">
        <div>
          <strong>{nodes.length}</strong>已登记记录
        </div>
        <div>
          <strong>{nodes.filter((n) => n.kind === "claim").length}</strong>
          逐条结论
        </div>
        <div>
          <strong>{nodes.filter((n) => n.state === "invalid").length}</strong>
          存在风险
        </div>
      </div>
      <div className="row toolbar">
        <input
          aria-label="搜索证据"
          placeholder="搜索标题、结论、ID、保存原因或确认人"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <select
          aria-label="证据类型"
          value={kind}
          onChange={(e) => setKind(e.target.value)}
        >
          <option value="">全部类型</option>
          {Object.entries(kindNames).map(([k, v]) => (
            <option key={k} value={k}>
              {v}
            </option>
          ))}
        </select>
        <select
          aria-label="证据状态"
          value={state}
          onChange={(e) => setState(e.target.value)}
        >
          <option value="">全部状态</option>
          <option value="eligible">符合正式条件</option>
          <option value="invalid">存在风险</option>
          <option value="needs-review">待复核</option>
        </select>
      </div>
      <div className="evidence-layout">
        <aside className="card scroll-list">
          {nodes
            .filter(
              (n) =>
                (!kind || n.kind === kind) &&
                (!state || n.state === state) &&
                JSON.stringify([
                  n.title,
                  n.id,
                  n.statement,
                  n.record_reason,
                  n.review,
                ])
                  .toLowerCase()
                  .includes(query.toLowerCase()),
            )
            .map((n) => (
              <button
                className={"item " + (n.id === selected ? "active" : "")}
                key={n.id}
                onClick={() => setSelected(n.id)}
              >
                <span className="eyebrow">{kindNames[n.kind] || n.kind}</span>
                <strong>{n.title}</strong>
                <span className="badge">
                  {n.review.status || "not-reviewed"}
                </span>
              </button>
            ))}
          {!nodes.length && <p>尚未登记证据记录。</p>}
        </aside>
        <section className="card">
          {node ? (
            <>
              <h2>{node.title}</h2>
              <p className="id">{node.id}</p>
              <p>{node.statement}</p>
              <h3>保存原因</h3>
              <p>{node.record_reason}</p>
              <div className="row">
                <span className="badge">
                  执行：{node.execution_status || "未提供"}
                </span>
                <span className="badge">
                  复核：{node.review.status || "not-reviewed"}
                </span>
              </div>
              <p>适用范围：{node.scope || "未提供"}</p>
              <button onClick={() => source()}>预览记录</button>
              <h3>来源与版本</h3>
              {refs(node.refs)}
              <h3>输入与产物</h3>
              {refs(node.assets, true)}
              <h3>风险与正式条件</h3>
              {node.risks.map((r) => (
                <p className="risk" key={r}>
                  {r}
                </p>
              ))}
              <p>
                首次观察到风险：
                {data?.monitor?.invalid_since[node.id] || "未观察或未记录"}
              </p>
              <ul>
                {node.formal_errors.map((r) => (
                  <li key={r}>{r}</li>
                ))}
              </ul>
              <h3>受影响报告</h3>
              {node.reports.length ? (
                node.reports.map((r) => (
                  <div className="proposal" key={r.id}>
                    <button onClick={() => setSelected(r.id)}>{r.path}</button>
                    <p className="id">{r.chain.join(" → ")}</p>
                  </div>
                ))
              ) : (
                <p>当前已登记关系中未发现受影响报告。</p>
              )}
              <details>
                <summary>复核记录与历史</summary>
                <pre>
                  {JSON.stringify(
                    { review: node.review, history: node.review_history },
                    null,
                    2,
                  )}
                </pre>
              </details>
            </>
          ) : (
            <div className="empty">选择一条记录查看来源、复核和下游影响。</div>
          )}
        </section>
      </div>
      <details className="card">
        <summary>监测事件与维护候选</summary>
        <pre>
          {JSON.stringify(data?.monitor || "尚未建立监测基线", null, 2)}
        </pre>
      </details>
      {data?.errors.map((x) => (
        <p className="alert" key={x}>
          {x}
        </p>
      ))}
      {preview && (
        <Modal title={preview.path} close={() => setPreview(null)}>
          <pre>{preview.text}</pre>
          {preview.truncated && <p>仅展示前 64 KiB。</p>}
        </Modal>
      )}
    </>
  );
}
