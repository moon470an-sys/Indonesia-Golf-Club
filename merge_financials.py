"""Merge financials_*.json into site/data/golf_courses.json (and refresh fees)."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).parent
SRC_DIR = ROOT.parent / "golf_data"
DST = ROOT / "data" / "golf_courses.json"

FIN_FILES = [
    "financials_jabodetabek.json",
    "financials_java.json",
    "financials_bali_resort.json",
    "financials_outer.json",
]

# Financials-id -> site-id mapping (built from name + heuristic)
# Site uses shorter/older IDs; financials uses fuller names.
ID_MAP = {
    # Jabodetabek
    "pondok-indah-golf-course": "pondok-indah-golf",
    "senayan-national-golf-club": "senayan-national",
    "cengkareng-golf-club": "cengkareng-golf",
    "modern-golf-country-club": "modern-golf",
    "gading-raya-padang-golf": "gading-raya",
    "matoa-nasional-golf": "matoa-nasional",
    "damai-indah-golf-pik": "damai-indah-pik",
    "imperial-klub-golf": "imperial-klub",
    "emeralda-golf-club": "emeralda-golf",
    "gunung-geulis-country-club": "gunung-geulis",
    "sentul-highlands-golf-club": "sentul-highlands",
    "rainbow-hills-golf-club": "rainbow-hills",
    "klub-golf-bogor-raya": "bogor-raya",
    "permata-sentul-golf": "permata-sentul",
    "riverside-golf-club-cibubur": "riverside-cibubur",
    "cimanggis-golf-estate": "cimanggis-golf",
    "rancamaya-golf-country-club": "rancamaya",
    "jababeka-golf-country-club": "jababeka-golf",
    "trump-international-golf-club-lido": "trump-lido",
    "royale-jakarta-golf-club": "royale-jakarta",
    # Java
    "parahyangan-golf-bandung": "parahyangan-bandung",
    "mountain-view-golf-bandung": "mountain-view-bandung",
    "jatinangor-national-golf": "jatinangor-national",
    "tirtayasa-golf-bandung": "tirtayasa-bandung",
    "ciater-highland-golf": "ciater-highland",
    "padalarang-golf": "padalarang-golf",
    "merapi-golf-yogyakarta": "merapi-yogya",
    "yogyakarta-golf-club": "yogyakarta-gc",
    "padang-golf-adisutjipto": "adisutjipto-yogya",
    "borobudur-international-golf": "borobudur-magelang",
    "gombel-golf-semarang": "gombel-semarang",
    "candi-golf-semarang": "candi-semarang",
    "ciputra-golf-surabaya": "ciputra-surabaya",
    "bukit-darmo-golf": "bukit-darmo-surabaya",
    "finna-golf-pasuruan": "finna-pasuruan",
    "graha-famili-golf": "graha-famili",
    "taman-dayu-golf": "taman-dayu",
    "araya-golf-malang": "araya-malang",
    "jember-golf-glantangan": "jember-glantangan",
    "singosari-golf-malang": "singosari-malang",
    "lombok-kosaido-sire-beach": "lombok-sire-beach",
    # Bali / Bintan / Batam
    "gec-rinjani-lombok": "gec-rinjani",
    "kaleang-naia-sumbawa": "kaleang-sumbawa",
    "laguna-golf-bintan": "laguna-bintan",
    # Sumatra
    "royal-sumatra-golf": "royal-sumatra",
    "tamora-golf-club": "tamora-medan",
    "graha-metropolitan-golf": "graha-metropolitan-medan",
    "bukit-barisan-country-club": "bukit-barisan-medan",
    "pekanbaru-rumbai-gc": "rumbai-pekanbaru",
    "labersa-golf-riau": "labersa-riau",
    "palembang-golf-club": "palembang-gc",
    "bukit-asam-golf": "bukit-asam",
    # Kalimantan
    "pertamina-balikpapan-gc": "pertamina-balikpapan",
    "karang-joang-gcc": "karang-joang",
    "bukit-sintuk-bintang-bontang": "bintang-sintuk-bontang",
    "mahulu-golf": "mahulu-samarinda",
    "alam-khatulistiwa-pontianak": "alam-khatulistiwa",
    # Sulawesi / Maluku / Papua
    "padang-golf-baddoka-makassar": "padang-golf-baddoka",
    "akr-grand-kawanua-manado": "akr-grand-kawanua",
    "sorowako-golf-club": "sorowako-gc",
}


def extract_entries(doc):
    if isinstance(doc, list):
        return doc
    for k in ("courses", "financials", "data", "entries"):
        if k in doc and isinstance(doc[k], list):
            return doc[k]
    return []


def slugify(name):
    s = name.lower()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_-]+", "-", s).strip("-")
    return s


def main():
    master = json.loads(DST.read_text(encoding="utf-8"))
    site_ids = {c["id"]: c for c in master["courses"]}
    site_name_to_id = {slugify(c["name_en"]): c["id"] for c in master["courses"]}

    # Load all financials
    fin_by_finid = {}
    for fname in FIN_FILES:
        p = SRC_DIR / fname
        if not p.exists():
            print(f"!! missing: {fname}")
            continue
        doc = json.loads(p.read_text(encoding="utf-8"))
        for e in extract_entries(doc):
            fid = e.get("id")
            if not fid:
                continue
            fin_by_finid[fid] = e.get("financials", {})

    print(f"Loaded {len(fin_by_finid)} financials records")

    # Match to site IDs
    matched = 0
    unmatched = []
    for finid, fin in fin_by_finid.items():
        # 1) direct
        if finid in site_ids:
            site_ids[finid]["financials"] = fin
            matched += 1
            continue
        # 2) explicit map
        if finid in ID_MAP and ID_MAP[finid] in site_ids:
            site_ids[ID_MAP[finid]]["financials"] = fin
            matched += 1
            continue
        unmatched.append(finid)

    print(f"Matched financials to {matched}/{len(fin_by_finid)} courses.")
    if unmatched:
        print("\nUnmatched financials IDs:")
        for u in unmatched:
            print(f"  - {u}")

    master["metadata"]["financials_added"] = "2026-05-01"
    master["metadata"]["financials_matched"] = matched

    DST.write_text(json.dumps(master, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\nWrote", DST)


if __name__ == "__main__":
    main()
