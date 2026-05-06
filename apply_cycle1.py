"""Apply cycle-1 reverify proposals (iter0001..iter0025) to golf_courses.json.

Conservative merge strategy:
  - SAFE auto-apply (additive only):
      * new_sources -> append to fees_2026_05.sources (dedup)
      * coords -> update lat/lng if Indonesia bbox sanity-check passes
      * financials.sources_add -> append to financials.sources
      * fees diff entries -> append to fees_2026_05.source_details as candidates
        (this matches the existing crawled-source schema; primary fees in
         fees_2026_05.weekday/weekend/schedule_detailed are NOT overwritten)
      * operating_status -> apply only when `after` maps to canonical
        {operating, closed_temporary, closed_permanent, uncertain}.
        Map agent terms: operational->operating, reopening/reactivating->uncertain
        Only when confidence is medium or high.
  - STAGED (manual review): everything else, written to
    data/staged_review/cycle1_high_risk.json

Updates fees_2026_05.last_verified and operating_status.last_verified to today.
Saves backup at data/golf_courses.backup.cycle1.<ts>.json.
"""

import json
import os
import sys
import glob
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
COURSES_PATH = ROOT / "data" / "golf_courses.json"
PROPOSALS_DIR = ROOT / "data" / "reverify_proposals"
STAGED_DIR = ROOT / "data" / "staged_review"
TODAY = datetime.now(timezone.utc).strftime("%Y-%m-%d")
TS = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
BACKUP_PATH = ROOT / "data" / f"golf_courses.backup.cycle1.{TS}.json"

# Indonesia bbox for coord sanity check
LAT_MIN, LAT_MAX = -11.5, 7.0
LNG_MIN, LNG_MAX = 94.5, 142.0

CANONICAL_STATUSES = {"operating", "closed_temporary", "closed_permanent", "uncertain"}
STATUS_ALIASES = {
    "operational": "operating",
    "reopening": "uncertain",      # transitional → uncertain (curator decides exact when reopened)
    "reactivating": "uncertain",
    "closed": "closed_permanent",
    "permanent_closed": "closed_permanent",
    "permanently_closed": "closed_permanent",
    "temporary_closed": "closed_temporary",
    "temporarily_closed": "closed_temporary",
    "operating": "operating",
    "closed_temporary": "closed_temporary",
    "closed_permanent": "closed_permanent",
    "uncertain": "uncertain",
}


def cycle1_batches():
    paths = sorted(PROPOSALS_DIR.glob("batch_*_iter00*.json"))
    out = []
    for p in paths:
        for i in range(1, 26):
            if f"iter{i:04d}" in p.name:
                out.append(p)
                break
    return out


def is_url(s):
    return isinstance(s, str) and s.strip().startswith(("http://", "https://"))


def append_unique(seq, items):
    """Append items to seq if not already present, returning count added."""
    if not isinstance(seq, list):
        return 0
    existing = set(seq) if all(isinstance(x, str) for x in seq) else None
    added = 0
    for it in items or []:
        if existing is not None:
            if it in existing:
                continue
            seq.append(it)
            existing.add(it)
            added += 1
        else:
            if it not in seq:
                seq.append(it)
                added += 1
    return added


def normalize_status(value):
    if not isinstance(value, str):
        return None
    return STATUS_ALIASES.get(value.strip().lower())


