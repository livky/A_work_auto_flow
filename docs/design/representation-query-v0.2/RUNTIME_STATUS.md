# 表示查询 v0.2 运行继承状态

固定实施 Run：`RUN-20260909T194710Z-3CF36B2FDD60`。本页记录 P0 底层兼容适配和 P3 导航的实际运行落点；[继承清点](INHERITANCE.md)保留原设计义务，[逐项机器映射](inheritance-map.json)保存实际测试 ID、受限状态和实现文件指纹。

**43 个方法已对应受约束的实际运行入口，完整旧协议验收与入口存在是两件事。** 最初缺少的重排、持久化维护状态、执行预约和执行结算现已分别补入真实确定性策略、规范回执状态读取及共享账本。所需模型/后端未配置时仍须 `UNSUPPORTED`，不能用能力拒绝计作模型执行。INH01–INH12 与 C01–C26 的完整验收仍由主集成流程逐项关闭。

2026-09-12基础召回更新：Coordinator的dense通道接入既有本地标准编码器，技术块正文进入可重建投影，词法/向量按记录限制窗口并固定命中来源。内置查询编码计入Ledger；Foundation通用ModelProvider/Tokenizer注册与任意IndexKey仍未开放，不能把新增dense解释为旧协议全覆盖。具体操作和升级见[材料查询手册](../../MATERIAL_QUERY.md)，本页原P0/P3回执保持历史时点。

2026-09-13阅读层补充：reading-list/view/bind/archive为RS工作状态公开动作，支持Owner/固定检查点与工作台查看；不计入旧43项Foundation协议，不修改冻结inheritance-map。当前流程由work-loop和material-query指导，具体边界见[AI阅读](../../AI_READING.md)。

## 1. 实际入口与共同边界

Python 入口位于 `automation/scripts/material_query/foundation.py`：`Foundation(coordinator).dispatch(action, raw)`。公共 API 使用 `foundation/<action>`；CLI 的 `material-query foundation-capabilities` 查看能力，`material-query foundation --request` 在同一进程内建立查询并执行一个底层动作。需要多步 read→rerank、分页→index-plan→index-execute 的工作使用保有 query 的应用 API。`capabilities` 只接受空对象；`definition-resolve` 是不读业务材料的纯版本别名映射；其余动作必须携带现有 `query_id`，复用原请求、可信 owner 权限、scope 上限、排除、累计账本、活动锁和 TTL。未知字段及不支持的硬语义明确拒绝。

该适配有独立严格输入；它没有把旧 v0.1 请求 DTO 直接冒充为新应用请求。`METHOD_MAP` 声明行为所有权，不能用一条函数名映射替代旧契约全字段的兼容性证明。

所有原件仍经既有来源登记检查，直接 file 请求也保留原 `source_ids`。固定记录重读检查当前权限和来源闭包；正式材料只呈现当前适用的已准入 claim。正式缓存候选在去重、选择及深化重放时重验复核，撤回后不继续展示旧认可。

## 2. 内容、版本和索引生命周期

- `describe/read/resolve/list-page` 分别负责元数据、固定内容、旧六字段引用和固定 manifest 页。分页不依赖 FTS，因此派生 SQLite 丢失后仍可枚举规范材料。claim 定位仅在此显式底层入口允许受预算约束的规范清单扫描，普通搜索不隐式扫描全库正文。
- `history/changes` 绑定首次读取的 HEAD 和 manifest 父链；随后规范 HEAD 前进不会把新提交插到旧游标中。历史回执另核 SHA，变化页保存固定前后引用及真实事件 ID。
- `validate` 保存批次及依据摘要；`apply` 只接受服务端验证句柄与匹配指纹，提交前重新校验。`commit/review` 调用原 `memory.api.dispatch`；规范 CAS、UUID 幂等、锁及版本所有权仍归原服务。
- `restore` 用旧内容创建新的规范修订，保留历史；必须绑定当前修订与 HEAD，拒绝覆盖后续修改。科学 review 不通过内容恢复重写。
- `representation-plan/build` 只组合已有字段，返回临时文本及固定贡献来源，`canonical=false`。新语义没有真实生成能力时提供维护技能入口，不能伪造已生成的领域综合。

索引采用以下明确的窄键，不声称支持任意编码器或所有旧表示槽：

```json
{
  "channel": "lexical",
  "representation": "existing",
  "encoder": null,
  "analyzer": {"name": "memory-fts", "version": "运行时 memory.index.PROJECTION_VERSION"},
  "dimension": null
}
```

