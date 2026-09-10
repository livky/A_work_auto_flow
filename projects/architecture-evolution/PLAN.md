> 当前活动计划：[表示查询正式开发与验收](runs/run-20260909t194710z-3cf36b2fdd60/IMPLEMENTATION_TRACKER.md)。原[实施准备](plans/implementation-preparation.md)与下文保留各自历史时点；实际能力见[运行状态](../../docs/design/representation-query-v0.2/RUNTIME_STATUS.md)。

# 本轮文档同步与架构演进计划

创建日期：2026-09-09。项目：`PRJ-ARCHITECTURE-EVOLUTION`。执行 Run：`RUN-20260909T151004Z-A68FBA9F176D`。状态：本轮已完成；项目继续用于后续演进。文档与结构检查通过，quick 整体不完整及人工待审分别保留。

## 用户目标与边界

按时间整理 `docs/` 的演进记录，以当前代码、schema 和实际命令为能力依据，修正全部现行 README、AGENTS 及关键导航。形成简单的模块关系影响图，保存在 Project，并要求后续每次开发检查关联影响。

本轮修改文档、规则和项目记录，不改产品可执行逻辑、规范记忆、历史 Run、合成 fixture、模型或发行规则。保留工作开始时的未提交用户修改。历史文档可以增加时点标识，不把原设计或旧验证结果改写成当前事实。

## 核对基线

- 代码基线：main `647d786`；记忆与研究文档主要源码通过 `5e97aee` 合入。
- 记忆事实依据：`automation/schemas/memory-v3.schema.json`、`memory/contracts.py`、`technical_units.py`、`documents.py`、`index.py`、`search.py`、`packets.py`。
- 时间依据：正文明确日期、阶段关联及 Git 历史分别记录；文件最后修改时间不能冒充功能完成时间。
- 当前分层：L0 来源、L1 技术单元、L2 事件/决策、L3 经验、L4 地图；独立章节和文稿 `level=null`。
- 历史限制：旧检索质量未通过、万条规模暂缓、人工及第二台物理机待验收；本轮文档校验不改变这些状态。

## 执行清单

- [x] 读取入口、当前状态、规则、技能和代码基线；建立 Project 与 Run。
- [x] 开发前运行 testing audit，冻结 quick 与 D01–D04 验收清单。
- [x] 按时间盘点全部 docs 文件，注明现行、历史、模板及固定合成材料。
- [x] 核对 v1/v2/v3、Run/L0、技术单元、独立文稿及检索默认边界。
- [x] 更新根入口、子目录 README/AGENTS、手册和实际 Skill 源。
- [x] 保存模块影响图、职责表、变更检查方法和本轮影响处置记录。
- [x] 完成文档一致性和链接检查，运行 quick、refresh-index、validate（quick 因前端缺依赖为 incomplete，不计整体通过）。
- [x] Run 保存实际输入指纹、结果、图快照和阅读审查入口；Project Run 查询与 L0 回读可定位，人工意见保持待审。

## 验收

| ID | 标准 | 证据入口 |
|---|---|---|
| D01 | docs 中全部文件有盘点，演进顺序可解释，日期不混用 | docs/DOCUMENT_HISTORY.md 与 inventory |
| D02 | 当前介绍与代码职责一致，历史记录未被重写 | 本轮变更清单、代码固定输入与文档自查 |
| D03 | 影响图在 Project 中，开发规则与 Skill 指向维护方法 | context/MODULE_IMPACT.md、根 AGENTS、维护手册 |
| D04 | 公开命令、链接、Project/Run 可定位与回读 | quick 回执、refresh-index、validate、Run 登记回执 |

## 验证选择与恢复

执行前清单位于本 Run 的 `testing/selection-v1.json`，包含 quick 核心和本次文档验收；不把源码核对算作实际功能通过。修改若影响安装或可执行代码，必须先更新选择并补相应回归，不能沿用文档范围。

根 README、AGENTS、ARCHITECTURE 和原 NOW 在本 Run 的 `baseline/` 留有修改前快照。恢复必须比较当前内容后人工合并；不要覆盖后续修改。规范记忆和旧 Run 不在本轮写入范围。

## 下一轮

文档同步完成后继续讨论统一查询契约、状态所有权与检索基线。是否替换后端、增加重排或图扩展，按实测缺口决定，另建对应 Run 和检查选择。
