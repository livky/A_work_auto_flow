# AI 起始导航

本页回答“为了当前任务，下一步应读什么”。保持短小；细节放在目标对象附近。

## 固定顺序

1. 读 [NOW.md](NOW.md)，确认当前重点、阻塞和最近变更。
2. 读派生的 [generated/workspace-index.md](generated/workspace-index.md)；若不存在，运行 `refresh-index`。
3. 根据任务路由：

| 用户意图          | 首选位置                                     | 关键产物                          |
| ----------------- | -------------------------------------------- | --------------------------------- |
| 理解核心模型算法 | `core-algorithms/<slug>/` | 全局算法卡、关联核心算法、接口 |
| 设计或修改算法    | `core-algorithms/<slug>/`               | 核心算法卡、公式、V&V/UQ、基准 Run    |
| 数据分析/异常诊断 | `runs/` + `data/` | Run、数据卡、契约、血缘、复盘     |
| 文献调研/专题研究 | `research/<topic>/`                        | 计划、证据台账、仿真、综合        |
| 维护分析工具      | `tools/`                                   | 工具卡、CLI、测试、适配器         |
| 查历史经验        | `knowledge/`                               | ADR、复盘、模式、周期回顾         |
| 做 PPT/文档/报告  | `reports/`                                 | brief、引用 Run、报告源、manifest |
| 接入外部平台      | `governance/` + `tools/external/`        | 授权记录、数据流、适配器、审计    |

## 检索提示

- 日常统一入口为 `workbench.cmd`（注册后 `rdwork`）；安装/升级使用 `setup.cmd`，合成测试用 `workbench.cmd workbench --demo`。见 [一键部署与工作台](../docs/SETUP_WORKBENCH.md)。

- 记录、确认和纠错先看 [MEMORY.md](MEMORY.md)。简单任务不必创建完整项目或套工作流。
- 当前组件能力用 `doctor` 检查；正式结论、封存和跨文档失效使用 [证据准入手册](../docs/EVIDENCE_CONTROLS.md)。探索记录不自动成为正式依据。
- 查看证据依据、复核、失效时间与报告影响，使用 evidence-inspection Skill 或 `evidence-view --serve`；变化观察用 `evidence-monitor`，只写本机观察记录和候选。见 [查看与监测手册](../docs/EVIDENCE_VIEW_MONITOR.md)。
- 接入已有算法/文档/仓库时，按 [已有材料接入指南](../docs/EXISTING_MATERIALS.md) 从用户给的路径和用途开始；助手负责归组与登记，不要求用户预先建项目或填完整核心算法模板。
- 历史 Run 使用 `search-runs "关键词" --project <slug>`；命令即时读源记录，注意复核状态与 `needs_revalidation`，再按链接读取证据。
- 先按稳定 ID 检索：项目 `PRJ-*`、核心算法 `MOD-*`、数据 `DATA-*`、运行 `RUN-*`、决策 `ADR-*`、事故 `INC-*`、报告 `REP-*`。
- 先找卡片和 manifest，再读大文件。
- 算法问答用 workspace-context Skill 或 retrieve-context（已知核心算法加 --module MOD-ID），读取 context_path 和 manifest_path。目标算法说明优先全文，其他证据按角色/长度/预算装载；检查 required_not_full、module_algorithm_missing、候选与风险。
- 证据不足、验证失败或文档—实现冲突时，主动用 context-feedback CTX-ID --outcome unresolved/conflict 记录具体缺口并扩展；最多 focus→investigate→wide 两次，不扩大读取授权或自动增加预算。保持用户 include/full/exclude，达到上限后说明缺失输入。细节见 [检索手册](../docs/RETRIEVAL.md)。
- 发现漏检、错误版本或用户明确纠正时，用 retrieval-feedback 保存真实反馈；按需汇总、改别名/来源映射并运行 evaluate-retrieval，不把 AI 判断伪装成人工确认。
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