`channel` 也可为 `graph`，但它仅覆盖已登记关联，水位始终标注 `existing_associations_only/partial`。`index-status` 是只读水位状态，不是逐字损坏审计。

`index-plan` 只接受本查询已返回的完整连续页：rebuild 使用内容页，incremental 使用变化页，repair 可选其一。首尾、顺序、游标、固定 HEAD 或页缺口不满足时拒绝。当前既有投影按完整 owner 维护；携带 kind/role/source/time/排除等硬选择的专用索引须由另一个真实 IndexKey 提供器实现。

`index-execute` 复用原 `memory.index._sync_fts` 事务，每 owner 原子更新内容、关系和 FTS 水位。repair/rebuild 强制重投影所有条目，可以修复行数不变但 FTS 文本损坏的情况。没有预先提交的删除阶段；故障回滚该 owner 的事务，原计划保留未完成 owner/事件，重试不产生第二次内容提交。词法/图维护保留已有向量水位。旧 Run/原生证据表示图、向量建立及跨 owner 全局原子性不在此窄适配内。

## 3. 43 个方法的实际去向

“局部回归通过”只覆盖机器映射列出的真实测试。应用委托还需相应应用模块及 HTTP/CLI 主集成结果；本页没有把委托自动算成旧接口已完全实现。

