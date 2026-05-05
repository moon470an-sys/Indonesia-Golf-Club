"""merge_crawled.py — Phase 2 of the price-data crawl loop.

Reads the most recent data/crawl_log_*.json (or one passed via --log) and
folds the extracted price candidates into data/golf_courses.json.

Compatibility-first schema decision:
    The site UI (app.js) reads `fees_2026_05.sources` as a STRING URL ARRAY.
    To avoid breaking it, we add a NEW parallel field:

        fees_2026_05.source_details = [
          { "url": "...", "publisher": "...", "tier": 1, "tier_score": 95,
            "value_idr": 1500000, "slot": "satAm",
            "fetched_at": "2026-05-05T15:30:00Z", "raw_excerpt": "...",
            "confidence": 88 },
          ...
        ]

    The existing string-URL `sources` array gets new URLs APPENDED if they
    are not already present (de-duped by URL). Existing URLs stay untouched.

    A new representative aggregate is added to:

        fees_2026_05.crawled_summary = {
          "wdAm": { "value_idr": 850000, "confidence": 88,
                    "verification_needed": false, "n_sources": 2 },
          ... (per slot)
        }

    Existing schedule_detailed / weekday / weekend objects are NOT modified.
    The crawled_summary is the *additive* representation that downstream code
    can opt-in to read; the rest of the schema is preserved verbatim.

Tier scoring + recency weighting:
    final_score = tier_score * recency_factor
    recency_factor = 1.0 if <=3mo, 0.85 if <=6mo, 0.65 if <=12mo, 0.4 otherwise
    representative value = max(score)-pick if Tier 1 exists, otherwise
                          weighted-average across visible candidates.

Run:  python merge_crawled.py [--log <file>] [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
COURSES_FILE = DATA / "golf_courses.json"

TIER_SCORES = {1: 95, 2: 80, 3: 65, 4: 50, 5: 35}

# 6 canonical AM/PM slots that the site UI consumes
SLOTS = ("wdAm", "wdPm", "satAm", "satPm", "sunAm", "sunPm")
# Generic slots from the crawler — fanned out at merge time
GENERIC_FANOUT = {
    "weekday": ("wdAm", "wdPm"),
    "weekend": ("satAm", "satPm", "sunAm", "sunPm"),
}


def find_latest_log() -> Optional[Path]:
    candidates = sorted(DATA.glob("crawl_log_*.json"), reverse=True)
    return candidates[0] if candidates else None


def parse_iso8601(s: str) -> Optional[datetime]:
    if not s:
        return None
    try:
        # Python 3.11+ accepts trailing 'Z' via fromisoformat
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


def recency_factor(fetched_at_iso: str, now: Optional[datetime] = None) -> float:
    now = now or datetime.now(timezone.utc)
    dt = parse_iso8601(fetched_at_iso)
    if not dt:
        return 0.4
    days = (now - dt).days
    if days <= 90:
        return 1.0
    if days <= 180:
        return 0.85
    if days <= 365:
        return 0.65
    return 0.4


def score_candidate(c: dict, now: Optional[datetime] = None) -> float:
    tier = int(c.get("tier", 5))
    base = TIER_SCORES.get(tier, 35)
    return base * recency_factor(c.get("fetched_at", ""), now)


def fan_out(candidates: list[dict]) -> dict[str, list[dict]]:
    """Group candidates by 6-slot key, expanding generic 'weekday'/'weekend'."""
    by_slot: dict[str, list[dict]] = defaultdict(list)
    for c in candidates:
        slot = c.get("slot")
        if slot in SLOTS:
            by_slot[slot].append(c)
        elif slot in GENERIC_FANOUT:
            for s in GENERIC_FANOUT[slot]:
                expanded = dict(c)
                expanded["from_generic"] = slot
                # Down-tier slightly to reflect lower specificity
                expanded["tier"] = min(int(c.get("tier", 5)) + 1, 5)
                by_slot[s].append(expanded)
    return dict(by_slot)


def remove_slot_outliers(slot_cands: list[dict]) -> tuple[list[dict], list[dict]]:
    """Drop candidates whose value is far below the slot median (likely
    ancillary-fee leakage), keeping only those within sane multiples.

    Heuristic: any value below 40% of the median is treated as outlier
    (caddy/cart/insurance values are typically 5-25% of green fees).
    Returns (kept, dropped). Never drops if <3 candidates (sample too small).
    """
    if len(slot_cands) < 3:
        return slot_cands, []
    values = sorted(c["value_idr"] for c in slot_cands)
    median = values[len(values) // 2]
    floor = median * 0.4
    kept, dropped = [], []
    for c in slot_cands:
        if c["value_idr"] < floor:
            dropped.append(c)
        else:
            kept.append(c)
    # Never strip more than half the population — be conservative
    if len(dropped) > len(slot_cands) // 2:
        return slot_cands, []
    return kept, dropped


def pick_representative(slot_cands: list[dict]) -> dict:
    """Choose representative value + meta for one slot.

    Filters obvious ancillary-leak outliers (values << slot median) before
    picking the trusted value. Outlier candidates are NOT deleted from
    source_details — only excluded from the representative aggregate.
    """
    if not slot_cands:
        return {}

    kept, dropped = remove_slot_outliers(slot_cands)
    cohort = kept if kept else slot_cands

    # If any Tier-1 candidate exists in the kept set, pick highest-scoring
    tier1 = [c for c in cohort if int(c.get("tier", 5)) == 1]
    if tier1:
        chosen = max(tier1, key=score_candidate)
        rep = chosen["value_idr"]
        confidence = int(score_candidate(chosen))
    else:
        weights = [score_candidate(c) for c in cohort]
        total_w = sum(weights) or 1.0
        rep = int(sum(c["value_idr"] * w for c, w in zip(cohort, weights)) / total_w)
        confidence = int(sum(weights) / len(cohort))

    values = [c["value_idr"] for c in cohort]
    lo, hi = min(values), max(values)
    diff_pct = (hi - lo) / lo * 100 if lo > 0 else 0.0
    return {
        "value_idr": rep,
        "confidence": confidence,
        "n_sources": len(cohort),
        "n_outliers_dropped": len(dropped),
        "min_idr": lo,
        "max_idr": hi,
        "verification_needed": diff_pct >= 30.0,
        "diff_pct": round(diff_pct, 1),
    }


def merge_one_course(course: dict, course_log: dict, now: datetime) -> dict:
    """Update `course` in place. Returns a per-course mutation summary."""
    cands = course_log.get("candidates", []) or []
    f = course.setdefault("fees_2026_05", {})
    existing_urls: list[str] = list(f.get("sources") or [])
    existing_url_set = {u for u in existing_urls if isinstance(u, str)}

    summary = {
        "course_id": course.get("id"),
        "name_en": course.get("name_en"),
        "candidates_in": len(cands),
        "new_urls_added": 0,
        "slots_filled": 0,
        "verification_flags": [],
    }

    if not cands:
        return summary

    # Append to source_details (additive, preserve any existing entries)
    sd = f.setdefault("source_details", [])
    seen_keys = set((d.get("source_url"), d.get("slot"), d.get("value_idr"))
                    for d in sd if isinstance(d, dict))
    for c in cands:
        key = (c.get("source_url"), c.get("slot"), c.get("value_idr"))
        if key in seen_keys:
            continue
        c2 = dict(c)
        c2["tier_score"] = TIER_SCORES.get(int(c.get("tier", 5)), 35)
        c2["score"] = round(score_candidate(c, now), 1)
        sd.append(c2)
        seen_keys.add(key)

        # Append URL to legacy sources string array if new
        url = c.get("source_url")
        if isinstance(url, str) and url and url not in existing_url_set:
            existing_urls.append(url)
            existing_url_set.add(url)
            summary["new_urls_added"] += 1

    f["sources"] = existing_urls

    # Build crawled_summary: representative per slot
    by_slot = fan_out(cands)
    cs = f.setdefault("crawled_summary", {})
    for slot in SLOTS:
        slot_cs = by_slot.get(slot) or []
        if not slot_cs:
            continue
        rep = pick_representative(slot_cs)
        if not rep:
            continue
        # Merge with existing summary if any (keep highest n_sources)
        prev = cs.get(slot)
        if prev and prev.get("n_sources", 0) >= rep["n_sources"]:
            continue
        cs[slot] = rep
        summary["slots_filled"] += 1
        if rep.get("verification_needed"):
            summary["verification_flags"].append(slot)

    # Provenance bookkeeping
    f["last_crawled"] = now.isoformat()
    return summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", help="explicit crawl_log_*.json path")
    ap.add_argument("--dry-run", action="store_true",
                    help="show changes but do not modify data/golf_courses.json")
    args = ap.parse_args()

    log_path = Path(args.log) if args.log else find_latest_log()
    if not log_path or not log_path.exists():
        print("ERROR: no crawl_log_*.json found in data/ — run crawl_runner.py first.",
              file=sys.stderr)
        sys.exit(2)

    log = json.loads(log_path.read_text(encoding="utf-8"))
    results = log.get("results", []) or []
    if not results:
        print("Log has zero results. Nothing to merge.")
        sys.exit(0)

    doc = json.loads(COURSES_FILE.read_text(encoding="utf-8"))
    courses = doc.get("courses") or []
    by_id = {c["id"]: c for c in courses}

    # Tier-distribution snapshot BEFORE
    def tier_counts(courses):
        out = defaultdict(int)
        for c in courses:
            f = c.get("fees_2026_05") or {}
            for s in (f.get("source_details") or []):
                t = int(s.get("tier", 5))
                out[t] += 1
        return dict(out)

    tier_before = tier_counts(courses)

    now = datetime.now(timezone.utc)
    summaries = []
    for r in results:
        cid = r.get("course_id")
        course = by_id.get(cid)
        if not course:
            continue
        s = merge_one_course(course, r, now)
        summaries.append(s)

    # Tier distribution AFTER
    tier_after = tier_counts(courses)

    # Aggregate stats
    total_new_urls = sum(s["new_urls_added"] for s in summaries)
    total_slots_filled = sum(s["slots_filled"] for s in summaries)
    total_v_flags = sum(len(s["verification_flags"]) for s in summaries)
    courses_touched = sum(1 for s in summaries
                          if s["new_urls_added"] or s["slots_filled"])

    print("=== Merge Summary ===")
    print(f"Source log:                {log_path.name}")
    print(f"Results in log:            {len(results)}")
    print(f"Courses touched:           {courses_touched}")
    print(f"New source URLs added:     {total_new_urls}")
    print(f"Slot summaries written:    {total_slots_filled}")
    print(f"Verification flags raised: {total_v_flags}")
    print()
    print("Tier distribution (source_details count):")
    print(f"  Before: {dict(sorted(tier_before.items()))}")
    print(f"  After:  {dict(sorted(tier_after.items()))}")
    print()

    flag_courses = [s for s in summaries if s["verification_flags"]]
    if flag_courses:
        print(f"Courses needing verification ({len(flag_courses)}):")
        for s in flag_courses[:20]:
            print(f"  {s['name_en']} — {', '.join(s['verification_flags'])}")
        if len(flag_courses) > 20:
            print(f"  ... and {len(flag_courses) - 20} more")
        print()

    if args.dry_run:
        print("[dry-run] no files written.")
        return

    # Backup before mutating
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = COURSES_FILE.parent / f"golf_courses.backup.{ts}.json"
    shutil.copy2(COURSES_FILE, backup)
    print(f"[backup] {backup.name}")

    COURSES_FILE.write_text(json.dumps(doc, ensure_ascii=False, indent=2),
                            encoding="utf-8")
    print(f"[write]  {COURSES_FILE.name}")

    # Append a compact summary block for VALIDATION_REPORT to ingest
    merge_summary_path = DATA / f"merge_summary_{ts}.json"
    merge_summary_path.write_text(json.dumps({
        "log_file": log_path.name,
        "courses_touched": courses_touched,
        "new_urls_added": total_new_urls,
        "slots_filled": total_slots_filled,
        "verification_flags": total_v_flags,
        "tier_before": tier_before,
        "tier_after": tier_after,
        "verification_needed_courses": [
            {"name_en": s["name_en"], "course_id": s["course_id"],
             "slots": s["verification_flags"]}
            for s in flag_courses
        ],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[summary] {merge_summary_path.name}")


if __name__ == "__main__":
    main()
