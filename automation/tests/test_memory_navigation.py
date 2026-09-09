"""U05: public packet navigation follows fixed, authorized one-hop references."""
from copy import deepcopy
import json
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from memory_fixture import materialize
from memory import packets, research
from memory.service import MemoryService
from memory.errors import MemoryError


class PacketNavigationTests(unittest.TestCase):
    def test_U05_snapshot_memo_keeps_final_real_source_recheck(self):
        with tempfile.TemporaryDirectory(prefix='SYNTHETIC memo ') as temporary:
            root=Path(temporary)
            source=root/'source.txt'; source.write_text('SYNTHETIC ONLY fixed bytes',encoding='utf-8')
            (root/'retrieval').mkdir()
            (root/'retrieval/sources.json').write_text(json.dumps({'sources':[{'source_id':'SRC-MEMO',
                'path':'source.txt','enabled':True,'sensitivity':'internal'}]}),encoding='utf-8')
            service=MemoryService(root)
            snapshot=packets.Snapshot(service)
            ref={'target_kind':'file','target_id':'SRC-MEMO','revision':None,
                'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'locator':'','relation':'input'}
            with patch.object(service,'_resolve_ref',wraps=service._resolve_ref) as resolve:
                first=snapshot.resolve(ref)
                second=snapshot.resolve({**ref,'locator':'different locator','relation':'background'})
                self.assertEqual(first,second)
                self.assertEqual(resolve.call_count,1)
                source.write_text('SYNTHETIC ONLY changed during assembly',encoding='utf-8')
                with self.assertRaises(MemoryError) as caught:
                    snapshot.recheck()
                self.assertEqual(caught.exception.code,'STALE_BASIS')
                self.assertEqual(resolve.call_count,2)

    def test_U05_fixed_experience_run_claim_file_chain_and_live_invalidations(self):
        with tempfile.TemporaryDirectory(prefix='SYNTHETIC U05 中文 ') as temporary:
            fixture = materialize(Path(temporary) / 'workspace', isolation_root=temporary)
            root = fixture.root
            service = MemoryService(root)
            receipt = service.commit(fixture.request(['MEM-EXP-THERMAL']))
            rid = receipt['record_results'][0]['record_id']
            record = service.inspect('RES-SYN-THERMAL')['records'][rid]
            choice = {'owner_id': 'RES-SYN-THERMAL', 'stage': 'wide'}
            def expand(ref, selection=None, budget=16000):
                result = packets.expand(service, [ref], selection or choice, budget)
                self.assertEqual(result['manifest']['budget']['used'], len(result['context_text']))
                self.assertLessEqual(len(result['context_text']), budget)
                return result
            def navigate(packet, target):
                options = packet['manifest']['navigation_refs']
                matches = [ref for ref in options if ref['target_id'] == target]
                self.assertEqual(len(matches), 1, options)
                ref = matches[0]
                self.assertEqual(set(ref), {'target_kind', 'target_id', 'revision', 'sha256', 'relation', 'locator'})
                self.assertEqual(ref['locator'], '')  # No free body text outside budget.
                return ref
            first = expand(research.fixed_ref(record))
            self.assertIn(record['payload']['prohibited'][0], first['context_text'])
            self.assertEqual(first['manifest']['source_refs'][0]['target_id'], rid)
            self.assertNotIn(rid, [ref['target_id'] for ref in first['manifest']['navigation_refs']])
            run_ref = navigate(first, 'RUN-SYN-THERMAL')
            self.assertEqual(run_ref['sha256'], record['sources'][0]['sha256'])
            second = expand(run_ref)
            claim_ref = navigate(second, 'CLM-SYN-THERMAL')
            self.assertEqual(claim_ref['target_kind'], 'claim')
            third = expand(claim_ref)
            file_ref = navigate(third, 'SRC-SYN-THERMAL')
            self.assertEqual(file_ref['sha256'], fixture.sources['SRC-SYN-THERMAL']['sha256'])
            fourth = expand(file_ref)
            original_path = root / fixture.sources['SRC-SYN-THERMAL']['path']
            original = original_path.read_bytes()
            self.assertIn(packets.normalize_context_text(original.decode('utf-8-sig')), fourth['context_text'])
            self.assertIn(fixture.sources['SRC-SYN-THERMAL']['path'], fourth['context_text'])
            self.assertEqual(fourth['manifest']['navigation_refs'], [])
            # Omitted bodies cannot expose their references as a budget bypass.
            tiny = expand(research.fixed_ref(record), budget=0)
            self.assertEqual(tiny['context_text'], '')
            self.assertEqual(tiny['manifest']['navigation_refs'], [])
            # A source change invalidates the exact previous link; neither a
            # fresh navigation nor browser-back expansion upgrades its hash.
            original_path.write_bytes(original + b'\nSYNTHETIC SOURCE CHANGED')
            old_source = expand(file_ref)
            self.assertEqual(old_source['context_text'], '')
            self.assertIn({'target_id': 'SRC-SYN-THERMAL', 'code': 'STALE_BASIS'}, old_source['manifest']['missing'])
            back = expand(claim_ref)
            self.assertNotIn('SRC-SYN-THERMAL', [ref['target_id'] for ref in back['manifest']['navigation_refs']])
            self.assertTrue(any(row['target_id'] == 'SRC-SYN-THERMAL' and row['code'] == 'STALE_BASIS' for row in back['manifest']['missing']))
            original_path.write_bytes(original)
            denied_choice = {**choice, 'exclude_ids': ['SRC-SYN-THERMAL']}
            self.assertEqual(expand(run_ref, denied_choice)['context_text'], '')
            self.assertEqual(expand(research.fixed_ref(record), denied_choice)['context_text'], '')
            denied_navigation = expand(claim_ref, denied_choice)
            self.assertEqual(denied_navigation['context_text'], '')
            self.assertNotIn('SRC-SYN-THERMAL', [ref['target_id'] for ref in denied_navigation['manifest']['navigation_refs']])
            # An explicit excluded file is rejected before its read/hash entry.
            actual_file = service._file
            def forbid_file(ref):
                if ref['target_id'] == 'SRC-SYN-THERMAL':
                    raise AssertionError('excluded source resolver must not run')
                return actual_file(ref)
            with patch.object(service, '_file', side_effect=forbid_file):
                self.assertEqual(expand(file_ref, denied_choice)['context_text'], '')
            registry_path = root / 'retrieval/sources.json'
            registry = json.loads(registry_path.read_text(encoding='utf-8'))
            for source in registry['sources']:
                if source['source_id'] == 'SRC-SYN-THERMAL':
                    source['enabled'] = False
            registry_path.write_text(json.dumps(registry), encoding='utf-8')
            revoked = expand(claim_ref)
            self.assertEqual(revoked['context_text'], '')
            self.assertNotIn('SRC-SYN-THERMAL', [ref['target_id'] for ref in revoked['manifest']['navigation_refs']])
            self.assertTrue(any(row['code'] == 'ACCESS_DENIED' for row in revoked['manifest']['missing']))
            self.assertEqual(expand(file_ref)['context_text'], '')
            self.assertEqual(service.inspect('RES-SYN-THERMAL')['head']['commit_id'], receipt['commit_id'])


if __name__ == '__main__':
    unittest.main()
