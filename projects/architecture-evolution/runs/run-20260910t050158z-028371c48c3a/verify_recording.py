"""Verify saved draft fields and pinned historical files without changing them."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
read = lambda path: json.loads(path.read_text(encoding='utf-8-sig'))
summary = {'batches': {}, 'documents': {}, 'frozen_files': 0, 'fixture_mismatches': []}
for batch in ('repair-units','repair-sections','repair-documents-map'):
    request = read(HERE / (batch+'-request.json'))
    receipt = read(HERE / (batch+'-receipt.json'))
    state = read(HERE / (batch+'-readback.json'))
    rows=[]
    for operation in request['operations']:
        rid = operation.get('record_id') or next(item['record_id'] for item in receipt['record_results'] if item.get('client_key')==operation['client_key'])
        record=state['records'][rid]
        for key,value in operation['draft'].items():
            assert record[key] == value, (rid,key)
        rows.append({'record_id':rid,'revision':record['revision'],'sha256':record['record_hash']})
    summary['batches'][batch]=rows
for name in ('floating-process-final','floating-report-final','project-process-final','project-brief-final'):
    data=read(HERE/(name+'.json'))
    assert data['report']['complete'] and not data['missing'], name
    summary['documents'][name]={'complete':True,'missing':0,'sections':len(data['report']['sections'])}
example=ROOT/'research/floating-point-summation'
for item in read(example/'fixtures/restore-manifest.json')['entries']:
    actual=hashlib.sha256((example/item['source']).read_bytes()).hexdigest()
    if actual != item['sha256']:
        summary['fixture_mismatches'].append({'source':item['source'],'expected':item['sha256'],'actual':actual})
    summary['frozen_files']+=1
tests=read(HERE/'testing/attempt-01/results.json')
summary['tested_program_bytes_match']=all(hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==value for name,value in tests['program_fingerprints'].items())
assert summary['tested_program_bytes_match']
(HERE/'recording-verification.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False,indent=2))
