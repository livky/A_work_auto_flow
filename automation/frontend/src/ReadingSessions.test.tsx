import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { api, download } from "./api";
import { ReadingSessions } from "./ReadingSessions";
vi.mock("./api", () => ({ api: vi.fn(), download: vi.fn() }));
const call = vi.mocked(api);
afterEach(() => {
  cleanup();
  vi.resetAllMocks();
});
const note = {
  session_id: "RS-one",
  revision: 4,
  context_markdown: "已读理解与必要细节 273.15",
  phase: "proceed",
  archived: false,
  gaps: [],
  candidates: [
    { candidate_id: "RC-one", title: "固定方法", status: "已记录理解" },
  ],
};
it("按对象读最新记录，打开原文后导出仍使用实际笔记快照版本", async () => {
  call.mockImplementation(async (path) =>
    path === "materials/reading-list"
      ? {
          value: {
            items: [{ session_id: "RS-one", goal: "温度研究", revision: 4 }],
            next_offset: null,
            unavailable_count: 0,
          },
        }
      : path === "materials/reading-view"
        ? { value: note }
        : { value: { revision: 5, readings: [], gaps: [] } },
  );
  render(<ReadingSessions ownerId="PRJ-one" />);
  fireEvent.click(await screen.findByRole("button", { name: "温度研究" }));
  expect(await screen.findByText("已读理解与必要细节 273.15")).toBeVisible();
  expect(call).toHaveBeenCalledWith("materials/reading-view", {
    session_id: "RS-one",
  });
  fireEvent.click(screen.getByRole("button", { name: "固定方法 · 读取原文" }));
  await waitFor(() =>
    expect(
      screen.getByRole("button", { name: "固定方法 · 读取原文" }),
    ).toBeEnabled(),
  );
  fireEvent.click(screen.getByRole("button", { name: "导出此版本笔记" }));
  expect(download).toHaveBeenCalledWith("RS-one-r4.md", note.context_markdown);
});
it("换对象或来源撤权时清除之前显示的笔记", async () => {
  call.mockImplementation(async (path) =>
    path === "materials/reading-list"
      ? {
          value: {
            items: [{ session_id: "RS-one", goal: "温度研究" }],
            next_offset: null,
            unavailable_count: 0,
          },
        }
      : { value: note },
  );
  const view = render(<ReadingSessions ownerId="PRJ-one" />);
  fireEvent.click(await screen.findByRole("button", { name: "温度研究" }));
  await screen.findByText("已读理解与必要细节 273.15");
  call.mockResolvedValue({ value: null, message: "来源撤权" });
  fireEvent.click(screen.getByRole("button", { name: "刷新当前阅读记录" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("来源撤权");
  expect(
    screen.queryByText("已读理解与必要细节 273.15"),
  ).not.toBeInTheDocument();
  view.rerender(<ReadingSessions ownerId="PRJ-other" />);
  await waitFor(() =>
    expect(call).toHaveBeenCalledWith(
      "materials/reading-list",
      expect.objectContaining({ owner_id: "PRJ-other" }),
    ),
  );
});
it("筛选后的空目录窗口仍能翻页，不报告全库无会话", async () => {
  call.mockResolvedValue({
    value: { items: [], next_offset: 20, unavailable_count: 0 },
  });
  render(<ReadingSessions ownerId="PRJ-one" />);
  fireEvent.click(
    await screen.findByRole("button", { name: "下一页阅读会话" }),
  );
  await waitFor(() =>
    expect(call).toHaveBeenCalledWith(
      "materials/reading-list",
      expect.objectContaining({ offset: 20 }),
    ),
  );
});
