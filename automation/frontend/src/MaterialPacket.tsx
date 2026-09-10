import { ResearchMarkdown } from "./ResearchDocument";
import type {
  FixedRef,
  MaterialPacket as Packet,
  Result,
} from "./generated/material-query";

/** Every endpoint preserves its envelope, including HTTP error responses. A
 * partial value is useful evidence, but must never be rendered as full success. */
export type MaterialRequest = <T>(
  route: string,
  data?: unknown,
) => Promise<Result<T>>;
export const groupTitles = {
  direct: "直接材料",
  required_context: "必要上下文",
  association: "关联建议",
  gaps: "缺口与限制",
};

export function FixedReferences({ refs }: { refs: FixedRef[] }) {
  return (
    <ul className="material-refs">
      {refs.map((ref, index) => (
        <li key={`${ref.kind}:${ref.id}:${index}`}>
          <code>{ref.id}</code>
          <span>
            {" "}
            · {ref.kind}
            {ref.revision === null ? "" : ` · 修订 ${ref.revision}`}
          </span>
          <small>
            SHA-256：{ref.sha256 || "未提供"}
            {ref.locator ? ` · ${ref.locator}` : ""}
          </small>
        </li>
      ))}
    </ul>
  );
}

export function ResultStatus({ result }: { result: Result<unknown> | null }) {
  if (!result) return null;
  const names = {
    ok: "完成",
    partial: "部分完成",
    rejected: "请求未接受",
    cancelled: "已取消",
    failed: "执行失败",
  };
  return (
    <section
      className={`material-status status-${result.status}`}
      aria-label="执行回执"
      role="status"
    >
      <strong>{names[result.status]}</strong>
      {result.code && <span> · {result.code}</span>}
      {result.stop_reason && <p>停止原因：{result.stop_reason}</p>}
      {result.warnings.length > 0 && (
        <ul>
          {result.warnings.map((warning, i) => (
            <li key={i}>{warning}</li>
          ))}
        </ul>
      )}
      <details>
        <summary>预算消耗与固定依据</summary>
        <dl>
          <dt>时间</dt>
          <dd>{result.consumed.wall_ms} ms</dd>
          <dt>读取</dt>
          <dd>{result.consumed.read_bytes} 字节</dd>
          <dt>输出</dt>
          <dd>{result.consumed.output_chars} 字符</dd>
          <dt>候选</dt>
          <dd>{result.consumed.candidates}</dd>
          <dt>图节点 / 边 / 跳数</dt>
          <dd>
            {result.consumed.graph_nodes} / {result.consumed.graph_edges} /{" "}
            {result.consumed.graph_hops}
          </dd>
          <dt>模型令牌</dt>
          <dd>{result.consumed.model_tokens}</dd>
        </dl>
        {result.basis ? (
          <>
            <p>一致性：{result.basis.consistency}</p>
            <FixedReferences refs={result.basis.refs} />
            <pre>
              {JSON.stringify(
                {
                  owner_heads: result.basis.owner_heads,
                  index_watermarks: result.basis.index_watermarks,
                },
                null,
                2,
              )}
            </pre>
          </>
        ) : (
          <p>未返回固定依据。</p>
        )}
      </details>
    </section>
  );
}

export function MaterialPacket({ packet }: { packet: Packet | null }) {
  if (!packet)
    return (
      <section className="material-empty">
        <h3>材料包</h3>
        <p>选择候选后组装。这里将分别显示正文、必要上下文、关联建议和缺口。</p>
      </section>
    );
  return (
    <section className="material-packet" aria-label="材料包">
      <h3>材料包</h3>
      <p>
        {packet.complete ? "结构完整" : "存在缺口"} ·{" "}
        {packet.canonical ? "正式材料" : "查询组装视图"}
      </p>
      {Object.entries(groupTitles).map(([group, title]) => (
        <section
          className={`packet-zone zone-${group}`}
          key={group}
          aria-label={title}
        >
          <h4>{title}</h4>
          {packet.parts.filter((part) => part.group === group).length === 0 ? (
            <p className="muted">本区没有内容。</p>
          ) : (
            packet.parts
              .filter((part) => part.group === group)
              .map((part, i) => (
                <article key={i}>
                  <h5>{part.heading}</h5>
                  <ResearchMarkdown text={part.markdown} />
                  {part.omitted.length > 0 && (
                    <p className="risk">未纳入：{part.omitted.join("；")}</p>
                  )}
                  <details>
                    <summary>来源与字段</summary>
                    <FixedReferences refs={part.refs} />
                    <p>{part.selectors.join("、") || "未提供字段选择器"}</p>
                  </details>
                </article>
              ))
          )}
        </section>
      ))}
      <details>
        <summary>材料包标识</summary>
        <p>{packet.packet_id}</p>
        <p>
          {packet.definition.key} · 版本 {packet.definition.version}
        </p>
      </details>
    </section>
  );
}
