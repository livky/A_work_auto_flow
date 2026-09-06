# AI 辅助研发工作区：成熟实践与本地设计

> 历史设计依据，描述当时参考的外部实践，不代表当前已实现功能或现行协作规则。当前用法以根 README、AGENTS 和 ARCHITECTURE 为准；外部产品信息保留原调研日期，不作为当前配置保证。

日期：2026-09-04  
受众：复杂工程研发、算法、数据与技术管理协作者

## 直接结论

适合本场景的不是一个巨型提示词，也不是一开始就上重型知识图谱，而是“可版本化的轻量控制平面 + 受控外部数据平面 + 可执行验证闭环”。根指令只负责稳定边界和路由；模块、数据、研究和报告拥有各自事实源；AI 通过索引和显式引用按需取上下文；重复流程逐步晋升为脚本、技能、契约与机械检查。

## 为什么根指令必须短小

OpenAI 的 agent-first 工程实践记录了单个巨大 `AGENTS.md` 的失效：它挤占任务上下文、让所有规则失去优先级、迅速陈旧且难以机械校验；实践转向短小入口、结构化文档、执行计划和自动漂移检查。[OpenAI：Harness engineering](https://openai.com/index/harness-engineering/)

Codex 官方机制也支持分层：它从项目根向当前目录收集 `AGENTS.md`，更近的文件优先，默认合并上限为 32 KiB。因而本工作区使用根级通用规则和项目/研究/数据/工具的就近规则。[OpenAI Docs：Custom instructions with AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md)

## 为什么要渐进加载上下文

长上下文仍有有限注意预算。成熟做法是保留轻量标识符、路径、索引和摘要，运行时再加载具体证据；长任务则用压缩、结构化笔记和专业分工保持连续性。[Anthropic：Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)

Codex 官方把 `AGENTS.md`、memory、skills、MCP 和 subagents 定义为互补层：稳定行为放 AGENTS，可复用流程放 skill，外部系统接入用 MCP，且 skill 按元数据 → `SKILL.md` → 参考/脚本逐层披露。[OpenAI Docs：Customization](https://learn.chatgpt.com/docs/customization/overview)

## 为什么大数据要留在共享盘

W3C PROV 把 provenance 定义为实体、活动和人员如何参与产出，并强调来源信息支持质量、可靠性与可信度判断。[W3C：PROV Overview](https://www.w3.org/TR/prov-overview/)

FAIR 原则要求数字对象可发现、可访问、可互操作和可复用，重点是持久标识、丰富元数据、协议、词汇和详细来源；FAIR 并不等同于向所有人公开。[Wilkinson 等：FAIR Guiding Principles](https://doi.org/10.1038/sdata.2016.18)

因此本框架不复制公司原始数据，而保存稳定数据 ID、受控 URI、schema、版本/指纹、敏感等级和派生关系。需要规模化后，可把这些中立 schema 映射到 DVC、MLflow、OpenLineage 或公司数据目录；例如 MLflow 能把数据源、digest、schema 与 profile 绑定到 Run，[MLflow：Dataset Tracking](https://mlflow.org/docs/latest/dataset/)；OpenLineage 则以 Dataset、Job、Run 和 facets 表达运行与数据血缘，[OpenLineage：Object Model](https://openlineage.io/docs/spec/object-model/)。

## 为什么要把每次分析固化为 Run

若只保留 Notebook 或最终图，后续无法可靠回答“哪批数据、哪段代码、哪些参数和环境产生了这个结论”。本框架的 `run.json` 将输入、实现、配置、环境、指标、产物、状态与父任务绑定，并允许以后接入实验平台，而不改变对象语义。

对于工程模型，完成条件还必须区分：

$$
\text{可信度} = f(\text{Verification},\ \text{Validation},\ \text{Uncertainty},\ \text{适用域}).
$$

Run 记录能够证明“做过什么”，但不能自动证明科学有效；反证设计、数据适用性和领域评审仍需工程师负责。

## 为什么历史问题要用 ADR 与无责复盘

重要路线选择用短小 ADR 保存背景、决定、状态和后果；逆转时保留原记录并标记被替代。[Michael Nygard：Documenting Architecture Decisions](https://www.cognitect.com/blog/2011/11/15/documenting-architecture-decisions)

Google SRE 的实践把复盘定义为事件、影响、处置、根因与防复发行动的书面记录，并建议预先定义触发条件、保持无责、正式评审和追踪行动项。[Google SRE：Postmortem Culture](https://sre.google/sre-book/postmortem-culture/)

这两类文档比“让 AI 永久记住一切”更可靠：聊天/自动记忆可以提供召回候选，但只有经验证和审阅的内容才晋升为正式知识。

## 为什么安全不能只靠提示词

NIST SSDF 把保护软件组件、记录来源、跟踪安全需求与设计决策纳入安全开发，并强调风险驱动与持续改进，而非僵化清单。[NIST：Secure Software Development Framework](https://csrc.nist.gov/projects/ssdf)

外部内容中的文字可能是提示注入；所以论文、网页、邮件、日志和插件输出都只作为数据。敏感动作依赖文件权限、网络策略、沙箱、审批与审计。公开产品声明也不能替代公司合同审查：例如 OpenAI API 数据默认不用于训练，但默认滥用监控日志可能含客户内容并最长保留 30 天，特定保留控制需要批准。[OpenAI：Data controls](https://developers.openai.com/api/docs/guides/your-data)

## 实施顺序

1. 先跑通一个低敏项目：项目卡 → 模块卡 → 数据卡/契约 → Run → 报告 → 知识写回。
2. 再把重复分析提升为 `tools/` CLI 和 `automation/workflows/` 工作流；获批后可迁移为仓库级技能。
3. 然后接入 Git/CI、文档漂移检查、实验跟踪与报告自动渲染。
4. 最后在公司批准下连接共享盘 inventory、内部日志、任务系统和企业文档平台。

## 限制与分歧

- OpenAI/Anthropic 的 agent-first 经验较新，不能证明多年后仍是最佳结构；因此本框架采用可迁移开放文件，而非深度绑定某个产品。
- MLflow、DVC、OpenLineage、Snakemake 等工具职责有重叠，当前信息不足以替用户选定技术栈；第一阶段只定义兼容对象。
- 数据保留年限、外部 AI 许可、设备控制边界和真实共享盘策略必须由公司制度决定。
- 模板能改善一致性，但不能替代领域 V&V、测量不确定度分析和人工技术责任。
