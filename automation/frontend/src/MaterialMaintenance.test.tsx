import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { MaterialMaintenance } from "./MaterialMaintenance";
import { defaultBudget, emptyScope } from "./MaterialQuery";
import type { MaintenancePlan, Result } from "./generated/material-query";
import type { MaterialRequest } from "./MaterialPacket";
import { download } from "./api";
vi.mock("./api", () => ({ api: vi.fn(), download: vi.fn() }));
const ref = {
  kind: "record" as const,
  id: "MEM-SYN-REVIEW",
  revision: 1,
  sha256: "b".repeat(64),
  locator: null,
};
const plan: MaintenancePlan = {
  plan_id: "PLAN-1",
  plan_digest: "original-digest",
  basis: {
    refs: [ref],
    owner_heads: [["RES-SYN", "head-1"]],
    index_watermarks: [],
    consistency: "single_owner_snapshot",
  },
  items: [
    {
      ref,
      action: "defer",
      reasons: ["等待实际阅读"],
      affected_refs: [],
      draft_json: null,
    },
  ],
  reviewed_refs: [],
  unchecked_regions: ["正文尚未审查"],
  semantic_reviewer: null,
};
const ok = <T,>(value: T): Result<T> => ({
  status: "ok",
  value,
  code: null,
  warnings: [],
  consumed: defaultBudget,
  stop_reason: null,
  basis: plan.basis,
});
afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});
async function create(request: ReturnType<typeof vi.fn>) {
  render(
    <MaterialMaintenance
      request={request as MaterialRequest}
      refs={[ref]}
      scope={emptyScope()}
    />,
  );
  fireEvent.click(screen.getByRole("button", { name: /生成维护任务包/ }));
  await screen.findByLabelText("审查结果 JSON");
}

