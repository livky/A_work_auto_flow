# 正式开发入口、文件清单与一致性核对

核对日期：2026-09-10。结论：需求、概念、接口草案、交互、阶段计划、用例设计、Skill、迁移与后续方向已经具备，可以启动 P0；尚不是已冻结且可直接实现全部阶段的工程基线。P0 必须交付可执行请求校验、请求/响应样本、旧接口适配基线和实际测试选择，之后才能进入 P1。产品实现和产品验收均未完成。

## 1. 正式开发按什么顺序读

| 顺序 | 文件 | 权威职责与现状 |
|---|---|---|
| 1 | 根 AGENTS.md、context/START_HERE.md、context/NOW.md | 当前规则、能力与下一步；不从历史 Run 猜状态 |
| 2 | 本页、README.md、IMPLEMENTATION.md | 文件范围、准备状态、阶段依赖与验收门槛 |
| 3 | CONTRACTS.md、contracts.py | 行为与字段/端口设计；Python 注解尚不是运行校验器 |
| 4 | WORKBENCH.md | 用户操作、页面状态、HTTP 与响应对应 |
| 5 | TEST_DESIGN.md、test-cases.json | fixture/断言/层次与设计覆盖；没有真实执行回执 |
| 6 | 根待开发计划.md | 首期取舍与B01–B10后续候选，不扩充本期范围 |
| 7 | 三个专项Skill、现行操作手册、模块影响图 | AI职责、现有命令与关联修改范围 |

本表中未写前缀的本目录文件位于 `docs/design/representation-query-v0.2/`。Project活动指针为 `projects/architecture-evolution/project.json` → `plans/implementation-preparation.md`。Project根 PLAN.md是前一轮完成记录，增加导航但保留正文。v0.1为继承设计，G03与本次新应用流程以v0.2为准；未重述的底层读取/事务/索引接口仍需在P0冻结兼容映射，不可称v0.2已覆盖全部底层签名。

## 2. 当前需要涉及的文件

下表路径均相对于工作区根目录。“检查/适配”不等于必须重写；新文件是建议的确定落点，开发中若调整须同步本表、导入方与测试映射。现有/拟新增逐项存在性见 [文件清单](development-files.json)。

| 阶段 | 现有文件：阅读、适配或按影响修改 | 拟新增文件 | 主要对应验收 |
|---|---|---|---|
| P0 契约 | automation/scripts/memory/contracts.py、api.py、cli.py、generate_types.py；automation/schemas/memory-v3.schema.json；automation/frontend/scripts/contracts.mjs | automation/scripts/material_query/contracts.py、validation.py、legacy_adapter.py；automation/schemas/material-query.schema.json；automation/frontend/src/generated/material-query.ts | Q01–Q12、Q66、Q68；兼容旧六字段Ref和旧路由 |
| P1 表示与读取 | automation/scripts/memory/service.py、store.py、raw_materials.py、technical_units.py、documents.py | automation/scripts/material_query/definitions.py、reader.py、representations.py | Q03/Q04/Q19–Q22/Q25/Q69 |
| P2 查询与材料包 | automation/scripts/memory/search.py、index.py、packets.py；automation/scripts/retrieval.py、qdrant_backend.py | automation/scripts/material_query/coordinator.py、state.py、budget.py、assembly.py | Q05–Q28、Q65/Q69/Q70 |
| P3 联想与加深 | automation/scripts/memory/associations.py、index.py、lineage.py | automation/scripts/material_query/associations.py、deepening.py | Q29–Q43；已有关系和新结构提议分开 |
| P4 维护 | automation/scripts/memory/impact.py、lineage.py、service.py、recovery.py、evidence_adapter.py | automation/scripts/material_query/maintenance.py | Q44–Q50/Q53/Q54/Q67 |
| P5 HTTP/界面 | automation/scripts/workbench_app/web.py、service.py、contracts.py；automation/frontend/src/App.tsx、api.ts、Memory.tsx、MemorySearch.tsx、ResearchDocument.tsx | automation/scripts/material_query/api.py、structure.py；automation/frontend/src/MaterialQuery.tsx、MaterialStructure.tsx、MaterialPacket.tsx、MaterialMaintenance.tsx、material-query.css | Q55–Q62；web.py增加材料路由，不能仅改memory/api.py |
| P6 构建/交付 | automation/frontend/package.json、package-lock.json、scripts/contracts.mjs、scripts/manifest.mjs；automation/ui/workbench-assets/asset-manifest.json及构建资源；automation/scripts/install_workspace_skills.py、portable.py；automation/setup.ps1、setup.cmd、.gitattributes | .agents/skills/material-query/SKILL.md、association-exploration/SKILL.md、semantic-maintenance/SKILL.md | Q63/Q64；自动发现、资源指纹和旧工作区保护 |
| 测试 | automation/testing/catalog.json、runner.py；automation/tests/memory_fixture.py、upgrade_fixture.py、test_portable.py、test_install_workspace_skills.py；automation/frontend/e2e/workbench.spec.ts | automation/tests/test_representation_contracts.py、test_material_queries.py、test_material_deepening.py、test_material_maintenance.py；automation/frontend/src/MaterialQuery.test.tsx、MaterialMaintenance.test.tsx；automation/frontend/e2e/material-query.spec.ts | 全Q用例分配给真实测试ID后才算实施覆盖 |

