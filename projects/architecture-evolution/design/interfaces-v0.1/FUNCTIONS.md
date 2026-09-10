# 逐函数设计目录

由 contract_ports.py 与 function-catalog.json 生成；所有端口尚未接入产品。输入类型的全部字段见 DATATYPES.md，行为共同约束见 SPEC.md。

## G01 固定读取与引用解析

保持固定版本，批量读取有上界；不依赖召回器。

实现落点（待拆分/适配）：`automation/scripts/memory/store.py; automation/scripts/memory/service.py; automation/scripts/memory/raw_materials.py`。

### ContentReader.describe

```python
ContentReader.describe(refs: tuple[t.FixedRef, ...], ctx: t.CallContext) -> t.Outcome[tuple[t.ContentMetadata, ...]]
```

- 抽象判断：保留：排序/导航只需元数据时避免读取全文。
- 前置条件：固定Ref可解析且来源获准。
- 返回保证：逐项返回真实身份、属性和标题；缺项显式说明。
- 调用：G12.authorize。
- 主要错误：NOT_FOUND, VERSION_MISMATCH, ACCESS_DENIED。

### ContentReader.read

```python
ContentReader.read(request: t.ReadRequest, ctx: t.CallContext) -> t.Outcome[t.ReadBatch]
```

- 抽象判断：保留：多入口共用固定正文读取。
- 前置条件：请求范围、表示、版本和预算均明确。
- 返回保证：返回实际正文、完整性、固定依据与缺口。
- 调用：ReferenceResolver.resolve；G12.authorize。
- 主要错误：SOURCE_MISSING, VERSION_MISMATCH, UNSUPPORTED。

### ContentReader.list_page

```python
ContentReader.list_page(scope: t.CorpusScope, page: t.PageRequest, ctx: t.CallContext) -> t.Outcome[t.Page[t.ContentMetadata]]
```

- 抽象判断：保留：避免枚举全库才能取前K项。
- 前置条件：limit为正；cursor与原范围一致。
- 返回保证：仅一页轻量元数据和有界续接位置。
- 调用：G12.authorize；RevisionStore.history。
- 主要错误：INVALID_ARGUMENT, BASIS_CHANGED。

### ReferenceResolver.resolve

```python
ReferenceResolver.resolve(refs: tuple[t.LegacyRef, ...], ctx: t.CallContext) -> t.Outcome[tuple[t.EvidenceLink, ...]]
```

- 抽象判断：保留：兼容旧六字段Ref，集中验证版本。
- 前置条件：原始引用真实存在；不猜测SHA或身份。
- 返回保证：保留关系语义并返回经回源核验的FixedRef。
- 调用：G12.authorize。
- 主要错误：NOT_FOUND, VERSION_MISMATCH, ACCESS_DENIED。

## G02 分级CRUD、版本与恢复

一个批次一个owner，CAS与幂等；新修订保留旧版。

实现落点（待拆分/适配）：`automation/scripts/memory/service.py; automation/scripts/memory/store.py; automation/scripts/memory/contracts.py`。

### ContentCommands.validate

```python
ContentCommands.validate(batch: t.ChangeBatch, ctx: t.CallContext) -> t.Outcome[t.ValidationReceipt]
```

- 抽象判断：保留：提交前提供准确可审查问题。
- 前置条件：单owner批次、注册schema、预期HEAD及来源可核验。
- 返回保证：验证凭据绑定批次SHA与依据；不写正式内容。
- 调用：G12.authorize；G12.assess；G01.read。
- 主要错误：INVALID_SCHEMA, BASIS_CHANGED, CONFLICT。

### ContentCommands.commit

```python
ContentCommands.commit(batch: t.ChangeBatch, ctx: t.CallContext) -> t.Outcome[t.CommitReceipt]
```

- 抽象判断：保留：统一类型规则与幂等用例入口。
- 前置条件：相同请求ID绑定同一完整语义；提交前再核验权限/CAS。
- 返回保证：单owner全部提交或不提交；client_key映射真实新Ref。
- 调用：ContentCommands.validate；RevisionStore.apply。
- 主要错误：IDEMPOTENCY_MISMATCH, CONFLICT, ACCESS_DENIED。

