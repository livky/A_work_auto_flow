"""补充只读清点：受控业务目录的文件元数据、悬空对象引用与公开文稿回读。

不读取缓存或遍历外部目录；独立来源/Run登记以外的文件只是待分类文件，
不是自动认定丢失的证据。重复运行追加新报告。
"""
import collections
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / 'automation/scripts'))
from memory import owners, api
from memory.service import MemoryService
from memory.index import Catalog
import retrieval

catalog = Catalog(ROOT)
service = MemoryService(ROOT)
report = {'documents': [], 'dangling_owner_links': [], 'files': [], 'unregistered_top_directories': []}
registered = {s['path'].replace('\\','/') for s in retrieval.read_json(ROOT/'retrieval/sources.json')['sources']}
for owner in catalog.owners.values():
    for key in ('inputs','artifacts'):
        registered.update(i['path'].replace('\\','/') for i in owner['native_data'].get(key,[]) if isinstance(i,dict) and i.get('path'))
    for key in ('related_run_ids','parent_run_ids','related_project_ids','related_module_ids','related_research_ids'):
        for target in owner['native_data'].get(key,[]):
            if target not in catalog.owners:
                report['dangling_owner_links'].append({'owner_id':owner['owner_id'],'field':key,'target':target})
    if owner['native_data'].get('sensitivity') == 'restricted':
        continue
    for record in catalog.snapshot(owner['owner_id'])['records'].values():
        if record['kind'] == 'document':
            request = {'owner_id':owner['owner_id'],'document_id':record['record_id'],'revision':record['revision']}
            try:
                result = api.dispatch(service,'document',request)
                # 保存公开回读，正文供人工检验；机械完整性不代表已逐页视觉验收。
                name = 'document-'+record['record_id']+'-r'+str(record['revision'])+'.json'
                (HERE/name).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
                report['documents'].append({'request':request,'path':name,'complete':result.get('report',{}).get('complete'),
                    'sections':len(result.get('report',{}).get('sections',[])),'missing':result.get('missing',[])})
            except Exception as exc:
                report['documents'].append({'request':request,'error':str(exc)})
skip = owners.EXCLUDED | {'memory','fixtures','archive','private','build','dist'}
for zone in owners.ROOT_TYPES:
    base = ROOT/zone
    if not base.exists():
        continue
    for directory, dirs, files in os.walk(base, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d not in skip and not (Path(directory)/d).is_symlink() and not (Path(directory)/d).is_junction())
        for name in files:
            path=Path(directory)/name
            if path.is_symlink():
                continue
            relative=path.relative_to(ROOT).as_posix()
            # 只保存路径/大小，不批量读取未登记正文。
            report['files'].append({'path':relative,'bytes':path.stat().st_size,'explicitly_registered':relative in registered})
report['summary']={'files':len(report['files']),'explicitly_registered_files':sum(x['explicitly_registered'] for x in report['files']),
                   'documents':len(report['documents']),'dangling_owner_links':len(report['dangling_owner_links'])}
out=HERE/('details-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'.json')
out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'path':str(out),**report['summary'],'documents':report['documents'],'dangling_owner_links':report['dangling_owner_links']},ensure_ascii=False,indent=2))
