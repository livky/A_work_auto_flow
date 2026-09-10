# v0.1 设计继承与公共基线

本页保留 P0 的**设计继承清点和映射**：G01–G12、共享执行控制 X01、43 个方法以及 C01–C26 均有明确处置、实现落点和 Q 验收关联。没有把旧方法延期或删除。现已补入受约束的底层运行适配、确定性重排、共享预约/结算、持久维护状态和真实导航回归，逐方法当前状态见 [运行继承状态](RUNTIME_STATUS.md)。**43 项已有运行落点，完整旧协议验收仍须逐项核验**；不能仅凭函数存在关闭 12 类保留义务和旧 C 的全部语义。

实施 Run：`RUN-20260909T194710Z-3CF36B2FDD60`。原 v0.1 设计版本及历史状态保持不变；本期具体修订以 [CONTRACTS.md](CONTRACTS.md) 与用户后续明确决定为准。机器来源、原前后置条件和逐项映射见 [inheritance-map.json](inheritance-map.json)。

## 1. 公共基线与维护职责

- [公共副本说明](baseline-v0.1/PUBLIC_BASELINE.md)规定复制范围和历史状态；[来源与副本指纹](baseline-v0.1/source-manifest.json)逐文件登记原路径、原 SHA256、副本 SHA256 和导航调整。
- 12 个原设计文件全部保留，包括 [SPEC](baseline-v0.1/SPEC.md)、[类型](baseline-v0.1/contract_types.py)、[43 方法签名](baseline-v0.1/contract_ports.py)、[原函数目录](baseline-v0.1/function-catalog.json)、[C01–C26](baseline-v0.1/IMPLEMENTATION.md) 与原正反请求。
- 签名、类型、JSON 样本、生成目录和检查器保持原字节；手写 Markdown 仅重定位公共副本导航、检查命令和未分发 Run 的说明入口，不修改原行为或历史验证数字。
- `baseline-v0.1/` 是受控继承依据，不是运行包，也不是另一份活动计划。产品仅导入 `automation/scripts/material_query/` 的运行契约；原 `memory` 继续拥有规范存储与事务。
- 后续更改需同时更新本页和 JSON 中受影响的处置/落点/验收状态。原基线保持固定；需要改旧契约时新建版本，不直接改基线 Python 或生成视图。

## 2. 明确替换与继续继承

| 事项 | 采用的 v0.2 解释 | 保留的旧保证 |
| --- | --- | --- |
| 表示类型与实例 | Definitions 列类型；Realizations.inspect 查固定材料能力；组包另行执行 | 原表示读取、贡献来源、构建计划和草案边界仍保留 |
| 表示名称 | topic_synthesis/domain_synthesis 显式映射 topic/domain，并绑定定义版本 | 不因别名映射丢失回退次序、来源或生成约束 |
| 搜索到组包 | 新入口 search → 选择候选 → assemble | 旧 search 的 context 选项需用显式适配序列保留，不静默忽略 |
| 执行时间 | wall_ms 是活动阶段时间区间并集；用户等待仅消耗独立 TTL | 原账本、预约、真实消耗和取消不重置 |
| 同查询加额度 | 首期不支持追加额度；需明确建立新查询 | 不得假扮原查询续查，也不能隐式无限扩展 |
| 查询存活 | 首期进程内、默认 15 分钟可收紧 TTL、重启 EXPIRED | 游标绑定原请求/授权/版本/消耗，同查询冲突并发拒绝 |

未列明替换的底层字段、前后置条件、状态所有权和错误处理继续有效。新 DTO 省略一个旧字段，不构成删除该约束的依据；适配器必须完整保留，或对不能满足的硬语义明确拒绝。

## 3. 逐功能组的继承

下表保留本期设计目标，当前实际入口、限制和局部测试状态另见 [RUNTIME_STATUS.md](RUNTIME_STATUS.md) 与 JSON 的 `runtime_hook/test_ids`。`material_query/`、`memory/` 均相对于 `automation/scripts/`；P0 保留全部底层协议，阶段列表示主要接入位置。

| 组 | 处置 | 不变量 | 阶段 | 方法数 | 需要核验的差异 |
| --- | --- | --- | --- | ---: | --- |
| G01 固定读取与引用解析 | 保留 | 保持固定版本，批量读取有上界；不依赖召回器。 | P0/P1 | 4 | INH01、INH02、INH06、INH07、INH11 |
| G02 分级CRUD、版本与恢复 | 保留 | 一个批次一个owner，CAS与幂等；新修订保留旧版。 | P0/P4/P1 | 5 | INH01、INH04、INH07、INH08 |
| G03 表示维护 | 细化 | 规范内容和派生表示分开；贡献来源闭包与生成版本可查。 | P0/P1/P4 | 4 | INH01、INH08、INH09、INH12 |
| G04 变化与索引维护 | 保留 | 内容提交与索引水位分离，增量/重建/补偿可重试。 | P0/P2 | 4 | INH04、INH09 |
| G05 候选召回 | 保留 | 实际范围、命中表示和通道诊断贯穿回执。 | P0/P2 | 2 | INH02、INH03、INH06 |
| G06 去重、融合与排序 | 保留 | 相关性不替代证据准入；输入正文有界、无隐藏召回。 | P0/P2 | 5 | INH03、INH05、INH09 |
| G07 关系导航 | 细化 | 导航采纳与科学支持分开，路径固定且展开有界。 | P0/P3 | 3 | INH11 |
| G08 渐进检索编排 | 细化 | 拥有计划和续接状态，范围、排除及预算不丢失。 | P0/P2 | 3 | INH02、INH03、INH06、INH09、INH10 |
| G09 上下文组装 | 细化 | 展开固定候选、补定义和边界，缺口交还编排器。 | P0/P2 | 1 | INH03、INH12 |
| G10 阅读视图 | 保留 | 读取已有正文和结构，不隐式生成新结论。 | P0/P5 | 2 | INH07 |
| G11 策略整理 | 细化 | 按策略正式修订；提交、复核、索引和恢复分别记账。 | P0/P4 | 3 | INH04、INH08 |
| G12 证据、复核与影响 | 保留 | 实际授权和读时有效性由专门规则判定。 | P0/P2/P4 | 4 | INH01、INH02、INH03、INH08、INH11 |
| X01 共享执行控制 | 细化 | 实际执行方预订/结算，父流水线不重复扣费；不构成第十三组业务功能。 | P0/P2 | 3 | INH09 |

