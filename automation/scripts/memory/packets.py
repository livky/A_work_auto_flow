"""有固定版本、范围和 Unicode 预算的只读记忆材料包。

正文只存在 context_text；manifest 只保存身份、版本、角色和缺口码。
不调用生成模型，不执行包里的建议。正式正文只接收证据适配器的合格
claim 文本，探索材料和类比即便命中检索也不能混入正式答案。
"""
from copy import deepcopy
import json
import os
from pathlib import Path
import uuid

from . import contracts, owners
from .errors import MemoryError
from .research import fixed_ref
from .evidence_adapter import EvidenceAdapter, iter_refs, legacy_ref

STAGES = {'focus': (6, 1, 2), 'investigate': (14, 1, 4), 'wide': (24, 2, 8)}
CHOICES = ('owner_id', 'owner_ids', 'owner_types', 'include_ids', 'full_ids', 'exclude_ids')
LINE_ENDING = '\r\n' if os.name == 'nt' else '\n'
PART_SEPARATOR = LINE_ENDING * 2


def normalize_context_text(text):
    """Match the host clipboard newline convention before spending budget.

    Stored records/originals remain byte-for-byte unchanged. Normalizing a
    previously normalized packet is idempotent, including existing CRLF text.
    """
    return text.replace('\r\n', '\n').replace('\r', '\n').replace('\n', LINE_ENDING)


def service_for(value):
    if hasattr(value, 'store') and hasattr(value, 'root'):
        return value
    from .service import MemoryService
    return MemoryService(value)


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)


def ref_metadata(ref):
    """定位文字可能包含摘录，因此 manifest 不承载自由 locator 正文。"""
    return {**{key: ref.get(key) for key in ('target_kind', 'target_id', 'revision', 'sha256', 'relation')}, 'locator': ''}


class Snapshot:
    """一次包生成的读取水位；结束前重新核对，不声称跨对象原子快照。"""
    def __init__(self, service):
        self.service = service_for(service)
        self.root = self.service.root
        self.views = {v['owner_id']: v for v in owners.list_owners(self.root)}
        self.snapshots, self.native_hashes, self.checks = {}, {}, []
        self.resolved_refs = {}
        self.used_owners = set()
        self._adapter = None

    @property
    def adapter(self):
        if self._adapter is None:
            self._adapter = EvidenceAdapter(self.service)
        return self._adapter

    def owner(self, owner_id, *, track=True):
        owner = self.views.get(owner_id)
        if not owner:
            raise MemoryError('NOT_FOUND', '材料归属不存在', {'owner_id': owner_id})
        if owner['native_data'].get('sensitivity', 'internal') == 'restricted':
            raise MemoryError('ACCESS_DENIED', '对象不在当前允许读取范围')
        if owner_id not in self.snapshots:
            self.snapshots[owner_id] = self.service.store.read_snapshot(owner)
            self.native_hashes[owner_id] = owner['fingerprint']
        if track:
            self.used_owners.add(owner_id)
        return owner, self.snapshots[owner_id]

    def all_records(self):
        for owner_id, owner in self.views.items():
            if owner['native_data'].get('sensitivity', 'internal') == 'restricted':
                continue
            yield from self.owner(owner_id, track=False)[1]['records'].values()

    def record(self, record_id, revision=None):
        for owner_id, owner in self.views.items():
            if owner['native_data'].get('sensitivity', 'internal') == 'restricted':
                continue
            snapshot = self.owner(owner_id, track=False)[1]
            if record_id in snapshot['records']:
                value = snapshot['records'][record_id]
                if value['sensitivity'] == 'restricted':
                    raise MemoryError('ACCESS_DENIED', '记录当前已限制访问')
                if revision is not None and revision != value['revision']:
                    value = self.service.store.read_record(owner, record_id, revision)
                if value['sensitivity'] == 'restricted':
                    raise MemoryError('ACCESS_DENIED', '记录不在当前允许读取范围')
                self.used_owners.add(owner_id)
                return value
        raise MemoryError('NOT_FOUND', '规范记录不存在', {'target_id': record_id})

    def resolve(self, ref):
        """真正的引用解析仍通过唯一服务授权边界；本地缓存只定位已读修订。"""
        # A fixed identity has one result inside this packet snapshot. Relation
        # and free locator text do not change which bytes are authorized. Keep
        # the original source check once and always recheck it before return.
        key = (ref['target_kind'], ref['target_id'], ref.get('revision'), ref.get('sha256'))
        if key in self.resolved_refs:
            return self.resolved_refs[key]
        if ref['target_kind'] == 'record':
            value = self.record(ref['target_id'], ref['revision'])
            if ref.get('sha256') not in (None, value['record_hash']):
                raise MemoryError('STALE_BASIS', '记录固定哈希与指定修订不同', {'target_id': ref['target_id']})
            self.resolved_refs[key] = value
            return value
        checks = []
        value = self.service._resolve_ref(ref, {}, checks)
        self.checks.extend(checks)
        if value.get('sensitivity') == 'restricted':
            raise MemoryError('ACCESS_DENIED', '来源不在当前允许读取范围')
        if value.get('owner'):
            self.owner(value['owner']['owner_id'])
        elif value.get('owner_id') in self.views:
            self.owner(value['owner_id'])
        self.resolved_refs[key] = value
        return value

    def heads(self):
        return {oid: value['head']['commit_id'] if value['head'] else 'none' for oid, value in self.snapshots.items() if oid in self.used_owners}

    def recheck(self, expected=None):
        for oid in expected or {}:
            self.owner(oid)
        # One fresh inventory checks moves/duplicate identities for the whole
        # packet. Re-enumerating every workspace once per used owner does not
        # strengthen the check and makes multi-owner summaries quadratic.
        try:
            current_owners = {owner['owner_id']: owner for owner in owners.list_owners(self.root)} if self.used_owners else {}
        except MemoryError as exc:
            raise MemoryError('STALE_BASIS', '包生成期间归属清单已变化或不可取得', {'cause': exc.code}) from exc
        for oid, initial in self.snapshots.items():
            if oid not in self.used_owners:
                continue
            try:
                current_owner = current_owners.get(oid)
                if current_owner is None:
                    raise MemoryError('NOT_FOUND', '固定快照的归属已不存在')
                current = self.service.store.read_snapshot(current_owner)
                cid = current['head']['commit_id'] if current['head'] else 'none'
                if current['head'] != initial['head'] or current_owner['fingerprint'] != self.native_hashes[oid]:
                    raise MemoryError('STALE_BASIS', '包生成期间对象依据发生变化')
                if expected is not None and oid in expected and expected[oid] != cid:
                    raise MemoryError('STALE_BASIS', '翻页或导出使用的对象 HEAD 已变化')
            except MemoryError as exc:
                raise MemoryError('STALE_BASIS', '固定对象快照已变化或不可取得', {'owner_id': oid}) from exc
        try:
            self.service._recheck(self.checks)
        except MemoryError as exc:
            raise MemoryError('STALE_BASIS', '包生成期间来源依据发生变化', {'cause': exc.code}) from exc


