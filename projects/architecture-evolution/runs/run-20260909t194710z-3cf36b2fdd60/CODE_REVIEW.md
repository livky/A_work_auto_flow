# 材料查询独立代码审查

审查日期：2026-09-10（Asia/Shanghai）。所属 Run：`RUN-20260909T194710Z-3CF36B2FDD60`。审查者：本轮独立 AI 子任务。审查对象为开发中的工作树，不是已经封存的 Release。

初始审查阶段只读运行代码，并在临时隔离目录调用真实 F1 夹具和公开接口复现，未修改运行代码、规范业务数据或旧冻结夹具。以下保留首次复现事实和修复建议。主任务修复后，五项具体故障均已独立复验通过，进程退出码0。随后按进一步授权补入硬 ceiling 回归及持久维护 status 实现，其实际代码、契约和验证记录独立列在后文。请求筛选与来源授权核验读取分别定义，不把自然语言范围冒称为操作系统访问控制。

## 范围与判断依据

- `automation/scripts/material_query/` 下的 `coordinator.py`、`reader.py`、`assembly.py`、`representations.py`、`structure.py`、`api.py`、`budget.py`、`state.py`，并按需检查局部 `evidence.py` 和原存储适配。
- 范围、固定引用、逐 claim 正式证据、缓存再鉴权、累计预算、分页和旧版正文兼容。
- 依据 `docs/design/representation-query-v0.2/CONTRACTS.md`：scope、ceiling 与权限交集；缺少必要定义或受范围限制时 `complete=false`；每步共享账本；取消/耗尽时保留实际完成部分；表示应组合已有正文。
- 来源权限是当前权限；复核历史、固定内容版本与当前有效性分别判断。软件回归不证明现实科学结论成立。

## 已复现问题

| 编号 | 严重度 | 首次复现结果 | 修复状态 |
|---|---|---|---|
| R01 | P1 | `full` 遗漏已登记必需材料，仍返回 `complete=true`；来源鉴权还读取了筛选范围外依赖正文 | 完整性故障修复并独立复验通过；读取/筛选语义见下文 |
| R02 | P2 | 主张正文更新后，旧 review 在鉴权阶段被拒绝，无法返回真实的 accepted 历史与 invalid 当前状态 | 已修复，独立复验通过 |
| R03 | P2 | `topic` 文稿组合跳过已有章节 prose，返回错误的“没有可组合正文”缺口 | 已修复，topic/domain 独立复验通过 |
| R04 | P2 | 结构树设置 `review_states=["accepted"]` 后遗漏真实 accepted 事件 | 已修复，独立复验通过 |
| R05 | P2 | 续页中途耗尽输出预算，已计费候选被丢弃，回执没有部分内容 | 已改为整页原子预留，独立复验通过 |

### R01：完整性与必需材料的范围

首次复现定位：`assembly.py` 的 `Assembler.add_record` 引用收集分支（当时约158–164行），`coordinator.py` 的 `Coordinator.reader`（约155行），`reader.py` 的 `authorize_sources`。原分支只展开 document、document_section 和 map，不展开技术单元 `sources` 中的 `relation="prerequisite"`。

F1 的 `A.unit` 已经合法固定引用 `B.unit` 为 prerequisite。将查询 `scope.owner_ids` 和 `scope_ceiling.owner_ids` 都设为 A，identity 选择 A.unit，定义设为 full，随后公开 assemble，得到：

```json
{"search_status":"ok","packet_status":"ok","complete":true,"gaps":[],"B_body_read":true,"B_in_contributors":false}
```

正文读取探针包装 `MeteredStore._record`，保留真实读路径和字节账本。结果表明必需的 B 没进入材料包，也没有缺口提示；而来源闭包鉴权已经读取了 B 正文。若请求范围允许 A/B，所需内容应按固定版本进入 required_context；如果 B 超出候选/组包范围，须保留明确缺口，不能标完整。若产品把 owner ceiling 定义为硬 I/O 边界，则需在打开 B 正文前拒绝依赖它的 A，不能跳过 B 的权限核验。

