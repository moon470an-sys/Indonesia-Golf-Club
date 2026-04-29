"""Merge membership data from 4 region files into master JSON."""
import json
from pathlib import Path

ROOT = Path(__file__).parent
SRC_DIR = ROOT.parent / "golf_data"
DST = ROOT / "data" / "golf_courses.json"

FILES = [
    "membership_jabodetabek.json",
    "membership_java.json",
    "membership_bali.json",
    "membership_outer.json",
]


def extract(doc):
    if isinstance(doc, list):
        return doc
    for k in ("courses", "entries", "results", "data", "membership", "memberships"):
        if k in doc and isinstance(doc[k], list):
            return doc[k]
    return []


by_id = {}
for fname in FILES:
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
            by_id[cid] = e.get("membership") or e

print(f"\nTotal records: {len(by_id)}")

master = json.loads(DST.read_text(encoding="utf-8"))

attached = priced = 0
for course in master["courses"]:
    cid = course["id"]
    m = by_id.get(cid)
    if not m:
        continue
    course["membership"] = m
    attached += 1
    cats = m.get("categories") or []
    has_price = any(
        (c.get("initiation_fee", {}) or {}).get("amount") is not None
        or (c.get("annual_fee", {}) or {}).get("amount") is not None
        or (c.get("monthly_fee", {}) or {}).get("amount") is not None
        for c in cats if isinstance(c, dict)
    )
    if has_price:
        priced += 1

DST.write_text(json.dumps(master, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\nAttached membership data to: {attached}/{len(master['courses'])}")
print(f"Courses with at least one priced category: {priced}")

# Show priced summary
print("\nCourses with disclosed pricing:")
for c in master["courses"]:
    m = c.get("membership") or {}
    cats = m.get("categories") or []
    if not isinstance(cats, list):
        continue
    priced_cats = []
    for cat in cats:
        if not isinstance(cat, dict):
            continue
        init = (cat.get("initiation_fee") or {}).get("amount")
        ann = (cat.get("annual_fee") or {}).get("amount")
        if init or ann:
            priced_cats.append(cat.get("name"))
    if priced_cats:
        print(f"  - {c['name_en']}: {len(priced_cats)} priced tier(s) — {priced_cats[:3]}")
