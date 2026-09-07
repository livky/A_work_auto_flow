# 材料关系工作台

运行 `workbench.cmd`，或已注册的 `rdwork`。选择“材料关系”，首次构建视图。图读取已登记材料与现有证据，分析只保存本机派生结果。

## 浏览与分析

1. 搜索材料，点击条目查看详情，选择“以此为中心”。默认一跳，可切换两跳；“返回上个中心”恢复上次焦点。
2. 问题辐射按材料类别排列；主题聚合将当前范围折叠成块，点击块或聚合连线展开；证据链仅显示有对应含义的关系。列表保留多重归属；重叠成员在画布按首个分组定位。
3. 点击原始连线查看关系类型、原字段、方向、定位及版本。箭头表示起点引用或关联终点，不能据箭头认定因果。红色风险、执行状态、复核状态分别查看。
4. “本次排除”同时限制扩展和导出。画布最多 300 个原始节点、1,000 条边，超限显示数量并支持分页。主题列表显示全局成员计数；展开后仍受局部上限约束。
5. 拖动、缩放及自定义分组属于展示设置；“保存视图”保存位置、中心、模式、分组和排除项，“重置布局”重排。分组展开状态保留在当前页面。
6. 勾选最多 50 个种子，按需运行共享关键词或本地语义相似；打开“显示候选”叠加虚线。每个种子最多 10 个近邻。关键词只取已登记关键词与别名；语义只查询当前本地索引，不自动下载模型或重建索引。
7. 结构聚类和候选聚类分别使用显式连接及候选连接；默认覆盖当前局部范围。“全范围结构聚类”在 Worker 中计算未排除材料，避免渲染全部节点。Louvain 固定分辨率 1、随机种子 173；社区不表示业务分类已成立。

语义分析必须已有完整配置和索引；缺失时先查看 `rdwork doctor`，必要时按已授权材料运行 `rdwork index-knowledge`。查询与独立索引进程冲突会报告忙碌，不删除存储锁。长材料最多均匀采样 8 个片段，结果记录覆盖与遗漏，分数不能作为模型有效性或证据可信度。

## AI 协作与候选

“复制关联摘要”和“导出 JSON”只导出当前选中的局部范围，包含问题、ID、来源、指纹、状态、方向及缺口，默认不包含全部正文。聚类另有完整导出，包含成员及源引用，可在当前 AI 会话中命名主题或提出跨组问题。

AI 回传单条 JSON，字段为 `kind`（`relation`、`cluster-name`、`bridge-question`）、`title`、`explanation`、`actor`、`refs`。每个引用必须携带真实 `id`、生成时的 64 位 SHA-256 `fingerprint` 和 `locator`。不能用展示 ID（`VIEW-GROUP:`）代替材料身份。

```json
{
  "kind": "relation",
  "title": "待核对的关联",
  "explanation": "说明具体共同条件、冲突或需要补读的证据",
  "actor": "assistant-observation",
  "refs": [{"id": "从摘要复制实际 ID", "fingerprint": "从摘要复制实际 SHA-256", "locator": "从来源复制章节或行号"}]
}
```

上例是字段说明，占位符不能直接导入。导入后默认待处理；可驳回、标记已处理或恢复待处理，操作保留处理者、时间和说明。“已处理”不等于结论已复核。未过期的主题名称建议可应用为展示分组；正式记录仍通过研究、Run 与证据流程登记。

## CLI

所有命令共用工作台服务层，无需打开网页。将实际材料 ID 替换下面占位符。

```powershell
rdwork relations refresh --dry-run
rdwork relations refresh
rdwork relations view --center "实际 ID" --hops 2 --exclude "排除 ID"
rdwork relations export --center "实际 ID" --question "具体问题" --format markdown
rdwork relations analyze keywords --seed "实际 ID"
rdwork relations analyze semantic --seed "实际 ID"
rdwork relations import-candidate ".\候选.json" --dry-run
rdwork relations import-candidate ".\候选.json"
rdwork relations candidates
rdwork relations resolve "候选 ID" --status handled --actor user --note "已检查的内容与限制"
rdwork relations --root "D:\研发\工作区" refresh
```

查看和导出默认 JSON，`--format markdown` 可输出文本；解析或边界错误返回非零退出码。写入前可用 `--dry-run` 预览；候选处理通过新增历史恢复，布局通过重新保存恢复。

## 状态、迁移与限制

`.local/workbench/` 保存 `projection.json`、`analysis.json`、`clusters.json`、`view.json`、`candidates.json` 和 `jobs.json`。它们排除 Git、离线包和正式检索；原位升级保留 `.local`。跨机候选用已检查的 JSON 单条导入，不依赖携带派生索引。清除缓存时只移除可重建的投影/分析/聚类文件，保留候选与偏好。

页面每 30 秒对已知文件做轻量变更检查；新增文件及登记变化用“检查版本”或刷新发现。版本变化会提示缓存过期，来源预览重新核对当前指纹；AI 候选的版本失效独立判断。任务失败保留上次完整缓存；取消在安全批次边界生效。退出服务后的未完成任务标记中断，不自动恢复执行。

界面适用于当前 Edge/Chrome。性能证据与全部验证结果见 [固定验证 Run](../runs/run-20260907t071646z-ce49506865c4/README.md)。合成数据只能验证软件行为，真实研发有效性需要实际材料与问题检验。