def role(record):
    kind, payload = record['kind'], record.get('payload', {})
    if kind == 'source':
        return 'direct_source'
    if kind == 'experience':
        return 'unreviewed_experience'
    if kind in {'event', 'narrative'} and payload.get('failure'):
        return 'counterevidence' if payload['failure']['category'] == 'counterexample' else 'failure'
    if kind == 'association' and payload.get('relation') == 'analogous_to':
        return 'analogy_' + payload.get('status', 'candidate')
    if kind == 'question':
        return 'unresolved_question' if payload.get('status') in {'open', 'investigating', 'blocked'} else 'question_' + payload['status']
    return kind


def render_record(record):
    """整条呈现正文、边界、未知值及固定引用；不能按字符截断禁用条件。"""
    rid = record['record_id']
    from .technical_units import is_unit, description_text, render_full
    if is_unit(record):
        return '\n\n'.join([f"### {record['title']}",
            f"身份：{rid} r{record['revision']}；归属：{record['owner_id']}；角色：detail",
            description_text(record), render_full(record), '固定来源：\n```json\n' + _json(record['sources']) + '\n```'])
    if record['kind'] in {'document', 'document_section'}:
        payload = record['payload']
        authored = ('\n\n'.join(payload[key] for key in ('purpose', 'audience', 'scope')) if record['kind'] == 'document'
                    else '\n\n'.join(block['markdown'] for block in payload['blocks'] if block['type'] == 'prose'))
        return '\n\n'.join([f"### {record['title']}", f"身份：{rid} r{record['revision']}；归属：{record['owner_id']}",
            authored, '固定内容引用：\n```json\n' + _json(list(iter_refs(payload))) + '\n```'])
    # Every copied item retains its owner even when no map or native Run fits
    # the budget. A reader must not infer ownership from an incidental source.
    lines = [f"### {record['title']}", f"身份：{rid} r{record['revision']}；归属：{record['owner_id']}；角色：{role(record)}", record['body_markdown']]
    lines.extend(['结构化记录：', '```json', _json(record['payload']), '```', '来源：', '```json', _json(record['sources']), '```'])
    if record.get('provenance_gap'):
        lines.append('已知缺口：' + record['provenance_gap'])
    return '\n\n'.join(line for line in lines if line != '')


def summary_projection(record):
    """Use saved technical descriptions/maps without repeating report prose.

    This is an explicitly short, deterministic projection, not an AI summary.
    Complete records remain available through full_ids or ordinary expand.
    """
    from .technical_units import is_unit, description_text
    head = f"### {record['title']}\n\n身份：{record['record_id']} r{record['revision']}；归属：{record['owner_id']}；总结材料短表示"
    payload = record['payload']
    if is_unit(record):
        return head + '\n\n' + description_text(record)
    if record['kind'] == 'detail':
        # v2 has no separate applicability object. Keep its authored method,
        # results and every limitation, and disclose the absent explicit scope.
        values = {key: payload[key] for key in ('question', 'method', 'results', 'limitations') if key in payload}
        return head + '\n\n' + _json(values) + '\n\n旧版未单列适用/不适用字段；需按原记录限制判断迁移。'
    if record['kind'] == 'map':
        values = {key: payload[key] for key in ('topic', 'next_steps', 'coverage') if key in payload}
        references = []
        for ref in iter_refs(payload):
            value = ref_metadata(ref)
            if value not in references:
                references.append(value)
        return head + '\n\n研究导航（未展开地图正文或嵌套报告）：\n' + _json(values) + '\n\n固定导航引用：\n' + _json(references)
    return None


