# 可复用分级测试与实际AI验收

本页是框架开发的测试入口。测试目录记录稳定能力和验收标准，每次开发在开始实现前保存一份任务选择清单；新增能力或真实故障同时更新目录。一次任务的执行结果保存在固定Run，不改写测试定义来追认结果。

选择测试前，按[文档与模块影响维护](DOCUMENTATION_MAINTENANCE.md)定位本次变化的模块，检查关联的契约、索引、文稿、UI、Skill 和迁移。把“需修改 / 已检查无需修改 / 延期”保存到本轮影响清单，再据影响选择测试；覆盖不是只查被编辑的文件。

## 三类验证

| 类别 | 用途 | 最低要求 |
|---|---|---|
| quick：核心简要回归 | 日常快速迭代 | 核心保存/版本/依据/预算边界的代表场景，加本次受影响能力的必要测试；按风险追加真实setup或浏览器，不以快速为由省略 |
| full：完整功能回归 | 较大变更收口与发布 | 全部Python功能测试、前端组件与正常浏览器场景；能力依赖、离线分发、性能分别列明，不把未执行项算通过 |
| actual-ai与人工审查 | 验证实际AI能够使用产品完成工作 | AI实际读取材料、生成请求、公开保存、回读、自查；为核心功能和新增功能生成可直接阅读的人工审查页 |

这些类别分别报告，不将AI自查、人类认可和单元测试累计成一个通过率。旧`verify --profile core/full`是能力自检入口，不能替代此处的测试层级。源码检查只证明定义存在，只有执行回执才能证明测试跑过。

## 每次开发前的选择

任务清单应保存目标、影响能力、catalog版本与指纹、必跑项、新增验收、复用历史依据、排除理由和已知限制。选定后冻结一版；范围改变时创建新版并保留原版和理由。

稳定能力地图至少覆盖：工作区登记与校验、对象内Run、材料来源与权限、版本记忆/CAS/恢复、结论复核与失效传播、检索和预算展开、目标/问题/续接、跨研究关联与总结、研究文档、工作台/任务监测、Windows升级迁移、依赖与模型分发。每项绑定现有测试入口和面向用户的验收标准，不仅列函数名。

新增测试和新能力必须被清单覆盖；未分类项显式报出，不能因为没有映射就自动跳过。quick固定一组核心门槛，再按任务影响增加测试；full包含新发现的测试，仍须报告各能力的缺项。耗时、失败、超时、跳过和缺能力单独保存，不能由进程退出0掩盖。

## 风险触发的必测

- 改校验、扫描、缓存边界、工具登记、发行清单、安装或恢复：执行[真实扩展旧工作区setup场景](UPGRADE_TESTING.md)，覆盖预览、升级、重复升级、恢复、完整文件哈希和目录保护及真实损坏拒绝。
- 改前端：相关组件、实际浏览器、类型检查、构建与指纹；使用端不依赖Node。
- 改依赖/模型：真实离线安装、升级、接收端再打包与恢复；普通core安装不能替代。
- 改检索：范围、敏感性、固定引用、L0排除、预算与相关排序回归；原质量留出集没有通过，不因本轮软件测试自动转为通过。
- 大规模性能与第二台物理机验收独立列出。当前万条规模测试按此前授权暂缓，不能悄悄重启或改写为通过。

## 可复用实际AI场景

| ID | 场景 | 人工重点 |
|---|---|---|
| A01 | AI生成记录，预检/提交/inspect/expand回到固定来源 | 核心：正文、归属、依据与限制 |
| A02 | 只给研究入口的新上下文，读取目标/检查点并继续 | 核心：已做未做、实际展开、正确下一步 |
| A03 | 保存结构化技术单元、完整块和独立章节 | 方法/变量/参数/结果与可独立阅读性 |
| A04 | 共享固定证据，保存完整研究过程与简版研究报告 | 双文稿正文、图表、结论与范围一致 |
| A05 | 局部修订、变化关注、受影响章节更新和旧版回读 | 影响理由、未变内容、旧证据保留 |
| A06 | 跨研究检索与展开，分别判断适用与不适用请求 | 保留适用条件和禁止迁移内容 |

