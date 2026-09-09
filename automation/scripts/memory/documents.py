"""Independent fixed-version research documents and bounded chapter contexts.

Documents and sections use the existing immutable MEM store without becoming a
memory layer. Reads never update a document pointer, rewrite a chapter, or run a
model. Impact results are review candidates, not scientific verdicts.
"""
from copy import deepcopy
import time

from . import contracts, technical_units
from .document import Reader
from .evidence_adapter import iter_refs
from .errors import MemoryError


def fixed_ref(record, relation='references'):
    return {'target_kind': 'record', 'target_id': record['record_id'],
            'revision': record['revision'], 'sha256': record['record_hash'],
            'locator': '', 'relation': relation}


def ref_metadata(ref):
    # A free locator can contain copied evidence. Manifests use identity only.
    return {key: ref.get(key) for key in ('target_kind', 'target_id', 'revision', 'sha256', 'relation')}


def _issue(ref, code):
    return {'target_id': ref['target_id'], 'code': code}


def _validate_request(request, definition):
    errors = contracts.validate_schema(request, contracts.SCHEMA['$defs'][definition], contracts.SCHEMA['$defs'])
    if errors:
        raise MemoryError('INVALID_ARGUMENT', '文档请求结构无效', errors=errors)
    if 'revision' in request and ('document_id' not in request or request['revision'] < 1):
        raise MemoryError('INVALID_ARGUMENT', 'revision 必须为正整数并与 document_id 同用')


