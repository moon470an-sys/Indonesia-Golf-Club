"""Append Indonesian-language sources to fees_2026_05.sources.
Validates each URL is on an allowed domain (course's own + SNS only).
Stores rich metadata (snippet, date, type) under fees_2026_05.indonesian_sources."""
import json
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).parent
SRC_DIR = ROOT.parent / "golf_data"
DST = ROOT / "data" / "golf_courses.json"

ID_FILES = [
    "sources_id_jabodetabek.json",
    "sources_id_java.json",
    "sources_id_bali.json",
    "sources_id_outer.json",
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
    for k in ("courses", "entries", "results", "data"):
        if k in doc and isinstance(doc[k], list):
            return doc[k]
    return []


id_by_id = {}
for fname in ID_FILES:
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
            id_by_id[cid] = e

print(f"\nTotal Indonesian-source records: {len(id_by_id)}")

master = json.loads(DST.read_text(encoding="utf-8"))

added_courses = 0
added_urls = 0
for course in master["courses"]:
    cid = course["id"]
    info = id_by_id.get(cid)
    if not info:
        continue
    f = course.get("fees_2026_05")
    if not isinstance(f, dict):
        continue

    own_host = host_of(course.get("website"))
    id_sources = info.get("indonesian_sources") or []

    new_urls = []
    metadata = []
    existing_urls = set(f.get("sources") or [])

    for entry in id_sources:
        if not isinstance(entry, dict):
            continue
        url = entry.get("url")
        if not url or not isinstance(url, str):
            continue
        h = host_of(url)
        if not h:
            continue
        if not (h == own_host or is_sns(h)):
            continue  # skip third-party
        if url in existing_urls:
            # Still keep metadata even if URL already in sources (for snippet)
            pass
        else:
            new_urls.append(url)
            existing_urls.add(url)
        metadata.append({
            "url": url,
            "type": entry.get("type"),
            "snippet": entry.get("snippet"),
            "date": entry.get("date"),
            "language": "id",
        })

    if new_urls:
        f["sources"] = (f.get("sources") or []) + new_urls
        added_urls += len(new_urls)
        added_courses += 1
    if metadata:
        f["indonesian_sources"] = metadata

DST.write_text(json.dumps(master, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\nAdded {added_urls} Indonesian URLs across {added_courses} courses.")

# Final stats
total_sources = sum(len(c.get("fees_2026_05", {}).get("sources") or [])
                    for c in master["courses"])
courses_with_id = sum(1 for c in master["courses"]
                      if c.get("fees_2026_05", {}).get("indonesian_sources"))
print(f"Final total source URLs: {total_sources}")
print(f"Courses with Bahasa metadata: {courses_with_id}/{len(master['courses'])}")