## 4. 逐方法映射

所有方法的原前置条件、返回保证、错误类别和调用要求已原样写入 JSON 的 `source` 字段。以下是最初设计落点，不是全量验收完成声明；当前实际符号已在 [运行状态表](RUNTIME_STATUS.md) 列明。实现可用内部函数或适配器承载，但必须满足相同语义；仅复制 Protocol 或把动作登记为 `UNSUPPORTED` 不算完成原义务。

| 原方法 | 处置/阶段 | 新适配落点 | Q 关联 | 理由 |
| --- | --- | --- | --- | --- |
| ContentReader.describe | 保留 / P1 | `material_query/reader.py` | Q16、Q20、Q21 | 保留批量元数据读取和逐项缺口；候选阶段不预读全部正文。 |
| ContentReader.read | 保留 / P1 | `material_query/reader.py` | Q19、Q20、Q21、Q22、Q69 | 固定版本读取由新 reader 适配原存储，返回实际来源/读取量和完整性。 |
| ContentReader.list_page | 保留 / P1 | `material_query/reader.py`、`material_query/structure.py` | Q16、Q56、Q70 | 保留按范围分页的轻量元数据入口；树页不能替代索引全量扫描所需内容页。 |
| ReferenceResolver.resolve | 细化 / P0 | `material_query/legacy_adapter.py`、`material_query/reader.py` | Q20、Q66、Q68 | 旧六字段 Ref 显式转换并回源固定 SHA；relation 进入 EvidenceLink 或边，不能丢弃。 |
| ContentCommands.validate | 保留 / P4 | `material_query/maintenance.py` | Q47、Q48、Q73 | 继续调用原 validate-draft；完整批次/依据绑定及服务端权限重验保留。 |
| ContentCommands.commit | 保留 / P4 | `material_query/maintenance.py` | Q48、Q49、Q50 | 单 owner CAS 与 request_id 幂等由原 memory 服务负责，新应用不得直接写规范文件。 |
| ContentCommands.restore | 保留 / P4 | `material_query/maintenance.py` | Q50、Q54、Q64 | 恢复创建新修订并拒绝覆盖后续修改；沿用既有恢复机制。 |
| RevisionStore.apply | 保留 / P4 | `material_query/foundation.py`、`material_query/maintenance.py` | Q48、Q49、Q50 | 底层物理提交原子性继续归 memory/store；完整原子提交与索引回执分离。 |
| RevisionStore.history | 保留 / P1 | `material_query/foundation.py`、`material_query/reader.py` | Q20、Q50、Q64 | 保留分页提交历史，不用当前结构树伪装固定历史链。 |
| RepresentationCatalog.list | 细化 / P1 | `material_query/definitions.py`、`material_query/representations.py` | Q01、Q02、Q03、Q04 | 由不依赖材料的 Definitions 与按固定材料执行的 Realizations.inspect 分工；available 细分 direct/assemblable。 |
| RepresentationCatalog.read | 细化 / P1 | `material_query/reader.py`、`material_query/representations.py`、`material_query/assembly.py` | Q19、Q20、Q21、Q25 | 读取实际表示或已有字段组合；固定贡献来源闭包并尊重 generation 约束。 |
| RepresentationBuilder.plan | 细化 / P4 | `material_query/representations.py`、`material_query/maintenance.py` | Q25、Q46、Q47、Q73 | 确定性组合计划与需要新语义的维护计划分开；都固定源、定义和策略版本。 |
| RepresentationBuilder.build | 细化 / P4 | `material_query/representations.py`、`material_query/assembly.py`、`material_query/maintenance.py` | Q24、Q25、Q48、Q73 | 机械组合返回临时包；新解释形成 v3 草案，经 review/validate/commit 才获得规范身份。 |
| ChangeReader.read | 保留 / P2 | `material_query/foundation.py`、`material_query/maintenance.py` | Q49、Q70 | 保留有界变化页和游标，供增量与补偿使用，不把同步刷新函数当完整变化协议。 |
| IndexLifecycle.status | 保留 / P2 | `material_query/foundation.py`、`material_query/coordinator.py` | Q14、Q15、Q70 | 读取每后端真实范围水位及覆盖状态；status 本身不隐式修复。 |
| IndexLifecycle.plan | 保留 / P2 | `material_query/foundation.py`、`material_query/maintenance.py` | Q49、Q70 | 增量变化页和全量内容页保持互斥输入，计划固定 IndexKey、basis 和续页位置。 |
| IndexLifecycle.execute | 保留 / P2 | `material_query/foundation.py`、`material_query/maintenance.py` | Q49、Q70 | 补偿原计划、保留未完成项；完整新代次经核验后切换，不重复内容提交。 |
| RecallProvider.capabilities | 保留 / P2 | `material_query/foundation.py`、`material_query/coordinator.py` | Q02、Q14、Q43、Q66 | 如实声明通道/表示/过滤/新鲜度/取消能力；不能满足的硬约束显式拒绝。 |
| RecallProvider.recall | 保留 / P2 | `material_query/foundation.py`、`material_query/coordinator.py` | Q06、Q07、Q08、Q11、Q12、Q14、Q15、Q16 | 复用身份、词法、可用向量及现有融合；保留双身份、原分数、匹配片段、水位和续页。 |
| CandidateDeduplicator.deduplicate | 保留 / P2 | `material_query/foundation.py`、`material_query/coordinator.py` | Q13、Q26 | 按规范固定身份及版本去重，同名不合并；保留所有 ChannelHit 和来源沿袭。 |
| FusionStrategy.fuse | 保留 / P2 | `material_query/foundation.py`、`material_query/coordinator.py` | Q13、Q43、Q66 | 保留可替换窄策略及现有融合基线；Q43 仅关联，仍须补融合专门断言。 |
| Reranker.rerank | 保留 / P2 | `material_query/foundation.py`、`material_query/coordinator.py` | Q16、Q23、Q43、Q66 | 仅对显式有界文本和输入候选重排，不隐藏新召回；无所需模型能力时拒绝。 |
| DiversitySelector.select | 保留 / P2 | `material_query/foundation.py`、`material_query/coordinator.py` | Q12、Q13、Q43 | 准入后才截断，选择输入子集并保留未选原因；相关/多样性不更改复核。 |
| RankingPipeline.rank | 保留 / P2 | `material_query/foundation.py`、`material_query/coordinator.py` | Q12、Q13、Q14、Q43、Q66 | 应用排序入口实际装配窄策略，所有阶段的通道故障与缺正文诊断贯穿。 |
| RelationNavigator.neighbors | 细化 / P3 | `material_query/associations.py`、`material_query/deepening.py` | Q30、Q39、Q40、Q41、Q42 | 由 bounded_graph 与结构视图复用有界导航，固定端点、关系类型与方向。 |
| RelationNavigator.paths | 保留 / P3 | `material_query/foundation.py`、`material_query/deepening.py` | Q38、Q39、Q40、Q41、Q42 | 仍需可回读的有序 edge_id 路径与目标约束；只返回无序边集合不算满足。 |
| RelationNavigator.suggest_links | 细化 / P3 | `material_query/associations.py`、`material_query/deepening.py` | Q29、Q31、Q32、Q33、Q34、Q35、Q36、Q37 | 拆为 discover/decide；临时结构候选可无既有边，采纳为导航不形成科学复核。 |
| ExpansionPolicy.next_step | 细化 / P2 | `material_query/foundation.py`、`material_query/coordinator.py`、`material_query/state.py` | Q26、Q28、Q38、Q41、Q43 | 保留可替换执行决策；首期先显式续查/加深，执行原因与缺口必须可查。 |
| SearchCoordinator.search | 细化 / P2 | `material_query/coordinator.py`、`material_query/state.py`、`material_query/budget.py` | Q05、Q06、Q07、Q08、Q10、Q11、Q12、Q14、Q15、Q16、Q69 | 新 QueryCoordinator.search 先返回绑定请求的固定候选；读取组包改为显式选择后的 assemble。 |
| SearchCoordinator.resume | 替换 / P2 | `material_query/coordinator.py`、`material_query/state.py`、`material_query/budget.py` | Q26、Q27、Q28、Q41、Q71、Q74 | 明确按 v0.2 改为 query_id/cursor 续查；不提供同查询追加额度，需新查询；固定状态、排除及原消耗保留。 |
| ContextBuilder.build | 细化 / P2 | `material_query/assembly.py`、`material_query/reader.py` | Q17、Q18、Q19、Q20、Q21、Q22、Q23、Q24、Q25、Q59 | 新 assemble 只接受原查询选中候选，组 direct/required_context/association/gaps，禁止隐式召回。 |
| ReadViewService.list | 保留 / P5 | `material_query/foundation.py`、`material_query/reader.py`、`material_query/structure.py` | Q55、Q56、Q60 | 保留已有可读文稿/视图发现；StructureView 只负责结构树，不覆盖全部阅读契约。 |
| ReadViewService.render | 保留 / P5 | `material_query/foundation.py`、`material_query/reader.py`、`material_query/assembly.py`、`material_query/structure.py` | Q24、Q54、Q59、Q60 | 全文、分层、摘要、双文稿及图视图共享固定依据；阅读不生成或提交新解释。 |
| MaintenancePlanner.plan | 细化 / P4 | `material_query/maintenance.py` | Q44、Q45、Q46、Q47、Q73 | SemanticMaintenance.plan 先形成有界影响计划，review 追加实际语义审查及新计划版本。 |
| MaintenanceExecutor.execute | 细化 / P4 | `material_query/maintenance.py` | Q47、Q48、Q49、Q50、Q53、Q54、Q67、Q73 | apply 仅接受服务端固定计划；逐 owner 提交、复核、索引和恢复分别记账，重复执行幂等。 |
| MaintenanceExecutor.status | 保留 / P4 | `material_query/foundation.py`、`material_query/maintenance.py` | Q49、Q50、Q61、Q74 | 保留不推进任务的状态读取入口；plan_id 可访问性校验和重启后依据重验不可省略。 |
| EvidencePolicy.authorize | 保留 / P0 | `material_query/foundation.py`、`material_query/reader.py`、`material_query/coordinator.py`、`material_query/maintenance.py` | Q07、Q10、Q21、Q33、Q57 | 可信 Context 由应用创建；每读写阶段取请求/上限/授权交集并保留排除。 |
| EvidencePolicy.assess | 保留 / P2 | `material_query/foundation.py`、`material_query/coordinator.py`、`material_query/assembly.py` | Q08、Q11、Q12、Q21、Q67 | 逐固定目标/claim 计算有效性和适用域；保留已评估及未解决部分，不信任索引自报。 |
| ReviewService.append_review | 保留 / P4 | `material_query/foundation.py`、`material_query/maintenance.py` | Q46、Q53、Q67 | 新内容以获授权且适用的流程追加新复核历史；既不继承旧复核，也不能只验证不继承而漏掉正向追加。 |
| ImpactAnalyzer.affected | 细化 / P4 | `material_query/foundation.py`、`material_query/maintenance.py`、`material_query/deepening.py` | Q39、Q44、Q45 | 分页返回已登记下游，并增加有界主题/近邻/反馈候选；未检查区域明确报告。 |
| ExecutionControl.reserve | 细化 / P2 | `material_query/foundation.py`、`material_query/budget.py`、`material_query/state.py` | Q23、Q26、Q34、Q41、Q71 | 执行前原子预约原账本上界；按 v0.2 累计活动墙钟计时，等待只消耗独立 TTL。 |
| ExecutionControl.settle | 细化 / P2 | `material_query/foundation.py`、`material_query/budget.py`、`material_query/state.py` | Q23、Q26、Q28、Q71 | 结算幂等、释放余量，父子不重复扣费；并行阶段区间并集计墙钟。 |
| ExecutionControl.check_cancelled | 保留 / P2 | `material_query/foundation.py`、`material_query/budget.py`、`material_query/state.py` | Q28、Q74 | 统一取消句柄；停发新工作并保留真实已完成部分，不假称已强停不支持取消的后端。 |

