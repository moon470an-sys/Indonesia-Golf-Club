"""
Fill missing lat/lng using Nominatim (OpenStreetMap free geocoder).
Usage: python geocode.py
- Reads ../golf_data/golf_courses.json
- Writes ./data/golf_courses.json (with filled coordinates)
- Respects Nominatim usage policy: 1 req/sec, custom User-Agent
"""
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).parent
SRC = ROOT.parent / "golf_data" / "golf_courses.json"
DST = ROOT / "data" / "golf_courses.json"

USER_AGENT = "IndonesiaGolfClubMap/1.0 (moon470an@gmail.com)"
NOMINATIM = "https://nominatim.openstreetmap.org/search"


def geocode(query: str):
    params = urllib.parse.urlencode({
        "q": query,
        "format": "json",
        "limit": 1,
        "countrycodes": "id",
    })
    req = urllib.request.Request(
        f"{NOMINATIM}?{params}",
        headers={"User-Agent": USER_AGENT},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data:
                return float(data[0]["lat"]), float(data[0]["lon"])
    except Exception as e:
        print(f"   ! error: {e}")
    return None, None


def main():
    src = json.loads(SRC.read_text(encoding="utf-8"))
    courses = src["courses"]
    missing = [c for c in courses if c.get("lat") is None or c.get("lng") is None]
    print(f"Total: {len(courses)} | Missing coords: {len(missing)}")

    for i, c in enumerate(missing, 1):
        # Try multiple query strategies
        queries = [
            c.get("address"),
            f'{c["name_en"]}, {c["region"]}, Indonesia',
            f'{c["name_en"]}, Indonesia',
        ]
        queries = [q for q in queries if q]

        lat = lng = None
        for q in queries:
            print(f"[{i}/{len(missing)}] {c['name_en']}: trying '{q[:80]}...'")
            lat, lng = geocode(q)
            time.sleep(1.1)  # Nominatim policy: max 1 req/sec
            if lat is not None:
                print(f"   -> {lat:.5f}, {lng:.5f}")
                break

        if lat is not None:
            c["lat"] = lat
            c["lng"] = lng
        else:
            print(f"   -> not found, leaving null")

    src["metadata"]["last_updated"] = "2026-04-29"
    src["metadata"]["geocoding"] = "Nominatim (OpenStreetMap)"
    DST.parent.mkdir(parents=True, exist_ok=True)
    DST.write_text(json.dumps(src, ensure_ascii=False, indent=2), encoding="utf-8")
    filled = sum(1 for c in courses if c.get("lat") is not None)
    print(f"\nDone. {filled}/{len(courses)} courses now have coordinates.")
    print(f"Saved to: {DST}")


if __name__ == "__main__":
    main()
