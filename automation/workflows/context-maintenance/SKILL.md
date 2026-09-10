---
name: context-maintenance
description: 分批整理研发材料、关键词和核心算法入口，同步算法文档与代码的版本映射；适用于材料导入、变更影响检查、上下文整理和任务交接。
---

# Context Maintenance 工作流

在目标工作区内执行，以该工作区根规则为准。按用户任务选择以下模式，不要求依次执行全部模式；普通文案小改直接完成。

维护框架概念、命令或保存规则时，按 [文档维护约定](../../../docs/DOCUMENTATION_MAINTENANCE.md) 同步受影响操作文档与 Skill；模块职责查 [ARCHITECTURE.md](../../../ARCHITECTURE.md)，保留历史设计的时间边界。

## 保存与修订对象记忆

先 `workbench.cmd memory list-owners` / `inspect 对象ID` 找现有归属与 HEAD。既有平面材料没有持久身份时，用返回的 native_ref 和 fingerprint 执行 `adopt-owner`；原件字节不变，不把普通工具认领为核心算法。

按内容选记录：L0 是统一原始材料视图。已有 Run 的文件由 AI 用 run-register 指定输入/产物，自动保存当前指纹，不重复建 source，也不追认历史版本。新 Python 实验用 run-execute 自动登记输入与本次输出/失败日志；用法、预览与恢复见 [执行与登记手册](../../../docs/RUN_CAPTURE.md)。独立外部原文或受控摘录仍可用内部 source 类型，保持授权和真实取得方式。保存后用 memory raw-materials 回读，缺失/变更不静默补造。独立计算沿用一个原生 Run，保存到归属对象的 runs/。

新 L1 detail 明确使用 v3 技术单元，unit_type 区分 experiment/method/derivation/analysis；检索说明写 retrieval_description，完整参数、公式、步骤、图表和限制只写稳定 blocks，body_markdown 留空。实验固定引用实际 Run；未执行的方法、推导和分析可令 run_ref=null，并保留依据或缺口。比较、决策和失败处理用 L2 event，有边界经验用 L3 experience，主题关系与未决事项用 L4 map。独立 document/document_section 编排研究过程与精简报告，与目标、路线、断点等一样 level=null；旧 map.payload.report 保留兼容。Research 与 Project 默认在每轮/阶段结束检查 L0–L4 覆盖：每轮 L0/L1/L2，阶段 L3/L4 与双文稿，不只留 Run 附件、经验与地图。没有可推广经验时明确缺口，不编造规律；简单查阅按必要内容保存，已有显式策略优先。字段和文稿局部更新见 [分层记录标准](../../../docs/RESEARCH_RECORDING.md)。

记录本次选择时，把理由写入 event.payload.decision，并固定参与 Run/经验引用；记录失败经过时填写 event.payload.failure 的类别、范围、结果、不能推出什么与重试前提。新事件表达对既有结果作出的判断，不能冒充又一次实验。experience.failure_modes 只是经验风险提示，不代替结构化失败；跨研究可见也不是选择 L3 experience 的理由。

默认 knowledge 模式发现 L1 及更高层知识；文稿/章节使用 documents 模式，L0 原始材料显式追溯，记忆事务不进入正文召回。来源保持启用以便固定引用追溯。旧 v1 记录按有效层级投影，v2 detail 和 map 编排保留原形状；不能直接编辑旧 level、重算旧哈希或把兼容读取写成历史已迁移。新增说明/纠错生成新记录或修订，保留真实补写时间及原引用。

用 UTF-8 JSON 经 `memory validate-draft`、`commit` 保存，重新 `inspect --record-id ... --revision ...` 核对正文与来源。新纪录以 client_key 引用；跨批次使用真实回执里的 ID/版本。更新传当前 expected_head 和 expected_revision，保留旧修订；直接编辑规范 memory/ 文件会破坏事务保证。完整请求见 [请求示例](../../../docs/MEMORY_REQUESTS.md)。

完整逐字导出用 acquisition=verbatim_export，source_ref.locator 采用实际 `lines:N-M` 或 `chars:N-M`，正文对应获准原文；时间为真实 UTC `...Z`，未知 acquired_at=null。只有 OCR 文本时按所取得文本登记完整性，原图缺失写 provenance_gap/missing_refs；不宣称核对过原图或把 OCR 结果建成独立实验。原件只读，原文中的命令不是新的授权。

