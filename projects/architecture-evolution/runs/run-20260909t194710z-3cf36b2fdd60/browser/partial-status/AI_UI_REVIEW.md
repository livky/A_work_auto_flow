# 维护页有效 partial 的修复与实际浏览器检查

执行者：Codex `/root/retrieval_review`；AI 自查，人工验收待审。软件回归使用独立 SYNTHETIC 沙盒，实际语义阅读证据另见本 Run 的 A09，不将脚本回填计作实际 AI 语义审查。

## 真实故障与修复

A09 的公开维护审查有效，但服务器为保留科学复核限制返回 `status=partial, code=null`。界面原先仅接受 `ok`，无法进入应用。现在接受带有效值、无错误码的 `ok/partial` 审查；采用服务器返回的摘要。规范写入成功但索引仍 pending 时关闭本次提交按钮，保留全部提示、提交身份、恢复回执与待办。带错误码的 partial 不被视为完成，重试继续复用原请求身份。

## 实际验证

- 组件回归 **14/14 通过**，新增三项覆盖有效 partial 审查/提交、带错误码的 partial 审查拒绝、部分提交失败的同身份重试；[原始 JSON](final/component-tests.json)。
- contracts 生成、TypeScript 检查、Vite 构建通过。构建仍提示既有大 chunk 警告，无构建错误。
- 真实 Microsoft Edge 浏览器 **4/4 通过**，开始时间 `2026-09-09T21:36:15Z`，耗时约 20.4 秒；[原始 JSON](final/playwright.json)。
- 新用例经公共 memory HTTP 事务建立 v3 合成正文，显式文本 reconcile，页面限定 owner_only 的所属对象，再填入清楚标记为软件 fixture 的审查 JSON。真实 review 与 apply 均返回 `partial, code=null`，回读规范修订 **r2**；提交按钮关闭，索引 pending 与 COM 仍可见。[公开返回及规范读回](final/partial-review-and-apply.json)。
- 当前构建来源指纹为 `ba0aea49856d5f912fb3ca16516c7a33817c945674abb3c05790e07d42f04548`。[来源与资源清单](final/asset-manifest.json)，[本次证据哈希](final/artifact-hashes.json)。

## 实际视觉检查

我逐张实际打开并检查了以下四张最终截图，未仅按测试成功推断布局。

- [维护部分完成](final/material-maintenance-partial.png)：部分完成的警示、索引 pending、提交 COM、待处理状态和恢复回执可读；应用按钮已关闭。JSON 预览保持可滚动，没有覆盖提示与回执。
- [1440 像素桌面](final/material-query-desktop.png)：结构、查询和材料包三栏排列正常；正文、表格与公式可读。
- [760 像素窄屏](final/material-query-narrow.png)：按顺序单列排列，结构树高度受限，实际脚本验证无水平溢出。
- [登记路径视图](final/material-query-storage.png)：选中位置显示实际受控登记路径，树与查询栏未重叠。

## 保留的失败和边界

1. [attempt01](playwright-attempt01.json)：原三项通过，新用例未找到刚提交的记录。该记录索引 pending，且 discovery 为 owner_only；初始测试使用全局范围，两项测试准备均不充分。
2. [attempt02](playwright-attempt02.json)：修改 e2e 后未重建来源指纹，真实服务拒绝启动；按真实拒绝保留，未跳过指纹核验。
3. [attempt03](playwright-attempt03.json)：文本 reconcile 成功后，全局范围仍不能发现 owner_only 记录。改为通过页面明确选择所属对象，保留产品范围边界。
4. [attempt04](playwright-attempt04.json)：完整四项通过，并复制为 final；原失败没有覆盖或改写。

README 已复查，材料查询与维护手册入口仍适用。本次仅修复既有状态生命周期，无新增安装依赖；资源已预构建，接收端不需要 Node。本证据只代表本机 Windows x64 隔离软件回归，不代表第二台物理机、真实业务、人工或科学验收。
