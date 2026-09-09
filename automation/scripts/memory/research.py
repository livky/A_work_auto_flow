"""问题、目标、路线和暂停快照的领域规则及纯操作构造器。

本模块不直接写文件、不运行实验、不安排后台任务。构造出的 operation
交给统一 MemoryService；validate_change 也由该服务在所有普通 put 上调用，
因此换一个 CLI/HTTP 入口不能绕过状态机或用执行成功替代问题解决。
"""
from copy import deepcopy

from . import contracts
from .errors import MemoryError


QUESTION_TRANSITIONS = {
    'open': {'investigating', 'blocked', 'resolved', 'superseded'},
    'investigating': {'open', 'blocked', 'resolved', 'superseded'},
    'blocked': {'open', 'investigating', 'resolved', 'superseded'},
    'resolved': {'open', 'investigating'},
    'superseded': {'open', 'investigating'},
}
ROUTE_TRANSITIONS = {
    'planned': {'active', 'blocked', 'closed', 'superseded'},
    'active': {'blocked', 'closed', 'superseded'},
    'blocked': {'active', 'closed', 'superseded'},
    'closed': {'active'},
    'superseded': {'active'},
}


def _fail(message, path):
    raise MemoryError('INVALID_TRANSITION', message,
                      errors=[{'code': 'INVALID_TRANSITION', 'path': path, 'message': message}])


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def fixed_ref(record, relation='references'):
    """绑定已取得修订，不把旧目标/路线自动升级为当前版本。"""
    return {'target_kind': 'record', 'target_id': record['record_id'],
            'revision': record['revision'], 'sha256': None,
            'locator': '完整规范修订', 'relation': relation}


def _resolved(ref, resolve_ref, path):
    if not isinstance(ref, dict):
        _fail('需要固定引用', path)
    if ref.get('target_kind') == 'record':
        if type(ref.get('revision')) is not int or ref['revision'] < 1:
            _fail('记录依据必须固定正整数修订', path + '/revision')
    elif not ref.get('sha256'):
        _fail('旧对象、结论或文件依据必须绑定内容指纹', path + '/sha256')
    if resolve_ref is None:
        # 构造器允许先准备草案；实际提交的服务必须提供真实解析器。
        return None
    value = resolve_ref(ref)
    if not isinstance(value, dict):
        _fail('固定依据无法解析', path)
    return value


def _kind(value):
    if value is None:
        return None
    if value.get('claim') is not None:
        return 'claim'
    return value.get('kind') or value.get('owner_type') or value.get('owner', {}).get('owner_type')


def _require_kind(ref, kinds, resolve_ref, path):
    value = _resolved(ref, resolve_ref, path)
    if value is not None and _kind(value) not in kinds:
        _fail('引用目标类别不符合用途：' + ', '.join(sorted(kinds)), path)
    return value


def _answer(ref, record_id, resolve_ref, path):
    """探索答案不强制 accepted，但必须真有答案/决策内容，不能自指导航。"""
    if not isinstance(ref, dict):
        _fail('需要固定答案引用', path)
    if ref.get('target_id') == record_id:
        _fail('问题不能用自身作为解决依据', path)
    value = _resolved(ref, resolve_ref, path)
    if value is None:
        return
    kind = _kind(value)
    payload = value.get('payload', {})
    raw = value.get('native_data', value.get('owner', {}).get('native_data', value))
    if kind == 'claim' or ref.get('target_kind') == 'claim':
        # 新旧 claim 由证据服务解析和检查真实身份；accepted 与否独立显示。
        return
    if kind == 'event' and (payload.get('claims') or _text(payload.get('decision')) or payload.get('decision_refs')):
        return
    if kind == 'experience' and (_text(payload.get('recommendation')) or payload.get('claims') or payload.get('claim_refs')):
        return
    if kind == 'run' and (raw.get('claims') or _text(raw.get('conclusion')) or _text(raw.get('decision'))):
        return
    _fail('解决依据必须是可取得的答案或决策，不能只引用导航、步骤或未决问题', path)


