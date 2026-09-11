import { afterEach, describe, expect, it, vi } from "vitest";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  within,
} from "@testing-library/react";
import { Memory } from "./Memory";
import { api } from "./api";

vi.mock("./api", () => ({ api: vi.fn(), download: vi.fn() }));
vi.mock("./RawMaterials", () => ({ RawMaterials: () => null }));
afterEach(cleanup);

describe("统一记忆层级入口", () => {
  it("每层只有一个筛选和新建入口，其他对象未迁移的内容仍可找到", async () => {
    const records = Object.fromEntries(
      ["event", "narrative", "map", "overview"].map((kind) => [
        kind,
        {
          record_id: kind,
          revision: 1,
          owner_id: "RES-SYNTHETIC",
          kind,
          title: `合成 ${kind}`,
          body_markdown: `保存的 ${kind} 正文`,
          record_reason: "仅软件回归",
          payload: { claims: [] },
          sources: [],
        },
      ]),
    );
    vi.mocked(api).mockImplementation(async (path) => {
      if (path === "memory/list-owners")
        return {
          owners: [
            { owner_id: "RES-SYNTHETIC", native_data: { title: "合成研究" } },
          ],
        } as never;
      if (path === "memory/inspect")
        return {
          records,
          head: null,
          claim_states: {},
          policy: {},
          index_status: "indexed",
        } as never;
      throw new Error(`未预期请求：${path}`);
    });
    render(<Memory />);
    await screen.findByRole("heading", { name: "合成 overview" });
    const filters = screen.getByRole("group", { name: "按层级或类型筛选" });
    expect(within(filters).getAllByLabelText("L2 研究经过")).toHaveLength(1);
    expect(within(filters).getAllByLabelText("L4 整体概览")).toHaveLength(1);
    expect(screen.queryByText("L2 事件记录（兼容）")).not.toBeInTheDocument();
    expect(screen.queryByText("L4 主题地图")).not.toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "新增L2 研究经过" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "新增L4 整体概览" }),
    ).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "清空类型" }));
    fireEvent.click(within(filters).getByLabelText("L4 整体概览"));
    expect(
      screen.getByRole("heading", { name: "合成 overview" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "合成 map" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("heading", { name: "合成 event" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("heading", { name: "合成 narrative" }),
    ).not.toBeInTheDocument();
  });
});
