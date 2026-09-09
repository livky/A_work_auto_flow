# 服务入口、算法与失败处理 v1

本文件描述待实现的程序，不是已有命令手册。所有函数位于计划新增的 `automation/scripts/memory/` 包；公共入口由 MemoryService 调度。CLI 参数和 HTTP 都转换为同一请求对象。

## 1. 入口清单

| 文件与函数签名 | 输入 | 输出及责任 |
|---|---|---|
| contracts.validate_record(draft, context) | 草案、类型登记和批次引用上下文 | ValidationResult：字段错误精确到 JSON pointer；不写入 |
| owners.list_owners(root, filters) | 获准工作区、类型/ID过滤 | OwnerView[]：native 信息、memory_home、能力；不加载大产物 |
| owners.resolve_owner(root, owner_id) | 稳定身份 | 唯一 OwnerDescriptor 或错误；禁止重复认领 |
| owners.adopt_owner(root, native_ref, expected_hash) | 已有材料定位及预期指纹 | 持久入口与别名；原文件字节不变 |
| owners.register_type(type_spec, adapter) | 类型schema、版本和可信适配器实现 | 登记可识别类型；不是允许AI上传并执行任意代码的入口 |
| policy.resolve(owner, request_overrides) | 四级策略来源 | 合并值及每项来源；保留显式false |
| service.inspect(owner_id, revision=None) | 对象、可选历史版本 | HEAD、策略来源、记录分页及风险 |
| service.validate_draft(request) | CommitRequest | ValidatedDraft、内容差异、缺口、预测 ID 映射；无写入 |
| service.commit(request) | CommitRequest | CommitReceipt；统一使用 store.commit_batch |
| store.commit_batch(owner, expected_head, request_id, operations) | 单对象批次 | 原子对象快照；版本、幂等、恢复，不调用模型 |
| service.review(request) | ReviewRequest | ReviewReceipt；旧 CLM 委托 evidence.review_claim，新 CLM 写独立 review 记录 |
| research.transition_question(id, expected_revision, state, basis) | 问题转换及依据 | 新修订或合法性错误；通过 commit 提交 |
| research.set_goal / checkpoint | 目标/检查点草案、固定引用 | 记录修订；旧目标引用不变 |
| research.route_transition(id, expected_revision, state, basis) | 路线状态、阻碍/重开依据 | 新修订及历史；通过commit提交 |
| evidence_adapter.formal_projection(refs, scope) | 固定引用及用途范围 | 仅合格CLM文本、拒绝原因和路径；供W04独立验收及后续包组装复用 |
| impact.question_resolution_validity(question_ref) | 问题及答案固定引用 | 保留历史问题状态，计算resolution_needs_revalidation及依据 |
| index.sync_owner(owner_id, generation) | 已提交对象代次 | IndexReceipt：indexed、pending、failed；FTS 与向量状态分开 |
| index.rebuild(scope, dry_run) | 获准对象集合 | 可核对重建清单和水位；不修改规范记录 |
| index.reconcile(owner_id=None) | 单对象或获准对象集合 | 比较HEAD/索引水位，重放持久索引待办；不再执行业务提交 |
| search.search(request) | SearchRequest | SearchResult：规范候选、通道排名、命中解释、风险和查询 ID |
| associations.propose(request) | seeds、method、范围、排除项 | 带来源版本的候选；不写 supports |
| associations.decide(request) | 候选、处理状态、解释及版本 | 一条规范关系及历史；通过 commit 保存 |
| packets.expand(refs, selection, budget) | 固定引用与保留的选择 | 有界展开、缺口、实际版本；受同一授权约束 |
| packets.build_context(request) | 查询结果、stage、budget、purpose、scope | context_text＋manifest；最多两次扩展 |
| history.build_history(owner_id, cursor, limit) | 对象、分页 | 发生时间线/记录时间、目标路线、固定来源与缺口 |
| history.resume(owner_id, budget, selection) | 对象与约束 | 当前目标、断点、变化风险、下一步；不执行实验 |
| consolidation.prepare(owner_id, since_commit, trigger) | 上次处理点、触发原因 | 变化、受影响记录、待处理项、固定 basis_heads |
| consolidation.apply(draft, expected_basis_heads) | AI 的 revise/retain/defer 决策及新记录 | 提交修改与 consolidation 记录；并发变化须重算 |
| summaries.prepare(query, owners, budget) | 跨项目问题及指定范围 | 有来源版本的总结材料包，不调用外部模型 |
| summaries.save(owner_id, draft, basis_heads) | AI 撰写的 L2/L3 与依据 | 通过同一 commit 保存；不创建第五层 |
| feedback.save(query_id, target, label, note, adopted_in) | 原查询、记录版本、反馈及实际应用结果 | 长期反馈记录；不提升复核 |
| migration.preview / apply | 类型适配、选定对象或旧源、路径映射 | 逐项计划、前后指纹、回执；保留原件 |
| recovery.inspect / recover | owner、事务 ID、恢复模式 | 检查锁/孤立事务、完成状态、可恢复建议；拒绝覆盖新修改 |