### ContentCommands.restore

```python
ContentCommands.restore(request: t.RestoreRequest, ctx: t.CallContext) -> t.Outcome[t.CommitReceipt]
```

- 抽象判断：保留：恢复是明确业务动作。
- 前置条件：旧Ref固定，当前HEAD与预期相同。
- 返回保证：创建恢复修订并保留后续历史；不倒退HEAD。
- 调用：G01.read；ContentCommands.commit。
- 主要错误：VERSION_MISMATCH, CONFLICT。

### RevisionStore.apply

```python
RevisionStore.apply(batch: t.ChangeBatch, validated: t.ValidationReceipt, ctx: t.CallContext) -> t.Outcome[t.CommitReceipt]
```

- 抽象判断：保留：隔离物理事务和内容规则。
- 前置条件：内部验证凭据匹配批次、规则与依据。
- 返回保证：原子生成提交/变化记录；不调用索引或模型。
- 调用：G12.authorize。
- 主要错误：CONFLICT, IDEMPOTENCY_MISMATCH。

### RevisionStore.history

```python
RevisionStore.history(owner: t.OwnerId, page: t.PageRequest, ctx: t.CallContext) -> t.Outcome[t.Page[t.CommitReceipt]]
```

- 抽象判断：保留：固定历史和恢复需要分页读版本。
- 前置条件：owner与cursor有效且可读。
- 返回保证：按固定历史链返回一页，不改变当前HEAD。
- 调用：G12.authorize。
- 主要错误：NOT_FOUND, ACCESS_DENIED。

## G03 表示维护

规范内容和派生表示分开；贡献来源闭包与生成版本可查。

实现落点（待拆分/适配）：`automation/scripts/memory/index.py; automation/scripts/memory/summaries.py; automation/scripts/memory/technical_units.py`。

### RepresentationCatalog.list

```python
RepresentationCatalog.list(refs: tuple[t.FixedRef, ...], requested: t.RepresentationSpec, ctx: t.CallContext) -> t.Outcome[tuple[t.RepresentationAvailability, ...]]
```

- 抽象判断：保留：让调用方发现缺失和未实现层次。
- 前置条件：固定内容与请求键明确。
- 返回保证：逐项available/stale/missing/unsupported；不虚构引用。
- 调用：G01.describe；G12.authorize。
- 主要错误：NOT_FOUND, ACCESS_DENIED。

### RepresentationCatalog.read

```python
RepresentationCatalog.read(refs: tuple[t.FixedRef, ...], ctx: t.CallContext) -> t.Outcome[t.ReadBatch]
```

- 抽象判断：保留：复用已有表示而不重新生成。
- 前置条件：表示Ref及全部贡献来源满足范围和授权。
- 返回保证：返回固定正文与实际来源，过期状态可见。
- 调用：G01.read；G12.authorize。
- 主要错误：SOURCE_MISSING, VERSION_MISMATCH, ACCESS_DENIED。

### RepresentationBuilder.plan

```python
RepresentationBuilder.plan(refs: tuple[t.FixedRef, ...], scope: t.CorpusScope, requested: t.RepresentationSpec, strategy: t.StrategyRef, ctx: t.CallContext) -> t.Outcome[t.RepresentationPlan]
```

- 抽象判断：保留：生成前冻结依赖和策略。
- 前置条件：源版本、请求表示与builder能力已核验。
- 返回保证：计划给出固定basis、生成器和范围。
- 调用：G01.describe；RepresentationCatalog.list。
- 主要错误：UNSUPPORTED, BUDGET_EXHAUSTED。

### RepresentationBuilder.build

```python
RepresentationBuilder.build(plan: t.RepresentationPlan, ctx: t.CallContext) -> t.Outcome[t.RepresentationBuild]
```

- 抽象判断：保留：替换提炼/投影算法。
- 前置条件：计划输入未漂移且取得预算额度。
- 返回保证：纯派生表示或新内容草案；不暗中提交新解释。
- 调用：G01.read；ExecutionControl.reserve。
- 主要错误：BASIS_CHANGED, BUDGET_EXHAUSTED, PARTIAL_FAILURE。