此复现使用真实存储/FTS和公开 search/assemble，不是 mock 输出。它没有证明跨越了登记的企业访问控制；它证明了完整性承诺有误，并暴露了请求范围与来源核验读取需要说清的地方。

初步讨论曾建议将一般筛选与真实读取排除分开；随后与主任务收敛到更明确的两层边界：primary scope 的 owner_ids/levels/kinds/roles/outcomes 等是候选/组包筛选；`scope_ceiling.owner_ids` 与可信 owner ACL 的交集是规范 record 正文读取硬上限。trusted ACL、excluded_owner_ids/excluded_refs/exclude_ids 对来源闭包同样有效。在固定来源鉴权所必需时，可以读取 primary scope 外、ceiling 与 ACL 内的来源，全部计入原 read_bytes/wall_ms；不得把这些核验内容放进候选、材料包或自动联想。依赖超出硬 ceiling 时须拒绝父材料，不能同时省略来源鉴权又返回父材料。

此两层解释是复验后确认的后续集成要求；下文05:09前的复验指纹还未包含该硬 ceiling 修改，不冒称已经验证。UI 应分别表达 primary 和 ceiling，不能无提示地把用户只想缩小候选的选择复制成读取硬上限。v2/experiment 的 RUN owner 来源也要遵守明确身份边界；如果 Run 不在硬上限内，应提示缺口而非私下扩大。原始文件没有从该 owner 集合自动推得的归属 ACL，仍由来源登记权限与显式 source 排除控制。

### R02：旧复核可读性与当前有效性混在一起

首次复现定位：`reader.py` 的 claim 来源分支（新增核对处约217–219行）。当前 claim 不同于固定来源 sha 时直接抛 STALE；`Evidence._reviews` 读取旧 review 因而提前失败。

在 F1 中保留 `A.event` 的第一条 `claim_id`，通过真实 `fx.revise` 只修改其 statement，再执行局部 `Evidence(Reader).assess(new_record, None)`：

```json
{"exception":"QueryError","code":"STALE","message":"结论固定指纹与当前容器不一致"}
```

这不是“旧 accepted 仍有效”；预期是保留可审计的历史 review，同时报告其绑定与当前 claim 不匹配、`effective_validity=false`。建议先检查当前容器和旧来源的可读权限；若 sha 不等于当前 claim，应在该容器的有界历史中确认固定 sha 确实存在，再读取该历史来源闭包。不能直接忽略 sha。正式支持的 `Evidence._reference` 继续要求当前 sha；review 的绑定检查继续把过期复核判 invalid。不存在的 sha 仍须拒绝。

### R03：主题文稿没有保留已写章节

首次复现定位：`assembly.py` 的 `content_parts`（约73–76行）和 `add_record` 子定义选择（当时约172行）。topic/domain document 的子章节被强制转为 unit_digest；该分支使用 `readable_payload(document_section)`，不会返回 section.blocks 中的 prose。

F1 中 identity 选择 `A.report`，定义为 topic。search 回执状态 ok，realization=assemblable；assemble 结果为：

```json
{"status":"partial","complete":false,"prose_present":false,"warnings":["选定材料没有可组合正文"]}
```

缺失的是夹具中实际已写的“配方中的固定章节说明。”，并非要求模型新生成的文字。应保持独立章节和技术单元摘要的区别，topic/domain 进入文稿章节时保留作者 prose，再按其固定块选择组合所需单元内容。

### R04：结构树未执行复核筛选

首次复现定位：`structure.py` 约115行，直接调用 `record_allowed(record, scope)`，没有提供逐 claim 的证据状态。`record_allowed` 的缺省 review 为 not-reviewed，因此 accepted/retracted/disputed 等筛选无法正确命中。

真实 F1 请求：`TreeRequest(scope=Scope(owner_ids=[A], review_states=["accepted"], ...), parent_ref=None, cursor=None, limit=100, view="logical", parent_node_id="RES-MQ-A::L2")`。

```json
{"status":"ok","nodes":[],"code":null,"read_bytes":175306}
```

