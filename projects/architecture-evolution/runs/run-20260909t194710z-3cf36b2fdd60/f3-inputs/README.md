# 独立合成 F3 与实际 AI 使用

本目录保存三份明确标记为 SYNTHETIC 的前提输入：水箱连续负反馈、API 退避重试和无旧边的新执行器饱和约束。它们由本次执行 AI 独立撰写，没有复制 F1 配方的语义标签，没有公司原件或真实实验数据。

[manifest.json](manifest.json) 固定了隔离 workspace、owner、原件 SHA256、规范记录 r1 与初始索引回执。它是 bootstrap 身份台账，不是 AI 语义验收答案。水箱的定义与模型分别为 L1，章节固定组合二者；重试与饱和各有独立 owner，饱和没有引用任何旧记录。

规范记录全部由 [f3-setup.py](../f3-setup.py) 调用公开 `memory validate-draft/commit/inspect` 创建，未写入 HEAD 或权威快照。owner 原生卡片、三份合成原件与来源登记是明确的隔离 bootstrap。路径位于正式 workspace 的 `.local/testing/material-query-f3-20260910-actual/workspace`，不代表真实项目。

## 保留的初始失败与限制

- 初次保存实际已经 committed，但返回向量 `INDEX_PENDING`。捕获脚本起初把非零退出统一当作中断；回执原样保留在 `setup-calls/tank-definitions-commit`。续接时沿用该真实记录，并未重复提交。
- `tank-model-validate` 的草案曾使用不合法的块 role `analysis`，公开验证返回 `INVALID_SCHEMA`，未提交。更正为登记的 `methods` 后，在 `tank-model-v2-*` 保存独立调用记录。未删除或改写失败回执。
- 公开 `memory reconcile` 显式关闭向量后，文本索引 indexed。本地没有自动下载或配置模型。
- 查询捕获辅助脚本第一次处理 definitions 的数组返回值时出现投影错误。公开 definitions 调用已经成功并保存在 A07；修正投影后沿用原调用。随后由于并行产品修改，试图重写初始源码指纹被拒绝；初始元数据保留，新调用另记当时源码指纹。两次均为本 Run 辅助脚本问题，没有伪造产品执行结果。

## 实际阅读与自查

[attempts.json](attempts.json) 指向 A07/A08 的真实公开调用与当时交付文本。`execute-queries.py` 只捕获请求、运行结果并投影返回 Markdown，不生成 AI 判断。AI 在工具中实际读完这些文本后，单独写入两份 `AI-ANALYSIS.md`，再保存阅读声明与逐项自评。

A07 覆盖摘要、全文、排除必要定义、needs_generation 和预算省略。A08 比较双方完整正文后形成条件参考和不可推广结论，通过公开入口保存 candidate 导航；具体回执位于 A08。父任务后续复用饱和输入执行 A09，初始 r1 仍以此目录固定。

输入与比较由同一 AI 在连续上下文中完成，不能称为盲测或独立科学复核。人工审查待处理，科学复核未进行。
