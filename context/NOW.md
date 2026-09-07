# 当前状态

更新日期：2026-09-07

## 当前实现

- 2026-09-07 按用户修正将材料分类下拉框改成紧凑多选勾选项；多个大类取并集，与搜索叠加，未选分类显示全部，已有材料勾选保持。前端 8 项测试与浏览器 3 项回归通过，预构建资源已更新。

- 2026-09-07 已提交半成品基线 `47809c4`。随后修复关系页勾选未参与图范围计算的问题：多选按一/两跳关联联动图、局部聚类和导出；清空恢复全图，明确聚焦时退出多选。材料列表新增大类筛选，与标题/ID 搜索叠加；跨分类保留勾选，同名材料显示 ID 区分。新增勾选/排除单元测试及跨分类浏览器回归；8 项前端测试、3 项浏览器测试和 116 项 Python 回归通过。

- 2026-09-07 已完成模块化工作台与材料关系：React/TypeScript 预构建界面、版本化 API、后台任务、辐射/聚合/证据链、按需关键词/本地语义/Louvain、桥接候选及 AI 摘要与 CLI。原始证据不因展示或候选改变；缓存、布局与候选位于排除发布的 `.local/workbench`。完整七步计划保留在 docs/design/workbench-relations-plan.md，操作 docs/MATERIAL_RELATIONS.md，开发 docs/WORKBENCH_DEVELOPMENT.md；验证证据 RUN-20260907T071646Z-CE49506865C4。Windows 中文路径无 Node 启动及离线完整环境复用通过；尚未在第二台物理机或真实公司问题上验收。

- 2026-09-07 已完成材料关系可视化工具调研与现有关系盘点。建议工作台增加问题辐射、主题聚合、证据链及 AI 局部关系摘要；本批仅调研，未实现图功能或新的底层存储。见 [调研建议](../research/material-relationship-view/SYNTHESIS.md)，证据 RUN-20260907T063633Z-159B86592CDD；业务有效性和交互性能待验证。


- 2026-09-07 已增加 setup.cmd 一键 Windows 完整/基础安装、--target 原位保留升级、SHA-256 备份恢复、--register/--unregister 幂等用户命令。已在本机注册 rdwork；工作台聚合证据、模块清单、监测启停与能力检查。合成数据位于 Git/离线包排除的 .local/test-workspace，正式记录保持独立。手册 docs/SETUP_WORKBENCH.md。
- 本批最终完整验证 102 项全部通过，无跳过；实际在线部署及离线复用、真实嵌入/OCR、自包含 cmd 升级恢复和命令注册均已验证。证据 RUN-20260907T042941Z-D9E5F49FE803；尚无另一台物理机或业务有效性验收。跨会话调度未创建，工作台持续监测需手动开启。

- 2026-09-07 已增加证据工作台：浏览器搜索/筛选、保存原因、来源预览、Run 输入/产物、复核历史、失效观察时间与报告依赖路径；不依赖向量/OCR。新增 evidence-monitor 单次只读监测，原子保存本机基线、事件和维护候选，重复不晋升。已安装 evidence-inspection 技能入口；定时频率尚待用户选择，未创建定时自动化。用法见 docs/EVIDENCE_VIEW_MONITOR.md。
- 本批回归 86 项，79 通过、7 原有模型测试跳过；界面及只读 HTTP/中文路径迁移已验证。首次监测已建基线，相同内容的重复日志只提出比较候选。证据见 RUN-20260907T023756Z-035991E67BBA；完整模型环境及真实业务验收仍未完成。

- “模块”已改为核心算法（测校项），目录 core-algorithms；仅收录公司算法/模块文档定义的关键模型算法。创建命令 new-core-algorithm 要求 --source-document，旧命令同样检查；MOD-ID 和 module.json 等兼容字段保留。普通脚本默认应用代码，不自动作为核心实现。变更证据见 docs/design/core-algorithms-rename-plan.md。

- Windows x64 迁移入口已补齐：`portable.cmd pack --apply` 创建完整离线 ZIP，解压后 `portable.cmd check` 自检；含中文/空格新路径迁移及索引重建通过，47 项回归通过。说明见 docs/WINDOWS_PORTABILITY.md，证据见 docs/design/windows-portability-plan.md；尚未跨物理电脑验证。

- core-algorithms、runs、research、tools 平级；project 仅可选交付聚合，旧 Run 兼容。尚未导入真实公司算法或数据。
- 框架支持工作区内 Python、Qdrant local、多语言 MiniLM 与 OCR，正常索引/推理离线；原件先保存，索引随后增量刷新，无文件保存监听。该源码副本早期缺少运行时和模型；2026-09-07 已通过 setup 补齐并实际自检，具体边界与本批 Run 见上方。
- 当前上下文使用 focus→investigate→wide：目标算法全文优先，代码/Run/研究/知识按角色、长度和必要性选择，支持 include/full/exclude 和持久偏好。未解决/冲突反馈可触发下一阶段，最多两次；预算和排除项保留。
- CTX 调查链、CF 上下文反馈、Q 查询与单源反馈分别保留。候选预览最多 40 项，完整选择清单另存；缺失算法或预算不足显式报告。
- workspace-context 与 context-maintenance 已安装为仓库 Skill，当前会话已识别；入口只引用 automation/workflows 的方法正文。
- 历史完整副本有 46 项测试通过，含真实本地模型离线分阶段检查；后续上下文调整通过定向回归及隔离 CLI 父子链验证。该历史证据见 PLAN.md 和 docs/design/adaptive-context-review-2026-09-06.md，不能证明本副本当前具备模型能力。
- 研发可靠性第一批已实现：结论级 claims、复核版本绑定、supports/input 跨文档失效传播、check-run/finalize-run、按 scope 筛选正式结论、doctor 与严格 verify。用法见 [证据准入手册](../docs/EVIDENCE_CONTROLS.md)，实现与验证见 RUN-20260906T140125Z-6DEFDCB569C4；尚无真实业务结论封存。
- 本批最终 core 回归共 72 项，65 通过、7 因缺本地模型跳过；full 实测返回失败，缺 vector/OCR 且存在 skipped。index-knowledge 仍因缺 qdrant_client 退出 2；未改成其他检索配置来绕过此问题。

## 下一步

2026-09-06 结构评审已完成，见 [工作智能体对比与改进建议](../research/agent-workspace-review/SYNTHESIS.md)。评审时基线为 49 项测试中 42 通过、7 跳过；该历史观察保留于 RUN-20260906T130218Z-252152E16BC5。第一批已针对其中的正式准入与跨研究失效缺口实施，范围见 [实施计划](../docs/design/evidence-controls-plan.md)；其他路线建议和真实业务验收仍待后续推进。

1. 提供首批低敏算法文档、关键代码、历史结果、研究/PPT 路径，按维护 Skill 分批接入并核对阅读清单。
2. 用真实问题检查召回、文档—代码一致性与上下文必要性，再调整角色和偏好；真实评估集仍为空，不宣称质量已获业务验证。
3. 公司数据边界按治理目录执行；当前没有企业连接器或自动备份。Git 已初始化，公开仓库仅发布框架源码、规则、模板与测试，本机环境和查询历史排除。

限制：AI/用户判断是否解决，程序不自动验证答案；OCR 不理解复杂图形；同一 Qdrant local 数据库串行使用；扩展不突破读取授权、不自动增加预算或撤回旧聊天内容。