F1 的 A.event 确有 accepted claim。结构入口应使用与搜索相同的逐 claim 复核/有效性交集，保留自己的账本和当前来源检查。不能把记录中不同 claim 的 review 和 validity 合并后错配。

第一次临时命令将 parent_node_id 误填进 parent_ref，接口正确返回 VALIDATION；该无效请求不计为复现。上面的有效请求已单独执行成功。

### R05：续页预算耗尽丢失已完成内容

首次复现定位：`Coordinator.resume` 的逐候选 charge 与异常返回分支（审查时约468–511行）。实际控制流与首次搜索不同：第三条 charge 成功，第四条失败后，统一 `failure(exc, state)` 返回空 value。

此例为有意缩小的控制流单元复现：使用真实 Coordinator、StateStore、Ledger 和 resume，仅 mock 再鉴权（因此不把本例当成真实权限集成）。四条候选 excerpt 都为 `abc`，每页两条，总输出预算九字符；第一页已计六字符，下一页结果：

```json
{"status":"rejected","value":null,"code":"BUDGET","output_chars":9,"charged_but_undelivered_chars":3}
```

应保留并返回已授权且已计费的第三条，或先原子预留整页，避免为最终没有交付的文本收费。重试同一游标不能修复当前行为，因为三字符额度已经消耗。

## 未形成缺陷的核对

- 已知的 exact claim 借用同容器其他 accepted claim 问题，在本轮读取代码时已使用逐 claim 身份和过滤；旧 findings 不重复登记。
- 已知的正式材料包缓存复核撤回问题，在当前代码已有 fresh project 再检查，主任务另有真实撤回复归测试；本审查不把其测试冒领为本子任务重新执行。
- v2 full 渲染已保留 methods/steps/formulas/variables/results 等保存字段。曾尝试以空 body_markdown 复现 availability 分歧，但原 v2 schema 正确拒绝空正文，故不登记为合法历史数据缺陷。
- 未发现客户端 HTTP payload 可以传入 access_handle 变成可信授权的新增路径。此为定向代码检查，不是全应用渗透验收。
- 所有复现只用合成材料；未验证真实公司数据、大规模性能、第二台物理机或真实领域结论。

## 再验证入口

主任务修复后，至少覆盖：A-only 和 A/B prerequisite 两种完整性；当前 claim 变更后的旧 review 与正式拒绝；topic/domain prose 保留；结构树 accepted/retracted 与 validity 同 claim 配对；resume/cancel 在第二条超限时的 partial 内容和重复游标。

优先将真实故障补入 `test_material_queries.py`、`test_material_api.py`、`test_material_assembly.py` 和局部证据回归，不用本报告代替可复用测试登记。现行规则、README、测试 catalog、完整回归和真实 setup 的总体处置由主任务记录到此 Run。

## 修复后独立复验

2026-09-10 05:09（Asia/Shanghai）前完成，单个新建临时 F1 工作区依次验证 R01–R04；R05 在真实 Coordinator/StateStore/Ledger 上单独注入候选与再鉴权桩，未使用真实来源权限。执行器为仓库的 `automation/python.ps1 -c`，同一进程保留真实断言，全部断言通过、退出码0。初次复现内容保留，不因修复删除。

```json
R01: {"A_only_complete":false,"A_only_warnings":["必要内容被当前范围排除"],"AB_complete":true,"B_contributor":true}
R03: {"topic_prose_present":true,"domain_prose_present":true,"topic_warnings":["必要内容被当前范围排除"]}
R04: {"status":"ok","accepted_event_present":true,"nodes":2}
R02: {"review_state":"accepted","effective_validity":false,"errors":["STALE_BASIS"]}
R05: {"status":"rejected","code":"BUDGET","output_chars":6,"charged_but_undelivered_chars":0}
```

R01/R03 的 A-only 缺口是预期保留：B 确为必需依赖且不在本次输出范围。R02 保留 review 曾 accepted 的事实，但当前主张没有被认作有效依据。R05 选择整页原子预留，因此该页不够时不再消耗任何额外输出额度；本项不声称返回半页。

