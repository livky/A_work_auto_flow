# 数据结构字段目录

由 contract_types.py 生成。全部字段显式传入；业务空值、单位、状态和版本规则见 SPEC.md。DraftDocument.body_json 复用注册的业务 schema，其他核心请求不接受无约束扩展字典。

## StrategyRef

注册的策略身份；后端私有参数由装配配置管理，不透传任意 SQL。

| 字段 | 类型 |
|---|---|
| name | `str` |
| version | `str` |

## FixedRef

固定内容身份；关系语义另存 EvidenceLink，hash 不等于证据已复核。

| 字段 | 类型 |
|---|---|
| target_kind | `Literal['record', 'owner', 'claim', 'file', 'representation']` |
| target_id | `str` |
| revision | `int \| None` |
| sha256 | `Sha256` |
| locator | `str \| None` |

## LegacyRef

现有六字段 Ref 的兼容输入；不完整 SHA 只能由实际回源核验补齐。

| 字段 | 类型 |
|---|---|
| target_kind | `Literal['record', 'owner', 'claim', 'file']` |
| target_id | `str` |
| revision | `int \| None` |
| sha256 | `Sha256 \| None` |
| locator | `str \| None` |
| relation | `str` |

## EvidenceLink

| 字段 | 类型 |
|---|---|
| ref | `FixedRef` |
| relation | `RelationKind` |

## OwnerHead

| 字段 | 类型 |
|---|---|
| owner_id | `OwnerId` |
| commit_id | `CommitId \| None` |

## ReadBasis

所用固定依据和真实读一致性；跨 owner 乐观检查不是全局快照。

| 字段 | 类型 |
|---|---|
| basis_id | `str` |
| owner_heads | `tuple[OwnerHead, ...]` |
| source_refs | `tuple[FixedRef, ...]` |
| observed_at | `UtcTime` |
| consistency | `Literal['fixed_refs', 'single_owner_snapshot', 'cross_owner_optimistic']` |

## TimeWindow

| 字段 | 类型 |
|---|---|
| field | `Literal['recorded_at', 'occurred_at', 'valid_at']` |
| start_inclusive | `UtcTime \| None` |
| end_exclusive | `UtcTime \| None` |

## Applicability

业务适用域；不能代替语料 owner 筛选或授权上下文。

| 字段 | 类型 |
|---|---|
| description | `str` |
| conditions | `tuple[str, ...]` |
| exclusions | `tuple[str, ...]` |
| valid_from | `UtcTime \| None` |
| valid_until | `UtcTime \| None` |
| subject_versions | `tuple[FixedRef, ...]` |

## ConfidenceAssessment

| 字段 | 类型 |
|---|---|
| target | `FixedRef` |
| level | `ConfidenceLevel` |
| assessed_by | `str` |
| method | `StrategyRef` |
| basis | `tuple[EvidenceLink, ...]` |
| applicability | `Applicability` |
| calibrated_probability | `float \| None` |
| calibration_ref | `FixedRef \| None` |

## AttemptAssessment

| 字段 | 类型 |
|---|---|
| attempt_ref | `FixedRef` |
| outcome | `AttemptOutcome` |
| conditions | `tuple[str, ...]` |

## KnowledgeFacets

内容描述；roles/outcomes 可多值，缺少信息不自动补成成功或确定。

| 字段 | 类型 |
|---|---|
| roles | `tuple[KnowledgeRole, ...]` |
| principle_kind | `Literal['definition', 'mathematical_axiom', 'derived_invariant', 'physical_law_model', 'engineering_assumption'] \| None` |
| attempts | `tuple[AttemptAssessment, ...]` |
| applicability | `Applicability` |
| counterexamples | `tuple[EvidenceLink, ...]` |
| confidence | `tuple[ConfidenceAssessment, ...]` |
| classification_basis | `tuple[EvidenceLink, ...]` |

## EvidenceAssessment