def merge_one(course, diff, no_change_confirmed, course_id, staged_high_risk, stats):
    if not isinstance(course, dict) or not diff:
        return False, []
    changes = []

    def get_dict(parent, key):
        """Get parent[key] as dict, replacing None/missing with empty dict."""
        v = parent.get(key)
        if not isinstance(v, dict):
            v = {}
            parent[key] = v
        return v

    # --- new_sources -> fees_2026_05.sources ---
    ns = diff.get("new_sources")
    if isinstance(ns, list) and ns:
        urls = [u for u in ns if is_url(u)]
        if urls:
            f = get_dict(course, "fees_2026_05")
            sources = f.setdefault("sources", [])
            n = append_unique(sources, urls)
            if n:
                stats["new_sources_added"] += n
                changes.append(f"+{n} sources")

    # --- coords ---
    cd = diff.get("coords")
    if isinstance(cd, dict):
        lat = cd.get("lat") if "lat" in cd else (cd.get("after") or [None, None])[0] if isinstance(cd.get("after"), list) else None
        lng = cd.get("lng") if "lng" in cd else (cd.get("after") or [None, None])[1] if isinstance(cd.get("after"), list) else None
        try:
            lat_f = float(lat) if lat is not None else None
            lng_f = float(lng) if lng is not None else None
        except (TypeError, ValueError):
            lat_f = lng_f = None
        if (lat_f is not None and lng_f is not None
            and LAT_MIN <= lat_f <= LAT_MAX and LNG_MIN <= lng_f <= LNG_MAX):
            old_lat = course.get("lat"); old_lng = course.get("lng")
            # Only update if difference is meaningful (avoid noise)
            if old_lat is None or old_lng is None or abs(old_lat - lat_f) > 0.0005 or abs(old_lng - lng_f) > 0.0005:
                course["lat"] = lat_f
                course["lng"] = lng_f
                course["coord_approximate"] = False
                stats["coords_updated"] += 1
                changes.append("coords")
        else:
            staged_high_risk.append({"id": course_id, "field": "coords", "value": cd, "reason": "out-of-bbox or unparsable"})

    # --- financials additive ---
    fin_diff = diff.get("financials")
    if isinstance(fin_diff, dict):
        applied_fin = False
        fin = get_dict(course, "financials")
        sa = fin_diff.get("sources_add")
        if isinstance(sa, list) and sa:
            urls = [u for u in sa if is_url(u)]
            if urls:
                fin_sources = fin.setdefault("sources", [])
                n = append_unique(fin_sources, urls)
                if n:
                    stats["financials_sources_added"] += n
                    applied_fin = True
        rn = fin_diff.get("recent_news_append")
        if isinstance(rn, str) and rn.strip():
            existing_notes = fin.get("recent_news") or ""
            if rn.strip() not in existing_notes:
                fin["recent_news"] = (existing_notes + ("\n" if existing_notes else "") + rn.strip()).strip()
                applied_fin = True
        # Stage non-additive financial fields
        non_additive_keys = [k for k in fin_diff if k not in ("sources_add", "recent_news_append", "last_verified")]
        if non_additive_keys:
            staged_high_risk.append({"id": course_id, "field": "financials", "value": {k: fin_diff[k] for k in non_additive_keys}, "reason": "non-additive financial field"})
        if applied_fin:
            changes.append("financials")
            stats["financials_updated"] += 1

    # --- fees -> append to source_details ---
    fees_diff = diff.get("fees")
    if isinstance(fees_diff, list) and fees_diff:
        f = get_dict(course, "fees_2026_05")
        sd = f.setdefault("source_details", [])
        existing_keys = {(e.get("slot"), e.get("source_url"), e.get("value_idr")) for e in sd if isinstance(e, dict)}
        added = 0
        for entry in fees_diff:
            if not isinstance(entry, dict):
                continue
            slot = entry.get("slot")
            src = entry.get("source_url") or entry.get("source")
            val = entry.get("value_idr") or entry.get("after_idr")
            key = (slot, src, val)
            if key in existing_keys:
                continue
            sd.append({
                "slot": slot,
                "value_idr": val,
                "publisher": entry.get("publisher"),
                "source_url": src,
                "tier": entry.get("tier"),
                "as_of": entry.get("as_of") or TODAY,
                "notes": entry.get("notes"),
            })
            existing_keys.add(key)
            added += 1
        if added:
            stats["fees_candidates_added"] += added
            changes.append(f"+{added} fee candidates")

    # --- operating_status (canonical only) ---
    os_diff = diff.get("operating_status")
    if isinstance(os_diff, dict):
        after = os_diff.get("after") or os_diff.get("status")
        canonical = normalize_status(after)
        confidence = (os_diff.get("confidence") or "low").lower()
        if canonical in CANONICAL_STATUSES and confidence in ("medium", "high"):
            current_op = get_dict(course, "operating_status")
            current_status = current_op.get("status")
            if current_status != canonical or current_op.get("confidence") != confidence:
                current_op["status"] = canonical
                current_op["confidence"] = confidence
                current_op["last_verified"] = TODAY
                evidence = os_diff.get("evidence")
                if isinstance(evidence, list) and evidence:
                    ev_list = current_op.setdefault("evidence", [])
                    append_unique(ev_list, evidence)
                cr = os_diff.get("closure_reason")
                if cr and isinstance(cr, str):
                    current_op["closure_reason"] = cr
                cn = os_diff.get("coord_notes")
                if cn and isinstance(cn, str):
                    current_op["coord_notes"] = cn
                stats["status_updated"] += 1
                changes.append(f"status->{canonical}")
        else:
            # Stage non-canonical or low-confidence status proposals for review
            staged_high_risk.append({
                "id": course_id, "field": "operating_status",
                "value": os_diff,
                "reason": f"canonical={canonical}, confidence={confidence}"
            })

    # --- membership: stage all non-empty replacements (full replacement is risky) ---
    mem_diff = diff.get("membership")
    if isinstance(mem_diff, dict) and mem_diff:
        # Only auto-apply if it's adding sources/notes to existing membership
        sources = mem_diff.get("sources")
        if isinstance(sources, list) and sources and len(mem_diff) <= 3:
            mem = get_dict(course, "membership")
            mem_sources = mem.setdefault("sources", [])
            urls = [u for u in sources if is_url(u)]
            n = append_unique(mem_sources, urls)
            if n:
                stats["membership_sources_added"] += n
                changes.append(f"+{n} membership sources")
        else:
            staged_high_risk.append({"id": course_id, "field": "membership", "value": mem_diff, "reason": "complex membership change"})

    # --- bump fees_2026_05.last_verified if anything was added/changed ---
    if changes:
        f = get_dict(course, "fees_2026_05")
        f["last_verified"] = TODAY

    return bool(changes), changes


