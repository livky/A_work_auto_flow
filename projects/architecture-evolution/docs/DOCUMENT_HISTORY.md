# 文档时间线与架构演进

本页为 `PRJ-ARCHITECTURE-EVOLUTION` 的文档盘点和历史导航。整理日期：2026-09-09；固定工作记录：`RUN-20260909T151004Z-A68FBA9F176D`。它解释设计如何演进，不替代[架构总览](../../../ARCHITECTURE.md)、[研究记录标准](../../../docs/RESEARCH_RECORDING.md)或当前程序契约。

本 Project 在完整 checkout 中保存；公共源码 ZIP 按现行发行规则不包含项目实例。公共使用者仍从随发行的架构总览和当前手册进入。历史 Run、测试附件和本机报告未随源码分发时，本页只保留来源线索，不复造附件，不把文档中的测试数字重新认定为本次通过。

## 如何读日期和状态

本次盘点覆盖 `docs/` 的全部文件，逐份 Markdown 阅读标题、时间/状态声明和章节提纲，重点核读架构演进相关正文。完整文件名、SHA-256、读取时点、正文声明日期、Git 首次/最近提交元数据见[机器清单](document-inventory.json)。清单是工作树读取快照，后续编辑会使其指纹过期。

清单的 `initial_inventory_sha256` 是**文档盘点子任务第一次读取时**的指纹。部分现行手册在该时点已经由并行文档工作修改，因此它不是整个开发任务开始前的用户基线。初始采集的精确时间未单独登记，明确留空；最终采集记录读取窗口和逐文件时点。

- **正文声明日期**：文档明确写出的计划、讨论、审查或更新时点。同一文件可能有多个时点；没有声明就留空。
- **Git 日期**：该文件进入或更新于某次提交的时间。集中提交会把多天工作放在同一天，不能据此认定功能在该日首次实现。
- **整理日期**：本次增加导航说明和核对代码的时间，不回填为历史实施日期。
- **执行结果**：必须由相应固定 Run 支持。验收配方中的 `not-run`、模板中的 `planned` 不应改成后续结果；软件检查、AI 自查、人工审查和科学复核分别成立。

`docs/系统记忆模块开发计划.md` 在初次盘点时是用户既有未跟踪文件，没有正文创建日期或可用 Git 历史。其增加提示前 SHA-256 为 `9a25c521b5fb6c9eed9df283a70853f1338e323e63bea29095da790e22230a76`，与 2026-09-08 技术目标讨论稿保留的原计划指纹一致。这证明当前取得了当时引用的同字节版本，不能证明原计划何时创建。本次仅加入有标记的时点提示；移除该提示后，原正文指纹保持不变。

## 按时间理解演进

