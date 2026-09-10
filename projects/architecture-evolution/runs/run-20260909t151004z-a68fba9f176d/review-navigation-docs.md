# 目录导航与检索手册检查回执

Run：`RUN-20260909T151004Z-A68FBA9F176D`。核对日期：2026-09-09。执行者：协作 AI（目录导航与检索审查）。代码基线：main `647d786`，本轮文档修改尚未提交；最终文件指纹由本 Run 的统一登记固定。

本回执汇总本轮已经执行的检查。它记录文档修正及实际检查范围，不将代码阅读视作功能测试，也不改变历史检索质量、规模测试或人工复核状态。

## 覆盖与处置

共检查 39 个现行入口：33 个子目录 README/AGENTS，以及 6 份检索、证据与工作台手册。其中 23 个已修改（17 个子目录入口、6 份手册），16 个检查后无需修改。根 README/AGENTS、context、docs/design、架构演进 Project 的新文档由本轮其他检查负责，不计入本表。实际历史 Run 的 README、规范记忆、冻结快照与合成 fixture 不作现行介绍批量改写。

### 已修改的 23 个文件

| 文件 | 处置原因 |
|---|---|
| `automation/README.md` | 对齐材料/记忆两条检索路径、当前记忆内容和模块入口 |
| `automation/workflows/README.md` | 对齐研究内容、对象 Run 与工作流维护入口 |
| `core-algorithms/README.md` | 补充算法归属 Run 及规范记忆导航，保留核心算法准入边界 |
| `data/lineage/README.md` | 对齐对象内 Run 的沿袭文件位置与既有布局兼容 |
| `docs/EVIDENCE_CONTROLS.md` | 区分记忆证据、固定引用、复核与生产准入边界 |
| `docs/EVIDENCE_VIEW_MONITOR.md` | 对齐只读证据检查、文稿影响提示和监测边界 |
| `docs/EXISTING_MATERIALS.md` | 更新已有材料导入、对象 Run、技术单元与检索选择入口 |
| `docs/MATERIAL_RELATIONS.md` | 区分材料关系、记忆关联、地图和独立文稿，以及默认导航与完整图扩展 |
| `docs/RETRIEVAL.md` | 明确两条检索路径、回执类型、向量默认值、知识/文稿/L0 范围与当前性能限制 |
| `docs/WORKBENCH_DEVELOPMENT.md` | 对齐工作台当前功能、记忆文稿与产品入口说明 |
| `knowledge/README.md` | 明确单文件对象记忆、运行归属与知识导航 |
| `projects/README.md` | 明确 Project 组织职责及对象内 Run 归属 |
| `reports/README.md` | 对齐报告对象、独立研究文稿与技术内容引用入口 |
| `research/AGENTS.md` | 对齐对象内 Run、技术单元、独立章节及双文稿的维护要求 |
| `research/_template/README.md` | 对齐研究模板的当前记录与阅读入口 |
| `research/agent-workspace-review/README.md` | 增加历史时点与当前入口说明，保留当时研究内容 |
| `research/floating-point-summation/README.md` | 增加当前记录入口，保留既有计算与结论 |
| `research/floating-point-summation/details/README.md` | 标明既有技术说明的历史位置与现行技术单元入口 |
| `research/material-relationship-view/README.md` | 区分历史研究时点与当前材料关系/记忆文稿功能 |
| `runs/AGENTS.md` | 对齐对象归属、根目录默认值和旧 Run 兼容规则 |
| `runs/README.md` | 说明对象内 Run、无归属根 Run、检索与运行登记入口 |
| `services/qdrant/README.md` | 对齐材料与记忆向量集合、重建属性及默认行为 |
| `tools/README.md` | 对齐工具登记、运行归属与维护入口 |

### 检查后无需修改的 16 个文件

| 文件 | 无需修改的判断 |
|---|---|
| `tools/scripts/README.md` | 脚本保存位置与用途说明未受本次记忆内容演进影响 |
| `tools/packages/README.md` | 包目录用途与当前工具登记边界一致 |
| `tools/external/README.md` | 外部工具引用说明未宣称新的记忆能力 |
| `tools/AGENTS.md` | 工具边界和维护规则无需本次修正 |
| `archive/README.md` | 归档用途与保留历史要求一致 |
| `data/samples/README.md` | 样例数据用途不涉及过时的记忆层级或 Run 归属 |
| `data/README.md` | 数据目录职责与原始数据边界一致 |
| `data/AGENTS.md` | 数据权限、来源与保留约束继续适用 |
| `core-algorithms/AGENTS.md` | 公司核心算法准入及证据要求继续适用 |
| `core-algorithms/_template/README.md` | 模板未包含需替换的检索或技术单元实现承诺 |
| `inbox/README.md` | 候选材料入口与分流职责继续适用 |
| `projects/AGENTS.md` | 项目组织与对象 Run 归属说明已符合当前实现 |
| `reports/templates/README.md` | 报告模板目录说明无需修改 |
| `reports/sources/README.md` | 来源引用目录说明无需修改 |
| `projects/_template/README.md` | 模板组织职责与当前 Project 边界一致 |
| `projects/_template/AGENTS.md` | 模板局部规则未与当前根约定冲突 |