为了首次实现即可用，W02 提供 inspect、validate-draft、commit、recover 最小 CLI；其他命令随对应服务加入，W12 才形成最终面向 AI 的调用指导。

## 2. 请求与回执

### 2.1 CommitRequest

必需字段：schema_version=1、request_id（调用方 UUID）、actor、owner_id、expected_head（新记忆为 null）、operations（非空数组）、dry_run（默认 false）。

每个 operation 为 put_record、transition_question、set_policy、decide_association、save_checkpoint 之一；普通 put_record 禁止写 review。创建有 client_key 和 draft；更新有 record_id、expected_revision、draft。单批次同一 ID 只能出现一次；跨批次引用用正式 ID。

允许一批创建来源、事件、问题及经验并互相引用，预检先完成 client_key 解析；supports/input 不能形成自证环。版本由服务端分配，业务生产调用禁止注入固定 ID；测试适配器使用隔离依赖注入。

### 2.2 CommitReceipt

包含 request_id、owner_id、commit_id、generation、save_status（committed/no_change/not_committed）、record_results（client_key→ID、revision、content_hash）、index_status（indexed/pending/failed）、index_details、warnings、error、recovery_ref。

同一请求的重新执行返回原 commit_id、记录映射和修订；索引当前状态可重新查询，不伪造第二次提交。dry-run 返回 would_create/would_update/errors，不持久化请求 ledger。

### 2.3 SearchRequest

必需 query、purpose=exploration|formal；formal 必须 scope。可选 owner_id、owner_types、include_ids、full_ids、exclude_ids、stage、budget、history=false、vector=auto|off|required、limit。明确 exclude 优先于 include/full，并写入 omission reason。访问权限在过滤和展开阶段均检查。

SearchResult 包含 query_id、query_fingerprint、scope、selection、source_heads、candidates、missing、degradation、timings。每个候选包含 canonical_id、revision、owner_id、roles、rank_channels、match_reason、boundaries、review_state、effective_validity、expansion_paths。

### 2.4 错误契约