## 5. C01–C26 与 Q 的逐项对应

`直接对应`只表示设计文字已有相关断言；`需补断言`表示 Q 有关联但不足以覆盖原 C 的全部要求。它们不是产品测试通过率。Q 定义来源为 [test-cases.json](test-cases.json)；已经执行的 Foundation 23 项、P3 17 项、共享账本 11 项和维护状态 11 项真实回归在 JSON 登记准确测试 ID，相关 C 仅标 `partial_runtime_passed`。没有列出的断言或集成场景仍须核验，不能由局部通过推出整条旧 C 完成。

| 旧 ID | 原要求 | 处置 | Q 关联 | 设计覆盖 | 说明 |
| --- | --- | --- | --- | --- | --- |
| C01 | 旧六字段 Ref 指定旧修订，读取不漂移；SHA 冲突明确失败 | 保留 | Q20、Q66 | 直接对应 | 旧六字段引用、固定修订和 SHA 冲突均保留。 |
| C02 | owner_ids=null 不限、[] 空集；排除优先于显式包含 | 保留 | Q06、Q07 | 直接对应 | null/空集与排除优先直接继承；显式 include_refs 字段仍须补齐。 |
| C03 | 失败经验、知识角色、复核和当前有效性分别筛选；未知按策略处理 | 保留 | Q08、Q11 | 直接对应 | 角色、尝试结果、复核与有效性独立；未知默认不匹配。 |
| C04 | 一个记录多 claim，仅一项被接受时不整体变为确定事实 | 保留 | Q11 | 直接对应 | 逐 claim 准入，不能由单 claim 接受推出整篇有效。 |
| C05 | 关键词卡/摘要/全文同源命中只归并身份，不增加独立支持数 | 细化 | Q03、Q13 | 直接对应 | 同源表示去重保留命中渠道；可组合摘要无需复制规范记录。 |
| C06 | 请求缺失或未实现表示，明确 missing/unsupported；回退必须获允许 | 细化 | Q02、Q04 | 需补断言 | 五状态细化旧可用性；仍需补 missing_policy 和显式 fallback 顺序的正反断言。 |
| C07 | 领域综合中一个贡献来源无权读取，不能通过概要泄露 | 保留 | Q10、Q21 | 需补断言 | Q10/Q21验证范围与重新鉴权，但需专测领域综合全部贡献来源闭包。 |
| C08 | 正式摘要生成新解释时返回草案，提交后才有规范固定身份 | 细化 | Q24、Q25、Q48 | 直接对应 | 模板并列/临时包与新增语义草案分开；规范固定身份只能来自提交。 |
| C09 | 内容已提交而索引失败，重试原索引计划不产生第二内容修订 | 保留 | Q49 | 直接对应 | 索引失败重试原索引计划，内容提交不得重复。 |
| C10 | 全量重建有历史无变化流的对象仍被纳入；半成品不发布完整水位 | 保留 | Q70 | 直接对应 | 全量枚举不依赖完整变化流，新代次完成前不替换完整索引。 |
| C11 | 相同 IndexPlan 重试幂等，未完成事件保留；不跳过游标缺口 | 保留 | Q70 | 需补断言 | Q70写明重试幂等，仍需固定事件缺口/分页游标故障断言。 |
| C12 | current 请求碰到过期索引：显式补偿/降级/拒绝，不伪造已完整 | 保留 | Q15 | 直接对应 | 当前索引落后显式补偿/降级/拒绝，回源不能证明全库已覆盖。 |
| C13 | 小 result_limit 不触发全库正文/向量窗口读取；统计实际读字节 | 保留 | Q16 | 直接对应 | 小 limit 下计量实际读取，不能先扫描全库正文再截断。 |
| C14 | 一个通道失败，其他结果与故障同时保留；最终材料包仍显示降级 | 保留 | Q14、Q59 | 需补断言 | Q14仅调用 search；须新增 assemble 后最终包仍保留缺通道诊断的集成断言。 |
| C15 | 更换融合或重排器不改业务调用方、身份或复核状态 | 保留 | Q43、Q66 | 需补断言 | Q43只替换 DeepeningStrategy，不能代替融合/重排器替换测试；补独立 G06 断言。 |
| C16 | 正式准入后不足K项，在剩余预算中补召回或明确覆盖不足 | 保留 | Q11、Q12 | 直接对应 | 正式准入先于最终 K 截断；不足在余量内补召回或报告缺口。 |
| C17 | 图同名实体歧义、错误连接与过期来源可见，路径保留差异 | 保留 | Q32、Q40、Q42 | 需补断言 | 同词机制负例与旧边状态已设计；另补同名实体消歧、错误连接和路径差异的专门断言。 |
| C18 | 关联被采纳为导航，不生成 accepted 科学支持 | 细化 | Q36、Q37 | 直接对应 | discover/decide 分离；导航采纳和有范围的拒绝都不变成科学复核。 |
| C19 | 扩大范围与深入表示分别选择，原角色/结果筛选和排除保留 | 细化 | Q33、Q38、Q43 | 需补断言 | 表示加深和补充范围已明确；一般语料扩大轴/原硬筛选继承仍需独立断言。 |
| C20 | 续查不能重置已用预算、累计跳数或提升权限；追加额度显式记账 | 替换 | Q26、Q27、Q41、Q71、Q74 | 直接对应 | 累计约束保留；v0.2明确取消同查询追加额度，需新查询；活动时间与TTL分离。 |
| C21 | 取消或截止后返回已完成部分、真实消耗与停止位置 | 细化 | Q28、Q71 | 直接对应 | 预算/取消保留部分结果和停止位置；墙钟截止采用v0.2活动时间及独立TTL。 |
| C22 | 上下文补齐必需定义；定义被排除/预算不足时不标完整 | 保留 | Q22、Q23 | 直接对应 | 必需定义被排除/预算不足时 complete=false，不能破坏公式后声称完整。 |
| C23 | 同一工作区视图读取不产生规范修订；新报告解释走正式提交 | 保留 | Q24、Q54、Q60 | 需补断言 | Q24只验证查询不写；必须覆盖独立文稿/图 render 不生成规范修订，及新解释走提交。 |
| C24 | 正式整理新版本不自动继承失配复核，适用流程可追加新复核 | 保留 | Q46、Q53、Q67 | 需补断言 | Q67覆盖不继承旧复核，尚需适用授权流程对新claim追加新复核的正向集成断言。 |
| C25 | 跨 owner 部分完成列出每个提交；恢复不会覆盖后续新修改 | 保留 | Q50 | 直接对应 | 逐owner回执与恢复拒绝覆盖后续修改直接继承。 |
| C26 | 替换后端后调用方不变；不支持的硬语义不能被适配器忽略 | 保留 | Q43、Q66、Q72 | 需补断言 | 现有Q仅覆盖加深替换/旧API/生成链；需覆盖读取、索引、召回、排序、存储适配的硬语义拒绝。 |

