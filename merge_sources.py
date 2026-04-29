"""Replace fees_2026_05.sources with curated official-site + SNS only URLs."""
import json
import re
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).parent
SRC_DIR = ROOT.parent / "golf_data"
DST = ROOT / "data" / "golf_courses.json"

SOURCE_FILES = [
    "sources_jabodetabek.json",
    "sources_java.json",
    "sources_bali.json",
    "sources_outer.json",
]

SNS_DOMAINS = {
    'instagram.com', 'facebook.com', 'm.facebook.com', 'fb.com',
    'twitter.com', 'x.com', 'tiktok.com', 'youtube.com', 'youtu.be',
    'linkedin.com', 'threads.net', 'threads.com'
}


def host_of(url):
    if not isinstance(url, str):
        return None
    try:
        h = urlparse(url).netloc.lower()
        return h[4:] if h.startswith('www.') else h
    except Exception:
        return None


def is_sns(host):
    if not host:
        return False
    return any(host == s or host.endswith('.' + s) for s in SNS_DOMAINS)


def extract(doc):
    if isinstance(doc, list):
        return doc
    for k in ("courses", "entries", "results", "data", "sources"):
        if k in doc and isinstance(doc[k], list):
            return doc[k]
    return []


# Load sources by id
sources_by_id = {}
for fname in SOURCE_FILES:
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
            sources_by_id[cid] = e

print(f"\nTotal source records: {len(sources_by_id)}")

master = json.loads(DST.read_text(encoding="utf-8"))

courses_with_sources = 0
total_urls = 0
for course in master["courses"]:
    cid = course["id"]
    f = course.get("fees_2026_05")
    if not isinstance(f, dict):
        continue
    info = sources_by_id.get(cid)
    if not info:
        f["sources"] = f.get("sources", [])  # leave existing filtered list as-is
        continue

    own_host = host_of(course.get("website"))
    raw_sources = info.get("sources") or []
    cleaned = []
    seen = set()
    for url in raw_sources:
        if not isinstance(url, str):
            continue
        h = host_of(url)
        if not h:
            continue
        if h == own_host or is_sns(h):
            if url not in seen:
                seen.add(url)
                cleaned.append(url)

    f["sources"] = cleaned
    if cleaned:
        courses_with_sources += 1
        total_urls += len(cleaned)
    # Add status metadata
    if info.get("official_site_status"):
        f["official_site_status"] = info["official_site_status"]
    if info.get("rates_visible_on_official") is not None:
        f["rates_visible_on_official"] = info["rates_visible_on_official"]
    if info.get("rate_post_dates"):
        f["rate_post_dates"] = info["rate_post_dates"]

DST.write_text(json.dumps(master, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\nCourses with at least 1 source: {courses_with_sources}/90")
print(f"Total URLs: {total_urls}")

# Show empty source courses
empty = [c["id"] for c in master["courses"]
         if c.get("fees_2026_05") and not (c["fees_2026_05"].get("sources") or [])]
print(f"\nCourses with NO sources ({len(empty)}):")
for cid in empty:
    print(f"  - {cid}")
