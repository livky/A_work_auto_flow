# 对象、Run 与执行回执：当前默认保存逻辑

核对日期：2026-09-13。本文描述当前实现，区分程序自动行为、AI 工作方法和未实现的自动化；对象已有策略或本次明确要求可以改变默认行为。

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
| L2 narrative | 有依据的研究/工作经过、选择与转折 | AI按实际价值保存，注明本次经过或来源叙述 |
| L3 experience | 有适用边界的经验和不可迁移范围 | AI 在证据支持时提炼，不为凑层数制造结论 |
| L4 overview | 用途、适用条件、现状、未决事项和导航 | AI按内容维护 |

独立 `document_section` 章节、`document` 研究过程文稿/精简报告、目标、路线、检查点等是辅助类型，level 为 null。两类文稿分别使用 `research_process` / `research_report`，通过固定章节引用组织同一批技术单元，L4 是整体概览。L1 的实验说明固定引用 Run；方法、推导和分析可以没有实际执行的 Run，须明确依据或缺口。说明文档不会再算一次实验。每条记忆只有一个 owner_id，存入该 owner 的 memory_home，通过公共记忆提交保存历史修订，不在父子对象两边复制正文。

新L1/章节/文稿使用v3，narrative/overview及分类experience使用v4；旧字节与固定引用保留。旧event/map实际整理后才提交新修订，不做原地替换。完整字段见[记录标准](RESEARCH_RECORDING.md)。

跨对象引用可复用同一 Run 或技术单元。程序不替 AI 决定所有 L1 应写父研究还是子 Run；按内容归属显式指定 owner_id。研究整体文稿、研究目标和阶段综合通常归研究，某次运行独有的记录可归 Run，以固定引用组织。

### 目前的聚合边界

- 非 Run 对象的 L0 会汇总 owner_id 或相关研究/项目/算法/数据关联字段命中的 Run，以及记忆固定引用和显式依赖。
- Run 对象的 L0 首先读取自身登记及显式引用；仅因子 Run 的 owner_id 指向该 Run，不会自动递归汇总子 Run。
- 项目关联某个研究，不等于研究的每个 Run 自动获得该 project_id；L0 不按整棵目录树推导归属。
- 更高层技术说明、经过、经验和概览不自动从子对象复制到父对象。文件保存、索引成功、结论复核是三个不同状态。

## 默认策略与工作入口

各类Owner默认使用work-loop，按有用内容保存L0依据、L1方法/分析、L2有依据的经过、L3可复用认识及L4概览。允许缺层，文稿按阅读和交付需要编排；不为每轮凑记录或强制双文稿。固定引用复用原件，来源主张、AI推断与本次验证明确区分。已有显式对象策略保留。

基础默认basic、normal、retain=L0–L4、owner_only、auto_summary=false、auto_deepen=false、checkpoint=true；Research/Project保留explore兼容值，粒度也是normal。retain表示可保留的内容，不是必填层；auto_summary不是后台调度。有效策略由memory inspect回读，已有显式配置优先，子Run不因目录继承父策略。CommitRequest没有任意request_overrides字段。

work-loop负责各类工作归属/记录/交接；material-query负责材料与阅读记录；开发、批量整理、结构迁移、复核追溯、下游语义维护按需使用对应专项Skill。run-execute/run-register是工具，不是另一主Skill。极小无复用价值操作不另建档。

## 运行中的阅读记录在哪里

工作台“系统记忆→选择对象→阅读记录”按owner_id列出RS，打开时从`.local/reading-sessions/RS-ID/HEAD.json`读取最新状态。CLI可用`material-query reading-list --owner ID`及`reading-view --session RS-ID --markdown`。未绑定旧会话在全局列表发现后显式bind；可关联固定检查点，关联保存在RS内。检查点是整体工作交接，RS下一步只指阅读子任务。

RS保存已交付候选、AI理解、必要细节、出处、尝试及预算；不复制原正文、不进入知识索引。Markdown导出标明版本，是快照；JSON由服务维护。归档只改状态并保留历史，不能删除原件或撤销知识结论。授权和来源变化需重新检查，旧导出不作为绕过撤权的入口。字段/容量/预算边界见[AI阅读](AI_READING.md)。

## 已核对的实现入口

- [Run 创建与归属选择](../automation/scripts/workspace_cli.py)：显式 owner 优先，否则唯一研究、指定项目、唯一算法，最后根 runs；多研究且无 owner 会报歧义。
- [对象内 Run 路径](../automation/scripts/manifest_discovery.py)及[对象身份/记忆路径](../automation/scripts/memory/owners.py)。
- [基础与研究策略](../automation/scripts/memory/policy.py)、[L0 聚合](../automation/scripts/memory/raw_materials.py)、[执行自动登记](../automation/scripts/run_capture.py)。
- [分层记录标准](RESEARCH_RECORDING.md)、[历史与复核](../context/MEMORY.md)、[执行手册](RUN_CAPTURE.md)。

本页记录现行归属和保存方式；父子递归聚合、后台自动总结和策略继承不能由目录结构推断，具体边界见上文。
