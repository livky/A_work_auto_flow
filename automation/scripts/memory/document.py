"""按当前归属及显式引用组装研究文稿；不建立全工作区证据图。

这里只提供可审阅的研究内容，不宣布结论已通过正式准入。原始证据保持
只读；未取得的固定来源显式显示缺口，权限撤销则隐藏依赖它的正文。
"""
from copy import deepcopy
import base64
import hashlib
import time
import re

from . import owners, contracts
from .errors import MemoryError
from .evidence_adapter import iter_refs


class Reader:
    """一次请求的局部读取集；身份清单仅枚举一次，正文按引用闭包读取。"""
    def __init__(self, service, *, views=None):
        self.service = service
        self.views = views if views is not None else {v['owner_id']: v for v in owners.list_owners(service.root, metadata_only=True)}
        self.states, self.checked, self.file_checks, self.used = {}, set(), {}, set()
        self.record_owners = {}
        self.registry_path = owners.safe_path(service.root, 'retrieval/sources.json')
        self.registry_hash = owners._hash(self.registry_path) if self.registry_path.is_file() else None

    def owner(self, oid):
        view = self.views.get(oid)
        if view is None:
            raise MemoryError('NOT_FOUND', '研究归属或引用不存在', {'target_id': oid})
        owners.require_readable_owner(view)
        self.used.add(oid)
        return view

    def state(self, oid):
        view = self.owner(oid)
        if oid not in self.states:
            self.states[oid] = self.service.store.read_snapshot(view)
            self.record_owners.update({rid: oid for rid in self.states[oid]['records']})
        return self.states[oid]

    def record(self, ref):
        rid = ref['target_id']
        oid = self.record_owners.get(rid)
        if oid is None:
            # Cross-owner references are uncommon. Locate them in immutable
            # HEAD manifests without opening unrelated record bodies.
            for candidate, view in self.views.items():
                if view['native_data'].get('sensitivity') == 'restricted':
                    continue
                head_path = self.service.store.path(view, 'HEAD.json')
                if not head_path.is_file():
                    continue
                head = self.service.store.read_json(head_path)
                manifest = self.service.store._manifest(view, head['commit_id'], head['manifest_hash'])
                if rid in manifest['record_heads']:
                    if oid is not None:
                        raise MemoryError('INTEGRITY_ERROR', '重复记录身份')
                    oid = candidate
            if oid is None:
                raise MemoryError('NOT_FOUND', '固定记录不存在', {'target_id': rid})
        current = self.state(oid)['records'][rid]
        if current['sensitivity'] == 'restricted':
            raise MemoryError('ACCESS_DENIED', '固定记录当前已限制访问')
        record = current if current['revision'] == ref['revision'] else self.service.store.read_record(self.owner(oid), rid, ref['revision'])
        if record['sensitivity'] == 'restricted':
            raise MemoryError('ACCESS_DENIED', '固定修订已限制访问')
        if ref.get('sha256') and ref['sha256'] != record['record_hash']:
            raise MemoryError('STALE_BASIS', '固定记录指纹不匹配')
        return record

    def check_ref(self, ref):
        # A failed recursive check must never leave an apparently verified
        # cache entry for a later record citing that same revoked source.
        try:
            return self._check_ref(ref)
        except MemoryError:
            self.checked.clear()
            raise

    def _check_ref(self, ref):
        """验证身份和当前授权；循环引用只检查一次，不递归执行建议。"""
        import evidence
        key = (ref['target_kind'], ref['target_id'], ref.get('revision'), ref.get('sha256'))
        if key in self.checked:
            return
        self.checked.add(key)
        kind = ref['target_kind']
        if kind == 'record':
            record = self.record(ref)
            for child in iter_refs({'sources': record['sources'], 'payload': record['payload']}):
                self.check_ref(child)
        elif kind == 'file':
            path, _meta = self.service._file(ref)
            actual = evidence.sha256(path)
            self.file_checks[key] = (deepcopy(ref), actual)
            if actual != ref.get('sha256'):
                raise MemoryError('STALE_BASIS', '固定来源已变化', {'target_id': ref['target_id']})
        elif kind == 'owner':
            view = self.owner(ref['target_id'])
            raw = view['native_data']
            # Legacy evidence cards use the existing review-excluding hash;
            # other owner adapters use the byte hash of their native card.
            actual = (evidence.fingerprint(raw) if view['native_ref'].get('id_field') in
                      {'run_id', 'research_id', 'module_id', 'evidence_id'} else view['fingerprint'])
            if ref.get('sha256') and actual != ref['sha256']:
                raise MemoryError('STALE_BASIS', '固定归属版本已变化')
            for child in raw.get('dependencies', []):
                target = child.get('target') if isinstance(child, dict) else None
                if target in self.views:
                    self.check_ref({'target_kind': 'owner', 'target_id': target,
                                    'sha256': child.get('sha256'), 'revision': None})
                elif target:
                    try:
                        evidence.reference_path(self.service.root, target)
                    except ValueError as exc:
                        raise MemoryError('ACCESS_DENIED', '归属引用当前不可读取') from exc
            # Check access to legacy input locators without loading raw logs or
            # large numeric artifacts merely to draw the research document.
            for child in [*raw.get('inputs', []), *raw.get('artifacts', [])]:
                target = child.get('path') or child.get('target') if isinstance(child, dict) else None
                if target:
                    try:
                        evidence.reference_path(self.service.root, target)
                    except ValueError as exc:
                        raise MemoryError('ACCESS_DENIED', '运行输入当前不可读取') from exc
        elif kind == 'claim':
            # Claims require the formal adapter's full provenance rules. This
            # fallback is explicit; ordinary detail/run references stay local.
            from .evidence_adapter import EvidenceAdapter
            adapter = EvidenceAdapter(self.service)
            if any(error['code'] in {'ACCESS_DENIED', 'UNSAFE_PATH'} for error in adapter.access_errors(ref)):
                raise MemoryError('ACCESS_DENIED', '结论固定来源当前不可读取')
            value = adapter.resolve_claim(ref['target_id'])
            if value['sha256'] != ref.get('sha256'):
                raise MemoryError('STALE_BASIS', '固定结论版本发生变化')
        else:
            raise MemoryError('INVALID_SCHEMA', '未知引用类型')

    def recheck(self):
        """返回前重验本次实际读取的卡片、HEAD、来源授权与指纹。"""
        import evidence
        registry = owners.safe_path(self.service.root, 'retrieval/sources.json')
        if (owners._hash(registry) if registry.is_file() else None) != self.registry_hash:
            raise MemoryError('STALE_BASIS', '研究读取期间来源登记发生变化')
        for oid in self.used:
            view = self.views[oid]
            path = owners.safe_path(self.service.root, view['native_ref']['path'])
            if evidence.sha256(path) != view['fingerprint']:
                raise MemoryError('STALE_BASIS', '研究读取期间对象登记发生变化')
            if oid in self.states:
                head_path = self.service.store.path(view, 'HEAD.json')
                head = self.service.store.read_json(head_path) if head_path.is_file() else None
                if head != self.states[oid]['head']:
                    raise MemoryError('STALE_BASIS', '研究读取期间 HEAD 发生变化')
        for ref, digest in self.file_checks.values():
            path, _ = self.service._file(ref)
            if evidence.sha256(path) != digest:
                raise MemoryError('STALE_BASIS', '研究读取期间来源发生变化')
        # A registry edit can revoke a legacy Run input even when its own
        # metadata stayed unchanged. Re-evaluate the visited owner access paths.
        visited = list(self.checked)
        self.checked = set()
        for kind, tid, revision, digest in visited:
            if kind == 'owner':
                self.check_ref({'target_kind': kind, 'target_id': tid, 'revision': revision, 'sha256': digest})
            elif kind == 'claim':
                self.check_ref({'target_kind': kind, 'target_id': tid,
                                'revision': revision, 'sha256': digest})


