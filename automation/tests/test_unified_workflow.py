"""跨八类Owner经公开提交/FTS/组包/L0回源；合成材料不代表领域验证。"""
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import json
import tempfile
import unittest

from material_query_fixture import materialize, _draft, _experience
from material_query.coordinator import Coordinator
from material_query.contracts import Scope, QueryRequest, DefinitionRef, AssociationOptions
from material_query.budget import DEFAULT_BUDGET
from material_query.wire import json_value
from memory import api, owners, index


class UnifiedOwnerWorkflowTests(unittest.TestCase):
    def test_eight_owner_types_find_body_and_return_direct_source_without_empty_layers(self):
        with tempfile.TemporaryDirectory() as directory:
            fx = materialize(Path(directory) / '八类 中文', isolation_root=directory)
            cards = [('research/unified/research.json','research_id','RES-UNIFIED'),
                     ('projects/unified/project.json','project_id','PRJ-UNIFIED'),
                     ('core-algorithms/unified/module.json','module_id','MOD-UNIFIED'),
                     ('runs/unified/run.json','run_id','RUN-UNIFIED'),
                     ('data/catalog/unified.dataset.json','dataset_id','DATA-UNIFIED'),
                     ('reports/manifests/unified.json','report_id','REP-UNIFIED'),
                     ('knowledge/unified.evidence.json','evidence_id','EVD-UNIFIED')]
            for path, key, oid in cards:
                file=fx.root/path;file.parent.mkdir(parents=True,exist_ok=True)
                file.write_text(json.dumps({key:oid,'title':'合成对象','claims':[], 'dependencies':[], 'sensitivity':'internal'},ensure_ascii=False),encoding='utf-8')
            (fx.root/'knowledge/unified.md').write_text('合成知识原文',encoding='utf-8')
            card=fx.root/'knowledge/unified.evidence.json'
            metadata=json.loads(card.read_text(encoding='utf-8'));metadata['document_path']='knowledge/unified.md'
            card.write_text(json.dumps(metadata),encoding='utf-8')
            script=fx.root/'tools/scripts/unified.py';script.parent.mkdir(parents=True,exist_ok=True)
            script.write_text('"""合成工具入口，未执行。"""\n',encoding='utf-8')
            registry=fx.root/'tools/registry.json'
            registry.write_text(json.dumps({'tools':[{'tool_id':'TOOL-UNIFIED','entrypoint':'tools/scripts/unified.py'}]}),encoding='utf-8')
            import evidence
            self.assertEqual(evidence.EvidenceGraph(fx.root).errors, [])
            ids=[row[2] for row in cards]+['TOOL-UNIFIED']
            found={o['owner_id']:o for o in owners.list_owners(fx.root)}
            self.assertEqual(len({found[oid]['owner_type'] for oid in ids}),8)
            original=Path(fx.sources['A']['path']).read_bytes() if Path(fx.sources['A']['path']).is_absolute() else (fx.root/fx.sources['A']['path']).read_bytes()
            for oid in ids:
                for kind in ('overview','experience'):
                    payload = ({'question':'适用条件是什么','claims':[], 'process_refs':[], 'technical_refs':[], 'experience_refs':[],
                                'limitations':['来源主张，未执行'], 'methods':['文档阅读'], 'results':['没有本次实验'],
                                'current_stage':'已整理','open_questions':['现实有效性未验证']}
                               if kind=='overview' else _experience('适用边界','先确认条件'))
                    draft=_draft(fx,'A',kind,'中性标题',payload,body='用途检索uniqueusage：文档介绍用于延迟补偿。来源主张，未在本机执行；增益需要独立验证。')
                    draft.update(owner_id=oid,schema_version=4 if kind=='overview' else 3,keywords=[])
                    fx.commit_draft(oid+kind,draft)
            index.rebuild(fx.root,vector='off')
            scope=Scope(None,None,None,None,None,None,None,False,(),(),None,None)
            query=QueryRequest(DefinitionRef('full','1'),'uniqueusage',(),scope,scope,'exploration',
                               AssociationOptions('off','existing-relations','1',0,0,None),DEFAULT_BUDGET,
                               'current',30,'reject',(),'',content_source='overview_experience',channels=('lexical',))
            app=Coordinator(fx.root)
            try:
                result=app.search(json_value(query));self.assertIn(result['status'],{'ok','partial'},result)
                page=result['value'];matches=page['candidates']
                expected={fx.record_ids[oid+kind] for oid in ids for kind in ('overview','experience')}
                self.assertEqual({c['refs'][0]['id'] for c in matches},expected)
                packet=app.assemble({'query_id':page['query_id'],'expected_request_digest':page['request_digest'],
                                     'candidate_ids':[c['candidate_id'] for c in matches]})
                self.assertIn('来源主张',str(packet))
                for oid in ids:
                    with self.subTest(owner=oid):
                        records=fx.service.inspect(oid)['records']
                        self.assertEqual({r['kind'] for r in records.values()},{'overview','experience'})
                        listing=api.dispatch(fx.service,'raw-materials',{'owner_id':oid})
                        row=next(r for r in listing['items'] if r['sha256']==fx.sources['A']['sha256'])
                        content=api.dispatch(fx.service,'raw-material',{'owner_id':oid,'material_id':row['material_id']})
                        self.assertEqual(content['verified_sha256'],fx.sources['A']['sha256'])
                        self.assertEqual(content['text'],original.decode('utf-8-sig'))
                self.assertEqual(found['TOOL-UNIFIED']['memory_home'],'tools/memory/TOOL-UNIFIED')
                self.assertEqual(list(script.parent.glob('*.json')),[])
            finally:app.close()
