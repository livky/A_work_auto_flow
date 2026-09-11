# AI 工作流目录

这些工作流按任务使用；框架开发、修复和开发规范调整由根规则要求使用 development-checks，其余只在任务需要时读取。用户要求和根规则优先。历史记录与纠错以 `context/MEMORY.md` 为准，不重复实现一套记忆规则。

| 用户意图 | 工作流入口 |
|---|---|
| 算法问答、文档/代码核对与证据不足扩展（已安装） | `workspace-context/SKILL.md` |
| 深入调研、论文、技术路线、仿真研究 | `research-loop/SKILL.md` |
| 数据异常、模型设计与验证 | `workspace-context/SKILL.md` 定位依据，`research-loop/SKILL.md` 执行与记录 |
| PPT、Word、PDF、周报和正式汇报 | `research-loop/SKILL.md` 固定依据与报告登记，按文件格式使用可用的文档技能 |
| 分批导入材料、关键词索引、算法/代码映射更新、整理与交接 | `context-maintenance/SKILL.md` |
| 查看结论依据、复核和报告影响；只读监测变化、维护候选 | `evidence-inspection/SKILL.md` |
| 开发或修复框架、必读文档维护与按风险选择验证 | `development-checks/SKILL.md` |
| 按内容来源查找、选择和展开固定材料，兼容旧表示 | `material-query/SKILL.md` |
| 跨领域结构比较、适用与不可迁移边界 | `association-exploration/SKILL.md` |
| 来源变化与反证的实际语义审查和维护 | `semantic-maintenance/SKILL.md` |

当前保留且登记八个轻量 Skill 入口：workspace-context、context-maintenance、evidence-inspection、research-loop、development-checks、material-query、association-exploration、semantic-maintenance。`.agents/skills` 入口只链接本目录方法源，避免两份规则漂移；新会话未发现时可直接让 AI 读源文件。诊断、算法设计、报告生产三个旧独立流程已合并到上述入口；历史原文和指纹见本次开发 Run 的退休清单。

安装器默认预览，`--apply` 才新建缺失入口，`--name` 可选择登记项；已有不同内容会保留并输出合并差异，不静默覆盖用户规则。框架升级使用根 `setup.cmd --target`，不要以单独安装一个 Skill 代替整套升级。

方法中的“记录”须区分对象内 Run、不可变记忆与检索投影；文件 Q/CTX 与记忆 QMEM/PKT 分别使用对应入口。L1 技术单元、L2 研究经过、L3 分类经验、L4 概览和独立双文稿的最新格式见 [分层记录标准](../../docs/RESEARCH_RECORDING.md)，框架文档同步见 [维护手册](../../docs/DOCUMENTATION_MAINTENANCE.md)。

工作流负责方法，`AGENTS.md` 负责稳定规则，确定性脚本负责机械动作，外部系统适配器负责权限受控的数据与工具访问。不要在三处复制同一长篇说明。
