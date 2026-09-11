# AI 起始导航

本页回答“为了当前任务，下一步应读什么”。保持短小；细节放在目标对象附近。

## 固定顺序

1. 读 [NOW.md](NOW.md)，确认当前重点、阻塞和最近变更。
2. 需要定位业务对象时，读派生的 [generated/workspace-index.md](generated/workspace-index.md)；若不存在，运行 `refresh-index`。框架开发直接进入下表的开发 Skill，不必通读对象清单。
3. 根据任务路由：

| 用户意图          | 首选位置                                     | 关键产物                          |
| ----------------- | -------------------------------------------- | --------------------------------- |
| 理解核心模型算法 | `core-algorithms/<slug>/` | 全局算法卡、关联核心算法、接口 |
| 设计或修改算法    | `core-algorithms/<slug>/`               | 核心算法卡、公式、V&V/UQ、基准 Run    |
| 数据分析/异常诊断 | 实际归属对象的 `runs/` + `data/`；无归属用根 `runs/` | Run、数据卡、契约、血缘、复盘 |
| 文献调研/专题研究 | `research/<topic>/`                        | 计划、证据台账、仿真、综合        |
| 维护分析工具      | `tools/`                                   | 工具卡、CLI、测试、适配器         |
| 查历史经验        | `knowledge/`                               | ADR、复盘、模式、周期回顾         |
| 理解研究过程/文稿 | 目标对象的 memory document / outline / section-context | 技术单元、固定章节、完整/精简文稿 |
| 维护框架与文档 | [development-checks](../automation/workflows/development-checks/SKILL.md) | 六份短文档的前后完整阅读/维护、按风险验证及任务记录 |
| 做 PPT/文档/报告  | `reports/`                                 | brief、引用 Run、报告源、manifest |
| 接入外部平台      | `governance/` + `tools/external/`        | 授权记录、数据流、适配器、审计    |

## 检索提示

- 按摘要、全文、章节、专题、领域或原始材料查询，优先使用工作台“材料查询”或 `workbench.cmd material-query`，先检查可用性/缺口再显式组包。语义联想和新反证维护分别用 association-exploration、semantic-maintenance Skill。见[材料查询手册](../docs/MATERIAL_QUERY.md)。规范正文仍由版本记忆保存。

- 跨材料关联可用工作台“材料关系”，或 `workbench.cmd relations export --center "实际 ID" --hops 2 --format markdown`。先按关系定位原文缺口，保持排除项与预算；相似与聚类不提升可信状态。见 [材料关系手册](../docs/MATERIAL_RELATIONS.md)。

- 日常统一入口为 `workbench.cmd`（注册后 `rdwork`）；安装/升级使用 `setup.cmd`，合成测试用 `workbench.cmd workbench --demo`。见 [一键部署与工作台](../docs/SETUP_WORKBENCH.md)。

- 记录、确认和纠错先看 [MEMORY.md](MEMORY.md)。简单任务不必创建完整项目或套工作流。
- 当前 L1 是完整技术单元，L2 研究经过、L3 经验、L4 整体概览；章节和完整/精简文稿独立保存。定义只从[研究记录标准](../docs/RESEARCH_RECORDING.md)展开，不按历史计划猜测。查局部经验先用 memory search，理解完整研究先读文稿目录/章节；原始证据再按固定引用追溯。
- 框架开发按 Skill 的六份短文档理解现状；模块影响只在 [ARCHITECTURE](../ARCHITECTURE.md) 维护，细节与历史分类从 [docs/README](../docs/README.md) 展开。本工作区的演进记录在 `projects/architecture-evolution/`，公共发行包不依赖项目实例。
- 当前组件能力用 `doctor` 检查；正式结论、封存和跨文档失效使用 [证据准入手册](../docs/EVIDENCE_CONTROLS.md)。探索记录不自动成为正式依据。
- 查看证据依据、复核、失效时间与报告影响，使用 evidence-inspection Skill 或 `evidence-view --serve`；变化观察用 `evidence-monitor`，只写本机观察记录和候选。见 [查看与监测手册](../docs/EVIDENCE_VIEW_MONITOR.md)。
- 接入已有算法/文档/仓库时，按 [已有材料接入指南](../docs/EXISTING_MATERIALS.md) 从用户给的路径和用途开始；助手负责归组与登记，不要求用户预先建项目或填完整核心算法模板。
- 历史 Run 使用 `search-runs "关键词" --project <slug>`；命令即时读源记录，注意复核状态与 `needs_revalidation`，再按链接读取证据。
- 先按稳定 ID 检索：项目 `PRJ-*`、核心算法 `MOD-*`、数据 `DATA-*`、运行 `RUN-*`、决策 `ADR-*`、事故 `INC-*`、报告 `REP-*`。
- 先找卡片和 manifest，再读大文件。
- 算法问答用 workspace-context Skill 或 retrieve-context（已知核心算法加 --module MOD-ID），读取 context_path 和 manifest_path。目标算法说明优先全文，其他证据按角色/长度/预算装载；检查 required_not_full、module_algorithm_missing、候选与风险。
- 证据不足、验证失败或文档—实现冲突时，主动用 context-feedback CTX-ID --outcome unresolved/conflict 记录具体缺口并扩展；最多 focus→investigate→wide 两次，不扩大读取授权或自动增加预算。保持用户 include/full/exclude，达到上限后说明缺失输入。细节见 [检索手册](../docs/RETRIEVAL.md)。
- 发现漏检、错误版本或用户明确纠正时，材料查询 Q 用 `retrieval-feedback`，材料上下文 CTX 用 `context-feedback`；规范记忆查询 QMEM 用 `memory feedback`，记忆材料包 PKT 用 `memory context` 的 `feedback_from` 继承扩展。保存真实回执并按对应链路评测，不混用 ID，也不把 AI 判断伪装成人工确认。
- 批量导入/变更用 context-maintenance Skill；按根规则分批写回和更新检索索引。安装入口在 .agents/skills，方法源在 automation/workflows；新会话发现技能前可显式读源。
- 只读取和任务相关的时间窗、字段、日志片段或论文章节。
- 相似历史问题只提供候选假设；必须用当前数据重新验证。

## 创建入口

```powershell
.\automation\workspace.ps1 new-project <slug> --title "标题"
.\automation\workspace.ps1 new-research <slug> --title "研究问题"
.\automation\workspace.ps1 new-core-algorithm <slug> --title "核心算法名" --source-document "公司算法文档名称或编号"
.\automation\workspace.ps1 new-run --title "分析目的" --module MOD-ID
.\automation\workspace.ps1 search-runs "关键词" --project <slug>
.\automation\workspace.ps1 refresh-index
.\automation\workspace.ps1 build-context --project <slug> --task "本次目标"
```

## 不应直接做的事

- 不把整个共享盘、全部日志或所有论文一次加入上下文。
- 不把未复核 AI 摘要当成正式结论。
- 不把真实密钥、账号、内部 URL 查询参数、人员隐私写入文档。
- 不在没有数据卡/契约/范围说明时批量修改或复制数据。
- 不让报告中的手填数字脱离生成它的 Run。