## G04 变化与索引维护

内容提交与索引水位分离，增量/重建/补偿可重试。

实现落点（待拆分/适配）：`automation/scripts/memory/store.py; automation/scripts/memory/index.py`。

### ChangeReader.read

```python
ChangeReader.read(scope: t.CorpusScope, page: t.PageRequest, ctx: t.CallContext) -> t.Outcome[t.Page[t.ChangeEvent]]
```

- 抽象判断：保留：增量维护无需扫描所有正文。
- 前置条件：分页范围和变化游标有效。
- 返回保证：有界变化页与读取basis，可重放。
- 调用：RevisionStore.history。
- 主要错误：BASIS_CHANGED, ACCESS_DENIED。

### IndexLifecycle.status

```python
IndexLifecycle.status(indexes: tuple[t.IndexKey, ...], scope: t.CorpusScope, ctx: t.CallContext) -> t.Outcome[tuple[t.Watermark, ...]]
```

- 抽象判断：保留：查询前确认索引覆盖。
- 前置条件：索引键与范围已注册。
- 返回保证：返回每后端水位；读取状态不隐式修复。
- 调用：G12.authorize。
- 主要错误：UNSUPPORTED。

### IndexLifecycle.plan

```python
IndexLifecycle.plan(mode: Literal['incremental', 'rebuild', 'repair'], index: t.IndexKey, scope: t.CorpusScope, changes: t.Page[t.ChangeEvent] | None, contents: t.Page[t.ContentMetadata] | None, ctx: t.CallContext) -> t.Outcome[t.IndexPlan]
```

- 抽象判断：保留：三种维护共享计划契约。
- 前置条件：增量changes或全量contents恰有一种有效输入。
- 返回保证：固定IndexKey、源版本、工作项和续扫位置。
- 调用：ChangeReader.read；G01.list_page；G03.list。
- 主要错误：INVALID_ARGUMENT, BASIS_CHANGED, UNSUPPORTED。

### IndexLifecycle.execute

```python
IndexLifecycle.execute(plan: t.IndexPlan, ctx: t.CallContext) -> t.Outcome[t.IndexReceipt]
```

- 抽象判断：保留：索引可重试并隔离内容事务。
- 前置条件：固定计划未变，后端能力兼容。
- 返回保证：逐项完成/待办，未完成页不发布完整水位。
- 调用：G03.read；index adapters；ExecutionControl.reserve。
- 主要错误：INDEX_PENDING, BASIS_CHANGED, PARTIAL_FAILURE。

## G05 候选召回

实际范围、命中表示和通道诊断贯穿回执。

实现落点（待拆分/适配）：`automation/scripts/memory/search.py; automation/scripts/retrieval.py; automation/scripts/qdrant_backend.py`。

### RecallProvider.capabilities

```python
RecallProvider.capabilities(ctx: t.CallContext) -> t.Outcome[t.ProviderCapabilities]
```

- 抽象判断：保留：支持部分能力的后端可被发现。
- 前置条件：装配的provider身份/版本存在。
- 返回保证：真实通道、表示、过滤、语法和取消能力。
- 调用：configured backend。
- 主要错误：UNSUPPORTED。

### RecallProvider.recall

```python
RecallProvider.recall(request: t.RecallRequest, ctx: t.CallContext) -> t.Outcome[t.CandidateBatch]
```

- 抽象判断：保留：词法/向量/图召回统一边界。
- 前置条件：硬过滤可满足，candidate_limit不超本阶段额度。
- 返回保证：候选保留内容/表示双身份、分数含义、水位与续页。
- 调用：G04.status；backend；G12.authorize。
- 主要错误：UNSUPPORTED, INDEX_STALE, BUDGET_EXHAUSTED。

## G06 去重、融合与排序

相关性不替代证据准入；输入正文有界、无隐藏召回。

实现落点（待拆分/适配）：`automation/scripts/memory/search.py; automation/scripts/retrieval_interfaces.py`。

### CandidateDeduplicator.deduplicate