class Session:
    """One read waterline; metadata inventory is shared by all selected refs.

    Store.read_snapshot currently parses all records in a visited owner. The
    metrics disclose that fact; chapter-context limits describe emitted context,
    not a claim that the filesystem parsed only one chapter.
    """
    def __init__(self, service, request):
        self.started = time.perf_counter()
        self.service, self.request = service, request
        self.reader = Reader(service)
        self.owner = self.reader.owner(request['owner_id'])
        self.state = self.reader.state(request['owner_id'])
        candidates = [record for record in self.state['records'].values()
                      if record['kind'] == 'document' and record['sensitivity'] != 'restricted']
        candidates.sort(key=lambda r: (r['updated_at'], r['revision'], r['record_id']), reverse=True)
        self.candidates = [{**{key: r[key] for key in ('record_id', 'revision', 'title', 'updated_at')},
                            'document_type': r['payload']['document_type']} for r in candidates]
        self.document = None
        explicit = request.get('document_id')
        if explicit:
            current = self.state['records'].get(explicit)
            if current is None or current['sensitivity'] == 'restricted':
                raise MemoryError('NOT_FOUND', '所选文档不存在或不可读取')
            self.document = self.reader.record({'target_id': explicit, 'revision': request.get('revision', current['revision'])})
            if self.document['kind'] != 'document' or self.document['owner_id'] != request['owner_id']:
                raise MemoryError('INVALID_ARGUMENT', 'document_id 必须是所选研究的独立文档')
            if request.get('document_type') and request['document_type'] != self.document['payload']['document_type']:
                raise MemoryError('INVALID_ARGUMENT', '所选文档与 document_type 不一致')
        else:
            document_type = request.get('document_type', 'research_process')
            self.document = next((r for r in candidates if r['payload']['document_type'] == document_type), None)
        self.section_cache, self.hints = {}, []
        self.common_issues = []
        if self.document:
            errors = contracts.validate_schema(self.document, contracts.SCHEMA['$defs']['DocumentRecordV3'], contracts.SCHEMA['$defs'])
            if errors:
                raise MemoryError('INVALID_SCHEMA', '固定文档结构无效', errors=errors)
            self.common_refs = [*self.document['sources'], *self.document['payload']['common_refs']]
            self.common_issues = self.check_refs(self.common_refs, request.get('selection', {}).get('exclude_ids', []))
        else:
            self.common_refs = []

    def check_refs(self, refs, excluded=()):
        """Check current permission and fixed bytes, then note newer revisions."""
        issues = []
        for ref in refs:
            try:
                if self.depends_on_excluded(ref, set(excluded)):
                    raise MemoryError('EXCLUDED', '所需依据被明确排除')
                self.reader.check_ref(ref)
                if ref['target_kind'] == 'record':
                    record = self.reader.record(ref)
                    current = self.reader.state(record['owner_id'])['records'][record['record_id']]
                    if current['revision'] != record['revision']:
                        hint = {'record_id': record['record_id'], 'revision': record['revision'], 'current_revision': current['revision']}
                        if hint not in self.hints:
                            self.hints.append(hint)
            except MemoryError as exc:
                item = _issue(ref, exc.code)
                if item not in issues:
                    issues.append(item)
        return issues

    def depends_on_excluded(self, ref, excluded, seen=None):
        if not excluded:
            return False
        if ref['target_id'] in excluded:
            return True
        if ref['target_kind'] != 'record':
            return False
        seen = set() if seen is None else seen
        key = (ref['target_id'], ref.get('revision'))
        if key in seen:
            return False
        seen.add(key)
        record = self.reader.record(ref)
        if record['owner_id'] in excluded:
            return True
        return any(self.depends_on_excluded(child, excluded, seen) for child in iter_refs({
            'sources': record['sources'], 'payload': record['payload']}))

    def metadata(self):
        if self.document is None:
            return None
        record, payload = self.document, self.document['payload']
        result = {key: record[key] for key in ('record_id', 'revision', 'title')}
        result.update({key: deepcopy(payload[key]) for key in ('document_type', 'purpose', 'audience', 'scope', 'common_refs', 'section_refs')})
        if self.common_issues:
            # General metadata is authored prose too; it cannot bypass a failed
            # common provenance gate merely by appearing above the chapters.
            result.update(title='依据不可用的文档', purpose='', audience='', scope='')
        return result

    def section(self, ref):
        key = (ref['target_id'], ref['revision'], ref['sha256'])
        if key not in self.section_cache:
            record = self.reader.record(ref)
            if record['kind'] != 'document_section':
                raise MemoryError('INVALID_SCHEMA', '文档章节引用了其他记录类别')
            errors = contracts.validate_schema(record, contracts.SCHEMA['$defs']['DocumentSectionRecordV3'], contracts.SCHEMA['$defs'])
            if errors:
                raise MemoryError('INVALID_SCHEMA', '固定章节结构无效', errors=errors)
            self.section_cache[key] = record
        return self.section_cache[key]

    def section_rows(self, *, check_units=False, excluded=()):
        rows = []
        if self.document is None:
            return rows
        for ref in self.document['payload']['section_refs']:
            row = {'section_id': ref['target_id'], 'ref': deepcopy(ref), 'section_key': '',
                   'title': '不可读取的章节', 'role': 'appendix', 'unit_refs': [], 'source_issues': []}
            if ref['target_id'] in excluded:
                row.update(title='已排除章节', source_issues=[_issue(ref, 'EXCLUDED')])
                rows.append(row)
                continue
            try:
                record = self.section(ref)
                issues = [*self.common_issues, *self.check_refs(record['sources'], excluded)]
                units = [b['ref'] for b in record['payload']['blocks'] if b['type'] == 'unit']
                if check_units:
                    issues.extend(self.check_refs(list(iter_refs(record['payload']['blocks']))))
                if not issues:
                    row.update({key: record['payload'][key] for key in ('section_key', 'title', 'role')})
                row.update(unit_refs=[deepcopy(value) for value in units], source_issues=issues)
            except MemoryError as exc:
                row['source_issues'] = [_issue(ref, exc.code)]
            rows.append(row)
        return rows

    def resolve_section(self, ref, *, excluded=()):
        row = {'section_id': ref['target_id'], 'section_key': '', 'title': '不可读取的章节',
               'role': 'appendix', 'ref': deepcopy(ref), 'source_issues': [], 'blocks': []}
        if ref['target_id'] in excluded:
            row['source_issues'] = [_issue(ref, 'EXCLUDED')]
            return row
        try:
            section = self.section(ref)
        except MemoryError as exc:
            row['source_issues'] = [_issue(ref, exc.code)]
            return row
        base_issues = [*self.common_issues, *self.check_refs([*self.common_refs, *section['sources']], excluded)]
        row['source_issues'] = base_issues
        if not base_issues:
            row.update({key: section['payload'][key] for key in ('section_key', 'title', 'role')})
        for block in section['payload']['blocks']:
            resolved = deepcopy(block)
            refs = block['evidence_refs'] if block['type'] == 'prose' else [block['ref']]
            issues = [*base_issues, *self.check_refs(refs, excluded)]
            if block['type'] == 'prose':
                if issues:
                    resolved['markdown'] = ''
            else:
                resolved.update(item=None, resolved_blocks=[], required_block_ids=[])
                if not issues:
                    try:
                        record = self.reader.record(block['ref'])
                        if record['kind'] != 'detail':
                            raise MemoryError('INVALID_SCHEMA', 'unit 引用不是技术单元')
                        selected, required = technical_units.select_blocks(record, block.get('block_ids'))
                        if any(record['record_id'] + '#' + value['block_id'] in excluded for value in selected):
                            raise MemoryError('EXCLUDED', '所选结果的必要内容块被明确排除')
                        resolved.update(resolved_blocks=selected, required_block_ids=required,
                            item={'id': record['record_id'], 'level': 'L1', 'record': deepcopy(record),
                                  'source_issues': [], 'formal_eligibility': 'not_evaluated'})
                    except MemoryError as exc:
                        issues.append(_issue(block['ref'], exc.code))
            resolved['source_issues'] = issues
            row['blocks'].append(resolved)
        return row

    def heads(self):
        return {oid: state['head']['commit_id'] if state['head'] else 'none'
                for oid, state in self.reader.states.items()}

    def metrics(self):
        return {'elapsed_ms': round((time.perf_counter() - self.started) * 1000, 2),
                'inventory_owners': len(self.reader.views), 'read_memory_owners': len(self.reader.states),
                'parsed_owner_records': sum(len(state['records']) for state in self.reader.states.values()),
                'resolved_sections': len(self.section_cache)}

    def finish(self, result):
        self.reader.recheck()
        return {**result, 'basis_heads': self.heads(), 'metrics': self.metrics(), 'writes': 0}


