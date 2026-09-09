import { useState } from "react";
import { api } from "./api";
import type { Ref } from "../../schemas/memory-v1";

export type Packet = {
  context_text: string;
  manifest: Record<string, unknown>;
  source_refs?: Ref[];
  basis_heads?: Record<string, string>;
};
type Candidate = {
  canonical_id: string;
  owner_id: string;
  revision?: number;
  title?: string;
  snippet: string;
  source_ref: Ref;
  review_state?: string;
  boundaries: unknown;
  risks?: unknown[];
};
type Result = {
  query_id: string;
  candidates: Candidate[];
  missing: unknown[];
  rejected: unknown[];
  degradation: unknown[];
};
export const parseIds = (text: string) =>
  text.split(/[\s,，]+/).filter(Boolean);

export function PacketView({
  packet,
  expandRef,
}: {
  packet: Packet;
  expandRef?: (ref: Ref) => void;
}) {
  const [message, setMessage] = useState("");
  return (
    <section className="card">
      <div className="row spread">
        <h2>可复制的材料内容</h2>
        <button
          onClick={async () => {
            try {
              await navigator.clipboard.writeText(packet.context_text);
              setMessage("已复制续接内容");
            } catch (error) {
              setMessage(String(error));
            }
          }}
        >
          复制续接内容
        </button>
      </div>
      <p className="muted">
        正文 {Array.from(packet.context_text).length}{" "}
        个字符。生成和复制不会启动实验。
      </p>
      {message && <p role="status">{message}</p>}
      <pre className="memory-body" data-testid="memory-packet">
        {packet.context_text}
      </pre>
      {expandRef && (
        <div className="row">
          {((packet.manifest.navigation_refs as Ref[]) || []).map((ref) => (
            <button
              key={ref.target_id + ref.revision}
              onClick={() => expandRef(ref)}
            >
              继续展开 {ref.target_id}
              {ref.revision ? ` · r${ref.revision}` : ""}
            </button>
          ))}
        </div>
      )}
      <details>
        <summary>范围、版本、预算与遗漏清单</summary>
        <pre>{JSON.stringify(packet.manifest, null, 2)}</pre>
      </details>
    </section>
  );
}

export function MemorySearch({
  ownerId,
  open,
}: {
  ownerId: string;
  open: (owner: string, record: string) => void;
}) {
  const [query, setQuery] = useState("");
  const [purpose, setPurpose] = useState("exploration");
  const [scope, setScope] = useState("");
  const [exclude, setExclude] = useState("");
  const [budget, setBudget] = useState(16000);
  const [result, setResult] = useState<Result | null>(null);
  const [packet, setPacket] = useState<Packet | null>(null);
  const [trail, setTrail] = useState<Packet[]>([]);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const selection = {
    owner_id: ownerId,
    exclude_ids: parseIds(exclude),
    purpose,
    scope,
    budget,
  };
  async function search() {
    setBusy(true);
    setMessage("");
    setPacket(null);
    setTrail([]);
    try {
      setResult(
        await api<Result>("memory/search", {
          query,
          ...selection,
          vector: "auto",
          stage: "focus",
        }),
      );
    } catch (error) {
      setMessage(String(error));
    } finally {
      setBusy(false);
    }
  }
  async function expand(ref: Ref) {
    setBusy(true);
    setMessage("");
    try {
      const next = await api<Packet>("memory/expand", {
        refs: [ref],
        selection,
        budget,
      });
      if (packet) setTrail((previous) => [...previous, packet]);
      setPacket(next);
    } catch (error) {
      setMessage(String(error));
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <section className="card">
        <h2>跨研究检索</h2>
        <label>
          要找的问题
          <input
            aria-label="记忆检索问题"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
        </label>
        <div className="memory-fields">
          <label>
            用途
            <select
              value={purpose}
              onChange={(event) => setPurpose(event.target.value)}
            >
              <option value="exploration">探索线索</option>
              <option value="formal">正式证据</option>
            </select>
          </label>
          <label>
            适用范围
            <input
              value={scope}
              onChange={(event) => setScope(event.target.value)}
              placeholder="正式证据必须明确范围"
            />
          </label>
          <label>
            排除对象或记录
            <input
              value={exclude}
              onChange={(event) => setExclude(event.target.value)}
              placeholder="输入 ID，以空格分隔"
            />
          </label>
          <label>
            正文字符预算
            <input
              type="number"
              min="1"
              max="16000"
              value={budget}
              onChange={(event) => setBudget(Number(event.target.value))}
            />
          </label>
        </div>
        <button
          className="primary"
          disabled={busy || !query.trim()}
          onClick={search}
        >
          {busy ? "正在读取…" : "检索记忆"}
        </button>
        {message && (
          <p className="risk" role="alert">
            {message}
          </p>
        )}
      </section>
      {result && (
        <section className="card">
          <h2>检索结果</h2>
          {!result.candidates.length && <p>当前范围没有符合条件的结果。</p>}
          {result.candidates.map((candidate) => (
            <article className="proposal" key={candidate.canonical_id}>
              <h3>{candidate.title || candidate.canonical_id}</h3>
              <p className="id">
                {candidate.canonical_id} ·{" "}
                {candidate.revision ? `r${candidate.revision}` : "固定指纹"} ·{" "}
                {candidate.owner_id}
              </p>
              <p>{candidate.snippet}</p>
              <pre>{JSON.stringify(candidate.boundaries, null, 2)}</pre>
              <p>复核：{candidate.review_state || "未复核"}</p>
              <div className="row">
                <button
                  disabled={busy}
                  onClick={() => expand(candidate.source_ref)}
                >
                  展开固定来源
                </button>
                {candidate.source_ref.target_kind === "record" && (
                  <button
                    onClick={() =>
                      open(candidate.owner_id, candidate.source_ref.target_id)
                    }
                  >
                    查看记录与版本
                  </button>
                )}
              </div>
            </article>
          ))}
          <details open={!!result.degradation.length}>
            <summary>缺失、拒绝与降级原因</summary>
            <pre>
              {JSON.stringify(
                {
                  missing: result.missing,
                  rejected: result.rejected,
                  degradation: result.degradation,
                },
                null,
                2,
              )}
            </pre>
          </details>
        </section>
      )}
      {packet && (
        <>
          {!!trail.length && (
            <button
              onClick={() => {
                setPacket(trail[trail.length - 1]);
                setTrail(trail.slice(0, -1));
              }}
            >
              返回上一层（已读取版本）
            </button>
          )}
          <PacketView packet={packet} expandRef={expand} />
        </>
      )}
    </>
  );
}