def validate_change(old, record, *, record_id, resolve_ref):
    """统一领域门：调用前先通过 schema，调用后才计算哈希并保存。

    resolve_ref 必须解析固定版本和授权范围；本函数只增加研究语义，
    不替代来源版本检查、证据复核或事务内的第二次回源校验。
    """
    kind, payload = record['kind'], record['payload']
    before = old['payload'] if old else None
    if kind == 'question':
        state = payload['status']
        if old and state != before['status']:
            if state not in QUESTION_TRANSITIONS[before['status']]:
                _fail('问题状态转换不在契约允许范围', '/payload/status')
            if before['status'] in {'resolved', 'superseded'} and not _text(payload['reopen_reason']):
                _fail('已结束问题重开必须说明原因', '/payload/reopen_reason')
        if state == 'resolved':
            if not payload['resolution_refs']:
                _fail('resolved 必须有固定答案或决策引用', '/payload/resolution_refs')
            for index, ref in enumerate(payload['resolution_refs']):
                _answer(ref, record_id, resolve_ref, f'/payload/resolution_refs/{index}')
        if state == 'superseded':
            ref = payload['replacement_ref']
            if not ref or ref.get('target_id') == record_id:
                _fail('替代必须指向另一个问题', '/payload/replacement_ref')
            _require_kind(ref, {'question'}, resolve_ref, '/payload/replacement_ref')
    elif kind == 'goal':
        ref = payload['previous_goal_ref']
        if ref:
            _require_kind(ref, {'goal'}, resolve_ref, '/payload/previous_goal_ref')
        if old and contracts.content_hash(record) != old['content_hash']:
            if not ref or ref.get('target_id') != record_id or ref.get('revision') != old['revision']:
                _fail('更改目标必须固定关联本目标上一修订', '/payload/previous_goal_ref')
            if not _text(payload['change_impact']):
                _fail('更改目标必须说明对既有尝试的影响', '/payload/change_impact')
        elif not old and ref and ref.get('target_id') == record_id:
            _fail('首版目标不能引用自身不存在的旧版本', '/payload/previous_goal_ref')
    elif kind == 'route':
        state = payload['status']
        _require_kind(payload['goal_ref'], {'goal'}, resolve_ref, '/payload/goal_ref')
        if state == 'blocked' and not _text(payload['blocker']):
            _fail('路线阻塞必须说明具体条件', '/payload/blocker')
        if state in {'active', 'closed'} and payload['blocker'] is not None:
            _fail('active/closed 路线不能继续携带未解决 blocker', '/payload/blocker')
        if not _text(payload['next_step']) or not _text(payload['reopen_condition']):
            _fail('路线必须说明下一步或关闭后动作，以及重新开启条件', '/payload/next_step')
        if state == 'superseded':
            ref = payload['replacement_ref']
            if not ref or ref.get('target_id') == record_id:
                _fail('替代必须指向另一条路线', '/payload/replacement_ref')
            _require_kind(ref, {'route'}, resolve_ref, '/payload/replacement_ref')
        if old:
            if payload['goal_ref'] != before['goal_ref']:
                _fail('更换目标应建新路线；旧尝试继续绑定旧目标', '/payload/goal_ref')
            if any(ref not in payload['attempt_refs'] for ref in before['attempt_refs']):
                _fail('路线修订不能移除已登记尝试', '/payload/attempt_refs')
            if state != before['status'] and state not in ROUTE_TRANSITIONS[before['status']]:
                _fail('路线状态转换不在允许范围', '/payload/status')
            if before['status'] in {'blocked', 'closed', 'superseded'} and state == 'active':
                if not _text(record.get('change_reason')):
                    _fail('重新 active 必须记录重新开启理由', '/change_reason')
                if not any(ref not in old['sources'] for ref in record['sources']):
                    _fail('重新 active 必须绑定变化后的固定依据', '/sources')
    elif kind == 'checkpoint':
        _require_kind(payload['goal_ref'], {'goal'}, resolve_ref, '/payload/goal_ref')
        for field, expected in [('route_refs', 'route'), ('question_refs', 'question')]:
            for index, ref in enumerate(payload[field]):
                _require_kind(ref, {expected}, resolve_ref, f'/payload/{field}/{index}')
        budget = payload['budget_remaining']
        # UnknownValue 原样保存；明确预算以调用方命名的单位为键，不擅自
        # 把未知值转换为 0，也不把负数当成可继续使用的余额。
        if 'value' not in budget and any(value < 0 for value in budget.values()):
            _fail('预算余额不得为负数；未知使用 UnknownValue', '/payload/budget_remaining')


