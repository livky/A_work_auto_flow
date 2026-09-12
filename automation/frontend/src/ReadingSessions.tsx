import { useEffect, useRef, useState } from "react";
import { api, download } from "./api";
import { ResearchMarkdown } from "./ResearchDocument";
import { MaterialPacket } from "./MaterialPacket";
import type { MaterialPacket as Packet } from "./generated/material-query";

type Session = {
  session_id: string;
  revision: number;
  owner_id: string | null;
  goal: string;
  phase: string;
  archived: boolean;
};
type Listing = {
  items: Session[];
  next_offset: number | null;
  unavailable_count: number;
};
type Reading = {
  session_id: string;
  revision: number;
  context_markdown: string;
  phase: string;
  archived: boolean;
  gaps: string[];
  candidates: { candidate_id: string; title: string; status: string }[];
};
type Result<T> = {
  status: string;
  message?: string;
  code?: string;
  warnings?: string[];
  value: T | null;
};

// 材料接口拒绝时使用Result的code/warnings，包含预算和权限原因；HTTP异常也保留该封套。
function failureMessage(value: unknown, fallback = "阅读记录不可用") {
  const wrapped = value as {
    materialResult?: Result<unknown>;
    message?: string;
  };
  const result = wrapped?.materialResult || (value as Result<unknown>);
  return (
    [result?.code, ...(result?.warnings || [])].filter(Boolean).join("：") ||
    wrapped?.message ||
    fallback
  );
}

/** Read the live RS through the public API; never cache private notes across owners. */
export function ReadingSessions({ ownerId }: { ownerId: string }) {
  const [items, setItems] = useState<Session[]>([]);
  const [next, setNext] = useState<number | null>(null);
  const [reading, setReading] = useState<Reading | null>(null);
  const [snapshotRevision, setSnapshotRevision] = useState(0);
  const [packet, setPacket] = useState<Packet | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const generation = useRef(0);

  async function list(offset = 0) {
    const token = ++generation.current;
    setBusy(true);
    setError("");
    setReading(null);
    setPacket(null);
    try {
      const response = await api<Result<Listing>>("materials/reading-list", {
        ...(ownerId ? { owner_id: ownerId } : {}),
        offset,
        limit: 20,
        include_archived: true,
      });
      if (token !== generation.current) return;
      if (!response.value)
        throw Error(failureMessage(response, "阅读清单不可用"));
      setItems(response.value.items);
      setNext(response.value.next_offset);
      if (response.value.unavailable_count)
        setError("部分记录当前不可读取；请检查来源或权限。");
    } catch (e) {
      if (token === generation.current) {
        setItems([]);
        setNext(null);
        setError(failureMessage(e));
      }
    } finally {
      if (token === generation.current) setBusy(false);
    }
  }

  async function view(id: string) {
    const token = ++generation.current;
    setBusy(true);
    setError("");
    setReading(null);
    setPacket(null);
    try {
      const response = await api<Result<Reading>>("materials/reading-view", {
        session_id: id,
      });
      if (token !== generation.current) return;
      if (!response.value) throw Error(failureMessage(response));
      setReading(response.value);
      setSnapshotRevision(response.value.revision);
    } catch (e) {
      if (token === generation.current) setError(failureMessage(e));
    } finally {
      if (token === generation.current) setBusy(false);
    }
  }

  async function openSource(candidateId: string) {
    if (!reading) return;
    const token = ++generation.current;
    setBusy(true);
    setError("");
    setPacket(null);
    try {
      const response = await api<
        Result<{
          revision: number;
          readings: { packet: Packet }[];
          gaps: string[];
        }>
      >("materials/reading-read", {
        session_id: reading.session_id,
        expected_revision: reading.revision,
        request_id: crypto.randomUUID(),
        candidate_ids: [candidateId],
      });
      if (token !== generation.current) return;
      if (!response.value) throw Error(failureMessage(response, "原文不可用"));
      setPacket(response.value.readings[0]?.packet || null);
      // 下一次打开沿用服务器新修订，避免浏览器自行推算版本。
      setReading({ ...reading, revision: response.value.revision });
      if (response.value.gaps.length) setError(response.value.gaps.join("；"));
    } catch (e) {
      if (token === generation.current) {
        setReading(null);
        setError(failureMessage(e));
      }
    } finally {
      if (token === generation.current) setBusy(false);
    }
  }

  useEffect(() => {
    setItems([]);
    setNext(null);
    void list();
    return () => {
      generation.current++;
    };
  }, [ownerId]);
  return (
    <section className="card">
      <h2>阅读记录</h2>
      <p className="muted">
        {ownerId ? "当前对象的阅读会话" : "全部可访问会话（含未绑定的旧记录）"}
        。打开或刷新时读取最新状态；不会自动重新检索。
      </p>
      <button disabled={busy} onClick={() => void list()}>
        刷新阅读清单
      </button>
      {error && <p role="alert">{error}</p>}
      {!busy && !items.length && (
        <p>本页没有可显示的会话。{next !== null ? "仍有下一页。" : ""}</p>
      )}
      <ul>
        {items.map((item) => (
          <li key={item.session_id}>
            <button disabled={busy} onClick={() => void view(item.session_id)}>
              {item.goal}
            </button>
            <span>
              {" "}
              · r{item.revision} · {item.archived ? "已归档" : "工作记录"}
            </span>
          </li>
        ))}
      </ul>
      {next !== null && (
        <button disabled={busy} onClick={() => void list(next)}>
          下一页阅读会话
        </button>
      )}
      {reading && (
        <article>
          <div className="row">
            <button
              disabled={busy}
              onClick={() => void view(reading.session_id)}
            >
              刷新当前阅读记录
            </button>
            <button
              onClick={() =>
                download(
                  `${reading.session_id}-r${snapshotRevision}.md`,
                  reading.context_markdown,
                )
              }
            >
              导出此版本笔记
            </button>
          </div>
          {reading.gaps.map((gap) => (
            <p role="status" key={gap}>
              {gap}
            </p>
          ))}
          <ResearchMarkdown text={reading.context_markdown} />
          <h3>打开固定原文</h3>
          <ul>
            {reading.candidates.map((item) => (
              <li key={item.candidate_id}>
                <button
                  disabled={busy || reading.archived}
                  onClick={() => void openSource(item.candidate_id)}
                >
                  {item.title} · 读取原文
                </button>
              </li>
            ))}
          </ul>
          <MaterialPacket packet={packet} />
        </article>
      )}
    </section>
  );
}