def document_order(record):
    """展示顺序只作导航，不改变保存时间或固定 Run：明确轮次优先。

    同批提交的 created_at 相同，不能以随机 UUID 决定第一、第二轮。
    未写轮次的记录仍按实际记录时间排序，再以标题自然数字序稳定破同分。
    """
    title = record['title']
    match = re.search(r'(?:第\s*)?([0-9]+|[一二三四五六七八九十]+)\s*轮', title)
    number = None
    if match:
        value = match[1]
        if value.isdecimal():
            number = int(value)
        else:
            digits = dict(zip('一二三四五六七八九', range(1, 10)))
            if '十' in value:
                left, right = value.split('十', 1)
                number = (digits.get(left, 1) * 10) + digits.get(right, 0)
            else:
                number = digits.get(value)
    natural = tuple((0, int(part)) if part.isdecimal() else (1, part.casefold())
                    for part in re.split(r'(\d+)', title) if part)
    return (0 if number is not None else 1, number or 0,
            record['payload'].get('occurred_at') or record['created_at'], natural, record['record_id'])


def resolve_report(reader, state, report_record_id=None):
    """Assemble fixed report blocks independently from current-record cards.

    Failed evidence hides the affected prose/detail, while retaining its place
    and explicit gap. A newer revision is never substituted into the narrative.
    """
    candidates = [r for r in state['records'].values() if r['kind'] == 'map'
                  and r['schema_version'] == 2 and r['payload'].get('report')
                  and r['sensitivity'] != 'restricted']
    candidates.sort(key=lambda r: (r.get('updated_at', r['created_at']), r['revision'], r['record_id']), reverse=True)
    summaries = [{k: r[k] for k in ('record_id', 'revision', 'title', 'created_at', 'updated_at') if k in r} for r in candidates]
    selected = next((r for r in candidates if r['record_id'] == report_record_id), None) if report_record_id else next(iter(candidates), None)
    if report_record_id and selected is None:
        raise MemoryError('NOT_FOUND', '所选报告不存在或不可读取')
    included, hints = set(), []
    coverage = {'included_detail_ids': [], 'uncovered_detail_ids': []}
    if selected is None:
        coverage['uncovered_detail_ids'] = sorted(r['record_id'] for r in state['records'].values() if r['kind'] == 'detail' and r['sensitivity'] != 'restricted')
        return None, summaries, coverage, hints
    raw = selected['payload']['report']
    errors = contracts.validate_report(raw) + contracts.validate_references(raw, {})
    if errors:
        raise MemoryError('INVALID_SCHEMA', '已保存报告编排不符合契约', errors=errors)
    report = {**deepcopy(raw), 'record_id': selected['record_id'], 'revision': selected['revision'], 'complete': True}
    base_refs = list(iter_refs({'sources': selected['sources'], 'payload': {
        key: value for key, value in selected['payload'].items() if key != 'report'}}))
    for section in report['sections']:
        for block in section['blocks']:
            issues = []
            refs = block['evidence_refs'] if block['type'] == 'prose' else [block['ref']]
            # General map sources remain applicable to every authored segment;
            # report block refs themselves are checked locally, not globally.
            for ref in [*base_refs, *refs]:
                try:
                    reader.check_ref(ref)
                    if ref['target_kind'] == 'record':
                        fixed = reader.record(ref)
                        current = reader.state(fixed['owner_id'])['records'][fixed['record_id']]
                        if current['revision'] != fixed['revision']:
                            hint = {'record_id': fixed['record_id'], 'revision': fixed['revision'], 'current_revision': current['revision']}
                            if hint not in hints:
                                hints.append(hint)
                except MemoryError as exc:
                    issues.append({'target_id': ref['target_id'], 'code': exc.code})
            if block['type'] == 'detail':
                included.add(block['ref']['target_id'])
                block['item'] = None
                if not issues:
                    record = reader.record(block['ref'])
                    if record['kind'] != 'detail':
                        issues.append({'target_id': record['record_id'], 'code': 'INVALID_SCHEMA'})
                    elif not record['body_markdown'].strip():
                        issues.append({'target_id': record['record_id'], 'code': 'DETAIL_MISSING'})
                    else:
                        block['item'] = {'id': record['record_id'], 'level': 'L1', 'record': deepcopy(record), 'source_issues': [], 'formal_eligibility': 'not_evaluated'}
            elif issues:
                block['markdown'] = ''
            block['source_issues'] = issues
            if issues:
                report['complete'] = False
    coverage['included_detail_ids'] = sorted(included)
    coverage['uncovered_detail_ids'] = sorted(r['record_id'] for r in state['records'].values() if r['kind'] == 'detail' and r['sensitivity'] != 'restricted' and r['record_id'] not in included)
    if coverage['uncovered_detail_ids']:
        report['complete'] = False
    return report, summaries, coverage, hints


