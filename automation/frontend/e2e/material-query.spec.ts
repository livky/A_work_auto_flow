import { test, expect as baseExpect, type Page } from "@playwright/test";
import { spawn, spawnSync, type ChildProcess } from "node:child_process";
import { resolve } from "node:path";
import { writeFile } from "node:fs/promises";

// Exercise the installed workbench assets and real HTTP coordinator against a
// disposable Chinese-path workspace. No real business owner or source is read.
const root = resolve("../..");
const expect = baseExpect.configure({ timeout: 30000 });
let process: ChildProcess;
let base: string;
let fixtureRoot: string;
test.describe.configure({ timeout: 180000 });
test.use({ actionTimeout: 30000 });
test.beforeAll(async () => {
  process = spawn(
    resolve(root, "services/qdrant/runtime/python.exe"),
    [resolve(root, "automation/tests/serve_memory_test.py")],
    { cwd: root, windowsHide: true, stdio: ["ignore", "pipe", "pipe"] },
  );
  await new Promise<void>((done, fail) => {
    let output = "";
    const timeout = setTimeout(() => {
      process.kill();
      fail(Error("材料查询沙盒启动超时：" + output));
    }, 150000);
    process.stdout!.on("data", (chunk) => {
      output += chunk;
      for (const line of output.split("\n"))
        try {
          const value = JSON.parse(line);
          if (value.root) fixtureRoot = value.root;
          if (value.url) {
            base = value.url;
            clearTimeout(timeout);
            done();
            return;
          }
        } catch {
          /* Keep startup diagnostics until a complete JSON line arrives. */
        }
    });
    process.stderr!.on("data", (chunk) => {
      output += chunk;
    });
    process.on("exit", (code) => {
      clearTimeout(timeout);
      fail(Error(`材料查询沙盒退出 ${code}：${output}`));
    });
  });
});
test.afterAll(() => process?.kill());
test.afterEach(async ({ page }, testInfo) => {
  if (testInfo.status !== testInfo.expectedStatus) {
    await page.screenshot({
      path: testInfo.outputPath("material-query-failure.png"),
      fullPage: true,
    });
    await testInfo.attach("visible-page", {
      body: await page.locator("body").innerText(),
      contentType: "text/plain",
    });
  }
});

async function search(page: Page) {
  await page.goto(base + "#/materials");
  await expect(
    page.getByRole("heading", { name: "材料查询", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "全局获准范围", exact: true }).click();
  await page.getByLabel("问题", { exact: true }).fill("SYNTHETIC");
  await page.getByRole("button", { name: "开始查询", exact: true }).click();
  await expect(page.getByTestId("material-candidate").first()).toBeVisible();
  await expect(
    page.getByRole("button", { name: "开始查询", exact: true }),
  ).toBeEnabled();
}

test("材料查询真实HTTP组装四区、固定依据与来源映射", async ({
  page,
}, testInfo) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(String(error)));
  await search(page);
  const storageResponse = page.waitForResponse(
    (response) =>
      response.url().endsWith("/materials/structure") &&
      response.request().postDataJSON()?.view === "storage" &&
      response.request().postDataJSON()?.parent_node_id === null,
  );
  await page.getByLabel("结构视图", { exact: true }).selectOption("storage");
  const storage = await (await storageResponse).json();
  expect(
    storage.value.nodes.some(
      (node: { registered_path: string | null }) => node.registered_path,
    ),
  ).toBe(true);
  await page.locator(".material-structure .tree-toggle").first().click();
  await page.getByRole("button", { name: /^归属原始登记/ }).click();
  await expect(page.locator(".material-structure details code")).toBeVisible();
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({
    path: testInfo.outputPath("material-query-storage.png"),
    fullPage: false,
  });
  await page.getByLabel("结构视图", { exact: true }).selectOption("logical");
  const first = page.getByTestId("material-candidate").first();
  await first.getByRole("checkbox").check();
  const assemblyResponse = page.waitForResponse((response) =>
    response.url().endsWith("/materials/assemble"),
  );
  await page
    .getByRole("button", { name: "组装所选材料（1）", exact: true })
    .click();
  const assembled = await (await assemblyResponse).json();
  expect(["ok", "partial"]).toContain(assembled.status);
  expect(assembled.value).toBeTruthy();
  const packet = page.getByRole("region", { name: "材料包", exact: true });
  for (const title of ["直接材料", "必要上下文", "关联建议", "缺口与限制"])
    await expect(
      packet.getByRole("region", { name: title, exact: true }),
    ).toBeVisible();
  await page.getByText("沿所选材料深化", { exact: true }).click();
  const deepenedResponse = page.waitForResponse((response) =>
    response.url().endsWith("/materials/deepen"),
  );
  await page.getByRole("button", { name: "深化所选材料", exact: true }).click();
  const deepened = await (await deepenedResponse).json();
  expect(["ok", "partial"]).toContain(deepened.status);
  await expect(page.getByText(/关系边：/)).toBeVisible();
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({
    path: testInfo.outputPath("material-query-desktop.png"),
    fullPage: false,
  });
  await page.setViewportSize({ width: 760, height: 1000 });
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({
    path: testInfo.outputPath("material-query-narrow.png"),
    fullPage: false,
  });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  expect(errors).toEqual([]);
});

