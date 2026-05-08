"""
Apply targeted coordinate fixes for courses the main audit could not resolve
or held back for review:
- Damai Indah Golf PIK / BSD (alias-based Nominatim retry)
- Klub Golf Bogor Raya (apply held-back >5 km move; OSM hit verified golfish)
- Jababeka Golf & Country Club (apply held-back >5 km move; OSM hit verified golfish)
"""
import json, time, urllib.parse, urllib.request
from pathlib import Path

ROOT = Path(__file__).parent
DATA = ROOT / "data" / "golf_courses.json"
USER_AGENT = "IndonesiaGolfClubMap/1.1 (moon470an@gmail.com) audit-fix"
NOMINATIM = "https://nominatim.openstreetmap.org/search"


def nominatim(query: str):
    params = urllib.parse.urlencode({
        "q": query, "format": "json", "limit": 5,
        "countrycodes": "id", "addressdetails": 1,
    })
    req = urllib.request.Request(
        f"{NOMINATIM}?{params}", headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"  ! error: {e}")
        return []


def golfish(it):
    cls = (it.get("class") or "").lower()
    typ = (it.get("type") or "").lower()
    name = (it.get("display_name") or "").lower()
    return (cls == "leisure" and typ in ("golf_course", "miniature_golf")) or "golf" in name


def find(*queries):
    for q in queries:
        print(f"  query: {q}")
        items = nominatim(q)
        time.sleep(1.1)
        for it in items:
            if golfish(it):
                return it, q
        if items:
            return items[0], q
    return None, None


def main():
    doc = json.loads(DATA.read_text(encoding="utf-8"))
    by_id = {c["id"]: c for c in doc["courses"]}

    # --- Damai Indah PIK ---
    cid = "damai-indah-pik"
    if cid in by_id:
        print(f"\n[{cid}]")
        hit, q = find(
            "Damai Indah Golf PIK",
            "Damai Indah Golf, Pantai Indah Kapuk",
            "PIK Country Club, Jakarta Utara",
            "Damai Indah Golf, Jakarta",
        )
        if hit:
            lat, lng = float(hit["lat"]), float(hit["lon"])
            print(f"  -> {lat:.5f}, {lng:.5f}  (golfish={golfish(hit)})  via '{q}'")
            print(f"     osm: {hit.get('display_name','')[:160]}")
            by_id[cid]["lat"] = lat
            by_id[cid]["lng"] = lng
            by_id[cid]["coord_source"] = "nominatim_audit_fix"
        else:
            print("  -> still not found")

    # --- Damai Indah BSD ---
    cid = "damai-indah-bsd"
    if cid in by_id:
        print(f"\n[{cid}]")
        hit, q = find(
            "Damai Indah Golf BSD",
            "Damai Indah Golf, Bumi Serpong Damai",
            "Damai Indah Golf, BSD City",
            "BSD Golf, Tangerang",
        )
        if hit:
            lat, lng = float(hit["lat"]), float(hit["lon"])
            print(f"  -> {lat:.5f}, {lng:.5f}  (golfish={golfish(hit)})  via '{q}'")
            print(f"     osm: {hit.get('display_name','')[:160]}")
            by_id[cid]["lat"] = lat
            by_id[cid]["lng"] = lng
            by_id[cid]["coord_source"] = "nominatim_audit_fix"
        else:
            print("  -> still not found")

    # --- Klub Golf Bogor Raya (apply held-back, OSM hit was verified golfish) ---
    cid = "bogor-raya"
    for c in doc["courses"]:
        if "Bogor Raya" in c.get("name_en", ""):
            cid = c["id"]
            break
    if cid in by_id:
        print(f"\n[{cid}] applying held-back >5 km move")
        hit, q = find("Klub Golf Bogor Raya")
        if hit and golfish(hit):
            lat, lng = float(hit["lat"]), float(hit["lon"])
            print(f"  -> {lat:.5f}, {lng:.5f}  via '{q}'")
            print(f"     osm: {hit.get('display_name','')[:160]}")
            by_id[cid]["lat"] = lat
            by_id[cid]["lng"] = lng
            by_id[cid]["coord_source"] = "nominatim_audit_fix"

    # --- Jababeka Golf & Country Club ---
    cid = None
    for c in doc["courses"]:
        if "Jababeka" in c.get("name_en", ""):
            cid = c["id"]
            break
    if cid:
        print(f"\n[{cid}] applying held-back >5 km move")
        hit, q = find("Jababeka Golf & Country Club")
        if hit and golfish(hit):
            lat, lng = float(hit["lat"]), float(hit["lon"])
            print(f"  -> {lat:.5f}, {lng:.5f}  via '{q}'")
            print(f"     osm: {hit.get('display_name','')[:160]}")
            by_id[cid]["lat"] = lat
            by_id[cid]["lng"] = lng
            by_id[cid]["coord_source"] = "nominatim_audit_fix"

    DATA.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSaved: {DATA}")


if __name__ == "__main__":
    main()
