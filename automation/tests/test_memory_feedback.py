"""N08：真实查询、后续 Run 和规范反馈形成闭环，不修改科学复核。"""
import uuid
import unittest
from copy import deepcopy

import test_memory_research as fixture
from memory import feedback, search, packets, research
from memory.errors import MemoryError


class FeedbackTests(unittest.TestCase):
    setUp = fixture.ResearchTests.setUp
    put = fixture.ResearchTests.put
    operation = fixture.ResearchTests.operation
    request = fixture.ResearchTests.request
    save = fixture.ResearchTests.save
    event = fixture.ResearchTests.event

    def test_n08_actual_search_six_labels_and_following_run_preserve_review(self):
        record = self.save(self.operation('event', self.event(action='反馈闭环温漂合成观察', claims=[{
            'claim_id': 'CLM-FEEDBACK', 'statement': '反馈不能让此合成结论通过复核',
            'kind': 'inference', 'scope': 'synthetic:only', 'evidence_refs': []}]),
            keywords=['温漂'], discovery='workspace_summary'))
        query = search.search(self.root, {'query': '温漂', 'owner_id': 'RES-R', 'purpose': 'exploration', 'vector': 'off'}, refresh=True)
        self.assertIn(record['record_id'], [row['canonical_id'] for row in query['candidates']])
        self.assertTrue((self.root / 'retrieval/queries' / (query['query_id'] + '.json')).is_file())
        self.put('runs/later/run.json', {'run_id': 'RUN-LATER', 'title': '查询后的实际合成应用',
            'status': 'completed', 'claims': [], 'related_research_ids': ['RES-R'], 'summary': '取得合成应用结果'})
        snap = packets.Snapshot(self.service)
        run = packets._item(snap, 'RUN-LATER', packets._request(self.service, {'include_ids': ['RUN-LATER']}))['ref']
        review_before = snap.adapter.claim_state('CLM-FEEDBACK')['review_state']
        saved = []
        for label in ('missing', 'invalid_analogy', 'lost_boundary', 'stale', 'adopted', 'outcome'):
            request = {'request_id': str(uuid.uuid4()), 'actor': {'kind': 'ai', 'id': 'synthetic-test'},
                'owner_id': 'RES-R', 'expected_head': self.service.inspect('RES-R')['head']['commit_id'],
                'query_id': query['query_id'], 'target': research.fixed_ref(record), 'label': label,
                'note': '真实闭环合成断言 ' + label, 'adopted_in': run if label in {'adopted', 'outcome'} else None}
            receipt = feedback.save(self.service, request)
            row = self.service.inspect('RES-R', record_id=receipt['record_results'][0]['record_id'])['record']
            self.assertEqual(row['payload']['query_id'], query['query_id'])
            self.assertEqual(row['payload']['target'], research.fixed_ref(record))
            self.assertIn(research.fixed_ref(record), row['sources'])
            if label in {'adopted', 'outcome'}:
                self.assertEqual(row['payload']['adopted_in'], run)
                self.assertIn(run, row['sources'])
            saved.append(row)
        before = self.service.inspect('RES-R')['head']
        for replacement in ({'query_id': 'QMEM-' + str(uuid.uuid4())},
                            {'target': {**research.fixed_ref(record), 'revision': 999}}, {'adopted_in': None}):
            invalid = {**deepcopy(request), **replacement, 'request_id': str(uuid.uuid4()), 'expected_head': before['commit_id']}
            with self.assertRaises(MemoryError):
                feedback.save(self.service, invalid)
            self.assertEqual(self.service.inspect('RES-R')['head'], before)
        self.assertEqual(len(saved), 6)
        self.assertEqual(packets.Snapshot(self.service).adapter.claim_state('CLM-FEEDBACK')['review_state'], review_before)