def main():
    if not COURSES_PATH.exists():
        print("ERROR: golf_courses.json not found", file=sys.stderr)
        sys.exit(1)

    with open(COURSES_PATH, "r", encoding="utf-8") as fh:
        doc = json.load(fh)

    # Backup
    BACKUP_PATH.write_bytes(COURSES_PATH.read_bytes())
    print(f"backup -> {BACKUP_PATH}")

    courses = doc.get("courses", [])
    by_id = {c.get("id"): c for c in courses if c.get("id")}
    if not by_id:
        print("ERROR: no courses found", file=sys.stderr)
        sys.exit(1)

    batches = cycle1_batches()
    print(f"cycle1 batches: {len(batches)}")

    staged_high_risk = []
    stats = {
        "batches_processed": 0,
        "courses_touched": 0,
        "new_sources_added": 0,
        "coords_updated": 0,
        "financials_updated": 0,
        "financials_sources_added": 0,
        "fees_candidates_added": 0,
        "status_updated": 0,
        "membership_sources_added": 0,
    }
    touched_ids = set()
    per_course_log = []

    for bp in batches:
        with open(bp, "r", encoding="utf-8") as fh:
            b = json.load(fh)
        for r in b.get("reports", []):
            cid = r.get("id")
            if cid not in by_id:
                continue
            diff = r.get("diff") or {}
            nc = r.get("no_change_confirmed") or []
            changed, changes = merge_one(by_id[cid], diff, nc, cid, staged_high_risk, stats)
            if changed:
                touched_ids.add(cid)
                per_course_log.append((cid, changes))
        stats["batches_processed"] += 1

    stats["courses_touched"] = len(touched_ids)

    # Validate course count unchanged
    if len(doc.get("courses", [])) != len(courses):
        print("ERROR: course count changed during merge", file=sys.stderr)
        sys.exit(2)

    # Save merged JSON
    with open(COURSES_PATH, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=2)

    # Save staged-review file
    STAGED_DIR.mkdir(parents=True, exist_ok=True)
    staged_path = STAGED_DIR / f"cycle1_high_risk_{TS}.json"
    with open(staged_path, "w", encoding="utf-8") as fh:
        json.dump({"created_at": TODAY, "items": staged_high_risk}, fh, ensure_ascii=False, indent=2)

    # Print summary
    print()
    print("=== APPLY CYCLE 1 SUMMARY ===")
    for k, v in stats.items():
        print(f"  {k}: {v}")
    print(f"  staged_high_risk_items: {len(staged_high_risk)}")
    print(f"  staged file: {staged_path}")
    print()
    print("Per-course changes:")
    for cid, chs in per_course_log[:50]:
        print(f"  {cid}: {', '.join(chs)}")
    if len(per_course_log) > 50:
        print(f"  ... (+{len(per_course_log)-50} more)")


if __name__ == "__main__":
    main()
