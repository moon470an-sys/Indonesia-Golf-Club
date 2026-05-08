"""
Audit and re-geocode all golf-course coordinates against Nominatim (OSM)
using golf-course-name-prioritized queries. Produces a diff report; only
applies updates when --apply is passed.

Usage:
    python audit_coords.py            # dry run, write report to coord_audit_report.json
    python audit_coords.py --apply    # apply updates to data/golf_courses.json

Notes:
- Respects Nominatim 1 req/sec policy.
- For each course, tries multiple queries (most specific first) and picks
  the first hit whose Nominatim `class` is leisure/golf or whose `display_name`
  contains "golf".
- Movement >5 km from the existing coordinate is flagged for human review
  (not auto-applied unless the existing coords were marked approximate).
"""
import argparse
import json
import math
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).parent
DATA = ROOT / "data" / "golf_courses.json"
REPORT = ROOT / "coord_audit_report.json"

USER_AGENT = "IndonesiaGolfClubMap/1.1 (moon470an@gmail.com) audit"
NOMINATIM = "https://nominatim.openstreetmap.org/search"

# Movement threshold (km) above which we mark the change as "needs review"
SOFT_MOVE_KM = 1.0       # log all moves above 1 km
HARD_REVIEW_KM = 5.0     # don't auto-apply moves above 5 km unless coord_approximate=True


def haversine_km(a_lat, a_lng, b_lat, b_lng):
    R = 6371.0
    rl1 = math.radians(a_lat); rl2 = math.radians(b_lat)
    dl  = math.radians(b_lat - a_lat)
    dn  = math.radians(b_lng - a_lng)
    s = math.sin(dl/2)**2 + math.cos(rl1)*math.cos(rl2)*math.sin(dn/2)**2
    return 2 * R * math.asin(math.sqrt(s))


def nominatim(query: str):
    params = urllib.parse.urlencode({
        "q": query,
        "format": "json",
        "limit": 5,
        "countrycodes": "id",
        "addressdetails": 1,
    })
    req = urllib.request.Request(
        f"{NOMINATIM}?{params}",
        headers={"User-Agent": USER_AGENT},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"  ! error: {e}", flush=True)
        return []


def is_golfish(item):
    """True when the OSM hit looks like a golf course / leisure POI."""
    cls = (item.get("class") or "").lower()
    typ = (item.get("type") or "").lower()
    name = (item.get("display_name") or "").lower()
    if cls == "leisure" and typ in ("golf_course", "miniature_golf"):
        return True
    if "golf" in name:
        return True
    return False


def best_hit(items, course):
    """Pick the most golf-likely hit; fallback to first hit."""
    for it in items:
        if is_golfish(it):
            return it
    return items[0] if items else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="Write updates back to golf_courses.json")
    ap.add_argument("--limit", type=int, default=0, help="Stop after N courses (debug)")
    args = ap.parse_args()

    doc = json.loads(DATA.read_text(encoding="utf-8"))
    courses = doc["courses"]
    if args.limit:
        courses = courses[:args.limit]

    report = {
        "total": len(courses),
        "found": 0,
        "missing": 0,
        "applied": 0,
        "soft_flagged": [],   # 1km < move <= 5km, applied
        "review": [],          # >5km move, NOT applied
        "not_found": [],
        "summary": [],
    }

    for i, c in enumerate(courses, 1):
        name = c.get("name_en", "")
        region = c.get("region", "")
        province = c.get("province", "")
        cur_lat = c.get("lat")
        cur_lng = c.get("lng")
        cur_approx = bool(c.get("coord_approximate"))

        queries = [
            f'{name}',
            f'{name}, {region}, Indonesia',
            f'{name}, {province}, Indonesia',
            f'{name} golf, Indonesia',
        ]
        # Dedupe while preserving order
        seen = set(); queries = [q for q in queries if not (q in seen or seen.add(q))]

        print(f"[{i}/{len(courses)}] {name}", flush=True)

        hit = None
        used_q = None
        for q in queries:
            items = nominatim(q)
            time.sleep(1.1)  # Nominatim policy
            h = best_hit(items, c)
            if h:
                hit = h
                used_q = q
                if is_golfish(h):
                    break  # high-confidence; stop searching
        if not hit:
            print("  -> not found", flush=True)
            report["missing"] += 1
            report["not_found"].append({"id": c["id"], "name": name})
            continue

        new_lat = float(hit["lat"]); new_lng = float(hit["lon"])
        report["found"] += 1
        move_km = None
        if cur_lat is not None and cur_lng is not None:
            move_km = haversine_km(cur_lat, cur_lng, new_lat, new_lng)

        entry = {
            "id": c["id"],
            "name": name,
            "old": [cur_lat, cur_lng],
            "new": [new_lat, new_lng],
            "move_km": round(move_km, 3) if move_km is not None else None,
            "query": used_q,
            "osm_class": hit.get("class"),
            "osm_type": hit.get("type"),
            "osm_display_name": hit.get("display_name"),
            "is_golfish": is_golfish(hit),
            "old_approx": cur_approx,
        }

        # Decision tree
        do_apply = False
        if move_km is None:
            do_apply = True
            entry["decision"] = "applied (no prior coord)"
        elif move_km <= SOFT_MOVE_KM:
            do_apply = entry["is_golfish"]
            entry["decision"] = "applied (small move)" if do_apply else "skipped (not golfish, small move)"
        elif move_km <= HARD_REVIEW_KM:
            do_apply = entry["is_golfish"]
            entry["decision"] = "applied (medium move, golfish)" if do_apply else "soft_flag"
            if do_apply:
                report["soft_flagged"].append(entry)
        else:
            # >5 km: only apply if old was approximate AND the hit is golfish
            do_apply = entry["is_golfish"] and cur_approx
            entry["decision"] = "applied (large move; old approx, hit golfish)" if do_apply else "review (large move)"
            if not do_apply:
                report["review"].append(entry)

        if do_apply and args.apply:
            c["lat"] = new_lat
            c["lng"] = new_lng
            c["coord_source"] = "nominatim_audit_v1"
            if cur_approx:
                c["coord_approximate"] = False
            report["applied"] += 1

        report["summary"].append(entry)

        if move_km is not None:
            print(f"  -> {new_lat:.5f}, {new_lng:.5f}  Δ={move_km:.2f} km  ({entry['decision']})", flush=True)
        else:
            print(f"  -> {new_lat:.5f}, {new_lng:.5f}  ({entry['decision']})", flush=True)

    if args.apply:
        DATA.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nApplied {report['applied']} updates to {DATA}", flush=True)

    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nReport: {REPORT}", flush=True)
    print(f"  total={report['total']}  found={report['found']}  applied={report['applied']}  "
          f"soft_flag={len(report['soft_flagged'])}  review={len(report['review'])}  "
          f"not_found={len(report['not_found'])}", flush=True)


if __name__ == "__main__":
    main()