def summary_fair_order(snapshot, candidates, request, effective):
    """Reserve one real readable item per selected owner before using leftovers.

    A small full/validated-short item creates an owner coverage floor. Remaining
    candidates are round-robin, starting with owners without a reserved item.
    No text is truncated, full requests are never shortened, and the normal
    final admission still enforces the global budget, stage and exclusions.
    """
    groups = {oid: [] for oid in request['owner_ids'] if oid not in request['exclude_ids']}
    for item in candidates:
        groups.setdefault(item['owner_id'], []).append(item)
    active = [oid for oid, items in groups.items() if items]
    if not active:
        return candidates
    quota = max(0, (effective - len(PART_SEPARATOR) * (len(active) - 1)) // len(active))
    reserved, chosen, covered = [], set(), set()
    for oid in active:
        variants = []
        for order, item in enumerate(groups[oid]):
            text = normalize_context_text(item['text'])
            variants.append((len(text), order, item))
            if len(text) > quota and item['canonical_id'] not in request['full_ids']:
                short = _short(snapshot, item, request)
                if short is not None:
                    variants.append((len(short), order, {**item, 'text': short, 'content_mode': 'short'}))
        fitting = [entry for entry in variants if entry[0] <= quota]
        substantive = [entry for entry in fitting if (entry[2].get('record') or {}).get('kind') in {'detail', 'experience', 'event', 'narrative', 'overview'}]
        fitting = substantive or fitting
        if fitting:
            _length, _order, item = min(fitting, key=lambda entry: (entry[0], entry[1]))
            reserved.append(item)
            chosen.add(item['canonical_id'])
            covered.add(oid)
    queues = {oid: [item for item in groups[oid] if item['canonical_id'] not in chosen] for oid in active}
    rotation = [oid for oid in active if oid not in covered] + [oid for oid in active if oid in covered]
    while any(queues.values()):
        for oid in rotation:
            if queues[oid]:
                reserved.append(queues[oid].pop(0))
    return reserved


def _request(service, request):
    value = deepcopy(request)
    previous = value.pop('feedback_from', None)
    if previous is not None:
        previous = previous.get('manifest', previous)
        if previous.get('expansion_count', 0) >= 2 or previous.get('stage') == 'wide':
            raise MemoryError('INVALID_ARGUMENT', '已达到两次自动扩展上限', {'code': 'EXPANSION_LIMIT', 'expansion_count': 2})
        inherited = {**previous['selection'], 'query': previous.get('query', ''),
                     'purpose': previous['purpose'], 'scope': previous.get('scope'),
                     'budget': previous['budget']['requested'],
                     'refs': deepcopy(previous.get('requested_refs', previous.get('source_refs', [])))}
        for key, old in inherited.items():
            if key in value and value[key] != old:
                raise MemoryError('INVALID_ARGUMENT', '反馈扩展不能改变原范围、目的或预算', {'field': key})
        value.update(inherited)
        value['stage'] = {'focus': 'investigate', 'investigate': 'wide'}[previous['stage']]
        value['expansion_count'] = previous.get('expansion_count', 0) + 1
    value.setdefault('purpose', 'exploration')
    value.setdefault('stage', 'focus')
    value.setdefault('expansion_count', 0)
    value.setdefault('query', '')
    value.setdefault('scope', None)
    value.setdefault('budget', 16000)
    if value['purpose'] not in {'exploration', 'formal'} or value['stage'] not in STAGES:
        raise MemoryError('INVALID_ARGUMENT', '未知上下文目的或阶段')
    if value['purpose'] == 'formal' and not value.get('scope'):
        raise MemoryError('INVALID_ARGUMENT', '正式材料包必须提供 scope')
    if type(value['budget']) is not int or value['budget'] < 0:
        raise MemoryError('INVALID_ARGUMENT', '上下文预算必须为非负 Unicode 码点数')
    for key in ('include_ids', 'full_ids', 'exclude_ids', 'owner_ids', 'owner_types'):
        value.setdefault(key, [])
        if not isinstance(value[key], list) or not all(isinstance(x, str) for x in value[key]):
            raise MemoryError('INVALID_ARGUMENT', '选择必须为 ID/类型字符串数组', {'field': key})
        value[key] = list(dict.fromkeys(value[key]))
    config_path = service.root / 'retrieval/config.json'
    hard = 16000
    if config_path.exists():
        try:
            hard = json.loads(config_path.read_text(encoding='utf-8-sig')).get('context_chars', hard)
        except (ValueError, OSError) as exc:
            raise MemoryError('INVALID_SCHEMA', '检索硬预算配置无法读取') from exc
    if type(hard) is not int or hard < 0:
        raise MemoryError('INVALID_SCHEMA', '工作区硬预算必须为非负整数')
    value['hard_limit'] = hard
    return value


def _visible(record, request):
    excluded = set(request['exclude_ids'])
    if record['record_id'] in excluded or record['owner_id'] in excluded or record['sensitivity'] == 'restricted':
        return False
    chosen = set(request['include_ids']) | set(request['full_ids'])
    chosen_owners = set(request['owner_ids']) | {request.get('owner_id')}
    return record['owner_id'] in chosen_owners or record['record_id'] in chosen or record['owner_id'] in chosen or record['discovery'] == 'workspace_summary'


def _item(snapshot, requested, request, seen=None):
    seen = set() if seen is None else seen
    ref = deepcopy(requested) if isinstance(requested, dict) else None
    tid = ref['target_id'] if ref else requested
    if tid in request['exclude_ids']:
        raise MemoryError('ACCESS_DENIED', '对象已明确排除')
    if tid in seen:
        raise MemoryError('INVALID_SCHEMA', '规范表示引用形成循环')
    seen.add(tid)
    if tid in snapshot.views:
        owner, state = snapshot.owner(tid)
        if tid in request['exclude_ids']:
            raise MemoryError('ACCESS_DENIED', '归属已排除')
        access = snapshot.adapter.access_errors(tid)
        if access:
            raise MemoryError('ACCESS_DENIED', '原生对象的来源权限或登记已变化', errors=access)
        if _depends_on_excluded(snapshot, {'evidence_refs': [{'target_kind': 'owner', 'target_id': tid}]}, set(request['exclude_ids'])):
            raise MemoryError('ACCESS_DENIED', '原生对象依据包含明确排除的来源')
        if not ref:
            import evidence
            node = snapshot.adapter.legacy.nodes.get(tid)
            ref = {'target_kind': 'owner', 'target_id': tid, 'revision': None,
                   'sha256': node['fingerprint'] if node else owner['fingerprint'], 'locator': 'metadata', 'relation': 'references'}
        snapshot.resolve(ref)
        return {'canonical_id': tid, 'owner_id': tid, 'ref': ref, 'role': 'run_attempt' if owner['owner_type'] == 'run' else 'owner',
                'text': f"### {owner['title']}\n\n身份：{tid}\n\n原生记录：\n```json\n{_json(owner['native_data'])}\n```", 'record': None}
    if (ref and ref['target_kind'] == 'claim') or (isinstance(tid, str) and tid.startswith('CLM-')):
        value = snapshot.adapter.resolve_claim(tid)
        snapshot.owner(value['owner_id'])
        parent = value.get('record')
        if parent and not _visible(parent, request):
            raise MemoryError('ACCESS_DENIED', '结论归属记录未被选择或不可见')
        if value['owner_id'] in request['exclude_ids']:
            raise MemoryError('ACCESS_DENIED', '结论归属已排除')
        access = snapshot.adapter.access_errors(tid)
        if access:
            raise MemoryError('ACCESS_DENIED', '结论来源权限或登记已变化', errors=access)
        # Legacy path references need the same explicit exclusion check as
        # modern file IDs before their derived claim text can be displayed.
        claim_refs = list(value['claim'].get('evidence_refs', []))
        if value.get('legacy'):
            claim_refs = []
            for old_ref in value['claim'].get('evidence_refs', []):
                try:
                    claim_refs.append(_legacy_navigation_ref(snapshot, old_ref))
                except MemoryError:
                    pass  # The one-hop navigation reports unresolved metadata.
        if _depends_on_excluded(snapshot, {'evidence_refs': claim_refs}, set(request['exclude_ids'])):
            raise MemoryError('ACCESS_DENIED', '结论依据包含明确排除的来源')
        ref = ref or {'target_kind': 'claim', 'target_id': tid, 'revision': None, 'sha256': value['sha256'], 'locator': 'statement', 'relation': 'references'}
        snapshot.resolve(ref)
        state = snapshot.adapter.claim_state(tid, request.get('scope') or value['claim'].get('scope'))
        return {'canonical_id': tid, 'owner_id': value['owner_id'], 'ref': ref, 'role': 'claim',
                'text': f"### {tid}\n\n角色：claim；复核状态：{state['review_state']}；当前有效：{state['effective_validity']}\n\n{_json(value['claim'])}", 'record': None}
    if ref and ref['target_kind'] == 'file':
        # 原件只通过服务来源登记定位；二进制原件由 L0/source 记录说明取得方式。
        snapshot.resolve(ref)
        path, _metadata = snapshot.service._file(ref)
        try:
            body = path.read_text(encoding='utf-8-sig')
        except UnicodeError as exc:
            raise MemoryError('CAPABILITY_UNAVAILABLE', '二进制来源需要已保存的受控表示') from exc
        return {'canonical_id': tid, 'owner_id': None, 'ref': ref, 'role': 'direct_source',
                'text': f"### {tid}\n\n登记定位：{_metadata['path']}\n\n固定来源：{ref['sha256']}\n\n{body}", 'record': None}
    record = snapshot.record(tid, ref.get('revision') if ref else None)
    if not _visible(record, request):
        raise MemoryError('ACCESS_DENIED', '记录被排除或不在选择范围')
    if _depends_on_excluded(snapshot, {'evidence_refs': list(iter_refs({'sources': record['sources'], 'payload': record['payload']}))}, set(request['exclude_ids'])):
        raise MemoryError('ACCESS_DENIED', '完整记录包含明确排除的来源，不能删掉边界后继续输出')
    access = [error for error in snapshot.adapter.access_errors(record['record_id'], revision=record['revision'])
              if error['code'] in {'ACCESS_DENIED', 'UNSAFE_PATH', 'UNRESOLVED_REFERENCE', 'NOT_FOUND'}]
    if access:
        # 正文被权限/登记门槛阻止时，仍报告其余固定依据的状态码；
        # 不让首个缺失来源掩盖另一输入变化或已撤回的答案。
        raise MemoryError('ACCESS_DENIED', '派生记录的来源权限或登记已变化',
                          errors=access + source_risks(snapshot, record, request['exclude_ids']))
    if record['kind'] == 'representation':
        return _item(snapshot, record['payload']['target'], request, seen)
    ref = ref or fixed_ref(record)
    snapshot.resolve(ref)
    from .technical_units import is_unit, description_text
    short = request.get('_unit_descriptions_only', False) and is_unit(record) and record['record_id'] not in request['full_ids']
    text = (f"### {record['title']}\n\n身份：{record['record_id']} r{record['revision']}；归属：{record['owner_id']}\n\n" + description_text(record)
            if short else render_record(record))
    if request.get('_summary_mode') and record['record_id'] not in request['full_ids']:
        projected = summary_projection(record)
        if projected is not None:
            text, short = projected, True
    return {'canonical_id': record['record_id'], 'owner_id': record['owner_id'], 'ref': ref,
            'role': role(record), 'text': text, 'record': record, 'content_mode': 'short' if short else 'full'}


def _short(snapshot, item, request):
    record = item['record']
    if not record:
        return None
    from .technical_units import is_unit, description_text
    if is_unit(record):
        return normalize_context_text(f"### {record['title']}\n\n身份：{record['record_id']} r{record['revision']}；归属：{record['owner_id']}；仅检索描述\n\n" + description_text(record))
    boundary = {key: record['payload'][key] for key in ('applicable', 'prohibited', 'failure_modes', 'retry_conditions', 'cannot_infer') if key in record['payload']}
    candidates = []
    for representation in snapshot.all_records():
        if representation['kind'] != 'representation' or not _visible(representation, request):
            continue
        payload = representation['payload']
        target = payload['target']
        if target['target_id'] != item['canonical_id'] or target.get('revision') != record['revision']:
            continue
        if any(ref not in payload['boundary_refs'] for ref in record['sources']):
            continue
        text = f"### {record['title']}\n\n身份：{record['record_id']} r{record['revision']}；归属：{record['owner_id']}；角色：{item['role']}；使用已保存短表示\n\n{payload['text']}\n\n适用与禁用边界：\n{_json(boundary)}\n\n固定来源：\n{_json(record['sources'])}"
        text = normalize_context_text(text)
        candidates.append((len(text), representation['record_id'], text, representation['owner_id']))
    if candidates:
        chosen = min(candidates)
        snapshot.owner(chosen[3])
        return chosen[2]
    return None


def source_risks(snapshot, record, excluded=()):
    """对检查点、结果的固定依赖逐层回源；循环按版本去重，不执行内容。"""
    queue = list(iter_refs({'sources': record.get('sources', []), 'payload': record.get('payload', {})}))
    visited, risks = set(), []
    while queue:
        ref = queue.pop(0)
        key = (ref['target_kind'], ref['target_id'], ref.get('revision'), ref.get('sha256'))
        if key in visited:
            continue
        visited.add(key)
        if len(visited) > 512:
            risks.append({'target_id': record['record_id'], 'code': 'REFERENCE_LIMIT', 'affected_ids': [record['record_id']]})
            break
        if ref['target_id'] in excluded:
            risks.append({'target_id': ref['target_id'], 'code': 'EXCLUDED_SOURCE', 'affected_ids': [record['record_id']]})
            continue
        try:
            value = snapshot.resolve(ref)
            if ref['target_kind'] == 'record':
                queue.extend(iter_refs({'sources': value['sources'], 'payload': value['payload']}))
                for claim in value['payload'].get('claims', []):
                    state = snapshot.adapter.claim_state(claim['claim_id'])
                    if state['review_state'] in {'retracted', 'superseded', 'disputed'}:
                        risks.append({'target_id': claim['claim_id'], 'code': 'EVIDENCE_INELIGIBLE',
                                      'affected_ids': [record['record_id']]})
            elif ref['target_kind'] == 'claim':
                state = snapshot.adapter.claim_state(ref['target_id'])
                if state['review_state'] in {'retracted', 'superseded', 'disputed'}:
                    risks.append({'target_id': ref['target_id'], 'code': 'EVIDENCE_INELIGIBLE', 'affected_ids': [record['record_id']]})
        except MemoryError as exc:
            risks.append({'target_id': ref['target_id'], 'code': exc.code, 'affected_ids': [record['record_id']]})
    return risks


def _depends_on_excluded(snapshot, claim, excluded):
    """排除选择沿固定依据闭包传播，避免中间记录隐藏被排除的来源。"""
    if not excluded:
        return False
    queue = list(claim.get('evidence_refs', []))
    seen = set()
    while queue:
        ref = queue.pop(0)
        if 'target_kind' not in ref:
            try:
                ref = _legacy_navigation_ref(snapshot, ref)
            except MemoryError:
                continue  # Source availability is reported by its own gate.
        key = (ref['target_kind'], ref['target_id'], ref.get('revision'), ref.get('sha256'))
        if key in seen:
            continue
        seen.add(key)
        if len(seen) > 512 or ref['target_id'] in excluded:
            return True
        try:
            if ref['target_kind'] == 'record':
                record = snapshot.record(ref['target_id'], ref['revision'])
                if record['owner_id'] in excluded:
                    return True
                queue.extend(iter_refs({'sources': record['sources'], 'payload': record['payload']}))
            elif ref['target_kind'] == 'claim':
                if ref['target_id'] in snapshot.adapter.legacy.nodes:
                    value = snapshot.adapter.resolve_claim(ref['target_id'])
                    claim_value, claim_owner, parent_sources = value['claim'], value['owner_id'], []
                else:
                    containers = snapshot.adapter.access_claim_containers(ref['target_id'], ref.get('sha256'))
                    claim_value, parent = containers[0]
                    claim_owner, parent_sources = parent['owner_id'], parent['sources']
                    for historical_claim, historical_parent in containers[1:]:
                        queue.extend(historical_claim.get('evidence_refs', []))
                        queue.extend(historical_parent['sources'])
                snapshot.owner(claim_owner)
                if claim_owner in excluded:
                    return True
                queue.extend(claim_value.get('evidence_refs', []))
                queue.extend(parent_sources)
            elif ref['target_kind'] == 'owner':
                owner, _state = snapshot.owner(ref['target_id'])
                native = owner['native_data']
                queue.extend(native.get('dependencies', []))
                queue.extend(native.get('inputs', []))
                queue.extend(native.get('artifacts', []))
                for nested in native.get('claims', []):
                    queue.extend(nested.get('evidence_refs', []))
        except MemoryError:
            # 真正失效/无法解析仍由正式证据门槛给出结构化拒绝。
            continue
    return False


def _formal_refs(snapshot, items, request):
    """仅筛选允许的导航路径；最终科学门槛仍全部交给 EvidenceAdapter。"""
    excluded = set(request['exclude_ids'])
    queue, visited, result = [item['ref'] for item in items], set(), []
    while queue:
        ref = queue.pop(0)
        tid = ref['target_id']
        key = (tid, ref.get('revision'), ref.get('sha256'))
        if key in visited or tid in excluded:
            continue
        visited.add(key)
        # _reference 检查旧修订是否仍可正式使用，不把固定 r1 偷换成 r2。
        try:
            snapshot.adapter._reference(ref)
        except MemoryError:
            result.append(ref)  # 由正式输出统一给出拒绝码。
            continue
        if ref['target_kind'] == 'claim':
            value = snapshot.adapter.resolve_claim(tid)
            if value['owner_id'] in excluded:
                continue
            if _depends_on_excluded(snapshot, value['claim'], excluded):
                continue
            snapshot.owner(value['owner_id'])
            result.append(ref)
        elif ref['target_kind'] == 'record':
            record = snapshot.record(tid, ref['revision'])
            if not _visible(record, request) or record['kind'] == 'association':
                continue
            if record['kind'] in {'event', 'narrative', 'experience', 'overview'}:
                for claim in record['payload']['claims']:
                    value = snapshot.adapter.resolve_claim(claim['claim_id'])
                    queue.append({'target_kind': 'claim', 'target_id': claim['claim_id'], 'revision': None,
                                  'sha256': value['sha256'], 'locator': 'statement', 'relation': 'references'})
            else:
                queue.extend(iter_refs({'sources': record['sources'], 'payload': record['payload']}))
        elif ref['target_kind'] == 'owner':
            owner, _state = snapshot.owner(tid)
            ids = {cid for cid, (_claim, record) in snapshot.adapter.claims.items() if record['owner_id'] == tid}
            ids.update(cid for cid, node in snapshot.adapter.legacy.nodes.items() if node.get('owner') == tid)
            for cid in sorted(ids):
                value = snapshot.adapter.resolve_claim(cid)
                queue.append({'target_kind': 'claim', 'target_id': cid, 'revision': None,
                              'sha256': value['sha256'], 'locator': 'statement', 'relation': 'references'})
    return result


def _legacy_navigation_ref(snapshot, ref):
    """Translate a declared legacy edge without minting a fresh source hash.

    Legacy records identify files by path. Only a unique registered file may
    become a clickable file Ref; the edge's original hash remains binding.
    Registry matching reads metadata only, before the service checks access.
    """
    return legacy_ref(snapshot.service, snapshot.adapter, ref)


def _navigation_refs(snapshot, item, request):
    """One-hop metadata for displayed items, separate from rendered sources.

    Do not render target bodies, recurse through targets, or silently refresh a
    fixed hash. Every emitted target has passed current exclusion, visibility,
    registration and fixed-version checks. A later click repeats those checks.
    """
    candidates, missing = [], []
    tid = item['canonical_id']
    kind = item['ref']['target_kind']
    if kind == 'record':
        record = item['record'] or snapshot.record(tid, item['ref']['revision'])
        candidates.extend(iter_refs({'sources': record['sources'], 'payload': record['payload']}))
        # A record's individually reviewable claims are legitimate next steps.
        for claim in record['payload'].get('claims', []):
            candidates.append({'target_kind': 'claim', 'target_id': claim['claim_id'], 'revision': None,
                'sha256': contracts.canonical_hash(claim), 'locator': '', 'relation': 'references'})
    elif kind == 'claim':
        value = snapshot.adapter.resolve_claim(tid)
        if value.get('record'):
            candidates.extend(iter_refs({'sources': value['record']['sources'], 'claims': value['claim']}))
        else:
            for old_ref in value['claim'].get('evidence_refs', []):
                try:
                    candidates.append(_legacy_navigation_ref(snapshot, old_ref))
                except MemoryError as exc:
                    missing.append({'target_id': tid, 'code': exc.code, 'affected_ids': [tid]})
    elif kind == 'owner':
        owner, _state = snapshot.owner(tid)
        native = owner['native_data']
        for claim in native.get('claims', []):
            value = snapshot.adapter.resolve_claim(claim['claim_id'])
            candidates.append({'target_kind': 'claim', 'target_id': claim['claim_id'], 'revision': None,
                'sha256': value['sha256'], 'locator': '', 'relation': 'references'})
        for old_ref in [*native.get('dependencies', []), *native.get('inputs', []), *native.get('artifacts', [])]:
            try:
                candidates.append(_legacy_navigation_ref(snapshot, old_ref))
            except MemoryError as exc:
                missing.append({'target_id': tid, 'code': exc.code, 'affected_ids': [tid]})
    result, seen = [], set()
    excluded = set(request['exclude_ids'])
    for ref in candidates:
        target = ref['target_id']
        key = (ref['target_kind'], target, ref.get('revision'), ref.get('sha256'))
        if target == tid or key in seen:
            continue
        seen.add(key)
        if len(seen) > 512:
            missing.append({'target_id': tid, 'code': 'REFERENCE_LIMIT'})
            break
        if target in excluded:
            missing.append({'target_id': target, 'code': 'EXCLUDED_SOURCE', 'affected_ids': [tid]})
            continue
        try:
            # Check ownership before resolving file hashes or reading bodies.
            if ref['target_kind'] == 'record':
                record = snapshot.record(target, ref['revision'])
                if not _visible(record, request):
                    raise MemoryError('ACCESS_DENIED', '导航目标记录不可见')
            elif ref['target_kind'] == 'claim':
                value = snapshot.adapter.resolve_claim(target)
                if value['owner_id'] in excluded or (value.get('record') and not _visible(value['record'], request)):
                    raise MemoryError('ACCESS_DENIED', '导航目标结论归属不可见')
            snapshot.resolve(ref)
            if ref['target_kind'] in {'record', 'claim', 'owner'}:
                denied = snapshot.adapter.access_errors(ref)
                if denied:
                    raise MemoryError('ACCESS_DENIED', '导航目标来源权限已变化', errors=denied)
            result.append(ref_metadata(ref))
        except MemoryError as exc:
            missing.append({'target_id': target, 'code': exc.code, 'affected_ids': [tid]})
    return result, missing


def expand(service, refs, selection=None, budget=None, *, snapshot=None, unit_descriptions_only=False, summary_mode=False):
    """按固定引用整条展开；full 不降级为摘要，exclude 始终先执行。"""
    service = service_for(service)
    request = deepcopy(selection or {})
    if budget is not None:
        request['budget'] = budget
    request = _request(service, request)
    request['_unit_descriptions_only'] = unit_descriptions_only
    request['_summary_mode'] = summary_mode
    snapshot = snapshot or Snapshot(service)
    effective = min(request['budget'], request['hard_limit'])
    manifest = {'schema_version': 1, 'packet_id': 'PKT-' + str(uuid.uuid4()), 'generated_at': service.clock(),
                'query': request['query'], 'purpose': request['purpose'], 'scope': request['scope'],
                'stage': request['stage'], 'expansion_count': request['expansion_count'],
                'selection': {key: deepcopy(request.get(key, [] if key.endswith('s') else None)) for key in CHOICES},
                'budget': {'requested': request['budget'], 'hard_limit': request['hard_limit'], 'effective': effective, 'used': 0},
                'items': [], 'omitted': [], 'missing': [], 'navigation_refs': [], 'required_not_full': [], 'basis_heads': {},
                'status': 'complete', 'snapshot_kind': 'per_owner_verified_heads', 'execution_started': False}
    # 只保留身份/修订，供后续扩展重试未放入正文的固定命中；自由 locator
    # 不可成为 manifest 中绕过字符预算的隐含正文。
    manifest['requested_refs'] = [ref_metadata(ref) if isinstance(ref, dict) else ref for ref in refs]
    by_id, order = {}, []
    for requested in refs:
        tid = requested.get('target_id') if isinstance(requested, dict) else requested
        if tid in request['exclude_ids']:
            manifest['omitted'].append({'target_id': tid, 'reason': 'excluded'})
            continue
        try:
            item = _item(snapshot, requested, request)
            if item['canonical_id'] not in by_id:
                if item['record']:
                    risks = source_risks(snapshot, item['record'], request['exclude_ids'])
                    manifest['missing'].extend(risks)
                    if risks:
                        item['text'] += '\n\n当前依据缺口：\n' + '\n'.join(f"- {risk['target_id']}: {risk['code']}" for risk in risks)
                order.append(item['canonical_id'])
                by_id[item['canonical_id']] = item
        except MemoryError as exc:
            manifest['missing'].append({'target_id': tid, 'code': exc.code})
            manifest['missing'].extend({'target_id': error.get('target_id', tid), 'code': error.get('code', exc.code),
                                         'affected_ids': [tid], 'path': error.get('path', [])} for error in exc.errors)
            if tid in request['full_ids']:
                manifest['required_not_full'].append(tid)
    # 明确 full 优先放置，但不改变相同优先级的查询顺序。
    order.sort(key=lambda tid: tid not in request['full_ids'])
    parts = []
    used, shown_owners = 0, set()
    if request['purpose'] == 'formal':
        projected = snapshot.adapter.formal_projection(_formal_refs(snapshot, [by_id[tid] for tid in order], request), request['scope'])
        for rejected in projected['rejected']:
            manifest['missing'].append({'target_id': rejected['canonical_id'],
                                        'code': 'EVIDENCE_INELIGIBLE'})
        candidates = [{'canonical_id': row['canonical_id'], 'owner_id': row['owner_id'], 'role': 'formal_claim',
                       'text': row['text'], 'ref': {'target_kind': 'claim', 'target_id': row['canonical_id'],
                            'revision': None, 'sha256': row['sha256'], 'relation': 'supports'}, 'record': None} for row in projected['claims']]
    else:
        candidates = [by_id[tid] for tid in order]
    if summary_mode:
        candidates = summary_fair_order(snapshot, candidates, request, effective)
    for item in candidates:
        tid = item['canonical_id']
        # 只采纳当前允许集合的正式 claim，避免 map 的导航穿过排除节点。
        if tid in request['exclude_ids'] or item['owner_id'] in request['exclude_ids']:
            manifest['omitted'].append({'target_id': tid, 'reason': 'excluded'})
            continue
        limit, _hops, owner_limit = STAGES[request['stage']]
        if len(parts) >= limit or (item['owner_id'] not in shown_owners and len(shown_owners) >= owner_limit):
            manifest['omitted'].append({'target_id': tid, 'reason': 'stage_limit'})
            if tid in request['full_ids']:
                manifest['required_not_full'].append(tid)
            continue
        text, mode = normalize_context_text(item['text']), item.get('content_mode', 'full')
        separator = len(PART_SEPARATOR) if parts else 0
        if used + separator + len(text) > effective and tid not in request['full_ids'] and request['purpose'] != 'formal':
            alternative = _short(snapshot, item, request)
            if alternative is not None:
                text, mode = alternative, 'short'
        if used + separator + len(text) > effective:
            manifest['omitted'].append({'target_id': tid, 'reason': 'budget'})
            if tid in request['full_ids']:
                manifest['required_not_full'].append(tid)
            continue
        parts.append(text)
        used += separator + len(text)
        if item['owner_id']:
            shown_owners.add(item['owner_id'])
            snapshot.owner(item['owner_id'])
        manifest['items'].append({'canonical_id': tid, 'owner_id': item['owner_id'], 'role': item['role'],
                                  'ref': ref_metadata(item['ref']), 'mode': mode, 'codepoints': len(text)})
        navigation, missing = _navigation_refs(snapshot, item, request)
        manifest['navigation_refs'].extend(ref for ref in navigation if ref not in manifest['navigation_refs'])
        manifest['missing'].extend(missing)
    # 明确选择但并未出现在输入命中的 full，不能悄悄消失。
    covered = {item['canonical_id'] for item in manifest['items'] if item['mode'] == 'full'}
    for tid in request['full_ids']:
        if tid not in request['exclude_ids'] and tid not in covered:
            manifest['required_not_full'].append(tid)
    manifest['required_not_full'] = list(dict.fromkeys(manifest['required_not_full']))
    if manifest['required_not_full']:
        manifest['status'] = 'insufficient_budget' if any(x['reason'] == 'budget' for x in manifest['omitted']) else 'incomplete'
    elif manifest['missing'] or manifest['omitted']:
        manifest['status'] = 'partial'
    manifest['basis_heads'] = snapshot.heads()
    manifest['source_refs'] = [deepcopy(item['ref']) for item in manifest['items']]
    snapshot.recheck(request.get('basis_heads'))
    context = PART_SEPARATOR.join(parts)
    manifest['budget']['used'] = len(context)
    return {'context_text': context, 'manifest': manifest}


def build_context(service, request, *, snapshot=None):
    """复用统一检索；显式 refs 可直接展开，绝不再实现第二套排名。"""
    service = service_for(service)
    normalized = _request(service, request)
    refs = list(normalized.get('refs', []))
    refs.extend(normalized['full_ids'])
    refs.extend(normalized['include_ids'])
    if normalized.get('query'):
        from . import search
        search_request = {key: value for key, value in normalized.items() if key in
                          {'query', 'purpose', 'scope', 'owner_id', 'owner_types', 'include_ids', 'full_ids', 'exclude_ids', 'stage', 'budget', 'limit', 'history', 'vector'}}
        search_request['include_ids'] = list(dict.fromkeys([*search_request.get('include_ids', []), *normalized['owner_ids']]))
        search_request.setdefault('vector', 'off')
        result = search.search(service.root, search_request, record=False)
        refs.extend(row.get('source_ref') or row.get('ref') or row['canonical_id'] for row in result['candidates'])
    return expand(service, refs, normalized, snapshot=snapshot, unit_descriptions_only=True)
