"""
Live source URL checker. Hits every cited URL across all data files
(financials_5y, course-level financials, fees) and reports HTTP status,
content-type, content-length. Concurrent.

Usage: python check_sources.py [--limit N]
"""
import argparse
import json
import re
import sys
import time
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).parent
DATA = ROOT / "data"
GOLF_DATA = ROOT.parent / "golf_data"

UA = "Mozilla/5.0 (Windows NT 10.0) Validator/1.0"
TIMEOUT = 12

def collect_urls():
    urls = []  # list of (url, context)

    def harvest_sources(srcs, ctx):
        for s in srcs or []:
            if isinstance(s, dict):
                u = s.get("url")
            elif isinstance(s, str):
                u = s
            else:
                continue
            if isinstance(u, str) and re.match(r"^https?://", u):
                urls.append((u, ctx))

    # 1. golf_courses.json
    fp = DATA / "golf_courses.json"
    if fp.exists():
        doc = json.loads(fp.read_text(encoding="utf-8"))
        for c in doc.get("courses", []):
            cid = c.get("id")
            if c.get("website"):
                urls.append((c["website"], f"course/{cid}/website"))
            f = c.get("fees_2026_05") or {}
            harvest_sources(f.get("sources"), f"course/{cid}/fees")
            m = c.get("membership") or {}
            harvest_sources(m.get("sources"), f"course/{cid}/membership")
            fin = c.get("financials") or {}
            harvest_sources(fin.get("sources"), f"course/{cid}/financials")
            harvest_sources(fin.get("parent_financial_sources"), f"course/{cid}/parent_fin")
            harvest_sources(fin.get("membership_sources"), f"course/{cid}/mem_sources")

    # 2. company_financials_5y.json
    fp = DATA / "company_financials_5y.json"
    if fp.exists():
        doc = json.loads(fp.read_text(encoding="utf-8"))
        for c in doc.get("companies", []):
            t = c.get("ticker")
            for yr, yd in (c.get("yearly") or {}).items():
                harvest_sources(yd.get("sources"), f"5y/{t}/{yr}")

    # 3. golf_data/*.json
    for fname in ["financials_jabodetabek.json","financials_bali_resort.json",
                  "financials_java.json","financials_outer.json",
                  "fees_jabodetabek.json","fees_bali_resort.json",
                  "fees_java.json","fees_outer.json"]:
        p = GOLF_DATA / fname
        if not p.exists(): continue
        doc = json.loads(p.read_text(encoding="utf-8"))
        items = doc if isinstance(doc, list) else doc.get("courses", doc.get("financials", doc.get("fees", [])))
        for e in items:
            cid = e.get("id")
            ns = "fin" if "financial" in fname else "fee"
            if "fees_2026_05" in e:
                harvest_sources(e["fees_2026_05"].get("sources"), f"{ns}/{cid}")
            fin = e.get("financials")
            if isinstance(fin, dict):
                harvest_sources(fin.get("sources"), f"{ns}/{cid}")

    return urls

def head(url):
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": UA, "Accept": "*/*"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return {
                "status": r.status,
                "content_type": r.getheader("Content-Type"),
                "content_length": r.getheader("Content-Length"),
            }
    except urllib.error.HTTPError as e:
        # Some servers reject HEAD; try GET with range
        if e.code in (400, 405, 403, 501):
            return get_one(url)
        return {"status": e.code, "error": str(e)}
    except urllib.error.URLError as e:
        return {"status": "ERR", "error": str(e.reason)[:80]}
    except Exception as e:
        return {"status": "ERR", "error": str(e)[:80]}

def get_one(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*", "Range": "bytes=0-1023"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return {
                "status": r.status,
                "content_type": r.getheader("Content-Type"),
                "content_length": r.getheader("Content-Length"),
            }
    except urllib.error.HTTPError as e:
        return {"status": e.code, "error": str(e)}
    except urllib.error.URLError as e:
        return {"status": "ERR", "error": str(e.reason)[:80]}
    except Exception as e:
        return {"status": "ERR", "error": str(e)[:80]}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="limit number of URLs (0=no limit)")
    ap.add_argument("--workers", type=int, default=12)
    args = ap.parse_args()

    urls = collect_urls()
    # Deduplicate while keeping first context
    seen = {}
    for u, ctx in urls:
        if u not in seen:
            seen[u] = []
        seen[u].append(ctx)
    unique = list(seen.keys())
    if args.limit:
        unique = unique[:args.limit]

    print(f"Collected {len(urls)} URL refs ({len(unique)} unique). Checking with {args.workers} workers, timeout {TIMEOUT}s...")
    print()

    results = {}
    bad = []
    start = time.time()
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        fut2url = {ex.submit(head, u): u for u in unique}
        done = 0
        for fut in as_completed(fut2url):
            u = fut2url[fut]
            try:
                r = fut.result()
            except Exception as e:
                r = {"status": "ERR", "error": str(e)[:80]}
            results[u] = r
            done += 1
            status = r.get("status")
            ok = isinstance(status, int) and 200 <= status < 400
            if not ok:
                bad.append((u, r, seen[u]))
            if done % 25 == 0:
                print(f"  ... checked {done}/{len(unique)}")
    elapsed = time.time() - start

    # Summary by status
    by_status = {}
    for u, r in results.items():
        s = r.get("status")
        by_status[s] = by_status.get(s, 0) + 1

    print()
    print("=" * 70)
    print(f"Done in {elapsed:.1f}s. Status distribution:")
    for k, v in sorted(by_status.items(), key=lambda x: str(x[0])):
        print(f"  {k}: {v}")
    print()
    print(f"BAD/SUSPECT URLs ({len(bad)}):")
    for url, r, ctxs in bad[:80]:
        ctx_short = ctxs[0] + (f" (+{len(ctxs)-1} more)" if len(ctxs)>1 else "")
        print(f"  [{r.get('status')}] {url}")
        print(f"     ctx: {ctx_short}")
        if r.get("error"):
            print(f"     err: {r['error']}")
    if len(bad) > 80:
        print(f"  ... and {len(bad)-80} more")

    # Write report JSON
    out = ROOT / "url_check_report.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump({
            "checked_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "total_refs": len(urls),
            "unique_urls": len(unique),
            "elapsed_seconds": round(elapsed, 1),
            "by_status": {str(k): v for k,v in by_status.items()},
            "bad_count": len(bad),
            "bad_urls": [{
                "url": u, "status": r.get("status"), "error": r.get("error"),
                "contexts": seen[u]
            } for u, r, _ in bad]
        }, f, ensure_ascii=False, indent=2)
    print(f"\nReport: {out}")

if __name__ == "__main__":
    main()