| 原方法 | 状态 | 运行落点 | 当前范围或缺口 |
| --- | --- | --- | --- |
| `ContentReader.describe` | 受约束适配；局部回归通过 | `describe` | 只描述规范 record/representation；原件与 claim 先 resolve，逐项缺失明示。 |
| `ContentReader.read` | 受约束适配；局部回归通过 | `read` | 固定记录/已登记文本原件；二进制需既有文档/OCR读取器；正式用途仅已准入 claim。 |
| `ContentReader.list_page` | 受约束适配；局部回归通过 | `list-page` | 固定 manifest 轻量元数据分页；支持规范记录，非任意旧 ReadView 格式枚举。 |
| `ReferenceResolver.resolve` | 受约束适配；局部回归通过 | `resolve` | 六字段 relation 保留；record 指定修订补 SHA；claim/owner 固定自身 SHA；独立旧表示 ID 不能改名冒充记录。 |
| `ContentCommands.validate` | 受约束适配；局部回归通过 | `validate` | 完整 memory-v3 单 owner 批次与 basis 绑定；验证不写入，应用时再次验证。 |
| `ContentCommands.commit` | 受约束适配；局部回归通过 | `commit` | 原公共 memory commit、CAS、UUID 幂等；索引 pending 单列，禁止自动无界索引。 |
| `ContentCommands.restore` | 受约束适配；局部回归通过 | `restore` | 历史内容生成新修订；固定当前版本与 HEAD，拒绝覆盖后续变更；review 不走内容恢复。 |
| `RevisionStore.apply` | 受约束适配；局部回归通过 | `apply` | 只能应用本 query 保存的验证句柄与批次指纹，最终事务归原 memory.store。 |
| `RevisionStore.history` | 受约束适配；局部回归通过 | `history` | 固定 HEAD 的 manifest 父链和已核验回执；查询游标在 HEAD 前进后不漂移。 |
| `RepresentationCatalog.list` | 受约束适配；局部回归通过 | `representation-list` | 列出固定记录对指定 definition 的实际可读/可组合能力。 |
| `RepresentationCatalog.read` | 受约束适配；局部回归通过 | `read` | 固定记录/已登记文本原件；二进制需既有文档/OCR读取器；正式用途仅已准入 claim。 |
| `RepresentationBuilder.plan` | 受约束适配；局部回归通过 | `representation-plan` | 只计划已有字段的确定性组合；新语义给维护技能入口并拒绝伪造内容。 |
| `RepresentationBuilder.build` | 受约束适配；局部回归通过 | `representation-build` | 返回临时文本与固定来源；canonical=false，不产生规范修订。 |
| `ChangeReader.read` | 受约束适配；局部回归通过 | `changes` | 固定历史提交的前后 refs 与事件 ID；不宣称旧协议所有事件过滤器已兼容。 |
| `IndexLifecycle.status` | 受约束适配；局部回归通过 | `index-status` | 只读既有 FTS/关联水位；未做物理逐字审计，graph 覆盖始终为 existing_associations_only/partial。 |
| `IndexLifecycle.plan` | 受约束适配；局部回归通过 | `index-plan` | 完整连续的服务端内容页或变化页；完整 owner 范围；固定窄 IndexKey；拒绝页缺口。 |
| `IndexLifecycle.execute` | 受约束适配；局部回归通过 | `index-execute` | 每 owner 原 FTS 事务；repair/rebuild 强制重投影；原计划可重试，保留向量水位；无跨 owner 全局原子性。 |
| `RecallProvider.capabilities` | 应用委托；本子任务未单测 | `delegated:Coordinator.capabilities` | 运行所有权已落到既有应用入口；旧 v0.1 DTO 不能直接原样提交。完整后置条件须由主集成测试核验。 |
| `RecallProvider.recall` | 应用委托；本子任务未单测 | `delegated:Coordinator.search` | 运行所有权已落到既有应用入口；旧 v0.1 DTO 不能直接原样提交。完整后置条件须由主集成测试核验。 |
| `CandidateDeduplicator.deduplicate` | 受约束适配；局部回归通过 | `deduplicate` | 仅输入候选固定身份去重，保留全部 hits/channels；正式候选重验当前 claim。 |
| `FusionStrategy.fuse` | 应用委托；本子任务未单测 | `delegated:Coordinator.ranking_strategies` | 运行所有权已落到既有应用入口；旧 v0.1 DTO 不能直接原样提交。完整后置条件须由主集成测试核验。 |
| `Reranker.rerank` | 受约束适配；局部回归通过 | `rerank` | term-overlap/1、exact-phrase/1 对已读 slice_id 的真实确定性排序；限输入候选，无隐藏召回；无所需模型仍拒绝。 |
| `DiversitySelector.select` | 受约束适配；局部回归通过 | `select` | 已准入候选的 owner-round-robin/1 子集；保留未选原因，不修改证据状态。 |
| `RankingPipeline.rank` | 应用委托；本子任务未单测 | `delegated:Coordinator._recall` | 运行所有权已落到既有应用入口；旧 v0.1 DTO 不能直接原样提交。完整后置条件须由主集成测试核验。 |
| `RelationNavigator.neighbors` | 应用委托；局部回归通过 | `delegated:deepening.deepen` | 运行所有权已落到既有应用入口；旧 v0.1 DTO 不能直接原样提交。完整后置条件须由主集成测试核验。 |
| `RelationNavigator.paths` | 受约束适配；局部回归通过 | `paths` | 由已返回有界图页组成有向最短固定路径、edge_ids、差异和条件；目标未连通明确缺口。 |
| `RelationNavigator.suggest_links` | 应用委托；局部回归通过 | `delegated:associations.discover/decide` | 运行所有权已落到既有应用入口；旧 v0.1 DTO 不能直接原样提交。完整后置条件须由主集成测试核验。 |
| `ExpansionPolicy.next_step` | 受约束适配；本子任务未单测 | `next-step` | 固定默认决策 resume/deepen/stop；不执行工作，不支持任意旧自定义扩展策略。 |
| `SearchCoordinator.search` | 应用委托；本子任务未单测 | `delegated:Coordinator.search` | 运行所有权已落到既有应用入口；旧 v0.1 DTO 不能直接原样提交。完整后置条件须由主集成测试核验。 |
| `SearchCoordinator.resume` | 应用委托；本子任务未单测 | `delegated:Coordinator.resume` | 运行所有权已落到既有应用入口；旧 v0.1 DTO 不能直接原样提交。完整后置条件须由主集成测试核验。 |
| `ContextBuilder.build` | 应用委托；本子任务未单测 | `delegated:Coordinator.assemble` | 运行所有权已落到既有应用入口；旧 v0.1 DTO 不能直接原样提交。完整后置条件须由主集成测试核验。 |
| `ReadViewService.list` | 受约束适配；局部回归通过 | `list-page` | 固定 manifest 轻量元数据分页；支持规范记录，非任意旧 ReadView 格式枚举。 |
| `ReadViewService.render` | 受约束适配；局部回归通过 | `read` | 固定记录/已登记文本原件；二进制需既有文档/OCR读取器；正式用途仅已准入 claim。 |
| `MaintenancePlanner.plan` | 应用委托；本子任务未单测 | `delegated:maintenance.plan` | 运行所有权已落到既有应用入口；旧 v0.1 DTO 不能直接原样提交。完整后置条件须由主集成测试核验。 |
| `MaintenanceExecutor.execute` | 应用委托；本子任务未单测 | `delegated:maintenance.apply` | 运行所有权已落到既有应用入口；旧 v0.1 DTO 不能直接原样提交。完整后置条件须由主集成测试核验。 |
| `MaintenanceExecutor.status` | 应用委托；局部回归通过 | `delegated:maintenance.status` | 重启后用新可信 query 读持久计划/规范幂等回执；返回逐 owner 提交、当前证据及索引水位，不推进执行。 |
| `EvidencePolicy.authorize` | 应用委托；本子任务未单测 | `delegated:Reader.owner/record` | 运行所有权已落到既有应用入口；旧 v0.1 DTO 不能直接原样提交。完整后置条件须由主集成测试核验。 |
| `EvidencePolicy.assess` | 应用委托；本子任务未单测 | `delegated:Evidence` | 运行所有权已落到既有应用入口；旧 v0.1 DTO 不能直接原样提交。完整后置条件须由主集成测试核验。 |
| `ReviewService.append_review` | 受约束适配；本子任务未单测 | `review` | 调用既有公开 review 命令；真实语义审查及审批依据由该命令/维护流程检查。 |
| `ImpactAnalyzer.affected` | 应用委托；本子任务未单测 | `delegated:maintenance.plan` | 运行所有权已落到既有应用入口；旧 v0.1 DTO 不能直接原样提交。完整后置条件须由主集成测试核验。 |
| `ExecutionControl.reserve` | 受约束适配；局部回归通过 | `reserve` | 共享 Ledger 原子占有 held 额度；并行竞争不超订，实际提供器及子调用共用预约。 |
| `ExecutionControl.settle` | 受约束适配；局部回归通过 | `settle` | 固定预约/账本身份，实际费用幂等结算并释放余量；不重复已 charge 的子调用费用，取消后仍允许清账。 |
| `ExecutionControl.check_cancelled` | 受约束适配；本子任务未单测 | `check-cancelled` | 检查同一查询当前取消句柄/活动账本；本测试组未单独行使此动作。 |