test("维护任务包导出保留未审状态，改变条件使旧候选失效", async ({ page }) => {
  const applyCalls: string[] = [];
  page.on("request", (request) => {
    if (request.url().endsWith("/materials/maintenance-apply"))
      applyCalls.push(request.url());
  });
  await search(page);
  await page
    .getByTestId("material-candidate")
    .first()
    .getByRole("checkbox")
    .check();
  await page.getByRole("button", { name: /生成维护任务包/ }).click();
  const editor = page.getByLabel("审查结果 JSON", { exact: true });
  await expect(editor).toBeVisible();
  const plan = JSON.parse(await editor.inputValue());
  expect(plan.reviewed_refs).toEqual([]);
  expect(plan.semantic_reviewer).toBeNull();
  const downloaded = page.waitForEvent("download");
  await page
    .getByRole("button", { name: "导出任务包 JSON", exact: true })
    .click();
  expect((await downloaded).suggestedFilename()).toContain("maintenance-");
  await expect(
    page.getByRole("button", { name: "应用已审查变更", exact: true }),
  ).toHaveCount(0);
  // Moving a pending item to a real decision requires an actual reviewer and
  // delivered reading evidence; merely editing the action must be rejected.
  const unreviewed = {
    ...plan,
    items: plan.items.map((item: unknown, index: number) =>
      index === 0 ? { ...(item as object), action: "retain" } : item,
    ),
  };
  await editor.fill(JSON.stringify(unreviewed));
  await page
    .getByRole("button", { name: "校验回填与固定依据", exact: true })
    .click();
  await expect(
    page
      .getByRole("region", { name: "维护任务包", exact: true })
      .getByRole("status", { name: "执行回执" }),
  ).toContainText("请求未接受");
  expect(JSON.parse(await editor.inputValue())).toEqual(unreviewed);
  await page.getByLabel("问题", { exact: true }).fill("更改查询条件");
  await expect(page.getByText(/下方是上一次结果/)).toBeVisible();
  await expect(
    page.getByRole("button", { name: /组装所选材料/ }),
  ).toBeDisabled();
  await expect(
    page.getByRole("button", { name: /生成维护任务包/ }),
  ).toBeDisabled();
  expect(applyCalls).toEqual([]);
});

