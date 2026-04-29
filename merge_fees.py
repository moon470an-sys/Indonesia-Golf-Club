"""Merge 4 fee JSON files into site/data/golf_courses.json."""
import json
from pathlib import Path

ROOT = Path(__file__).parent
SRC_DIR = ROOT.parent / "golf_data"
DST = ROOT / "data" / "golf_courses.json"

FEE_FILES = [
    "fees_jabodetabek.json",
    "fees_java.json",
    "fees_bali_resort.json",
    "fees_outer.json",
]


def extract_entries(doc):
    """Each agent saved either a JSON array or a dict with 'fees'/'courses' key."""
    if isinstance(doc, list):
        return doc
    for k in ("fees", "courses", "data", "entries"):
        if k in doc and isinstance(doc[k], list):
            return doc[k]
    return []


# Load all fees by id
fees_by_id = {}
for fname in FEE_FILES:
    src = SRC_DIR / fname
    if not src.exists():
        print(f"!! missing: {fname}")
        continue
    doc = json.loads(src.read_text(encoding="utf-8"))
    entries = extract_entries(doc)
    print(f"{fname}: {len(entries)} entries")
    for e in entries:
        cid = e.get("id")
        if not cid:
            continue
        # Each entry may have key 'fees_2026_05' or be the fee object itself
        if "fees_2026_05" in e:
            fees_by_id[cid] = e["fees_2026_05"]
        else:
            # Build a fees object from the entry minus id
            fees_by_id[cid] = {k: v for k, v in e.items() if k != "id"}

print(f"\nTotal fee records: {len(fees_by_id)}")

# Merge into master
master = json.loads(DST.read_text(encoding="utf-8"))
matched = 0
for course in master["courses"]:
    cid = course["id"]
    if cid in fees_by_id:
        course["fees_2026_05"] = fees_by_id[cid]
        matched += 1

master["metadata"]["fees_added"] = "2026-04-29"
master["metadata"]["fees_matched"] = matched

DST.write_text(json.dumps(master, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\nMatched fees to {matched}/{len(master['courses'])} courses.")

unmatched_fees = [cid for cid in fees_by_id if cid not in {c['id'] for c in master['courses']}]
if unmatched_fees:
    print(f"\nFee entries with no matching course (id mismatch?):")
    for cid in unmatched_fees:
        print(f"  - {cid}")
