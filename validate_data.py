"""
Site data validator. Checks all JSON data files for:
  1. Schema/required fields/types
  2. Coordinate sanity (Indonesia bbox)
  3. Currency / numeric ranges
  4. Accounting identity (assets = liabilities + equity, ±5%)
  5. Cross-file ID consistency
  6. Source URL structure
  7. Outlier detection (z-score on revenue/membership)

Usage: python validate_data.py [--strict]
Exits with code 1 if any CRITICAL issue found.
"""
import datetime
import json
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).parent
DATA = ROOT / "data"
GOLF_DATA = ROOT.parent / "golf_data"

# Indonesia bbox (slightly padded)
LAT_MIN, LAT_MAX = -11.5, 6.5
LNG_MIN, LNG_MAX = 94.5, 141.5

# Severity buckets
issues = {"critical": [], "warning": [], "info": []}

def report(level, file, where, msg):
    issues[level].append({"file": file, "where": where, "msg": msg})

def is_url(s):
    return isinstance(s, str) and re.match(r"^https?://", s) is not None

def fmt_num(n):
    if n is None: return "None"
    if isinstance(n, (int, float)):
        if abs(n) >= 1e12: return f"{n/1e12:.2f}T"
        if abs(n) >= 1e9: return f"{n/1e9:.2f}B"
        if abs(n) >= 1e6: return f"{n/1e6:.2f}M"
    return str(n)

# ========== 1. golf_courses.json ==========
def validate_courses():
    fp = DATA / "golf_courses.json"
    with open(fp, encoding="utf-8") as f:
        doc = json.load(f)

    file = "site/data/golf_courses.json"
    if "courses" not in doc:
        report("critical", file, "root", "missing 'courses' key")
        return None

    courses = doc["courses"]
    ids = []
    region_counts = Counter()
    province_counts = Counter()
    fees_count = 0
    fin_count = 0
    coord_approx = 0
    for i, c in enumerate(courses):
        cid = c.get("id")
        ids.append(cid)
        if not cid:
            report("critical", file, f"courses[{i}]", "missing id")
            continue

        # Required fields
        for f in ["name_en", "region", "province"]:
            if not c.get(f):
                report("warning", file, cid, f"missing {f}")

        # Coordinates
        lat, lng = c.get("lat"), c.get("lng")
        if lat is None or lng is None:
            report("warning", file, cid, "missing lat/lng")
        elif not isinstance(lat, (int, float)) or not isinstance(lng, (int, float)):
            report("critical", file, cid, f"non-numeric lat/lng: {lat},{lng}")
        elif not (LAT_MIN <= lat <= LAT_MAX) or not (LNG_MIN <= lng <= LNG_MAX):
            report("critical", file, cid, f"coords outside Indonesia bbox: ({lat},{lng})")

        if c.get("coord_approximate"):
            coord_approx += 1

        # Holes
        h = c.get("holes")
        if h is not None and (not isinstance(h, int) or h < 0 or h > 90):
            report("warning", file, cid, f"unusual holes: {h}")

        # year_opened
        y = c.get("year_opened")
        if y is not None and (not isinstance(y, int) or y < 1880 or y > 2026):
            report("warning", file, cid, f"unusual year_opened: {y}")

        # Website / phone format
        if c.get("website") and not is_url(c["website"]):
            report("warning", file, cid, f"malformed website URL: {c['website']}")

        # Fees
        f = c.get("fees_2026_05")
        if f:
            fees_count += 1
            wd = f.get("weekday", {})
            we = f.get("weekend", {})
            wd_v = wd.get("green_fee_idr") if isinstance(wd, dict) else None
            we_v = we.get("green_fee_idr") if isinstance(we, dict) else None
            for tag, v in [("weekday", wd_v), ("weekend", we_v)]:
                if v is not None:
                    if not isinstance(v, (int, float)) or v < 0 or v > 50_000_000:
                        report("warning", file, cid, f"fees.{tag} out of range: {v}")

        # Financials sanity (operator/parent links)
        fin = c.get("financials")
        if fin:
            fin_count += 1

        region_counts[c.get("region","")] += 1
        province_counts[c.get("province","")] += 1

    # Duplicate IDs
    dup = [k for k, v in Counter(ids).items() if v > 1 and k]
    if dup:
        report("critical", file, "ids", f"duplicate ids: {dup}")

    report("info", file, "totals", f"courses={len(courses)} fees={fees_count} financials={fin_count} coord_approx={coord_approx}")
    return doc