```python
CandidateDeduplicator.deduplicate(batches: tuple[t.CandidateBatch, ...], ctx: t.CallContext) -> t.Outcome[t.CandidateBatch]
```

- 抽象判断：保留：同源多表示需要归并。
- 前置条件：输入固定身份和哈希一致；不能用标题代替身份。
- 返回保证：合并同版命中并保留所有通道依据、遗漏和水位。
- 调用：no recall or writes。
- 主要错误：VERSION_MISMATCH, INVALID_ARGUMENT。

### FusionStrategy.fuse

```python
FusionStrategy.fuse(query: t.QuerySpec, batch: t.CandidateBatch, ctx: t.CallContext) -> t.Outcome[t.RankedBatch]
```

- 抽象判断：保留：融合方法和参数需要替换。
- 前置条件：去重候选及排名/分数含义可用。
- 返回保证：输出融合排名并保留候选来源。
- 调用：no source writes。
- 主要错误：INVALID_ARGUMENT, UNSUPPORTED。

### Reranker.rerank

```python
Reranker.rerank(query: t.QuerySpec, ranked: t.RankedBatch, texts: tuple[t.TextSlice, ...], ctx: t.CallContext) -> t.Outcome[t.RankedBatch]
```

- 抽象判断：保留：昂贵相关性模型可替换。
- 前置条件：明确提供所需TextSlice，模型额度足够。
- 返回保证：仅在输入候选中重排；模型失败与缺正文可见。
- 调用：ExecutionControl.reserve；configured model。
- 主要错误：BUDGET_EXHAUSTED, PARTIAL_FAILURE, UNSUPPORTED。

### DiversitySelector.select

```python
DiversitySelector.select(query: t.QuerySpec, ranked: t.RankedBatch, limit: int, ctx: t.CallContext) -> t.Outcome[t.RankedBatch]
```

- 抽象判断：保留：最终数量与覆盖偏好独立。
- 前置条件：limit不超请求，输入已满足当前准入要求。
- 返回保证：选择输入子集，保留次序依据和未选原因。
- 调用：no recall or writes。
- 主要错误：INVALID_ARGUMENT。

### RankingPipeline.rank

```python
RankingPipeline.rank(request: t.RankingRequest, ctx: t.CallContext) -> t.Outcome[t.RankedBatch]
```

- 抽象判断：保留：上层一次调用排序流程。
- 前置条件：批次和文本固定，ranking策略已注册。
- 返回保证：去重/融合/重排/多样性结果和阶段缺口不丢失。
- 调用：CandidateDeduplicator.deduplicate；FusionStrategy.fuse；Reranker.rerank；DiversitySelector.select。
- 主要错误：UNSUPPORTED, BUDGET_EXHAUSTED, PARTIAL_FAILURE。

## G07 关系导航

导航采纳与科学支持分开，路径固定且展开有界。

实现落点（待拆分/适配）：`automation/scripts/memory/associations.py; automation/scripts/memory/lineage.py`。

### RelationNavigator.neighbors

```python
RelationNavigator.neighbors(request: t.GraphRequest, ctx: t.CallContext) -> t.Outcome[t.GraphSlice]
```

- 抽象判断：保留：图浏览和图召回复用有界邻居。
- 前置条件：种子可见，方向/关系类型/节点边数上限明确。
- 返回保证：有类型邻居和固定来源，未遍历部分显式返回。
- 调用：G12.authorize；graph adapter。
- 主要错误：ACCESS_DENIED, BUDGET_EXHAUSTED, INDEX_STALE。

### RelationNavigator.paths

```python
RelationNavigator.paths(request: t.GraphRequest, ctx: t.CallContext) -> t.Outcome[t.GraphSlice]
```

- 抽象判断：保留：解释为何关联到某条知识。
- 前置条件：种子和目标均可读；累计跳数不重置。
- 返回保证：返回可回读的有序边路径和差异/缺口。
- 调用：RelationNavigator.neighbors。
- 主要错误：NOT_FOUND, BUDGET_EXHAUSTED, INDEX_STALE。

### RelationNavigator.suggest_links

```python
RelationNavigator.suggest_links(request: t.GraphRequest, strategy: t.StrategyRef, ctx: t.CallContext) -> t.Outcome[t.GraphSlice]
```

