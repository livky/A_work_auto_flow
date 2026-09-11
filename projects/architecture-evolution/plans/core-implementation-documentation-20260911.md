# CORE 核心实现说明维护

日期：2026-09-11。状态：文档维护及定向检查完成。

## 目标与范围

按用户要求在 docs/CORE.md 集中维护查询选项与排序算法、固定关联/独立关系/必要依赖、上下文组装与文稿读取，以及 Skill 指导的结果解析、文本结构、保存顺序、JSON 数据和本地不可变提交。正文不加使用示例。保持原工作树已有修改，不改规范业务记忆、运行代码、前端和依赖。

## 处置与依据

- CORE：根据 material_query 的 coordinator/content/associations/assembly/reader、memory 的 search/index/contracts/service/store/documents，以及研究与记录方法源核对后补充。
- README、docs/README、DOCUMENTATION_MAINTENANCE：维护入口及同次更新触发；development-checks 更新 CORE 的必读职责。
- context-maintenance：纠正当前写作仍引用旧 event 字段的遗留句，使用 narrative 正文及 stages；不改变历史语义。
- ARCHITECTURE、TESTING：本次无模块/状态所有权或测试标准变化，核对后无需修改。
- DEVELOPMENT_HISTORY：保留已有决策，新增 D12 的理由和当前边界。

## 验证选择

纯文档及现行 Skill 字段纠错，选择代码/契约静态核对、Markdown 本地链接检查、工作区 refresh-index 与 validate；不将静态核对记为软件行为回归或实际 AI 研究验收。未更改运行代码、依赖、安装器和前端，无需重跑迁移/构建或打包；Windows x64 和旧工作数据的部署路径不变。

## 完成核对

六份必读文档与 DEVELOPMENT_HISTORY 已完整后读；修改项及无需修改项见上方处置。CORE 最终回读修正“无变化”的描述为内容字段指纹判断，避免误称 AI 语义等价判断，并补累计预算/取消边界。

- refresh-index：退出码0，工作区导航索引刷新完成。
- validate：退出码0，0错误、4警告；均为既有 Run `run-20260910t183626z-429304f92e99/verification/architecture-snapshot.md` 中相对链接脱离原目录，保留固定快照字节。
- 本次七份文档/Skill 的118个本地链接目标均存在；该检查不验证锚点、语义正确性或行为回归。
- 本次无新增软件测试执行或实际 AI 研究场景验收；Skill 修正仅按当前 schema 与记录标准静态核对，不宣称验证了 AI 后续写作质量。

## 用户反馈后的精简（2026-09-11）

用户要求 CORE 以人类易读的伪代码和必要解释为主，AI 按实现文件索引自行展开细节。本轮重写为7段核心流程，保留选项、算法用途和关键边界，去掉字段/目录清单、公式参数及 G01–G12 的重复功能表。同步修改维护约定、文档索引和 development-checks；开发历史新增 D13，保留原 D12 的来由。

六份必读文档与开发历史按要求回读；README、ARCHITECTURE、TESTING 含义未受影响，无需修改。纯文档表达调整，检查本地链接和工作区校验，不运行功能回归，不涉及 Windows 部署、依赖或业务记录迁移。

本次精简验证：82个本地链接目标检查通过；refresh-index退出码0；validate退出码0，0错误、4个既有固定快照相对链接警告。未修改固定快照。

## 恢复功能分工（2026-09-11）

前轮精简误删G01–G12表，已恢复功能身份、输入输出、边界及共享执行控制；补保存/查询/维护交接图和ARCHITECTURE模块映射。原架构模块影响表未丢失、未改写。CORE、维护约定、development-checks及开发历史D14已同步；README、ARCHITECTURE、文档索引和TESTING核对无需修改。保留现有伪代码。refresh-index和validate退出码均为0；校验0错误、4个既有固定快照链接警告。仅文档恢复，未改变软件行为或运行回归。

## 架构约束遗漏审查（2026-09-11）

依据：Git HEAD 的 ARCHITECTURE 与当前架构、根 AGENTS、本轮 CORE 精简/恢复及维护约定。Git 差异含本轮之前的工作树变化，不把全部差异归因于本次 CORE 编辑。

| 审查项 | 发现与处置 |
|---|---|
| G01–G12 功能定义与交接 | 本轮确曾误删，前一步已恢复，继续保留 |
| 对象不复制、Project 引用聚合、查询回执不是临时索引、影响提示不自动修改结论 | 旧架构有明确表述，现行架构入口弱化；补回稳定设计约束 |
| 依赖局部化、状态显式、性能评估三原则 | 根 AGENTS 一直保留；架构新增直接可读的设计要求及导航 |
| 模块影响表、状态权威、单 Owner 事务、固定版本与预算、实际实现限制 | 原文仍在；集中连接到设计约束，未宣称实现新解耦能力 |
| 旧 event/map、v3 当前契约等历史定义 | 已有 D09–D11 与 v4 替代，不恢复过期定义或修改固定历史 |
| 升级保护、离线依赖、Windows x64、测试分级 | 根规则及现行测试/部署入口仍在，无需恢复或改程序 |

六份文档完成前后核对：ARCHITECTURE、CORE、docs/README、DOCUMENTATION_MAINTENANCE 已修改；根 README 与 TESTING 核对无需修改。development-checks 补架构必读职责，DEVELOPMENT_HISTORY 补 D15。纯文档恢复，不触发代码回归、前端构建、依赖打包或升级测试。

验证：109个本地链接目标存在（不包含锚点自动校验）；新增稳定设计约束标题与入口人工核对。refresh-index 和 validate 均退出0，0错误、4个既有固定 Run 快照相对链接警告，未改快照。当前只核对了上述明确文档范围，不宣称完成全库历史审计。