| 时间与证据性质 | 主要变化 | 文档入口 | 现在如何使用 |
|---|---|---|---|
| 2026-09-04，正文日期 | 文件化证据、Run、渐进装载与外部数据边界的早期设计依据 | [成熟实践与本地设计](../../../docs/design/ai-assisted-rd-workspace-practices.md) | 保留当时外部实践判断；不把旧产品描述当当前产品保证 |
| 2026-09-06，审查文档日期 | 调整工作流、材料维护、全局对象与本地检索；分阶段上下文；核心算法命名；结论准入及依赖失效；Windows 迁移原型 | [工作流审查](../../../docs/design/workflow-review-2026-09-06.md)、[材料审查](../../../docs/design/materials-review-2026-09-06.md)、[检索审查](../../../docs/design/local-retrieval-review-2026-09-06.md)、[分阶段上下文](../../../docs/design/adaptive-context-review-2026-09-06.md)、[证据准入计划](../../../docs/design/evidence-controls-plan.md) | 阅读当时发现及约束起源；当前用法转入检索、证据和迁移手册 |
| 2026-09-07，NOW 的带日期状态与文档执行记录；部分计划自身无日期 | 证据工作台、只读监测、`setup.cmd`、材料关系视图；依赖分发与扩展旧工作区保护 | [部署计划](../../../docs/design/setup-workbench-plan.md)、[监测计划](../../../docs/design/evidence-view-monitor-plan.md)、[材料关系计划](../../../docs/design/workbench-relations-plan.md)、[依赖分发计划](../../../docs/design/dependency-release-plan.md)、[升级测试](../../../docs/UPGRADE_TESTING.md) | “未发布”“仅本机”等保留为批次状态；不因后续源码提交自动改写验收边界 |
| 日期未声明；2026-09-08 讨论稿引用了同指纹版本 | 早期持续研究、分层记忆与问题驱动检索分析方案 | [原开发计划](../../../docs/系统记忆模块开发计划.md) | 作为目标形成过程中的分析材料；不倒填日期或把其中参数全部当批准需求 |
| 2026-09-08，正文日期 | 确认首版 L0–L3；八类对象复用原身份；统一版本记录；冻结 W00–W13 及 115+18 项验收 | [目标讨论稿](../../../docs/系统记忆模块技术目标讨论稿.md)、[技术实现计划](../../../docs/系统记忆模块技术实现计划.md)、[首版契约](../../../docs/design/system-memory/01-data-contracts.md)、[服务与算法](../../../docs/design/system-memory/02-services-algorithms.md) | 保留首版选择；首版“不设 L4”是当时决定，不覆盖次日经反馈形成的新分层 |
| 2026-09-08 至 09，实施/状态文档声明 | 从首批存储扩展到检索、证据、续接、巩固、工作台及迁移；记录了检索留出质量失败、规模暂缓、人工待审 | [持续实施计划](../../../docs/design/system-memory/IMPLEMENTATION.md)、[历史状态](../../../docs/design/system-memory/STATUS.md) | 状态段落按自己的时点阅读。功能回归完成不能覆盖检索质量失败或人工审查缺口 |
| 2026-09-09，重构计划声明 | 在事件层前插入可复核的 L1 详细研究记录；旧事件/经验/地图投影为 L2/L3/L4；Run 优先归属对象 | [L0–L4 重构](../../../docs/design/system-memory/L0-L4-REFACTOR.md)、[对象与 Run 保存](../../../docs/OBJECT_RUN_STORAGE.md) | 通过版本投影兼容旧记录，不改旧修订、旧层级字段和旧哈希；不得从日志自动捏造详细研究说明 |
| 2026-09-09，报告计划的执行记录 | v2 的 `map.payload.report` 组织连续正文与固定 L1 引用，解决按层级堆卡片和重复显示的问题 | [报告编排计划](../../../docs/design/system-memory/RESEARCH-REPORT-COMPOSITION.md) | 这是连贯文稿的中间方案；现有实现保留兼容读取，当前新文稿由独立文档对象承载 |
| 2026-09-09，v3 计划与状态声明 | L1 技术单元分实验/方法/推导/分析；检索说明与稳定正文块分开；独立章节组成完整过程与简版报告；增加局部上下文、变化影响和分级测试 | [技术单元与双文稿](../../../docs/design/RESEARCH_DOCUMENTS.md)、[记录标准](../../../docs/RESEARCH_RECORDING.md)、[分级测试](../../../docs/TESTING.md) | 当前契约延续该结构；旧 map.report 是兼容入口，L4 回到精简研究地图，不是双文稿的唯一存储位置 |
| 2026-09-09，NOW 与固定开发 Run 线索；L0 设计本身未声明创建日期 | L0 从已有 Run 输入/产物和固定来源构建统一投影；`run-execute`/`run-register` 保存登记与回执 | [L0 统一入口设计](../../../docs/design/L0_MATERIALS.md)、[运行与登记](../../../docs/RUN_CAPTURE.md) | 列表只读取登记；登记时间/当前指纹不冒充过去执行时的原件版本 |
| 2026-09-09，Git/发行边界记录 | 分层记忆、研究文稿、L0 捕获代码集中并入源码；真实历史 Run 不随源码分发；浮点例子留在完整仓库并从公共归档排除 | [当前状态](../../../context/NOW.md)、[发行排除规则](../../../.gitattributes) | 源码能证明有哪些接口，无法单独证明缺失附件中的历史验收数字；示例也不等于公司业务验证 |
| 2026-09-09，本次导航整理；旧 PLAN 正文声明 2026-09-06 | 根 PLAN 增加历史时点提示；当前架构、使用方式、项目计划及通用维护职责分开 | [旧根计划](../../../PLAN.md)、[当前项目计划](../PLAN.md)、[文档维护手册](../../../docs/DOCUMENTATION_MAINTENANCE.md) | 保留旧计划正文和历史结果，不让它继续充当当前工作入口；本行只按指定根入口核读，不扩大为其他目录的全量盘点 |