def build_document(service, owner_id, report_record_id=None):
    started = time.perf_counter()
    reader = Reader(service)
    owner = reader.owner(owner_id)
    state = reader.state(owner_id)
    items, missing = [], []
    for record in state['records'].values():
        level = contracts.project_memory_level(record)
        if level not in {'L1', 'L2', 'L3', 'L4'} or record['sensitivity'] == 'restricted':
            continue
        issues, denied = [], False
        for ref in iter_refs({'sources': record['sources'], 'payload': record['payload']}):
            try:
                reader.check_ref(ref)
            except MemoryError as exc:
                issue = {'target_id': ref['target_id'], 'code': exc.code}
                issues.append(issue)
                denied = denied or exc.code in {'ACCESS_DENIED', 'UNSAFE_PATH'}
        if denied:
            missing.append({'record_id': record['record_id'], 'code': 'ACCESS_DENIED'})
            continue
        items.append({'id': record['record_id'], 'level': level, 'record': deepcopy(record),
                      'source_issues': issues, 'formal_eligibility': 'not_evaluated'})
    items.sort(key=lambda row: (row['level'], document_order(row['record'])))
    if not any(row['level'] == 'L1' for row in items):
        missing.append({'code': 'DETAIL_MISSING', 'message': '尚无 L1 详细研究记录；旧 Run 和经验不能替代计算过程。'})
    report, candidates, coverage, hints = resolve_report(reader, state, report_record_id)
    reader.recheck()
    return {'schema_version': 1, 'owner_id': owner_id, 'title': owner['title'],
            'items': items, 'missing': missing, 'generated_at': service.clock(),
            'report': report, 'report_candidates': candidates,
            'report_coverage': coverage, 'report_version_hints': hints,
            'basis_heads': {oid: snapshot['head']['commit_id'] if snapshot['head'] else 'none'
                            for oid, snapshot in reader.states.items()},
            'metrics': {'elapsed_ms': round((time.perf_counter() - started) * 1000, 2),
                        'inventory_owners': len(reader.views), 'read_memory_owners': len(reader.states),
                        'records': len(items)}, 'writes': 0}