不能继续使用“C01–C26 已全部由 Q 用例覆盖”作为 P0 退出依据。尤其 C15 的融合/重排替换与 Q43 的加深策略替换是不同测试；C14 要把通道降级追到最终材料包；C24 除了禁止继承旧复核，还要求适用流程能够给新内容追加真实复核。

## 6. 运行层需补齐的最小字段和签名

下面 12 项全部是**本期保留义务**，没有作为后续候选延期。它们记录相对当前 v0.2 设计 DTO 的实际差异，待运行实现与相应测试逐项关闭。保留完整 foundation 契约只是第一步，调用方必须实际传递并执行这些约束。

### INH01 完整固定身份及旧六字段 Ref 映射

发现：v0.2 FixedRef 只列 record/file；v0.1 的 owner/claim/representation 不能靠改标签映射。relation 在旧 Ref 中存在，不能在转换时丢失。

最小字段与语义：

- 内部 FixedRef 保留 target_kind={record,owner,claim,file,representation}、target_id、revision、sha256、locator；新 DTO kind/id 是显式别名，不是缩减身份集合。
- 旧 LegacyRef 的 sha256 可缺省，但只有真实回源并核验固定修订后补齐；无法解析必须返回缺口或拒绝，不取当前 HEAD 猜测。
- relation 原值保存在 EvidenceLink 或有类型边中；额外记录 source_ref/转换依据以支持旧响应回读。
- record 使用正 revision 与 record_hash；file 使用登记 source_id/内容 SHA256；owner/claim/representation 使用各自真实固定目标，不能强改成 record。
- claim 的父记录与定位可作为解析依据，但须保留 claim 身份/版本和仅针对该 claim 的语义。

