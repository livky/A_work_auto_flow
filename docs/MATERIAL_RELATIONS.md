# 材料关系工作台

现行说明核对日期：2026-09-09。材料关系页、规范记忆关联与检索上下文是相互配合的入口，保存位置及扩展行为不同，不能把画布连接直接当作证据或默认召回结果。

运行 `workbench.cmd`，或已注册的 `rdwork`。选择“材料关系”，首次构建视图。图读取已登记材料与现有证据，分析只保存本机派生结果。

## 浏览与分析

1. 搜索材料，点击条目查看详情，选择“以此为中心”。默认一跳，可切换两跳；“返回上个中心”恢复上次焦点。
   搜索框下以小勾选项列出核心算法、实验、研究、结论等大类，支持多选，同时展示所选类别的材料；不勾选分类时显示全部，可与搜索叠加。勾选材料后，关系图实时显示所有勾选材料及其一跳／两跳关联，导出和局部聚类使用相同范围。切换列表分类保留材料勾选；“清空勾选”恢复全部材料。“以此为中心”则清空多选，切换为单材料聚焦。
2. 问题辐射按材料类别排列；主题聚合将当前范围折叠成块，点击块或聚合连线展开；证据链仅显示有对应含义的关系。列表保留多重归属；重叠成员在画布按首个分组定位。
3. 点击原始连线查看关系类型、原字段、方向、定位及版本。箭头表示起点引用或关联终点，不能据箭头认定因果。红色风险、执行状态、复核状态分别查看。
4. “本次排除”同时限制扩展和导出。画布最多 300 个原始节点、1,000 条边，超限显示数量并支持分页。主题列表显示全局成员计数；展开后仍受局部上限约束。
5. 拖动、缩放及自定义分组属于展示设置；“保存视图”保存位置、中心、模式、分组和排除项，“重置布局”重排。分组展开状态保留在当前页面。
6. 勾选最多 50 个种子，按需运行共享关键词或本地语义相似；打开“显示候选”叠加虚线。每个种子最多 10 个近邻。关键词只取已登记关键词与别名；语义只查询当前本地索引，不自动下载模型或重建索引。
7. 结构聚类和候选聚类分别使用显式连接及候选连接；默认覆盖当前局部范围。“全范围结构聚类”在 Worker 中计算未排除材料，避免渲染全部节点。Louvain 固定分辨率 1、随机种子 173；社区不表示业务分类已成立。

当前页面默认选择 L1；可按需选择 L2、L3、L4 与原生对象范围。L1 是完整技术单元，L4 是研究知识地图；新完整过程与简版文稿是 level=null 的独立 document/document_section，不作为第五层或自动加入本页的 L1–L4 投影。Run 的物理目录可以在对象内，图使用稳定身份与固定引用，目录搬移不构成新的实验。

本页的语义分析必须已有完整配置和文件索引；缺失时先查看 `rdwork doctor`，必要时按已授权材料运行 `rdwork index-knowledge`。它查询既有 `workspace_*` 文件片段集合，不重新编码全部记忆，也不是 `memory search` 的向量召回。查询与独立索引进程冲突会报告忙碌，不删除存储锁。长材料最多均匀采样 8 个片段，结果记录覆盖与遗漏；尚无当前文件片段向量的材料会报告缺口。分数不能作为模型有效性或证据可信度。

## 规范记忆关联与自动扩展

| 机制 | 保存与读取 | 含义 |
|---|---|---|
| 材料画布及 AI 回传建议 | `relations` 命令，`.local/workbench/` | 本机展示与待处理候选；handled 只是处理记录 |
| 规范导航关联 | `memory associations-propose/decide/view`，对象不可变记忆修订 | 固定两端版本、关系说明和迁移限制；可 accepted/rejected，源变化后显示过期 |
| 证据依赖 | 原业务 claims/dependencies 与记忆固定 Ref | `supports/input` 参与证据准入和失效检查；不是相似度建议 |

记忆关联请求示例见 [版本记忆指南](MEMORY_USAGE.md)。关键词提议采用共享词 Jaccard，默认至少两个共有词且分数不低于 0.3；语义提议当前重新编码可见记录的 `body_markdown` 并计算余弦，默认阈值 0.8。它尚未统一复用 v3 技术块的记忆向量，与本页的片段采样算法不同；块式记录和长正文的关联覆盖需单独验证，不能混用阈值或声称已有同样的规模限制。提议不直接成为科学支持，`associations-decide` 也拒绝把导航关系写为 supports/input。

普通 `memory context` 返回选中材料的一跳导航元数据，后续可按固定 Ref 展开；默认不会自动遍历所有已接受关联并追加正文。当前 `complete_graph_context` 评估方案额外调用有界关联扩展，最多两跳的遍历函数及其评估结果不等于默认生产查询已经采用。前端画布的两跳范围同样只控制展示与导出。检索入口、预算与回执区别见 [检索手册](RETRIEVAL.md)。

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

下列 `relations` 命令共用材料工作台服务层，无需打开网页；它们不代替规范记忆的 `memory associations-*` 接口。将实际材料 ID 替换下面占位符。

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

界面适用于当前 Edge/Chrome。性能证据与全部验证结果见 固定验证 Run（历史记录已从 main 移除，原路径：`../runs/run-20260907t071646z-ce49506865c4/README.md`）。合成数据只能验证软件行为，真实研发有效性需要实际材料与问题检验。