def build_document(service, request):
    """Prefer an independent fixed document; preserve the explicit legacy view."""
    _validate_request(request, 'DocumentRequest')
    session = Session(service, request)
    if session.document is None:
        from .document import build_document as legacy_document
        result = legacy_document(service, request['owner_id'], request.get('report_record_id'))
        result.update(document=None, document_source='legacy_report' if result['report'] else 'uncomposed')
        if request.get('document_type') == 'research_report':
            # A historical continuous process is not a separately authored
            # brief. Switching document type must never relabel that long text.
            result.update(document_source='uncomposed', report=None, items=[], report_candidates=session.candidates)
            result['missing'].append({'code': 'DOCUMENT_MISSING', 'message': '尚未保存独立简版研究报告'})
        return result
    sections = [session.resolve_section(ref) for ref in session.document['payload']['section_refs']]
    included = {block['ref']['target_id'] for section in sections for block in section['blocks'] if block['type'] == 'unit'}
    # A unit can support a brief through cited prose/common definitions without
    # being copied as a full unit block. Coverage is editorial, not an access gate.
    authored_refs = list(session.common_refs)
    for ref in session.document['payload']['section_refs']:
        try:
            authored_refs.extend(iter_refs(session.section(ref)['payload']['blocks']))
        except MemoryError:
            continue
    for ref in authored_refs:
        if ref['target_kind'] == 'record':
            try:
                if session.reader.record(ref)['kind'] == 'detail':
                    included.add(ref['target_id'])
            except MemoryError:
                pass
    uncovered = sorted(record['record_id'] for record in session.state['records'].values()
                       if record['kind'] == 'detail' and record['sensitivity'] != 'restricted' and record['record_id'] not in included)
    complete = not session.common_issues and all(not section['source_issues'] and all(
        not block['source_issues'] for block in section['blocks']) for section in sections)
    meta = session.metadata()
    result = {'schema_version': 1, 'owner_id': request['owner_id'], 'title': session.owner['title'],
        'document_source': 'independent', 'document': meta,
        'report': {'version': 1, 'record_id': meta['record_id'], 'revision': meta['revision'], 'title': meta['title'],
                   'sections': sections, 'complete': complete},
        'items': [], 'missing': session.common_issues, 'generated_at': service.clock(),
        'report_candidates': session.candidates,
        'report_coverage': {'included_detail_ids': sorted(included), 'uncovered_detail_ids': uncovered},
        'report_version_hints': session.hints}
    # Full immutable record cards are an explicit audit request, not a duplicate
    # appendix injected into every long document response.
    if request.get('include_records'):
        from .document import build_document as legacy_document
        result['items'] = legacy_document(service, request['owner_id'])['items']
    return session.finish(result)