场景可以共享一条研究旅程，A02必须真正隔离上下文。脚本可记录调用和机械核对，但不能预填AI正文、自评或人工意见。实际保存必须走公开CLI/API；失败/重试只追加。人工首页只展示核心、本次新增和重要受影响结果，不要求每次重审所有历史H项。

Project 默认分层记录复用 A01/A03/A04：先确认公共 inspect 的类型默认与 Research 一致，再保存项目技术单元、事件和双文稿并回读正文；同时用 `test_memory_owners` 验证显式 basic/false/空保留列表不会被新默认覆盖，用 `test_memory_owner_service` 验证只读检查不偷偷创建内容。分层建议不等于自动生成或科学复核。

每项保留：执行前任务/预期、输入与Skill指纹、实际AI上下文身份（未知字段留空）、生成请求、唯一调用日志、退出码、回执、固定回读、AI实际阅读范围、逐预期自查、人工待审状态、限制。审查页先给可读正文和观察，再链接JSON细节。`execution`、`mechanical_checks`、`ai_assessment`、`human_review`、`scientific_review`分开记录。

## 实现与历史执行记录

2026-09-09 技术文稿批次：本规范先于技术单元与独立文档实现冻结；catalog、任务选择器、执行器与实际 AI 审查工具已实现，下方给出可调用命令。该批开发范围见[设计记录](design/RESEARCH_DOCUMENTS.md)，执行结果、原失败及复验见固定 Run（本地历史记录，未随源码分发：`../projects/memory-layers-v2/runs/run-20260909t055625z-b13c2fc3994f/README.md`）。该批实际 AI 已完成 A01–A06，人工意见待审；后续开发须引用各自的实际 Run，不把本段作为新一轮通过记录。

## 已实现的测试命令

`workbench.cmd testing` 为统一入口；也可直接使用 `automation/python.ps1 automation/testing/runner.py`。二者使用同一 catalog、选择校验和执行逻辑。命令支持 `--help`，以 JSON 返回状态和产物路径；非通过、缺项或输入错误返回非零。

```powershell
# 只读盘点：新增未分类、失效ID、能力及quick门槛
.\workbench.cmd testing audit
.\workbench.cmd testing catalog
.\workbench.cmd testing coverage

# 开发前冻结；输出只能是新的.local文件，或既有Run下的新文件
.\workbench.cmd testing prepare --tier quick --goal "本次开发目标" --capability research --actual-ai A03 --actual-ai A04 --acceptance "N01:技术单元可独立展开" --out .local/testing/task/selection-v1.json
.\workbench.cmd testing validate --plan .local/testing/task/selection-v1.json
.\workbench.cmd testing coverage --plan .local/testing/task/selection-v1.json

# 范围改变创建新版本；不提供的选择字段继承上一版
.\workbench.cmd testing update --plan .local/testing/task/selection-v1.json --reason "新增章节变化影响场景" --out .local/testing/task/selection-v2.json

# 运行前完成本次前端build；runner本身不联网安装或自动重建前端
.\workbench.cmd testing run --plan .local/testing/task/selection-v2.json --out .local/testing/task/attempt-01
```

运行目录必须尚不存在，重试使用 `attempt-02` 等新目录。每次保留 `selection.json`、`results.json`、可读 `README.md`、实际命令数组及阶段机器结果/日志；Python 子进程逐条保存进度，超时或中断仍保留部分结果。测试器不写原始材料或覆盖旧选择/旧执行。正式任务宜将这些路径改到本次固定 Run 的 `testing/` 下。