## 4. P3 导航的验证边界

既有导航先从索引取得候选身份，再回读规范端点、固定修订及当前关联状态。普通 sources 中未投影的反向依赖使用受候选数/字节预算限制的规范核验，并明确不完整窗口。文稿 source_mapping 保留 document→section→指定 unit 修订/块及必需定义，不把旧修订替换为当前正文。

图节点身份包含 kind、ID、revision、SHA、locator。循环和菱形共享节点/边账本；选择后发现的节点为新种子也不能重置原累计跳数。游标只属于原请求、种子和策略，预算/取消终止不能重试成空成功。`paths` 用已返回的有界边生成有序最短固定引用链、edge_ids、迁移条件与差异；未连通只能说明当前页不足。

导航决定通过原公开 commit 的 `decide_association` 操作保存同一条关联，保留固定端点及关系语义，提交回执如实报告索引 pending。重复 UUID 请求幂等，改变同一 UUID 的请求拒绝；导航采纳没有创建 claim/review。原联想开关关闭时不能通过 discover 绕过；无模型结构发现只返回实际技能入口，未验证领域发现能力。

## 5. 重排、执行控制与持久状态

`read` 为每个实际读取的固定文本片段返回 `slice_id`；`rerank` 明确接收 `candidate_ids/text_slice_ids/strategy/strategy_version`，只能使用本 query 的服务端文本片段，不接受客户端伪造正文，也不补读未提供的材料。当前 `term-overlap/1` 和 `exact-phrase/1` 是真实确定性相关性策略，模型成本为零；候选身份、全部命中来源和复核状态保持不变。无正文、未知策略、提供器故障均可见；取消时保留已完成分数并释放未消费预约。

`reserve` 的 `ceiling` 使用当前 Budget 单位。Ledger 在锁内核对实际消耗加 held，保证竞争提供器不能占有同一剩余额度；`provider(reservation)` 使既有子函数 charge 沿用预约。`settle` 绑定原预约和账本，实际费用低于已计量费用时拒绝，重复相同结算幂等，剩余额度释放；父调用确认子费用不会再扣一遍。真实外部费用超出预约时如实记录 overrun 并停止新工作，不把已发生超支截断成上限。取消或超时之后仍可结算；墙钟取活动区间实际并集，不把并行子提供器报告的 wall_ms 相加。

