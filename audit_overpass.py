"""
Overpass-based coordinate audit. Queries every leisure=golf_course feature
in Indonesia (way + relation + node), takes the polygon centroid where
available, then matches each course in our dataset to OSM features by
name similarity. This is significantly more accurate than Nominatim's
text search because:
- It uses the actual OSM `name` tag on the golf course geometry, not
  arbitrary nearby POIs.
- For ways/relations (most courses are polygons), it returns the centroid
  of the actual course boundary, not a single tagged point that may have
  been placed on a clubhouse, parking lot, or unrelated building.

Usage:
    python audit_overpass.py            # dry run -> overpass_match_report.json
    python audit_overpass.py --apply    # apply matches above threshold
"""
import argparse, json, math, re, time, unicodedata
import urllib.request, urllib.parse
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).parent
DATA = ROOT / "data" / "golf_courses.json"
CACHE = ROOT / ".overpass_cache.json"
REPORT = ROOT / "overpass_match_report.json"

OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.openstreetmap.fr/api/interpreter",
]

# Match threshold: name similarity in [0,1]. 0.70 filters out unrelated
# brands while still catching variants like "Damai Indah Golf" vs
# "Damai Indah Golf & Country Club".
ACCEPT_THRESHOLD = 0.78

# Movement sanity: even a strong name match shouldn't move a marker
# more than 25 km from its current location (catches name collisions
# across regions).
MAX_MOVE_KM = 25.0

# When name score is high (>=0.85) we tolerate slightly larger moves
# because the brand name is unambiguous; this catches cases where the
# original coord was just plain wrong.
HIGH_CONF_SCORE = 0.85
HIGH_CONF_MAX_MOVE_KM = 25.0


def haversine_km(a_lat, a_lng, b_lat, b_lng):
    R = 6371.0
    dl = math.radians(b_lat - a_lat); dn = math.radians(b_lng - a_lng)
    s = (math.sin(dl/2)**2
         + math.cos(math.radians(a_lat))*math.cos(math.radians(b_lat))*math.sin(dn/2)**2)
    return 2 * R * math.asin(math.sqrt(s))


def fetch_overpass():
    """Fetch all leisure=golf_course features in Indonesia.
    Cached to .overpass_cache.json so repeated runs are instant."""
    if CACHE.exists():
        print(f"[cache] using {CACHE}")
        return json.loads(CACHE.read_text(encoding="utf-8"))

    query = """
[out:json][timeout:90];
area["ISO3166-1"="ID"][admin_level=2]->.id;
(
  node["leisure"="golf_course"](area.id);
  way["leisure"="golf_course"](area.id);
  relation["leisure"="golf_course"](area.id);
);
out center tags;
"""
    last_err = None
    for endpoint in OVERPASS_ENDPOINTS:
        try:
            print(f"[overpass] querying {endpoint} ...", flush=True)
            data = urllib.parse.urlencode({"data": query}).encode("utf-8")
            req = urllib.request.Request(endpoint, data=data,
                headers={"User-Agent": "IndonesiaGolfClubMap/1.2 audit"})
            with urllib.request.urlopen(req, timeout=120) as resp:
                doc = json.loads(resp.read().decode("utf-8"))
            CACHE.write_text(json.dumps(doc, ensure_ascii=False, indent=2),
                             encoding="utf-8")
            print(f"[overpass] {len(doc.get('elements', []))} features cached")
            return doc
        except Exception as e:
            print(f"  ! {endpoint} failed: {e}")
            last_err = e
            time.sleep(2)
    raise RuntimeError(f"All Overpass endpoints failed: {last_err}")


_punct_re = re.compile(r"[^\w\s]+", re.UNICODE)
_stops = {
    "golf", "club", "course", "country", "the", "a", "an", "and", "&",
    "padang", "lapangan", "of", "at", "indonesia",
}


def normalize(s: str) -> str:
    if not s: return ""
    s = unicodedata.normalize("NFKC", s)
    s = s.lower()
    s = _punct_re.sub(" ", s)
    return " ".join(t for t in s.split() if t)


def normalize_strict(s: str) -> str:
    """Drop generic golf/club stopwords for fairer name comparison."""
    return " ".join(t for t in normalize(s).split() if t not in _stops)


def name_score(my_name: str, osm_name: str) -> float:
    """0..1 similarity, robust to brand-suffix differences."""
    if not my_name or not osm_name: return 0.0
    a_full = normalize(my_name);  b_full = normalize(osm_name)
    a_core = normalize_strict(my_name);  b_core = normalize_strict(osm_name)
    if not a_core or not b_core:
        return SequenceMatcher(None, a_full, b_full).ratio()
    full_r = SequenceMatcher(None, a_full, b_full).ratio()
    core_r = SequenceMatcher(None, a_core, b_core).ratio()
    # Token overlap
    a_tokens = set(a_core.split()); b_tokens = set(b_core.split())
    if a_tokens and b_tokens:
        jacc = len(a_tokens & b_tokens) / len(a_tokens | b_tokens)
    else:
        jacc = 0.0
    # Substring bonus when one core is contained in the other
    sub = 1.0 if (a_core and b_core and (a_core in b_core or b_core in a_core)) else 0.0
    return max(full_r, core_r, jacc, sub * 0.95)


