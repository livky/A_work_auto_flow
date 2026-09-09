"""Topic evidence regression: preserve identity, fallbacks and user selection.

These tests verify ranking mechanics with synthetic channels/real SQLite; they
do not establish semantic model quality. Real-model evaluation remains separate.
"""
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'automation/scripts'))
from memory import search
from memory_fixture import materialize
from test_memory_index import draft, request
from memory.service import MemoryService


class TopicRankingTests(unittest.TestCase):
    def test_specific_claim_precedes_container_without_merging_identity(self):
        channels = {'fts':['RUN','EXPERIENCE','CLAIM'], 'vector':['NOISE','RUN','CLAIM','EXPERIENCE']}
        rows = {
            'RUN': {'keywords':['预热'], 'owner_id':'RUN', 'entity_kind':'legacy-run'},
            'CLAIM': {'keywords':['预热'], 'owner_id':'RUN', 'entity_kind':'legacy-claim'},
            'EXPERIENCE': {'keywords':['预热'], 'owner_id':'RESEARCH', 'entity_kind':'record'},
            'NOISE': {'keywords':['预载'], 'owner_id':'OTHER', 'entity_kind':'record'},
        }
        result, terms = search.topic_evidence_ranking(channels, rows, '预热应该注意什么？')
        self.assertEqual(terms, ['预热'])
        ids = [r['canonical_id'] for r in result]
        self.assertEqual(set(ids), set(rows))
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(set(ids[:2]), {'CLAIM','EXPERIENCE'})
        self.assertGreater(ids.index('RUN'), ids.index('CLAIM'))
        self.assertEqual(result[-1]['priority_tier'], 2)
        expected = search.rrf({'fts':['EXPERIENCE','CLAIM'], 'vector':['CLAIM','EXPERIENCE']})
        self.assertEqual([(r['canonical_id'],r['score']) for r in result[:2]],
                         [(r['canonical_id'],r['score']) for r in expected])

    def test_no_explicit_topic_keeps_vector_discovery_exactly(self):
        channels = {'fts':['B'], 'vector':['A','B']}
        rows = {cid:{'keywords':['预热'], 'entity_kind':'record'} for cid in ('A','B')}
        result, terms = search.topic_evidence_ranking(channels, rows, '读数一直变动该怎么办')
        self.assertEqual(terms, [])
        self.assertEqual(result, search.rrf(channels))

    def test_missing_keywords_and_unknown_granularity_are_retained(self):
        channels = {'fts':['UNTAGGED','TAGGED'], 'vector':['UNTAGGED']}
        rows = {'UNTAGGED':{'keywords':[], 'entity_kind':'record'},
                'TAGGED':{'keywords':['vibration'], 'entity_kind':'record'}}
        result, terms = search.topic_evidence_ranking(channels, rows, 'VIBRATION 边界')
        self.assertEqual(terms, ['vibration'])
        self.assertEqual([r['canonical_id'] for r in result], ['TAGGED','UNTAGGED'])
        self.assertEqual(result[1]['priority_tier'], 1)

    def test_english_keyword_requires_identifier_boundary(self):
        channels = {'fts':['A']}
        rows = {'A':{'keywords':['cat'], 'entity_kind':'record'}}
        self.assertEqual(search.topic_evidence_ranking(channels, rows, 'concatenate')[1], [])
        self.assertEqual(search.topic_evidence_ranking(channels, rows, '查看CAT参数')[1], ['cat'])

    def test_live_search_explicit_selection_and_exclusion_override_tiers(self):
        with tempfile.TemporaryDirectory() as temp:
            fixture = materialize(Path(temp)/'workspace', isolation_root=Path(temp))
            service = MemoryService(fixture.root)
            owner = 'RES-SYN-THERMAL'
            head = None
            created = []
            for topic in ('预热','预载'):
                value = draft(owner, title=topic+'条件', body='预热和预载都需检查条件')
                value['keywords'] = [topic]
                receipt = service.commit(request(value, head=head))
                head = receipt['commit_id']
                created.append(receipt['record_results'][0]['record_id'])
            query = {'query':'预热', 'purpose':'exploration', 'owner_id':owner,
                     'vector':'off', 'stage':'wide', 'limit':100,
                     'include_ids':[created[1]], 'full_ids':[created[1]]}
            result = search.search(fixture.root, query, record=False)
            self.assertEqual(result['candidates'][0]['canonical_id'], created[1])
            query['exclude_ids'] = [created[1]]
            excluded = search.search(fixture.root, query, record=False)
            self.assertNotIn(created[1], [r['canonical_id'] for r in excluded['candidates']])
            by_id = search.search(fixture.root, {**query, 'query':created[0]}, record=False)
            selected = next(r for r in by_id['candidates'] if r['canonical_id']==created[0])
            self.assertEqual(selected['match_reason']['topic_terms'], [])
            self.assertIn('identity', selected['rank_channels'])


if __name__ == '__main__':
    unittest.main()
