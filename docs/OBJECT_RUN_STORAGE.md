# 对象、Run 与执行回执：当前默认保存逻辑

核对日期：2026-09-10。本文描述当前实现，区分程序自动行为、AI 工作方法和未实现的自动化；对象已有策略或本次明确要求可以改变默认行为。

当前模块职责以 [ARCHITECTURE.md](../ARCHITECTURE.md) 为入口；保存/归属规则变化时，按 [文档维护约定](DOCUMENTATION_MAINTENANCE.md) 同步本页、执行手册与对应 Skill。

## 三个概念

1. **大类型对象**：研究、项目、核心算法、Run、数据、工具、知识、报告。每个具体条目有自己的身份、原始卡片和可选版本记忆。
2. **对象内 Run**：某条目开展的一次可独立说明的分析、实验、变换或验证。它仍是同一种 Run，有独立 RUN-ID、run.json、输入、输出、执行状态和复核历史。
3. **执行回执**：同一 Run 下调用一次 `run-execute` 的结果，放在 `.run-captures/唯一编号/`。它没有新的 RUN-ID，不是子 Run，也不是 L1 技术单元。

根 `runs/` 是一种物理位置，工作台的 Run 类型是跨目录的逻辑分类。研究内部的 Run 同样会被发现为 Run 类型条目，并不是在根 runs/ 又存了一份。

“大的 Run”若指根 runs/ 的条目，与对象内 Run 使用相同结构，仅 owner_id 与位置不同。若它承担长周期、大型目标，当前规则优先用 Project 或 Research 作父对象。代码也允许 `new-run --owner RUN-ID` 建嵌套 Run，但没有第二套大小 Run 数据模型。

## 八类对象的保存位置

下面均为相对工作区根的示意路径；实际以 `memory list-owners` 返回的 native_ref 和 memory_home 为准。`r` 表示新 Run 的目录名。

| 大类型 | 本体示例 | 对象自己的版本记忆 | 对象内新 Run |
|---|---|---|---|
| 研究 Research | research/主题/research.json、计划、证据台账、综合 | research/主题/memory/ | research/主题/runs/r/ |
| 项目 Project | projects/项目/project.json、目标、里程碑与引用 | projects/项目/memory/ | projects/项目/runs/r/ |
| 核心算法 | core-algorithms/算法/module.json、算法文档及实现映射 | core-algorithms/算法/memory/ | core-algorithms/算法/runs/r/ |
| Run | runs/原运行/run.json，或其他对象内的 run.json | 原运行目录/memory/ | 原运行目录/runs/r/ |
| 数据 Data | data/catalog/输入.dataset.json | 该登记文件路径.memory/ | 该登记文件路径.memory.runtime/runs/r/ |
| 工具 Tool | tools/registry.json 中的工具条目，或 tool.json | tools/memory/工具ID/ | tools/runtime/工具ID/runs/r/ |
| 知识 Knowledge | knowledge/经验.md，或对应 .evidence.json | 实际身份所绑定的文件路径.memory/ | 该 memory_home.runtime/runs/r/ |
| 报告 Report | 报告登记 JSON、证据边车或已采用的 Markdown | 实际身份所绑定的文件路径.memory/ | 该 memory_home.runtime/runs/r/ |

数据即使以 dataset.json 登记，当前适配器也使用文件旁置方式；不能凭目录外观套用研究的路径规则。知识/报告究竟绑定正文还是边车，须看 native_ref。临时 FILE 身份必须先 adopt-owner 成为稳定对象才能拥有新 Run；采用身份不改写原文。

上表的 memory/ 是保存逻辑记录的容器，不是原数据目录。首次规范提交/采用对象时按需创建，不要求每个条目初始就有完整目录。

## 新 Run 内部统一保存什么

```text
某对象/
├── memory/                       对象自己的 L1–L4、文稿与辅助记录
└── runs/某个 Run/
    ├── run.json                  身份、归属、输入/产物登记、状态等
    ├── README.md                 问题、方法、结果与限制
    ├── lineage.jsonl             创建时建立的血缘日志文件
    ├── memory/                   此 Run 自己的版本记忆，按需创建
    ├── steps.jsonl               AI 按需记录的步骤，并非自动捕获
    └── .run-captures/某次执行/
        ├── outputs/              本次生成结果
        ├── stdout.txt
        ├── stderr.txt
        ├── execution.json        实际命令、输入版本、时间、退出码
        └── registration.json     登记前后版本与恢复依据
```

`new-run` 只创建 run.json、README.md、空 lineage.jsonl，不执行实验、不填写技术结论。`run-execute` 使用当前 Python，固定明确的脚本/输入指纹，在独立 outputs 目录执行并登记输出与日志；失败和超时也保存。已有文件或其他工具结果用 `run-register` 登记当前版本。原件默认只读，外部数据不因登记而复制进工作区。

同一 Run 多次执行时，每次保留新回执和结果目录，Run 操作状态对应最近一次执行；不是多个独立验证证据。输入版本、独立问题或需要单独复现的结果发生实质变化时，AI 应建立新 Run。`parent_run_ids` 表达实际消费的上游结果，不等于文件夹父子关系；仅有 owner_id 为父 Run 不会自动填写 parent_run_ids。

## L0–L4 保存和归属

