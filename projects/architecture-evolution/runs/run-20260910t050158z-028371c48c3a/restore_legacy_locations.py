"""Preview/apply verified legacy Run locations; preserve canonical bytes."""
import argparse
import hashlib
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from restore_sources import ROOT, HERE, EXAMPLE, REGISTRY, digest

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--apply', action='store_true')
parser.add_argument('--rollback', action='store_true', help='核对本次登记指纹后恢复；默认仍为预览')
args = parser.parse_args()
before = REGISTRY.read_bytes()
if args.rollback:
    receipt = json.loads((HERE / 'locations-repair.json').read_text(encoding='utf-8'))
    backup = (HERE / 'sources-before-locations.json').read_bytes()
    if digest(before) != receipt['after_sha256'] or digest(backup) != receipt['before_sha256']:
        raise SystemExit('Later registry edits or changed backup; rollback refused')
    if args.apply:
        REGISTRY.write_bytes(backup)
    print(json.dumps({'rollback': True, 'applied': args.apply}))
    raise SystemExit(0)
registry = json.loads(before.decode('utf-8-sig'))
entries = json.loads((EXAMPLE / 'fixtures/restore-manifest.json').read_text(encoding='utf-8-sig'))['entries']
changes = []
for frozen in entries:
    old = frozen['target']
    if not old.startswith('runs/run-'):
        continue
    current = EXAMPLE / frozen['source']
    if digest(current.read_bytes()) != frozen['sha256']:
        raise SystemExit('Frozen file changed: ' + frozen['source'])
    relative = current.relative_to(ROOT).as_posix()
    matching = [s for s in registry['sources'] if s['path'] == relative]
    if len(matching) > 1:
        raise SystemExit('Ambiguous registered destination: ' + relative)
    if matching:
        item = matching[0]
    else:
        item = {'source_id': 'SRC-SUMMATION-RELOCATED-' + hashlib.sha256(old.encode()).hexdigest()[:16],
                'path': relative, 'enabled': True, 'sensitivity': 'internal',
                'memory_level': 'L0', 'discovery': 'trace_only'}
        registry['sources'].append(item)
    item.update(relocated_from=old, sha256=frozen['sha256'])
    changes.append(item.copy())
after = (json.dumps(registry, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
receipt = {'applied': args.apply, 'changes': changes, 'before_sha256': digest(before), 'after_sha256': digest(after)}
if args.apply:
    backup = HERE / 'sources-before-locations.json'
    if backup.exists():
        raise SystemExit('Backup already exists; do not repeat application')
    backup.write_bytes(before)
    (HERE / 'locations-repair.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
    REGISTRY.write_bytes(after)
print(json.dumps(receipt, ensure_ascii=False, indent=2))