除明确记录的前后引用和版本关系外，不从 Git 时间、Run ID 的时间片或文件修改时间推断同日内精确实施顺序。特别是 L0 投影与文稿演进属于不同变化原因，不必强行串成彼此依赖的单一流水线。

## 与当前代码核对的关键节点

| 历史说法 | 读取时的实现证据 | 解释 |
|---|---|---|
| 首版只用 L0–L3 | [contracts.py](../../../automation/scripts/memory/contracts.py) 的 `LEGACY_LEVELS`、`V2_LEVELS`、`LEVELS` 和 `project_memory_level` | 三代格式并存。当前展示采用 L0–L4；旧 event/experience/map 投影到 L2/L3/L4，不回写旧字节 |
| 首版仅有 v1 Schema | [v1](../../../automation/schemas/memory-v1.schema.json)、[v2](../../../automation/schemas/memory-v2.schema.json)、[v3](../../../automation/schemas/memory-v3.schema.json)；`RECORD_SCHEMA_VERSION = 3` | 首版契约文档是历史设计。当前程序支持新文稿类型及旧格式，不应机械把所有旧草案改成 v3 |
| L4 map 负责完整报告 | [documents.py](../../../automation/scripts/memory/documents.py) 的 `build_document`；兼容实现 [document.py](../../../automation/scripts/memory/document.py) | 优先独立固定文档；没有新文档时明确返回 `legacy_report`/`uncomposed`。旧长文不能改名充当独立简版报告 |
| L1 正文与普通检索是同一份长文本 | [index.py](../../../automation/scripts/memory/index.py) 的 `_row`、`project_owner`；v3 detail 的 `retrieval_description`、`blocks` | 当前索引剥离完整技术块与 figures，普通条目排除 L0 和 document/document_section，避免引用正文重复占据排名 |
| L0 必须额外新建 source | [raw_materials.py](../../../automation/scripts/memory/raw_materials.py)、[run_capture.py](../../../automation/scripts/run_capture.py)、[api.py](../../../automation/scripts/memory/api.py) | 现有 Run/来源登记可只读投影；新增执行或明确登记后，不需再造第二套原始材料记录 |

以上是本次静态核对，不是一次新的运行时验证或数据迁移。当前指纹和代码版本由本次工作记录固定；检索真实性、业务有效性、规模性能与跨物理机验收仍按各自证据判断。

## 如何避免再次读错历史

1. 修改当前行为时更新对应手册和当前架构入口；旧计划正文保留，在顶部写清“何时的什么方案”及现行入口。
2. 保存新的行为或验收结果时使用新的批次/Run；冻结规格、旧失败、人工待审不应被“已完成”覆盖。
3. 旧方案被替代时明确替代的是哪个职责：v1 层级被版本投影兼容；v2 report 的组织职责被独立 document 接管；L0 原始来源仍保留。
4. 此项目保存演进、影响和核对过程；通用维护规范在当前手册维护。盘点 JSON 仅记录读取快照，不充当另一个可编辑的业务状态源。

## 本次检查与历史验证缺口

26 份历史文档仅增加标记内的时点说明；移除本次标记后，其余字节与初次盘点指纹一致。所有新增时点导航和本页本地链接均已检查可定位。`fixtures/` 下 20 个文件保持初次盘点字节；模板及验收配方没有被改写为通过。

