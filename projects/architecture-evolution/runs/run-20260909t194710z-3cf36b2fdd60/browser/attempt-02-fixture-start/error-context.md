# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: material-query.spec.ts >> 材料查询真实HTTP组装四区、固定依据与来源映射
- Location: e2e\material-query.spec.ts:77:1

# Error details

```
Error: 材料查询沙盒退出 1：Traceback (most recent call last):
  File "D:\��������\A_work\A_work_auto_flow\automation\tests\serve_memory_test.py", line 94, in <module>
    main()
  File "D:\��������\A_work\A_work_auto_flow\automation\tests\serve_memory_test.py", line 23, in main
    fixture = materialize(Path(temporary)/"���� ����ɳ��", isolation_root=temporary)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "D:\��������\A_work\A_work_auto_flow\automation\tests\memory_fixture.py", line 247, in materialize
    generated.rename(path.parent)
  File "pathlib.py", line 1363, in rename
PermissionError: [WinError 5] �ܾ����ʡ�: 'D:\\��������\\A_work\\A_work_auto_flow\\.local\\memory-browser-qtuav7tt\\���� ����ɳ��\\core-algorithms\\synthetic-18' -> 'D:\\��������\\A_work\\A_work_auto_flow\\.local\\memory-browser-qtuav7tt\\���� ����ɳ��\\core-algorithms\\�ϳ��㷨'

```

# Test source

