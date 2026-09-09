"""阶段巩固必须保留未完成项、拒绝旧依据并避免重复生成正文。"""
from copy import deepcopy
import hashlib
import json
import unittest
import uuid
from test_memory_store import MemoryStoreTests, draft, request
from memory import consolidation, research, packets
from test_memory_contracts import examples
from memory.errors import MemoryError


class ConsolidationTests(unittest.TestCase):
    setUp = MemoryStoreTests.setUp
    tearDown = MemoryStoreTests.tearDown

    def seed_three(self):
        head = None
        for number in range(3):
            value = draft(); value["title"] += str(number)
            receipt = self.service.commit(request(value, head=head))
            head = receipt["commit_id"]
        return head

    def application(self, basis, decisions):
        return {"request_id": str(uuid.uuid4()), "owner_id": "RES-TEST", "actor": {"kind": "ai", "id": "synthetic-test"},
                "expected_head": self.service.inspect("RES-TEST")["head"]["commit_id"],
                "reason": "合成阶段巩固", "basis": basis, "decisions": decisions}

    def put(self, path, value):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(value, ensure_ascii=False) if isinstance(value, dict) else value, encoding='utf-8')
        return target

    def save(self, value):
        head = self.service.inspect(value['owner_id'])['head']
        receipt = self.service.commit(request(value, head=head['commit_id'] if head else None))
        return self.service.inspect(value['owner_id'], record_id=receipt['record_results'][0]['record_id'])['record']

    def file_ref(self, identity, path):
        return {'target_kind': 'file', 'target_id': identity, 'revision': None,
                'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'locator': '', 'relation': 'input'}

    def test_n01_external_bytes_review_and_cross_owner_impact(self):
        source = self.put('data/input.txt', '固定原测量')
        self.put('retrieval/sources.json', {'sources': [{'source_id': 'SRC-CONS', 'path': 'data/input.txt', 'enabled': True}]})
        ref = self.file_ref('SRC-CONS', source)
        native = self.put('runs/source/run.json', {'run_id': 'RUN-SOURCE', 'status': 'running', 'claims': []})
        native_ref = packets._item(packets.Snapshot(self.service), 'RUN-SOURCE',
            packets._request(self.service, {'include_ids': ['RUN-SOURCE']}))['ref']
        value = draft(); value.update(sources=[ref, native_ref], provenance_gap=None)
        value['payload']['claims'] = [{'claim_id': 'CLM-CONS', 'statement': '合成范围内的待检验结论',
                                      'scope': 'synthetic:only', 'kind': 'inference', 'evidence_refs': [ref]}]
        original = self.save(value)
        claim_value = packets.Snapshot(self.service).adapter.resolve_claim('CLM-CONS')
        claim_ref = {'target_kind': 'claim', 'target_id': 'CLM-CONS', 'revision': None,
                     'sha256': claim_value['sha256'], 'locator': '', 'relation': 'references'}
        dependent = draft(); dependent.update(title='直接引用结论的经验', sources=[claim_ref], provenance_gap=None)
        dependent['payload']['claim_refs'] = [claim_ref]
        self.save(dependent)
        problem = draft(); problem.update(kind='question', payload=examples()['question'], title='延期问题')
        question = self.save(problem)
        self.put('research/cross/research.json', {'research_id': 'RES-CROSS', 'title': '跨对象地图'})
        cross = draft('RES-CROSS'); cross.update(kind='map', payload=examples()['map'],
            sources=[research.fixed_ref(original)], provenance_gap=None)
        cross['payload']['result_refs'] = [research.fixed_ref(original)]
        mapping = self.save(cross)
        self.put('research/unrelated/research.json', {'research_id': 'RES-UNRELATED', 'title': '无关对象'})
        unrelated = self.save(draft('RES-UNRELATED'))
        basis = consolidation.prepare(self.service, 'RES-TEST')
        decisions = [{'target': item, 'action': 'defer' if item['target_id'] == question['record_id'] else 'retain',
                      'reason': '合成基线保留'} for item in [*basis['changed'], *basis['affected']]
                     if item['target_id'] in {original['record_id'], question['record_id'], mapping['record_id']}]
        # 同一对象可能由changed与affected同时到达；每个身份只处置一次。
        decisions = list({item['target']['target_id']: item for item in decisions}.values())
        consolidation.apply(self.service, self.application(basis, decisions))
        old_draft = consolidation.prepare(self.service, 'RES-TEST')
        old_request = self.application(old_draft, [])
        before = self.service.inspect('RES-TEST')['head']
        source.write_text('变化后的原测量', encoding='utf-8')
        native.write_text(json.dumps({'run_id': 'RUN-SOURCE', 'status': 'completed', 'claims': []}), encoding='utf-8')
        with self.assertRaises(MemoryError) as caught:
            consolidation.apply(self.service, old_request)
        self.assertEqual(caught.exception.code, 'STALE_BASIS')
        self.assertEqual(self.service.inspect('RES-TEST')['head'], before)
        fresh = self.save(draft())
        self.service.review({'schema_version': 1, 'request_id': str(uuid.uuid4()), 'target_claim_id': 'CLM-CONS',
            'state': 'retracted', 'actor': {'kind': 'workflow', 'id': 'test'}, 'reason': '真实合成撤回',
            'scope': 'synthetic:only', 'evidence_refs': [], 'expected_head': self.service.inspect('RES-TEST')['head']['commit_id']})
        changed = consolidation.prepare(self.service, 'RES-TEST')
        self.assertTrue({'SRC-CONS', 'RUN-SOURCE', fresh['record_id'], 'CLM-CONS'} <= {r['target_id'] for r in changed['changed']})
        self.assertTrue({original['record_id'], mapping['record_id']} <= {r['target_id'] for r in changed['affected']})
        self.assertIn(question['record_id'], [r['target_id'] for r in changed['remaining']])
        self.assertNotIn(unrelated['record_id'], [r['target_id'] for r in changed['affected']])
        self.assertEqual(self.service.inspect('RES-TEST', 1, record_id=original['record_id'])['record'], original)

    def test_n03_real_revise_retain_defer_and_unhandled(self):
        self.seed_three()
        map_value = draft(); map_value.update(kind='map', payload=examples()['map'], title='导航地图')
        mapping = self.save(map_value)
        basis = consolidation.prepare(self.service, 'RES-TEST')
        records = self.service.inspect('RES-TEST')['records']
        others = [r for r in basis['changed'] if r['target_id'] != mapping['record_id']]
        revised = research._draft(mapping)
        revised['payload']['next_steps'] = ['取得新输入后继续']
        revised['change_reason'] = '同批更新下一步导航'
        decisions = [{'target': {**research.fixed_ref(mapping), 'revision': 2}, 'action': 'revise', 'reason': '更新导航'},
                     {'target': others[0], 'action': 'retain', 'reason': '已有边界仍成立'},
                     {'target': others[1], 'action': 'defer', 'reason': '缺少新输入'}]
        req = self.application(basis, decisions)
        req['operations'] = [{'op': 'put_record', 'record_id': mapping['record_id'], 'expected_revision': 1, 'draft': revised}]
        receipt = consolidation.apply(self.service, req)
        saved = [r for r in self.service.inspect('RES-TEST')['records'].values() if r['kind'] == 'consolidation'][0]
        self.assertEqual(saved['payload']['decisions'][0]['target']['revision'], 2)
        again = consolidation.prepare(self.service, 'RES-TEST')
        self.assertEqual({r['target_id'] for r in again['remaining']}, {others[1]['target_id'], others[2]['target_id']})
        self.assertEqual(self.service.inspect('RES-TEST', 1, record_id=mapping['record_id'])['record'], mapping)
        self.assertEqual(self.service.inspect('RES-TEST', record_id=mapping['record_id'])['record']['revision'], 2)
        repeated = {**deepcopy(req), 'request_id': str(uuid.uuid4())}
        self.assertEqual(consolidation.apply(self.service, repeated)['save_status'], 'no_change')

    def test_n07_same_source_paraphrase_distinct_source_and_explicit_counterexample(self):
        first = self.put('data/a.txt', '合成测量 A')
        second = self.put('data/b.txt', '合成测量 B')
        self.put('retrieval/sources.json', {'sources': [
            {'source_id': 'SRC-A', 'path': 'data/a.txt', 'enabled': True},
            {'source_id': 'SRC-B', 'path': 'data/b.txt', 'enabled': True}]})
        a_ref, b_ref = self.file_ref('SRC-A', first), self.file_ref('SRC-B', second)
        rows = []
        for title, source in [('同源原述', a_ref), ('同源改述', a_ref), ('异源相似结论', b_ref)]:
            value = draft(); value.update(title=title, sources=[source], provenance_gap=None, keywords=['预热', '温漂'])
            rows.append(self.save(value))
        opposite = draft(); opposite.update(title='同范围相反结果', sources=[b_ref, research.fixed_ref(rows[0], 'contradicts')], provenance_gap=None)
        contrary = self.save(opposite)
        before = self.service.inspect('RES-TEST')['records']
        prepared = consolidation.prepare(self.service, 'RES-TEST')
        merges = [{r['target_id'] for r in c['refs']} for c in prepared['candidates'] if c['kind'] == 'merge_candidate']
        self.assertIn({rows[0]['record_id'], rows[1]['record_id']}, merges)
        self.assertFalse(any(rows[2]['record_id'] in pair for pair in merges))
        conflicts = [c for c in prepared['candidates'] if c['kind'] == 'conflict_candidate']
        self.assertTrue(any({r['target_id'] for r in c['refs']} == {rows[0]['record_id'], contrary['record_id']} and c['basis_refs'] for c in conflicts))
        consolidation.apply(self.service, self.application(prepared, []))
        after = self.service.inspect('RES-TEST')['records']
        self.assertTrue(all(after[rid] == row for rid, row in before.items()))

    def test_N01_N02_N03_repeat_and_remaining(self):
        self.seed_three()
        map_value = draft(); map_value.update(kind='map', payload=examples()['map'], title='重复巩固导航地图')
        mapping = self.save(map_value)
        basis = consolidation.prepare(self.service, "RES-TEST")
        self.assertEqual(len(basis["changed"]), 4)
        others = [r for r in basis['changed'] if r['target_id'] != mapping['record_id']]
        decisions = [{"target": others[0], "action": "retain", "reason": "原边界仍适用"},
                     {"target": others[1], "action": "defer", "reason": "尚缺测试结果"},
                     {'target': {**research.fixed_ref(mapping), 'revision': 2}, 'action': 'revise', 'reason': '导航补充下一步'}]
        req = self.application(basis, decisions)
        revised = research._draft(mapping)
        revised['payload']['next_steps'] = ['验证下一份合成输入']
        revised['change_reason'] = '补充下一步，不嵌入旧地图正文'
        req['operations'] = [{'op': 'put_record', 'record_id': mapping['record_id'], 'expected_revision': 1, 'draft': revised}]
        receipt = consolidation.apply(self.service, req)
        for _ in range(100):
            repeated = deepcopy(req); repeated["request_id"] = str(uuid.uuid4())
            value = consolidation.apply(self.service, repeated)
            self.assertEqual(value["save_status"], "no_change")
            self.assertEqual(value["commit_id"], receipt["commit_id"])
        records = self.service.inspect("RES-TEST")["records"]
        self.assertEqual(sum(r["kind"] == "consolidation" for r in records.values()), 1)
        self.assertEqual(records[mapping['record_id']]['revision'], 2)
        self.assertEqual(records[mapping['record_id']]['body_markdown'], mapping['body_markdown'])
        again = consolidation.prepare(self.service, "RES-TEST")
        self.assertEqual(len(again["remaining"]), 2)
        self.assertEqual(again["changed"], [])

    def test_N04_stale_basis_and_forged_omission_are_rejected(self):
        head = self.seed_three()
        basis = consolidation.prepare(self.service, "RES-TEST")
        req = self.application(basis, [])
        value = draft(); value["title"] = "新的独立结果"
        self.service.commit(request(value, head=head))
        before = self.service.inspect("RES-TEST")["head"]
        with self.assertRaises(MemoryError) as caught:
            consolidation.apply(self.service, req)
        self.assertEqual(caught.exception.code, "STALE_BASIS")
        self.assertEqual(self.service.inspect("RES-TEST")["head"], before)
        from memory.contracts import canonical_hash
        basis = consolidation.prepare(self.service, "RES-TEST")
        basis["changed"] = []
        basis["basis_hash"] = canonical_hash({k:basis[k] for k in ("owner_id", "basis_heads", "changed", "affected", "remaining")})
        with self.assertRaises(MemoryError):
            consolidation.apply(self.service, self.application(basis, []))


del MemoryStoreTests