复验完成后立即读取的工作树 SHA256（并行开发未封存；后续改变需以 Run 最终指纹为准）：

| 文件（均在 automation/scripts/material_query/） | SHA256 |
|---|---|
| coordinator.py | `5e7357864de80ae48839cd5f82127486815baf910e6860d4dc10f8c1d208c4f8` |
| reader.py | `be35da67d32e519091a6481bc65341d3e78d3e980a32316bc015b07c909abcbe` |
| assembly.py | `4d9900c796d82bb634e6c29d9fbb0b5a17432bbd2eb35611cd28e50a98f30eaa` |
| structure.py | `68444a10d1790cce6e613e767283acadc85f851a3372464235a6934f3999d5ae` |
| evidence.py | `75805244fe8e71dda466528a30e6b313418b974bdc1c356e13235026958214e7` |
| api.py | `1e1cd4243cfe4cc860f983702c50f78592cb20868e6ef29ded0029d662b6f208` |

该定向复验不替代完整回归、实际 AI 语义评价、人工审查或第二台物理机验收。本审查没有创建这些类别的“通过”记录。

## 硬 ceiling 的后续集成检查

已证实的五处逻辑故障已按上述版本关闭。主任务随后将 Reader 的可信 owner ACL 与 `scope_ceiling.owner_ids` 取交集；以下四项已经由本子任务补为真实 F1 回归并执行通过，不沿用早期结果替代：

1. primary=A、ceiling=A/B：A 可发现；B 只作来源授权核验，输出范围仍为 A，必要上下文缺失必须留 gap。
2. primary=A、ceiling=A：A 有 B prerequisite 时拒绝该父材料，正文探针证明 B 的 `_record` 调用为零。
3. primary=A/B、ceiling=A/B：固定 A/B 正文和 contributors 完整。
4. 显式 exclude B：无论 ceiling 如何，派生 A 不得绕过来源排除。
5. 将本轮故障纳入可复用测试与 catalog，核对 UI 默认范围、Run owner 引用、契约和 README；最终完整测试与升级验收仍由主任务统一记录。

新增 `automation/tests/test_material_scope.py`：四个具体测试方法，第四项包含 owner、固定 ref、普通 id 三种排除子场景。`MeteredStore._record` 探针保留真实读路径；超出 owner ceiling 或被用户排除的 B 调用数为零。执行命令：

```powershell
.\automation\python.ps1 -m unittest discover -s automation/tests -p test_material_scope.py -v
```

结果：4项通过，29.037秒，退出码0。已通过 `testing register` 按 retrieval 能力登记到当时 catalog revision26，旧目录版本由工具自动保留。此后其他子任务继续登记，不能把26当作最终版本。UI与通用文档检查由主任务接续。

## 持久维护状态接口补齐

经主任务进一步授权，本子任务实现 `maintenance.status(coordinator, {query_id, plan_id})`，父任务接入公开 `maintenance-status` API。状态使用新查询的可信权限、owner ceiling、排除和累计账本，因此重启后可用新 query 查看旧持久计划，不依赖原 query 内存。状态接口不执行 apply，不补偿索引，不重建丢失的临时回执。

实现依据与行为：