def _draft(record):
    """剥离服务字段，保留所有规范正文与旧固定引用。"""
    # Record version determines how the stored level is interpreted. Omitting
    # it here silently opts a v1 revision into the v2 defaults, making old
    # experience/map levels invalid (and misrepresenting version-only edits).
    # Preserve the version; an explicit taxonomy upgrade belongs to the caller.
    return {key: deepcopy(record[key]) for key in ('schema_version', *contracts.CONTENT_FIELDS, 'record_reason', 'change_reason')
            if key in record}


def _old(record, expected_revision, kind):
    if record.get('kind') != kind:
        _fail('目标记录类别不匹配', '/kind')
    if record.get('revision') != expected_revision:
        raise MemoryError('VERSION_CONFLICT', '记录修订已变化', {'record_id': record.get('record_id'), 'current_revision': record.get('revision')})


def _basis(basis, allowed):
    if not isinstance(basis, dict) or set(basis) - set(allowed):
        raise MemoryError('INVALID_ARGUMENT', '转换依据包含未知字段')
    if not _text(basis.get('change_reason')):
        _fail('转换必须说明变更理由', '/change_reason')


def transition_question(record, expected_revision, state, basis):
    """只构造一个问题修订；状态和依据仍须通过统一提交领域门。"""
    _old(record, expected_revision, 'question')
    _basis(basis, {'change_reason', 'resolution_refs', 'replacement_ref', 'reopen_reason',
                   'missing_evidence', 'decision_affected', 'sources'})
    if state not in QUESTION_TRANSITIONS:
        _fail('未知问题状态', '/payload/status')
    draft = _draft(record)
    draft['payload']['status'] = state
    for key, value in basis.items():
        if key in {'change_reason', 'sources'}:
            draft[key] = deepcopy(value)
        else:
            draft['payload'][key] = deepcopy(value)
    # 新一轮重开/解决不继承上次的重开理由或替代定位；历史修订仍保留。
    if state != 'superseded':
        draft['payload']['replacement_ref'] = None
    draft['payload']['reopen_reason'] = basis.get('reopen_reason')
    validate_change(record, draft, record_id=record['record_id'], resolve_ref=None)
    return {'op': 'transition_question', 'record_id': record['record_id'],
            'expected_revision': expected_revision, 'draft': draft}


def route_transition(record, expected_revision, state, basis):
    """重开依据通过 sources 固定保存，解释通过 change_reason 保存。"""
    _old(record, expected_revision, 'route')
    _basis(basis, {'change_reason', 'blocker', 'next_step', 'reopen_condition', 'replacement_ref',
                   'attempt_refs', 'basis_refs', 'evidence_changes'})
    if state not in ROUTE_TRANSITIONS:
        _fail('未知路线状态', '/payload/status')
    draft = _draft(record)
    draft['payload']['status'] = state
    draft['change_reason'] = basis['change_reason']
    for key in ('blocker', 'next_step', 'reopen_condition', 'replacement_ref', 'attempt_refs'):
        if key in basis:
            draft['payload'][key] = deepcopy(basis[key])
    if state in {'active', 'closed'}:
        draft['payload']['blocker'] = None
    if state != 'superseded':
        draft['payload']['replacement_ref'] = None
    reopening = record['payload']['status'] in {'blocked', 'closed', 'superseded'} and state == 'active'
    if reopening and not _text(basis.get('evidence_changes')):
        _fail('重新开启必须明确说明依据发生了什么变化', '/change_reason')
    if basis.get('evidence_changes'):
        draft['change_reason'] += '\n依据变化：' + basis['evidence_changes']
    for ref in basis.get('basis_refs', []):
        if ref not in draft['sources']:
            draft['sources'].append(deepcopy(ref))
    validate_change(record, draft, record_id=record['record_id'], resolve_ref=None)
    return {'op': 'put_record', 'record_id': record['record_id'],
            'expected_revision': expected_revision, 'draft': draft}