| error.code | CLI 退出码 / HTTP | 触发与保证 |
|---|---|---|
| INVALID_ARGUMENT / INVALID_SCHEMA | 2 / 400或422 | 未知字段、层级、枚举、格式；业务内容不变 |
| NOT_FOUND / UNRESOLVED_REFERENCE | 2 / 404或422 | 不存在的目标或不完整固定引用；不静默建立空目标 |
| ACCESS_DENIED / UNSAFE_PATH | 4 / 403 | 超范围、联接、非法路径；不读取禁止正文、不写目标 |
| VERSION_CONFLICT / STALE_BASIS | 5 / 409 | HEAD/记录/巩固依据变化；返回可比较版本，不自动覆盖 |
| IDEMPOTENCY_CONFLICT | 5 / 409 | 相同 request_id 不同规范请求内容；拒绝写入 |
| LOCKED | 6 / 423 | 活跃写锁或 Qdrant 占用；可重试，不删除别的进程锁 |
| INTEGRITY_ERROR | 7 / 422 | hash、manifest、旧业务元数据损坏；保留现场 |
| STORAGE_ERROR | 8 / 500 | 存储失败；回执明确是否已提交和恢复定位 |
| INDEX_PENDING | 3 / 202 | 已成功保存，索引未跟上；save_status=committed |
| EVIDENCE_INELIGIBLE / INVALID_TRANSITION | 9 / 422 | 正式复核不满足或状态转换缺依据；保留旧状态 |
| CAPABILITY_UNAVAILABLE | 10 / 503 | vector=required 但模型不可用；auto 则正常返回降级说明 |
| 成功或 no_change | 0 / 200或201 | 成功回执不能掩盖任一索引/证据错误 |

formal 查询可成功返回零条合格结果，并用 rejected 列表说明原因；不是把不合格候选塞入正文。预检失败可一次返回多个字段错误；非零返回都须是可解析 JSON，日志走 stderr。

## 3. 保存、幂等与恢复算法

1. 解析 owner 与允许路径；校验请求结构、单对象范围和临时引用。
2. 取得该 owner 的排他锁，检查 request_ledger。相同 ID+规范请求 hash 已存在时直接返回原提交；不同 hash 拒绝。此步先于旧 expected_head 检查，确保提交成功后的重试不误报冲突。
3. 比较 expected_head 及每个 expected_revision；读取所有受引用快照，检查状态和依赖。新对象 HEAD=null；已有对象省略 expected_head 不允许盲写。
4. 对相同 content_hash 的 put 标为 no_change。全批无变化则记录轻量请求回执，不创建内容修订；该回执走独立、原子写的 request-receipts 区，不能修改旧 commit。读取幂等状态同时检查已提交 ledger 与该区。
5. 在同盘 staging 写新修订、完整 manifest 和 receipt，flush/fsync，校验所有 hash。对关联源 HEAD/文件指纹做提交前二次检查。
6. 将已完成 staging 原子改名到唯一 commits/<commit-id>。再次确认锁与 expected_head 后，以原子替换切换 HEAD；这一步是提交生效点。
7. 释放 owner 锁，更新派生索引。失败保留 commit 中的索引待办，返回 INDEX_PENDING；补偿以 generation 为水位，不重复业务记录。
8. 每次正式读取只认 HEAD 可达的提交。HEAD 切换前中断：旧快照可读，孤立 commit 待检查；切换后回执丢失：ledger 可重放原回执。recover 不把未知孤立提交自动接到新 HEAD 上。

锁含进程 ID、启动标识、时间与 owner；恢复只在可证明原进程已退出时清理，证据不足返回 LOCKED。多 owner 可以独立提交，SQLite/Qdrant 按现有单写约束串行。Windows 文件被占用、磁盘满、写入/改名/HEAD 替换失败分别注入测试；目录元数据的断电持久性受文件系统限制，不能把进程中断测试报告成任意断电无损保证。

规范请求 hash 包含 actor、owner、expected_head、operations 的语义内容，排除 request_id 和 dry_run；dry-run 不占用该 ID。每个失败窗口的恢复判定见 S 组验收。

## 4. 证据与派生失效

扩展 EvidenceGraph 的“读取适配”，复用旧状态、scope 和正式门槛；旧 review_claim 不批量重算历史 owner_fingerprint。

维护两个遍历语义：
- **正式依据检查**：沿 supports/input 传播撤回、缺失、内容变化和循环；contradicts/background 不按支持依赖传播。已复核的旧 Run 仍需原有 check-run/finalize-run 门槛。
- **更新影响检查**：从变化来源沿 derived_from、表示 target、地图引用、检查点引用等反向边标记 stale/needs_revalidation。相似邻居可提示检查，但不得直接宣布其结论被撤回。

