"""Fill remaining null coordinates with city-center approximations."""
import json
from pathlib import Path

ROOT = Path(__file__).parent
DATA = ROOT / "data" / "golf_courses.json"

CITY_COORDS = {
    "Medan": (3.5952, 98.6722),
    "Pekanbaru": (0.5071, 101.4478),
    "Palembang": (-2.9909, 104.7565),
    "Balikpapan": (-1.2654, 116.8312),
    "Bontang": (0.1340, 117.4858),
    "Samarinda": (-0.5022, 117.1536),
    "Palangkaraya": (-2.2128, 113.9135),
    "Banjarmasin": (-3.4423, 114.8347),
    "Pontianak": (-0.0263, 109.3425),
    "Makassar": (-5.1477, 119.4327),
    "Manado": (1.4748, 124.8421),
    "Sorowako": (-2.5839, 121.3618),
    "Palu": (-0.9003, 119.8779),
    "Kendari": (-3.9778, 122.5170),
    "Jayapura": (-2.5337, 140.7181),
    "Timika": (-4.5285, 136.8855),
    "Ambon": (-3.6954, 128.1814),
    "Tanjung Enim": (-3.7239, 103.7714),
    "Bandar Lampung": (-5.4297, 105.2616),
    "Sumbawa": (-8.7333, 117.4167),
}

doc = json.loads(DATA.read_text(encoding="utf-8"))
filled = 0
for c in doc["courses"]:
    if c.get("lat") is None:
        coord = CITY_COORDS.get(c.get("region"))
        if coord:
            c["lat"], c["lng"] = coord
            c["coord_approximate"] = True
            filled += 1
            print(f"  filled {c['name_en']} -> {coord} (city: {c['region']})")

DATA.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
total_with_coords = sum(1 for c in doc["courses"] if c.get("lat") is not None)
print(f"\nFilled {filled} more. Total with coords: {total_with_coords}/{len(doc['courses'])}")
