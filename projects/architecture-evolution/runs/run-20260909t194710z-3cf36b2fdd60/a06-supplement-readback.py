"""Capture public A06 readbacks and hash checks without grading the AI result.

Only the explicit text-index reconciliation can write derived state. All memory
inspect/view calls are read-only; original source bytes are merely hashed.
"""
import json
import sys
from pathlib import Path

RUN = Path(__file__).resolve().parent
ROOT = RUN.parents[3]
sys.path.insert(0, str(ROOT / 'automation/testing'))
import ai_review

attempt = Path(ai_review.read_json(RUN / 'a06-supplement-attempt.json')['attempt'])
fixture = ROOT / '.local/testing/material-query-f3-20260910-actual/workspace'
runtime = ROOT / 'services/qdrant/runtime/python.exe'
cli = ROOT / 'automation/scripts/workspace_cli.py'
base = [str(runtime), '-X', 'utf8', str(cli), '--root', str(fixture), 'memory']
saved = ai_review.read_json(attempt / 'calls/call-e7eaed358e5c41339bc7171c9cf63ae4/stdout.txt')
new_record = saved['record_results'][0]['record_id']
calls = {}

def capture(label, argv, payload=None):
    """Every actual child command keeps its original exit status and output."""
    request = None
    if payload is not None:
        request = attempt / 'authored-requests' / (label + '.json')
        ai_review.write_new(request, payload)
        argv = argv + ['--request', str(request)]
    call, receipt = ai_review.capture_call(attempt, base + argv,
                                           request=request, cwd=fixture)
    calls[label] = {'call': str(call), 'exit_code': receipt['exit_code']}
    return ai_review.read_json(call / 'stdout.txt')

index = capture('text-reconcile', ['reconcile'], {'owner_id': 'RES-F3-RETRY', 'vector': 'off'})
navigation = capture('saved-navigation-inspect', ['inspect', 'RES-F3-RETRY',
                     '--record-id', new_record, '--revision', '1'])
view = capture('saved-navigation-view', ['associations-view'],
               {'owner_id': 'RES-F3-RETRY', 'record_id': new_record, 'revision': 1})

discovery = ai_review.read_json(attempt / 'calls/call-2eaaaa7e125a4b59b5cd13cab7c22294/stdout.txt')
owners = ['RES-F3-TANK', 'RES-F3-TANK', 'RES-F3-RETRY', 'RES-F3-SATURATION']
originals = []
for number, (candidate, owner) in enumerate(zip(discovery['value']['candidates'], owners), 1):
    # The explicit owner list follows the four candidates read by the AI.
    ref = candidate['refs'][0]
    output = capture('original-' + str(number), ['inspect', owner,
                      '--record-id', ref['id'], '--revision', str(ref['revision'])])
    record = output['record']
    originals.append({'ref': ref, 'returned_owner': record['owner_id'],
                      'returned_hash': record['record_hash'],
                      'same_hash': record['record_hash'] == ref['sha256'],
                      'same_owner': record['owner_id'] == owner})

old_navigation = capture('old-navigation-inspect', ['inspect', 'RES-F3-RETRY',
                         '--record-id', 'MEM-bab0426e-0012-5106-9124-4b5fba49a65f',
                         '--revision', '1'])
metadata = ai_review.read_json(RUN / 'a06-supplement-metadata.json')
source_after = {owner: ai_review.digest(fixture / 'research' / owner / 'data/合成 输入.md')
                for owner in ['tank', 'retry', 'saturation']}
checks = {
    'calls': calls, 'new_navigation': {'record_id': new_record,
        'record_hash': navigation['record']['record_hash'],
        'owner_id': navigation['record']['owner_id'],
        'status': navigation['record']['payload']['status'],
        'relation': navigation['record']['payload']['relation']},
    'original_record_readbacks': originals,
    'old_navigation_hash': old_navigation['record']['record_hash'],
    'old_navigation_unchanged': old_navigation['record']['record_hash'] ==
        '2f319ec12299920fc1c24c3310dda7aded06a448c439ff96db79f78ced50b6b1',
    'source_hashes_after': source_after,
    'source_bytes_unchanged': source_after == metadata['original_source_sha256'],
    'final_heads': {owner: ai_review.read_json(fixture / 'research' / owner / 'memory/HEAD.json')
                    for owner in ['tank', 'retry', 'saturation']},
    'note': 'Hash/identity checks only; no scientific or human review assertion.',
}
ai_review.write_new(attempt / 'readback-checks.json', checks)
print(json.dumps(checks, ensure_ascii=False, indent=2))
