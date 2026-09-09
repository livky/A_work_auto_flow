"""G01/G03–G07 real decisions, indexed endpoint views and frozen directed graph."""
from copy import deepcopy
from contextlib import closing
import json
from pathlib import Path
import unittest
import uuid

from test_memory_store import MemoryStoreTests, ROOT, draft, request, snapshot_files
from memory import associations, index, packets, research, search
from memory.errors import MemoryError
from memory.evidence_adapter import EvidenceAdapter


class AssociationNavigationTests(unittest.TestCase):
    setUp = MemoryStoreTests.setUp
    tearDown = MemoryStoreTests.tearDown

    def save(self, marker, with_claim=False):
        value = draft(); value.update(title='SYNTHETIC ONLY ' + marker, body_markdown=marker,
            keywords=['预热', '偏差', marker])
        if with_claim:
            value['payload']['claims'] = [{'claim_id': 'CLM-G-' + marker, 'statement': 'SYNTHETIC ONLY ' + marker,
                'kind': 'inference', 'scope': 'synthetic:only', 'evidence_refs': []}]
        head = self.service.inspect('RES-TEST')['head']
        receipt = self.service.commit(request(value, head=head['commit_id'] if head else None))
        return self.service.inspect('RES-TEST')['records'][receipt['record_results'][0]['record_id']]

    def decide(self, left, right, *, status='accepted', relation='analogous_to', payload=None):
        payload = payload or {'from': associations.record_ref(left), 'to': associations.record_ref(right),
            'relation': relation, 'explanation': 'SYNTHETIC ONLY 共同前置条件', 'shared_structure': '前置条件影响结果',
            'transfer_limits': ['不能直接迁移参数；不提供科学支持'],
            'basis_refs': [associations.record_ref(left), associations.record_ref(right)], 'status': status}
        req = {'request_id': str(uuid.uuid4()), 'actor': {'kind': 'workflow', 'id': 'synthetic-g'},
            'owner_id': 'RES-TEST', 'expected_head': self.service.inspect('RES-TEST')['head']['commit_id'],
            'payload': payload, 'reason': 'SYNTHETIC ONLY 测试导航', 'title': 'SYNRELATIONMARKER',
            'discovery': 'workspace_summary'}
        return associations.decide(self.service, req), req

    def test_G01_explanation_candidate_and_real_proposal_are_read_only(self):
        exact = associations.keyword_candidates(['预热', '偏差', '条件'], ['预热', '偏差', '夹具'])
        self.assertAlmostEqual(exact['score'], .5, delta=1e-12)
        self.assertEqual(exact['shared'], ['偏差', '预热'])
        self.assertEqual(exact['left_only'], ['条件'])
        self.assertEqual(exact['right_only'], ['夹具'])
        self.assertEqual(exact['status'], 'candidate')
        self.assertFalse(associations.keyword_candidates(['预热'], ['预热', '夹具'])['eligible'])
        a, b = self.save('A'), self.save('B')
        before = snapshot_files(self.root)
        proposed = associations.propose(self.service, {'owner_id': 'RES-TEST', 'method': 'keyword', 'seeds': [a['record_id']]})
        self.assertEqual(len(proposed['candidates']), 1)
        self.assertEqual(proposed['candidates'][0]['status'], 'candidate')
        self.assertNotIn('review', proposed['candidates'][0])
        self.assertNotIn('supports', json.dumps(proposed['candidates']))
        self.assertEqual(before, snapshot_files(self.root))

    def test_G03_G07_indexed_reverse_view_single_edge_and_stale_search(self):
        a, b = self.save('LEFT', True), self.save('RIGHT', True)
        states_before = {cid: EvidenceAdapter(self.service).claim_state(cid) for cid in ('CLM-G-LEFT', 'CLM-G-RIGHT')}
        receipt, req = self.decide(a, b)
        rid = receipt['record_results'][0]['record_id']
        self.assertEqual(associations.decide(self.service, req)['commit_id'], receipt['commit_id'])
        originals = {x['record_id']: deepcopy(x) for x in (a, b)}
        index.reconcile(self.root, vector='off')
        before = snapshot_files(self.root)
        for endpoint, other, direction in ((a, b, 'forward'), (b, a, 'reverse')):
            result = associations.propose(self.service, {'owner_id': 'RES-TEST', 'method': 'explicit', 'seeds': [endpoint['record_id']]})
            self.assertEqual(len(result['neighbors']), 1)
            neighbor = result['neighbors'][0]
            self.assertEqual(neighbor['association_id'], rid)
            self.assertEqual(neighbor['target_id'], other['record_id'])
            self.assertEqual(neighbor['direction'], direction)
            self.assertTrue(neighbor['derived_view'])
        self.assertEqual(before, snapshot_files(self.root))
        with closing(index.connect(self.root, create=False)) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM memory_edges').fetchone()[0], 1)
        for status in ('rejected', 'withdrawn', 'accepted'):
            receipt, _ = self.decide(a, b, status=status)
            self.assertEqual(receipt['record_results'][0]['record_id'], rid)
        records = self.service.inspect('RES-TEST')['records']
        self.assertEqual({key: records[key] for key in originals}, originals)
        self.assertEqual({cid: EvidenceAdapter(self.service).claim_state(cid) for cid in states_before}, states_before)
        self.assertEqual([r['record_id'] for r in records.values() if r['kind'] == 'association'], [rid])
        relation = records[rid]
        self.assertEqual([self.service.inspect('RES-TEST', n, record_id=rid)['record']['payload']['status'] for n in range(1,5)],
                         ['accepted', 'rejected', 'withdrawn', 'accepted'])
        update = research._draft(a); update['body_markdown'] = 'LEFT UPDATED'; update['change_reason'] = 'SYNTHETIC 新来源修订'
        self.service.commit(request(update, head=receipt['commit_id'], rid=a['record_id'], revision=1))
        stale = associations.view(self.service, relation)
        self.assertTrue(stale['stale'])
        self.assertEqual(stale['changed_endpoints'], [{'target_id': a['record_id'], 'reason': 'revision_changed', 'current_revision': 2}])
        self.assertEqual(relation['payload']['from']['revision'], 1)
        self.assertEqual(associations.expand_neighbors([a['record_id']], [stale]), [])
        current = associations.propose(self.service, {'owner_id': 'RES-TEST', 'method': 'explicit', 'seeds': [b['record_id']]})
        self.assertEqual(current['neighbors'], [])
        result = search.search(self.root, {'query': 'SYNRELATIONMARKER', 'owner_id': 'RES-TEST', 'vector': 'off', 'purpose': 'exploration'}, record=False)
        hit = next(row for row in result['candidates'] if row['canonical_id'] == rid)
        self.assertTrue(any(risk['code'] == 'STALE_ASSOCIATION' for risk in hit['risks']))
        formal = search.search(self.root, {'query': 'SYNRELATIONMARKER', 'owner_id': 'RES-TEST', 'vector': 'off',
            'purpose': 'formal', 'scope': 'synthetic:only'}, record=False)
        self.assertEqual(formal['candidates'], [])

    def test_G04_frozen_valid_wrong_analogy_never_becomes_support(self):
        raw = json.loads((ROOT/'docs/design/system-memory/fixtures/records.json').read_text(encoding='utf-8'))
        recipes = {r['record_id']: r for r in raw['records'] if r['record_id'] in {'MEM-ASSOC-VALID', 'MEM-ASSOC-WRONG'}}
        a, b, c = self.save('THERMAL'), self.save('PRESSURE'), self.save('RETRY')
        before_reviews = deepcopy(EvidenceAdapter(self.service).reviews)
        saved = []
        for name, other in (('MEM-ASSOC-VALID', b), ('MEM-ASSOC-WRONG', c)):
            payload = deepcopy(recipes[name]['payload'])
            payload.update({'from': associations.record_ref(a), 'to': associations.record_ref(other),
                            'basis_refs': [associations.record_ref(a), associations.record_ref(other)]})
            receipt, _ = self.decide(a, other, payload=payload)
            rid = receipt['record_results'][0]['record_id']; saved.append(rid)
            row = self.service.inspect('RES-TEST')['records'][rid]
            self.assertEqual(row['payload']['status'], recipes[name]['payload']['status'])
            self.assertTrue(row['payload']['shared_structure'])
            self.assertTrue(row['payload']['transfer_limits'])
            output = packets.expand(self.service, [associations.record_ref(row)], {'owner_id': 'RES-TEST', 'purpose': 'formal', 'scope': 'synthetic:only'})
            self.assertEqual(output['context_text'], '')
            for field, value in (('shared_structure', ''), ('transfer_limits', [])):
                invalid = deepcopy(payload); invalid[field] = value
                before = snapshot_files(self.root)
                with self.assertRaises(MemoryError):
                    self.decide(a, other, payload=invalid)
                self.assertEqual(before, snapshot_files(self.root))
        rows = self.service.inspect('RES-TEST')['records']
        self.assertEqual(rows[saved[1]]['payload']['status'], 'candidate')
        self.assertEqual(EvidenceAdapter(self.service).reviews, before_reviews)
        self.assertFalse(any(r['payload'].get('relation') in {'supports','input'} for r in rows.values()))

    def test_G04_public_formal_search_rejects_candidate_even_with_accepted_endpoint(self):
        from memory_fixture import build_verified_legacy
        from memory.service import MemoryService
        fixture = build_verified_legacy(self.root/'verified', isolation_root=self.root)
        service = MemoryService(Path(fixture['root']))
        adapter = EvidenceAdapter(service)
        self.assertTrue(adapter.claim_state('CLM-SYNTHETIC', 'synthetic:only')['effective_validity'])
        refs = [{'target_kind':kind,'target_id':target,'revision':None,'sha256':adapter.legacy.nodes[target]['fingerprint'],
                 'locator':'','relation':'references'} for kind,target in (('owner','RUN-SYNTHETIC'),('claim','CLM-SYNTHETIC'))]
        receipt = associations.decide(service, {'request_id':str(uuid.uuid4()), 'actor':{'kind':'workflow','id':'SYNTHETIC G04'},
            'owner_id':'RUN-SYNTHETIC','expected_head':None,'title':'SYNG04CANDIDATE', 'reason':'类比仍不是科学支持',
            'payload':{'from':refs[0],'to':refs[1],'relation':'analogous_to','explanation':'SYNTHETIC ONLY 待检查',
                       'shared_structure':'待检查','transfer_limits':['不可作为支持'],'basis_refs':refs,'status':'candidate'}})
        rid=receipt['record_results'][0]['record_id']
        index.reconcile(service.root,vector='off')
        result=search.search(service.root,{'query':'SYNG04CANDIDATE','owner_id':'RUN-SYNTHETIC','vector':'off',
            'purpose':'formal','scope':'synthetic:only'},record=False)
        self.assertEqual(result['candidates'],[])
        self.assertTrue(any(row['canonical_id']==rid for row in result['rejected']))
        row=service.inspect('RUN-SYNTHETIC')['records'][rid]
        self.assertEqual(packets.expand(service,[associations.record_ref(row)],{'owner_id':'RUN-SYNTHETIC',
            'purpose':'formal','scope':'synthetic:only'})['context_text'],'')
        self.assertTrue(EvidenceAdapter(service).claim_state('CLM-SYNTHETIC','synthetic:only')['effective_validity'])

    def test_G05_G06_frozen_six_node_directed_graph_and_excluded_bridge(self):
        variant = json.loads((ROOT/'docs/design/system-memory/fixtures/variants.json').read_text(encoding='utf-8'))['graph_variants'][0]
        mapping = {node: self.save(node)['record_id'] for node in variant['nodes']}
        self.assertEqual(len(set(mapping.values())), 6)
        def edge(a,b):
            return {'from': {'target_id': mapping[a]}, 'to': {'target_id': mapping[b]}, 'status':'accepted', 'relation':'related_to'}
        edges = [edge(a,b) for a,b in variant['edges']]
        for hops, expected in ((1,variant['one_hop_from_A']), (2,variant['two_hops_from_A'])):
            actual = associations.expand_neighbors([mapping['A']], edges, hops=hops)
            self.assertEqual({r['target_id'] for r in actual}, {mapping[x] for x in expected})
            self.assertEqual(len(actual), len({r['target_id'] for r in actual}))
        before = deepcopy(edges)
        with self.assertRaises(MemoryError):
            associations.expand_neighbors([mapping['A']], edges, hops=2, expansion_count=2, limit=3)
        self.assertEqual(edges, before)
        self.assertLessEqual(len(associations.expand_neighbors([mapping['A']], edges, hops=2, limit=1)), 1)
        line = [edge('A','B'), edge('B','C')]
        for options in ({'exclude_ids':[mapping['B']]}, {'allowed_ids':[mapping['A'],mapping['C']]}):
            self.assertEqual(associations.expand_neighbors([mapping['A']], line, hops=2, **options), [])
        # Explicit C remains a direct search selection. No B-containing path is
        # fabricated by treating an excluded intermediate as a hidden bridge.
        index.reconcile(self.root, vector='off')
        direct = search.search(self.root, {'query': 'SYNTHETIC', 'owner_id':'RES-TEST', 'purpose':'exploration', 'vector':'off',
            'include_ids':[mapping['C']], 'exclude_ids':[mapping['B']], 'stage':'wide'}, record=False)
        selected = next(row for row in direct['candidates'] if row['canonical_id']==mapping['C'])
        self.assertTrue(selected['match_reason']['explicit_selection'])
        self.assertNotIn(mapping['B'], json.dumps(selected['expansion_paths']))


del MemoryStoreTests

if __name__ == '__main__':
    unittest.main()