由证据服务计算的读时状态；不得信任索引或调用方自报的 accepted。

| 字段 | 类型 |
|---|---|
| target | `FixedRef` |
| review_state | `ReviewState` |
| validity | `ValidityState` |
| applicability | `Applicability` |
| assessed_at | `UtcTime` |
| review_refs | `tuple[FixedRef, ...]` |
| evaluated_claim_refs | `tuple[FixedRef, ...]` |
| unresolved_claim_refs | `tuple[FixedRef, ...]` |
| reasons | `tuple[str, ...]` |

## FacetFilter

| 字段 | 类型 |
|---|---|
| roles | `tuple[KnowledgeRole, ...] \| None` |
| outcomes | `tuple[AttemptOutcome, ...] \| None` |
| review_states | `tuple[ReviewState, ...] \| None` |
| validities | `tuple[ValidityState, ...] \| None` |
| confidence_levels | `tuple[ConfidenceLevel, ...] \| None` |
| applicability | `Applicability \| None` |
| include_unknown | `bool` |

## CorpusScope

硬语料约束；include/exclude 按身份匹配，exclude 始终优先。

| 字段 | 类型 |
|---|---|
| owner_ids | `tuple[OwnerId, ...] \| None` |
| kinds | `tuple[str, ...] \| None` |
| layers | `tuple[Layer, ...] \| None` |
| source_ids | `tuple[str, ...] \| None` |
| time_window | `TimeWindow \| None` |
| facets | `FacetFilter \| None` |
| include_refs | `tuple[FixedRef, ...]` |
| exclude_ids | `tuple[str, ...]` |

## RepresentationSpec

具名表示可扩展；搜索表示和结果视图分别选择，不映射为速度等级。

| 字段 | 类型 |
|---|---|
| keys | `tuple[RepresentationKey, ...]` |
| fallback_order | `tuple[RepresentationKey, ...]` |
| missing | `Literal['reject', 'skip', 'fallback']` |
| allow_build | `bool` |

## FreshnessPolicy

| 字段 | 类型 |
|---|---|
| mode | `Literal['fixed', 'current', 'allow_stale']` |
| allow_index_repair | `bool` |
| max_staleness_seconds | `float \| None` |

## BudgetLimits

全部是硬上限；不设无限默认。token 上限依赖指定 tokenizer。

| 字段 | 类型 |
|---|---|
| deadline | `UtcTime` |
| max_candidates | `int` |
| max_rerank | `int` |
| max_graph_nodes | `int` |
| max_graph_edges | `int` |
| max_hops | `int` |
| max_read_bytes | `int` |
| max_model_calls | `int` |
| max_model_input_tokens | `int` |
| max_model_output_tokens | `int` |
| max_context_chars | `int` |
| tokenizer | `StrategyRef \| None` |

## BudgetUsage

| 字段 | 类型 |
|---|---|
| elapsed_ms | `float` |
| candidates | `int` |
| reranked | `int` |
| graph_nodes | `int` |
| graph_edges | `int` |
| read_bytes | `int` |
| model_calls | `int` |
| model_input_tokens | `int` |
| model_output_tokens | `int` |
| context_chars | `int` |

## CallContext

由可信应用装配；恢复查询沿用预算账本，不能用新调用 ID 重置额度。

| 字段 | 类型 |
|---|---|
| call_id | `str` |
| root_operation_id | `str` |
| access_handle | `str` |
| budget_handle | `str` |
| cancellation_handle | `str` |

## Issue

| 字段 | 类型 |
|---|---|
| code | `str` |
| message | `str` |
| affected_refs | `tuple[FixedRef, ...]` |
| retry | `Literal['never', 'same_request', 'replan', 'after_external_change']` |

## Outcome

成功/部分/拒绝/失败分开；拒绝无数据，部分结果必须列出缺口。

