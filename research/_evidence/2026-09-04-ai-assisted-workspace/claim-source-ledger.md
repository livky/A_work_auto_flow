# Claim-to-source ledger

访问日期：2026-09-04

| 声明 | 来源 | 发布者/作者 | 日期 | URL | 备注 |
|---|---|---|---|---|---|
| 短 `AGENTS.md` 作为地图，详细知识进入结构化 docs，并机械检查 | Harness engineering | Ryan Lopopolo / OpenAI | 2026-02-11 | https://openai.com/index/harness-engineering/ | 新项目实战，长期效果仍待观察 |
| Codex 从根向 cwd 合并指令，更近文件优先，默认 32 KiB | Custom instructions with AGENTS.md | OpenAI | 持续更新 | https://learn.chatgpt.com/docs/agent-configuration/agents-md | 官方产品机制 |
| AGENTS、memory、skills、MCP、subagents 是互补层，skills 渐进披露 | Customization | OpenAI | 持续更新 | https://learn.chatgpt.com/docs/customization/overview | 官方产品机制 |
| 上下文是有限资源，应按需检索并使用压缩/笔记 | Effective context engineering | Anthropic | 2025-09-29 | https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents | 厂商工程经验 |
| 研究数据治理应覆盖六阶段生命周期 | NIST RDaF 2.0 | Hanisch 等 / NIST | 2024-02 | https://doi.org/10.6028/NIST.SP.1500-18r2 | 可裁剪框架，不是目录标准 |
| 来源应表达实体、活动、执行者和派生 | PROV Overview / PROV-DM | W3C | 2013-04-30 | https://www.w3.org/TR/prov-overview/ | W3C 标准族 |
| 数据应可发现、可访问、可互操作、可复用 | FAIR Guiding Principles | Wilkinson 等 | 2016-03-15 | https://doi.org/10.1038/sdata.2016.18 | FAIR 不等于公开 |
| Run 可记录参数、指标、代码与产物，数据可有 source/digest/schema/profile | MLflow Tracking / Dataset | MLflow Project | 持续更新 | https://mlflow.org/docs/latest/tracking | 工具能力，不要求当前安装 |
| Dataset/Job/Run 可表达运行和数据血缘 | OpenLineage Object Model | OpenLineage Project | v1.53.0 | https://openlineage.io/docs/spec/object-model/ | 偏数据管道，可扩展 |
| 显著事件应有无责、可执行的正式复盘 | Postmortem Culture | Lunney、Lueder / Google SRE | 2016 | https://sre.google/sre-book/postmortem-culture/ | 从在线可靠性类比到研发诊断 |
| 参数化报告可复用同一源生成不同输出 | Quarto Parameters | Quarto Project / Posit | 持续更新 | https://quarto.org/docs/computations/parameters.html | 复杂 PPT 仍需视觉 QA |
| SSDF 强调安全开发、来源、设计决策和持续改进 | Secure Software Development Framework | NIST | SP 800-218 v1.1 | https://csrc.nist.gov/projects/ssdf | 风险导向参考 |
| OpenAI API 默认不训练，但默认日志可能保留 30 天；ZDR/MAM 需批准 | Data controls | OpenAI | 持续更新 | https://developers.openai.com/api/docs/guides/your-data | 不代表用户公司合同或产品配置 |

停止检索原因：指令分层、渐进上下文、数据/元数据分离、Run 与血缘、知识闭环和安全边界均已有一手或标准证据，继续检索主要产生同类工具重复，未发现会改变总体架构的反证。
