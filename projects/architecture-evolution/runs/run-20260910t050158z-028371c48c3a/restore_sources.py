"""Repair only this synthetic example's missing source registrations.

Run without arguments to preview. --apply appends verified registrations and
saves the original registry. --rollback restores it only if no later edits
occurred. Fixed records and historical Run metadata are never rewritten.
"""
import argparse
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
EXAMPLE = ROOT / 'research/floating-point-summation'
REGISTRY = ROOT / 'retrieval/sources.json'
BACKUP = HERE / 'sources-before.json'
RECEIPT = HERE / 'sources-repair.json'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--rollback', action='store_true')
    args = parser.parse_args()
    before = REGISTRY.read_bytes()
    if args.rollback:
        receipt = json.loads(RECEIPT.read_text(encoding='utf-8'))
        if digest(before) != receipt['after_sha256']:
            raise ValueError('Later registry edits exist; rollback refused')
        saved = BACKUP.read_bytes()
        if digest(saved) != receipt['before_sha256']:
            raise ValueError('Backup changed; rollback refused')
        if args.apply:
            REGISTRY.write_bytes(saved)
        print(json.dumps({'rollback': True, 'applied': args.apply}))
        return
    registry = json.loads(before.decode('utf-8-sig'))
    fixed = json.loads((EXAMPLE / 'fixtures/restore-manifest.json').read_text(encoding='utf-8-sig'))
    by_target = {item['target']: item for item in fixed['entries']}
    required = json.loads((EXAMPLE / 'fixtures/sources.json').read_text(encoding='utf-8-sig'))['sources']
    known = {item.get('source_id'): item for item in registry['sources']}
    added = []
    for original in required:
        # Resolve only an explicitly frozen file. This does not discover or
        # authorize unrelated workspace files, and requires exact old bytes.
        item = dict(original)
        entry = by_target[item['path']]
        path = (EXAMPLE / entry['source']).resolve()
        if not path.is_relative_to(EXAMPLE.resolve()):
            raise ValueError('Source escapes selected example')
        actual = digest(path.read_bytes())
        if actual != entry['sha256']:
            raise ValueError('Frozen input changed: ' + entry['source'])
        item['path'] = path.relative_to(ROOT).as_posix()
        item['sha256'] = actual
        if item['source_id'] in known:
            if known[item['source_id']]['path'] != item['path']:
                raise ValueError('Existing source conflicts: ' + item['source_id'])
            continue
        added.append(item)
    registry['sources'].extend(added)
    after = (json.dumps(registry, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    receipt = {'applied': args.apply, 'added': added, 'before_sha256': digest(before), 'after_sha256': digest(after)}
    if args.apply and added:
        if BACKUP.exists() or RECEIPT.exists():
            raise ValueError('Recovery files already exist')
        BACKUP.write_bytes(before)
        RECEIPT.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
        REGISTRY.write_bytes(after)
    print(json.dumps(receipt, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, KeyError, OSError) as exc:
        raise SystemExit(str(exc))
