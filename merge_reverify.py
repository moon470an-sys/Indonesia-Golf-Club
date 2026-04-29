"""Apply re-verification results: update coords and status. Preserve existing
closed_permanent flags (Bali National / Bali Beach / Nirwana) which were
already corrected before re-verification ran."""
import json
from pathlib import Path

ROOT = Path(__file__).parent
SRC_DIR = ROOT.parent / "golf_data"
DST = ROOT / "data" / "golf_courses.json"

REVERIFY_FILES = [
    "reverify_jabodetabek.json",
    "reverify_java.json",
    "reverify_bali.json",
    "reverify_outer.json",
]

# Already marked closed_permanent before re-verify; do NOT downgrade
PROTECT_PERMANENT = {"bali-national", "bali-beach-sanur", "nirwana-bali"}


def extract(doc):
    if isinstance(doc, list):
        return doc
    for k in ("courses", "entries", "results", "data"):
        if k in doc and isinstance(doc[k], list):
            return doc[k]
    return []


# Load reverify entries by id
rv_by_id = {}
for fname in REVERIFY_FILES:
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
            rv_by_id[cid] = e

print(f"\nTotal reverify records: {len(rv_by_id)}")

# Load master
master = json.loads(DST.read_text(encoding="utf-8"))

coord_updated = 0
status_updated = 0
for course in master["courses"]:
    cid = course["id"]
    rv = rv_by_id.get(cid)
    if not rv:
        continue

    # --- Update coordinates if verified ---
    new_lat = rv.get("verified_lat")
    new_lng = rv.get("verified_lng")
    if new_lat is not None and new_lng is not None:
        course["lat"] = new_lat
        course["lng"] = new_lng
        course.pop("coord_approximate", None)  # remove fallback flag
        coord_updated += 1

    # --- Update status (but protect permanent closures) ---
    if cid in PROTECT_PERMANENT:
        # Keep existing closed_permanent flag, just refresh evidence date
        if "operating_status" in course:
            course["operating_status"]["last_verified"] = "2026-04-29"
        continue

    new_status = rv.get("status", "uncertain")
    course["operating_status"] = {
        "status": new_status,
        "confidence": rv.get("confidence"),
        "evidence": rv.get("evidence", []),
        "closure_reason": rv.get("closure_reason"),
        "reopened_as": rv.get("reopened_as"),
        "coord_notes": rv.get("coord_notes"),
        "last_verified": rv.get("last_verified", "2026-04-29"),
    }
    status_updated += 1

# Status counts
from collections import Counter
counts = Counter(c.get("operating_status", {}).get("status", "?") for c in master["courses"])
print(f"\nFinal status distribution ({len(master['courses'])} total):")
for s, n in counts.most_common():
    print(f"  {s}: {n}")

print(f"\nCoord updates: {coord_updated}")
print(f"Status updates: {status_updated}")

# Print non-operating list
print("\nClosed permanent:")
for c in master["courses"]:
    if c.get("operating_status", {}).get("status") == "closed_permanent":
        print(f"  - {c['name_en']} ({c['region']})")
print("\nClosed temporary:")
for c in master["courses"]:
    if c.get("operating_status", {}).get("status") == "closed_temporary":
        print(f"  - {c['name_en']} ({c['region']})")
print("\nUncertain:")
for c in master["courses"]:
    if c.get("operating_status", {}).get("status") == "uncertain":
        print(f"  - {c['name_en']} ({c['region']})")

master["metadata"]["last_updated"] = "2026-04-29"
master["metadata"]["coordinates_reverified"] = "2026-04-29 (Google Maps satellite verified)"
DST.write_text(json.dumps(master, ensure_ascii=False, indent=2), encoding="utf-8")
print("\nSaved.")
