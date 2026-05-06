"""apply_finance_patches.py — Apply verified financial corrections from
agent JSON outputs to data/golf_courses.json.

Each chunk_N_result.json contains an `issues` array with
  {id, field, current_value, correct_value, evidence_url, note}

This script:
  1. Backs up data/golf_courses.json with timestamp
  2. Applies each issue: set financials[field] = correct_value
  3. Records the evidence_url + note in a parallel
     financials.verification_log[] array (additive — does not delete)
  4. Stamps last_verified to today (2026-05-06)
  5. Reports counts (changed, skipped, missing)

Run:  python apply_finance_patches.py [--dry-run]
"""
import json, sys, shutil, glob
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data' / 'golf_courses.json'
TODAY = '2026-05-06'

def main():
    dry = '--dry-run' in sys.argv
    doc = json.loads(DATA.read_text(encoding='utf-8'))
    by_id = {c['id']: c for c in doc['courses']}

    patches = []
    for f in sorted(glob.glob(str(ROOT / 'data' / 'agent_input' / 'chunk_*_result.json'))):
        try:
            data = json.loads(Path(f).read_text(encoding='utf-8'))
        except Exception as e:
            print(f'  [skip] {f}: {e}'); continue
        for issue in (data.get('issues') or []):
            patches.append((f.split('/')[-1], issue))

    print(f'Loaded {len(patches)} patches from {len(set(p[0] for p in patches))} result files')

    changed_courses = set()
    field_changes = {}
    missing_courses = []

    for source_file, issue in patches:
        cid = issue.get('id'); field = issue.get('field')
        new_val = issue.get('correct_value')
        if not cid or not field:
            continue
        course = by_id.get(cid)
        if not course:
            missing_courses.append(cid); continue
        fin = course.setdefault('financials', {})

        # Apply value
        old_val = fin.get(field)
        fin[field] = new_val

        # Append to verification_log
        log = fin.setdefault('verification_log', [])
        log.append({
            'verified_at': TODAY,
            'field': field,
            'old_value': old_val,
            'new_value': new_val,
            'evidence_url': issue.get('evidence_url'),
            'note': issue.get('note'),
            'source_chunk': source_file,
        })

        # Stamp last_verified
        fin['last_verified'] = TODAY

        changed_courses.add(cid)
        field_changes[field] = field_changes.get(field, 0) + 1

    print()
    print(f'Courses touched: {len(changed_courses)}')
    print(f'Field updates: {sum(field_changes.values())}')
    for f, n in sorted(field_changes.items(), key=lambda x: -x[1]):
        print(f'  {f}: {n}')
    if missing_courses:
        print(f'Missing course IDs (skipped): {len(missing_courses)}')
        for m in missing_courses[:10]:
            print(f'  {m}')

    if dry:
        print('\n[dry-run] no files written.')
        return

    # Backup + write
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup = DATA.parent / f'golf_courses.backup.{ts}.json'
    shutil.copy2(DATA, backup)
    print(f'\n[backup] {backup.name}')
    DATA.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'[write]  {DATA.name}')

if __name__ == '__main__':
    main()