```ts
  1   | import { test, expect as baseExpect, type Page } from "@playwright/test";
  2   | import { spawn, type ChildProcess } from "node:child_process";
  3   | import { resolve } from "node:path";
  4   | 
  5   | // Exercise the installed workbench assets and real HTTP coordinator against a
  6   | // disposable Chinese-path workspace. No real business owner or source is read.
  7   | const root = resolve("../..");
  8   | const expect = baseExpect.configure({ timeout: 30000 });
  9   | let process: ChildProcess;
  10  | let base: string;
  11  | test.describe.configure({ timeout: 180000 });
  12  | test.use({ actionTimeout: 30000 });
  13  | test.beforeAll(async () => {
  14  |   process = spawn(
  15  |     resolve(root, "services/qdrant/runtime/python.exe"),
  16  |     [resolve(root, "automation/tests/serve_memory_test.py")],
  17  |     { cwd: root, windowsHide: true, stdio: ["ignore", "pipe", "pipe"] },
  18  |   );
  19  |   await new Promise<void>((done, fail) => {
  20  |     let output = "";
  21  |     const timeout = setTimeout(() => {
  22  |       process.kill();
  23  |       fail(Error("材料查询沙盒启动超时：" + output));
  24  |     }, 150000);
  25  |     process.stdout!.on("data", (chunk) => {
  26  |       output += chunk;
  27  |       for (const line of output.split("\n"))
  28  |         try {
  29  |           const value = JSON.parse(line);
  30  |           if (value.url) {
  31  |             base = value.url;
  32  |             clearTimeout(timeout);
  33  |             done();
  34  |             return;
  35  |           }
  36  |         } catch {
  37  |           /* Keep startup diagnostics until a complete JSON line arrives. */
  38  |         }
  39  |     });
  40  |     process.stderr!.on("data", (chunk) => {
  41  |       output += chunk;
  42  |     });
  43  |     process.on("exit", (code) => {
  44  |       clearTimeout(timeout);
> 45  |       fail(Error(`材料查询沙盒退出 ${code}：${output}`));
      |            ^ Error: 材料查询沙盒退出 1：Traceback (most recent call last):
  46  |     });
  47  |   });
  48  | });
  49  | test.afterAll(() => process?.kill());
  50  | test.afterEach(async ({ page }, testInfo) => {
  51  |   if (testInfo.status !== testInfo.expectedStatus) {
  52  |     await page.screenshot({
  53  |       path: testInfo.outputPath("material-query-failure.png"),
  54  |       fullPage: true,
  55  |     });
  56  |     await testInfo.attach("visible-page", {
  57  |       body: await page.locator("body").innerText(),
  58  |       contentType: "text/plain",
  59  |     });
  60  |   }
  61  | });
  62  | 
  63  | async function search(page: Page) {
  64  |   await page.goto(base + "#/materials");
  65  |   await expect(
  66  |     page.getByRole("heading", { name: "材料查询", exact: true }),
  67  |   ).toBeVisible();
  68  |   await page.getByRole("button", { name: "全局获准范围", exact: true }).click();
  69  |   await page.getByLabel("问题", { exact: true }).fill("SYNTHETIC");
  70  |   await page.getByRole("button", { name: "开始查询", exact: true }).click();
  71  |   await expect(page.getByTestId("material-candidate").first()).toBeVisible();
  72  |   await expect(
  73  |     page.getByRole("button", { name: "开始查询", exact: true }),
  74  |   ).toBeEnabled();
  75  | }
  76  | 
  77  | test("材料查询真实HTTP组装四区、固定依据与来源映射", async ({
  78  |   page,
  79  | }, testInfo) => {
  80  |   const errors: string[] = [];
  81  |   page.on("pageerror", (error) => errors.push(String(error)));
  82  |   await search(page);
  83  |   const first = page.getByTestId("material-candidate").first();
  84  |   await first.getByRole("checkbox").check();
  85  |   const assemblyResponse = page.waitForResponse((response) =>
  86  |     response.url().endsWith("/materials/assemble"),
  87  |   );
  88  |   await page
  89  |     .getByRole("button", { name: "组装所选材料（1）", exact: true })
  90  |     .click();
  91  |   const assembled = await (await assemblyResponse).json();
  92  |   expect(["ok", "partial"]).toContain(assembled.status);
  93  |   expect(assembled.value).toBeTruthy();
  94  |   const packet = page.getByRole("region", { name: "材料包", exact: true });
  95  |   for (const title of ["直接材料", "必要上下文", "关联建议", "缺口与限制"])
  96  |     await expect(
  97  |       packet.getByRole("region", { name: title, exact: true }),
  98  |     ).toBeVisible();
  99  |   await page.getByText("沿所选材料深化", { exact: true }).click();
  100 |   const deepenedResponse = page.waitForResponse((response) =>
  101 |     response.url().endsWith("/materials/deepen"),
  102 |   );
  103 |   await page.getByRole("button", { name: "深化所选材料", exact: true }).click();
  104 |   const deepened = await (await deepenedResponse).json();
  105 |   expect(["ok", "partial"]).toContain(deepened.status);
  106 |   await expect(page.getByText(/关系边：/)).toBeVisible();
  107 |   await page.evaluate(() => window.scrollTo(0, 0));
  108 |   await page.screenshot({
  109 |     path: testInfo.outputPath("material-query-desktop.png"),
  110 |     fullPage: false,
  111 |   });
  112 |   await page.setViewportSize({ width: 760, height: 1000 });
  113 |   await page.evaluate(() => window.scrollTo(0, 0));
  114 |   await page.screenshot({
  115 |     path: testInfo.outputPath("material-query-narrow.png"),
  116 |     fullPage: false,
  117 |   });
  118 |   expect(
  119 |     await page.evaluate(
  120 |       () => document.documentElement.scrollWidth <= window.innerWidth,
  121 |     ),
  122 |   ).toBe(true);
  123 |   expect(errors).toEqual([]);
  124 | });
  125 | 
  126 | test("维护任务包导出保留未审状态，改变条件使旧候选失效", async ({ page }) => {
  127 |   const applyCalls: string[] = [];
  128 |   page.on("request", (request) => {
  129 |     if (request.url().endsWith("/materials/maintenance-apply"))
  130 |       applyCalls.push(request.url());
  131 |   });
  132 |   await search(page);
  133 |   await page
  134 |     .getByTestId("material-candidate")
  135 |     .first()
  136 |     .getByRole("checkbox")
  137 |     .check();
  138 |   await page.getByRole("button", { name: /生成维护任务包/ }).click();
  139 |   const editor = page.getByLabel("审查结果 JSON", { exact: true });
  140 |   await expect(editor).toBeVisible();
  141 |   const plan = JSON.parse(await editor.inputValue());
  142 |   expect(plan.reviewed_refs).toEqual([]);
  143 |   expect(plan.semantic_reviewer).toBeNull();
  144 |   const downloaded = page.waitForEvent("download");
  145 |   await page
```