| 字段 | 类型 |
|---|---|
| status | `Literal['ok', 'partial', 'rejected', 'failed']` |
| value | `T \| None` |
| issues | `tuple[Issue, ...]` |
| usage | `BudgetUsage` |

## PageRequest

| 字段 | 类型 |
|---|---|
| limit | `int` |
| cursor | `Cursor \| None` |

## Page

| 字段 | 类型 |
|---|---|
| items | `tuple[T, ...]` |
| next_cursor | `Cursor \| None` |
| basis | `ReadBasis` |

## ContentMetadata

| 字段 | 类型 |
|---|---|
| ref | `FixedRef` |
| owner_id | `OwnerId` |
| kind | `str` |
| layer | `Layer \| None` |
| title | `str` |
| facets | `KnowledgeFacets` |

## TextSlice

| 字段 | 类型 |
|---|---|
| ref | `FixedRef` |
| markdown | `str` |
| required_refs | `tuple[FixedRef, ...]` |
| complete | `bool` |

## ReadRequest

| 字段 | 类型 |
|---|---|
| refs | `tuple[FixedRef, ...]` |
| scope | `CorpusScope` |
| representation | `RepresentationSpec` |
| freshness | `FreshnessPolicy` |

## ReadBatch

| 字段 | 类型 |
|---|---|
| items | `tuple[TextSlice, ...]` |
| basis | `ReadBasis` |
| missing | `tuple[Issue, ...]` |

## DraftDocument

复用注册的内容 schema，不在接口包复制十五类业务 payload。

body_json 必须通过 schema_key 对应的固定版本校验；不接受任意自由字典。
新 v3 内容目前映射 memory-v3.schema.json 的 Draft/类型校验入口。

| 字段 | 类型 |
|---|---|
| owner_id | `OwnerId` |
| schema_key | `str` |
| schema_version | `int` |
| body_json | `str` |

## PutChange

| 字段 | 类型 |
|---|---|
| client_key | `str` |
| previous | `FixedRef \| None` |
| draft | `DraftDocument` |
| reason | `str` |

## RetireChange

| 字段 | 类型 |
|---|---|
| target | `FixedRef` |
| action | `Literal['archive', 'retract', 'supersede']` |
| replacement | `FixedRef \| None` |
| reason | `str` |

## ChangeBatch

| 字段 | 类型 |
|---|---|
| request_id | `str` |
| owner_id | `OwnerId` |
| expected_head | `CommitId \| None` |
| basis | `ReadBasis` |
| changes | `tuple[PutChange \| RetireChange, ...]` |

## ValidationReceipt

| 字段 | 类型 |
|---|---|
| batch_sha256 | `Sha256` |
| validator | `StrategyRef` |
| validated_basis | `ReadBasis` |
| validation_handle | `str` |

## CommittedChange

| 字段 | 类型 |
|---|---|
| client_key | `str` |
| previous | `FixedRef \| None` |
| current | `FixedRef \| None` |
| action | `Literal['put', 'archive', 'retract', 'supersede', 'restore']` |

## CommitReceipt

| 字段 | 类型 |
|---|---|
| request_id | `str` |
| owner_id | `OwnerId` |
| commit_id | `CommitId` |
| changes | `tuple[CommittedChange, ...]` |
| change_cursor | `Cursor` |
| follow_up_required | `tuple[Literal['index', 'review', 'document_impact'], ...]` |

## RestoreRequest

| 字段 | 类型 |
|---|---|
| request_id | `str` |
| owner_id | `OwnerId` |
| expected_head | `CommitId` |
| restore_refs | `tuple[FixedRef, ...]` |
| reason | `str` |

## Representation

| 字段 | 类型 |
|---|---|
| ref | `FixedRef` |
| key | `RepresentationKey` |
| represented_refs | `tuple[FixedRef, ...]` |
| authority | `Literal['canonical', 'derived']` |
| generator | `StrategyRef` |
| state | `Literal['available', 'stale']` |
| contributors | `tuple[FixedRef, ...]` |

