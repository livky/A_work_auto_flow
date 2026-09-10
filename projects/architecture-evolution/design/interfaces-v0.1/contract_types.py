"""v0.1 设计契约：语言无关字段的 Python 3.10+ 类型表达。

本文件是可导入、可检查的设计产物，尚未由产品路由/后端使用。
单位、空值、状态约束与错误语义见 SPEC.md；这里不实现算法或静默默认值。
仅依赖标准库。tuple 表示有序不可变集合；可空筛选的 None=不限制，()=空集。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, Literal, NewType, TypeAlias, TypeVar

OwnerId = NewType("OwnerId", str)
RecordId = NewType("RecordId", str)
CommitId = NewType("CommitId", str)
Sha256 = NewType("Sha256", str)
RepresentationKey = NewType("RepresentationKey", str)
Cursor = NewType("Cursor", str)
UtcTime = NewType("UtcTime", str)  # RFC 3339 UTC；不用文件 mtime 猜测业务时间。
Layer: TypeAlias = Literal["L0", "L1", "L2", "L3", "L4"]
KnowledgeRole: TypeAlias = Literal["fact_claim", "insight", "hypothesis", "experience", "method", "principle", "definition", "constraint"]
AttemptOutcome: TypeAlias = Literal["success", "failure", "mixed", "unknown"]
ReviewState: TypeAlias = Literal["not-reviewed", "accepted", "disputed", "retracted", "superseded"]
ValidityState: TypeAlias = Literal["valid", "invalid", "unknown"]
ConfidenceLevel: TypeAlias = Literal["high", "medium", "low", "unknown"]
RelationKind: TypeAlias = Literal["references", "input", "supports", "contradicts", "supersedes", "depends_on", "similar_structure", "same_entity", "mentions"]
Channel: TypeAlias = Literal["identity", "lexical", "dense", "sparse", "graph"]
StopReason: TypeAlias = Literal["sufficient", "exhausted", "no_gain", "budget", "cancelled", "missing_source", "stale", "unsupported", "denied", "error"]
T = TypeVar("T")


@dataclass(frozen=True)
class StrategyRef:
    """注册的策略身份；后端私有参数由装配配置管理，不透传任意 SQL。"""
    name: str
    version: str


@dataclass(frozen=True)
class FixedRef:
    """固定内容身份；关系语义另存 EvidenceLink，hash 不等于证据已复核。"""
    target_kind: Literal["record", "owner", "claim", "file", "representation"]
    target_id: str
    revision: int | None  # record 必须为正整数；原生对象/文件允许仅由 SHA 固定。
    sha256: Sha256
    locator: str | None   # 仅接受已登记且可验证的定位语法，不接受任意读取路径。


@dataclass(frozen=True)
class LegacyRef:
    """现有六字段 Ref 的兼容输入；不完整 SHA 只能由实际回源核验补齐。"""
    target_kind: Literal["record", "owner", "claim", "file"]
    target_id: str
    revision: int | None
    sha256: Sha256 | None
    locator: str | None
    relation: str


@dataclass(frozen=True)
class EvidenceLink:
    ref: FixedRef
    relation: RelationKind


@dataclass(frozen=True)
class OwnerHead:
    owner_id: OwnerId
    commit_id: CommitId | None


@dataclass(frozen=True)
class ReadBasis:
    """所用固定依据和真实读一致性；跨 owner 乐观检查不是全局快照。"""
    basis_id: str
    owner_heads: tuple[OwnerHead, ...]
    source_refs: tuple[FixedRef, ...]
    observed_at: UtcTime
    consistency: Literal["fixed_refs", "single_owner_snapshot", "cross_owner_optimistic"]


@dataclass(frozen=True)
class TimeWindow:
    field: Literal["recorded_at", "occurred_at", "valid_at"]
    start_inclusive: UtcTime | None
    end_exclusive: UtcTime | None


@dataclass(frozen=True)
class Applicability:
    """业务适用域；不能代替语料 owner 筛选或授权上下文。"""
    description: str
    conditions: tuple[str, ...]
    exclusions: tuple[str, ...]
    valid_from: UtcTime | None
    valid_until: UtcTime | None
    subject_versions: tuple[FixedRef, ...]


@dataclass(frozen=True)
class ConfidenceAssessment:
    target: FixedRef
    level: ConfidenceLevel
    assessed_by: str
    method: StrategyRef
    basis: tuple[EvidenceLink, ...]
    applicability: Applicability
    calibrated_probability: float | None
    calibration_ref: FixedRef | None  # 概率非空时必须有校准依据，不能用相似度顶替。


@dataclass(frozen=True)
class AttemptAssessment:
    attempt_ref: FixedRef
    outcome: AttemptOutcome
    conditions: tuple[str, ...]


@dataclass(frozen=True)
class KnowledgeFacets:
    """内容描述；roles/outcomes 可多值，缺少信息不自动补成成功或确定。"""
    roles: tuple[KnowledgeRole, ...]
    principle_kind: Literal["definition", "mathematical_axiom", "derived_invariant", "physical_law_model", "engineering_assumption"] | None
    attempts: tuple[AttemptAssessment, ...]
    applicability: Applicability
    counterexamples: tuple[EvidenceLink, ...]
    confidence: tuple[ConfidenceAssessment, ...]
    classification_basis: tuple[EvidenceLink, ...]


@dataclass(frozen=True)
class EvidenceAssessment:
    """由证据服务计算的读时状态；不得信任索引或调用方自报的 accepted。"""
    target: FixedRef
    review_state: ReviewState
    validity: ValidityState
    applicability: Applicability
    assessed_at: UtcTime
    review_refs: tuple[FixedRef, ...]
    evaluated_claim_refs: tuple[FixedRef, ...]
    unresolved_claim_refs: tuple[FixedRef, ...]
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class FacetFilter:
    # 不同字段 AND；单字段候选值 OR。显式过滤时 unknown 默认不匹配。
    roles: tuple[KnowledgeRole, ...] | None
    outcomes: tuple[AttemptOutcome, ...] | None
    review_states: tuple[ReviewState, ...] | None
    validities: tuple[ValidityState, ...] | None
    confidence_levels: tuple[ConfidenceLevel, ...] | None
    applicability: Applicability | None
    include_unknown: bool


@dataclass(frozen=True)
class CorpusScope:
    """硬语料约束；include/exclude 按身份匹配，exclude 始终优先。"""
    owner_ids: tuple[OwnerId, ...] | None
    kinds: tuple[str, ...] | None  # 来自已注册内容类型，非数据库表名。
    layers: tuple[Layer, ...] | None
    source_ids: tuple[str, ...] | None
    time_window: TimeWindow | None
    facets: FacetFilter | None
    include_refs: tuple[FixedRef, ...]
    exclude_ids: tuple[str, ...]


@dataclass(frozen=True)
class RepresentationSpec:
    """具名表示可扩展；搜索表示和结果视图分别选择，不映射为速度等级。"""
    keys: tuple[RepresentationKey, ...]
    fallback_order: tuple[RepresentationKey, ...]
    missing: Literal["reject", "skip", "fallback"]
    allow_build: bool  # 允许本请求构建仍受能力/预算约束，不授予内容提交权限。


@dataclass(frozen=True)
class FreshnessPolicy:
    mode: Literal["fixed", "current", "allow_stale"]
    allow_index_repair: bool
    max_staleness_seconds: float | None


@dataclass(frozen=True)
class BudgetLimits:
    """全部是硬上限；不设无限默认。token 上限依赖指定 tokenizer。"""
    deadline: UtcTime
    max_candidates: int
    max_rerank: int
    max_graph_nodes: int
    max_graph_edges: int
    max_hops: int
    max_read_bytes: int
    max_model_calls: int
    max_model_input_tokens: int
    max_model_output_tokens: int
    max_context_chars: int
    tokenizer: StrategyRef | None


@dataclass(frozen=True)
class BudgetUsage:
    elapsed_ms: float
    candidates: int
    reranked: int
    graph_nodes: int
    graph_edges: int
    read_bytes: int
    model_calls: int
    model_input_tokens: int
    model_output_tokens: int
    context_chars: int


@dataclass(frozen=True)
class CallContext:
    """由可信应用装配；恢复查询沿用预算账本，不能用新调用 ID 重置额度。"""
    call_id: str
    root_operation_id: str
    access_handle: str
    budget_handle: str
    cancellation_handle: str


@dataclass(frozen=True)
class Issue:
    code: str
    message: str
    affected_refs: tuple[FixedRef, ...]
    retry: Literal["never", "same_request", "replan", "after_external_change"]


@dataclass(frozen=True)
class Outcome(Generic[T]):
    """成功/部分/拒绝/失败分开；拒绝无数据，部分结果必须列出缺口。"""
    status: Literal["ok", "partial", "rejected", "failed"]
    value: T | None
    issues: tuple[Issue, ...]
    usage: BudgetUsage


@dataclass(frozen=True)
class PageRequest:
    limit: int
    cursor: Cursor | None


@dataclass(frozen=True)
class Page(Generic[T]):
    items: tuple[T, ...]
    next_cursor: Cursor | None
    basis: ReadBasis


@dataclass(frozen=True)
class ContentMetadata:
    ref: FixedRef
    owner_id: OwnerId
    kind: str
    layer: Layer | None
    title: str
    facets: KnowledgeFacets


@dataclass(frozen=True)
class TextSlice:
    ref: FixedRef
    markdown: str
    required_refs: tuple[FixedRef, ...]
    complete: bool


@dataclass(frozen=True)
class ReadRequest:
    refs: tuple[FixedRef, ...]
    scope: CorpusScope
    representation: RepresentationSpec
    freshness: FreshnessPolicy


@dataclass(frozen=True)
class ReadBatch:
    items: tuple[TextSlice, ...]
    basis: ReadBasis
    missing: tuple[Issue, ...]


@dataclass(frozen=True)
class DraftDocument:
    """复用注册的内容 schema，不在接口包复制十五类业务 payload。

    body_json 必须通过 schema_key 对应的固定版本校验；不接受任意自由字典。
    新 v3 内容目前映射 memory-v3.schema.json 的 Draft/类型校验入口。
    """
    owner_id: OwnerId
    schema_key: str
    schema_version: int
    body_json: str


@dataclass(frozen=True)
class PutChange:
    client_key: str
    previous: FixedRef | None
    draft: DraftDocument
    reason: str


@dataclass(frozen=True)
class RetireChange:
    target: FixedRef
    action: Literal["archive", "retract", "supersede"]
    replacement: FixedRef | None
    reason: str


@dataclass(frozen=True)
class ChangeBatch:
    request_id: str
    owner_id: OwnerId
    expected_head: CommitId | None
    basis: ReadBasis
    changes: tuple[PutChange | RetireChange, ...]


@dataclass(frozen=True)
class ValidationReceipt:
    batch_sha256: Sha256
    validator: StrategyRef
    validated_basis: ReadBasis
    validation_handle: str  # 内部一次验证凭据；不能以这个字符串替代实际校验。


@dataclass(frozen=True)
class CommittedChange:
    client_key: str
    previous: FixedRef | None
    current: FixedRef | None
    action: Literal["put", "archive", "retract", "supersede", "restore"]


@dataclass(frozen=True)
class CommitReceipt:
    request_id: str
    owner_id: OwnerId
    commit_id: CommitId
    changes: tuple[CommittedChange, ...]
    change_cursor: Cursor
    follow_up_required: tuple[Literal["index", "review", "document_impact"], ...]


@dataclass(frozen=True)
class RestoreRequest:
    request_id: str
    owner_id: OwnerId
    expected_head: CommitId
    restore_refs: tuple[FixedRef, ...]
    reason: str


@dataclass(frozen=True)
class Representation:
    ref: FixedRef
    key: RepresentationKey
    represented_refs: tuple[FixedRef, ...]
    authority: Literal["canonical", "derived"]
    generator: StrategyRef
    state: Literal["available", "stale"]
    contributors: tuple[FixedRef, ...]


@dataclass(frozen=True)
class RepresentationAvailability:
    key: RepresentationKey
    content_ref: FixedRef
    state: Literal["available", "stale", "missing", "unsupported"]
    representation: Representation | None
    reason: str | None


@dataclass(frozen=True)
class RepresentationPlan:
    plan_id: str
    scope: CorpusScope
    source_refs: tuple[FixedRef, ...]
    requested: RepresentationSpec
    basis: ReadBasis
    builder: StrategyRef


@dataclass(frozen=True)
class RepresentationBuild:
    # 新解释先成为草稿，通过内容提交获得固定身份后才成为可索引规范表示。
    derived: tuple[Representation, ...]
    content_proposals: tuple[DraftDocument, ...]
    basis: ReadBasis


@dataclass(frozen=True)
class IndexKey:
    channel: Channel
    representation: RepresentationKey
    encoder: StrategyRef | None
    analyzer: StrategyRef | None
    dimension: int | None


@dataclass(frozen=True)
class Watermark:
    index: IndexKey
    covered_basis: ReadBasis
    cursor: Cursor | None
    coverage: Literal["complete", "partial", "unknown"]


@dataclass(frozen=True)
class ChangeEvent:
    event_id: str
    owner_id: OwnerId
    commit_id: CommitId
    previous_refs: tuple[FixedRef, ...]
    current_refs: tuple[FixedRef, ...]


@dataclass(frozen=True)
class IndexPlan:
    plan_id: str
    mode: Literal["incremental", "rebuild", "repair"]
    index: IndexKey
    scope: CorpusScope
    changes: tuple[ChangeEvent, ...]
    source_refs: tuple[FixedRef, ...]
    target_basis: ReadBasis
    from_cursor: Cursor | None
    next_scan_cursor: Cursor | None


@dataclass(frozen=True)
class IndexReceipt:
    plan_id: str
    completed_events: tuple[str, ...]
    pending_events: tuple[str, ...]
    watermark: Watermark
    resume_cursor: Cursor | None


@dataclass(frozen=True)
class ProviderCapabilities:
    provider: StrategyRef
    channels: tuple[Channel, ...]
    representations: tuple[RepresentationKey, ...]
    filter_fields: tuple[str, ...]
    query_dialects: tuple[Literal["plain", "phrase", "boolean"], ...]
    freshness_modes: tuple[Literal["fixed", "current", "allow_stale"], ...]
    supports_hard_cancel: bool
    supports_filter_pushdown: bool


@dataclass(frozen=True)
class QuerySpec:
    text: str
    dialect: Literal["plain", "phrase", "boolean"]
    seeds: tuple[FixedRef, ...]
    scope: CorpusScope
    scope_ceiling: CorpusScope
    representations: RepresentationSpec
    channels: tuple[Channel, ...]
    purpose: Literal["exploration", "formal", "audit"]
    applicability: Applicability | None
    freshness: FreshnessPolicy
    limits: BudgetLimits
    planner: StrategyRef
    ranking: StrategyRef
    result_limit: int
    expansion_axes: tuple[Literal["owners", "time", "representations", "channels"], ...]


@dataclass(frozen=True)
class ChannelHit:
    channel: Channel
    provider: StrategyRef
    representation_ref: FixedRef
    rank: int
    raw_score: float | None
    score_meaning: str
    matched_text: tuple[TextSlice, ...]


@dataclass(frozen=True)
class Candidate:
    content: ContentMetadata
    hits: tuple[ChannelHit, ...]
    evidence_state: EvidenceAssessment


@dataclass(frozen=True)
class CandidateBatch:
    candidates: tuple[Candidate, ...]
    basis: ReadBasis
    watermarks: tuple[Watermark, ...]
    omitted: tuple[Issue, ...]
    next_cursor: Cursor | None


@dataclass(frozen=True)
class RecallRequest:
    query: QuerySpec
    channel: Channel
    candidate_limit: int
    cursor: Cursor | None


@dataclass(frozen=True)
class RankingRequest:
    query: QuerySpec
    batch: CandidateBatch
    texts: tuple[TextSlice, ...]  # 需要的重排正文由应用显式有界读取，不隐藏二次召回。
    limit: int


@dataclass(frozen=True)
class RankedCandidate:
    candidate: Candidate
    position: int
    ranking_score: float | None
    explanation: tuple[str, ...]  # 已执行特征/规则，不要求模型私有推理。


@dataclass(frozen=True)
class RankedBatch:
    items: tuple[RankedCandidate, ...]
    basis: ReadBasis
    watermarks: tuple[Watermark, ...]
    omitted: tuple[Issue, ...]


@dataclass(frozen=True)
class GraphEdge:
    edge_id: str
    source: FixedRef
    target: FixedRef
    kind: RelationKind
    evidence: tuple[EvidenceLink, ...]
    state: Literal["proposed", "accepted_navigation", "verified_claim", "stale", "retracted"]
    differences: tuple[str, ...]


@dataclass(frozen=True)
class GraphRequest:
    seeds: tuple[FixedRef, ...]
    targets: tuple[FixedRef, ...]
    scope: CorpusScope
    edge_kinds: tuple[RelationKind, ...]
    direction: Literal["out", "in", "both"]
    max_hops: int
    max_nodes: int
    max_edges: int
    cursor: Cursor | None


@dataclass(frozen=True)
class GraphSlice:
    nodes: tuple[ContentMetadata, ...]
    edges: tuple[GraphEdge, ...]
    paths: tuple[tuple[str, ...], ...]  # 有序 edge_id；每条路径须能定位两端版本。
    basis: ReadBasis
    next_cursor: Cursor | None
    omitted: tuple[Issue, ...]


@dataclass(frozen=True)
class ContextOptions:
    representation: RepresentationSpec
    max_chars: int
    include_required_definitions: bool


@dataclass(frozen=True)
class ContextRequest:
    refs: tuple[FixedRef, ...]
    scope: CorpusScope
    purpose: Literal["exploration", "formal", "audit"]
    applicability: Applicability | None
    basis: ReadBasis
    freshness: FreshnessPolicy
    options: ContextOptions


@dataclass(frozen=True)
class ContextPacket:
    packet_id: str
    items: tuple[TextSlice, ...]
    basis: ReadBasis
    selected_refs: tuple[FixedRef, ...]
    omitted: tuple[Issue, ...]
    actual_chars: int


@dataclass(frozen=True)
class ExpansionStep:
    action: Literal["recall", "navigate", "deepen", "stop"]
    scope: CorpusScope
    representation: RepresentationSpec
    channel: Channel | None
    refs: tuple[FixedRef, ...]
    reason: str
    stop_reason: StopReason | None


@dataclass(frozen=True)
class SearchProgress:
    query: QuerySpec
    basis: ReadBasis
    visited_refs: tuple[FixedRef, ...]
    steps: tuple[ExpansionStep, ...]
    last_batch: RankedBatch | None
    gaps: tuple[Issue, ...]
    usage: BudgetUsage


@dataclass(frozen=True)
class SearchReceipt:
    search_id: str
    normalized_query: QuerySpec
    ranked: RankedBatch
    progress: SearchProgress
    context: ContextPacket | None
    next_cursor: Cursor | None
    stop_reason: StopReason
    unavailable_channels: tuple[Channel, ...]


@dataclass(frozen=True)
class ResumeRequest:
    cursor: Cursor
    version_action: Literal["keep_fixed", "restart_on_current"]
    additional_budget: BudgetLimits | None  # 显式追加，须经调用权限/策略核验并记账。


@dataclass(frozen=True)
class ViewRequest:
    view: Literal["full", "layers", "digests", "research_process", "research_report", "relation_graph"]
    refs: tuple[FixedRef, ...]
    scope: CorpusScope
    basis: ReadBasis
    max_chars: int


@dataclass(frozen=True)
class ReadView:
    view: str
    text: tuple[TextSlice, ...]
    graph: GraphSlice | None
    basis: ReadBasis
    omitted: tuple[Issue, ...]


@dataclass(frozen=True)
class MaintenanceRequest:
    mode: Literal["organize", "recover"]
    scope: CorpusScope
    policy: StrategyRef
    changed_refs: tuple[FixedRef, ...]
    basis: ReadBasis


@dataclass(frozen=True)
class ReviewRequirement:
    owner_id: OwnerId
    changed_client_keys: tuple[str, ...]
    previous_refs: tuple[FixedRef, ...]
    method: StrategyRef


@dataclass(frozen=True)
class MaintenancePlan:
    plan_id: str
    request: MaintenanceRequest
    changes: tuple[ChangeBatch, ...]  # 每项一个 owner；不宣称跨 owner 原子提交。
    review_targets: tuple[ReviewRequirement, ...]
    impacted_refs: tuple[FixedRef, ...]
    recovery_refs: tuple[FixedRef, ...]


@dataclass(frozen=True)
class MaintenanceReceipt:
    plan_id: str
    commits: tuple[CommitReceipt, ...]
    pending_owner_ids: tuple[OwnerId, ...]
    review_states: tuple[EvidenceAssessment, ...]
    pending_reviews: tuple[FixedRef, ...]
    index_states: tuple[Watermark, ...]
    resume_cursor: Cursor | None


@dataclass(frozen=True)
class ReviewCommand:
    request_id: str
    target: FixedRef
    expected_owner_head: CommitId | None
    state: ReviewState
    applicability: Applicability
    evidence: tuple[EvidenceLink, ...]
    method: StrategyRef
    reason: str


@dataclass(frozen=True)
class AccessDecision:
    allowed_scope: CorpusScope
    rejected_ids: tuple[str, ...]
    basis: ReadBasis


@dataclass(frozen=True)
class BudgetReservation:
    reservation_id: str
    budget_handle: str
    ceiling: BudgetUsage