最小签名/适配：

- `ReferenceResolver.resolve(refs: tuple[LegacyRef, ...], ctx) -> Outcome[tuple[EvidenceLink, ...]]`
- `ContentReader.describe/read；FixedRef 与 v0.2 DTO 的显式双向转换`

须补或确认的断言：

- 旧六字段逐字段往返保留 relation；四种旧 kind 的固定读取、缺 SHA 的真实补齐和失配拒绝。
- 两个 claim 仅一个已复核时，解析不能把授权/复核范围扩到父记录全部内容。

对应 C01、C04、C07、C26；Q 关联：Q20、Q66、Q68、Q11。

### INH02 Scope 的来源、包含/排除、时间和确信筛选

发现：v0.2 Scope 省略 source_ids/include_refs、一般 exclude_ids、confidence_levels、结构化 applicability，以及 occurred_at/valid_at 时间维度。

最小字段与语义：

- source_ids: tuple[str,...] | None；include_refs: tuple[FixedRef,...]；exclude_ids: tuple[str,...]，同时保留新 excluded_refs/excluded_owner_ids 的精确语义。
- confidence_levels: tuple[high|medium|low|unknown,...] | None；不能用 score 或 evidence_status 代替。
- Applicability 保留 description/conditions/exclusions/valid_from/valid_until/subject_versions；字符串 applicability 只作为有版本的便捷输入，不能吞掉旧结构化硬约束。
- TimeWindow(field=recorded_at|occurred_at|valid_at,start_inclusive,end_exclusive)；v0.2 recorded_from/recorded_before 为 recorded_at 的显式兼容形式。
- owner_ids/kinds/layers(levels)/source_ids/roles/outcomes/review_states/validities/confidence 各自 null=不限、[]=空集；不同字段 AND、同字段 OR。
- 显式 include 不能覆盖排除、请求范围上限或授权；unknown 默认不匹配已启用约束，include_unknown 只能明确放开未知。
- 时间窗口左闭右开；旧 UTC Z 和新 RFC3339 时区规则须显式规范化。同字段双入口冲突时拒绝，不靠覆盖顺序取值。