- 抽象判断：保留：类比策略可替换且不直接采纳。
- 前置条件：固定两端与策略版本可用。
- 返回保证：所有新建议保持proposed，科学支持不由相似度创建。
- 调用：G01.read；RelationNavigator.neighbors；ExecutionControl.reserve。
- 主要错误：UNSUPPORTED, BUDGET_EXHAUSTED。

## G08 渐进检索编排

拥有计划和续接状态，范围、排除及预算不丢失。

实现落点（待拆分/适配）：`automation/scripts/memory/search.py; automation/scripts/memory/packets.py; automation/scripts/context_engine.py`。

### ExpansionPolicy.next_step

```python
ExpansionPolicy.next_step(progress: t.SearchProgress, capabilities: tuple[t.ProviderCapabilities, ...], ctx: t.CallContext) -> t.Outcome[t.ExpansionStep]
```

- 抽象判断：保留：扩展策略与执行编排分离。
- 前置条件：已执行步骤/缺口/预算真实；原始上限不变。
- 返回保证：返回一个可审查动作或明确停止原因。
- 调用：capability descriptions only。
- 主要错误：UNSUPPORTED, BUDGET_EXHAUSTED。

### SearchCoordinator.search

```python
SearchCoordinator.search(query: t.QuerySpec, context: t.ContextOptions | None, ctx: t.CallContext) -> t.Outcome[t.SearchReceipt]
```

- 抽象判断：保留：单一查询入口保留约束和诊断。
- 前置条件：规范请求、授权、策略和额度可用。
- 返回保证：保存实际步骤/水位/停止原因及可续接状态。
- 调用：G12；G03；G04；G05；G06；G07；G09；ExpansionPolicy.next_step。
- 主要错误：INVALID_ARGUMENT, UNSUPPORTED, BUDGET_EXHAUSTED, PARTIAL_FAILURE。

### SearchCoordinator.resume

```python
SearchCoordinator.resume(request: t.ResumeRequest, ctx: t.CallContext) -> t.Outcome[t.SearchReceipt]
```

- 抽象判断：保留：真正续查而非重新开始扩大limit。
- 前置条件：游标绑定原请求/范围/预算；当前授权再次通过。
- 返回保证：继承排除与已花费额度；换版本或追加预算显式记录。
- 调用：saved search state；SearchCoordinator.search。
- 主要错误：BASIS_CHANGED, ACCESS_DENIED, IDEMPOTENCY_MISMATCH。

## G09 上下文组装

展开固定候选、补定义和边界，缺口交还编排器。

实现落点（待拆分/适配）：`automation/scripts/memory/packets.py; automation/scripts/memory/technical_units.py`。

### ContextBuilder.build

```python
ContextBuilder.build(request: t.ContextRequest, ctx: t.CallContext) -> t.Outcome[t.ContextPacket]
```

- 抽象判断：保留：召回与实际材料包生成分离。
- 前置条件：选择的Ref固定，预算/用途/表示明确。
- 返回保证：补齐必要定义，保留限制与遗漏，不隐藏二次召回。
- 调用：G01.read；G03.read；G12.assess。
- 主要错误：SOURCE_MISSING, VERSION_MISMATCH, BUDGET_EXHAUSTED。

## G10 阅读视图

读取已有正文和结构，不隐式生成新结论。

实现落点（待拆分/适配）：`automation/scripts/memory/documents.py; automation/scripts/memory/document.py; automation/scripts/memory/raw_materials.py`。

### ReadViewService.list

```python
ReadViewService.list(scope: t.CorpusScope, page: t.PageRequest, ctx: t.CallContext) -> t.Outcome[t.Page[t.ContentMetadata]]
```

- 抽象判断：保留：发现已有文稿/视图。
- 前置条件：scope与分页明确。
- 返回保证：列出已有可读视图及版本，不生成新文稿。
- 调用：G01.list_page；G12.authorize。
- 主要错误：ACCESS_DENIED, BASIS_CHANGED。

### ReadViewService.render

```python
ReadViewService.render(request: t.ViewRequest, ctx: t.CallContext) -> t.Outcome[t.ReadView]
```

