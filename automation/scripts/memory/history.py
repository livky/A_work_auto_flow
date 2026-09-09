"""按固定修订显示研究经过，按暂停点准备续接材料；从不自动重做实验。"""
from copy import deepcopy

from . import packets, research
from .errors import MemoryError
from .evidence_adapter import iter_refs


def _row(record):
    occurred = record['payload'].get('occurred_at')
    goal = (research.fixed_ref(record) if record['kind'] == 'goal' else record['payload'].get('goal_ref'))
    return {'id': f"{record['record_id']}@{record['revision']}", 'canonical_id': record['record_id'],
            'revision': record['revision'], 'kind': record['kind'], 'role': packets.role(record),
            'ref': research.fixed_ref(record), 'occurred_at': occurred,
            'occurred_label': occurred or '发生时间未知', 'created_at': record['created_at'],
            'goal_ref': deepcopy(goal), 'title': record['title'], 'record': deepcopy(record)}


def build_history(service, owner_id, *, offset=0, limit=50, basis_heads=None):
    """分页水位由调用者带回；同一规范修订/旧 Run 不会重复进入时间线。"""
    service = packets.service_for(service)
    if type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= 500:
        raise MemoryError('INVALID_ARGUMENT', '历史 offset 必须非负，limit 范围为 1..500')
    snapshot = packets.Snapshot(service)
    owner, current = snapshot.owner(owner_id)
    if basis_heads is not None:
        snapshot.recheck(basis_heads)
    rows, seen, explicit_runs, missing = [], set(), set(), []
    from .document import Reader
    access = Reader(service, views=snapshot.views)
    access.states[owner_id] = current
    access.record_owners.update({rid: owner_id for rid in current['records']})
    access.used.add(owner_id)
    for record in service.store.read_history(owner, current):
        # A currently revoked record also hides its older prose. Immutable
        # history is retained on disk but is not an authorization bypass.
        if (record['sensitivity'] == 'restricted' or
                current['records'][record['record_id']]['sensitivity'] == 'restricted'):
            continue
        denied, issues = False, []
        for ref in iter_refs({'sources': record['sources'], 'payload': record['payload']}):
            try:
                access.check_ref(ref)
            except MemoryError as exc:
                issues.append({'target_id': ref['target_id'], 'code': exc.code})
                denied = denied or exc.code in {'ACCESS_DENIED', 'UNSAFE_PATH'}
        if denied:
            missing.append({'target_id': record['record_id'], 'code': 'ACCESS_DENIED'})
            continue
        row = _row(record)
        row['source_issues'] = issues
        rows.append(row)
        seen.add(row['id'])
        explicit_runs.update(ref['target_id'] for ref in iter_refs(record['payload']) if ref.get('target_kind') == 'owner' and ref['target_id'].startswith('RUN-'))
    # 关联只来自显式 ID 字段/引用；目录标题和父路径不产生额外事件归属。
    for ref in owner['native_data'].get('dependencies', []):
        target = ref.get('target') if isinstance(ref, dict) else None
        if isinstance(target, str) and target.startswith('RUN-'):
            explicit_runs.add(target)
    for candidate in snapshot.views.values():
        raw = candidate['native_data']
        if candidate['owner_type'] == 'run' and (candidate['owner_id'] == owner_id or
                owner_id in raw.get('related_research_ids', []) or owner_id in raw.get('related_project_ids', []) or
                raw.get('project_id') == owner_id):
            explicit_runs.add(candidate['owner_id'])
    for run_id in sorted(explicit_runs):
        try:
            item = packets._item(snapshot, run_id, packets._request(service, {'owner_id': owner_id, 'include_ids': [run_id]}))
            raw = snapshot.views[run_id]['native_data']
            rows.append({'id': run_id, 'canonical_id': run_id, 'revision': None, 'kind': 'run',
                         'role': 'run_attempt', 'ref': item['ref'], 'occurred_at': raw.get('occurred_at'),
                         'occurred_label': raw.get('occurred_at') or '发生时间未知',
                         'created_at': raw.get('created_at'), 'goal_ref': deepcopy(raw.get('goal_ref')),
                         'title': snapshot.views[run_id]['title'], 'native_data': deepcopy(raw)})
        except MemoryError as exc:
            missing.append({'target_id': run_id, 'code': exc.code})
    rows.sort(key=lambda row: (row['occurred_at'] or row.get('created_at') or '', row['canonical_id'], row['revision'] or 0))
    heads = snapshot.heads()
    heads.update({oid: value['head']['commit_id'] if value['head'] else 'none'
                  for oid, value in access.states.items()})
    access.recheck()
    snapshot.recheck(basis_heads)
    end = offset + limit
    return {'schema_version': 1, 'owner_id': owner_id, 'generated_at': service.clock(),
            'basis_heads': heads, 'items': rows[offset:end], 'total': len(rows),
            'offset': offset, 'next_offset': end if end < len(rows) else None, 'missing': missing,
            'snapshot_kind': 'per_owner_verified_heads', 'writes': 0}