`maintenance-status` 由 maintenance 服务读取不可变计划版本与规范事务/幂等回执。进程重启后使用新 query 重新授权旧 plan；输出实际逐 owner 提交、pending owner/review/index、当前证据状态及 stale 缺口，不执行下一步。临时目录回执自报成功不能覆盖规范账本；规范提交后出现新 HEAD 仍保留已核实旧提交并提示依据变化。

## 6. 已执行回归和未完成验收

本机 Windows x64 的隔离合成 fixture，规范记录/review/关联均经实际 `memory.api.dispatch`，不伪造规范 HEAD 或科学结论：

| 命令 | 实际结果 | 关键覆盖 |
| --- | --- | --- |
| `.\automation\python.ps1 -m unittest discover -s automation/tests -p test_material_deepening.py -v` | 17/17 通过，70.953 秒 | 固定块/原件、循环菱形、累计预算、方向、撤权、正式撤回、决定幂等与无科学提升 |
| `.\automation\python.ps1 -m unittest discover -s automation/tests -p test_material_foundation.py -v` | 23/23 通过，60.209 秒 | 无索引规范页/claim、固定历史、真实 CAS/恢复、索引故障/修复、固定正文重排、缺正文/故障/取消、公开预约结算 |
| `.\automation\python.ps1 -m unittest discover -s automation/tests -p test_material_budget.py -v` | 11/11 通过，0.004 秒 | 原子竞争预订、父子不重复计量、身份绑定、余量释放、超支如实计费、取消清账与并行活动墙钟 |
| `.\automation\python.ps1 -m unittest discover -s automation/tests -p test_material_maintenance_status.py -v` | 11/11 通过，43.808 秒；维护实施子任务执行 | 重启只读、规范提交核验、部分跨 owner 完成、伪造回执拒绝、权限撤销与当前复核/索引 |

测试数字只证明所列软件行为。模型有效性、业务资料正确性、实际 AI 语义审查、人工验收、第二台物理机和完整离线升级均不由这些结果证明。主测试 Run、README/技能入口、预构建资源、迁移清单、真实 setup.cmd 升级/恢复和发布完整性由主集成任务记录，不能用这两组测试替代。

## 7. 继承审计后的补充闭合

逐项执行状态改由固定 Run 的 [38 项继承验收](../../../projects/architecture-evolution/runs/run-20260909t194710z-3cf36b2fdd60/INHERITANCE_ACCEPTANCE.md) 与机器回执记录；上表保留较早的实际执行，不把较早次数改写成新版本全通过。完整旧 DTO、未配置模型和未覆盖后端的限制仍逐项保留。

此次补充包括规范可选知识分类与逐 claim 交叉筛选、多表示原始分数/固定命中/片段、按最终结果数增量读取与续查、真实通道故障贯穿最终包、缺水位降级、结构化 Issue/Basis、四项独立模型额度边界、版本化表示别名、旧关系与平行边、获准/拒绝路径差异，以及 domain 多来源撤权和新 claim 追加适用 review。

P3 最终模块回归 **20/20，81.543 秒**；模型额度账本 **15/15，0.005 秒**；Foundation 较早补充 **24/24，62.690 秒**。随后 C17 新测试的两个夹具/断言错误分别保留原失败回执；仅修正测试体后的定向回归 **1/1，35.792 秒**，没有将失败的 25 项模块执行重写为全通过。详情与源码指纹见 [补充回执](../../../projects/architecture-evolution/runs/run-20260909t194710z-3cf36b2fdd60/inheritance-closure-final.json)。主任务完整测试另行记录。

`references/input/same_entity/mentions` 与现有关系并存，平行边保留 `legacy_relation/evidence_relations`。未注册规范关系明确报告缺口。关联可选 `differences` 保存显式审查的差异；拒绝/撤回/旧修订边只在有权范围内作为诊断输出，不加入可导航路径，也不能成为扩展桥。规范状态改变后，已缓存的获准边须重新授权并失效。路径仍为有界最短固定链，不声称枚举全部替代路径。

别名转换必须指定 `source_contract_version=0.1` 与 `target_definition_version=1`，显式将 `topic_synthesis/domain_synthesis` 转为 `topic/domain`；未知版本拒绝。当前 `model_providers/tokenizers` 为空，独立模型成本边界的通过只证明账本，不能当作真实模型运行或分词费用验收。