test("真实预算耗尽显示停止原因并保留查询范围", async ({ page }) => {
  await page.goto(base + "#/materials");
  await page.getByRole("button", { name: "全局获准范围", exact: true }).click();
  await page.getByLabel("问题", { exact: true }).fill("SYNTHETIC");
  await page.getByText("关联补充与预算", { exact: true }).click();
  await page.getByLabel("输出字符", { exact: true }).fill("0");
  await page.getByRole("button", { name: "开始查询", exact: true }).click();
  const status = page
    .locator(".material-search")
    .getByRole("status", { name: "执行回执" });
  await expect(status).toContainText("BUDGET");
  await expect(status).toContainText("停止原因");
  await expect(page.locator(".scope-summary")).toContainText("全局获准范围");
});

test("有效 partial 审查与真实提交保留索引待办，关闭已完成提交", async ({
  page,
  request,
}, testInfo) => {
  const owner = "RES-SYN-THERMAL";
  const marker = "SYNTHETIC-PARTIAL-UI-REGRESSION";
  async function memory(action: string, data: unknown) {
    const response = await request.post(base + "api/v1/memory/" + action, {
      data,
      headers: { Origin: new URL(base).origin },
    });
    return response.json();
  }
  // Create a v3 record through the same public transaction endpoint used by
  // callers. The small input has no dependencies or scientific review claims.
  const draft = {
    schema_version: 3,
    owner_id: owner,
    kind: "detail",
    title: marker,
    keywords: [marker],
    body_markdown: "",
    sources: [],
    provenance_gap: "SYNTHETIC 软件状态回归输入，未做科学或人工验收",
    record_reason: "隔离维护页部分成功回归",
    sensitivity: "internal",
    discovery: "owner_only",
    payload: {
      unit_type: "method",
      run_ref: null,
      evidence_refs: [],
      figures: [],
      missing_refs: [],
      retrieval_description: {
        question: "检查维护状态",
        method: "合成固定正文",
        key_findings: ["仅供软件检查"],
        applicable: ["隔离浏览器"],
        not_applicable: ["现实结论"],
        limitations: ["未执行实验"],
      },
      blocks: [
        {
          block_id: "method",
          role: "methods",
          markdown: "合成正文：保留完整回执。",
          requires_block_ids: [],
        },
      ],
    },
  };
  const initial = await memory("inspect", { owner_id: owner });
  const committed = await memory("commit", {
    schema_version: 1,
    request_id: crypto.randomUUID(),
    owner_id: owner,
    expected_head: initial.head.commit_id,
    actor: { kind: "workflow", id: "synthetic-partial-browser-test" },
    operations: [{ op: "put_record", client_key: "partial-unit", draft }],
  });
  expect(committed.save_status, JSON.stringify(committed)).toBe("committed");
  const recordId = committed.record_results[0].record_id;
  // Saving canonical content can truthfully leave indexes pending. Explicitly
  // reconcile the synthetic input before testing indexed candidate discovery.
  const reconcileRequest = testInfo.outputPath("reconcile-request.json");
  await writeFile(reconcileRequest, JSON.stringify({ vector: "off" }));
  const reconciled = spawnSync(
    resolve(root, "services/qdrant/runtime/python.exe"),
    [
      resolve(root, "automation/scripts/workspace_cli.py"),
      "--root",
      fixtureRoot,
      "memory",
      "reconcile",
      "--request",
      reconcileRequest,
    ],
    {
      cwd: root,
      windowsHide: true,
      encoding: "utf8",
      timeout: 60000,
      env: {
        ...globalThis.process.env,
        PYTHONUTF8: "1",
        PYTHONIOENCODING: "utf-8",
      },
    },
  );
  await testInfo.attach("input-reconcile", {
    body: reconciled.stdout + reconciled.stderr,
    contentType: "text/plain",
  });
  expect(reconciled.status, reconciled.stdout + reconciled.stderr).toBe(0);
  await page.goto(base + "#/materials");
  // owner_only records intentionally do not appear in unscoped global search.
  // Select the record's owner explicitly through the public scope controls.
  await page.getByText("高级范围与查询约束", { exact: true }).click();
  await page
    .getByLabel("归属对象（逗号分隔，留空表示空集合）", { exact: true })
    .fill(owner);
  await page.getByLabel("问题", { exact: true }).fill(recordId);
  await page.getByRole("button", { name: "开始查询", exact: true }).click();
  const candidate = page
    .getByTestId("material-candidate")
    .filter({ hasText: marker });
  await candidate.getByRole("checkbox").check();
  await page.getByRole("button", { name: /生成维护任务包/ }).click();
  const editor = page.getByLabel("审查结果 JSON", { exact: true });
  await expect(editor).toBeVisible();
  const plan = JSON.parse(await editor.inputValue());
  expect(plan.read_receipt).toBeTruthy();
  expect(
    plan.context_items.some((part: { markdown: string }) =>
      part.markdown.includes("保留完整回执"),
    ),
  ).toBe(true);
  // This is an explicitly labelled software fixture declaration. The separate
  // A09 actual-AI run is the evidence for real semantic reading and decisions.
  const revised = structuredClone(draft);
  revised.payload.blocks[0].markdown +=
    "\n\n合成修订：规范提交后继续显示索引待办。";
  const reviewedInput = {
    ...plan,
    reviewer_kind: "ai",
    semantic_reviewer: "SYNTHETIC browser fixture; not actual AI assessment",
    review_note:
      "SYNTHETIC 状态回归，仅验证固定回填与提交；不构成人工或科学复核。",
    reviewed_refs: [
      ...new Map(
        plan.context_items
          .flatMap((part: { refs: object[] }) => part.refs)
          .map((ref: object) => [JSON.stringify(ref), ref]),
      ).values(),
    ],
    items: plan.items.map((item: { ref: { id: string } }) =>
      item.ref.id === recordId
        ? {
            ...item,
            action: "revise",
            reasons: ["合成状态回归追加一段正文"],
            draft_json: JSON.stringify(revised),
          }
        : item,
    ),
  };
  await editor.fill(JSON.stringify(reviewedInput));
  const reviewResponse = page.waitForResponse((response) =>
    response.url().endsWith("/materials/maintenance-review"),
  );
  await page
    .getByRole("button", { name: "校验回填与固定依据", exact: true })
    .click();
  const reviewed = await (await reviewResponse).json();
  expect(reviewed.status, JSON.stringify(reviewed)).toBe("partial");
  expect(reviewed.code).toBeNull();
  const apply = page.getByRole("button", {
    name: "应用已审查变更",
    exact: true,
  });
  await expect(apply).toBeVisible();
  await page.getByRole("checkbox", { name: /我已核对当前变更预览/ }).check();
  const applyResponse = page.waitForResponse((response) =>
    response.url().endsWith("/materials/maintenance-apply"),
  );
  await apply.click();
  const outcome = await (await applyResponse).json();
  expect(outcome.status, JSON.stringify(outcome)).toBe("partial");
  expect(outcome.code).toBeNull();
  expect(outcome.value.commits).toHaveLength(1);
  expect(outcome.value.index_status).toBe("pending");
  await expect(apply).toHaveCount(0);
  const receipt = page.getByRole("region", {
    name: "维护提交回执",
    exact: true,
  });
  await expect(receipt).toContainText("索引状态：pending");
  await expect(receipt).toContainText(outcome.value.commits[0][1]);
  const current = await memory("inspect", { owner_id: owner });
  expect(current.records[recordId].revision).toBe(2);
  expect(current.records[recordId].payload.blocks[0].markdown).toContain(
    "继续显示索引待办",
  );
  await testInfo.attach("partial-review-and-apply", {
    body: JSON.stringify(
      { reviewed, outcome, current_record: current.records[recordId] },
      null,
      2,
    ),
    contentType: "application/json",
  });
  await receipt.scrollIntoViewIfNeeded();
  await page.screenshot({
    path: testInfo.outputPath("material-maintenance-partial.png"),
    fullPage: false,
  });
});
