"""L0 projection verifies real declarations, fixed bytes and read-only boundaries."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from unittest.mock import patch
import unittest

import test_memory_research as fixture
from memory import raw_materials, render
from memory.api import dispatch
from memory.errors import MemoryError


class RawMaterialsTests(unittest.TestCase):
    setUp = fixture.ResearchTests.setUp
    put = fixture.ResearchTests.put
    operation = fixture.ResearchTests.operation
    request = fixture.ResearchTests.request
    save = fixture.ResearchTests.save

    def seed(self):
        self.path = self.put('runs/attempt/输入 空格.txt', '原始细节\n' * 80)
        # Fix the synthetic input bytes across Windows/POSIX; preview preserves
        # original line endings rather than silently normalizing the evidence.
        self.path.write_bytes(('原始细节\n' * 80).encode('utf-8'))
        self.digest = hashlib.sha256(self.path.read_bytes()).hexdigest()
        self.entry = {'path': self.path.relative_to(self.root).as_posix(), 'sha256': self.digest}
        self.native = {'run_id': 'RUN-R', 'owner_id': 'RES-R', 'status': 'succeeded', 'claims': [],
                       'inputs': [deepcopy(self.entry)], 'artifacts': [deepcopy(self.entry)]}
        self.put('runs/attempt/run.json', self.native)

    def rows(self, owner='RES-R'):
        return dispatch(self.service, 'raw-materials', {'owner_id': owner})

    def original(self, rows=None):
        return next(item for item in (rows or self.rows())['items'] if item['sha256'] == self.digest)

    def read(self, row, **values):
        return dispatch(self.service, 'raw-material', {'owner_id': 'RES-R', 'material_id': row['material_id'], **values})

    def test_l01_native_run_without_source_and_research_deduplicate_usage(self):
        self.seed()
        other = {**self.native, 'run_id': 'RUN-SECOND'}
        self.put('research/topic/runs/second/run.json', other)
        self.put('runs/unrelated/run.json', {**self.native, 'run_id': 'RUN-OTHER', 'owner_id': 'RES-OTHER'})
        result = self.rows()
        row = self.original(result)
        self.assertEqual(len([item for item in result['items'] if item['sha256'] == self.digest]), 1)
        self.assertEqual({origin['run_id'] for origin in row['origins']}, {'RUN-R', 'RUN-SECOND'})
        self.assertFalse(any('RUN-OTHER' in str(item) for item in result['items']))
        self.assertEqual(len(self.rows('RUN-R')['items']), 2)  # original + current Run metadata
        self.assertFalse(self.service.inspect('RUN-R')['records'])
        self.assertEqual(self.read(row, max_chars=7)['text'], '原始细节\n原始')
        self.assertTrue(self.read(row, max_chars=7)['truncated'])

    def test_l02_source_alias_merges_with_native_fixed_file(self):
        self.seed()
        self.put('retrieval/sources.json', {'sources': [
            {'source_id': 'SRC-A', 'path': self.entry['path'], 'enabled': True},
            {'source_id': 'SRC-B', 'path': self.entry['path'], 'enabled': True}]})
        for identity in ('SRC-A', 'SRC-B'):
            self.save(self.operation('source', {'source_ref': {'target_kind': 'file', 'target_id': identity,
                'revision': None, 'sha256': self.digest, 'locator': '', 'relation': 'input'},
                'acquisition': 'original_link', 'completeness': 'complete', 'acquired_at': None}))
        row = self.original()
        self.assertEqual({ref['target_id'] for ref in row['source_refs']}, {'SRC-A', 'SRC-B'})
        self.assertEqual(len([origin for origin in row['origins'] if origin['role'] == 'source']), 2)
        exported = json.loads(render.export(self.service, {'owner_id': 'RES-R', 'include_raw_materials': True, 'format': 'json'})['content'])
        self.assertEqual(exported['records'], [])
        self.assertEqual(len(exported['manifest']['raw_materials']['items']), 2)
        self.assertNotIn('原始细节', json.dumps(exported, ensure_ascii=False))

    def test_l03_fixed_versions_do_not_merge_or_return_changed_content(self):
        self.seed()
        old = self.original()
        self.path.write_text('新的原件', encoding='utf-8')
        with self.assertRaises(MemoryError) as caught:
            self.read(old)
        self.assertEqual(caught.exception.code, 'STALE_BASIS')
        new_digest = hashlib.sha256(self.path.read_bytes()).hexdigest()
        self.native['artifacts'] = [{**self.entry, 'sha256': new_digest}]
        self.put('runs/attempt/run.json', self.native)
        versions = [item for item in self.rows()['items'] if item['path'] == self.entry['path']]
        self.assertEqual({item['sha256'] for item in versions}, {self.digest, new_digest})
        self.assertEqual(self.read(next(item for item in versions if item['sha256'] == new_digest))['text'], '新的原件')

    def test_l04_revoked_alias_restricted_owner_and_traversal_are_not_bypassed(self):
        self.seed()
        old = self.original()
        self.put('retrieval/sources.json', {'sources': [{'source_id': 'SRC-BLOCK', 'path': self.entry['path'], 'enabled': False}]})
        self.assertFalse(any(item['sha256'] == self.digest for item in self.rows()['items']))
        with self.assertRaises(MemoryError):
            self.read(old)
        self.put('retrieval/sources.json', {'sources': []})
        secret = self.put('research/secret/secret.txt', '不得读取')
        self.put('research/secret/research.json', {'research_id': 'RES-SECRET', 'title': 'restricted', 'sensitivity': 'restricted'})
        self.native['artifacts'] = [{'path': '../outside.txt', 'sha256': 'a' * 64},
            {'path': secret.relative_to(self.root).as_posix(), 'sha256': hashlib.sha256(secret.read_bytes()).hexdigest()}]
        self.put('runs/attempt/run.json', self.native)
        result = self.rows()
        self.assertNotIn('secret.txt', str(result['items']))
        self.assertEqual({gap['code'] for gap in result['missing']}, {'UNSAFE_PATH', 'ACCESS_DENIED'})
        self.native['sensitivity'] = 'restricted'
        self.put('runs/attempt/run.json', self.native)
        with self.assertRaises(MemoryError):
            self.rows('RUN-R')

    def test_l05_missing_hash_missing_file_and_client_identity_fail_closed(self):
        self.seed()
        self.native['inputs'][0].pop('sha256')
        self.native['artifacts'] = [{'path': 'runs/attempt/不存在.txt', 'sha256': 'a' * 64}]
        self.put('runs/attempt/run.json', self.native)
        result = self.rows()
        self.assertEqual({item['status'] for item in result['items']}, {'registered', 'missing', 'unversioned'})
        for item in result['items']:
            if item['status'] != 'registered':
                with self.assertRaises(MemoryError):
                    self.read(item)
        with self.assertRaises(MemoryError):
            self.read({'material_id': '../secret'})
        with self.assertRaises(MemoryError):
            self.read(result['items'][0], max_chars=0)

    def test_l06_listing_does_not_open_original_bodies_or_create_memory(self):
        self.seed()
        before = {path.relative_to(self.root).as_posix(): path.read_bytes() for path in self.root.rglob('*') if path.is_file()}
        actual_open = Path.open
        def guarded(path, *args, **kwargs):
            if path == self.path:
                raise AssertionError('listing opened the original body')
            return actual_open(path, *args, **kwargs)
        with patch.object(Path, 'open', guarded):
            result = self.rows()
        self.assertEqual(result['canonical_writes'], 0)
        self.assertFalse(result['content_loaded'])
        self.assertEqual(before, {path.relative_to(self.root).as_posix(): path.read_bytes() for path in self.root.rglob('*') if path.is_file()})
