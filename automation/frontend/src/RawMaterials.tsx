import { useEffect, useState } from "react";
import { api } from "./api";

type Material = {
  material_id: string;
  title: string;
  path: string;
  sha256: string | null;
  status: string;
  origins: {
    owner_id: string;
    run_id?: string;
    role: string;
    title?: string;
    record_id?: string;
    revision?: number;
  }[];
  source_refs: unknown[];
};
type Inventory = {
  items: Material[];
  total: number;
  missing: { target_id: string; code: string }[];
};
type Preview = {
  text?: string;
  image_data?: string;
  truncated?: boolean;
  message?: string;
  verified_sha256: string;
};

function Original({ ownerId, item }: { ownerId: string; item: Material }) {
  const [preview, setPreview] = useState<Preview | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const status =
    (
      {
        registered: "固定引用，打开时核验",
        missing: "文件缺失",
        unversioned: "未登记固定指纹",
      } as Record<string, string>
    )[item.status] || item.status;
  return (
    <article className="proposal raw-material" data-testid="raw-material">
      <div className="row spread">
        <h3>{item.title}</h3>
        <span className="badge">L0 原始材料</span>
      </div>
      <p className="id">{item.path}</p>
      <p>{status}</p>
      {item.origins.some(
        (origin) => origin.role === "current_run_metadata",
      ) && <p className="muted">当前运行元数据：环境、参数与登记信息。</p>}
      <p>
        使用对象：
        {[
          ...new Set(
            item.origins.map((origin) => origin.run_id || origin.owner_id),
          ),
        ].join("、")}
      </p>
      <details>
        <summary>版本与使用关系</summary>
        <pre>
          {JSON.stringify(
            {
              sha256: item.sha256,
              origins: item.origins,
              source_refs: item.source_refs,
            },
            null,
            2,
          )}
        </pre>
      </details>
      <button
        disabled={busy || item.status !== "registered"}
        onClick={async () => {
          setBusy(true);
          setError("");
          setPreview(null);
          try {
            setPreview(
              await api<Preview>("memory/raw-material", {
                owner_id: ownerId,
                material_id: item.material_id,
                max_chars: 20000,
              }),
            );
          } catch (cause) {
            setError(String(cause));
          } finally {
            setBusy(false);
          }
        }}
      >
        {busy ? "正在核验…" : "核验并查看原件"}
      </button>
      {error && (
        <p role="alert" className="risk">
          {error}
        </p>
      )}
      {preview && (
        <div className="raw-preview">
          <p className="muted">
            已核对固定指纹；原件只读。
            {preview.truncated && "仅显示前 20000 字符，完整材料仍在原路径。"}
          </p>
          {preview.text !== undefined && <pre>{preview.text}</pre>}
          {preview.image_data && (
            <img
              src={preview.image_data}
              alt={item.title}
              style={{ maxWidth: "100%" }}
            />
          )}
          {preview.message && <p>{preview.message}</p>}
        </div>
      )}
    </article>
  );
}

export function RawMaterials({
  ownerId,
  onCount,
}: {
  ownerId: string;
  onCount: (count: number) => void;
}) {
  const [value, setValue] = useState<Inventory | null>(null);
  const [error, setError] = useState("");
  const [generation, setGeneration] = useState(0);
  useEffect(() => {
    // Do not display the previous owner's originals during a new request.
    let active = true;
    setValue(null);
    setError("");
    onCount(0);
    api<Inventory>("memory/raw-materials", { owner_id: ownerId })
      .then((result) => {
        if (active) {
          setValue(result);
          onCount(result.total);
        }
      })
      .catch((cause) => {
        if (active) setError(String(cause));
      });
    return () => {
      active = false;
    };
  }, [ownerId, generation, onCount]);
  return (
    <section aria-label="L0 原始材料" className="raw-materials">
      <div className="row spread">
        <h2>L0 原始材料{value ? ` · ${value.total}` : ""}</h2>
        <button onClick={() => setGeneration((current) => current + 1)}>
          刷新原始材料
        </button>
      </div>
      <p className="muted">
        汇总已登记的输入、脚本、输出和独立来源，同一文件及版本只列一次。原件不会自动复制或进入普通检索。
      </p>
      {error && (
        <p role="alert" className="risk">
          {error}
        </p>
      )}
      {!value && !error && <p>正在读取材料登记…</p>}
      {value && !value.total && <p>当前对象尚无已登记的原始材料。</p>}
      {!!value?.missing.length && (
        <details>
          <summary>未能取得的来源</summary>
          <pre>{JSON.stringify(value.missing, null, 2)}</pre>
        </details>
      )}
      {value?.items.map((item) => (
        <Original
          key={item.material_id + generation}
          ownerId={ownerId}
          item={item}
        />
      ))}
    </section>
  );
}