另发现一项**既有冻结清单不一致**：`fixture-manifest.json` 登记 19 个文件的完整指纹，其中 `acceptance.json`、`records.json`、`work-packages.json` 的当前 SHA-256 与清单不符。这三个文件与初次盘点快照、Git HEAD `647d7862331e283439d06d42ec01d3882a32d163` 完全同字节；主要结构仍为 v1，115 个验收项、48 条记录、14 个工作包数量相符。清单和校验脚本没有声明可以忽略这三个文件，所以不能把该项算作通过。

Git 仅保留这组文件集中引入的提交 `5e97aee8a03093124b95d294abaecfa36b1a2df8`，目前缺少可说明差异成因的更早版本或回执。故只能确认“已有清单与文件不一致”，尚不能判定它仅是旧清单、合法后续变更或其他问题。本次不重写 fixture、不重新冻结清单掩盖差异；机器清单保留期望值、实际值及 HEAD 对比，后续应凭原版本/变更依据单独追溯。它也不能被解释为本次历史导航改动造成的新故障。

## 全部文档的分类目录

下表列出全部 Markdown；其余 JSON、Python 配方同样列入机器清单。当前手册按用途找入口；历史设计与验收记录先看其时间上下文；模板和合成材料不参与真实能力结论。`docs/design/workspace-rules-reference.md` 虽位于 design，仍是现行按需检查参考，未被改为历史文档。

<!-- inventory-markdown-table:start -->
最终读取窗口：`2026-09-09T15:30:03.218813+00:00` 至 `2026-09-09T15:30:13.479008+00:00`（UTC）。Git HEAD：`647d7862331e283439d06d42ec01d3882a32d163`；清单同时记录尚未提交的工作树状态。

本次清单：74 个文件，其中 58 份 Markdown。分类数量：当前手册 18、验收记录 6、历史设计 21、合成fixture 20、模板 9。

“Git 首次提交日”仅辅助找到历史版本，不代表文档创建或功能实施日。无明确日期的文件不据 Git 日期补写正文时间。

### 历史设计

| 文档 | 正文明确日期 | Git 首次提交日 |
|---|---|---|
| [docs/design/ai-assisted-rd-workspace-practices.md](../../../docs/design/ai-assisted-rd-workspace-practices.md) | 2026-09-04 | 2026-09-06 |
| [docs/design/core-algorithms-rename-plan.md](../../../docs/design/core-algorithms-rename-plan.md) | 2026-09-06、2026-09-07 | 2026-09-06 |
| [docs/design/evidence-controls-plan.md](../../../docs/design/evidence-controls-plan.md) | 2026-09-06 | 2026-09-07 |
| [docs/design/windows-portability-plan.md](../../../docs/design/windows-portability-plan.md) | 2026-09-06 | 2026-09-06 |
| [docs/design/workbench-relations-plan.md](../../../docs/design/workbench-relations-plan.md) | 2026-09-07 | 2026-09-07 |
| [docs/MEMORY_DEVELOPMENT.md](../../../docs/MEMORY_DEVELOPMENT.md) | 2026-09-08、2026-09-09 | 2026-09-09 |
| [docs/系统记忆模块技术实现计划.md](../../../docs/系统记忆模块技术实现计划.md) | 2026-09-08 | 2026-09-09 |
| [docs/系统记忆模块技术目标讨论稿.md](../../../docs/系统记忆模块技术目标讨论稿.md) | 2026-09-08 | 2026-09-09 |
| [docs/design/RESEARCH_DOCUMENTS.md](../../../docs/design/RESEARCH_DOCUMENTS.md) | 2026-09-09 | 2026-09-09 |
| [docs/design/system-memory/02-services-algorithms.md](../../../docs/design/system-memory/02-services-algorithms.md) | 2026-09-09 | 2026-09-09 |
| [docs/design/system-memory/L0-L4-REFACTOR.md](../../../docs/design/system-memory/L0-L4-REFACTOR.md) | 2026-09-09 | 2026-09-09 |
| [docs/design/system-memory/RESEARCH-REPORT-COMPOSITION.md](../../../docs/design/system-memory/RESEARCH-REPORT-COMPOSITION.md) | 2026-09-09 | 2026-09-09 |
| [docs/design/L0_MATERIALS.md](../../../docs/design/L0_MATERIALS.md) | 未声明 | 2026-09-09 |
| [docs/design/dependency-release-plan.md](../../../docs/design/dependency-release-plan.md) | 未声明 | 2026-09-07 |
| [docs/design/evidence-view-monitor-plan.md](../../../docs/design/evidence-view-monitor-plan.md) | 未声明 | 2026-09-07 |
| [docs/design/setup-workbench-plan.md](../../../docs/design/setup-workbench-plan.md) | 未声明 | 2026-09-07 |
| [docs/design/system-memory/01-data-contracts.md](../../../docs/design/system-memory/01-data-contracts.md) | 未声明 | 2026-09-09 |
| [docs/design/system-memory/03-work-packages.md](../../../docs/design/system-memory/03-work-packages.md) | 未声明 | 2026-09-09 |
| [docs/design/system-memory/04-acceptance.md](../../../docs/design/system-memory/04-acceptance.md) | 未声明 | 2026-09-09 |
| [docs/design/system-memory/05-human-acceptance.md](../../../docs/design/system-memory/05-human-acceptance.md) | 未声明 | 2026-09-09 |
| [docs/系统记忆模块开发计划.md](../../../docs/系统记忆模块开发计划.md) | 未声明 | 无 Git 历史 |

