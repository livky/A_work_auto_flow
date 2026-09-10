# 表示查询继承逐项验收

固定 Run：`RUN-20260909T194710Z-3CF36B2FDD60`。审计快照：`2026-09-09T22:48:54.859061+00:00`。

38 项均列出当前代码和真实测试 ID，并区分已绑定与尚待绑定的执行回执；没有把 43 个方法入口存在当作完整旧协议验收。具体修复 H01–H07 与 S01 已在其支持范围内闭合，旧 DTO/后端及未执行矩阵仍逐项保留。

“范围内通过”只对应本机合成材料的所列软件行为；“部分验证”表示所列子集有实际依据、原义务仍有明确剩余。表内 T 编号链接到后文真实测试与执行回执；AI 阅读/审查和单元测试分开列出。

## 完整测试与补充回归

以下为生成本文时的真实套件状态。运行中或失败不计作完整通过；单项已执行结果只作为相应断言的局部证据。

- [testing/build-attempt-02/results.json](testing/build-attempt-02/results.json)：`passed`，构建步骤回执。
- [testing/build-attempt-03/results.json](testing/build-attempt-03/results.json)：`passed`，构建步骤回执。
- [testing/full-attempt-01/results.json](testing/full-attempt-01/results.json)：`failed`，tier=`full`，selection=4。
- [testing/quick-attempt-01/results.json](testing/quick-attempt-01/results.json)：`failed`，tier=`quick`，selection=2。

最终 P3 20/20（81.543 秒），C17 夹具修正后定向 1/1（35.792 秒）；Foundation 之前两次 25 项执行各有一个测试错误，原失败保留，未重写为全通过。[补充回执](inheritance-closure-final.json)。分类 8/8、新 review 1/1、domain 撤权 1/1 与召回独立回执见对应测试。

## INH01–INH12 与 C01–C26