- 抽象判断：保留：多阅读方式统一固定依据。
- 前置条件：视图类型受支持，来源范围可读。
- 返回保证：返回已有正文/图结构及缺口，生成新解释另走整理。
- 调用：G01.read；G07.neighbors；G12.assess。
- 主要错误：UNSUPPORTED, SOURCE_MISSING, BUDGET_EXHAUSTED。

## G11 策略整理

按策略正式修订；提交、复核、索引和恢复分别记账。

实现落点（待拆分/适配）：`automation/scripts/memory/consolidation.py; automation/scripts/memory/summaries.py`。

### MaintenancePlanner.plan

```python
MaintenancePlanner.plan(request: t.MaintenanceRequest, ctx: t.CallContext) -> t.Outcome[t.MaintenancePlan]
```

- 抽象判断：保留：正式修改先形成具体计划。
- 前置条件：策略版本、允许动作、依据和目标范围明确。
- 返回保证：按owner拆分固定批次与影响/复核/恢复要求。
- 调用：G01；G12；ImpactAnalyzer.affected。
- 主要错误：ACCESS_DENIED, BASIS_CHANGED, UNSUPPORTED。

### MaintenanceExecutor.execute

```python
MaintenanceExecutor.execute(plan: t.MaintenancePlan, resume: t.Cursor | None, ctx: t.CallContext) -> t.Outcome[t.MaintenanceReceipt]
```

- 抽象判断：保留：有状态、有恢复的正式整理。
- 前置条件：计划获准且输入未变，重试沿用计划/请求身份。
- 返回保证：逐owner记录提交、新复核、索引及待办；部分成功不冒充原子性。
- 调用：G02；G03；G04；G12；saved maintenance state。
- 主要错误：CONFLICT, PARTIAL_FAILURE, IDEMPOTENCY_MISMATCH。

### MaintenanceExecutor.status

```python
MaintenanceExecutor.status(plan_id: str, ctx: t.CallContext) -> t.Outcome[t.MaintenanceReceipt]
```

- 抽象判断：保留：续接先查看确实完成的工作。
- 前置条件：plan_id可访问。
- 返回保证：返回已保存状态，不自行执行下一步。
- 调用：saved maintenance state。
- 主要错误：NOT_FOUND, ACCESS_DENIED。

## G12 证据、复核与影响

实际授权和读时有效性由专门规则判定。

实现落点（待拆分/适配）：`automation/scripts/memory/evidence_adapter.py; automation/scripts/memory/impact.py; automation/scripts/evidence.py`。

### EvidencePolicy.authorize

```python
EvidencePolicy.authorize(scope: t.CorpusScope, action: Literal['read', 'query', 'write', 'review', 'maintain'], ctx: t.CallContext) -> t.Outcome[t.AccessDecision]
```

- 抽象判断：保留：可信范围不能由下游自行决定。
- 前置条件：可信调用上下文存在，动作明确。
- 返回保证：得到授权范围交集，未知权限按拒绝处理。
- 调用：trusted access adapter。
- 主要错误：ACCESS_DENIED, INVALID_ARGUMENT。

### EvidencePolicy.assess

```python
EvidencePolicy.assess(refs: tuple[t.FixedRef, ...], purpose: Literal['exploration', 'formal', 'audit'], applicability: t.Applicability | None, basis: t.ReadBasis, ctx: t.CallContext) -> t.Outcome[tuple[t.EvidenceAssessment, ...]]
```

- 抽象判断：保留：复核/有效性与相似性排序分离。
- 前置条件：目标固定，用途/适用域和读取basis明确。
- 返回保证：返回逐目标/claim读时评估及未解决部分。
- 调用：G01.read；evidence adapter。
- 主要错误：SOURCE_MISSING, VERSION_MISMATCH, BASIS_CHANGED。

### ReviewService.append_review

```python
ReviewService.append_review(command: t.ReviewCommand, ctx: t.CallContext) -> t.Outcome[t.EvidenceAssessment]
```