def outline(service, request):
    _validate_request(request, 'OutlineRequest')
    session = Session(service, request)
    return session.finish({'schema_version': 1, 'owner_id': request['owner_id'],
        'document_source': 'independent' if session.document else 'uncomposed', 'document': session.metadata(),
        'sections': session.section_rows(check_units=True), 'report_candidates': session.candidates,
        'watch_baseline': {'owner_id': request['owner_id'],
            'head': session.state['head']['commit_id'] if session.state['head'] else None,
            'unit_ids': sorted(r['record_id'] for r in session.state['records'].values()
                               if r['kind'] == 'detail' and r['sensitivity'] != 'restricted')},
        'missing': session.common_issues})


def section_context(service, request):
    """Build a bounded task packet without serialized full payload duplication."""
    _validate_request(request, 'SectionContextRequest')
    session = Session(service, request)
    if session.document is None:
        raise MemoryError('NOT_FOUND', '尚无独立文档，不能选择固定章节')
    budget = request.get('budget', {}).get('max_chars', 20000)
    if type(budget) is not int or not 1 <= budget <= 1_000_000:
        raise MemoryError('INVALID_ARGUMENT', 'max_chars 必须在 1 到 1000000 之间')
    selection = {key: list(dict.fromkeys(request.get('selection', {}).get(key, [])))
                 for key in ('include_ids', 'full_ids', 'exclude_ids')}
    excluded = set(selection['exclude_ids'])
    wanted = set(selection['include_ids']) | set(selection['full_ids'])
    rows = session.section_rows(excluded=excluded)
    target = next((row for row in rows if row['section_id'] == request['section_id']), None)
    if target is None:
        raise MemoryError('NOT_FOUND', '所选章节不在固定文档中')
    chosen_sections = {target['section_id']} | {row['section_id'] for row in rows if row['section_id'] in wanted}
    manifest = {'selection': selection, 'read_refs': [], 'omitted': [], 'missing': [], 'required_not_full': [],
                'budget': {'max_chars': budget, 'used_chars': 0}, 'complete': True}
    chunks, seen = [], set()
    packet_document = {key: session.metadata()[key] for key in ('record_id', 'revision', 'document_type')}
    if session.document['record_id'] in excluded or request['owner_id'] in excluded:
        manifest.update(complete=False, missing=[{'target_id': session.document['record_id'], 'code': 'EXCLUDED'}], basis_heads=session.heads())
        session.reader.recheck()
        return {'schema_version': 1, 'owner_id': request['owner_id'], 'document': packet_document,
                'section_id': request['section_id'], 'context_text': '', 'manifest': manifest,
                'metrics': session.metrics(), 'writes': 0}

    def add(text, ref=None, *, required=True, block_ids=None):
        cost = len(text) + (2 if chunks else 0)
        if manifest['budget']['used_chars'] + cost > budget:
            item = {'target_id': ref['target_id'] if ref else session.document['record_id'], 'code': 'BUDGET_EXCEEDED'}
            manifest['omitted'].append(item)
            if required:
                manifest['required_not_full'].append(item)
                manifest['complete'] = False
            return False
        chunks.append(text)
        manifest['budget']['used_chars'] += cost
        if ref:
            item = ref_metadata(ref)
            if block_ids is not None:
                item['block_ids'] = block_ids
            if item not in manifest['read_refs']:
                manifest['read_refs'].append(item)
        return True

    meta = session.metadata()
    heading = '\n\n'.join([f"# {meta['title']}", '目的：' + meta['purpose'], '读者：' + meta['audience'],
                           '范围：' + meta['scope'], '目录：\n' + '\n'.join(row['section_id'] + ' ' + row['title'] for row in rows)])
    add(heading, fixed_ref(session.document))
    for row in rows:
        if row['section_id'] not in chosen_sections:
            manifest['omitted'].append({'target_id': row['section_id'], 'code': 'NOT_SELECTED'})
            continue
        section = session.resolve_section(row['ref'], excluded=excluded)
        if section['source_issues']:
            manifest['missing'].extend(section['source_issues'])
            manifest['complete'] = False
        add('## ' + section['title'], row['ref'])
        for block in section['blocks']:
            if block['source_issues']:
                manifest['missing'].extend(block['source_issues'])
                manifest['complete'] = False
                continue
            if block['type'] == 'prose':
                add(block['markdown'], row['ref'])
                continue
            record = block['item']['record']
            identity = (record['record_id'], record['revision'], tuple(value['block_id'] for value in block['resolved_blocks']))
            if identity in seen:
                continue
            seen.add(identity)
            content = technical_units.description_text(record)
            full = ('\n\n'.join(value['markdown'] for value in block['resolved_blocks'])
                    if technical_units.is_unit(record) else record['body_markdown'])
            text = f"### {record['title']}\n\n{record['record_id']} r{record['revision']}\n\n{content}\n\n{full}"
            if not add(text, block['ref'], block_ids=[value['block_id'] for value in block['resolved_blocks']]):
                # A saved description is a safe fallback, never a fabricated
                # truncated result. The missing full content stays explicit.
                add(f"### {record['title']}（仅检索描述）\n\n{content}", block['ref'], required=False)
    # Common methods and explicitly selected records are independent additions.
    # They are not silently promoted to full just because a title is nearby.
    extras = list(session.document['payload']['common_refs'])
    for identity in sorted(wanted - chosen_sections):
        rid = identity.split('#', 1)[0]
        if any(ref['target_id'] == rid for ref in extras):
            continue
        try:
            current = session.reader.record({'target_id': rid, 'revision': None})
            extras.append(fixed_ref(current))
        except MemoryError as exc:
            manifest['missing'].append({'target_id': rid, 'code': exc.code})
            manifest['complete'] = False
    for ref in extras:
        if any(identity[0] == ref['target_id'] for identity in seen):
            continue
        issues = session.check_refs([ref], excluded)
        if issues:
            manifest['missing'].extend(issues)
            manifest['complete'] = False
            continue
        if ref['target_kind'] != 'record':
            # Raw files stay fixed locators; explicit material expansion uses
            # the existing trace/expand endpoint with its separate source gates.
            add('共同依据：' + ref['target_id'], ref)
            continue
        record = session.reader.record(ref)
        full = ref['target_id'] in selection['full_ids']
        if technical_units.is_unit(record):
            selected_ids = [identity.split('#', 1)[1] for identity in selection['full_ids'] if identity.startswith(ref['target_id'] + '#')]
            full = full or bool(selected_ids)
            blocks, _ = technical_units.select_blocks(record, selected_ids or None)
            if full and any(ref['target_id'] + '#' + value['block_id'] in excluded for value in blocks):
                manifest['missing'].append(_issue(ref, 'EXCLUDED'))
                manifest['complete'] = False
                continue
            text = technical_units.description_text(record)
            if full:
                text += '\n\n' + '\n\n'.join(value['markdown'] for value in blocks)
        else:
            text = record['body_markdown'] if full else record['title']
        add('### ' + record['title'] + '\n\n' + text, ref)
    session.reader.recheck()
    manifest['basis_heads'] = session.heads()
    # Purpose/scope and the outline already consumed context budget above.
    # Do not return a second, unbounded copy through metadata/locator fields.
    return {'schema_version': 1, 'owner_id': request['owner_id'], 'document': packet_document,
            'section_id': request['section_id'], 'context_text': '\n\n'.join(chunks),
            'manifest': manifest, 'metrics': session.metrics(), 'writes': 0}


