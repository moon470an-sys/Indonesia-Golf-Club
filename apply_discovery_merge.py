"""apply_discovery_merge.py — Add newly discovered courses to golf_courses.json.

Reads data/agent_input/discover_*_result.json (one per region) and appends
new course objects to data/golf_courses.json. Skips IDs already present.
Backs up the file before writing. Prints a summary.

Run:  python apply_discovery_merge.py [--dry-run]
"""
import json, sys, glob, shutil
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data' / 'golf_courses.json'

def main():
    dry = '--dry-run' in sys.argv
    doc = json.loads(DATA.read_text(encoding='utf-8'))
    existing_ids = {c['id'] for c in doc['courses']}

    additions = []
    skipped = []
    by_region = {}

    for f in sorted(glob.glob(str(ROOT / 'data' / 'agent_input' / 'discover_*_result.json'))):
        try:
            data = json.loads(Path(f).read_text(encoding='utf-8'))
        except Exception as e:
            print(f'  [skip] {f}: {e}'); continue
        region_key = data.get('region', Path(f).stem)
        for course in data.get('missing') or []:
            cid = course.get('id')
            if not cid:
                skipped.append(('no-id', course.get('name_en','?'))); continue
            if cid in existing_ids:
                skipped.append(('dup-id', cid)); continue
            additions.append(course)
            existing_ids.add(cid)
            by_region.setdefault(region_key, []).append(cid)

    print(f'New courses to add: {len(additions)}')
    for r, lst in by_region.items():
        print(f'  {r}: {len(lst)} ({", ".join(lst)})')
    if skipped:
        print(f'Skipped: {len(skipped)}')
        for kind, cid in skipped:
            print(f'  [{kind}] {cid}')

    if dry:
        print('\n[dry-run] no files written.')
        return

    if not additions:
        print('Nothing to merge.')
        return

    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup = DATA.parent / f'golf_courses.backup.{ts}.json'
    shutil.copy2(DATA, backup)
    print(f'\n[backup] {backup.name}')

    doc['courses'].extend(additions)
    doc.setdefault('metadata', {})
    doc['metadata']['last_discovery_merge'] = ts
    doc['metadata']['total_courses'] = len(doc['courses'])

    DATA.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'[write]  {DATA.name} (total_courses now {len(doc["courses"])})')

if __name__ == '__main__':
    main()
