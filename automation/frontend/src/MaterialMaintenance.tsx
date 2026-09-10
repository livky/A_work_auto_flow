import { useRef, useState } from "react";
import { download } from "./api";
import { ResearchMarkdown } from "./ResearchDocument";
import type {
  FixedRef,
  MaintenancePlan,
  MaintenanceReceipt,
  Result,
  Scope,
} from "./generated/material-query";
import {
  FixedReferences,
  ResultStatus,
  type MaterialRequest,
} from "./MaterialPacket";

const actionNames = {
  retain: "保留",
  revise: "修订",
  resynthesize: "重新综合",
  retract: "撤回",
  defer: "暂缓",
};

/** A returned plan is a review package, not authorization to write. Any local
 * edit invalidates the server-reviewed digest, including edits made in flight. */
export function MaterialMaintenance({
  request,
  refs,
  scope,
}: {
  request: MaterialRequest;
  refs: FixedRef[];
  scope: Scope;
}) {
  const [original, setOriginal] = useState<MaintenancePlan | null>(null);
  const [baseline, setBaseline] = useState<MaintenancePlan | null>(null);
  const [draft, setDraft] = useState("");
  const [reviewed, setReviewed] = useState<MaintenancePlan | null>(null);
  const [result, setResult] = useState<Result<unknown> | null>(null);
  const [receipt, setReceipt] = useState<MaintenanceReceipt | null>(null);
  const [busy, setBusy] = useState(false);
  const [applying, setApplying] = useState(false);
  const [error, setError] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const editVersion = useRef(0);
  const applyIds = useRef<Record<string, string>>({});
  let parsed: MaintenancePlan | null = null;
  let parseError = "";
  if (draft)
    try {
      const value = JSON.parse(draft);
      if (
        !value ||
        !Array.isArray(value.items) ||
        !value.plan_id ||
        !value.plan_digest
      )
        throw Error("需要包含 plan_id、plan_digest 和 items 的完整任务包");
      const isRef = (ref: unknown) =>
        Boolean(
          ref &&
          typeof ref === "object" &&
          typeof (ref as FixedRef).id === "string" &&
          typeof (ref as FixedRef).sha256 === "string" &&
          typeof (ref as FixedRef).kind === "string",
        );
      const strings = (values: unknown) =>
        Array.isArray(values) &&
        values.every((value) => typeof value === "string");
      if (
        !value.items.every(
          (item: MaintenancePlan["items"][number]) =>
            item &&
            isRef(item.ref) &&
            typeof item.action === "string" &&
            strings(item.reasons) &&
            Array.isArray(item.affected_refs) &&
            item.affected_refs.every(isRef) &&
            (item.draft_json === null || typeof item.draft_json === "string"),
        ) ||
        !strings(value.unchecked_regions) ||
        !Array.isArray(value.reviewed_refs) ||
        !value.reviewed_refs.every(isRef) ||
        (value.review_note !== undefined &&
          typeof value.review_note !== "string") ||
        (value.reviewer_kind !== undefined &&
          ![null, "human", "ai"].includes(value.reviewer_kind)) ||
        !(
          value.semantic_reviewer === null ||
          typeof value.semantic_reviewer === "string"
        )
      )
        throw Error("任务包条目、原因、影响引用或审查身份格式有误");
      parsed = value as MaintenancePlan;
    } catch (cause) {
      parseError = String(cause);
    }

  function edit(value: string) {
    editVersion.current++;
    setDraft(value);
    setReviewed(null);
    setConfirmed(false);
    setReceipt(null);
  }
  function updateReview(patch: Partial<MaintenancePlan>) {
    if (parsed) edit(JSON.stringify({ ...parsed, ...patch }, null, 2));
  }
  // The reading checklist is derived from the server-delivered package, never
  // from user-edited JSON. Its receipt is copied unchanged and remains evidence
  // of delivery only; the named reviewer supplies the semantic judgment.
  const deliveredRefs = [
    ...new Map(
      (baseline?.context_items || [])
        .flatMap((item) => item.refs)
        .map((ref) => [JSON.stringify(ref), ref]),
    ).values(),
  ];
  const humanReviewed =
    parsed?.reviewer_kind === "human" &&
    deliveredRefs.length > 0 &&
    deliveredRefs.every((ref) =>
      parsed?.reviewed_refs.some(
        (reviewedRef) => JSON.stringify(reviewedRef) === JSON.stringify(ref),
      ),
    );
  async function createPlan() {
    setBusy(true);
    setError("");
    setResult(null);
    setReceipt(null);
    const version = ++editVersion.current;
    try {
      const response = await request<MaintenancePlan>(
        "materials/maintenance-plan",
        {
          changed_refs: refs,
          scope,
          strategy: "dependency-review",
          strategy_version: "1",
        },
      );
      if (editVersion.current !== version) return;
      setResult(response);
      setReviewed(null);
      setConfirmed(false);
      if (response.value) {
        setOriginal(response.value);
        setBaseline(response.value);
        setDraft(JSON.stringify(response.value, null, 2));
      }
    } catch (cause) {
      setError(String(cause));
    } finally {
      setBusy(false);
    }
  }
  async function review() {
    if (!parsed || !original) return;
    setBusy(true);
    setError("");
    const version = editVersion.current;
    try {
      const response = await request<MaintenancePlan>(
        "materials/maintenance-review",
        { plan: parsed, expected_digest: original.plan_digest },
      );
      setResult(response);
      if (version !== editVersion.current) {
        setError("校验期间草案发生变化，请重新校验当前草案。");
        return;
      }
      // A reviewed package may deliberately remain partial because the server
      // preserves scientific-review warnings or unchecked regions. Accept only
      // code-free successful envelopes, while retaining every warning below.
      if (
        ["ok", "partial"].includes(response.status) &&
        !response.code &&
        response.value
      ) {
        setOriginal(response.value);
        setReviewed(response.value);
        setDraft(JSON.stringify(response.value, null, 2));
        setConfirmed(false);
      }
    } catch (cause) {
      setError(String(cause));
    } finally {
      setBusy(false);
    }
  }
  async function apply() {
    if (!reviewed || !confirmed) return;
    setBusy(true);
    setApplying(true);
    setError("");
    const key = `${reviewed.plan_id}:${reviewed.plan_digest}`;
    // Keep the same ID across an uncertain transport retry to avoid duplicate
    // commits. A newly reviewed digest receives a new operation identity.
    const requestId = (applyIds.current[key] ||= crypto.randomUUID());
    try {
      const response = await request<MaintenanceReceipt>(
        "materials/maintenance-apply",
        {
          plan_id: reviewed.plan_id,
          expected_digest: reviewed.plan_digest,
          request_id: requestId,
        },
      );
      setResult(response);
      if (response.value) setReceipt(response.value);
      // Canonical writes can finish with indexing or deferred work still
      // pending. Close this submission, but keep its receipt visible. A partial
      // error remains retryable with the same request ID and reviewed digest.
      if (
        ["ok", "partial"].includes(response.status) &&
        !response.code &&
        response.value
      ) {
        setConfirmed(false);
        setReviewed(null);
      }
    } catch (cause) {
      setError(String(cause));
    } finally {
      setBusy(false);
      setApplying(false);
    }
  }
  return (
    <section className="material-maintenance" aria-label="维护任务包">
      <h3>维护任务包</h3>
      <p>
        以所选材料为变化入口，整理依赖影响。导出的任务包需要实际阅读与审查后回填；生成计划本身不代表已复核。
      </p>
      <button
        disabled={busy || refs.length === 0}
        onClick={() => void createPlan()}
      >
        生成维护任务包（{refs.length} 个引用）
      </button>
      {original && (
        <>
          <div className="material-actions">
            <button
              onClick={() =>
                download(`maintenance-${original.plan_id}.json`, draft)
              }
            >
              导出任务包 JSON
            </button>
            <label className="file-label">
              导入审查结果
              <input
                type="file"
                accept=".json,application/json"
                disabled={busy}
                onChange={async (event) => {
                  const file = event.target.files?.[0];
                  if (file) {
                    try {
                      edit(await file.text());
                    } catch (cause) {
                      setError(String(cause));
                    }
                  }
                  event.target.value = "";
                }}
              />
            </label>
          </div>
          <section aria-label="维护审查材料">
            <h4>本次交付的审查材料</h4>
            {(baseline?.context_items || []).map((item, index) => (
              <article key={index} className="maintenance-context">
                <h5>{item.heading}</h5>
                <ResearchMarkdown text={item.markdown} />
                {item.omitted.length > 0 && (
                  <p className="risk">缺少内容：{item.omitted.join("；")}</p>
                )}
                <details>
                  <summary>材料固定引用</summary>
                  <FixedReferences refs={item.refs} />
                </details>
              </article>
            ))}
            {!baseline?.context_items?.length && (
              <p>当前任务包未交付正文，请导出给实际审查者补齐读取与审查。</p>
            )}
            <p className="muted">
              交付回执记录已提供的材料。审查者需要判断变更及依据，不能据此认定科学结论已经验证。
            </p>
          </section>
          {parsed && (
            <fieldset disabled={applying} className="maintenance-human-review">
              <legend>在此完成人工审查</legend>
              <label>
                人工审查身份
                <input
                  value={
                    parsed.reviewer_kind === "human"
                      ? parsed.semantic_reviewer || ""
                      : ""
                  }
                  onChange={(event) =>
                    updateReview({
                      semantic_reviewer: event.target.value,
                      reviewer_kind: "human",
                      reviewed_refs: [],
                    })
                  }
                />
              </label>
              <label>
                实际审查说明
                <textarea
                  aria-label="实际审查说明"
                  value={parsed.review_note || ""}
                  onChange={(event) =>
                    updateReview({
                      review_note: event.target.value,
                      reviewer_kind: "human",
                      reviewed_refs: [],
                    })
                  }
                  placeholder="说明实际阅读了什么、为何采取所选动作、仍有哪些限制。"
                />
              </label>
              <label>
                <input
                  type="checkbox"
                  checked={humanReviewed}
                  disabled={
                    !baseline?.read_receipt ||
                    !deliveredRefs.length ||
                    !parsed.semantic_reviewer?.trim() ||
                    !parsed.review_note?.trim()
                  }
                  onChange={(event) =>
                    updateReview({
                      reviewer_kind: "human",
                      reviewed_refs: event.target.checked ? deliveredRefs : [],
                    })
                  }
                />
                我已审查上方列出的材料，并填写了实际判断
              </label>
            </fieldset>
          )}
          <label>
            审查结果 JSON
            <textarea
              aria-label="审查结果 JSON"
              className="maintenance-json"
              spellCheck={false}
              disabled={applying}
              value={draft}
              onChange={(event) => edit(event.target.value)}
            />
          </label>
          {parseError && <p role="alert">{parseError}</p>}
          {parsed && Array.isArray(parsed.items) && (
            <div className="maintenance-diff" aria-label="维护变更预览">
              {parsed.items.map((item, index) => {
                const previous = baseline?.items.find(
                  (value) => value.ref?.id === item.ref?.id,
                );
                return (
                  <article key={index}>
                    <h4>
                      {item.ref?.id || `条目 ${index + 1}`} ·{" "}
                      {actionNames[item.action] || item.action}
                    </h4>
                    <p>
                      {Array.isArray(item.reasons)
                        ? item.reasons.join("；")
                        : "原因格式有误"}
                    </p>
                    <div className="draft-comparison">
                      <section>
                        <strong>导出时草案</strong>
                        <pre>{previous?.draft_json || "无正文草案"}</pre>
                      </section>
                      <section>
                        <strong>回填后草案</strong>
                        <pre>{item.draft_json || "无正文草案"}</pre>
                      </section>
                    </div>
                    {Array.isArray(item.affected_refs) && (
                      <details>
                        <summary>影响引用</summary>
                        <FixedReferences refs={item.affected_refs} />
                      </details>
                    )}
                  </article>
                );
              })}
              <p>审查身份：{parsed.semantic_reviewer || "尚未填写"}</p>
              <p>
                未检查范围：
                {Array.isArray(parsed.unchecked_regions)
                  ? parsed.unchecked_regions.join("；") || "未列出"
                  : "格式有误"}
              </p>
            </div>
          )}
          <button disabled={busy || !parsed} onClick={() => void review()}>
            校验回填与固定依据
          </button>
          {reviewed && (
            <div className="maintenance-apply">
              <p>服务器已接受此版本的审查结果。请检查上方各项动作和草案。</p>
              <label>
                <input
                  type="checkbox"
                  checked={confirmed}
                  onChange={(event) => setConfirmed(event.target.checked)}
                />
                我已核对当前变更预览，提交此版本
              </label>
              <button
                disabled={busy || !confirmed}
                onClick={() => void apply()}
              >
                应用已审查变更
              </button>
            </div>
          )}
        </>
      )}
      {busy && <p role="status">正在处理维护任务…</p>}
      {error && <p role="alert">{error}</p>}
      <ResultStatus result={result} />
      {receipt && (
        <section aria-label="维护提交回执">
          <h4>提交回执</h4>
          <p>索引状态：{receipt.index_status}</p>
          <p>
            已提交：
            {receipt.commits
              .map(([owner, commit]) => `${owner} · ${commit}`)
              .join("；") || "无"}
          </p>
          <p>待处理：{receipt.pending_items.join("；") || "无"}</p>
          {receipt.recovery_receipt && (
            <p>恢复回执：{receipt.recovery_receipt}</p>
          )}
        </section>
      )}
    </section>
  );
}