def document_impact(service, request):
    """Compare explicit fixed edges and observation baselines with live heads.

    No text similarity is treated as a dependency. A new revision is a review
    candidate even when the old fixed bytes remain readable and valid.
    """
    _validate_request(request, 'DocumentImpactRequest')
    session = Session(service, request)
    if session.document is None:
        raise MemoryError('NOT_FOUND', '尚无独立文档，不能检查章节影响')
    doc = session.document
    section_ids = [ref['target_id'] for ref in doc['payload']['section_refs']]
    changes, included, unit_versions = [], set(), {}

    def add(code, target_id, affected, path, before=None, after=None, relation='evidence', message=None):
        change = {'code': code, 'target_id': target_id, 'section_ids': sorted(set(affected)),
                  'path': path, 'before_ref': ref_metadata(before) if before else None,
                  'after_ref': ref_metadata(after) if after else None,
                  'relation_type': relation, 'requires_review': True,
                  'message': message or {'NEW_REVISION': '固定依据已有新修订，原稿未自动替换',
                    'NEW_UNIT_UNCOVERED': '关注研究出现尚未纳入的新技术单元',
                    'DOCUMENT_BASIS_MISMATCH': '两份文稿引用同一技术单元的不同固定版本'}.get(code, '文档依据或关注对象需要重新检查')}
        if change not in changes:
            changes.append(change)

    def visit(ref, affected, path, seen):
        key = (ref['target_kind'], ref['target_id'], ref.get('revision'), ref.get('sha256'))
        if key in seen:
            return
        seen.add(key)
        current_path = path + [ref['target_id']]
        try:
            if ref['target_kind'] != 'record':
                session.reader.check_ref(ref)
                return
            old = session.reader.record(ref)
            current = session.reader.state(old['owner_id'])['records'][old['record_id']]
            if current['revision'] != old['revision']:
                add('NEW_REVISION', old['record_id'], affected, current_path, ref, fixed_ref(current))
            if old['kind'] == 'detail':
                included.add(old['record_id'])
                unit_versions.setdefault(old['record_id'], []).append((ref, list(affected)))
            # Follow declared evidence only. watch_refs has no Ref-shaped data
            # and is handled separately below, without a supports relationship.
            for child in iter_refs({'sources': old['sources'], 'payload': old['payload']}):
                visit(child, affected, current_path, seen)
        except MemoryError as exc:
            add(exc.code, ref['target_id'], affected, current_path, ref)

    for ref in session.common_refs:
        visit(ref, section_ids, [doc['record_id']], set())
    watched = [(doc['payload']['watch_refs'], section_ids, [doc['record_id']])]
    for ref in doc['payload']['section_refs']:
        visit(ref, [ref['target_id']], [doc['record_id']], set())
        try:
            section = session.section(ref)
            watched.append((section['payload']['watch_refs'], [ref['target_id']], [doc['record_id'], ref['target_id']]))
        except MemoryError:
            pass  # The fixed edge above already emitted its exact failure.
    uncovered = set()
    for watches, affected, path in watched:
        for watch in watches:
            if watch['watch_type'] == 'revision':
                ref = {'target_kind': 'record', 'target_id': watch['record_id'], 'revision': watch['baseline_revision'],
                       'sha256': watch['baseline_record_hash'], 'locator': '', 'relation': 'references'}
                try:
                    before = session.reader.record(ref)
                    current = session.reader.state(before['owner_id'])['records'][before['record_id']]
                    session.reader.check_ref(fixed_ref(current))
                    if current['revision'] != before['revision']:
                        add('NEW_REVISION', ref['target_id'], affected, path + [ref['target_id']], ref, fixed_ref(current), 'watch')
                except MemoryError as exc:
                    add(exc.code, ref['target_id'], affected, path + [ref['target_id']], ref, relation='watch')
            else:
                oid = watch['owner_id']
                try:
                    current_state = session.reader.state(oid)
                    known = set(watch['baseline_unit_ids'])
                    for record in current_state['records'].values():
                        if record['kind'] != 'detail' or record['record_id'] in known | included or record['sensitivity'] == 'restricted':
                            continue
                        ref = fixed_ref(record)
                        try:
                            session.reader.check_ref(ref)
                        except MemoryError:
                            # A denied new unit is not a discoverable candidate.
                            continue
                        uncovered.add(record['record_id'])
                        add('NEW_UNIT_UNCOVERED', record['record_id'], affected, path + [oid, record['record_id']],
                            after=ref, relation='watch')
                except MemoryError as exc:
                    add(exc.code, oid, affected, path + [oid], relation='watch')
    # Compare the latest counterpart document's explicit unit versions. This
    # exposes inconsistent bases without merging the two separately authored texts.
    other_type = 'research_report' if doc['payload']['document_type'] == 'research_process' else 'research_process'
    others = [r for r in session.state['records'].values() if r['kind'] == 'document'
              and r['payload']['document_type'] == other_type and r['sensitivity'] != 'restricted']
    if others:
        other = max(others, key=lambda r: (r['updated_at'], r['revision'], r['record_id']))
        for section_ref in other['payload']['section_refs']:
            try:
                section = session.section(section_ref)
                for block in section['payload']['blocks']:
                    if block['type'] != 'unit':
                        continue
                    other_ref = block['ref']
                    if other_ref['target_id'] not in unit_versions:
                        continue
                    session.reader.check_ref(other_ref)
                    for own_ref, affected in unit_versions[other_ref['target_id']]:
                        if (own_ref['revision'], own_ref['sha256']) != (other_ref['revision'], other_ref['sha256']):
                            add('DOCUMENT_BASIS_MISMATCH', own_ref['target_id'], affected,
                                [doc['record_id'], other['record_id'], section_ref['target_id'], own_ref['target_id']], own_ref, other_ref, 'composition')
            except MemoryError:
                continue
    return session.finish({'schema_version': 1, 'owner_id': request['owner_id'], 'document': session.metadata(),
        'changes': changes, 'affected_section_ids': sorted({sid for change in changes for sid in change['section_ids']}),
        'uncovered_unit_ids': sorted(uncovered), 'scientific_review': 'not_evaluated'})