## 重点实现核对

以下是文档应表达的当前边界，均基于本轮已读取的代码，而非本回执新增的实现：

- `workspace_cli.py`、`manifest_discovery.py`：新 Run 按 owner 保存；根 Run 和旧布局继续发现，目录型、单文件及工具对象有不同运行位置。
- `memory/search.py`、`feedback.py`、`packets.py`：材料检索使用 `Q-*`/`CTX-*`，记忆检索使用 `QMEM-*`/`PKT-*`；反馈入口不可混用。`memory search` 的向量默认 `auto`，`memory context` 默认 `off`，内部搜索使用 `record=False`，不能承诺产生持久 QMEM 查询历史。
- `memory/index.py`：材料与规范记忆共用 SQLite 文件，使用不同表及向量集合；索引是派生投影，不替代规范记忆及固定来源。
- `memory/contracts.py`、`search.py`、`packets.py`：v3 L1 使用检索说明和完整技术块；独立 `document`/`document_section` 的层级为 null；L4 继续是地图。L0 不进入默认知识全文/向量排名。
- `memory/packets.py`、`evaluation.py`：默认上下文中的导航信息不等于运行完整邻接扩展；`complete_graph_context` 属于评估链路。
- `memory/associations.py`：语义关联仍读取 `body_markdown`，未等同覆盖 v3 技术块；全库候选/投影扫描及关联质量、规模性能仍有待后续评估。

## 实际检查结果

1. 对上述 23 个修改文件执行 `git diff --check -- <明确的 23 个文件>`，无空白错误输出。因本机仓库所有权检查，命令仅使用本次 `git -c safe.directory=D:/共享桌面/A_work/A_work_auto_flow`，未修改全局 Git 配置。
2. 对这 23 个文件的 72 个本地 Markdown 链接目标逐项检查存在性。修正 4 处误指向 `docs/ARCHITECTURE.md` 的引用，使其指向根 `ARCHITECTURE.md`；最终没有缺失目标。
3. 核对 3 个有片段的跨文档引用：`docs/EXISTING_MATERIALS.md` → `RESEARCH_RECORDING.md#文件归属`、`RETRIEVAL.md#先选择入口`；`reports/README.md` → `RESEARCH_RECORDING.md#连贯报告的编排`。目标标题存在。检索手册原指向根 README 旧附录的入口已改为架构说明。
4. 只读交叉审查根导航与记录标准，报告起始导航混用反馈入口、L1 全部绑定 Run 的旧句、术语表空行断表，以及根 PLAN 缺少历史标识。具体修复和最终验证由根代理统一收口，本回执不把“已报告”记为“已修复”。
5. 再次只读检查 `projects/architecture-evolution/context/MODULE_IMPACT.md` 与 `docs/DOCUMENTATION_MAINTENANCE.md`，未发现明显实质问题。影响图明确箭头表示变更检查关系，已交代代码路径基准、当前唯一维护位置、固定快照、人工待审和非自动化边界；通用手册明确概念主要维护位置，并为不含 Project 实例的公共源码包保留独立维护入口。

## 限制

- 链接检查排除代码围栏、外部 URL、应用协议、纯页内片段和示例占位目标；没有检查远程 URL 可用性，也未渲染浏览器页面。片段检查只覆盖上述 3 个实际引用，不构成全仓 Markdown 渲染验收。
- 39 个入口的计数对应本协作检查范围，不代表全仓全部文档的覆盖数。根入口、设计盘点、Skill、统一命令与完整链接检查见同一 Run 的其他回执。
- 本协作检查未重新运行产品功能、模型、历史实验、检索质量、万条规模、安装升级、第二台物理机或真实业务验收；统一测试的实际状态以本 Run 的 testing 回执为准。
- 本轮修改的是可维护介绍和导航；保留历史 Run、规范记忆、原始数据与冻结 fixture 的原字节。已存在的质量未通过、规模暂缓和人工待审没有因此变为通过。
- 本回执创建后若继续修改受检文件，应以最终统一检查及登记的指纹为交付依据。AI 内容检查不是人工审查或业务结论复核。