最小签名/适配：

- `normalize_scope(old: CorpusScope | new: Scope) -> normalized scope without dropping hard filters`
- `effective_scope = requested ∩ ceiling ∩ authorized − persistent exclusions；每次读取/扩展重新核验`

须补或确认的断言：

- 每个 null/[] 及未知策略；显式包含同时被身份、owner 和来源排除时仍不得返回。
- recorded_at/occurred_at/valid_at 三类边界与时区；source_ids 和 confidence/applicability 约束不能被适配器忽略。

对应 C02、C03、C07、C19、C26；Q 关联：Q06、Q07、Q08、Q09、Q10、Q21、Q33、Q66。

### INH03 结构化命中来源、逐 claim 评估及水位诊断

发现：v0.2 Candidate 的 refs/channels/score/evidence_status 不足以表达逐通道命中表示、原始分数含义、逐 claim 评估和覆盖水位。

最小字段与语义：

- Candidate 保留规范 content_ref 与逐 hit 的 representation_ref；同源多表示不是独立支持数。
- ChannelHit 至少含 channel/provider(name,version)/representation_ref/rank/raw_score/score_meaning/matched_text；ranking_score 独立于原始分数。
- EvidenceAssessment 保留 target/review_state/validity/applicability/assessed_at/review_refs/evaluated_claim_refs/unresolved_claim_refs/reasons。
- CandidateBatch/RankedBatch 保留 basis/watermarks/omitted/next_cursor；水位明确索引键、来源范围、版本与 complete/partial/unknown。
- 最终 MaterialPacket 或其外层 Result 保留查询和后续阶段的结构化缺通道/过期/缺源诊断，不只在 search 临时显示。

最小签名/适配：

- `RecallProvider.recall(...) -> CandidateBatch`
- `RankingPipeline.rank(...) -> RankedBatch`
- `EvidencePolicy.assess(refs,purpose,applicability,basis,ctx) -> per-target assessments`

须补或确认的断言：

- 同源双表示命中保留不同通道原分数/片段/模型版本，融合不得擦掉。
- 向量不可用但词法成功，经选择、assemble、响应序列化后最终包仍显示明确降级。

对应 C04、C05、C14、C16；Q 关联：Q11、Q12、Q13、Q14、Q15、Q59、Q69。

### INH04 变化读取与完整索引生命周期

发现：v0.2 未重述 G04 的独立签名；单个 reconcile 调用或水位字符串不能覆盖增量、重建、补偿的完整行为。

最小字段与语义：

- IndexKey(channel,representation,encoder,analyzer,dimension)；模型/编码变更保持可隔离版本，本期384维兼容边界不变。
- ChangeEvent(event_id,owner_id,commit_id,previous_refs,current_refs)；IndexPlan 含 plan_id/mode/index/scope/input refs/basis/from_cursor/next_scan_cursor。
- Watermark 含 covered_basis/cursor/coverage；IndexReceipt 含 completed_events/pending_events/watermark/resume_cursor。
- 增量 changes 与全量 contents 恰好一种有效输入；变化流不完整不能阻止全量内容枚举。
- 索引失败与内容已提交分别持久回执；未完成页不可推进完整水位，重建完整新代次后才切换。

最小签名/适配：

- `ChangeReader.read(scope,page,ctx)`
- `IndexLifecycle.status(indexes,scope,ctx)`
- `IndexLifecycle.plan(mode,index,scope,changes,contents,ctx)`
- `IndexLifecycle.execute(plan,ctx)`

须补或确认的断言：

- 无历史变化流对象仍被全量纳入；中断重建不发布完整水位。
- 同 plan 重试、跨页事件缺口、重复事件及部分失败不跳过游标；索引补偿不再次提交内容。

对应 C09、C10、C11、C12、C26；Q 关联：Q15、Q49、Q70。

### INH05 独立排序策略及替换验收

发现：v0.2 只在行为描述提及 G06；Q43 的端口实际是 DeepeningStrategy.deepen，不能证明融合或重排可替换。

最小字段与语义：

- StrategyRef(name,version) 与调用实际使用的策略回执；重排输入 TextSlice 显式有界，ranking_score 不改复核。
- 保留去重固定身份、融合通道依据、多样性未选理由及各阶段 omitted。

最小签名/适配：

- `CandidateDeduplicator.deduplicate(batches,ctx)`
- `FusionStrategy.fuse(query,batch,ctx)`
- `Reranker.rerank(query,ranked,texts,ctx)`
- `DiversitySelector.select(query,ranked,limit,ctx)`
- `RankingPipeline.rank(request,ctx)`

须补或确认的断言：

- 分别替换两个融合实现与两个重排实现，查询调用方/固定身份/复核状态不变。
- 缺正文或模型/额度不足显式失败；重排器不能自行召回；正式准入不足 K 的补召回仍由编排控制。

对应 C15、C16、C26；Q 关联：Q12、Q13、Q16、Q23、Q43、Q66。

### INH06 查询硬能力、新鲜度和扩展控制

发现：v0.2 QueryRequest 未承载旧 seeds/dialect/channels/planner/ranking/expansion_axes/audit/fixed 及显式修复配置，必须由完整底层协议和显式适配保留。

最小字段与语义：

