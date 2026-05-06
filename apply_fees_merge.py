"""apply_fees_merge.py — Merge fees_2026_05 patches from agent results.

Reads data/agent_input/fees_chunk_*_result.json and overwrites the
fees_2026_05 field for each matching course in data/golf_courses.json.

Backs up the file before writing. Skips IDs not found in main data.
Skips courses that already have a non-null fees_2026_05 unless --force.

Run:  python apply_fees_merge.py [--dry-run] [--force]
"""
import json
import sys
import glob
import shutil
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data' / 'golf_courses.json'


def main():
    dry = '--dry-run' in sys.argv
    force = '--force' in sys.argv

    doc = json.loads(DATA.read_text(encoding='utf-8'))
    by_id = {c['id']: c for c in doc['courses']}

    applied = []
    skipped_no_match = []
    skipped_existing = []
    bad = []

    pattern = str(ROOT / 'data' / 'agent_input' / 'fees_chunk_*_result.json')
    files = sorted(glob.glob(pattern))
    if not files:
        print(f'No result files matched: {pattern}')
        sys.exit(2)

    for f in files:
        try:
            data = json.loads(Path(f).read_text(encoding='utf-8'))
        except Exception as e:
            print(f'  [skip-file] {f}: {e}')
            continue
        if not isinstance(data, list):
            print(f'  [skip-file] {f}: top-level not a list')
            continue
        for entry in data:
            cid = entry.get('id')
            fees = entry.get('fees_2026_05')
            if not cid or not isinstance(fees, dict):
                bad.append((Path(f).name, cid, 'missing id or fees_2026_05'))
                continue
            course = by_id.get(cid)
            if not course:
                skipped_no_match.append(cid)
                continue
            if course.get('fees_2026_05') and not force:
                skipped_existing.append(cid)
                continue
            course['fees_2026_05'] = fees
            applied.append((cid, Path(f).name))

    print(f'Applied:           {len(applied)}')
    for cid, src in applied:
        print(f'  + {cid}  ({src})')
    if skipped_no_match:
        print(f'Skipped no-match: {len(skipped_no_match)}')
        for cid in skipped_no_match:
            print(f'  - {cid}')
    if skipped_existing:
        print(f'Skipped existing fees (use --force to overwrite): {len(skipped_existing)}')
        for cid in skipped_existing:
            print(f'  - {cid}')
    if bad:
        print(f'Bad entries: {len(bad)}')
        for src, cid, reason in bad:
            print(f'  ! {src} {cid}: {reason}')

    if dry:
        print('\n[dry-run] no files written.')
        return
    if not applied:
        print('Nothing to apply.')
        return

    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup = DATA.parent / f'golf_courses.backup.{ts}.json'
    shutil.copy2(DATA, backup)
    print(f'\n[backup] {backup.name}')

    doc.setdefault('metadata', {})
    doc['metadata']['last_fees_merge'] = ts

    DATA.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'[write]  {DATA.name}')


if __name__ == '__main__':
    main()