| 项 | 判定 | 实际已验证范围 | 测试 | 剩余限制 |
| --- | --- | --- | --- | --- |
| INH01 | 部分验证 | 固定 record 修订/字节、旧六字段 relation、无索引 claim 定位与 owner 自身指纹已有运行适配。 | [T040](#t040) [T038](#t038) [T067](#t067) | 四类旧身份全字段往返和各自 SHA 冲突矩阵未闭合；独立旧 representation ID 与 owner/claim 直接正文读取仍明确不支持。 |
| INH02 | 部分验证 | 规范 v3 可选 knowledge_facets 真实保存角色、多个尝试、逐目标 confidence、完整适用字段和固定分类依据；角色/多结果/review/validity 独立交叉，未知显式标注，空集不变不限，分类依据进入授权闭包；旧 v1/v2 固定读写不回填。 | [T063](#t063) [T092](#t092) [T073](#t073) [T035](#t035) [T036](#t036) [T032](#t032) [T037](#t037) [T031](#t031) [T033](#t033) [T034](#t034) | 旧完整 Applicability 请求 DTO 的业务时间和 subject_versions 条件尚未适配；现有请求以明确条件/排除数组精确匹配。不能把规范字段无损保存解释为旧请求全字段兼容，也不能把 confidence 当科学认可。 |
| INH03 | 部分验证 | 多表示保留各自固定身份、原分数、实际 matched_text 与真实 lexical 投影版本；RRF 不增加同通道投票；真实通道故障保留其他结果，缺水位明确降级，逐 claim 准入和最终包诊断已执行。 | [T084](#t084) [T089](#t089) [T082](#t082) [T083](#t083) [T068](#t068) [T070](#t070) [T081](#t081) | 未注册 dense/sparse 模型通道不计为实际运行；当前真实支持 identity/lexical 和既有关系导航，不伪造模型或编码版本。 |
| INH04 | 部分验证 | manifest 内容页、固定变化页、连续页计划、每 owner FTS 原子事务、故障重试和修复已有真实执行。 | [T043](#t043) [T044](#t044) [T042](#t042) [T049](#t049) | 仅 lexical/existing 和 existing_associations_only 图窄键；旧 Run/原生证据图、dense/custom encoder、筛选专用索引不支持。重建中断、无变化流 fixture、完整中间页缺口及多 owner 计划仍未专测。 |
| INH05 | 部分验证 | 两种真实融合和两种固定文本重排策略均可切换；重排不扩充候选，保留原身份和 evidence；缺文本/故障/取消如实返回。 | [T071](#t071) [T051](#t051) [T052](#t052) [T086](#t086) | 融合替换测试比较固定ID集合；重排比较原完整候选/evidence。尚未单独替换完整RankingPipeline后端；无模型提供器明确不支持。 |
| INH06 | 部分验证 | 固定查询、筛选上限、受控补充范围、续查共享账本、取消/忙锁/TTL均有入口；非 plain、未知策略、查询内修复与按秒容忍明确拒绝。 | [T075](#t075) [T062](#t062) [T015](#t015) [T021](#t021) | 完整旧 QuerySpec/Resume DTO 不是原样兼容接口；旧 context 序列、audit 独立用途、planner/capability 下推及双扩展轴需完整适配验收。旧 additional_budget 明确被设计替换为新查询。 |
| INH07 | 部分验证 | 固定历史游标在 HEAD 前进后不漂移；固定文稿/字段组合只读；A09 新文稿经正式提交并读回新旧版本。 | [T041](#t041) [T054](#t054) [T077](#t077) | 独立旧 ReadView(view/text/graph/omitted) 全结构兼容和所有视图不写规范修订的组合断言未闭合；A09 是实际 AI 阅读/维护，不能替代全视图协议测试。 |
| INH08 | 部分验证 | 真实 CAS/幂等/固定 changes、逐 owner 提交待办、重启只读 status、恢复新修订、撤回 review 已测；变化后旧 review 不再准入，新适用 review 绑定新 claim/输入，正式投影恢复且旧 review 原样保留。 | [T055](#t055) [T057](#t057) [T060](#t060) [T058](#t058) [T053](#t053) [T090](#t090) | 正向 C24 集成使用公开 memory review 与实际 Evidence.project；旧 ReviewCommand/CommitReceipt 的所有字段 DTO 桥接仍需按原后端逐项验收。A09 本身没有应撤回的已复核 claim。 |
| INH09 | 部分验证 | 12维账本/预约结算及并发已测；模型输入、输出、调用数、总tokens各自先耗尽和零额度四种边界分别执行；能力明确model_providers/tokenizers为空。 | [T006](#t006) [T007](#t007) [T005](#t005) [T008](#t008) [T004](#t004) [T010](#t010) [T009](#t009) | 模型/分词策略未注册，当前只有可计量硬资源边界；不宣称真实tokenizer、模型调用或任意编码器费用已验收。 |
| INH10 | 部分验证 | Issue(code/message/affected_refs/retry)与Basis(basis_id/observed_at)已补；重试类别/隐藏引用、稳定观察身份和真实missing材料包Issue已有直接执行。 | [T096](#t096) [T097](#t097) [T069](#t069) [T043](#t043) | 旧Outcome逐类/逐阶段无损转换仍需按具体原后端核验；当前warnings兼容保留，affected_refs仅使用已观察固定对象。早期A07预算stop_reason为空为历史回执事实。 |
| INH11 | 部分验证 | 旧 references/input/same_entity/mentions 与同端点平行边保留原关系/证据关系；同名固定实体不合并。显式差异随获准路径返回；规范拒绝后缓存 stale，新查询仅返回有权诊断边，拒绝/旧边不能成为桥；ceiling/排除不泄露桥节点。 | [T016](#t016) [T018](#t018) [T022](#t022) [T047](#t047) [T012](#t012) [T013](#t013) [T048](#t048) | 路径服务提供有界最短固定链，没有承诺或实现全部替代路径枚举；显式用户/AI 判错作为合成输入测试，导航认可不等于科学有效。未注册规范关系只报告缺口。 |
| INH12 | 部分验证 | 六类型及已有字段组合、missing/reject/skip/fallback/stale已测；纯foundation/definition-resolve按0.1与目标定义1显式映射旧topic_synthesis/domain_synthesis并实际用于查询。 | [T045](#t045) [T069](#t069) [T054](#t054) [T002](#t002) [T023](#t023) | 多项 fallback 次序尚未专测；旧 topic_synthesis/domain_synthesis 通过显式版本映射可实际查询。领域多贡献来源撤权已有专测；新解释由外部 AI 维护草案→review→apply 取得新修订，自动 builder 只组合既有字段。 |
| C01 | 部分验证 | r1 固定修订、缺 SHA 补齐、relation 保留和固定正文 r1 字节已有直接断言。 | [T040](#t040) [T054](#t054) [T067](#t067) [T024](#t024) | 四类旧 kind 全字段往返与 record/file/owner 各自 SHA 失配未完全覆盖；独立旧表示 ID、owner 正文不支持。 |
| C02 | 部分验证 | owner 空集返回空；包含与排除同 ref 时排除优先；来源 owner/ref/id 排除先于依赖正文。 | [T063](#t063) [T065](#t065) [T092](#t092) [T093](#t093) | 查询 owner_ids=null 对照、每个筛选维度 null/[] 和显式 include 与来源排除的全部组合未专测。 |
| C03 | 部分验证 | 规范 v3 可选 knowledge_facets 真实保存角色、多个尝试、逐目标 confidence、完整适用字段和固定分类依据；角色/多结果/review/validity 独立交叉，未知显式标注，空集不变不限，分类依据进入授权闭包；旧 v1/v2 固定读写不回填。 | [T073](#t073) [T030](#t030) [T029](#t029) [T035](#t035) [T036](#t036) [T032](#t032) [T037](#t037) [T031](#t031) [T033](#t033) [T034](#t034) | 旧完整 Applicability 请求 DTO 的业务时间和 subject_versions 条件尚未适配；现有请求以明确条件/排除数组精确匹配。不能把规范字段无损保存解释为旧请求全字段兼容，也不能把 confidence 当科学认可。 |
| C04 | 范围内通过 | 两个 claim 仅一项获准时，正式投影/最终包不含另一项；精确未复核 claim 不借用同篇认可。 | [T026](#t026) [T027](#t027) [T068](#t068) | 通过范围为真实 memory-v3 合成事件/claim；不连带证明旧 EvidenceAssessment 全字段及所有历史 kind。 |
| C05 | 范围内通过 | 公开提交的两种可检索表示归为同一规范候选；原BM25不同分数与各表示固定ID/SHA保留；两个表示仍只投一份词法RRF票。 | [T084](#t084) [T039](#t039) | 已测真实两表示与身份通道；原关键词卡/摘要/全文三种存储槽完整历史组合不是本夹具；模型通道未运行。 |
| C06 | 部分验证 | 缺摘要为 needs_generation；reject 不给替代正文、skip 省略；显式 full fallback 生效。 | [T069](#t069) [T072](#t072) | 多项 fallback 顺序、未知 fallback 拒绝及各类型 generation 边界未全测；未登记 definition/version 明确 UNSUPPORTED。 |
| C07 | 范围内通过 | 真实 domain map 同时引用 A/B 两 owner 的原件和必要单元；query→select→assemble 正常纳入双贡献。撤销 B 原件后首次/缓存组包都拒绝，B 单元正文与 B 原件打开次数均为零，且不泄露 B 正文。 | [T093](#t093) [T092](#t092) [T074](#t074) [T023](#t023) | 本机公开规范提交与来源登记的合成 domain 夹具；不代表真实业务综合质量，未覆盖任意模型生成内容。 |
| C08 | 部分验证 | 已有字段build canonical=false且HEAD不变；新解释走实际AI的maintenance-plan→draft_json→review（保存不可变草案计划）→apply（规范r2）→固定读回。 | [T054](#t054) [T059](#t059) [T056](#t056) | A09实际路径适用于已有内容的外部AI修订/重新综合；Foundation自动builder仍content_proposals=[]。保留未实现的自动生成分支，不以UNSUPPORTED冒充这一路径通过。 |
| C09 | 范围内通过 | 内容已提交而 FTS 事务故障时回滚索引；原计划重试及重复成功不产生第二内容修订，保留向量水位。 | [T043](#t043) | 仅 lexical/existing 单 owner 原事务；dense/custom encoder 和跨 owner 全局原子性不支持。 |
| C10 | 部分验证 | 索引丢失后由 manifest 全量内容页重建，纳入所有枚举记录，规范 HEAD 不变。 | [T042](#t042) [T046](#t046) | 真正无历史变化流 fixture、rebuild 中断时完整水位不发布未专测；incremental 故障不能替代此断言。 |
| C11 | 部分验证 | 拒绝只有首个未完页、漏首个页、错误页类型；同计划失败重试与成功重放已测。 | [T044](#t044) [T043](#t043) | 缺完整多页的中间缺口、顺序倒置、重复事件和多 owner 部分完成；跨查询持久索引计划未证明支持。 |
| C12 | 范围内通过 | current 对真实HEAD超前和owner水位行丢失均明确降级；缺水位不再因FTS仍存在而伪装完整。 | [T064](#t064) [T083](#t083) [T075](#t075) | 查询内修复及按秒容忍仍是明确UNSUPPORTED；内容/索引整体状态依实际FixedRef与水位判断。 |
| C13 | 范围内通过 | result_limit=1 的真实正文探针只观察首个规范候选；resume再读下一项并累计候选/字节/输出成本；零字节预算阻止正文。 | [T080](#t080) [T076](#t076) [T028](#t028) | 通过为本机词法/身份提供器的小型真实F1；未注册向量不计通过，万条/全库规模性能及第二台物理机另行验收。 |
| C14 | 范围内通过 | SQLite/OSError 词法故障保留已完成 identity，词法迭代故障保留前缀；同一真实故障后的 assemble 保留 lexical warning、partial 和 complete=false。 | [T089](#t089) [T082](#t082) [T070](#t070) | 未注册向量通道的实际故障不在本次可执行范围；可插拔故障隔离不是向量模型质量证明。 |
| C15 | 部分验证 | topic-evidence-v2 与 rrf 切换保留固定 ID 集；term-overlap 与 exact-phrase 重排保留候选/evidence/成本边界。 | [T071](#t071) [T051](#t051) | 融合替换测试只直接比較固定ID集合，候选/evidence保真由固定文本重排与多表示诊断回归分开验证；只限已登记确定性策略。 |
| C16 | 部分验证 | 实际第一候选被排除时，在剩余候选预算中补入下一项后才返回K；正式逐claim准入发生在K之前。 | [T086](#t086) [T068](#t068) | 现直接补召回测试用排除反例；正式复核准入与增量K为同实现顺序，但未单独构造前K全无效、后K有效的组合夹具。 |
| C17 | 部分验证 | 旧 references/input/same_entity/mentions 与同端点平行边保留原关系/证据关系；同名固定实体不合并。显式差异随获准路径返回；规范拒绝后缓存 stale，新查询仅返回有权诊断边，拒绝/旧边不能成为桥；ceiling/排除不泄露桥节点。 | [T016](#t016) [T018](#t018) [T022](#t022) [T047](#t047) [T020](#t020) [T048](#t048) | 路径服务提供有界最短固定链，没有承诺或实现全部替代路径枚举；显式用户/AI 判错作为合成输入测试，导航认可不等于科学有效。未注册规范关系只报告缺口。 |
| C18 | 范围内通过 | accept_navigation 调用真实 decide_association；claim_states 前后相等，重复请求幂等且冲突拒绝。 | [T013](#t013) | 通过范围为既有固定关联；不证明生成模型发现质量或科学有效性。 |
| C19 | 部分验证 | 显式 supplement_scope 受 ceiling/排除控制；深化沿用查询范围，隐藏节点不能成为桥或进入 basis。 | [T015](#t015) [T014](#t014) [T011](#t011) | 一般语料扩大轴、表示加深独立选择及原 role/outcome 硬筛选全组合未专测；主筛选变更要求新查询。 |
| C20 | 部分验证 | 循环/菱形共享唯一节点/边额度；新种子不归零累计 hop；撤权旧游标拒绝；忙操作不计费；预约/结算幂等。 | [T012](#t012) [T017](#t017) [T019](#t019) [T062](#t062) [T087](#t087) [T088](#t088) [T079](#t079) [T078](#t078) [T085](#t085) | 旧 additional_budget 按明确替换 S03 不支持同查询增加；改为新 query/账本。没有把全部旧 resume DTO 兼容或持久重启游标计作通过。 |
| C21 | 部分验证 | 重排取消保留一个已完成分数和真实 rerank_items，释放余量；取消后结算、预算实际消耗不归零已测。 | [T050](#t050) [T003](#t003) [T095](#t095) | 尚未覆盖每个搜索/组包阶段停止时已完成部分和结构化位置；A07 预算包 stop_reason=null，必须结合 warnings/gaps/complete。 |
| C22 | 范围内通过 | 方法块需要的定义实际补齐；定义被 primary scope 排除则 complete=false，合法两层范围允许则包含；小预算不截碎完整块。 | [T094](#t094) [T091](#t091) [T066](#t066) | 通过范围为现有完整块/定义和 A07 合成文本；不证明任意公式解析或自动语义生成正确性。 |
| C23 | 部分验证 | 固定表示 read/build 不写 HEAD；固定双文稿读取保留旧 bytes；A09 新解释和新文稿经显式 commit。 | [T054](#t054) [T077](#t077) | 独立 graph render 与所有旧 ReadView 结构组合的无规范写入断言未完整执行；A09 连续 AI 上下文不是盲测。 |
| C24 | 范围内通过 | 真实 claim 修订后旧 accepted review 保留历史但不准入；公开追加新 accepted review 绑定新 SHA/content hash/固定 inputs/适用域，Evidence.project 只正式呈现新 claim。错 owner/域/旧 hash/空 inputs 拒绝，旧 review 与旧记录固定读回不变。 | [T030](#t030) [T025](#t025) [T058](#t058) [T090](#t090) | 验收的是适用授权流程和软件证据门控，不代表现实结论已获人工或科学复核；A09 单独记录，不作为这项正向集成的替代证据。 |
| C25 | 范围内通过 | 跨 owner 首项真提交后故障列明已完成和 pending，仅重试未完成；恢复创建新修订并拒绝覆盖后来的修订。 | [T057](#t057) [T061](#t061) [T053](#t053) | 通过为本机隔离 fixture 的顺序多 owner 事务与显式恢复；不支持跨 owner 全局原子提交，也未完成真实业务人工验收。 |
| C26 | 部分验证 | 严格 DTO 拒未知字段，未登记修复/容忍/排序明确拒绝；两个融合/重排可保持调用结构与固定 ID。 | [T075](#t075) [T071](#t071) [T051](#t051) [T001](#t001) | 读取/索引/召回/存储每类替换两种真实后端未执行；H01–H07 的本次具体问题已补受限实现或明示能力边界，仍不能以 43 方法映射关闭完整旧协议和未注册后端义务。 |

## 修复前问题与当前处置

| 编号 | 原问题 | 当前处置 |
| --- | --- | --- |
| H01 | 旧 attempts/confidence 与独立分类筛选缺映射 | 规范可选 knowledge_facets、公开提交与逐 claim 交叉筛选；完整旧适用请求 DTO 仍保留限制。 |
| H02 | 多表示命中被折叠、原分数/片段不足 | 保留各表示固定身份、原 BM25、matched_text/投影版本；RRF 每通道单票。 |
| H03 | 小 result_limit 先读取大量候选 | 按候选准入和最终 K 增量读取，resume 共用账本与固定身份。 |
| H04 | 真实通道故障丢失已完成部分 | SQLite/OSError 与迭代失败保留已完成结果，诊断贯穿 assemble。 |
| H05 | 结构化 Issue/Basis 字段缺失 | 补 code/message/affected_refs/retry 与稳定 basis_id/observed_at；不宣称所有旧 Outcome 无损桥接。 |
| H06 | 旧关系被改名/遗漏及错误连接信息不足 | 注册旧关系并保留平行边；未知关系报缺口；差异/拒绝诊断受权限约束且不导航。 |
| H07 | 四项模型预算边界缺直接验收 | 输入/输出/调用/总 tokens 分别先耗尽及零额度已测；model_providers/tokenizers 明确为空。 |
| S01 | owner 水位行缺失可伪装 current | 水位缺失即 partial，FTS 行存在也不等价于完整。 |

修复前逐项原始判定保存在机器回执的 `original_audit_snapshot`，现行表不会抹去原缺口。`inheritance-map.json` 仅增加独立 `execution_audit`，保留原设计覆盖与验收状态。

## 真实测试与来源

共 97 个唯一测试 ID；97 个绑定过实际通过回执。源码行号与指纹是当前快照，历史执行指纹未知时留空。

### T001

`test_material_api.MaterialApiTests.test_capabilities_definitions_and_unknown_control_fields` — 有真实通过记录。源码：[第 32 行](../../../../automation/tests/test_material_api.py#L32)。
执行依据：[testing/full-attempt-01/01-python.json](testing/full-attempt-01/01-python.json)；[testing/quick-attempt-01/01-python.json](testing/quick-attempt-01/01-python.json)

### T002

`test_material_api.MaterialApiTests.test_realization_inspection_reports_changed_original_as_stale` — 有真实通过记录。源码：[第 102 行](../../../../automation/tests/test_material_api.py#L102)。
执行依据：[testing/full-attempt-01/01-python.json](testing/full-attempt-01/01-python.json)；[testing/quick-attempt-01/01-python.json](testing/quick-attempt-01/01-python.json)

### T003

`test_material_budget.MaterialBudgetReservationTests.test_cancelled_provider_can_still_settle_actual_cost` — 有真实通过记录。源码：[第 155 行](../../../../automation/tests/test_material_budget.py#L155)。
执行依据：[inheritance-closure-foundation-budget.json](inheritance-closure-foundation-budget.json)；[testing/full-attempt-01/01-python.json](testing/full-attempt-01/01-python.json)；[testing/quick-attempt-01/01-python.json](testing/quick-attempt-01/01-python.json)

### T004

`test_material_budget.MaterialBudgetReservationTests.test_competing_providers_cannot_reserve_same_remaining_capacity` — 有真实通过记录。源码：[第 67 行](../../../../automation/tests/test_material_budget.py#L67)。
执行依据：[inheritance-closure-foundation-budget.json](inheritance-closure-foundation-budget.json)；[testing/full-attempt-01/01-python.json](testing/full-attempt-01/01-python.json)；[testing/quick-attempt-01/01-python.json](testing/quick-attempt-01/01-python.json)

### T005

`test_material_budget.MaterialBudgetReservationTests.test_model_call_limit_can_exhaust_before_input_output_and_total` — 有真实通过记录。源码：[第 61 行](../../../../automation/tests/test_material_budget.py#L61)。
执行依据：[inheritance-closure-foundation-budget.json](inheritance-closure-foundation-budget.json)；[testing/full-attempt-01/01-python.json](testing/full-attempt-01/01-python.json)

### T006

`test_material_budget.MaterialBudgetReservationTests.test_model_input_limit_can_exhaust_before_output_calls_and_total` — 有真实通过记录。源码：[第 55 行](../../../../automation/tests/test_material_budget.py#L55)。
执行依据：[inheritance-closure-foundation-budget.json](inheritance-closure-foundation-budget.json)；[testing/full-attempt-01/01-python.json](testing/full-attempt-01/01-python.json)

### T007

`test_material_budget.MaterialBudgetReservationTests.test_model_output_limit_can_exhaust_before_input_calls_and_total` — 有真实通过记录。源码：[第 58 行](../../../../automation/tests/test_material_budget.py#L58)。
执行依据：[inheritance-closure-foundation-budget.json](inheritance-closure-foundation-budget.json)；[testing/full-attempt-01/01-python.json](testing/full-attempt-01/01-python.json)

### T008

`test_material_budget.MaterialBudgetReservationTests.test_model_total_limit_can_exhaust_before_input_output_and_calls` — 有真实通过记录。源码：[第 64 行](../../../../automation/tests/test_material_budget.py#L64)。
执行依据：[inheritance-closure-foundation-budget.json](inheritance-closure-foundation-budget.json)；[testing/full-attempt-01/01-python.json](testing/full-attempt-01/01-python.json)

### T009

`test_material_budget.MaterialBudgetReservationTests.test_parallel_provider_wall_cost_is_one_observed_active_interval` — 有真实通过记录。源码：[第 167 行](../../../../automation/tests/test_material_budget.py#L167)。
执行依据：[inheritance-closure-foundation-budget.json](inheritance-closure-foundation-budget.json)；[testing/full-attempt-01/01-python.json](testing/full-attempt-01/01-python.json)；[testing/quick-attempt-01/01-python.json](testing/quick-attempt-01/01-python.json)

### T010

`test_material_budget.MaterialBudgetReservationTests.test_parent_settlement_does_not_repeat_child_charges` — 有真实通过记录。源码：[第 94 行](../../../../automation/tests/test_material_budget.py#L94)。
执行依据：[inheritance-closure-foundation-budget.json](inheritance-closure-foundation-budget.json)；[testing/full-attempt-01/01-python.json](testing/full-attempt-01/01-python.json)；[testing/quick-attempt-01/01-python.json](testing/quick-attempt-01/01-python.json)

### T011

`test_material_deepening.MaterialDeepeningTests.test_ceiling_filters_graph_content_and_basis` — 有真实通过记录。源码：[第 192 行](../../../../automation/tests/test_material_deepening.py#L192)。
执行依据：[inheritance-closure-p3.json](inheritance-closure-p3.json)；[inheritance-closure-final.json](inheritance-closure-final.json)；[testing/full-attempt-01/01-python.json](testing/full-attempt-01/01-python.json)；[testing/quick-attempt-01/01-python.json](testing/quick-attempt-01/01-python.json)

### T012

`test_material_deepening.MaterialDeepeningTests.test_cycles_diamonds_and_cursor_share_unique_budget` — 有真实通过记录。源码：[第 211 行](../../../../automation/tests/test_material_deepening.py#L211)。
执行依据：[inheritance-closure-p3.json](inheritance-closure-p3.json)；[inheritance-closure-final.json](inheritance-closure-final.json)；[testing/full-attempt-01/01-python.json](testing/full-attempt-01/01-python.json)；[testing/quick-attempt-01/01-python.json](testing/quick-attempt-01/01-python.json)

### T013

`test_material_deepening.MaterialDeepeningTests.test_decision_retries_are_idempotent_and_never_promote_review` — 有真实通过记录。源码：[第 268 行](../../../../automation/tests/test_material_deepening.py#L268)。
执行依据：[inheritance-closure-p3.json](inheritance-closure-p3.json)；[inheritance-closure-final.json](inheritance-closure-final.json)；[testing/full-attempt-01/01-python.json](testing/full-attempt-01/01-python.json)；[testing/quick-attempt-01/01-python.json](testing/quick-attempt-01/01-python.json)

### T014

`test_material_deepening.MaterialDeepeningTests.test_excluded_node_is_not_a_bridge_or_a_basis_entry` — 有真实通过记录。源码：[第 181 行](../../../../automation/tests/test_material_deepening.py#L181)。
执行依据：[inheritance-closure-p3.json](inheritance-closure-p3.json)；[inheritance-closure-final.json](inheritance-closure-final.json)；[testing/full-attempt-01/01-python.json](testing/full-attempt-01/01-python.json)；[testing/quick-attempt-01/01-python.json](testing/quick-attempt-01/01-python.json)

### T015

`test_material_deepening.MaterialDeepeningTests.test_existing_association_uses_explicit_supplement_scope_and_ceiling` — 有真实通过记录。源码：[第 161 行](../../../../automation/tests/test_material_deepening.py#L161)。
执行依据：[inheritance-closure-p3.json](inheritance-closure-p3.json)；[inheritance-closure-final.json](inheritance-closure-final.json)；[testing/full-attempt-01/01-python.json](testing/full-attempt-01/01-python.json)；[testing/quick-attempt-01/01-python.json](testing/quick-attempt-01/01-python.json)

### T016

`test_material_deepening.MaterialDeepeningTests.test_legacy_relations_keep_parallel_edges_and_explicit_evidence_links` — 有真实通过记录。源码：[第 104 行](../../../../automation/tests/test_material_deepening.py#L104)。
执行依据：[inheritance-closure-p3.json](inheritance-closure-p3.json)；[inheritance-closure-final.json](inheritance-closure-final.json)；[testing/full-attempt-01/01-python.json](testing/full-attempt-01/01-python.json)

### T017

`test_material_deepening.MaterialDeepeningTests.test_new_seed_does_not_reset_cumulative_hop_boundary` — 有真实通过记录。源码：[第 237 行](../../../../automation/tests/test_material_deepening.py#L237)。
执行依据：[inheritance-closure-p3.json](inheritance-closure-p3.json)；[inheritance-closure-final.json](inheritance-closure-final.json)；[testing/full-attempt-01/01-python.json](testing/full-attempt-01/01-python.json)；[testing/quick-attempt-01/01-python.json](testing/quick-attempt-01/01-python.json)

### T018

`test_material_deepening.MaterialDeepeningTests.test_same_title_fixed_entities_are_not_merged_by_navigation` — 有真实通过记录。源码：[第 128 行](../../../../automation/tests/test_material_deepening.py#L128)。
执行依据：[inheritance-closure-p3.json](inheritance-closure-p3.json)；[inheritance-closure-final.json](inheritance-closure-final.json)；[testing/full-attempt-01/01-python.json](testing/full-attempt-01/01-python.json)

### T019

`test_material_deepening.MaterialDeepeningTests.test_source_revocation_blocks_cached_cursor_and_hidden_details` — 有真实通过记录。源码：[第 257 行](../../../../automation/tests/test_material_deepening.py#L257)。
执行依据：[inheritance-closure-p3.json](inheritance-closure-p3.json)；[inheritance-closure-final.json](inheritance-closure-final.json)；[testing/full-attempt-01/01-python.json](testing/full-attempt-01/01-python.json)；[testing/quick-attempt-01/01-python.json](testing/quick-attempt-01/01-python.json)

### T020

`test_material_deepening.MaterialDeepeningTests.test_stale_existing_edge_is_gap_and_not_reused` — 有真实通过记录。源码：[第 173 行](../../../../automation/tests/test_material_deepening.py#L173)。
执行依据：[inheritance-closure-p3.json](inheritance-closure-p3.json)；[inheritance-closure-final.json](inheritance-closure-final.json)；[testing/full-attempt-01/01-python.json](testing/full-attempt-01/01-python.json)；[testing/quick-attempt-01/01-python.json](testing/quick-attempt-01/01-python.json)

### T021

`test_material_deepening.MaterialDeepeningTests.test_unknown_strategy_and_foreign_cursor_are_rejected` — 有真实通过记录。源码：[第 334 行](../../../../automation/tests/test_material_deepening.py#L334)。
执行依据：[inheritance-closure-p3.json](inheritance-closure-p3.json)；[inheritance-closure-final.json](inheritance-closure-final.json)；[testing/full-attempt-01/01-python.json](testing/full-attempt-01/01-python.json)；[testing/quick-attempt-01/01-python.json](testing/quick-attempt-01/01-python.json)

### T022

`test_material_deepening.MaterialDeepeningTests.test_unmapped_canonical_relation_is_a_gap_not_an_invented_dependency` — 有真实通过记录。源码：[第 145 行](../../../../automation/tests/test_material_deepening.py#L145)。
执行依据：[inheritance-closure-p3.json](inheritance-closure-p3.json)；[inheritance-closure-final.json](inheritance-closure-final.json)；[testing/full-attempt-01/01-python.json](testing/full-attempt-01/01-python.json)

### T023

`test_material_domain_scope.MaterialDomainScopeTests.test_domain_two_owner_sources_are_rechecked_before_revoked_body_reads` — 有真实通过记录。源码：[第 58 行](../../../../automation/tests/test_material_domain_scope.py#L58)。
执行依据：[testing/full-attempt-01/01-python.json](testing/full-attempt-01/01-python.json)；[material-domain-scope-tests.txt](material-domain-scope-tests.txt)

### T024

`test_material_evidence.MaterialEvidenceTests.test_bad_fixed_claim_hash_and_legacy_owner_are_explicitly_rejected` — 有真实通过记录。源码：[第 116 行](../../../../automation/tests/test_material_evidence.py#L116)。
执行依据：[testing/full-attempt-01/01-python.json](testing/full-attempt-01/01-python.json)；[testing/quick-attempt-01/01-python.json](testing/quick-attempt-01/01-python.json)

### T025

`test_material_evidence.MaterialEvidenceTests.test_historical_claim_hash_resolves_without_revalidating_changed_claim` — 有真实通过记录。源码：[第 74 行](../../../../automation/tests/test_material_evidence.py#L74)。
执行依据：[testing/full-attempt-01/01-python.json](testing/full-attempt-01/01-python.json)；[testing/quick-attempt-01/01-python.json](testing/quick-attempt-01/01-python.json)

### T026

`test_material_evidence.MaterialEvidenceTests.test_only_one_of_two_claims_is_effectively_accepted` — 有真实通过记录。源码：[第 44 行](../../../../automation/tests/test_material_evidence.py#L44)。
执行依据：[testing/full-attempt-01/01-python.json](testing/full-attempt-01/01-python.json)；[testing/quick-attempt-01/01-python.json](testing/quick-attempt-01/01-python.json)

### T027

`test_material_evidence.MaterialEvidenceTests.test_project_returns_only_accepted_statement_and_exact_claim_selection` — 有真实通过记录。源码：[第 99 行](../../../../automation/tests/test_material_evidence.py#L99)。
执行依据：[testing/full-attempt-01/01-python.json](testing/full-attempt-01/01-python.json)；[testing/quick-attempt-01/01-python.json](testing/quick-attempt-01/01-python.json)

### T028

`test_material_evidence.MaterialEvidenceTests.test_read_budget_zero_exact_and_one_less_than_measured_source_closure` — 有真实通过记录。源码：[第 164 行](../../../../automation/tests/test_material_evidence.py#L164)。
执行依据：[testing/full-attempt-01/01-python.json](testing/full-attempt-01/01-python.json)；[testing/quick-attempt-01/01-python.json](testing/quick-attempt-01/01-python.json)

### T029

`test_material_evidence.MaterialEvidenceTests.test_retracted_and_superseded_reviews_remain_ineligible` — 有真实通过记录。源码：[第 67 行](../../../../automation/tests/test_material_evidence.py#L67)。
执行依据：[testing/full-attempt-01/01-python.json](testing/full-attempt-01/01-python.json)；[testing/quick-attempt-01/01-python.json](testing/quick-attempt-01/01-python.json)

### T030

`test_material_evidence.MaterialEvidenceTests.test_wrong_scope_changed_content_and_old_revision_are_ineligible` — 有真实通过记录。源码：[第 55 行](../../../../automation/tests/test_material_evidence.py#L55)。
执行依据：[testing/full-attempt-01/01-python.json](testing/full-attempt-01/01-python.json)；[testing/quick-attempt-01/01-python.json](testing/quick-attempt-01/01-python.json)

### T031

`test_material_facets.MaterialFacetTests.test_applicability_uses_exact_structured_conditions_and_exclusions` — 有真实通过记录。源码：[第 153 行](../../../../automation/tests/test_material_facets.py#L153)。
执行依据：[facets-acceptance.json](facets-acceptance.json)；[testing/full-attempt-01/01-python.json](testing/full-attempt-01/01-python.json)；[testing/facets-final-20260910.log](testing/facets-final-20260910.log)

### T032

`test_material_facets.MaterialFacetTests.test_confidence_targets_exact_claim_and_never_promotes_review` — 有真实通过记录。源码：[第 116 行](../../../../automation/tests/test_material_facets.py#L116)。
执行依据：[facets-acceptance.json](facets-acceptance.json)；[testing/full-attempt-01/01-python.json](testing/full-attempt-01/01-python.json)；[testing/facets-final-20260910.log](testing/facets-final-20260910.log)

### T033

`test_material_facets.MaterialFacetTests.test_facet_basis_is_in_real_source_permission_and_revocation_closure` — 有真实通过记录。源码：[第 161 行](../../../../automation/tests/test_material_facets.py#L161)。
执行依据：[facets-acceptance.json](facets-acceptance.json)；[testing/full-attempt-01/01-python.json](testing/full-attempt-01/01-python.json)；[testing/facets-final-20260910.log](testing/facets-final-20260910.log)

### T034

`test_material_facets.MaterialFacetTests.test_legacy_v1_v2_save_and_fixed_read_need_no_backfill_or_new_field` — 有真实通过记录。源码：[第 206 行](../../../../automation/tests/test_material_facets.py#L206)。
执行依据：[facets-acceptance.json](facets-acceptance.json)；[testing/full-attempt-01/01-python.json](testing/full-attempt-01/01-python.json)；[testing/facets-final-20260910.log](testing/facets-final-20260910.log)

### T035

`test_material_facets.MaterialFacetTests.test_public_roundtrip_preserves_multiple_attempts_confidence_and_old_revision` — 有真实通过记录。源码：[第 94 行](../../../../automation/tests/test_material_facets.py#L94)。
执行依据：[facets-acceptance.json](facets-acceptance.json)；[testing/full-attempt-01/01-python.json](testing/full-attempt-01/01-python.json)；[testing/facets-final-20260910.log](testing/facets-final-20260910.log)

### T036

`test_material_facets.MaterialFacetTests.test_role_multiple_outcomes_review_and_validity_intersect_independently` — 有真实通过记录。源码：[第 104 行](../../../../automation/tests/test_material_facets.py#L104)。
执行依据：[facets-acceptance.json](facets-acceptance.json)；[testing/full-attempt-01/01-python.json](testing/full-attempt-01/01-python.json)；[testing/facets-final-20260910.log](testing/facets-final-20260910.log)

### T037

`test_material_facets.MaterialFacetTests.test_unknown_is_explicit_and_empty_filters_never_become_unrestricted` — 有真实通过记录。源码：[第 130 行](../../../../automation/tests/test_material_facets.py#L130)。
执行依据：[facets-acceptance.json](facets-acceptance.json)；[testing/full-attempt-01/01-python.json](testing/full-attempt-01/01-python.json)；[testing/facets-final-20260910.log](testing/facets-final-20260910.log)

### T038

`test_material_foundation.MaterialFoundationTests.test_claim_resolver_uses_canonical_container_after_index_loss` — 有真实通过记录。源码：[第 236 行](../../../../automation/tests/test_material_foundation.py#L236)。
执行依据：[inheritance-closure-foundation-budget.json](inheritance-closure-foundation-budget.json)；[testing/full-attempt-01/01-python.json](testing/full-attempt-01/01-python.json)；[testing/quick-attempt-01/01-python.json](testing/quick-attempt-01/01-python.json)

### T039

`test_material_foundation.MaterialFoundationTests.test_dedup_and_selection_keep_original_evidence_status` — 有真实通过记录。源码：[第 518 行](../../../../automation/tests/test_material_foundation.py#L518)。
执行依据：[inheritance-closure-foundation-budget.json](inheritance-closure-foundation-budget.json)；[testing/full-attempt-01/01-python.json](testing/full-attempt-01/01-python.json)；[testing/quick-attempt-01/01-python.json](testing/quick-attempt-01/01-python.json)

### T040

`test_material_foundation.MaterialFoundationTests.test_describe_and_resolve_keep_fixed_revision_and_relation` — 有真实通过记录。源码：[第 214 行](../../../../automation/tests/test_material_foundation.py#L214)。
执行依据：[inheritance-closure-foundation-budget.json](inheritance-closure-foundation-budget.json)；[testing/full-attempt-01/01-python.json](testing/full-attempt-01/01-python.json)；[testing/quick-attempt-01/01-python.json](testing/quick-attempt-01/01-python.json)

### T041

`test_material_foundation.MaterialFoundationTests.test_fixed_history_cursor_does_not_shift_when_head_advances` — 有真实通过记录。源码：[第 281 行](../../../../automation/tests/test_material_foundation.py#L281)。
执行依据：[inheritance-closure-foundation-budget.json](inheritance-closure-foundation-budget.json)；[testing/full-attempt-01/01-python.json](testing/full-attempt-01/01-python.json)；[testing/quick-attempt-01/01-python.json](testing/quick-attempt-01/01-python.json)

### T042

`test_material_foundation.MaterialFoundationTests.test_full_rebuild_uses_manifest_contents_after_index_loss` — 有真实通过记录。源码：[第 394 行](../../../../automation/tests/test_material_foundation.py#L394)。
执行依据：[inheritance-closure-foundation-budget.json](inheritance-closure-foundation-budget.json)；[testing/full-attempt-01/01-python.json](testing/full-attempt-01/01-python.json)；[testing/quick-attempt-01/01-python.json](testing/quick-attempt-01/01-python.json)

### T043

`test_material_foundation.MaterialFoundationTests.test_index_failure_retries_plan_without_second_content_commit` — 有真实通过记录。源码：[第 359 行](../../../../automation/tests/test_material_foundation.py#L359)。
执行依据：[inheritance-closure-foundation-budget.json](inheritance-closure-foundation-budget.json)；[testing/full-attempt-01/01-python.json](testing/full-attempt-01/01-python.json)；[testing/quick-attempt-01/01-python.json](testing/quick-attempt-01/01-python.json)

### T044

`test_material_foundation.MaterialFoundationTests.test_index_plan_requires_contiguous_complete_input_pages` — 有真实通过记录。源码：[第 349 行](../../../../automation/tests/test_material_foundation.py#L349)。
执行依据：[inheritance-closure-foundation-budget.json](inheritance-closure-foundation-budget.json)；[testing/full-attempt-01/01-python.json](testing/full-attempt-01/01-python.json)；[testing/quick-attempt-01/01-python.json](testing/quick-attempt-01/01-python.json)

### T045

`test_material_foundation.MaterialFoundationTests.test_legacy_definition_aliases_are_versioned_pure_and_usable_by_query` — 有真实通过记录。源码：[第 100 行](../../../../automation/tests/test_material_foundation.py#L100)。
执行依据：[inheritance-closure-foundation-budget.json](inheritance-closure-foundation-budget.json)；[testing/full-attempt-01/01-python.json](testing/full-attempt-01/01-python.json)

### T046

`test_material_foundation.MaterialFoundationTests.test_manifest_content_page_survives_missing_search_index` — 有真实通过记录。源码：[第 226 行](../../../../automation/tests/test_material_foundation.py#L226)。
执行依据：[inheritance-closure-foundation-budget.json](inheritance-closure-foundation-budget.json)；[testing/full-attempt-01/01-python.json](testing/full-attempt-01/01-python.json)；[testing/quick-attempt-01/01-python.json](testing/quick-attempt-01/01-python.json)

### T047

`test_material_foundation.MaterialFoundationTests.test_paths_are_ordered_fixed_and_target_constrained` — 有真实通过记录。源码：[第 433 行](../../../../automation/tests/test_material_foundation.py#L433)。
执行依据：[inheritance-closure-foundation-budget.json](inheritance-closure-foundation-budget.json)；[testing/full-attempt-01/01-python.json](testing/full-attempt-01/01-python.json)；[testing/quick-attempt-01/01-python.json](testing/quick-attempt-01/01-python.json)

### T048

`test_material_foundation.MaterialFoundationTests.test_rejected_wrong_connection_preserves_differences_without_becoming_a_path` — 有真实通过记录。源码：[第 449 行](../../../../automation/tests/test_material_foundation.py#L449)。
执行依据：[inheritance-closure-final.json](inheritance-closure-final.json)；[testing/full-attempt-01/01-python.json](testing/full-attempt-01/01-python.json)

### T049

`test_material_foundation.MaterialFoundationTests.test_repair_rebuild_replace_corrupt_fts_text_without_content_write` — 有真实通过记录。源码：[第 409 行](../../../../automation/tests/test_material_foundation.py#L409)。
执行依据：[inheritance-closure-foundation-budget.json](inheritance-closure-foundation-budget.json)；[testing/full-attempt-01/01-python.json](testing/full-attempt-01/01-python.json)；[testing/quick-attempt-01/01-python.json](testing/quick-attempt-01/01-python.json)

### T050

`test_material_foundation.MaterialFoundationTests.test_rerank_cancellation_preserves_completed_scores_and_releases_hold` — 有真实通过记录。源码：[第 196 行](../../../../automation/tests/test_material_foundation.py#L196)。
执行依据：[inheritance-closure-foundation-budget.json](inheritance-closure-foundation-budget.json)；[testing/full-attempt-01/01-python.json](testing/full-attempt-01/01-python.json)；[testing/quick-attempt-01/01-python.json](testing/quick-attempt-01/01-python.json)

### T051

`test_material_foundation.MaterialFoundationTests.test_rerank_only_uses_provided_fixed_slices_and_preserves_evidence` — 有真实通过记录。源码：[第 145 行](../../../../automation/tests/test_material_foundation.py#L145)。
执行依据：[inheritance-closure-foundation-budget.json](inheritance-closure-foundation-budget.json)；[testing/full-attempt-01/01-python.json](testing/full-attempt-01/01-python.json)；[testing/quick-attempt-01/01-python.json](testing/quick-attempt-01/01-python.json)

### T052

`test_material_foundation.MaterialFoundationTests.test_rerank_reports_missing_text_provider_failure_and_zero_budget` — 有真实通过记录。源码：[第 173 行](../../../../automation/tests/test_material_foundation.py#L173)。
执行依据：[inheritance-closure-foundation-budget.json](inheritance-closure-foundation-budget.json)；[testing/full-attempt-01/01-python.json](testing/full-attempt-01/01-python.json)；[testing/quick-attempt-01/01-python.json](testing/quick-attempt-01/01-python.json)

### T053

`test_material_foundation.MaterialFoundationTests.test_restore_creates_new_revision_and_rejects_later_changes` — 有真实通过记录。源码：[第 327 行](../../../../automation/tests/test_material_foundation.py#L327)。
执行依据：[inheritance-closure-foundation-budget.json](inheritance-closure-foundation-budget.json)；[testing/full-attempt-01/01-python.json](testing/full-attempt-01/01-python.json)；[testing/quick-attempt-01/01-python.json](testing/quick-attempt-01/01-python.json)

### T054

`test_material_foundation.MaterialFoundationTests.test_source_read_and_representation_build_are_read_only` — 有真实通过记录。源码：[第 294 行](../../../../automation/tests/test_material_foundation.py#L294)。
执行依据：[inheritance-closure-foundation-budget.json](inheritance-closure-foundation-budget.json)；[testing/full-attempt-01/01-python.json](testing/full-attempt-01/01-python.json)；[testing/quick-attempt-01/01-python.json](testing/quick-attempt-01/01-python.json)

### T055

`test_material_foundation.MaterialFoundationTests.test_validate_apply_binding_cas_and_idempotency` — 有真实通过记录。源码：[第 308 行](../../../../automation/tests/test_material_foundation.py#L308)。
执行依据：[inheritance-closure-foundation-budget.json](inheritance-closure-foundation-budget.json)；[testing/full-attempt-01/01-python.json](testing/full-attempt-01/01-python.json)；[testing/quick-attempt-01/01-python.json](testing/quick-attempt-01/01-python.json)

### T056

`test_material_maintenance.MaterialMaintenanceTests.test_apply_uses_real_cas_and_same_request_id_replays_without_new_revision` — 有真实通过记录。源码：[第 187 行](../../../../automation/tests/test_material_maintenance.py#L187)。
执行依据：[testing/full-attempt-01/01-python.json](testing/full-attempt-01/01-python.json)；[testing/quick-attempt-01/01-python.json](testing/quick-attempt-01/01-python.json)

### T057

`test_material_maintenance.MaterialMaintenanceTests.test_cross_owner_failure_returns_committed_owner_and_retries_only_pending_owner` — 有真实通过记录。源码：[第 334 行](../../../../automation/tests/test_material_maintenance.py#L334)。
执行依据：[testing/full-attempt-01/01-python.json](testing/full-attempt-01/01-python.json)；[testing/quick-attempt-01/01-python.json](testing/quick-attempt-01/01-python.json)

### T058

`test_material_maintenance.MaterialMaintenanceTests.test_retract_appends_real_review_and_preserves_claim_record` — 有真实通过记录。源码：[第 228 行](../../../../automation/tests/test_material_maintenance.py#L228)。
执行依据：[testing/full-attempt-01/01-python.json](testing/full-attempt-01/01-python.json)；[testing/quick-attempt-01/01-python.json](testing/quick-attempt-01/01-python.json)

### T059

`test_material_maintenance.MaterialMaintenanceTests.test_review_saves_new_immutable_version_without_business_commit` — 有真实通过记录。源码：[第 149 行](../../../../automation/tests/test_material_maintenance.py#L149)。
执行依据：[testing/full-attempt-01/01-python.json](testing/full-attempt-01/01-python.json)；[testing/quick-attempt-01/01-python.json](testing/quick-attempt-01/01-python.json)

### T060

`test_material_maintenance_status.MaterialMaintenanceStatusTests.test_applied_plan_reports_real_commit_fixed_changes_and_live_index_pending` — 有真实通过记录。源码：[第 125 行](../../../../automation/tests/test_material_maintenance_status.py#L125)。
执行依据：[testing/full-attempt-01/01-python.json](testing/full-attempt-01/01-python.json)；[testing/quick-attempt-01/01-python.json](testing/quick-attempt-01/01-python.json)

### T061

`test_material_maintenance_status.MaterialMaintenanceStatusTests.test_partial_cross_owner_failure_is_observed_without_resuming_second_owner` — 有真实通过记录。源码：[第 146 行](../../../../automation/tests/test_material_maintenance_status.py#L146)。
执行依据：[testing/full-attempt-01/01-python.json](testing/full-attempt-01/01-python.json)；[testing/quick-attempt-01/01-python.json](testing/quick-attempt-01/01-python.json)

### T062

`test_material_queries.MaterialQueryTests.test_active_query_rejects_poll_and_resume_without_charging` — 有真实通过记录。源码：[第 230 行](../../../../automation/tests/test_material_queries.py#L230)。
执行依据：[testing/full-attempt-01/01-python.json](testing/full-attempt-01/01-python.json)；[testing/quick-attempt-01/01-python.json](testing/quick-attempt-01/01-python.json)

### T063

`test_material_queries.MaterialQueryTests.test_empty_scope_is_empty_not_global` — 有真实通过记录。源码：[第 56 行](../../../../automation/tests/test_material_queries.py#L56)。
执行依据：[testing/full-attempt-01/01-python.json](testing/full-attempt-01/01-python.json)；[testing/quick-attempt-01/01-python.json](testing/quick-attempt-01/01-python.json)

### T064

`test_material_queries.MaterialQueryTests.test_equal_index_watermarks_do_not_hide_an_unindexed_head` — 有真实通过记录。源码：[第 186 行](../../../../automation/tests/test_material_queries.py#L186)。
执行依据：[testing/full-attempt-01/01-python.json](testing/full-attempt-01/01-python.json)；[testing/quick-attempt-01/01-python.json](testing/quick-attempt-01/01-python.json)

### T065

`test_material_queries.MaterialQueryTests.test_exclusion_dominates_include` — 有真实通过记录。源码：[第 61 行](../../../../automation/tests/test_material_queries.py#L61)。
执行依据：[testing/full-attempt-01/01-python.json](testing/full-attempt-01/01-python.json)；[testing/quick-attempt-01/01-python.json](testing/quick-attempt-01/01-python.json)

### T066

`test_material_queries.MaterialQueryTests.test_explicit_block_locator_survives_selection_and_keeps_required_definition` — 有真实通过记录。源码：[第 202 行](../../../../automation/tests/test_material_queries.py#L202)。
执行依据：[testing/full-attempt-01/01-python.json](testing/full-attempt-01/01-python.json)；[testing/quick-attempt-01/01-python.json](testing/quick-attempt-01/01-python.json)

### T067

`test_material_queries.MaterialQueryTests.test_fixed_old_revision_can_be_selected` — 有真实通过记录。源码：[第 113 行](../../../../automation/tests/test_material_queries.py#L113)。
执行依据：[testing/full-attempt-01/01-python.json](testing/full-attempt-01/01-python.json)；[testing/quick-attempt-01/01-python.json](testing/quick-attempt-01/01-python.json)

### T068

`test_material_queries.MaterialQueryTests.test_formal_exact_claim_never_borrows_other_accepted_claim` — 有真实通过记录。源码：[第 124 行](../../../../automation/tests/test_material_queries.py#L124)。
执行依据：[testing/full-attempt-01/01-python.json](testing/full-attempt-01/01-python.json)；[testing/quick-attempt-01/01-python.json](testing/quick-attempt-01/01-python.json)

### T069

`test_material_queries.MaterialQueryTests.test_missing_representation_never_silently_renders_another_type` — 有真实通过记录。源码：[第 163 行](../../../../automation/tests/test_material_queries.py#L163)。
执行依据：[testing/full-attempt-01/01-python.json](testing/full-attempt-01/01-python.json)；[testing/quick-attempt-01/01-python.json](testing/quick-attempt-01/01-python.json)

### T070

`test_material_queries.MaterialQueryTests.test_optional_channel_degradation_survives_packet` — 有真实通过记录。源码：[第 98 行](../../../../automation/tests/test_material_queries.py#L98)。
执行依据：[testing/full-attempt-01/01-python.json](testing/full-attempt-01/01-python.json)；[testing/quick-attempt-01/01-python.json](testing/quick-attempt-01/01-python.json)

### T071

`test_material_queries.MaterialQueryTests.test_pluggable_ranking_keeps_fixed_identities` — 有真实通过记录。源码：[第 108 行](../../../../automation/tests/test_material_queries.py#L108)。
执行依据：[testing/full-attempt-01/01-python.json](testing/full-attempt-01/01-python.json)；[testing/quick-attempt-01/01-python.json](testing/quick-attempt-01/01-python.json)

### T072

`test_material_queries.MaterialQueryTests.test_real_fts_digest_and_selected_assembly` — 有真实通过记录。源码：[第 45 行](../../../../automation/tests/test_material_queries.py#L45)。
执行依据：[testing/full-attempt-01/01-python.json](testing/full-attempt-01/01-python.json)；[testing/quick-attempt-01/01-python.json](testing/quick-attempt-01/01-python.json)

### T073

`test_material_queries.MaterialQueryTests.test_retracted_review_filter_is_distinct_from_current_validity` — 有真实通过记录。源码：[第 217 行](../../../../automation/tests/test_material_queries.py#L217)。
执行依据：[testing/full-attempt-01/01-python.json](testing/full-attempt-01/01-python.json)；[testing/quick-attempt-01/01-python.json](testing/quick-attempt-01/01-python.json)

### T074

`test_material_queries.MaterialQueryTests.test_source_revocation_blocks_cached_search_and_assembly` — 有真实通过记录。源码：[第 75 行](../../../../automation/tests/test_material_queries.py#L75)。
执行依据：[testing/full-attempt-01/01-python.json](testing/full-attempt-01/01-python.json)；[testing/quick-attempt-01/01-python.json](testing/quick-attempt-01/01-python.json)

### T075

`test_material_queries.MaterialQueryTests.test_unregistered_repair_and_tolerance_are_not_ignored` — 有真实通过记录。源码：[第 159 行](../../../../automation/tests/test_material_queries.py#L159)。
执行依据：[testing/full-attempt-01/01-python.json](testing/full-attempt-01/01-python.json)；[testing/quick-attempt-01/01-python.json](testing/quick-attempt-01/01-python.json)

### T076

`test_material_queries.MaterialQueryTests.test_zero_read_budget_does_not_open_record_body` — 有真实通过记录。源码：[第 85 行](../../../../automation/tests/test_material_queries.py#L85)。
执行依据：[testing/full-attempt-01/01-python.json](testing/full-attempt-01/01-python.json)；[testing/quick-attempt-01/01-python.json](testing/quick-attempt-01/01-python.json)

### T077

`test_material_query_fixture.MaterialQueryFixtureTests.test_fixed_unit_and_documents_keep_old_bytes_after_r2` — 有真实通过记录。源码：[第 40 行](../../../../automation/tests/test_material_query_fixture.py#L40)。
执行依据：[testing/full-attempt-01/01-python.json](testing/full-attempt-01/01-python.json)；[testing/quick-attempt-01/01-python.json](testing/quick-attempt-01/01-python.json)

### T078

`test_material_recall.MaterialRecallTests.test_candidate_budget_is_cumulative_across_pages` — 有真实通过记录。源码：[第 156 行](../../../../automation/tests/test_material_recall.py#L156)。
执行依据：[material-recall-final-tests.json](material-recall-final-tests.json)；[testing/full-attempt-01/01-python.json](testing/full-attempt-01/01-python.json)

### T079

`test_material_recall.MaterialRecallTests.test_current_resume_skips_changed_fixed_candidate_without_switching_revision` — 有真实通过记录。源码：[第 193 行](../../../../automation/tests/test_material_recall.py#L193)。
执行依据：[material-recall-final-tests.json](material-recall-final-tests.json)；[testing/full-attempt-01/01-python.json](testing/full-attempt-01/01-python.json)

### T080

`test_material_recall.MaterialRecallTests.test_final_one_reads_only_first_canonical_body_and_resume_reads_next` — 有真实通过记录。源码：[第 108 行](../../../../automation/tests/test_material_recall.py#L108)。
执行依据：[material-recall-final-tests.json](material-recall-final-tests.json)；[testing/full-attempt-01/01-python.json](testing/full-attempt-01/01-python.json)

### T081

`test_material_recall.MaterialRecallTests.test_formal_representation_fragment_is_null_without_claim_approval` — 有真实通过记录。源码：[第 300 行](../../../../automation/tests/test_material_recall.py#L300)。
执行依据：[material-recall-final-tests.json](material-recall-final-tests.json)；[testing/full-attempt-01/01-python.json](testing/full-attempt-01/01-python.json)

### T082

`test_material_recall.MaterialRecallTests.test_lexical_iterator_failure_keeps_its_completed_prefix` — 有真实通过记录。源码：[第 264 行](../../../../automation/tests/test_material_recall.py#L264)。
执行依据：[material-recall-final-tests.json](material-recall-final-tests.json)；[testing/full-attempt-01/01-python.json](testing/full-attempt-01/01-python.json)

### T083

`test_material_recall.MaterialRecallTests.test_missing_owner_watermark_is_partial_even_when_fts_rows_exist` — 有真实通过记录。源码：[第 208 行](../../../../automation/tests/test_material_recall.py#L208)。
执行依据：[material-recall-final-tests.json](material-recall-final-tests.json)；[testing/full-attempt-01/01-python.json](testing/full-attempt-01/01-python.json)

### T084

`test_material_recall.MaterialRecallTests.test_multiple_representations_keep_individual_raw_scores_and_fixed_refs` — 有真实通过记录。源码：[第 270 行](../../../../automation/tests/test_material_recall.py#L270)。
执行依据：[material-recall-final-tests.json](material-recall-final-tests.json)；[testing/full-attempt-01/01-python.json](testing/full-attempt-01/01-python.json)

### T085

`test_material_recall.MaterialRecallTests.test_read_budget_exhausted_after_first_page_cannot_open_next_body` — 有真实通过记录。源码：[第 165 行](../../../../automation/tests/test_material_recall.py#L165)。
执行依据：[material-recall-final-tests.json](material-recall-final-tests.json)；[testing/full-attempt-01/01-python.json](testing/full-attempt-01/01-python.json)

### T086

`test_material_recall.MaterialRecallTests.test_rejected_first_candidate_is_refilled_before_final_k` — 有真实通过记录。源码：[第 128 行](../../../../automation/tests/test_material_recall.py#L128)。
执行依据：[material-recall-final-tests.json](material-recall-final-tests.json)；[testing/full-attempt-01/01-python.json](testing/full-attempt-01/01-python.json)

### T087

`test_material_recall.MaterialRecallTests.test_repeated_resume_reuses_paid_page_without_second_candidate_charge` — 有真实通过记录。源码：[第 137 行](../../../../automation/tests/test_material_recall.py#L137)。
执行依据：[material-recall-final-tests.json](material-recall-final-tests.json)；[testing/full-attempt-01/01-python.json](testing/full-attempt-01/01-python.json)

### T088

`test_material_recall.MaterialRecallTests.test_resume_retains_frozen_revision_after_real_commit_and_reindex` — 有真实通过记录。源码：[第 177 行](../../../../automation/tests/test_material_recall.py#L177)。
执行依据：[material-recall-final-tests.json](material-recall-final-tests.json)；[testing/full-attempt-01/01-python.json](testing/full-attempt-01/01-python.json)

### T089

`test_material_recall.MaterialRecallTests.test_sqlite_and_oserror_lexical_failures_preserve_completed_identity` — 有真实通过记录。源码：[第 244 行](../../../../automation/tests/test_material_recall.py#L244)。
执行依据：[material-recall-final-tests.json](material-recall-final-tests.json)；[testing/full-attempt-01/01-python.json](testing/full-attempt-01/01-python.json)

### T090

`test_material_review_inheritance.MaterialReviewInheritanceTests.test_new_review_revalidates_changed_claim_and_preserves_old_review_owner_scope` — 有真实通过记录。源码：[第 25 行](../../../../automation/tests/test_material_review_inheritance.py#L25)。
执行依据：[review-inheritance-acceptance.json](review-inheritance-acceptance.json)；[testing/full-attempt-01/01-python.json](testing/full-attempt-01/01-python.json)；[testing/review-inheritance-final-20260910.log](testing/review-inheritance-final-20260910.log)

### T091

`test_material_scope.MaterialScopeTests.test_both_scopes_allow_required_fixed_content_and_complete_packet` — 有真实通过记录。源码：[第 85 行](../../../../automation/tests/test_material_scope.py#L85)。
执行依据：[testing/full-attempt-01/01-python.json](testing/full-attempt-01/01-python.json)；[testing/quick-attempt-01/01-python.json](testing/quick-attempt-01/01-python.json)

### T092

`test_material_scope.MaterialScopeTests.test_explicit_user_exclusions_deny_derived_parent_under_wide_ceiling` — 有真实通过记录。源码：[第 95 行](../../../../automation/tests/test_material_scope.py#L95)。
执行依据：[testing/full-attempt-01/01-python.json](testing/full-attempt-01/01-python.json)；[testing/quick-attempt-01/01-python.json](testing/quick-attempt-01/01-python.json)

### T093

`test_material_scope.MaterialScopeTests.test_owner_ceiling_rejects_parent_before_outside_dependency_body_read` — 有真实通过记录。源码：[第 78 行](../../../../automation/tests/test_material_scope.py#L78)。
执行依据：[testing/full-attempt-01/01-python.json](testing/full-attempt-01/01-python.json)；[testing/quick-attempt-01/01-python.json](testing/quick-attempt-01/01-python.json)

### T094

`test_material_scope.MaterialScopeTests.test_primary_scope_limits_output_but_ceiling_allows_source_authorization` — 有真实通过记录。源码：[第 68 行](../../../../automation/tests/test_material_scope.py#L68)。
执行依据：[testing/full-attempt-01/01-python.json](testing/full-attempt-01/01-python.json)；[testing/quick-attempt-01/01-python.json](testing/quick-attempt-01/01-python.json)

### T095

`test_representation_contracts.BudgetLedgerTests.test_q28_cancellation_preserves_completed_cost_and_stops_next_charge` — 有真实通过记录。源码：[第 325 行](../../../../automation/tests/test_representation_contracts.py#L325)。
执行依据：[testing/full-attempt-01/01-python.json](testing/full-attempt-01/01-python.json)；[testing/quick-attempt-01/01-python.json](testing/quick-attempt-01/01-python.json)；[testing/contracts-final-20260910.log](testing/contracts-final-20260910.log)

### T096

`test_representation_contracts.RepresentationContractTests.test_basis_observation_is_stable_for_same_observation_and_changes_with_refs` — 有真实通过记录。源码：[第 45 行](../../../../automation/tests/test_representation_contracts.py#L45)。
执行依据：[testing/full-attempt-01/01-python.json](testing/full-attempt-01/01-python.json)；[testing/contracts-final-20260910.log](testing/contracts-final-20260910.log)

### T097

`test_representation_contracts.RepresentationContractTests.test_structured_issue_retries_and_never_discloses_unobserved_refs` — 有真实通过记录。源码：[第 58 行](../../../../automation/tests/test_representation_contracts.py#L58)。
执行依据：[testing/full-attempt-01/01-python.json](testing/full-attempt-01/01-python.json)；[testing/contracts-final-20260910.log](testing/contracts-final-20260910.log)

## 实际 AI 记录及边界

A07 覆盖摘要/正文、固定来源、完整块与预算缺口；其历史小预算包 stop_reason=null 仍是原回执事实。A08 实际比较固定两端并保存有条件导航判断。A09 由外部 AI 提交维护草案，经不可变 review 计划、apply 和固定读回产生规范新修订；自动 representation builder 仍只组合既有字段。A09 没有应撤回的已复核 claim，C24 另用公开 API 正向集成补足。三者均不是人工验收、盲测或现实模型验证。

- [A07 实际评估](actual-ai/A07/attempt-fed7c90e130740dca3055ed6aaf3dab0/assessments/assessment-4867088575974f52ad4d933d84707dc5.json)，执行者 `Codex /root/retrieval_review actual AI`。
- [A08 实际评估](actual-ai/A08/attempt-827ddd756ca34e78825e4e48c7d98aa4/assessments/assessment-6ad5dd19f48641d7860d39b97d5267b7.json)，执行者 `Codex /root/retrieval_review actual AI`。
- [A09 实际评估](actual-ai/A09/attempt-6a3c96e965c1408e998f7cfc8de720e7/assessments/assessment-e5b36d2cf0d34558bdff303687f91f38.json)，执行者 `Codex /root/retrieval_review actual AI`。

本审计未增加依赖/模型或修改业务原件；README 已核对现有材料查询导航，详细分类说明由 MATERIAL_QUERY 指向 KNOWLEDGE_FACETS。完整清单、预构建资源、真实 setup 升级/恢复、刷新索引及校验由主集成回执证明，不用本表替代。

机器回执：[inheritance-acceptance.json](inheritance-acceptance.json)。刷新本文：

```powershell
.\automation\python.ps1 projects/architecture-evolution/runs/run-20260909t194710z-3cf36b2fdd60/build_inheritance_acceptance.py
```