新 memory claim 的 ReviewEvent 绑定 claim 内容及所在 event/experience content_hash。新增独立 checkpoint/goal/policy 不改这个 hash；真正修改结论或证据仍阻止正式沿用。正式包在生成前回源检查，记录检查时采用的版本；之后原件变化无法撤销已经交付的旧文本，下一次复用重新检查。

遍历采用 visited 集合和有向循环检测，输出实际阻断路径；一个来源通过两条路径出现只报告一次规范节点。失效不直接改写所有下游正文和复核历史，而是在当前视图/正式入口阻止沿用，AI 再提交修订。

## 5. 索引、排名和相关性算法

### 5.1 增量索引

比较 owner HEAD generation 和 indexed_generation，按 changed_ids 读取当前修订。FTS 更新在一次 SQLite 事务中提交；向量失败单独记录水位。删除表示、收窄权限、撤回和 owner_only 变化必须清理旧索引可见性。仍须查询回源过滤，以覆盖崩溃或外部手工变更。

来源材料 SRC-* 继续走已有全文系统；MEM/CLM 的多表示映射统一 canonical_id，不能因 Markdown 展示副本出现第二个证据。旧文件路径来源 ID 由适配映射到新规范身份，移动后重建索引而不改 record_id。

### 5.2 多通道检索

先做访问/排除范围过滤，再取得全文、记忆 FTS 与向量各通道候选。同通道把同一规范记录的多表示折叠，取最优名次并重新编号，避免重复表示挤占其他记录的名次；随后进行 RRF：

$$
\operatorname{score}(d)=\sum_{c\in C_d}\frac{1}{60+\operatorname{rank}_c(d)}
$$

其中 d 为规范记录，C_d 为命中的检索通道，rank 从 1 开始。60 为首版固定融合参数；各通道初始权重相同，禁止把原始向量分数和 FTS 分数直接相加。并列按 canonical_id 升序，测试必须可重复。

2026-09-09 增加探索检索策略 `topic-evidence-tiers-v2`：在已回源且有权读取的候选中，找出查询明确提到的完整登记关键词。先融合具有这些主题关键词的具体记录；同一原生 Run 的匹配 claim 已出现时，把宽泛 Run 容器保留到后层，不合并或改写两者身份。其余匹配（包括缺少关键词、只由向量发现的记录）仍保留为后备候选。各层内继续使用上述等权 RRF；层号优先于层内分数，因此不能把不同层的分数当成全局相关性概率。

没有显式主题、按精确 ID 查询、显式历史读取、正式证据投影及旧基线方案保持原排序路径。用户 include/full 优先于分层，exclude、权限、跨对象与正文预算照常生效。关键词只参与排序，不授予权限或科学复核状态。查询指纹记录策略版本，返回的 match_reason 记录命中主题与层号。该改进的开发/独立验证另列版本，不覆盖首版质量失败或改变冻结门槛。

从直接命中沿允许导航边进行有界邻接遍历；排除节点在扩展前移除，不能作为隐形桥梁。明确 accepted 的导航边默认参与扩展；candidate 单独显示并要求显式选择。候选相似度不会写科学证据关系。

复用当前 [context-policy.json](../../../retrieval/context-policy.json) 的 focus=6、investigate=14、wide=24 上限和 1/1/2 跳；跨对象上限首版为 2/4/8，不要求填满。默认上下文预算 16,000 Unicode 码点，并受工作区更小硬上限约束；这些是可配置工程默认值，以固定合成评价再检查，不能自动扩大用户预算。

### 5.3 分析方法