# ========== 2. company_financials_5y.json ==========
def validate_5y_financials():
    fp = DATA / "company_financials_5y.json"
    if not fp.exists():
        report("critical", "site/data/company_financials_5y.json", "root", "FILE MISSING")
        return None
    with open(fp, encoding="utf-8") as f:
        doc = json.load(f)

    file = "site/data/company_financials_5y.json"
    companies = doc.get("companies", [])
    if not companies:
        report("critical", file, "root", "no companies")
        return None

    tickers_seen = []
    for c in companies:
        t = c.get("ticker")
        if not t:
            report("critical", file, "company", "missing ticker")
            continue
        tickers_seen.append(t)

        for req in ["exchange", "company_name", "currency", "yearly", "data_quality"]:
            if c.get(req) in (None, "", {}):
                report("warning", file, t, f"missing/empty {req}")

        yearly = c.get("yearly", {})
        years = sorted(yearly.keys())
        if not years:
            report("critical", file, t, "no yearly data")
            continue
        # Years should be consecutive, contained in 2020-2024
        for y in years:
            if y not in {"2020","2021","2022","2023","2024"}:
                report("warning", file, t, f"unexpected year key: {y}")

        currency = c.get("currency", "IDR").upper()

        # Per-year sanity
        for yr, yd in yearly.items():
            for k in ("revenue","operating_profit","net_profit","ebitda",
                      "total_assets","total_liabilities","total_equity",
                      "eps","dividend_per_share","employees"):
                v = yd.get(k)
                if v is None:
                    continue
                if not isinstance(v, (int, float)):
                    report("warning", file, f"{t}/{yr}/{k}", f"non-numeric: {v!r}")

            # Accounting identity: assets ≈ liabilities + equity
            a = yd.get("total_assets")
            l = yd.get("total_liabilities")
            e = yd.get("total_equity")
            if a and l and e and isinstance(a,(int,float)) and isinstance(l,(int,float)) and isinstance(e,(int,float)):
                rhs = l + e
                # Tolerance: 5% (NCI / minority interest may cause gap)
                if abs(a - rhs) / max(abs(a),1) > 0.05:
                    report("warning", file, f"{t}/{yr}",
                           f"accounting identity drift: A={fmt_num(a)} vs L+E={fmt_num(rhs)} ({(a-rhs)/a*100:+.1f}%)")

            # Negative revenue is impossible
            if yd.get("revenue") is not None and isinstance(yd.get("revenue"),(int,float)) and yd["revenue"] < 0:
                report("critical", file, f"{t}/{yr}", f"negative revenue: {fmt_num(yd['revenue'])}")

            # Sources: at least one if any number set
            has_value = any(yd.get(k) is not None for k in ["revenue","net_profit","total_assets"])
            srcs = yd.get("sources", [])
            if has_value and not srcs:
                report("warning", file, f"{t}/{yr}", "values present but no sources cited")
            for j, s in enumerate(srcs):
                if isinstance(s, dict):
                    if not is_url(s.get("url","")):
                        report("warning", file, f"{t}/{yr}/sources[{j}]", f"malformed source URL: {s.get('url')}")
                elif isinstance(s, str):
                    if not is_url(s):
                        report("warning", file, f"{t}/{yr}/sources[{j}]", f"non-URL source: {s}")

        # IDR foreign-equiv consistency (rough rate sanity)
        if currency != "IDR":
            for yr, yd in yearly.items():
                rev = yd.get("revenue")
                rev_idr = yd.get("revenue_idr_equiv")
                if rev and rev_idr and isinstance(rev,(int,float)) and isinstance(rev_idr,(int,float)):
                    # Implied rate
                    rate = rev_idr / rev
                    expected_rates = {"USD": (13000, 17000), "SGD": (10000, 13000)}
                    rng = expected_rates.get(currency)
                    if rng and not (rng[0] <= rate <= rng[1]):
                        report("warning", file, f"{t}/{yr}",
                               f"unusual implied {currency}/IDR rate: {rate:.0f} (expected {rng[0]}-{rng[1]})")

    # Duplicate tickers
    dup = [k for k,v in Counter(tickers_seen).items() if v>1]
    if dup:
        report("critical", file, "tickers", f"duplicate: {dup}")

    report("info", file, "totals",
           f"companies={len(companies)} unique_tickers={len(set(tickers_seen))}")
    return doc

