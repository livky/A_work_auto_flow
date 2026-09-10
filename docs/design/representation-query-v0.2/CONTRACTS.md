# 接口与行为契约

本规范用于后续开发，2026-09-10 尚未实施。所有方法签名见 [contracts.py](contracts.py)。旧 memory-v3 请求不直接接收这些新字段；新应用服务通过适配器调用原能力。

## 1. 三种对象分开

**表示类型 Definition** 是版本化的组合规则，不绑定具体分析。`Definitions.list/get` 只返回六种注册类型与支持情况，不扫描全部正文。**实际表示 Realization** 是固定材料按类型能提供哪些内容。**材料包 MaterialPacket** 是针对本次问题、选定候选与预算形成的临时输出，包含实际来源、字段与省略清单。

| key / 用户名称 | 首期主要内容 | 必需补充与加深路线 |
|---|---|---|
| original / 原始材料 | 已登记 L0 原件或受控摘录 | 定位信息、必要 L2 背景；从命中块到原页/文件；无权或无法读取明确缺失 |
| full / 完整研究内容 | L1 完整技术单元；选择文稿时按过程稿章节顺序 | L2 决策、L3 限制及 L0 固定引用；缺定义不可标完整 |
| section / 相关章节与技术块 | 被选中的 L1 blocks 或独立 document_section | 变量定义、单位、前置块；章节到技术单元到原文 |
| unit_digest / 单元摘要 | L1 retrieval_description 的问题、方法、结果、限制；L3 则用问题/建议/适用模板 | 原技术单元或经验固定引用；不要求另存摘要文件 |
| topic / 主题材料 | L4 地图＋已有简报相关章节 | 相关 L3/L2 的冲突/限制、L1 固定入口及过程稿目录 |
| domain / 领域材料 | 多个选定主题的地图/简报，逐主题并列 | 跨主题差异、反证与来源；产生新的统一解释必须生成待审草案 |

层级描述记录用途：L0 来源、L1 技术内容、L2 事件/决策、L3 经验、L4 地图。完整研究过程与简报是独立 document/section（level=null），不增加 L5。类型组合规则只读已有记录。FieldRule.selectors 首期登记 `source.content`、`detail.blocks`、`detail.retrieval_description`、`event.decision`、`experience.recommendation`、`experience.applicability`、`map`、`document.sections`、`document_section.content` 等明确字段路径；实现时逐项映射实际 v3 字段，未知路径拒绝。

Realization 状态：direct 可直接读取；assemblable 可由已有字段组合；needs_generation 需要新的语义内容；stale 有来源/类型版本漂移；unsupported 当前提供器不支持。类型存在、材料可组合和索引已覆盖分别显示。没有摘要不等于不能组合摘要；也不能把缺正文伪装成可用摘要。generation=never 的类型禁止生成；draft_only 只产生草案。查询不会自动提交新规范内容，首期 MaterialPacket.canonical=false。

## 2. 查询与组包

1. 应用层验证 schema/枚举、注册策略与定义版本，创建可信 Context 和累计账本。question 与 keywords 至少一项非空。scope、scope_ceiling 与权限取交集；请求的 ceiling 只能收紧授权。所有后续操作绑定服务端保存的原请求。
2. 搜索已有索引。G05 首期使用现有身份、词法与可用向量通道，保留现有融合；G06 去重合并同源表示，保留通道来源。缺通道返回能力与降级，不偷偷下载模型。
3. 核验固定版本、表示可用性与用途准入，再给最终候选。正式用途逐 claim 检查有效复核、适用域与版本；不将一个被接受的 claim 扩成整篇已验证。准入后不足 K，在剩余额度内补取，否则列缺口。
4. 返回 SearchReceipt，包括 query_id、摘要指纹、固定候选、游标和到期时间。score 仅用于当前策略排序，不能当置信度。候选只显示已有索引的相关摘录和实际能力，选择前不读取全部全文。
5. 用户或 AI 选择 candidate_ids，assemble 只接受同一查询返回的候选。服务端重新核验权限、原请求指纹和固定依据；读取所选内容与注册的必需上下文，按定义组合。不得隐含启动新召回、改变用途或范围。
6. MaterialPacket 分 direct、required_context、association、gaps 四区，逐段保存 FixedRef/selector，列出 contributors 与 omitted。预算不足、缺定义、源不可读或过期时 complete=false。必要定义不能为凑字符数截成错误公式。
7. 继续查找使用 resume；加深使用 DeepeningStrategy。每一步共享原账本、排除与授权；取消保留已完成结果及实际消耗。新查询可以有新预算，但不能冒充同一查询的免费续查。

