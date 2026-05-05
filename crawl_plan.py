"""crawl_plan.py — Phase 0 of the price-data crawl loop.

Scans data/golf_courses.json and emits a prioritized work queue:
- P0: no usable fee data at all (no slot value, no source URL)
- P1: only one source, OR no gogolf cross-reference, OR < 4 of 6 time slots filled
- P2: last_verified > 6 months old, OR existing primary vs gogolf disagree by 30%+

Run BEFORE crawl_runner.py. Does not touch the network. Reads only.

Output: crawl_queue.json (next to data/) with the full prioritized list.
Console: per-priority counts + 5 sample courses each.

Schema-compatibility note:
    Existing site code reads `fees_2026_05.sources` as a string-URL array.
    The crawl loop ADDS a parallel `fees_2026_05.source_details` array of
    objects (url, publisher, tier, value, fetched_at, ...) without disturbing
    the existing array. This planner only enumerates work — no mutation.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA_FILE = ROOT / "data" / "golf_courses.json"
OUT_FILE = ROOT / "data" / "crawl_queue.json"

# Cutoff: anything verified before this date is "stale"
STALENESS_CUTOFF_DAYS = 180

SLOT_KEYS = ["wdAm", "wdPm", "satAm", "satPm", "sunAm", "sunPm"]


def first_number(obj, keys=()):
    if isinstance(obj, (int, float)):
        return float(obj)
    if not isinstance(obj, dict):
        return None
    for k in keys:
        v = obj.get(k)
        if isinstance(v, (int, float)):
            return float(v)
    for v in obj.values():
        if isinstance(v, (int, float)):
            return float(v)
    return None


def extract_am_pm(slot_data):
    """Mirror of app.js extractAmPm — pull AM/PM proxies from a slot dict."""
    if not isinstance(slot_data, dict):
        return None, None
    am_vals, pm_vals, all_day = [], [], []
    KEYS = ("visitor", "visitor_18h", "visitor_min", "visitor_max",
            "green_fee_idr", "guest_fee_idr", "all_inclusive")

    def find_numeric(o):
        if isinstance(o, (int, float)):
            return [float(o)]
        if not isinstance(o, dict):
            return []
        out = [o[k] for k in KEYS if isinstance(o.get(k), (int, float))]
        if out:
            return [float(x) for x in out]
        for k, v in o.items():
            if "visitor" in k.lower() and isinstance(v, (int, float)):
                out.append(float(v))
        if out:
            return out
        return [float(v) for v in o.values() if isinstance(v, (int, float))]

    def walk(o, depth=0):
        if depth > 5 or not isinstance(o, dict):
            return
        for k, v in o.items():
            lk = k.lower()
            is_am = "morning" in lk or lk.endswith("_am") or lk == "am"
            is_pm = ("afternoon" in lk or lk.endswith("_pm") or lk == "pm"
                     or "twilight" in lk or "sunset" in lk)
            is_all = "all_day" in lk
            if is_am:
                am_vals.extend(find_numeric(v))
            elif is_pm:
                pm_vals.extend(find_numeric(v))
            elif is_all:
                all_day.extend(find_numeric(v))
            elif isinstance(v, dict):
                walk(v, depth + 1)

    walk(slot_data)
    am = min(am_vals) if am_vals else (min(all_day) if all_day else None)
    pm = min(pm_vals) if pm_vals else (min(all_day) if all_day else None)
    return am, pm


def get_primary_rates(c):
    f = c.get("fees_2026_05") or {}
    sd = f.get("schedule_detailed") or {}
    wd_am, wd_pm = extract_am_pm(sd.get("weekday"))
    sat_am, sat_pm = extract_am_pm(sd.get("weekend_saturday"))
    sun_am, sun_pm = extract_am_pm(sd.get("weekend_sunday"))
    out = {
        "wdAm": wd_am, "wdPm": wd_pm,
        "satAm": sat_am, "satPm": sat_pm,
        "sunAm": sun_am, "sunPm": sun_pm,
    }
    wd = f.get("weekday") or {}
    we = f.get("weekend") or {}
    wd_fb = wd.get("green_fee_idr") or wd.get("guest_fee_idr")
    we_fb = we.get("green_fee_idr") or we.get("guest_fee_idr")
    if out["wdAm"] is None and out["wdPm"] is None and wd_fb:
        out["wdAm"] = out["wdPm"] = float(wd_fb)
    if out["satAm"] is None and out["satPm"] is None and we_fb:
        out["satAm"] = out["satPm"] = float(we_fb)
    if out["sunAm"] is None and out["sunPm"] is None and we_fb:
        out["sunAm"] = out["sunPm"] = float(we_fb)
    return out


def get_gogolf_rates(c):
    sch = (c.get("fees_gogolf_reference") or {}).get("schedule")
    if not sch:
        return None
    return {
        "wdAm": sch.get("weekday", {}).get("am"),
        "wdPm": sch.get("weekday", {}).get("pm"),
        "satAm": sch.get("saturday", {}).get("am"),
        "satPm": sch.get("saturday", {}).get("pm"),
        "sunAm": sch.get("sunday", {}).get("am"),
        "sunPm": sch.get("sunday", {}).get("pm"),
    }


def parse_date_safe(s):
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(str(s)[:10], fmt)
        except ValueError:
            continue
    return None


def get_primary_url_count(c):
    f = c.get("fees_2026_05") or {}
    return sum(1 for u in (f.get("sources") or [])
               if isinstance(u, str) and u.startswith(("http://", "https://")))


def has_gogolf(c):
    return bool((c.get("fees_gogolf_reference") or {}).get("source_url"))


def filled_slot_count(c):
    pri = get_primary_rates(c)
    return sum(1 for v in pri.values() if v is not None)


def max_pct_diff_primary_vs_gogolf(c):
    pri = get_primary_rates(c)
    gg = get_gogolf_rates(c)
    if not gg:
        return 0.0, None
    max_pct = 0.0
    worst_slot = None
    for slot in SLOT_KEYS:
        a, b = pri.get(slot), gg.get(slot)
        if a is None or b is None or a == 0:
            continue
        diff = abs(a - b) / min(a, b) * 100
        if diff > max_pct:
            max_pct = diff
            worst_slot = slot
    return max_pct, worst_slot


def classify(c, today):
    f = c.get("fees_2026_05") or {}
    op = (c.get("operating_status") or {}).get("status", "operating")
    # Skip permanently closed — no point crawling rates
    if op == "closed_permanent":
        return None, None, None

    primary_url_count = get_primary_url_count(c)
    has_gg = has_gogolf(c)
    n_slots = filled_slot_count(c)
    diff_pct, diff_slot = max_pct_diff_primary_vs_gogolf(c)
    last_v = parse_date_safe(f.get("last_verified"))
    age_days = (today - last_v).days if last_v else None

    # P0: no usable data at all
    if n_slots == 0 and primary_url_count == 0 and not has_gg:
        return "P0", "no fee data, no source", {
            "n_slots": n_slots,
            "primary_url_count": primary_url_count,
            "has_gogolf": has_gg,
            "age_days": age_days,
        }

    # P1: only one source OR fewer than 4 of 6 slots filled
    if (primary_url_count + (1 if has_gg else 0)) <= 1 or n_slots < 4:
        reasons = []
        if primary_url_count + (1 if has_gg else 0) <= 1:
            reasons.append(f"only {primary_url_count + (1 if has_gg else 0)} source")
        if n_slots < 4:
            reasons.append(f"{n_slots}/6 slots filled")
        return "P1", "; ".join(reasons), {
            "n_slots": n_slots,
            "primary_url_count": primary_url_count,
            "has_gogolf": has_gg,
            "age_days": age_days,
        }

    # P2: stale OR cross-source disagreement >= 30%
    if age_days is not None and age_days >= STALENESS_CUTOFF_DAYS:
        return "P2", f"verified {age_days}d ago", {
            "n_slots": n_slots,
            "primary_url_count": primary_url_count,
            "has_gogolf": has_gg,
            "age_days": age_days,
        }
    if diff_pct >= 30:
        return "P2", f"primary vs gogolf {diff_pct:.0f}% on {diff_slot}", {
            "n_slots": n_slots,
            "primary_url_count": primary_url_count,
            "has_gogolf": has_gg,
            "age_days": age_days,
            "diff_pct": round(diff_pct, 1),
            "diff_slot": diff_slot,
        }

    # Otherwise — already well-covered, skip
    return None, None, None


def candidate_seed_urls(c):
    """Build a prioritized list of seed URLs likely to contain fees.

    v2 strategy (much higher yield than v1):
      1. *Re-visit known sources* — URLs already in fees_2026_05.sources are
         the highest-yield seeds; they were proven to contain prices when
         originally added. Re-fetching them validates current values.
      2. Official-site root — let the runner discover rate-page links from
         in-page anchors (rate/price/fee/harga/tarif keywords) instead of
         guessing path extensions.
      3. Q-Access search — runner follows the detail link from the search
         results card, not just the search page itself.
      4. Wayback CDX — runner uses the CDX API to find the most recent
         snapshot of known sources.
    """
    out = []
    seen = set()

    def push(kind, url):
        if not url or url in seen:
            return
        seen.add(url)
        out.append((kind, url))

    # 1. Known sources (highest yield — already proven to host prices)
    f = c.get("fees_2026_05") or {}
    for u in (f.get("sources") or []):
        if isinstance(u, str) and u.startswith(("http://", "https://")):
            push("known_source", u)

    # GoGolf reference URL is also a known yielding source for some courses
    gg_url = (c.get("fees_gogolf_reference") or {}).get("source_url")
    if isinstance(gg_url, str) and gg_url.startswith(("http://", "https://")):
        push("known_source", gg_url)

    # 2. Official site root — runner will discover rate-page links from HTML
    site = (c.get("website") or "").rstrip("/")
    if site:
        push("official_root", site)

    # 3. Q-Access search → runner follows detail link from results
    name_slug = (c.get("name_en") or "").lower().split(",")[0].split("(")[0].strip()
    name_slug = name_slug.replace(" ", "+")[:40]
    if name_slug:
        push("qaccess_search",
             f"https://www.qaccess.asia/QGolfPrice?searchString={name_slug}")

    # 4. Wayback CDX (runner resolves to a real snapshot URL)
    if site:
        push("wayback_cdx",
             f"https://web.archive.org/cdx/search/cdx?url={site}/&output=json&limit=3&filter=statuscode:200")

    return out


def main():
    if not DATA_FILE.exists():
        print(f"ERROR: {DATA_FILE} not found", file=sys.stderr)
        sys.exit(2)

    doc = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    courses = doc.get("courses") or []

    today = datetime(2026, 5, 5)  # match harness clock
    queue = {"P0": [], "P1": [], "P2": []}
    skipped_perm_closed = 0

    for c in courses:
        if (c.get("operating_status") or {}).get("status") == "closed_permanent":
            skipped_perm_closed += 1
            continue
        priority, reason, meta = classify(c, today)
        if priority is None:
            continue
        seeds = candidate_seed_urls(c)
        queue[priority].append({
            "id": c["id"],
            "name_en": c["name_en"],
            "region": c.get("region"),
            "province": c.get("province"),
            "website": c.get("website"),
            "operating_status": (c.get("operating_status") or {}).get("status", "operating"),
            "reason": reason,
            "diagnostics": meta,
            "seed_urls": seeds,
        })

    # Sort each bucket by name for determinism
    for k in queue:
        queue[k].sort(key=lambda x: x["name_en"].lower())

    out = {
        "generated_at": today.isoformat() + "Z",
        "total_courses": len(courses),
        "skipped_permanently_closed": skipped_perm_closed,
        "well_covered": (len(courses) - skipped_perm_closed
                         - len(queue["P0"]) - len(queue["P1"]) - len(queue["P2"])),
        "P0_count": len(queue["P0"]),
        "P1_count": len(queue["P1"]),
        "P2_count": len(queue["P2"]),
        "queue": queue,
    }
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    # Console summary
    print(f"=== Crawl Plan (Phase 0) ===")
    print(f"Total courses:                   {out['total_courses']}")
    print(f"Skipped (permanently closed):    {skipped_perm_closed}")
    print(f"Already well-covered (skip):     {out['well_covered']}")
    print(f"P0 (no fee data):                {out['P0_count']}")
    print(f"P1 (one source / sparse slots):  {out['P1_count']}")
    print(f"P2 (stale / disagreement 30%+):  {out['P2_count']}")
    print()
    print(f"Output: {OUT_FILE}")
    print()
    for level in ("P0", "P1", "P2"):
        sample = queue[level][:5]
        if not sample:
            continue
        print(f"--- {level} sample (top 5 of {len(queue[level])}) ---")
        for entry in sample:
            print(f"  {entry['name_en']:<40} | {entry['region']:<14} | {entry['reason']}")
        print()


if __name__ == "__main__":
    main()
