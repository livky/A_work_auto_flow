# AI 工作流目录

这些工作流是可选方法参考。只有当前任务确实受益时才读取最匹配的一份，不要求每个任务匹配工作流；用户要求和根规则优先。历史记录与纠错以 `context/MEMORY.md` 为准，不重复实现一套记忆规则。

| 用户意图 | 工作流入口 |
|---|---|
| 算法问答、文档/代码核对与证据不足扩展（已安装） | `workspace-context/SKILL.md` |
| 深入调研、论文、技术路线、仿真研究 | `research-loop/SKILL.md` |
| 数据异常、指标漂移、跨核心算法诊断 | `analysis-diagnosis/SKILL.md` |
| 理解、设计或修改公司文档定义的核心算法/测校项 | `core-algorithm-design/SKILL.md` |
| PPT、Word、PDF、周报和正式汇报 | `report-production/SKILL.md` |
| 分批导入材料、关键词索引、算法/代码映射更新、整理与交接 | `context-maintenance/SKILL.md` |
| 查看结论依据、复核和报告影响；只读监测变化、维护候选 | `evidence-inspection/SKILL.md` |

workspace-context 和 context-maintenance 已通过校验并安装到 .agents/skills；入口仅链接本目录方法源，避免两份规则漂移。新会话/重载后可使用 $workspace-context、$context-maintenance；当前未发现技能时可直接让 AI 读源文件。其他流程保留为按需方法，不安装全部技能。

证据查看与只读监测新增 $evidence-inspection，已安装轻量入口。升级旧副本时可执行 `automation/python.ps1 automation/scripts/install_workspace_skills.py --name evidence-inspection --apply`，不覆盖其他技能的本地修改。

工作流负责方法，`AGENTS.md` 负责稳定规则，确定性脚本负责机械动作，外部系统适配器负责权限受控的数据与工具访问。不要在三处复制同一长篇说明。