Scope 的 null=该维度不限，[]=空集。所有筛选并用，排除优先；unknown 默认不匹配约束，只有 include_unknown=true 才显式纳入。时间为 RFC3339，区间左闭右开。固定引用按 record_hash 核验记录，文件按来源登记和内容 SHA256 核验，不能只用标题或当前 HEAD。跨对象读取报告各 HEAD 与乐观一致性，不能宣称全局事务快照。

预算全部非负整数，output_share 为 [0,1]。消耗单位与 Budget 一致；wall_ms 为各实际执行阶段的累计活动墙钟时间：同一阶段并行任务按时间区间并集计量，不对并行耗时求和；用户阅读、勾选和确认期间不计入执行预算。查询存活时间由独立TTL限制。首期可用可调 UI 预设：10秒、2MiB 读取、12000字符、100候选、50图节点、100边、2跳、0模型token；这是启动配置，不是实测最优值。联想默认 off；打开后默认最多2项、输出占比15%，未使用份额可回给主材料，联想不得抢占主材料必需定义。客户端缩小预算可接受；首期不提供同查询加额度接口，超额须明确发起新查询。

## 3. 联想与加深策略接口

AssociationStrategy.discover 产生临时候选：固定两端来源、共同结构、差异、可迁移条件、建议验证方法、生成方法与状态。调用选项从 query_id 的 AssociationOptions 读取，不能绕过最初开关和预算。相关性准入先于新颖性。首期 existing_only 读取已有有效导航关系；explore_structural 通过已有词法/向量候选和 AI 的结构比较，允许没有既存边的材料成为候选，但仅在明确启用且有可用执行代理时提供。无代理返回 unsupported，不能返回空列表假装已探索。

StructuralProfile 的 problem、变量角色、mechanism、约束、干预与结果条件由 AI/人依据固定来源提取；不能按共享几个词自动断言机制相同。生成该 profile 的步骤本身也计入预算。模板输出、候选召回可由程序执行；语义比较由 [联想 Skill](../../../automation/workflows/association-exploration/SKILL.md) 主导。首期不要求新增结构向量索引。

supplement_scope 默认继承主范围；若主查失败、联想查成功，须明确给出独立 outcome 筛选，并仍受 scope_ceiling、授权和全部原排除约束；UI 显示差异，不悄悄放宽。decide 的 accept_navigation 仅保存导航用途，reject 保存有范围的反馈。正式证据复核走现有证据命令，不能由此产生 verified_claim。重复 request_id 幂等；同键不同内容冲突；新版本不继承旧候选采纳状态。

DeepeningStrategy 三种模式有统一签名：source_mapping 按精确段落/块定位回源；bounded_graph 沿已有关系做有界遍历；structural_discovery 发现没有既有边的新联系。首期先实现前两种，第三种复用 AssociationStrategy 的受限 AI 路径并允许 unsupported。策略名字和版本由注册表解析，禁止请求自带任意可执行代码。更换实现不改 QueryCoordinator、UI 和材料包格式。

图有五类用途：contains/precedes 组织位置与顺序；depends_on 表示 source 使用 target，上游变化查 reverse；supports/contradicts/supersedes 表示证据；similar_structure 表示经验联想；member_of 表示主题归属。GraphEdge 固定两端版本、依据、作者/生成版本、状态、条件和差异。邻接投影双向可查，visited 按固定节点身份去重；方向、关系、跳数、节点、边、时间均有上限。循环和分页不重置累计跳数。

