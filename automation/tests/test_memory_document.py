"""研究文稿只读、局部读取、分层、固定图片和撤销回归（全为合成数据）。"""
import base64
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import test_memory_research as fixture
from memory import document, owners, history, research, contracts, index
from memory.errors import MemoryError
import evidence


class DocumentTests(unittest.TestCase):
    setUp = fixture.ResearchTests.setUp
    put = fixture.ResearchTests.put
    operation = fixture.ResearchTests.operation
    request = fixture.ResearchTests.request
    save = fixture.ResearchTests.save
    event = fixture.ResearchTests.event

    def detail(self):
        run = evidence.read(self.root / 'runs/attempt/run.json')
        run_ref = {'target_kind': 'owner', 'target_id': 'RUN-R', 'revision': None,
                   'sha256': evidence.fingerprint(run), 'locator': 'run.json', 'relation': 'input'}
        image = self.root / 'research/topic/figures/result.png'
        image.parent.mkdir(parents=True, exist_ok=True)
        image.write_bytes(base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jP1sAAAAASUVORK5CYII='))
        ref = {'target_kind': 'file', 'target_id': 'SRC-FIGURE', 'revision': None,
               'sha256': evidence.sha256(image), 'locator': 'synthetic picture', 'relation': 'input'}
        self.put('retrieval/sources.json', {'sources': [{'source_id': 'SRC-FIGURE', 'path': 'research/topic/figures/result.png', 'enabled': True}]})
        payload = {'run_ref': run_ref, 'question': '合成求和是否稳定', 'method': '固定输入比较',
                   'steps': ['读取固定输入', '比较合成结果'], 'inputs': [ref],
                   'parameters': [{'name': 'n', 'value': 3, 'unit': '1', 'description': '合成项数'}],
                   'formulas': [{'latex': 's=\\sum_i x_i', 'variables': [{'symbol': 's', 'meaning': '和', 'unit': '1'}]}],
                   'figures': [{'caption': '合成结果图', 'ref': ref}], 'results': '合成结果为 3',
                   'limitations': ['仅为软件测试'], 'missing_refs': []}
        operation = self.operation('detail', payload, schema_version=2, level='L1',
                    body_markdown='## 方法\n\n计算 $s=3$。\n\n| 输入 | 结果 |\n|---|---|\n| 合成 | 3 |', sources=[run_ref, ref])
        return self.save(operation)

    def test_document_current_layers_and_no_unrelated_memory_body_reads(self):
        detail = self.detail()
        event = self.save(self.operation('event', self.event(), schema_version=2))
        for i in range(25):
            self.put(f'research/无关 {i}/research.json', {'research_id': f'RES-OTHER-{i}', 'title': '不应读取正文'})
        raw_path = self.put('research/无关 0/runs/raw/outputs/large.json', '{"raw":"' + 'x' * 4_000_000 + '"}')
        original = self.service.store.read_snapshot
        visited = []
        def read(view):
            visited.append(view['owner_id'])
            self.assertEqual(view['owner_id'], 'RES-R')
            return original(view)
        original_read = owners._read
        def metadata(path, *args, **kwargs):
            self.assertNotEqual(path, raw_path, 'unrelated raw JSON must not be parsed')
            return original_read(path, *args, **kwargs)
        with patch.object(self.service.store, 'read_snapshot', side_effect=read), patch('memory.evidence_adapter.EvidenceAdapter', side_effect=AssertionError('global adapter opened')), patch.object(owners, '_read', side_effect=metadata):
            value = document.build_document(self.service, 'RES-R')
        self.assertEqual([(r['id'], r['level']) for r in value['items']], [(detail['record_id'], 'L1'), (event['record_id'], 'L2')])
        self.assertEqual(visited, ['RES-R'])
        self.assertEqual(value['metrics']['read_memory_owners'], 1)
        self.assertEqual(value['writes'], 0)
        self.assertIn('s=3', value['items'][0]['record']['body_markdown'])

    def test_shared_revocation_hides_all_dependants_and_figure(self):
        detail = self.detail()
        second = self.save(self.operation('detail', detail['payload'], schema_version=2, level='L1',
                           title='第二份说明', body_markdown='第二份同来源合成计算说明', sources=detail['sources']))
        self.put('retrieval/sources.json', {'sources': [{'source_id': 'SRC-FIGURE', 'path': 'research/topic/figures/result.png', 'enabled': False}]})
        result = document.build_document(self.service, 'RES-R')
        self.assertEqual(result['items'], [])
        self.assertEqual({x.get('record_id') for x in result['missing'] if x['code'] == 'ACCESS_DENIED'}, {detail['record_id'], second['record_id']})
        with self.assertRaises(MemoryError):
            document.figure(self.service, 'RES-R', detail['record_id'], 1, 0)

    def test_image_is_fixed_local_raster_and_changed_source_is_not_silent(self):
        detail = self.detail()
        before = document.figure(self.service, 'RES-R', detail['record_id'], 1, 0)
        self.assertTrue(before['data_url'].startswith('data:image/png;base64,'))
        (self.root / 'research/topic/figures/result.png').write_bytes(b'<svg onload="bad()"/>')
        value = document.build_document(self.service, 'RES-R')
        self.assertEqual(value['items'][0]['source_issues'][0]['code'], 'STALE_BASIS')
        with self.assertRaises(MemoryError):
            document.figure(self.service, 'RES-R', detail['record_id'], 1, 0)

    def test_history_traverses_chain_once_and_detects_head_change(self):
        record = self.save(self.operation('event', self.event(), schema_version=2))
        for i in range(3):
            draft = {k: deepcopy(v) for k,v in record.items() if k in {'schema_version','owner_id','kind','level','title','keywords','body_markdown','payload','sources','provenance_gap','discovery','sensitivity','record_reason'}}
            draft['body_markdown'] = f'合成修订{i}'
            draft['change_reason'] = '合成历史测试'
            operation = {'op': 'put_record', 'record_id': record['record_id'], 'expected_revision': record['revision'], 'draft': draft}
            record = self.save(operation)
        owner = owners.resolve_owner(self.root, 'RES-R')
        with patch.object(self.service.store, 'read_snapshot', wraps=self.service.store.read_snapshot) as read:
            values = self.service.store.read_history(owner)
        self.assertEqual(read.call_count, 1)
        self.assertEqual({r['revision'] for r in values}, {1,2,3,4})
        reader = document.Reader(self.service)
        reader.state('RES-R')
        path = self.service.store.path(owner, 'HEAD.json')
        value = json.loads(path.read_text(encoding='utf-8'))
        value['generation'] += 1
        path.write_text(json.dumps(value), encoding='utf-8')
        with self.assertRaisesRegex(MemoryError, 'HEAD'):
            reader.recheck()

    def test_resume_includes_detailed_calculation_and_map_by_default(self):
        detail = self.detail()
        mapping = self.save(self.operation('map', {'topic': '合成研究地图', 'goal_refs': [], 'route_refs': [],
            'result_refs': [], 'question_refs': [], 'conflict_refs': [], 'next_steps': ['核对输入'],
            'coverage': {'owner_ids': ['RES-R'], 'source_versions': [], 'missing': []}},
            schema_version=2, body_markdown='合成 L4 综合正文'))
        result = history.resume(self.service, 'RES-R')
        self.assertIn(detail['record_id'], result['manifest']['selection']['full_ids'])
        self.assertIn(mapping['record_id'], result['manifest']['selection']['full_ids'])
        self.assertIn('合成 L4 综合正文', result['context_text'])
        self.assertIn('s=3', result['context_text'])
        self.assertFalse(result['manifest']['resume']['execution_started'])

    def test_document_round_order_is_natural_not_random_record_id(self):
        records = [{'title': title, 'record_id': str(i), 'created_at': '2026-01-01', 'payload': {}}
                   for i,title in enumerate(['第10轮结果', '第3轮结果', '第1轮结果', '第二轮结果'])]
        self.assertEqual([r['title'] for r in sorted(records,key=document.document_order)],
                         ['第1轮结果', '第二轮结果', '第3轮结果', '第10轮结果'])

    def test_report_fixed_revision_order_coverage_and_revoked_blocks(self):
        detail = self.detail()
        ref = {**research.fixed_ref(detail), 'sha256': detail['record_hash']}
        report = {'version': 1, 'title': '连续合成报告', 'sections': [
            {'section_id': 'start', 'title': '问题', 'role': 'introduction', 'blocks': [{'type': 'prose', 'markdown': '独有连接文本', 'evidence_refs': []}]},
            {'section_id': 'exp', 'title': '实验', 'role': 'experiment', 'blocks': [{'type': 'detail', 'ref': ref}]},
            {'section_id': 'end', 'title': '结论', 'role': 'conclusion', 'blocks': [{'type': 'prose', 'markdown': '依赖实验的秘密结论', 'evidence_refs': [ref]}]}]}
        payload = {'topic': '主题', 'goal_refs': [], 'route_refs': [], 'result_refs': [], 'question_refs': [], 'conflict_refs': [], 'next_steps': [], 'coverage': {'owner_ids': ['RES-R'], 'source_versions': [], 'missing': []}, 'report': report}
        mapping = self.save(self.operation('map', payload, schema_version=2))
        self.assertIn('独有连接文本', index._searchable_payload(payload))
        self.assertNotIn(ref['sha256'], index._searchable_payload(payload))
        draft = {k: deepcopy(detail[k]) for k in ('schema_version','owner_id','kind','level','title','keywords','body_markdown','payload','sources','provenance_gap','discovery','sensitivity','record_reason')}
        draft.update(body_markdown='新版正文不可偷偷替换', change_reason='合成修订')
        self.save({'op': 'put_record', 'record_id': detail['record_id'], 'expected_revision': 1, 'draft': draft})
        self.save(self.operation('detail', detail['payload'], schema_version=2, body_markdown='尚未纳入的计算', sources=detail['sources']))
        value = document.build_document(self.service, 'RES-R', mapping['record_id'])
        self.assertEqual([s['section_id'] for s in value['report']['sections']], ['start', 'exp', 'end'])
        self.assertEqual(value['report']['sections'][1]['blocks'][0]['item']['record']['body_markdown'], detail['body_markdown'])
        self.assertEqual(value['report_version_hints'][0]['current_revision'], 2)
        self.assertEqual(len(value['report_coverage']['uncovered_detail_ids']), 1)
        self.assertFalse(value['report']['complete'])
        self.put('retrieval/sources.json', {'sources': [{'source_id': 'SRC-FIGURE', 'path': 'research/topic/figures/result.png', 'enabled': False}]})
        value = document.build_document(self.service, 'RES-R')
        self.assertIsNone(value['report']['sections'][1]['blocks'][0]['item'])
        self.assertEqual(value['report']['sections'][2]['blocks'][0]['markdown'], '')
        self.assertNotIn('依赖实验的秘密结论', json.dumps(value, ensure_ascii=False))

    def test_report_rejects_duplicate_and_synthesis_before_experiment(self):
        detail = self.detail()
        block = {'type': 'detail', 'ref': {**research.fixed_ref(detail), 'sha256': detail['record_hash']}}
        section = {'section_id': 'exp', 'title': '实验', 'role': 'experiment', 'blocks': [block]}
        report = {'version': 1, 'title': '测试', 'sections': [section]}
        self.assertEqual(contracts.validate_report(report), [])
        for sections in ([section, section], [{'section_id': 'end', 'title': '结论', 'role': 'conclusion', 'blocks': [{'type': 'prose', 'markdown': '结论', 'evidence_refs': []}]}, section]):
            self.assertTrue(contracts.validate_report({**report, 'sections': sections}))
        self.assertIsNone(document.build_document(self.service, 'RES-R')['report'])