- 关键词关系：记录规范化关键词集合 Jaccard，共有词至少 2，初始阈值 0.3；返回共有词与各自差异。
- 语义关系：复用既有 encoder 的余弦相似，阈值读取既有配置；记录模型/编码器/源版本。测试用确定性向量检查数学逻辑，另跑真实离线模型评价。
- 显式关联：读取已保存关系及证据边，保留方向、来源与处理状态。
- 三种方法只提出候选。AI 解释共同问题结构与禁用条件后才能保存导航关系；聚类名称和类比建议都不自动复核结论。

## 6. 研究经过、上下文包与续接

history 读取 owner 的规范记忆和显式关联的旧 Run，按 occurred_at 排序；发生时间未知时显示“发生时间未知”，用 created_at 作稳定排列而不冒充事实时间。相同时间用 record_id 排序。按目标版本分段并保留路线切换、失败、问题、撤回和替代链，分页展开；不因关系遍历形成循环而无限加载。

resume 依次组装当前目标/约束、最新检查点、路线与未决问题、检查点后来源变化、下一步所需经验。旧目标仍能展开；检查点与当前 goal 不一致必须标明。准备包只建议下一步，不自动执行工具。

context_text 的预算使用 Unicode 码点计数，包含标题、正文、边界和内嵌引用；Python len 与前端 Array.from 一致。元数据 manifest 不含额外证据正文。条目优先完整装载；预算不足时选事先保存的有边界短表示或整体省略，不能截掉禁用条件。必读内容无法容纳时返回 insufficient_budget 与缺口，不宣称上下文完整。扩展最多两次，继承 include/full/exclude、scope、purpose 和预算。

## 7. 巩固与跨项目总结

prepare 根据上次 consolidation 的 basis_heads 及显式剩余项计算差异，返回 changed/affected/remaining；不计算“科学价值总分”。同一变化集的指纹作为 basis_hash。AI 提交每项 revise/retain/defer，程序检查所引用 heads 未变化，使用同一 commit 保存新经验、地图及巩固记录。

retain 需要理由，defer 仍在下一次 remaining。相同 basis_hash+相同决策重复提交 no_change。没有新源但出现新的解释时，change_reason 必须说明内容改变，允许新修订；语义相近但来源不同只提合并候选，不凭模型分数自动删记录。

跨项目 summaries.prepare 复用检索与展开的范围、固定版本和预算。save 将新的可复用经验归 L2，主题综合归 L3，选择一个 owner；源项目不被复制或改写。总结中可检验新主张通过 CLM 建模，默认 not-reviewed，不能继承来源的 accepted。

## 8. HTTP 与工作台

复用 [workbench_app/web.py](../../../automation/scripts/workbench_app/web.py) 的同源和本机服务边界，增加 /api/v1/memory/ 下 inspect、validate、commit、review、search、history、resume、prepare、summaries、associations、feedback、recover。HTTP action 为固定允许集合，不执行任意 shell。

前端类型从 W01 schema 生成。对象页提供“概览/经过/记录/问题与路线/版本与依据”，检索页提供“问题条件/候选类别/命中理由/展开”，关系页扩展相关性说明，保存后分别展示保存/索引/复核状态。Markdown 渲染不得执行 HTML 脚本。总结材料包可复制导出，AI 文本回填仍走同一 validate+commit。

## 9. 迁移接口边界

migration.preview 只读，输出身份映射、源指纹、目标路径、已有数据冲突和缺失依赖；apply 必须验证预览基线。旧对象按需采用，不自动提取未记录事实。导出单对象时生成依赖清单，默认只包含明确选定对象和受控文本，不递归复制外部原件。导入先验证包内相对路径和 hash，遇到 ID 相同内容不同返回冲突。

Windows 源码升级继续使用 setup.cmd；W11 对新的规范目录、辅助实体、请求回执、历史和共享 fixture 明确保护，派生索引重建。源码恢复不得删除升级后新记忆；旧版本不支持新 schema 时明确拒绝写入。细项见 M 组验收。