## RepresentationAvailability

| 字段 | 类型 |
|---|---|
| key | `RepresentationKey` |
| content_ref | `FixedRef` |
| state | `Literal['available', 'stale', 'missing', 'unsupported']` |
| representation | `Representation \| None` |
| reason | `str \| None` |

## RepresentationPlan

| 字段 | 类型 |
|---|---|
| plan_id | `str` |
| scope | `CorpusScope` |
| source_refs | `tuple[FixedRef, ...]` |
| requested | `RepresentationSpec` |
| basis | `ReadBasis` |
| builder | `StrategyRef` |

## RepresentationBuild

| 字段 | 类型 |
|---|---|
| derived | `tuple[Representation, ...]` |
| content_proposals | `tuple[DraftDocument, ...]` |
| basis | `ReadBasis` |

## IndexKey

| 字段 | 类型 |
|---|---|
| channel | `Channel` |
| representation | `RepresentationKey` |
| encoder | `StrategyRef \| None` |
| analyzer | `StrategyRef \| None` |
| dimension | `int \| None` |

## Watermark

| 字段 | 类型 |
|---|---|
| index | `IndexKey` |
| covered_basis | `ReadBasis` |
| cursor | `Cursor \| None` |
| coverage | `Literal['complete', 'partial', 'unknown']` |

## ChangeEvent

| 字段 | 类型 |
|---|---|
| event_id | `str` |
| owner_id | `OwnerId` |
| commit_id | `CommitId` |
| previous_refs | `tuple[FixedRef, ...]` |
| current_refs | `tuple[FixedRef, ...]` |

## IndexPlan

| 字段 | 类型 |
|---|---|
| plan_id | `str` |
| mode | `Literal['incremental', 'rebuild', 'repair']` |
| index | `IndexKey` |
| scope | `CorpusScope` |
| changes | `tuple[ChangeEvent, ...]` |
| source_refs | `tuple[FixedRef, ...]` |
| target_basis | `ReadBasis` |
| from_cursor | `Cursor \| None` |
| next_scan_cursor | `Cursor \| None` |

## IndexReceipt

| 字段 | 类型 |
|---|---|
| plan_id | `str` |
| completed_events | `tuple[str, ...]` |
| pending_events | `tuple[str, ...]` |
| watermark | `Watermark` |
| resume_cursor | `Cursor \| None` |

## ProviderCapabilities

| 字段 | 类型 |
|---|---|
| provider | `StrategyRef` |
| channels | `tuple[Channel, ...]` |
| representations | `tuple[RepresentationKey, ...]` |
| filter_fields | `tuple[str, ...]` |
| query_dialects | `tuple[Literal['plain', 'phrase', 'boolean'], ...]` |
| freshness_modes | `tuple[Literal['fixed', 'current', 'allow_stale'], ...]` |
| supports_hard_cancel | `bool` |
| supports_filter_pushdown | `bool` |

## QuerySpec

| 字段 | 类型 |
|---|---|
| text | `str` |
| dialect | `Literal['plain', 'phrase', 'boolean']` |
| seeds | `tuple[FixedRef, ...]` |
| scope | `CorpusScope` |
| scope_ceiling | `CorpusScope` |
| representations | `RepresentationSpec` |
| channels | `tuple[Channel, ...]` |
| purpose | `Literal['exploration', 'formal', 'audit']` |
| applicability | `Applicability \| None` |
| freshness | `FreshnessPolicy` |
| limits | `BudgetLimits` |
| planner | `StrategyRef` |
| ranking | `StrategyRef` |
| result_limit | `int` |
| expansion_axes | `tuple[Literal['owners', 'time', 'representations', 'channels'], ...]` |

## ChannelHit