新增 package 还需 `automation/scripts/material_query/__init__.py`；不在此另开一个服务或数据库。P0/P1/P2/P3/P4中的新包作为应用适配层，旧 memory 包继续拥有规范存储。CLI新命令若首期提供，经现有 memory/cli.py 委托同一应用层；不能新增另一套语义。JSON/TS生成文件不手改：P0选定并实现从受控Python契约到JSON schema/TS的生成链，生成产物与校验回归共同入库，旧memory-v3 schema继续独立。

## 3. 文档与Skill需要同步的文件

- 用户与规则入口：README.md、AGENTS.md、ARCHITECTURE.md、context/START_HERE.md、context/NOW.md。
- 现行手册：docs/MEMORY_REQUESTS.md、MEMORY_USAGE.md、RETRIEVAL.md、MATERIAL_RELATIONS.md、RESEARCH_RECORDING.md、WORKBENCH_DEVELOPMENT.md。功能真正实现时才增加可运行命令；本轮只增加计划导航，不把设计变成使用说明。
- 维护与交付：docs/DOCUMENTATION_MAINTENANCE.md、TESTING.md、UPGRADE_TESTING.md、DEPENDENCY_RELEASE.md、SETUP_WORKBENCH.md；修改依赖/安装时按风险执行，未改变的说明记录“已检查无需修改”。
- Skill方法源：automation/workflows/material-query/SKILL.md、association-exploration/SKILL.md、semantic-maintenance/SKILL.md；同时检查workspace-context、context-maintenance、research-loop、development-checks已有入口，防止绕开新约束。
- 项目协调：projects/architecture-evolution/project.json、plans/implementation-preparation.md、PLAN.md、context/MODULE_IMPACT.md；根待开发计划.md同步实际阶段和策略状态。

原始数据、旧规范记录、旧Run、既有冻结fixture不属于可直接编辑文件。对规范内容的修订使用公共事务；fixture需要新场景就修改构造器生成隔离副本，不能篡改旧快照使测试通过。

## 4. 本次核对发现与处置

| 问题 | 处置 | 仍需在实施中完成 |
|---|---|---|
| NOW下一步指向v0.1，与活动计划不一致 | 已统一为v0.2/P0；前期文字标明历史时点 | 每阶段更新当前指针，不改旧Run |
| Project根PLAN仍是已完成旧批次 | 增加当前活动计划导航，保留历史内容 | 不维护两个相互独立的活跃计划 |
| 缺逐文件落点与存在性区分 | 本页＋JSON清单明确现有/拟新增、阶段和作用 | 新文件落地后更新状态及真实测试ID |
| 10秒wall预算从搜索一直计时，会吞掉用户选择时间 | 改为各执行阶段的累计活动墙钟时间；用户等待不计入，另有查询TTL | Q71计时/等待/并行测试 |
| 类型注解与静态检查容易被误解为接口验证已齐全 | 明确当前仅设计；P0补校验与正反请求/响应样本 | Q72生成链与样本验证 |
| “无代理导出任务包”与“AI桥P4/P5实现”范围不够清楚 | 首期必须提供有界任务包/审查草案回填；自动代理桥属可选B07 | Q73无代理导出与回填边界；不能伪造AI读取 |
| 查询状态/游标寿命未定 | 本轮补首期生命周期、重启和并发规则 | Q74查询重启/同会话并发 |
| 70项用例只有设计，无fixture脚本/真实ID/执行选择 | 状态保持未执行，补P0硬交付清单 | 不宣称测试实施完成或发布就绪 |