### 验收记录

| 文档 | 正文明确日期 | Git 首次提交日 |
|---|---|---|
| [docs/design/adaptive-context-review-2026-09-06.md](../../../docs/design/adaptive-context-review-2026-09-06.md) | 2026-09-06 | 2026-09-06 |
| [docs/design/local-retrieval-review-2026-09-06.md](../../../docs/design/local-retrieval-review-2026-09-06.md) | 2026-09-06 | 2026-09-06 |
| [docs/design/materials-review-2026-09-06.md](../../../docs/design/materials-review-2026-09-06.md) | 2026-09-06 | 2026-09-06 |
| [docs/design/workflow-review-2026-09-06.md](../../../docs/design/workflow-review-2026-09-06.md) | 2026-09-06 | 2026-09-06 |
| [docs/design/system-memory/IMPLEMENTATION.md](../../../docs/design/system-memory/IMPLEMENTATION.md) | 2026-09-08、2026-09-09 | 2026-09-09 |
| [docs/design/system-memory/STATUS.md](../../../docs/design/system-memory/STATUS.md) | 2026-09-09 | 2026-09-09 |

### 当前手册

| 文档 | 正文明确日期 | Git 首次提交日 |
|---|---|---|
| [docs/design/workspace-rules-reference.md](../../../docs/design/workspace-rules-reference.md) | 2026-09-06 | 2026-09-06 |
| [docs/EVIDENCE_CONTROLS.md](../../../docs/EVIDENCE_CONTROLS.md) | 2026-09-09 | 2026-09-07 |
| [docs/EVIDENCE_VIEW_MONITOR.md](../../../docs/EVIDENCE_VIEW_MONITOR.md) | 2026-09-09 | 2026-09-07 |
| [docs/EXISTING_MATERIALS.md](../../../docs/EXISTING_MATERIALS.md) | 2026-09-09 | 2026-09-06 |
| [docs/MATERIAL_RELATIONS.md](../../../docs/MATERIAL_RELATIONS.md) | 2026-09-09 | 2026-09-07 |
| [docs/MEMORY_REQUESTS.md](../../../docs/MEMORY_REQUESTS.md) | 2026-09-09 | 2026-09-09 |
| [docs/MEMORY_USAGE.md](../../../docs/MEMORY_USAGE.md) | 2026-09-09 | 2026-09-09 |
| [docs/OBJECT_RUN_STORAGE.md](../../../docs/OBJECT_RUN_STORAGE.md) | 2026-09-09 | 2026-09-09 |
| [docs/RESEARCH_RECORDING.md](../../../docs/RESEARCH_RECORDING.md) | 2026-09-09 | 2026-09-09 |
| [docs/RETRIEVAL.md](../../../docs/RETRIEVAL.md) | 2026-09-09 | 2026-09-06 |
| [docs/RUN_CAPTURE.md](../../../docs/RUN_CAPTURE.md) | 2026-09-09 | 2026-09-09 |
| [docs/TESTING.md](../../../docs/TESTING.md) | 2026-09-09 | 2026-09-09 |
| [docs/WORKBENCH_DEVELOPMENT.md](../../../docs/WORKBENCH_DEVELOPMENT.md) | 2026-09-09 | 2026-09-07 |
| [docs/DEPENDENCY_RELEASE.md](../../../docs/DEPENDENCY_RELEASE.md) | 未声明 | 2026-09-07 |
| [docs/DOCUMENTATION_MAINTENANCE.md](../../../docs/DOCUMENTATION_MAINTENANCE.md) | 未声明 | 无 Git 历史 |
| [docs/SETUP_WORKBENCH.md](../../../docs/SETUP_WORKBENCH.md) | 未声明 | 2026-09-07 |
| [docs/UPGRADE_TESTING.md](../../../docs/UPGRADE_TESTING.md) | 未声明 | 2026-09-07 |
| [docs/WINDOWS_PORTABILITY.md](../../../docs/WINDOWS_PORTABILITY.md) | 未声明 | 2026-09-06 |