def feature_coord(el):
    """Return (lat, lng) for an Overpass element."""
    if el.get("type") == "node":
        return el.get("lat"), el.get("lon")
    c = el.get("center") or {}
    return c.get("lat"), c.get("lon")


def feature_names(el):
    """All name-like tags worth scoring against."""
    t = el.get("tags") or {}
    keys = ("name", "name:en", "name:id", "alt_name", "official_name",
            "loc_name", "short_name", "old_name")
    out = []
    for k in keys:
        v = t.get(k)
        if v: out.append(v)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--threshold", type=float, default=ACCEPT_THRESHOLD)
    args = ap.parse_args()

    overpass = fetch_overpass()
    features = overpass.get("elements", [])

    # Pre-extract candidates once for speed
    cands = []
    for el in features:
        lat, lng = feature_coord(el)
        if lat is None or lng is None: continue
        names = feature_names(el)
        if not names: continue
        cands.append({
            "id": f'{el.get("type")}/{el.get("id")}',
            "lat": float(lat), "lng": float(lng),
            "names": names,
            "tags": el.get("tags") or {},
        })
    print(f"[overpass] {len(cands)} named golf-course features in Indonesia")

    doc = json.loads(DATA.read_text(encoding="utf-8"))

    report = {
        "threshold": args.threshold,
        "courses_total": len(doc["courses"]),
        "matched": 0, "applied": 0, "no_match": 0, "weak_match": 0,
        "results": [],
    }

    for c in doc["courses"]:
        name = c.get("name_en", "")
        cur_lat = c.get("lat"); cur_lng = c.get("lng")

        # Stage 1: Score every candidate; keep all that score >= 0.55 so we
        # can disambiguate by proximity below (handles same-brand siblings
        # like Damai Indah PIK vs BSD that share a name).
        scored = []
        for cand in cands:
            best_for_cand = 0.0; via = None
            for nm in cand["names"]:
                s = name_score(name, nm)
                if s > best_for_cand:
                    best_for_cand = s; via = nm
            if best_for_cand >= 0.55:
                scored.append((best_for_cand, via, cand))

        # Stage 2: pick best candidate with proximity tiebreaker. We choose
        # the candidate that maximizes:
        #   composite = score - 0.0008 * distance_km
        # which prefers high name match but breaks ties toward the candidate
        # closest to the existing coordinate. This crucially picks the right
        # branch when one OSM brand has multiple sister courses.
        best = None; best_score = 0.0; best_via = None
        if scored:
            # If we have an existing coord, score with distance penalty
            best_composite = -1e9
            for s, via, cand in scored:
                d = None
                if cur_lat is not None and cur_lng is not None:
                    d = haversine_km(cur_lat, cur_lng, cand["lat"], cand["lng"])
                penalty = 0.0008 * (d or 0)
                composite = s - penalty
                if composite > best_composite:
                    best_composite = composite
                    best = cand; best_score = s; best_via = via

        if not best:
            report["no_match"] += 1
            report["results"].append({
                "id": c["id"], "name": name, "decision": "no_match",
                "score": 0.0,
            })
            continue

        # Sanity check on movement
        move_km = None
        if cur_lat is not None and cur_lng is not None:
            move_km = haversine_km(cur_lat, cur_lng, best["lat"], best["lng"])

        decision = "match"
        applied = False
        if best_score < args.threshold:
            decision = "weak_match"
            report["weak_match"] += 1
        elif move_km is not None and move_km > MAX_MOVE_KM:
            decision = "match_too_far"
        else:
            decision = "match"
            report["matched"] += 1
            applied = True

        if applied and args.apply:
            c["lat"] = best["lat"]
            c["lng"] = best["lng"]
            c["coord_source"] = "overpass_v1"
            c["coord_osm_ref"] = best["id"]
            if c.get("coord_approximate"): c["coord_approximate"] = False
            report["applied"] += 1

        report["results"].append({
            "id": c["id"], "name": name,
            "decision": decision,
            "score": round(best_score, 3),
            "move_km": round(move_km, 3) if move_km is not None else None,
            "old": [cur_lat, cur_lng],
            "new": [best["lat"], best["lng"]],
            "matched_name": best_via,
            "osm_ref": best["id"],
            "applied": applied,
        })

        if decision == "match":
            move_str = f" d={move_km:.2f} km" if move_km is not None else ""
            print(f"[OK ] {name}: '{best_via}' score={best_score:.2f}{move_str}")
        elif decision == "match_too_far":
            print(f"[FAR] {name}: '{best_via}' score={best_score:.2f} d={move_km:.2f} km - held back")
        else:
            print(f"[WK ] {name}: best='{best_via}' score={best_score:.2f}")

    if args.apply:
        DATA.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nApplied {report['applied']} updates -> {DATA}")

    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nReport: {REPORT}")
    print(f"  total={report['courses_total']}  matched={report['matched']}  "
          f"weak={report['weak_match']}  no_match={report['no_match']}  "
          f"applied={report['applied']}")


if __name__ == "__main__":
    main()