| 字段 | 类型 |
|---|---|
| channel | `Channel` |
| provider | `StrategyRef` |
| representation_ref | `FixedRef` |
| rank | `int` |
| raw_score | `float \| None` |
| score_meaning | `str` |
| matched_text | `tuple[TextSlice, ...]` |

## Candidate

| 字段 | 类型 |
|---|---|
| content | `ContentMetadata` |
| hits | `tuple[ChannelHit, ...]` |
| evidence_state | `EvidenceAssessment` |

## CandidateBatch

| 字段 | 类型 |
|---|---|
| candidates | `tuple[Candidate, ...]` |
| basis | `ReadBasis` |
| watermarks | `tuple[Watermark, ...]` |
| omitted | `tuple[Issue, ...]` |
| next_cursor | `Cursor \| None` |

## RecallRequest

| 字段 | 类型 |
|---|---|
| query | `QuerySpec` |
| channel | `Channel` |
| candidate_limit | `int` |
| cursor | `Cursor \| None` |

## RankingRequest

| 字段 | 类型 |
|---|---|
| query | `QuerySpec` |
| batch | `CandidateBatch` |
| texts | `tuple[TextSlice, ...]` |
| limit | `int` |

## RankedCandidate

| 字段 | 类型 |
|---|---|
| candidate | `Candidate` |
| position | `int` |
| ranking_score | `float \| None` |
| explanation | `tuple[str, ...]` |

## RankedBatch

| 字段 | 类型 |
|---|---|
| items | `tuple[RankedCandidate, ...]` |
| basis | `ReadBasis` |
| watermarks | `tuple[Watermark, ...]` |
| omitted | `tuple[Issue, ...]` |

## GraphEdge

| 字段 | 类型 |
|---|---|
| edge_id | `str` |
| source | `FixedRef` |
| target | `FixedRef` |
| kind | `RelationKind` |
| evidence | `tuple[EvidenceLink, ...]` |
| state | `Literal['proposed', 'accepted_navigation', 'verified_claim', 'stale', 'retracted']` |
| differences | `tuple[str, ...]` |

## GraphRequest

| 字段 | 类型 |
|---|---|
| seeds | `tuple[FixedRef, ...]` |
| targets | `tuple[FixedRef, ...]` |
| scope | `CorpusScope` |
| edge_kinds | `tuple[RelationKind, ...]` |
| direction | `Literal['out', 'in', 'both']` |
| max_hops | `int` |
| max_nodes | `int` |
| max_edges | `int` |
| cursor | `Cursor \| None` |

## GraphSlice

| 字段 | 类型 |
|---|---|
| nodes | `tuple[ContentMetadata, ...]` |
| edges | `tuple[GraphEdge, ...]` |
| paths | `tuple[tuple[str, ...], ...]` |
| basis | `ReadBasis` |
| next_cursor | `Cursor \| None` |
| omitted | `tuple[Issue, ...]` |

## ContextOptions

| 字段 | 类型 |
|---|---|
| representation | `RepresentationSpec` |
| max_chars | `int` |
| include_required_definitions | `bool` |

## ContextRequest

| 字段 | 类型 |
|---|---|
| refs | `tuple[FixedRef, ...]` |
| scope | `CorpusScope` |
| purpose | `Literal['exploration', 'formal', 'audit']` |
| applicability | `Applicability \| None` |
| basis | `ReadBasis` |
| freshness | `FreshnessPolicy` |
| options | `ContextOptions` |

## ContextPacket

| 字段 | 类型 |
|---|---|
| packet_id | `str` |
| items | `tuple[TextSlice, ...]` |
| basis | `ReadBasis` |
| selected_refs | `tuple[FixedRef, ...]` |
| omitted | `tuple[Issue, ...]` |
| actual_chars | `int` |

## ExpansionStep

| 字段 | 类型 |
|---|---|
| action | `Literal['recall', 'navigate', 'deepen', 'stop']` |
| scope | `CorpusScope` |
| representation | `RepresentationSpec` |
| channel | `Channel \| None` |
| refs | `tuple[FixedRef, ...]` |
| reason | `str` |
| stop_reason | `StopReason \| None` |