def _new(owner_id, kind, payload, title, metadata):
    metadata = deepcopy(metadata or {})
    allowed = {'body_markdown', 'keywords', 'sources', 'provenance_gap', 'record_reason',
               'discovery', 'sensitivity', 'change_reason'}
    if set(metadata) - allowed:
        raise MemoryError('INVALID_ARGUMENT', '记录元数据含服务身份字段或未知字段')
    return {'owner_id': owner_id, 'kind': kind, 'title': title, 'body_markdown': '',
            'sources': [], 'provenance_gap': None, 'sensitivity': 'internal',
            **metadata, 'payload': deepcopy(payload)}


def set_goal(owner_id, payload, *, previous=None, title='研究目标', metadata=None):
    """更新同一目标时产生新修订并固定前版；旧路线和尝试完全不改。"""
    if previous:
        _old(previous, previous['revision'], 'goal')
        if previous['owner_id'] != owner_id:
            raise MemoryError('INVALID_ARGUMENT', '不能跨对象修订目标')
        draft = _draft(previous)
        draft.update(title=title, payload=deepcopy(payload))
        # metadata 使用同一白名单，但更新不把未提供的旧字段重置。
        extras = _new(owner_id, 'goal', payload, title, metadata)
        for key in metadata or {}:
            draft[key] = extras[key]
        draft['payload']['previous_goal_ref'] = fixed_ref(previous, 'derived_from')
        draft['change_reason'] = draft['payload']['change_impact']
        return {'op': 'put_record', 'record_id': previous['record_id'],
                'expected_revision': previous['revision'], 'draft': draft}
    value = deepcopy(payload)
    value.setdefault('previous_goal_ref', None)
    return {'op': 'put_record', 'client_key': 'goal',
            'draft': _new(owner_id, 'goal', value, title, metadata)}


def checkpoint(owner_id, payload, *, title='研究检查点', metadata=None):
    """保存当时暂停条件与预算原值，不解析成调度指令。"""
    return {'op': 'save_checkpoint', 'client_key': 'checkpoint',
            'draft': _new(owner_id, 'checkpoint', payload, title, metadata)}


def checkpoint_view(record, *, resolve_ref=None):
    """恢复前按固定引用重验，保留原快照及不可取得项，不执行任何下一步。"""
    if record.get('kind') != 'checkpoint':
        raise MemoryError('INVALID_ARGUMENT', '目标不是检查点')
    result = {'record_id': record['record_id'], 'revision': record['revision'],
              'payload': deepcopy(record['payload']), 'risks': [], 'execution_started': False}
    if resolve_ref:
        fields = ['goal_ref', 'route_refs', 'completed_refs', 'question_refs']
        for field in fields:
            refs = record['payload'][field]
            refs = refs if isinstance(refs, list) else [refs]
            for ref in refs:
                try:
                    _resolved(ref, resolve_ref, '/payload/' + field)
                except MemoryError as exc:
                    result['risks'].append({'ref': deepcopy(ref), 'code': exc.code, 'path': '/payload/' + field})
    return result


def question_view(records, *, validity=None):
    """问题生命周期与 Run/Research 完成状态无关；终态失效也不覆写历史。"""
    values = records.values() if isinstance(records, dict) else records
    result = []
    for record in values:
        if record['kind'] != 'question':
            continue
        item = {'record_id': record['record_id'], 'revision': record['revision'],
                'payload': deepcopy(record['payload']), 'unresolved': record['payload']['status'] in {'open', 'investigating', 'blocked'}}
        if validity and record['payload']['status'] == 'resolved':
            item['resolution_validity'] = validity(fixed_ref(record))
        result.append(item)
    return sorted(result, key=lambda item: item['record_id'])


def ingest_source(owner_id, payload, *, title, metadata, overwrite_original=False):
    """准备已取得的来源记录；来源定位仍由 commit 对登记 ID 回源核验。"""
    if overwrite_original:
        raise MemoryError('INVALID_ARGUMENT', '记忆来源接入只读原件，不支持覆盖原件')
    return {'op': 'put_record', 'client_key': 'source',
            'draft': _new(owner_id, 'source', payload, title, metadata)}