def figure(service, owner_id, record_id, revision, figure_index):
    """只返回固定记录声明的本工作区栅格图片，拒绝 HTML/SVG 和任意路径。"""
    reader = Reader(service)
    reader.state(owner_id)
    record = reader.record({'target_id': record_id, 'revision': revision})
    if record['owner_id'] != owner_id or record['kind'] != 'detail':
        raise MemoryError('ACCESS_DENIED', '图片不属于所选详细研究记录')
    figures = record['payload'].get('figures', [])
    if type(figure_index) is not int or not 0 <= figure_index < len(figures):
        raise MemoryError('NOT_FOUND', '图片序号不存在')
    for ref in iter_refs({'sources': record['sources'], 'payload': record['payload']}):
        reader.check_ref(ref)
    ref = figures[figure_index]['ref']
    if ref['target_kind'] != 'file':
        raise MemoryError('INVALID_ARGUMENT', '图片必须引用已登记固定文件')
    path, _ = service._file(ref)
    if not path.is_relative_to(service.root):
        raise MemoryError('ACCESS_DENIED', '研究图片必须为工作区受控附件')
    if path.stat().st_size > 8 * 1024 * 1024:
        raise MemoryError('INVALID_ARGUMENT', '图片超过 8 MiB 展示上限')
    raw = path.read_bytes()
    mime = ('image/png' if raw.startswith(b'\x89PNG\r\n\x1a\n') else
            'image/jpeg' if raw.startswith(b'\xff\xd8\xff') else
            'image/webp' if raw[:4] == b'RIFF' and raw[8:12] == b'WEBP' else None)
    if mime is None or hashlib.sha256(raw).hexdigest() != ref['sha256']:
        raise MemoryError('INTEGRITY_ERROR', '图片格式或固定指纹不匹配')
    reader.recheck()
    return {'data_url': 'data:' + mime + ';base64,' + base64.b64encode(raw).decode('ascii'),
            'caption': figures[figure_index]['caption'], 'sha256': ref['sha256']}
