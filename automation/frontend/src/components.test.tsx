import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { Modal } from "./components";
afterEach(cleanup);
it("弹窗纯文本显示材料并支持关闭", () => {
  HTMLDialogElement.prototype.showModal = vi.fn();
  const close = vi.fn();
  render(
    <Modal title="证据" close={close}>
      <p>{"<script>unsafe()</script>"}</p>
    </Modal>,
  );
  expect(screen.getByText("<script>unsafe()</script>")).toBeInTheDocument();
  expect(document.querySelector("script")).toBeNull();
  fireEvent.click(screen.getByText("关闭"));
  expect(close).toHaveBeenCalled();
});
