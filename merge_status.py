"""Merge operating status into golf_courses.json and remove duplicates."""
import json
from pathlib import Path

ROOT = Path(__file__).parent
SRC_DIR = ROOT.parent / "golf_data"
DST = ROOT / "data" / "golf_courses.json"

STATUS_FILES = [
    "status_jabodetabek.json",
    "status_java.json",
    "status_bali.json",
    "status_outer.json",
]


def extract(doc):
    if isinstance(doc, list):
        return doc
    for k in ("courses", "entries", "status", "results", "data"):
        if k in doc and isinstance(doc[k], list):
            return doc[k]
    return []


# Load status by id
status_by_id = {}
for fname in STATUS_FILES:
    src = SRC_DIR / fname
    if not src.exists():
        print(f"!! missing: {fname}")
        continue
    doc = json.loads(src.read_text(encoding="utf-8"))
    entries = extract(doc)
    print(f"{fname}: {len(entries)} entries")
    for e in entries:
        cid = e.get("id")
        if cid:
            status_by_id[cid] = {
                "status": e.get("status", "uncertain"),
                "confidence": e.get("confidence"),
                "evidence": e.get("evidence", []),
                "closure_reason": e.get("closure_reason"),
                "reopened_as": e.get("reopened_as"),
                "last_verified": e.get("last_verified"),
            }

print(f"\nTotal status records: {len(status_by_id)}")

# Load master
master = json.loads(DST.read_text(encoding="utf-8"))

# Remove confirmed duplicates
DUPLICATE_REMOVE = {"bandung-giri-gahana"}  # = jatinangor-national
before = len(master["courses"])
master["courses"] = [c for c in master["courses"] if c["id"] not in DUPLICATE_REMOVE]
removed = before - len(master["courses"])
print(f"\nRemoved {removed} duplicate(s): {DUPLICATE_REMOVE}")

# Merge status into each course
matched = 0
for course in master["courses"]:
    cid = course["id"]
    if cid in status_by_id:
        course["operating_status"] = status_by_id[cid]
        matched += 1

# Status counts
from collections import Counter
counts = Counter(c.get("operating_status", {}).get("status", "unknown") for c in master["courses"])
print(f"\nStatus distribution after merge ({len(master['courses'])} total):")
for s, n in counts.most_common():
    print(f"  {s}: {n}")

master["metadata"]["total_courses"] = len(master["courses"])
master["metadata"]["status_verified"] = "2026-04-29"

DST.write_text(json.dumps(master, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\nMatched status to {matched}/{len(master['courses'])} courses.")