规范记录内的结构/固定引用及被明确采纳的关系是权威来源，SQLite memory_edges/后续邻接表是可重建投影。内容提交、显式采纳/撤回、源版本变更产生更新任务；查询临时结果不全量入图。图水位与词法/向量分别记录，读取重检权限。模型/编码更换重建相应投影，不重写规范结论。

## 4. AI 主导的语义维护

SemanticMaintenance.plan 由程序形成影响候选和固定依据；除反向依赖，还检查限定范围的主题成员、语义邻近和实际反馈，报告未检查区域，不能宣称发现全部影响。无新引用边并不代表新反证不影响旧综合。

AI 通过 [语义维护 Skill](../../../automation/workflows/semantic-maintenance/SKILL.md) 读取完整受影响内容，逐项决定 retain/revise/resynthesize/retract/defer；可以局部改，但须检查整体连贯、定义、反证和范围。review 接收同一 plan 的语义审查及 v3 草案，验证旧 digest、依据、动作合法性，保存不可覆盖的新计划版本，返回新 digest。客户端不能伪造 reviewed_refs 代替真实执行记录；审查身份及实际读取由代理回执核对。

apply 仅接受服务端保存且通过验证的计划身份/指纹，并重新核对 HEAD/权限。通过现有 validate-draft/commit 做单 owner CAS；跨 owner 顺序提交并分别回执，不假装全局原子。内容提交成功、索引失败返回 pending/failed，仅重试投影，不重复内容提交。恢复使用既有恢复机制核对指纹，拒绝覆盖后续新修改。复核历史留存，新 claim/修订不得自动获得旧语义复核。retract 是追加纠错/复核动作，不删除历史记录。

无需生成式 AI 的路径可用字段模板、固定摘录和人工编排；未知语义变化保留待审，不能把哈希、embedding 或模板执行成功当作语义正确。索引任务、schema 校验、读取和事务继续由程序执行。首期无后台自动改写；后续调度是另一个明确启用的能力。

## 5. 状态、失败与兼容

Result 是统一业务回执；code 使用 VALIDATION、DENIED、CONFLICT、EXPIRED、UNSUPPORTED、STALE、BUDGET、SOURCE_MISSING、INDEX_FAILED、CANCELLED、INTERNAL。HTTP 400/403/409/410/422/500 对应输入/授权/冲突/到期/能力/内部失败；有用部分结果 HTTP 200＋partial，并保留 warnings、stop_reason、basis、consumed；取消可返回 cancelled。内部路径、凭据与未授权计数不出现在错误详情。正式用途遇到过期/未复核来源列缺口，不靠 allow_stale 绕过证据准入。

客户端未知字段拒绝，未知版本拒绝；缺默认配置才补齐。旧 API 不改字段语义；适配器显式转换六字段 Ref 与新 FixedRef，relation 在边/证据链接保存，不丢失。定义版本新增不批量重写旧记录；旧包按原版本可回读，当前组包需重新校验定义。保存幂等、并发、索引水位继承现有机制，抽象不要求新增数据库或服务。

## 6. 首期状态生命周期与代理边界

查询状态首期保存在工作台进程内，含原请求指纹、授权绑定、候选、固定依据、累计账本与游标；默认TTL为创建后15分钟，可由服务端配置收紧，过期/进程重启返回EXPIRED，不能恢复成零消耗的旧查询。游标为服务端不透明身份；同一query只允许一个活动操作，重复相同操作可回读原回执，冲突并发返回CONFLICT，取消可独立发出。程序活动时间计入wall_ms，用户停留时间只消耗TTL。

维护计划与审查草案保存于受控.local临时计划区，固定plan_id/digest和版本；规范提交与幂等回执仍由memory存储负责。重启后重新核验计划依据与HEAD，不能自动续写；清理临时计划不可删除规范提交和恢复回执。首期任务包导出/回填是有界人工桥：只导出获准固定材料、预期结构与预算，回填按review接口预检并记录实际审查来源；没有可验证读取回执时semantic_reviewer及reviewed_refs不能据客户端自报冒充已完成审查。自动调用模型代理是B07可选后续项，不是首期必备后台能力。