## SearchProgress

| 字段 | 类型 |
|---|---|
| query | `QuerySpec` |
| basis | `ReadBasis` |
| visited_refs | `tuple[FixedRef, ...]` |
| steps | `tuple[ExpansionStep, ...]` |
| last_batch | `RankedBatch \| None` |
| gaps | `tuple[Issue, ...]` |
| usage | `BudgetUsage` |

## SearchReceipt

| 字段 | 类型 |
|---|---|
| search_id | `str` |
| normalized_query | `QuerySpec` |
| ranked | `RankedBatch` |
| progress | `SearchProgress` |
| context | `ContextPacket \| None` |
| next_cursor | `Cursor \| None` |
| stop_reason | `StopReason` |
| unavailable_channels | `tuple[Channel, ...]` |

## ResumeRequest

| 字段 | 类型 |
|---|---|
| cursor | `Cursor` |
| version_action | `Literal['keep_fixed', 'restart_on_current']` |
| additional_budget | `BudgetLimits \| None` |

## ViewRequest

| 字段 | 类型 |
|---|---|
| view | `Literal['full', 'layers', 'digests', 'research_process', 'research_report', 'relation_graph']` |
| refs | `tuple[FixedRef, ...]` |
| scope | `CorpusScope` |
| basis | `ReadBasis` |
| max_chars | `int` |

## ReadView

| 字段 | 类型 |
|---|---|
| view | `str` |
| text | `tuple[TextSlice, ...]` |
| graph | `GraphSlice \| None` |
| basis | `ReadBasis` |
| omitted | `tuple[Issue, ...]` |

## MaintenanceRequest

| 字段 | 类型 |
|---|---|
| mode | `Literal['organize', 'recover']` |
| scope | `CorpusScope` |
| policy | `StrategyRef` |
| changed_refs | `tuple[FixedRef, ...]` |
| basis | `ReadBasis` |

## ReviewRequirement

| 字段 | 类型 |
|---|---|
| owner_id | `OwnerId` |
| changed_client_keys | `tuple[str, ...]` |
| previous_refs | `tuple[FixedRef, ...]` |
| method | `StrategyRef` |

## MaintenancePlan

| 字段 | 类型 |
|---|---|
| plan_id | `str` |
| request | `MaintenanceRequest` |
| changes | `tuple[ChangeBatch, ...]` |
| review_targets | `tuple[ReviewRequirement, ...]` |
| impacted_refs | `tuple[FixedRef, ...]` |
| recovery_refs | `tuple[FixedRef, ...]` |

## MaintenanceReceipt

| 字段 | 类型 |
|---|---|
| plan_id | `str` |
| commits | `tuple[CommitReceipt, ...]` |
| pending_owner_ids | `tuple[OwnerId, ...]` |
| review_states | `tuple[EvidenceAssessment, ...]` |
| pending_reviews | `tuple[FixedRef, ...]` |
| index_states | `tuple[Watermark, ...]` |
| resume_cursor | `Cursor \| None` |

## ReviewCommand

| 字段 | 类型 |
|---|---|
| request_id | `str` |
| target | `FixedRef` |
| expected_owner_head | `CommitId \| None` |
| state | `ReviewState` |
| applicability | `Applicability` |
| evidence | `tuple[EvidenceLink, ...]` |
| method | `StrategyRef` |
| reason | `str` |

## AccessDecision

| 字段 | 类型 |
|---|---|
| allowed_scope | `CorpusScope` |
| rejected_ids | `tuple[str, ...]` |
| basis | `ReadBasis` |

## BudgetReservation

| 字段 | 类型 |
|---|---|
| reservation_id | `str` |
| budget_handle | `str` |
| ceiling | `BudgetUsage` |