def resume(service, owner_id, budget=None, selection=None):
    """当前目标→检查点→路线/问题→经验；明确旧目标差异和来源变化。"""
    service = packets.service_for(service)
    snapshot = packets.Snapshot(service)
    _owner, state = snapshot.owner(owner_id)
    request = {'owner_id': owner_id, 'purpose': 'exploration', **deepcopy(selection or {})}
    if budget is not None:
        request['budget'] = budget
    pointers = (state['manifest'] or {}).get('pointers', {})
    records = state['records']
    ordered, preferred = [], []
    for slot in ('goal', 'checkpoint'):
        pointer = pointers.get(slot)
        if pointer and pointer['record_id'] in records:
            record = records[pointer['record_id']]
            ordered.append(research.fixed_ref(record))
            preferred.append(record['record_id'])
    for kind in ('map', 'detail', 'route', 'question', 'experience'):
        choices = [record for record in records.values() if record['kind'] == kind and record['sensitivity'] != 'restricted']
        if kind in {'map', 'detail'}:
            # Resume uses the newest synthesis and detailed calculation before
            # older navigation. Explicit full selections still take precedence;
            # budget/permission failures remain visible in required_not_full.
            from .document import document_order
            choices.sort(key=lambda row: (row.get('updated_at', row['created_at']), document_order(row)), reverse=True)
            if choices:
                preferred.append(choices[0]['record_id'])
        if kind == 'question':
            # resolved 也保留到回源视图，避免已撤回答案的问题被终态筛掉。
            choices.sort(key=lambda row: row['payload']['status'] not in {'open', 'investigating', 'blocked'})
        for record in choices:
            ordered.append(research.fixed_ref(record))
    checkpoint_pointer, goal_pointer = pointers.get('checkpoint'), pointers.get('goal')
    mismatch = False
    checkpoint_id = checkpoint_pointer['record_id'] if checkpoint_pointer else None
    if checkpoint_pointer and goal_pointer:
        old_goal = records[checkpoint_id]['payload']['goal_ref']
        mismatch = old_goal['target_id'] != goal_pointer['record_id'] or old_goal.get('revision') != goal_pointer['revision']
        if mismatch:
            # 旧目标也可展开，只是明确不同版本，不把新条件回写给旧尝试。
            ordered.append(old_goal)
    request.setdefault('full_ids', preferred)
    result = packets.expand(service, ordered, request, snapshot=snapshot)
    result['manifest']['resume'] = {'owner_id': owner_id, 'checkpoint_id': checkpoint_id,
                                   'checkpoint_goal_mismatch': mismatch, 'execution_started': False}
    if mismatch:
        # 说明文字同样进入总预算；空间不足则只返回非正文标记与明确缺口。
        notice = '检查点绑定旧目标版本；当前目标的约束不得回填给旧尝试。'
        notice = packets.normalize_context_text(notice)
        combined = notice + (packets.PART_SEPARATOR + result['context_text'] if result['context_text'] else '')
        if len(combined) <= result['manifest']['budget']['effective']:
            result['context_text'] = combined
            result['manifest']['budget']['used'] = len(combined)
        else:
            result['manifest']['missing'].append({'target_id': checkpoint_id, 'code': 'GOAL_MISMATCH_NOTICE_BUDGET'})
            result['manifest']['status'] = 'incomplete'
    return result