| 层次 | 默认内容 | 谁负责生成 |
|---|---|---|
| L0 | 原始输入、脚本、输出、日志和固定文件引用的统一视图 | 执行/登记命令写材料登记，L0 自动投影 |
| L1 detail | v3 实验、方法、推导或分析技术单元；检索说明与稳定完整正文块 | AI 阅读真实证据后写入，不由日志自动生成 |
| L2 event | 实际观察、失败、决定及依据、后续行动 | AI 按重要事件保存 |
| L3 experience | 有适用边界的经验和不可迁移范围 | AI 在证据支持时提炼，不为凑层数制造结论 |
| L4 map | 问题、证据结构、未决事项和导航 | AI 随研究阶段维护 |

独立 `document_section` 章节、`document` 研究过程文稿/精简报告、目标、路线、检查点等是辅助类型，level 为 null。两类文稿分别使用 `research_process` / `research_report`，通过固定章节引用组织同一批技术单元，L4 仍是知识地图。L1 的实验说明固定引用 Run；方法、推导和分析可以没有实际执行的 Run，须明确依据或缺口。说明文档不会再算一次实验。每条记忆只有一个 owner_id，存入该 owner 的 memory_home，通过公共记忆提交保存历史修订，不在父子对象两边复制正文。

新记录默认 v3；v1 层级按现行语义投影，v2 detail 和旧 map 编排保留兼容，不改旧字节与固定引用。当前记录与检索模式见 [记忆使用指南](MEMORY_USAGE.md)，不要从文件夹名称或旧模板推断记录版本。

跨对象引用可复用同一 Run 或技术单元。程序不替 AI 决定所有 L1 应写父研究还是子 Run；按内容归属显式指定 owner_id。研究整体文稿、研究目标和阶段综合通常归研究，某次运行独有的记录可归 Run，以固定引用组织。

### 目前的聚合边界

- 非 Run 对象的 L0 会汇总 owner_id 或相关研究/项目/算法/数据关联字段命中的 Run，以及记忆固定引用和显式依赖。
- Run 对象的 L0 首先读取自身登记及显式引用；仅因子 Run 的 owner_id 指向该 Run，不会自动递归汇总子 Run。
- 项目关联某个研究，不等于研究的每个 Run 自动获得该 project_id；L0 不按整棵目录树推导归属。
- 更高层说明、事件、经验和地图不自动从子对象复制到父对象。文件保存、索引成功、结论复核是三个不同状态。

## 默认策略与 Skill

程序基础策略为 basic、normal 粒度、owner_only 发现范围、auto_summary=false、auto_deepen=false、checkpoint=true。Research 与 Project 类型均为 explore、fine、retain=L0–L4、auto_summary=true；其他六类沿用基础默认，其中 Run 显式设 basic。该 Project 默认自 2026-09-10 起采用，已有显式对象策略保持原意。

这些是记录/整理策略，不是后台 AI 调度开关。Research/Project 的 auto_summary=true 不表示保存文件后系统就自行调用模型写报告；仍需 AI 执行准备、编写、提交和回读。当前公共服务读取内置工作区/类型默认值和对象 HEAD 指向的 policy；保存对象策略后通过 inspect 查看有效值及逐字段来源。纯 Python `policy.resolve` 支持“工作区 → 类型 → 对象 → 请求”的覆盖顺序，但当前 CommitRequest 没有自由的 request_overrides 字段，不能把解析器能力当作已接入的 CLI 配置。子 Run 不因目录在研究或项目下就自动继承父对象的 explore 策略。

Skill 由 AI 按本轮任务选择，不由对象目录自动触发。多项工作可以组合 Skill，不要求每次全套执行。

| 任务 | 通常使用的 Skill | 行为与保存结果 |
|---|---|---|
| 读取对象、核对实现、理解历史 | workspace-context | 定位目标、按证据缺口展开；查字段不新建 Run |
| 导入材料、修订与整理知识 | context-maintenance | 采用身份、登记材料、保存修订、核对引用和索引 |
| 研究问题、仿真、反证与多轮探索 | research-loop | 读取目标/检查点；建立独立 Run；按 L0–L4 保存，编排文稿并回读 |
| 开发/修复/工具回归 | development-checks | 固定测试计划、执行分级回归、登记实际回执与人工检查入口 |
| 查看依据、复核、失效和下游影响 | evidence-inspection | 只读追溯；按授权维护复核；监测仅写观察记录，不启动实验 |
| 生成具体交付格式 | documents、pdf、presentations、spreadsheets 等对应 Skill | 按实际格式生成与校验成品；涉及计算依据仍使用固定 Run |

按对象看：研究通常由 research-loop 主导；算法/数据/Run 先 workspace-context，再按研究、开发或整理任务组合；工具开发主要 development-checks；知识维护主要 context-maintenance；报告按文件格式 Skill 加证据检查；项目按所属工作组合并维护目标、里程碑与引用。对象名称本身不决定需要进行研究或运行程序。

## 已核对的实现入口

- [Run 创建与归属选择](../automation/scripts/workspace_cli.py)：显式 owner 优先，否则唯一研究、指定项目、唯一算法，最后根 runs；多研究且无 owner 会报歧义。
- [对象内 Run 路径](../automation/scripts/manifest_discovery.py)及[对象身份/记忆路径](../automation/scripts/memory/owners.py)。
- [基础与研究策略](../automation/scripts/memory/policy.py)、[L0 聚合](../automation/scripts/memory/raw_materials.py)、[执行自动登记](../automation/scripts/run_capture.py)。
- [分层记录标准](RESEARCH_RECORDING.md)、[历史与复核](../context/MEMORY.md)、[执行手册](RUN_CAPTURE.md)。

本页记录现行归属和保存方式；父子递归聚合、后台自动总结和策略继承不能由目录结构推断，具体边界见上文。