describe("维护任务包审查与提交", () => {
  it("人工审查仅在实际填写并勾选后引用服务器交付材料", async () => {
    const delivered = {
      ...plan,
      read_receipt: "server-delivery-receipt",
      context_items: [
        {
          group: "direct",
          heading: "合成完整材料",
          markdown: "完整正文与限制 $s=1$",
          refs: [ref],
          selectors: ["body"],
          omitted: [],
        },
      ],
      review_note: "",
      reviewer_kind: null,
    };
    const request = vi.fn().mockResolvedValue(ok(delivered));
    await create(request);
    expect(screen.getByText("合成完整材料")).toBeVisible();
    const acknowledgement = screen.getByRole("checkbox", {
      name: /我已审查上方列出的材料/,
    });
    expect(acknowledgement).not.toBeChecked();
    expect(acknowledgement).toBeDisabled();
    fireEvent.change(screen.getByLabelText("人工审查身份"), {
      target: { value: "synthetic human" },
    });
    fireEvent.change(screen.getByLabelText("实际审查说明"), {
      target: { value: "已阅读合成材料，保持暂缓，真实模型未验收。" },
    });
    fireEvent.click(acknowledgement);
    const reviewedDraft = JSON.parse(
      (screen.getByLabelText("审查结果 JSON") as HTMLTextAreaElement).value,
    );
    expect(reviewedDraft.reviewed_refs).toEqual([ref]);
    expect(reviewedDraft.reviewer_kind).toBe("human");
    expect(reviewedDraft.read_receipt).toBe("server-delivery-receipt");
    expect(request).toHaveBeenCalledTimes(1);
  });
  it("损坏回填JSON显示格式错误而不崩溃或丢弃输入", async () => {
    const request = vi.fn().mockResolvedValue(ok(plan));
    await create(request);
    const invalid = JSON.stringify({ ...plan, items: [null] });
    fireEvent.change(screen.getByLabelText("审查结果 JSON"), {
      target: { value: invalid },
    });
    expect(screen.getByRole("alert")).toHaveTextContent("格式有误");
    expect(screen.getByLabelText("审查结果 JSON")).toHaveValue(invalid);
    expect(
      screen.getByRole("button", { name: "校验回填与固定依据" }),
    ).toBeDisabled();
  });
  it("生成仅提供待审任务包，导出不伪造阅读或自动提交", async () => {
    const request = vi.fn().mockResolvedValue(ok(plan));
    await create(request);
    expect(
      screen.queryByRole("button", { name: "应用已审查变更" }),
    ).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "导出任务包 JSON" }));
    const exported = JSON.parse(vi.mocked(download).mock.calls[0][1]);
    expect(exported.reviewed_refs).toEqual([]);
    expect(exported.semantic_reviewer).toBeNull();
    expect(request).toHaveBeenCalledTimes(1);
  });
  it("拒绝回填时保留草案并展示拒绝依据", async () => {
    const request = vi
      .fn()
      .mockResolvedValueOnce(ok(plan))
      .mockResolvedValueOnce({
        ...ok(null),
        status: "rejected",
        code: "REVIEW_REQUIRED",
        warnings: ["缺少实际阅读回执"],
      });
    await create(request);
    const updated = {
      ...plan,
      items: [
        {
          ...plan.items[0],
          action: "revise",
          draft_json: '{"body_markdown":"回填后正文"}',
        },
      ],
    };
    fireEvent.change(screen.getByLabelText("审查结果 JSON"), {
      target: { value: JSON.stringify(updated) },
    });
    fireEvent.click(screen.getByRole("button", { name: "校验回填与固定依据" }));
    await screen.findByText("缺少实际阅读回执");
    expect(screen.getByLabelText("审查结果 JSON")).toHaveValue(
      JSON.stringify(updated),
    );
    expect(
      screen.queryByRole("button", { name: "应用已审查变更" }),
    ).not.toBeInTheDocument();
  });
  it("仅提交服务器审查摘要，不确定重试复用请求 ID", async () => {
    const reviewed = {
      ...plan,
      plan_digest: "reviewed-digest",
      semantic_reviewer: "human:synthetic-reviewer",
      reviewed_refs: [ref],
    };
    const request = vi
      .fn()
      .mockResolvedValueOnce(ok(plan))
      .mockResolvedValueOnce(ok(reviewed))
      .mockRejectedValueOnce(Error("网络中断"))
      .mockResolvedValueOnce(
        ok({
          commits: [["RES-SYN", "commit-2"]],
          pending_items: [],
          index_status: "indexed",
          recovery_receipt: null,
        }),
      );
    await create(request);
    fireEvent.click(screen.getByRole("button", { name: "校验回填与固定依据" }));
    const apply = await screen.findByRole("button", { name: "应用已审查变更" });
    expect(apply).toBeDisabled();
    fireEvent.click(
      screen.getByRole("checkbox", { name: /我已核对当前变更预览/ }),
    );
    fireEvent.click(apply);
    await screen.findByText(/网络中断/);
    fireEvent.click(apply);
    await screen.findByText(/commit-2/);
    const calls = request.mock.calls.filter(
      ([route]) => route === "materials/maintenance-apply",
    );
    expect(calls).toHaveLength(2);
    expect(calls[0][1]).toEqual(calls[1][1]);
    expect(calls[0][1].expected_digest).toBe("reviewed-digest");
    expect(calls[0][1].request_id).toBeTruthy();
  });
  it("校验期间编辑的草案不会被迟到审查结果覆盖", async () => {
    let resolveReview!: (value: unknown) => void;
    const request = vi
      .fn()
      .mockResolvedValueOnce(ok(plan))
      .mockImplementationOnce(
        () =>
          new Promise((resolve) => {
            resolveReview = resolve;
          }),
      );
    await create(request);
    fireEvent.click(screen.getByRole("button", { name: "校验回填与固定依据" }));
    const changed = JSON.stringify({
      ...plan,
      unchecked_regions: ["后来修改"],
    });
    fireEvent.change(screen.getByLabelText("审查结果 JSON"), {
      target: { value: changed },
    });
    resolveReview(ok({ ...plan, plan_digest: "late-digest" }));
    await waitFor(() =>
      expect(screen.getByText(/校验期间草案发生变化/)).toBeVisible(),
    );
    expect(screen.getByLabelText("审查结果 JSON")).toHaveValue(changed);
    expect(
      screen.queryByRole("button", { name: "应用已审查变更" }),
    ).not.toBeInTheDocument();
  });
  it("有效 partial 审查采用返回摘要，成功 partial 提交保留待办并关闭提交", async () => {
    const request = vi
      .fn()
      .mockResolvedValueOnce(ok(plan))
      .mockResolvedValueOnce({
        ...ok({ ...plan, plan_digest: "partial-reviewed" }),
        status: "partial",
        warnings: ["审查保存不代表科学确认"],
      })
      .mockResolvedValueOnce({
        ...ok({
          commits: [["RES-SYN", "commit-partial"]],
          pending_items: ["需另行复核"],
          index_status: "pending",
          recovery_receipt: null,
        }),
        status: "partial",
        warnings: ["规范已保存，索引尚待更新"],
      });
    await create(request);
    fireEvent.click(screen.getByRole("button", { name: "校验回填与固定依据" }));
    const apply = await screen.findByRole("button", { name: "应用已审查变更" });
    expect(screen.getByText("审查保存不代表科学确认")).toBeVisible();
    fireEvent.click(
      screen.getByRole("checkbox", { name: /我已核对当前变更预览/ }),
    );
    fireEvent.click(apply);
    await screen.findByText(/commit-partial/);
    expect(request.mock.calls[2][1].expected_digest).toBe("partial-reviewed");
    expect(
      screen.queryByRole("button", { name: "应用已审查变更" }),
    ).not.toBeInTheDocument();
    expect(screen.getByText("规范已保存，索引尚待更新")).toBeVisible();
    expect(screen.getByText(/待处理：需另行复核/)).toBeVisible();
    expect(screen.getByText("索引状态：pending")).toBeVisible();
  });
  it("带错误码的 partial 审查保留草案且不开放提交", async () => {
    const request = vi
      .fn()
      .mockResolvedValueOnce(ok(plan))
      .mockResolvedValueOnce({
        ...ok({ ...plan, plan_digest: "not-accepted" }),
        status: "partial",
        code: "CONFLICT",
        warnings: ["部分依据已改变"],
      });
    await create(request);
    fireEvent.click(screen.getByRole("button", { name: "校验回填与固定依据" }));
    await screen.findByText("部分依据已改变");
    expect(
      screen.queryByRole("button", { name: "应用已审查变更" }),
    ).not.toBeInTheDocument();
    expect(
      JSON.parse(
        (screen.getByLabelText("审查结果 JSON") as HTMLTextAreaElement).value,
      ).plan_digest,
    ).toBe("original-digest");
  });
  it("partial 提交错误保留已提交回执并以同一身份重试", async () => {
    const pending = {
      commits: [["RES-SYN", "commit-one"]],
      pending_items: ["RES-SECOND"],
      index_status: "pending",
      recovery_receipt: "recovery-1",
    };
    const request = vi
      .fn()
      .mockResolvedValueOnce(ok(plan))
      .mockResolvedValueOnce(ok(plan))
      .mockResolvedValueOnce({
        ...ok(pending),
        status: "partial",
        code: "WRITE_FAILED",
        warnings: ["后一归属写入失败"],
      })
      .mockResolvedValueOnce({
        ...ok({ ...pending, pending_items: [] }),
        status: "partial",
      });
    await create(request);
    fireEvent.click(screen.getByRole("button", { name: "校验回填与固定依据" }));
    const apply = await screen.findByRole("button", { name: "应用已审查变更" });
    fireEvent.click(
      screen.getByRole("checkbox", { name: /我已核对当前变更预览/ }),
    );
    fireEvent.click(apply);
    await screen.findByText("后一归属写入失败");
    expect(screen.getByText(/commit-one/)).toBeVisible();
    await waitFor(() => expect(apply).toBeEnabled());
    fireEvent.click(apply);
    await waitFor(() =>
      expect(
        screen.queryByRole("button", { name: "应用已审查变更" }),
      ).not.toBeInTheDocument(),
    );
    expect(request.mock.calls[2][1]).toEqual(request.mock.calls[3][1]);
  });
});