- QuerySpec 保留 seeds、dialect=plain|phrase|boolean、channels、planner/ranking 的注册版本以及 expansion_axes。
- purpose=audit 与 exploration/formal 保持不同用途；客户端不能将 audit 静默转成 exploration。
- FreshnessPolicy 保留 mode=fixed|current|allow_stale、allow_index_repair、max_staleness_seconds；需要修复时仍计预算且不得隐式扩大权限。
- ProviderCapabilities 保留支持通道/表示/过滤/语法/新鲜度/硬取消/过滤下推；无法满足硬条件必须拒绝。
- v0.2 的显式搜索→选择→组包与原 search 可含 context 分开适配；旧 context 参数不应被忽略。
- 原扩大语料与深入表示两个方向继续独立。首期更改主查询硬筛选须新查询；显式补充范围受 ceiling/排除/授权约束。
- 已明确变更：旧 ResumeRequest.additional_budget 不在 v0.2 同查询入口支持；新请求建立新账本并标明新查询，不伪装旧续查。
- 已明确变更：查询首期进程内、默认15分钟TTL、重启EXPIRED；原版本切换行为需保留前序查询和新basis，不复活零消耗旧游标。

最小签名/适配：

- `ExpansionPolicy.next_step(progress,capabilities,ctx)`
- `QueryCoordinator.search/assemble/resume/cancel`
- `Legacy QuerySpec/ResumeRequest 到新应用调用序列的显式转换或明确不支持回执`

须补或确认的断言：

- 种子查询、非plain语法、audit、fixed 与 current 的显式处理；不支持不得静默删字段。
- 扩大范围和加深表示分别选择，原角色/结果与排除保留；旧追加预算请求明确拒绝并提示新查询。

对应 C12、C16、C19、C20、C26；Q 关联：Q05、Q12、Q14、Q15、Q26、Q27、Q33、Q38、Q43、Q66、Q74。

### INH07 历史分页与独立阅读视图

发现：v0.2 StructureView.list_page 是结构树；它没有替代按历史分页和 render 读取全文/层级/双文稿/图的所有能力。

最小字段与语义：

- ReadView 保留 view、text、graph、basis、omitted；ViewRequest 保留 refs/scope/basis/max_chars。
- Page 的 items/next_cursor/basis 与版本历史链保留；结构树的 parent_ref 不是提交历史游标。

最小签名/适配：

- `RevisionStore.history(owner,page,ctx)`
- `ReadViewService.list(scope,page,ctx)`
- `ReadViewService.render(request,ctx)`

须补或确认的断言：

- 直接阅读完整过程稿、简报和关系图不产生规范修订；新解释经正式提交才出现。
- 分页历史包含旧修订而非只列当前 HEAD；跨 owner 读取报告乐观一致性。

对应 C01、C23、C26；Q 关联：Q20、Q24、Q54、Q55、Q56、Q60、Q64、Q69。

### INH08 维护状态、完整提交回执与新增复核

发现：v0.2 apply 的简短 owner/commit 元组和单一 index_status 缺少 client_key→新Ref、逐owner索引/复核待办及 status/恢复计划；Q67只覆盖不继承旧复核。

最小字段与语义：

- CommitReceipt 保留 request_id/owner_id/commit_id/changes(client_key,previous,current,action)/change_cursor/follow_up_required。
- MaintenanceReceipt 保留逐 owner commits、pending_owner_ids、review_states/pending_reviews、index_states 和续接/恢复身份；简版UI可显示摘要但不能擦除真实回执。
- MaintenanceRequest 的 organize/recover 语义保留；恢复是新计划/新修订，不能倒退HEAD。
- ReviewCommand 保留目标、expected_owner_head、state、applicability、evidence、method、reason 及 request_id。
- 维护 plan/review/apply 使用服务端保存身份和digest；reviewed_refs 与 semantic_reviewer 由可核验实际阅读/审查来源支持。
- 授权且适用的自动/人工复核均可追加新复核；新claim不继承旧认可。未验证客户端自报不能冒充真实审查。

最小签名/适配：

- `ContentCommands.validate/commit/restore 与 RevisionStore.apply/history`
- `SemanticMaintenance.plan/review/apply；MaintenanceExecutor.status(plan_id,ctx) 保留只读状态入口`
- `ReviewService.append_review(command,ctx)`
- `ImpactAnalyzer.affected(refs,scope,page,ctx)`

须补或确认的断言：

- 新claim经适用授权流程追加新review且保留旧review；不只测拒绝继承。
- 部分跨owner提交返回每个真实固定新Ref/待办；status不推进任务，重启不自动续写。
- 恢复计划拒绝覆盖后续新修改；内容已提交但索引失败只重试投影。

对应 C08、C09、C24、C25、C26；Q 关联：Q44、Q45、Q46、Q47、Q48、Q49、Q50、Q53、Q61、Q67、Q73。

### INH09 完整预算维度与执行控制

发现：v0.2 Budget 把模型输入/输出token合为model_tokens，未公开 max_rerank/model_calls/tokenizer；不能因此忽略底层已指定的硬上限。

最小字段与语义：

- 内部账本保留 candidates/reranked/graph_nodes/graph_edges/累计hops/read_bytes/model_calls/model_input_tokens/model_output_tokens/context_chars。
- 保留 tokenizer(name,version)；合并的 model_tokens 可以作为额外总上限，不能替代旧输入/输出及调用次数约束。
- BudgetReservation 保留 reservation_id/budget_handle/ceiling；预约与结算幂等，父子阶段不得重复扣费。
- 明确替换旧 deadline 主导语义：新应用 wall_ms 为活动阶段时间区间并集，用户等待不计，TTL独立；旧deadline适配必须显式拒绝冲突或形成受控限制。
- Context/CallContext 由可信服务端装配 root_operation_id/访问/账本/取消绑定；恢复不相信客户端剩余额度。
- 新 QueryRequest 的整数字段禁止bool、负数和非有限数；零额度禁止相应操作。

