"""C08 synthetic structural cases shared with the real frontend test runner.

Emit finite JSON only. Expected validity is computed by the production Python
schema validator, not stored labels. Domain authorization remains service-side.
"""
from copy import deepcopy
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from memory import contracts
from test_memory_contracts import draft, examples


def matrix():
    rows = []
    def add(name, value, definition='MemoryDraft'):
        errors = contracts.validate_schema(value, contracts.SCHEMA['$defs'][definition], contracts.SCHEMA['$defs'])
        rows.append({'name': name, 'definition': definition, 'value': value, 'valid': not errors})
    for kind in examples():
        normalized = contracts.validate_record(draft(kind), {'allow_review': True})
        assert normalized['valid'], normalized['errors']
        value = normalized['record']
        add(kind + ':valid', value)
        add(kind + ':reverse-keys', dict(reversed(list(value.items()))))
        for field in ('owner_id', 'title', 'payload', 'record_reason'):
            bad = deepcopy(value); del bad[field]
            add(kind + ':missing-' + field, bad)
        for field, invalid in (('level', 'L4'), ('kind', 'alien'), ('schema_version', True), ('title', 123)):
            bad = deepcopy(value); bad[field] = invalid
            add(kind + ':invalid-' + field, bad)
        bad = deepcopy(value); bad['payload']['magic_score'] = 123
        add(kind + ':unknown-payload', bad)
        bad = deepcopy(value); bad['body_markdown'] = '中文🙂\n多行𠮷\n'
        add(kind + ':unicode-newlines', bad)
    # bool must not be accepted as integer, and field constraints must survive
    # oneOf expansion. These cases catch cross-language coercion regressions.
    for reason in ('unknown', 'not_acquired', 'not_applicable', 'alien'):
        add('unknown:' + reason, {'value': None, 'reason': reason, 'note': '未取得'}, 'UnknownValue')
    for revision in (1, True, None, '1'):
        add('ref-revision:' + repr(revision), {'target_kind': 'record', 'target_id': 'MEM-C08',
            'revision': revision, 'sha256': None, 'locator': '中文🙂', 'relation': 'references'}, 'Ref')
    return rows


def content_matrix():
    """新增内容契约独立计数，保留原188项的历史覆盖与断言。"""
    rows = []
    common = {'claims': [], 'process_refs': [], 'technical_refs': [], 'experience_refs': [], 'limitations': []}
    payloads = {
        'narrative': {**common, 'question': '合成问题', 'stages': [{'situation': '起点', 'action': '试验',
            'reason': '核对机制', 'outcome': '仍未解决', 'evidence_refs': []}]},
        'overview': {**common, 'question': '合成问题', 'methods': [], 'results': [], 'current_stage': '进行中', 'open_questions': ['缺现实依据']},
        'experience': {**examples()['experience'], 'knowledge_type': 'hypothesis', 'process_refs': [], 'technical_refs': []},
    }
    for kind, payload in payloads.items():
        value = {**draft(), 'schema_version': 4, 'kind': kind, 'payload': deepcopy(payload)}
        normalized = contracts.validate_record(value)
        assert normalized['valid'], normalized['errors']
        valid = normalized['record']
        variants = [('valid', valid)]
        for field in ('body_markdown', 'payload'):
            bad = deepcopy(valid); del bad[field]; variants.append(('missing-' + field, bad))
        for field in ('process_refs', 'technical_refs'):
            bad = deepcopy(valid); del bad['payload'][field]; variants.append(('missing-' + field, bad))
        bad = deepcopy(valid); bad['body_markdown'] = ''; variants.append(('empty-body', bad))
        bad = deepcopy(valid); bad['schema_version'] = 3; variants.append(('wrong-version', bad))
        bad = deepcopy(valid)
        if kind == 'narrative':
            bad['payload']['stages'] = []
        elif kind == 'overview':
            del bad['payload']['open_questions']
        else:
            bad['payload']['knowledge_type'] = 'accepted'
        variants.append(('wrong-content', bad))
        for name, value in variants:
            errors = contracts.validate_schema(value, contracts.SCHEMA['$defs']['MemoryDraft'], contracts.SCHEMA['$defs'])
            rows.append({'name': kind + ':' + name, 'definition': 'MemoryDraft', 'value': value, 'valid': not errors})
    return rows


if __name__ == '__main__':
    # ASCII transport also works under Windows GBK; the frontend decodes the
    # escaped Unicode before validation, preserving the actual code points.
    print(json.dumps(content_matrix() if '--content-v4' in sys.argv else matrix(), ensure_ascii=True))