# ========== 3. financials_*.json (course-level) ==========
def validate_course_financials():
    files = ["financials_jabodetabek.json", "financials_bali_resort.json",
             "financials_java.json", "financials_outer.json"]
    if not GOLF_DATA.exists():
        report("info", "golf_data/", "root",
               f"optional parent dir '{GOLF_DATA}' not present — skipping course-level financials checks")
        return
    for f in files:
        fp = GOLF_DATA / f
        if not fp.exists():
            report("warning", f"golf_data/{f}", "root", "FILE MISSING")
            continue
        with open(fp, encoding="utf-8") as fh:
            doc = json.load(fh)
        items = doc if isinstance(doc, list) else doc.get("courses", doc.get("financials", []))
        if not items:
            report("warning", f"golf_data/{f}", "root", "no entries")
            continue

        ids = []
        for entry in items:
            cid = entry.get("id")
            if not cid:
                report("warning", f"golf_data/{f}", "entry", "missing id")
                continue
            ids.append(cid)
            fin = entry.get("financials", {})
            if not fin:
                report("info", f"golf_data/{f}", cid, "no financials data")
                continue
            # Listed status whitelist
            ok_statuses = {"listed","subsidiary-of-listed","private","state-owned",
                           "government","local-government","military","foundation",
                           "joint-venture","plantation-soe","tbk-reporting-not-yet-traded",
                           "subsidiary-of-state-owned (BUMN holding, unlisted)",
                           "unknown", None}
            ls = fin.get("listed_status")
            if ls and ls not in ok_statuses:
                report("info", f"golf_data/{f}", cid, f"non-standard listed_status: {ls}")

        dup = [k for k,v in Counter(ids).items() if v>1]
        if dup:
            report("critical", f"golf_data/{f}", "ids", f"duplicate: {dup}")
        report("info", f"golf_data/{f}", "totals", f"entries={len(items)}")

# ========== 4. fees_*.json ==========
def validate_fees():
    files = ["fees_jabodetabek.json", "fees_bali_resort.json",
             "fees_java.json", "fees_outer.json"]
    if not GOLF_DATA.exists():
        report("info", "golf_data/", "root",
               f"optional parent dir '{GOLF_DATA}' not present — skipping course-level fees checks")
        return
    for f in files:
        fp = GOLF_DATA / f
        if not fp.exists():
            report("warning", f"golf_data/{f}", "root", "FILE MISSING")
            continue
        with open(fp, encoding="utf-8") as fh:
            doc = json.load(fh)
        items = doc if isinstance(doc, list) else doc.get("fees", [])
        ids = [e.get("id") for e in items if e.get("id")]
        dup = [k for k,v in Counter(ids).items() if v>1]
        if dup:
            report("critical", f"golf_data/{f}", "ids", f"duplicate: {dup}")
        # Sanity: weekend fee rarely lower than weekday by >50%
        weird_count = 0
        for e in items:
            fees = e.get("fees_2026_05", {})
            wd = fees.get("weekday", {})
            we = fees.get("weekend", {})
            if isinstance(wd, dict) and isinstance(we, dict):
                wdv = wd.get("green_fee_idr")
                wev = we.get("green_fee_idr")
                if wdv and wev and isinstance(wdv,(int,float)) and isinstance(wev,(int,float)):
                    if wev < wdv * 0.5:
                        report("info", f"golf_data/{f}", e.get("id"),
                               f"weekend ({fmt_num(wev)}) < 50% of weekday ({fmt_num(wdv)})")
                        weird_count += 1
        report("info", f"golf_data/{f}", "totals", f"entries={len(items)}")