最小签名/适配：

- `ExecutionControl.reserve(ceiling,ctx)`
- `ExecutionControl.settle(reservation,actual,ctx)`
- `ExecutionControl.check_cancelled(ctx)`

须补或确认的断言：

- 输入token先耗尽、输出token先耗尽、调用数先耗尽及总额先耗尽四种边界。
- 活动墙钟并行区间并集、用户等待只耗TTL；取消/续查/重复settle不重置或重复扣费。

对应 C13、C20、C21；Q 关联：Q23、Q26、Q28、Q34、Q41、Q71、Q74。

### INH10 结构化错误、重试语义和读取依据

发现：新 Result code/warnings 无法单独承载每项受影响引用、重试方式和最后确定状态；Basis 省略原 observed_at/basis_id。

最小字段与语义：

- 保留 Issue(code,message,affected_refs,retry)；对外返回前过滤不可见对象信息。
- ReadBasis 保留 basis_id/owner_heads/source_refs/observed_at/consistency；新版 Basis 的索引水位是新增信息。
- 错误码可映射为 v0.2 公共码，但原错误类别/阶段、是否可按同一请求重试及已提交状态须保留结构化诊断。
- ok必须有业务值的规则需对cancel Result[None]明确特例；partial保留真实结果和缺口，单owner事务不得以partial掩盖部分提交。

最小签名/适配：

- `统一 Outcome↔Result 适配，保留 retry、affected_refs 和阶段状态；HTTP 只映射传输状态`

须补或确认的断言：

- 同一内容请求与同一索引重试需要不同动作；UI/材料包不能只剩一个笼统failed。
- 拒绝无业务值，部分结果有缺口；诊断不泄漏隐藏对象数量/标题/路径。

对应 C14、C21、C25；Q 关联：Q14、Q28、Q49、Q59、Q69。

### INH11 关系枚举、固定路径和建议语义

发现：v0.2 新增 contains/precedes/member_of，但省略旧 references/input/same_entity/mentions；DeepenReceipt 没有显式有序路径及目标约束。

最小字段与语义：

- 旧关系 references/input/same_entity/mentions 与新关系同时注册，不能全部改写成 depends_on；未知关系拒绝。
- GraphRequest 的 seeds/targets/edge_kinds/direction/累计hop及node/edge/cursor保留；out/in与forward/reverse显式映射。
- GraphSlice.paths 保留有序 edge_id；每条边保留固定两端、证据链接关系、state、differences；新版conditions/proposer/generator_version作为细化。
- 临时建议、导航采纳与verified_claim互不替代；旧边版本失效不自动继承新版采纳。

最小签名/适配：

- `RelationNavigator.neighbors/paths/suggest_links`
- `AssociationStrategy.discover/decide；DeepeningStrategy.deepen`

须补或确认的断言：

- 旧关系无损转换，同名不同实体不合并；错误连接或旧版边不能被路径裁剪隐藏。
- seed→target路径顺序可复读，差异/缺口保留；分页和循环不能归零累计跳数。

对应 C17、C18、C20；Q 关联：Q31、Q32、Q36、Q37、Q38、Q39、Q40、Q41、Q42、Q43。

### INH12 表示注册、命名映射与构建边界

发现：新六类型与五状态细化旧实例目录，但旧注册键可扩展、回退顺序、allow_build和构建计划仍需显式继承。

最小字段与语义：

- topic_synthesis→topic、domain_synthesis→domain 采用版本化显式别名；原件/全文/章节/摘要名称不变，不能只按字符串相近猜测。
- 注册键可扩展；首期六种支持集合与类型表示能力分开。未注册键UNSUPPORTED，不能映射到任意路径、SQL或可执行代码。
- available 依实际字段映射 direct/assemblable；missing 需结合 missing_selectors/needs_generation表达；stale/unsupported继续显式。
- DefinitionRef、贡献来源、selector、generator/定义版本贯穿计划与实际组合；allow_build不得转成自动规范提交权限。
- fallback_order及missing=reject|skip|fallback保留；未知回退或越权贡献来源不替换为默认结果。

最小签名/适配：

- `Definitions.list/get；Realizations.inspect`
- `RepresentationCatalog.read 与 RepresentationBuilder.plan/build 的内部适配仍保留，不能仅用类型列表替代`

须补或确认的断言：

- 有L1 retrieval_description可组合，不因未保存单独摘要判缺失；缺必需定义不得标完整。
- 显式fallback顺序、generation=never/draft_only、source变化和全部贡献来源权限闭包。

对应 C05、C06、C07、C08、C22；Q 关联：Q01、Q02、Q03、Q04、Q19、Q22、Q24、Q25、Q64。

## 7. 已完成的验证与仍需关闭的门槛

公共副本的原检查器实际执行通过：40 个领域方法、3 个执行控制方法、72 个数据结构和 12 个正反结构请求。该检查只验证设计一致性和请求结构，不执行存储、权限、检索或维护后端。

继承检查器另行核对：方法/组/旧 C 编号集合完整且无重复、Q 引用存在、每项有处置和落点、缺口引用可解析、12 文件指纹及公共链接。当前完整工作区还可核验原源文件未变；公共包缺少 Project 原件时会明确标为仅验证副本，不能伪称检查过未分发原件。

从工作区根目录运行：

```powershell
.\automation\python.ps1 docs/design/representation-query-v0.2/baseline-v0.1/check_contracts.py
.\automation\python.ps1 docs/design/representation-query-v0.2/baseline-v0.1/check_inheritance.py
```

此子任务未改产品代码、旧 Run、规范记录或冻结 fixture。真实运行契约、Q 的实际测试 ID、跨端口行为、公共发行与真实 setup 升级由本期对应阶段继续验证；P0 不能因这份清点完整而提前宣称全部退出门槛满足。
