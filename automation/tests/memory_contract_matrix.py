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


if __name__ == '__main__':
    # ASCII transport also works under Windows GBK; the frontend decodes the
    # escaped Unicode before validation, preserving the actual code points.
    print(json.dumps(matrix(), ensure_ascii=True))