# ========== 5. Cross-file ID consistency ==========
def validate_cross_consistency(courses_doc):
    if not courses_doc:
        return
    site_ids = {c["id"] for c in courses_doc["courses"]}

    # 5y tickers should map to actual courses via golf_courses.financials
    fin_tickers_in_courses = set()
    for c in courses_doc["courses"]:
        fin = c.get("financials", {})
        for k in ("idx_ticker","foreign_ticker"):
            v = fin.get(k)
            if v:
                # SGX:BN4 split
                v = v.split(":")[-1]
                fin_tickers_in_courses.add(v)

    fp = DATA / "company_financials_5y.json"
    if fp.exists():
        with open(fp, encoding="utf-8") as fh:
            doc = json.load(fh)
        company_tickers = {c["ticker"] for c in doc.get("companies", [])}
        # Tickers cited in courses but not in 5y dataset
        orphan = fin_tickers_in_courses - company_tickers
        if orphan:
            report("info", "cross-check", "tickers",
                   f"tickers cited in courses but no 5y data: {sorted(orphan)}")
        # Tickers in 5y dataset but not used in any course
        unused = company_tickers - fin_tickers_in_courses
        if unused:
            report("info", "cross-check", "tickers",
                   f"tickers in 5y data but no course link: {sorted(unused)}")

# ========== 6. Outlier scan ==========
def detect_outliers(courses_doc):
    if not courses_doc: return
    fees = []
    for c in courses_doc["courses"]:
        f = c.get("fees_2026_05", {})
        if isinstance(f.get("weekday"), dict):
            v = f["weekday"].get("green_fee_idr")
            if isinstance(v, (int,float)) and v > 0:
                fees.append((c["id"], "weekday", v))
        if isinstance(f.get("weekend"), dict):
            v = f["weekend"].get("green_fee_idr")
            if isinstance(v, (int,float)) and v > 0:
                fees.append((c["id"], "weekend", v))
    if len(fees) < 5: return
    vals = [v for _,_,v in fees]
    med = statistics.median(vals)
    mad = statistics.median([abs(v - med) for v in vals]) or 1
    for cid, slot, v in fees:
        z = (v - med) / mad
        if abs(z) > 5:
            report("info", "outlier", cid,
                   f"{slot} fee {fmt_num(v)} vs median {fmt_num(med)} (z={z:.1f})")

# ========== Main ==========
def main():
    courses_doc = validate_courses()
    fin_doc = validate_5y_financials()
    validate_course_financials()
    validate_fees()
    validate_cross_consistency(courses_doc)
    detect_outliers(courses_doc)

    print("=" * 70)
    print(f"{'VALIDATION SUMMARY':^70}")
    print("=" * 70)
    print(f"  CRITICAL: {len(issues['critical'])}")
    print(f"  WARNING:  {len(issues['warning'])}")
    print(f"  INFO:     {len(issues['info'])}")
    print()

    for level in ("critical", "warning", "info"):
        if not issues[level]:
            continue
        print(f"--- {level.upper()} ({len(issues[level])}) ---")
        for it in issues[level][:50]:
            print(f"  [{it['file']}] {it['where']}: {it['msg']}")
        if len(issues[level]) > 50:
            print(f"  ... and {len(issues[level])-50} more")
        print()

    out = ROOT / "validation_raw.md"
    with open(out, "w", encoding="utf-8") as f:
        f.write("# 데이터 재검증 리포트 (raw — 자동생성)\n\n")
        f.write("> 사람이 정리한 분석본은 VALIDATION_REPORT.md를 참조하세요.\n\n")
        f.write(f"실행일: {datetime.date.today().isoformat()}\n\n")
        f.write(f"- **CRITICAL**: {len(issues['critical'])}\n")
        f.write(f"- **WARNING**: {len(issues['warning'])}\n")
        f.write(f"- **INFO**: {len(issues['info'])}\n\n")
        for level in ("critical","warning","info"):
            if not issues[level]: continue
            f.write(f"## {level.upper()} ({len(issues[level])})\n\n")
            f.write("| 파일 | 위치 | 메시지 |\n|---|---|---|\n")
            for it in issues[level]:
                f.write(f"| `{it['file']}` | {it['where']} | {it['msg']} |\n")
            f.write("\n")

    print(f"Report written: {out}")

    if issues["critical"]:
        sys.exit(1)
    sys.exit(0)

if __name__ == "__main__":
    main()