`--capability` 可重复，用于本次受影响的完整能力集合；quick 固定门槛仍保留。`--add-test` 选择已登记的额外测试，`--acceptance` 保存新验收标准，`--reuse-evidence` 保存历史回执与适用范围。update 中显式给出的列表替换该列表，未给出的字段继承。`--exclude TEST_ID=原因` 保留排除理由，但被选项未运行会使整体结果为 `incomplete`，不能用排除制造通过。

目录位于 `automation/testing/catalog.json`，逐个登记稳定测试 ID、能力、验收目标、quick/full、运行依赖和独立授权；扫描器不执行测试。quick 核心覆盖 Python 代表场景、实际浏览器、相关组件、类型检查和真实扩展旧工作区 setup 升级/恢复，实际项目数以冻结的 catalog/selection 为准；影响能力的用例另行追加。手册不再维护第二份固定数量。

新增测试需显式分类，后续新增方法仍会被再次审计，例如：

```powershell
.\workbench.cmd testing register --module test_memory_documents_v3 --capability research --reason "新增独立章节固定版本行为"
.\workbench.cmd testing audit
```

上述模块名为示例，应替换为实际新增测试模块。前端用 `src/Example.test.tsx` 或 `e2e/example.spec.ts` 作为 `--module`。新增测试如依赖模型，登记时用 `--requires vector` 和 `--authorization vector` 明确标注；普通登记不替代开发者判断。register 保留旧 catalog 副本并增加 revision，随后必须 update 任务选择。删除或改名的测试会显示失效 ID，需开发者审查并修改受控 catalog，不能静默忽略。

`full` 发现全部 Python 测试并执行选定集合，包含全部普通组件/浏览器场景。vector/OCR 的授权使用 `--allow-capability vector`、`--allow-capability ocr`，仅在任务已授权相应检查时提供；缺模型或跳过仍不是 full 通过。完整离线分发由 `dependencies` 影响能力触发，并要求获准的 `dependency-release` 授权和 `--bundle` 本地路径。万条规模不在默认 quick/full 内，仍按用户要求暂缓；不得只因命令支持 `scale` 就启动。另一物理机、实际AI使用和人工/科学复核均独立于软件通过状态。

软件执行状态为 `passed / incomplete / failed`；阶段还保留超时、中断和具体 skip。退出码为 0 也不能覆盖零测试、数量不匹配、缺机器结果或跳过。`coverage` 是定义/选择覆盖，不是执行通过。`actual_ai_scenarios` 只登记需要开展的实际AI场景，调用和人工审查使用独立的 `ai_review.py` 产物，不由普通测试器预填。

测试器本身已以 `automation/tests/test_test_tiers.py` 的 7 项隔离行为测试验证，包含真实子进程成功/失败/跳过、超时留存、未授权规模拒绝、版本不覆盖和新增测试审计；这不代替本轮完整功能或实际AI验收。

2026-09-09 回执可靠性补充：组件执行按冻结的文件/测试标题与 `assertionResults` 对账；Vitest 未选中的过滤项单列 `filtered_out`，不当作已选测试跳过。真正选中但跳过的测试仍为 `incomplete`。Windows 回执原子替换仅对明确的 WinError 5/32/33 做有界重试，冲突保存在 `*.write-events.jsonl`；重试耗尽保留 pending 内容，最终主回执仍被占用时另存不可覆盖的 `results-failed-*.json`，命令返回其路径。未启动阶段明确标为失败/未执行。相关专用测试现为 10 项通过，旧失败执行不改写。

## 表示查询用例与实施回执

[完整设计](design/representation-query-v0.2/TEST_DESIGN.md)和机器用例目录保留冻结的设计状态。实际测试已在catalog按具体方法登记，涵盖运行契约、真实F1存储/索引、查询/组包、局部证据、关系加深、维护Writer与工作台；本轮结果以固定实施Run为准，不能把设计静态检查当作功能通过。实际AI模板新增A07表示选择与缺口、A08结构联想负例、A09无旧边反证维护；模板本身始终不包含执行答案或通过状态。