- 抽象判断：保留：新内容需要新复核历史。
- 前置条件：目标与owner HEAD未变，方法与依据满足实际规则。
- 返回保证：追加真实复核并返回状态，不覆写旧review。
- 调用：G02.commit；G12.assess。
- 主要错误：CONFLICT, INVALID_SCHEMA, ACCESS_DENIED。

### ImpactAnalyzer.affected

```python
ImpactAnalyzer.affected(refs: tuple[t.FixedRef, ...], scope: t.CorpusScope, page: t.PageRequest, ctx: t.CallContext) -> t.Outcome[t.Page[t.FixedRef]]
```

- 抽象判断：保留：更改后找已登记下游。
- 前置条件：变化Ref与可读范围固定。
- 返回保证：分页返回已知依赖，未登记关系不宣称不存在。
- 调用：G01；registered relation adapter。
- 主要错误：SOURCE_MISSING, BASIS_CHANGED。

## X01 共享执行控制

实际执行方预订/结算，父流水线不重复扣费；不构成第十三组业务功能。

实现落点（待拆分/适配）：`new internal execution control adapter`。

### ExecutionControl.reserve

```python
ExecutionControl.reserve(ceiling: t.BudgetUsage, ctx: t.CallContext) -> t.Outcome[t.BudgetReservation]
```

- 抽象判断：保留：工作开始前防止预算超支。
- 前置条件：成本上界非负，使用原操作账本。
- 返回保证：原子预约额度；无法保证上界时拒绝。
- 调用：shared execution ledger。
- 主要错误：BUDGET_EXHAUSTED, CANCELLED。

### ExecutionControl.settle

```python
ExecutionControl.settle(reservation: t.BudgetReservation, actual: t.BudgetUsage, ctx: t.CallContext) -> t.Outcome[t.BudgetUsage]
```

- 抽象判断：保留：真实消耗与未用额度分别处理。
- 前置条件：预约身份与原账本匹配，结算幂等。
- 返回保证：累计真实消耗并释放余额，父子层不重复扣费。
- 调用：shared execution ledger。
- 主要错误：INVALID_ARGUMENT, IDEMPOTENCY_MISMATCH。

### ExecutionControl.check_cancelled

```python
ExecutionControl.check_cancelled(ctx: t.CallContext) -> t.Outcome[bool]
```

- 抽象判断：保留：统一取消检查而非各引擎猜测。
- 前置条件：取消句柄绑定原操作。
- 返回保证：返回当前取消标志，不能宣称不支持的强制终止已完成。
- 调用：shared cancellation token。
- 主要错误：ACCESS_DENIED。

## 已遍历但不单独增加的函数

| 候选 | 处理 | 理由 |
|---|---|---|
| search_success_experience / search_certain_fact | merge | 归入 QuerySpec.scope.facets；避免每个标签新增一个函数。 |
| search_L0 / search_L1 / search_L4 | merge | 层级由 CorpusScope.layers，表示由 RepresentationSpec 选择。 |
| fast_search / slow_search | reject | 材料抽象程度与速度没有固定等价关系，预算及实际耗时单独表达。 |
| get_one / get_many 两套读取 | merge | 只保留批量 read/describe；单条是长度为1的批次。 |
| rebuild_index / retry_index 多套结果类型 | merge | G04 plan.mode 区分，统一执行回执及水位。 |
| delete_everything / 删除原件 | reject | 普通分级CRUD不授予原始数据删除权，规范撤回/归档用明确动作。 |
| auto_accept_from_similarity | reject | 关联或排名不能代替证据复核。 |
| summarize_inside_read | reject | 新解释通过 G11/G02 保存；纯读取不隐藏调用模型写正式内容。 |
| one_repository_per_L_level | reject | 重复身份、事务与版本维护，层级差异由内容schema与规则表达。 |
| distributed_global_transaction | reserve | 当前单owner原子性；跨owner显式部分完成，未实现全局事务不返回成功。 |
| sparse / multi_vector / temporal_graph implementations | reserve | 通过能力、策略和IndexKey预留；具体后端尚待评测与适配。 |
| frontend_refresh_interfaces | reuse | 沿用现有工作台动作，由应用适配新契约；本轮不更改页面。 |