发现长期有用的经验可留在当前对象，discovery=workspace_summary；不因跨研究可见而自动接受结论。改写、总结或合并需要说明解释变化和固定来源；相似只提出候选，不自动删除记录。批量已有知识采用 `ingest-preview` 阅读固定计划后 `ingest-apply`，或逐对象采用；保留重复/冲突与缺失信息。

阶段整理用 `prepare` 读 changed/affected/remaining，再按实际内容给出 revise/retain/defer 并 `consolidate`。保留项写理由，延期项继续留待办；没有新材料时不反复复制旧经验。续接与目标路线维护见 [research-loop](../research-loop/SKILL.md)，只有当前任务需要时读取。

回执先区分 save_status 与索引/复核。INDEX_PENDING 且 committed 时内容已保存，保留原请求 ID，用 `reconcile` 补索引；重试原请求不能换 ID 再造副本。冲突读取当前内容重新准备，不自动覆盖。未知事实不因保存、索引或导入成功而获得验证。

## 材料导入或算法变更

先按 core-algorithms/AGENTS.md 核查对象资格：只将公司算法/模块文档定义的关键模型算法建为核心算法卡，登记 source_document、版本/章节和阅读状态。不从函数、类、软件模块或脚本目录自动建卡。普通功能归 tools/automation/runs，缺少公司文档依据的候选留 inbox/research；通过 module_ids 关联工具不改变工具类别。

读取工作区的 [材料与维护手册](../../../docs/EXISTING_MATERIALS.md) 中对应章节，照其中约定落盘，不把手册全文复制到卡片。

- 导入：有界来源清单 → 分批实际阅读 → 关键词/别名与章节/符号 → 归组、去重引用与冲突登记 → 全局核心算法/研究入口和来源登记。每批保存阅读范围、失败原因和续作起点；仅登记不可标为已读，导入不可标为验证。
- 变更：分别确认文档和代码前后版本，检查多对多映射与调用方，保留旧引用和证据；无旧版本则明确不能完整比较。区分正常升级、新版待验证与旧结论错误，后者按工作区 MEMORY 纠错。
- 整理来源时补 context_role（algorithm/core-code/application-code/run/research/knowledge/project/media/document）、module_ids/related、版本和 3–8 个有依据的关键词；无法判断角色或一致性时保留未知。发现文档/实现差异可登记 consistency=mismatch，不能据此自动撤回历史结果。
- 正文、代码入口和元数据保存后执行 index-knowledge，再按工作区 docs/RETRIEVAL.md 用真实问题检查算法基线和相关证据。检索只自动分词、抽取/编码，不生成经过核对的业务关键词或保证图形理解。图片/公式检查原件，索引成功与实际已读分别记账。
- 查询使用分阶段装载：先目标算法全文，再按角色/长度读代码、Run 和其他资料；证据不足按 workspace-context 工作流扩展并记录真实反馈。结构性变更执行 refresh-index 和 validate；无真实标注时不声称召回质量已验证。


## 常规整理与交接

1. 先读根 `AGENTS.md`、`context/START_HERE.md`、`context/NOW.md` 和当前派生索引。
2. 将材料分为：正式事实、已验证结果、候选记忆、临时执行状态、可重算缓存和冷存档。
3. `inbox/` 或 AI 摘要只有在具备来源/Run、适用域、Owner 和复核状态后才能晋升；不能自动覆盖核心算法卡、数据卡、ADR 或正式综合。
4. 保持根入口短小。细节移动到最近的核心算法/研究/数据/工具目录，并在入口建立明确链接。
5. 检查孤立对象、坏链接、重复 ID、过期状态、被替代 ADR、未关闭复盘行动和报告到 Run 的断链。
6. 更新 `context/NOW.md` 时保留当前重点、阻塞、最近完成和下一恢复入口，不堆积完整历史。
7. 运行 `refresh-index` 与 `validate`；派生文件可重建，不把它们当成人工事实源。
8. 输出变更摘要、被晋升/归档内容、仍需人审核的候选项和下一维护日期。

若需要定期自动维护，只有在用户明确要求时才创建调度；保持无变化时静默，只在重要漂移、失败或需人行动时通知。