## 5. P0开工与退出清单

开工前冻结一份新的实施Run：用户范围、代码与未提交差异指纹、schema/Skill/catalog指纹、影响表与基线回执。先执行testing audit，再prepare实际选择；本次文档核对不代替该步骤。

P0退出必须同时具备：

1. 受控运行契约、严格请求校验、错误映射与JSON/TS生成链；字段/枚举不靠多份手工拷贝维护。
2. 六种表示的请求/响应样本；成功、部分、拒绝、取消、过期各有机器可校验样本；未知字段和非法预算有反例。文件建议置于 `automation/tests/fixtures/material-query/`，此目录尚未创建。
3. F1可复现fixture构造器、固定输入manifest、旧适配结果和旧版本回读基线；F2复用现有upgrade_fixture。
4. 真实测试ID与Q编号的映射、冻结selection、执行回执；未实现项明示缺口。类型解析与“有用例文字”不能通过此门槛。
5. 查询状态/预算、权限、策略开关、降级和恢复由同一应用层执行；新路由默认关闭，旧接口回归通过。

无外部企业接入或额外模型需求，本计划不需要新增账号/模型审批。历史前端开发依赖缺失、固定fixture指纹差异、独立检索质量未通过是开工前需要重新核实的环境/基线风险，不能抄旧通过率；它们不阻止当前完成文档准备。

## 6. v0.1不是整体废弃：修正清单遗漏

上一轮“83个现有文件”没有包含v0.1目录的12个文件，属于清单遗漏，不能据此声称此前行为与接口已全部迁入v0.2。现已补入，清单为95个现有文件＋33个拟新增文件。文件存在性不是需求覆盖证明。

| 原文件 | 正式开发仍需继承的内容 | 与v0.2的关系 |
|---|---|---|
| README.md、CORE.md | 总体目标、概念、完整调用闭环、存储端职责 | 总体设计依据，必须阅读；具体新增应用流程读v0.2 |
| SPEC.md | 范围/身份/用途/状态所有权/错误和跨端口不变量 | 未明确变更的约束继续有效；计时等明确修订按v0.2 |
| contract_types.py、contract_ports.py | 72个数据结构、40个领域方法和3个执行控制方法 | v0.2的14个方法不是这43个方法的替代全集；底层抽象仍需适配 |
| function-catalog.json、FUNCTIONS.md、DATATYPES.md | 每个接口的必要性、前后置条件、候选取舍和字段解释 | 目录继续作为逐项追踪依据；两份生成视图不手改 |
| REPRESENTATION_AND_GRAPH.md | 表示配方、联想、AI分工、图生命周期及设计原因 | v0.2细化其部分字段与流程，不删除尚未映射的目标 |
| request-examples.json、check_contracts.py | 原有正反请求与结构检查 | 保留旧基线，新版检查不能替代 |
| IMPLEMENTATION.md | 原代码适配映射、C01–C26验收与约束 | 阶段排期用v0.2 P0–P6；旧验收须逐项映射，不能遗漏 |

P0增加硬门槛：为G01–G12及执行控制、43个方法、C01–C26逐项记录“保留/细化/替换/延期及理由→实现位置→验收ID”；旧字段与新字段同名也不能假设语义一致。存在明确冲突时采用用户后续决定和明确修订，其余继续继承；未解决冲突列缺口，不静默丢弃。当前尚未完成这份逐方法迁移覆盖表，因此只能说资料已列入，不能说全部设计已对齐或可跳过P0冻结。

公共发行包不包含Project实例，P0须将有效基础契约及说明迁入受控公共目录，保留原来源和版本映射；在此之前完整开发须同时读取v0.1与v0.2。本次只修导航与清单，不改旧Run及冻结规范内容。
