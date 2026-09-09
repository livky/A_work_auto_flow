"""跨对象总结先准备固定材料，再将用户/AI提供的新解释保存到一个归属。"""
from copy import deepcopy

from . import contracts, packets
from .errors import MemoryError


def prepare(service, query, owners, budget=None, selection=None):
    """返回可复制给 AI 的材料包；不调用生成模型，不声称总结已经完成。"""
    service = packets.service_for(service)
    if not isinstance(owners, list) or not owners or not all(isinstance(oid, str) for oid in owners):
        raise MemoryError('INVALID_ARGUMENT', '总结准备需要明确选择归属 ID 数组')
    request = {'query': query, 'purpose': 'exploration', 'owner_ids': list(dict.fromkeys(owners)),
               **deepcopy(selection or {})}
    if budget is not None:
        request['budget'] = budget
    # 指定对象内部 owner_only 记录可由这次显式选择读取。结果、经验、问题
    # 和地图优先，原对象只作为定位，不复制整个项目目录或运行外部工具。
    snapshot = packets.Snapshot(service)
    refs, substantive = [], set()
    explicit = set(request.get('include_ids', [])) | set(request.get('full_ids', []))
    for oid in request['owner_ids']:
        if oid in request.get('exclude_ids', []):
            continue
        _owner, state = snapshot.owner(oid)
        for record in state['records'].values():
            if record['kind'] in {'detail', 'event', 'experience', 'map', 'question', 'goal', 'route'} or record['record_id'] in explicit:
                refs.append({'target_kind': 'record', 'target_id': record['record_id'], 'revision': record['revision'],
                             'sha256': None, 'locator': '规范总结材料', 'relation': 'references'})
                if record['kind'] in {'detail', 'event', 'experience'}:
                    substantive.add(record['record_id'])
    # 准备可在关键词索引尚未建好时使用已选择的固定记录；跨项目选择
    # 已明确，不能因索引空或降级而遗漏该对象的全部局部结果。
    request['refs'] = refs
    # The caller has explicitly selected the summary corpus. A global search
    # would both duplicate these reads and pull in unselected owners. Expand
    # the fixed chosen records directly; expand performs the final fresh HEAD
    # and source check before returning this already-verified packet.
    searched = packets.expand(service, refs, request, snapshot=snapshot, summary_mode=True)
    searched['manifest']['summary'] = {'prepared_only': True, 'ai_summary_completed': False,
                                       'owner_ids': request['owner_ids'], 'execution_started': False}
    coverage = []
    for oid in request['owner_ids']:
        ids = [item['canonical_id'] for item in searched['manifest']['items'] if item['owner_id'] == oid]
        meaningful = [rid for rid in ids if rid in substantive]
        status = 'excluded' if oid in request.get('exclude_ids', []) else 'covered' if meaningful else 'navigation_only' if ids else 'not_in_packet'
        coverage.append({'owner_id': oid, 'record_ids': ids, 'substantive_record_ids': meaningful, 'status': status})
        if status == 'not_in_packet':
            searched['manifest']['missing'].append({'target_id': oid, 'code': 'SUMMARY_OWNER_NOT_IN_PACKET'})
            if searched['manifest']['status'] == 'complete':
                searched['manifest']['status'] = 'partial'
    searched['manifest']['summary']['owner_coverage'] = coverage
    searched['manifest']['basis_heads'].update(snapshot.heads())
    searched['basis_heads'] = deepcopy(searched['manifest']['basis_heads'])
    searched['source_refs'] = deepcopy(searched['manifest']['source_refs'])
    return searched


def save(service, request):
    """单对象保存 L3/L4；无新来源的新解释需显式理由，不继承 accepted。

    request 是 CommitRequest 加 basis_heads。用户不能以 request_hash 覆盖
    幂等身份；内部哈希绑定公开请求，固定来源 HEAD 由统一提交入口复核。
    """
    service = packets.service_for(service)
    public = deepcopy(request)
    if not isinstance(public, dict):
        raise MemoryError('INVALID_ARGUMENT', '总结保存请求必须为对象')
    allowed = {'schema_version', 'request_id', 'actor', 'owner_id', 'expected_head', 'draft',
               'record_id', 'expected_revision', 'operations', 'dry_run', 'basis_heads'}
    if set(public) - allowed:
        raise MemoryError('INVALID_ARGUMENT', '总结保存请求包含未知字段')
    basis = public.pop('basis_heads', {})
    if 'draft' in public:
        if 'operations' in public:
            raise MemoryError('INVALID_ARGUMENT', '不能同时指定草案与批次操作')
        operation = {'op': 'put_record', 'draft': public.pop('draft')}
        if 'record_id' in public:
            operation.update(record_id=public.pop('record_id'), expected_revision=public.pop('expected_revision', None))
        else:
            operation['client_key'] = 'summary'
        public['operations'] = [operation]
    public.setdefault('schema_version', 1)
    operations = public.get('operations', [])
    if not operations:
        raise MemoryError('INVALID_ARGUMENT', '总结保存需要至少一条经验或地图')
    for operation in operations:
        draft = operation.get('draft', {})
        if draft.get('kind') not in {'experience', 'map'} or draft.get('owner_id') != public.get('owner_id'):
            raise MemoryError('INVALID_ARGUMENT', '总结只能保存为单一归属的 L3 experience 或 L4 map')
        if operation.get('record_id') and not str(draft.get('change_reason', '')).strip():
            raise MemoryError('INVALID_ARGUMENT', '新的解释或边界修订必须说明 change_reason')
    digest = contracts.canonical_hash({key: value for key, value in request.items() if key not in {'request_id', 'dry_run'}})
    return service._commit(public, request_hash=digest, basis_heads=basis)