- 读取指定 plan_id 下的不可覆盖版本，核对存储/计划指纹和版本父链；列出各分支，不以文件时间猜测“最新计划”。计划 JSON 本身的读取也计入 read_bytes。
- 从固定计划内容重新形成稳定逐 owner 请求，与持久 start 回执严格比对；完成事实以规范 `MemoryStore._receipt` 的请求哈希、回执哈希和当前 ledger 为准。临时 owner/completed 回执只能与此事实对照，不能自行宣告成功。
- 规范提交已完成但临时回执写入丢失时，返回已核实提交及真实的本地回执缺口；完整文件指纹证明 status 没有修文件或重写业务。
- 每条提交返回严格类型的 request/owner/commit/generation/save_status、固定变化引用、content_hash、变化状态和原规范 receipt_sha256，不在新契约中传任意旧字典。
- 每次重检当前来源权限和固定依据。后续独立 HEAD 修改不会抹掉已核实的历史提交；返回 `basis_stale=true` 和明确警告，状态读取不授予继续应用旧计划的许可。
- 索引状态从实际 HEAD 与词法/向量水位读取。索引未覆盖当前结论时明确 not-assessed/unknown，不沿用缓存 accepted；显式补偿后可以读到真实 retracted/invalid 状态。
- 严格 DTO 在 `contracts.py`：MaintenanceStatusRequest、MaintenanceStatusReceipt及Version/Commit/CommittedChange/Review/Index/Attempt内层类型；`SemanticMaintenance.status` 已声明，生成器包含具体 `Result_MaintenanceStatusReceipt`，JSON Schema与TS已刷新。

状态结果中的 `resume_cursor=null` 表示此入口不提供自动推进或状态分页。恢复所需的原 request_id、plan_digest 与 recovery_receipt 保存在实际 attempts 中；应用仍走原有明确 apply 契约。多个审查分支、缺索引和当前复核未知均如实保留，不能据执行完成推断语义/科学复核通过。

### 实际执行结果

```powershell
.\automation\python.ps1 -m unittest discover -s automation/tests -p test_material_maintenance_status.py -v
.\automation\python.ps1 -m unittest discover -s automation/tests -p test_material_maintenance.py -v
.\automation\python.ps1 -m unittest discover -s automation/tests -p test_representation_contracts.py -v
.\automation\python.ps1 automation/scripts/material_query/generate_types.py --check
```

| 验证 | 实际结果 |
|---|---|
| 新持久状态回归 | 11项通过，43.808秒，退出码0 |
| 原维护计划/审查/受限事务回归 | 19项通过，40.440秒，退出码0 |
| 原运行契约、预算与生成一致性回归 | 19项通过，0.166秒，退出码0 |
| Schema/TS生成漂移检查 | passed，changed=[]，退出码0 |

11项状态回归包含：重启与全文件只读核对、真实提交和固定变化、跨owner部分失败不续写、临时回执丢失、伪造临时回执、来源撤权、新ctx硬上限零目标正文读取、零预算/取消/并发、未知计划/越权字段拒绝、后续HEAD变动、索引pending到真实撤回状态。登记时 catalog 到达revision30，11个实际测试方法均已分类。最终任务选择应由主任务更新到其实际最新目录指纹。

2026-09-10 05:31:33+08:00 读取的交付文件 SHA256：

| 文件 | SHA256 |
|---|---|
| automation/scripts/material_query/maintenance.py | `9d57cd431cf2f8f618ea381cd9ee3e5fd17573d303f81eac8a92dee785ef54c7` |
| automation/scripts/material_query/contracts.py | `80488421866dc385ff92ae7cab0576d8fb6aeb775e5a4c9c90dde835dbf48de2` |
| automation/scripts/material_query/generate_types.py | `ed15dcdbe26984bbee1e626f4cc87186d7021ef2801b4eef71a9a34413fbbd62` |
| automation/tests/test_material_scope.py | `f0fdddd027aa2cf249cac737076e9ff1b79b06eaf4dc89ad4783a2abeb82e693` |
| automation/tests/test_material_maintenance_status.py | `68debfe2561f6b4489f479eb37829df43f8a686b22e74d0d4b45cd373794156f` |
| automation/schemas/material-query.schema.json | `1c67748a60e915cd80183dd4b47ae16f68b85703679cb5640facf3965581f0cb` |
| automation/frontend/src/generated/material-query.ts | `ccb09693f61f7f6c850909feb855ef3695593dc6cba6c2e10618fc9766d2e1ba` |

仅新增标准库实现及隔离测试，未引入新依赖。父任务负责包含最终生成TS的前端重建、公开路由/CLI委托、README与契约手册、全局测试选择、refresh-index/validate和真实扩展旧工作区setup检查。本节不把这些尚未由本子任务执行的总体检查写为通过。
