"""O03: repeat real history/index operations without duplicating a Run attempt.

The three statements deliberately use different terms. Searching each term
must return its own CLM identity, not just one inseparable Run result.
"""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from memory_fixture import materialize, snapshot
from memory import history, index, owners, search
from memory.service import MemoryService


class LegacyIdentityTests(unittest.TestCase):
    def test_O03_three_claims_repeat_history_and_index_keep_one_run_attempt(self):
        with tempfile.TemporaryDirectory(prefix='SYNTHETIC O03 中文 ') as temporary:
            fixture = materialize(Path(temporary) / 'workspace', isolation_root=temporary)
            root = fixture.root
            run = owners.resolve_owner(root, 'RUN-SYN-THERMAL')
            path = root / run['native_ref']['path']
            raw = json.loads(path.read_text(encoding='utf-8'))
            template = raw['claims'][0]
            expected = {}
            raw['claims'] = []
            for n, token in enumerate(('SYNALPHAPREHEAT', 'SYNBETAINPUT', 'SYNGAMMABOUNDARY')):
                claim = deepcopy(template)
                claim.update(claim_id='CLM-O03-' + str(n), statement=token + ' SYNTHETIC ONLY 独立结论')
                raw['claims'].append(claim)
                expected[token] = claim['claim_id']
            path.write_text(json.dumps(raw, ensure_ascii=False), encoding='utf-8')
            # The explicit research link defines membership, not its directory.
            raw['related_research_ids'] = ['RES-SYN-THERMAL']
            path.write_text(json.dumps(raw, ensure_ascii=False), encoding='utf-8')
            original = path.read_bytes()
            service = MemoryService(root)
            before = snapshot(root)
            adapter = owners.run_adapter(root, 'RUN-SYN-THERMAL')
            self.assertEqual(adapter['event_id'], 'RUN-SYN-THERMAL')
            self.assertEqual({c['claim_id'] for c in adapter['claims']}, set(expected.values()))
            previous = None
            for _ in range(3):
                index.rebuild(root, vector='off')
                timeline = history.build_history(service, 'RES-SYN-THERMAL', limit=500)
                attempts = [row for row in timeline['items'] if row['canonical_id'] == 'RUN-SYN-THERMAL']
                self.assertEqual(len(attempts), 1)
                self.assertEqual(attempts[0]['kind'], 'run')
                if previous is not None:
                    self.assertEqual(timeline['items'], previous)
                previous = timeline['items']
                for token, cid in expected.items():
                    result = search.search(root, {'query': token, 'vector': 'off', 'purpose': 'exploration',
                        'owner_id': 'RES-SYN-THERMAL', 'stage': 'wide', 'limit': 100}, record=False)
                    hits = [r for r in result['candidates'] if r['canonical_id'] in expected.values()]
                    self.assertEqual([r['canonical_id'] for r in hits], [cid])
                    self.assertEqual(hits[0]['source_ref']['target_kind'], 'claim')
                    self.assertTrue(hits[0]['source_ref']['sha256'])
                self.assertEqual(path.read_bytes(), original)
                self.assertEqual(service.inspect('RUN-SYN-THERMAL')['records'], {})
                self.assertEqual(service.inspect('RES-SYN-THERMAL')['records'], {})
            # Only disposable retrieval outputs can be added; native/sidecar
            # snapshots remain intact and no MEM-event has been manufactured.
            self.assertFalse(list(root.glob('**/memory/commits/*/records/*.json')))
            after = snapshot(root)
            for name, digest in before['files'].items():
                self.assertEqual(after['files'][name], digest, name)


if __name__ == '__main__':
    unittest.main()
