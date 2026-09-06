# 当前状态

更新日期：2026-09-06

## 当前实现

- “模块”已改为核心算法（测校项），目录 core-algorithms；仅收录公司算法/模块文档定义的关键模型算法。创建命令 new-core-algorithm 要求 --source-document，旧命令同样检查；MOD-ID 和 module.json 等兼容字段保留。普通脚本默认应用代码，不自动作为核心实现。变更证据见 docs/design/core-algorithms-rename-plan.md。

- Windows x64 迁移入口已补齐：`portable.cmd pack --apply` 创建完整离线 ZIP，解压后 `portable.cmd check` 自检；含中文/空格新路径迁移及索引重建通过，47 项回归通过。说明见 docs/WINDOWS_PORTABILITY.md，证据见 docs/design/windows-portability-plan.md；尚未跨物理电脑验证。

- core-algorithms、runs、research、tools 平级；project 仅可选交付聚合，旧 Run 兼容。尚未导入真实公司算法或数据。
- 已有工作区内 Python、Qdrant local、多语言 MiniLM 与 OCR，正常索引/推理离线；原件先保存，索引随后增量刷新，无文件保存监听。
- 当前上下文使用 focus→investigate→wide：目标算法全文优先，代码/Run/研究/知识按角色、长度和必要性选择，支持 include/full/exclude 和持久偏好。未解决/冲突反馈可触发下一阶段，最多两次；预算和排除项保留。
- CTX 调查链、CF 上下文反馈、Q 查询与单源反馈分别保留。候选预览最多 40 项，完整选择清单另存；缺失算法或预算不足显式报告。
- workspace-context 与 context-maintenance 已安装为仓库 Skill，当前会话已识别；入口只引用 automation/workflows 的方法正文。
- 全套 46 项测试通过，含真实本地模型离线分阶段检查；上下文后续调整通过定向回归及隔离 CLI 父子链验证。证据见 PLAN.md 和 docs/design/adaptive-context-review-2026-09-06.md。

## 下一步

1. 提供首批低敏算法文档、关键代码、历史结果、研究/PPT 路径，按维护 Skill 分批接入并核对阅读清单。
2. 用真实问题检查召回、文档—代码一致性与上下文必要性，再调整角色和偏好；真实评估集仍为空，不宣称质量已获业务验证。
3. 公司数据边界按治理目录执行；当前没有企业连接器或自动备份。Git 已初始化，公开仓库仅发布框架源码、规则、模板与测试，本机环境和查询历史排除。

限制：AI/用户判断是否解决，程序不自动验证答案；OCR 不理解复杂图形；同一 Qdrant local 数据库串行使用；扩展不突破读取授权、不自动增加预算或撤回旧聊天内容。