### 合成fixture

| 文档 | 正文明确日期 | Git 首次提交日 |
|---|---|---|
| [docs/design/system-memory/fixtures/README.md](../../../docs/design/system-memory/fixtures/README.md) | 未声明 | 2026-09-09 |
| [docs/design/system-memory/fixtures/sources/cache.md](../../../docs/design/system-memory/fixtures/sources/cache.md) | 未声明 | 2026-09-09 |
| [docs/design/system-memory/fixtures/sources/ocr.md](../../../docs/design/system-memory/fixtures/sources/ocr.md) | 未声明 | 2026-09-09 |
| [docs/design/system-memory/fixtures/sources/pressure.md](../../../docs/design/system-memory/fixtures/sources/pressure.md) | 未声明 | 2026-09-09 |
| [docs/design/system-memory/fixtures/sources/repeat.md](../../../docs/design/system-memory/fixtures/sources/repeat.md) | 未声明 | 2026-09-09 |
| [docs/design/system-memory/fixtures/sources/retry.md](../../../docs/design/system-memory/fixtures/sources/retry.md) | 未声明 | 2026-09-09 |
| [docs/design/system-memory/fixtures/sources/thermal-v2.md](../../../docs/design/system-memory/fixtures/sources/thermal-v2.md) | 未声明 | 2026-09-09 |
| [docs/design/system-memory/fixtures/sources/thermal.md](../../../docs/design/system-memory/fixtures/sources/thermal.md) | 未声明 | 2026-09-09 |
| [docs/design/system-memory/fixtures/sources/units.md](../../../docs/design/system-memory/fixtures/sources/units.md) | 未声明 | 2026-09-09 |
| [docs/design/system-memory/fixtures/sources/vibration.md](../../../docs/design/system-memory/fixtures/sources/vibration.md) | 未声明 | 2026-09-09 |

### 模板

| 文档 | 正文明确日期 | Git 首次提交日 |
|---|---|---|
| [docs/design/system-memory/human-acceptance/REVIEW_TEMPLATE.md](../../../docs/design/system-memory/human-acceptance/REVIEW_TEMPLATE.md) | 未声明 | 2026-09-09 |
| [docs/templates/CORE_ALGORITHM_CARD_TEMPLATE.md](../../../docs/templates/CORE_ALGORITHM_CARD_TEMPLATE.md) | 未声明 | 2026-09-06 |
| [docs/templates/INTERFACE_CONTRACT_TEMPLATE.md](../../../docs/templates/INTERFACE_CONTRACT_TEMPLATE.md) | 未声明 | 2026-09-06 |
<!-- inventory-markdown-table:end -->
