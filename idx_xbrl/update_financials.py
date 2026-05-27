"""IDX XBRL → company_financials_5y.json 머지 오케스트레이터.

흐름:
  1) golf_courses.json에서 unique IDX 티커 수집 (24개)
  2) 각 티커에 대해 search → instance.zip 다운로드 → parse
  3) 결과를 company_financials_5y.json의 companies[].yearly[YEAR]에 머지
       - 숫자 필드(revenue/net_profit/total_assets/total_liabilities/total_equity/eps 등)는 XBRL로 덮어쓰기
       - sources 배열에 IDX XBRL 출처를 맨 앞에 추가 (중복 시 갱신)
       - 신규 ticker는 새 company entry 생성
  4) 백업 → 새 JSON 저장
  5) 결과 리포트(logs/xbrl_update_{YYYYMMDD_HHMMSS}.json) 기록

Usage:
  python update_financials.py                # 최신 회계연도 자동, 모든 ticker
  python update_financials.py --year 2024    # 회계연도 지정
  python update_financials.py --tickers BSDE,DMIG --year 2024 --no-cache
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shutil
import sys
import time
import traceback
from typing import Optional

from download_idx import (
    IDXDownloadError,
    fetch_xbrl_zip,
    make_session,
    DEFAULT_PERIOD,
)
from parse_xbrl import parse_xbrl

HERE = os.path.dirname(os.path.abspath(__file__))
SITE_DIR = os.path.dirname(HERE)
COURSES_PATH = os.path.join(SITE_DIR, "data", "golf_courses.json")
FINANCIALS_PATH = os.path.join(SITE_DIR, "data", "company_financials_5y.json")
DEFAULT_CACHE = os.path.join(HERE, "cache")
DEFAULT_LOGS = os.path.join(HERE, "logs")

# XBRL → company.yearly[YEAR] 필드 매핑
XBRL_TO_YEAR_FIELDS = {
    "revenue": "revenue",
    "net_profit": "net_profit",
    "net_profit_total": "net_profit_total",
    "total_assets": "total_assets",
    "current_assets": "current_assets",
    "noncurrent_assets": "noncurrent_assets",
    "total_liabilities": "total_liabilities",
    "current_liabilities": "current_liabilities",
    "noncurrent_liabilities": "noncurrent_liabilities",
    "total_equity": "total_equity",
    "total_equity_parent": "total_equity_parent",
    "net_profit_nci": "non_controlling_interests_profit",
    "profit_before_tax": "profit_before_tax",
    "eps_basic": "eps",
    "eps_diluted": "eps_diluted",
    "gross_profit": "gross_profit",
    "cost_of_revenue": "cost_of_revenue",
    "ga_expenses": "ga_expenses",
    "selling_expenses": "selling_expenses",
    "finance_income": "finance_income",
    "cash_and_equivalents": "cash_and_equivalents",
    "cfo": "cfo",
    "cfi": "cfi",
    "cff": "cff",
}

# operating_profit은 GP - SG&A 로 derive
def _derive_operating_profit(year_block: dict) -> Optional[float]:
    gp = year_block.get("gross_profit")
    ga = year_block.get("ga_expenses")
    se = year_block.get("selling_expenses")
    if gp is None:
        return None
    if ga is None and se is None:
        return None
    return gp - (ga or 0) - (se or 0)


def collect_tickers(courses_path: str) -> list[str]:
    with open(courses_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    tickers: set[str] = set()
    for c in data.get("courses") or []:
        fi = c.get("financials") or {}
        t = fi.get("idx_ticker")
        if isinstance(t, str) and t.strip():
            tickers.add(t.strip().upper())
    return sorted(tickers)


def load_financials(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_financials(path: str, data: dict) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def backup_financials(path: str) -> str:
    ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = path.replace(".json", f".backup.xbrl.{ts}.json")
    shutil.copy2(path, backup)
    return backup


def find_or_create_company(financials: dict, ticker: str, entity_name: Optional[str]) -> dict:
    companies = financials.setdefault("companies", [])
    for c in companies:
        if c.get("ticker") == ticker:
            return c
    new = {
        "ticker": ticker,
        "exchange": "IDX",
        "company_name": entity_name or ticker,
        "currency": "IDR",
        "yearly": {},
        "data_quality": "xbrl_audited",
        "last_verified": dt.date.today().isoformat(),
    }
    companies.append(new)
    return new


def merge_year(
    company: dict,
    year: str,
    xbrl_year_block: dict,
    fetched_iso: str,
    period: str,
    source_file: str,
) -> dict:
    """단일 연도 블록을 머지하고 변경 통계를 반환."""
    yearly = company.setdefault("yearly", {})
    year_block = yearly.setdefault(year, {})

    changes: dict[str, dict] = {}
    for xkey, jkey in XBRL_TO_YEAR_FIELDS.items():
        new_val = xbrl_year_block.get(xkey)
        if new_val is None:
            continue
        old_val = year_block.get(jkey)
        if old_val != new_val:
            changes[jkey] = {"old": old_val, "new": new_val}
            year_block[jkey] = new_val

    # operating_profit derive (XBRL은 직접 노출 안 함)
    op = _derive_operating_profit(xbrl_year_block)
    if op is not None:
        old_op = year_block.get("operating_profit")
        if old_op != op:
            changes["operating_profit"] = {"old": old_op, "new": op}
            year_block["operating_profit"] = op

    # XBRL source 메타 (sources 배열 맨 앞에 1건만 유지)
    xbrl_src = {
        "url": f"https://www.idx.co.id/en/listed-companies/financial-statements-and-annual-report/?ticker={company.get('ticker')}",
        "title": f"{company.get('ticker')} {year} {period.upper()} XBRL Instance",
        "publisher": "IDX (Indonesia Stock Exchange)",
        "date_published": fetched_iso,
        "date_accessed": dt.date.today().isoformat(),
        "source_type": "IDX_XBRL",
        "source_file": source_file,
    }
    sources = year_block.setdefault("sources", [])
    sources[:] = [s for s in sources if s.get("source_type") != "IDX_XBRL"]
    sources.insert(0, xbrl_src)
    year_block["data_quality_year"] = "xbrl_audited"
    year_block["period_end"] = xbrl_year_block.get("period_end")

    return changes


def process_ticker(
    ticker: str,
    year: int,
    period: str,
    session,
    cache_dir: str,
    overwrite_cache: bool,
) -> dict:
    """단일 ticker에 대해 zip 다운로드 + 파싱."""
    result = {"ticker": ticker, "year": year, "period": period, "status": "pending"}
    try:
        zip_path = fetch_xbrl_zip(
            ticker, year, period,
            cache_dir=cache_dir,
            overwrite=overwrite_cache,
            session=session,
        )
        if not zip_path:
            result["status"] = "not_found"
            return result
        result["zip_path"] = zip_path
        rec = parse_xbrl(zip_path)
        result["parsed"] = rec
        result["status"] = "ok"
    except IDXDownloadError as e:
        result["status"] = "download_error"
        result["error"] = str(e)
    except Exception as e:
        result["status"] = "parse_error"
        result["error"] = str(e)
        result["traceback"] = traceback.format_exc()
    return result


def propagate_to_courses(
    courses_path: str,
    per_ticker: dict[str, dict],
    year: str,
    fetched_iso: str,
    dry_run: bool = False,
) -> dict:
    """XBRL 결과를 golf_courses.json의 course.financials에 propagate.

    렌더링 경로:
      - 재무 분석 탭은 c.financials.{revenue_idr, net_profit_idr, total_assets_idr, ...}를 읽음
      - 가격 탭 finance-col도 동일
    따라서 ticker별 최신 연도 값을 코스 financials에 미러링.
    """
    with open(courses_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    propagated: dict[str, int] = {}
    course_changes: list[dict] = []
    for c in data.get("courses") or []:
        fi = c.get("financials") or {}
        t = (fi.get("idx_ticker") or "").strip().upper()
        if not t:
            continue
        res = per_ticker.get(t)
        if not res or res.get("status") != "ok":
            continue
        rec = res.get("parsed") or {}
        years = rec.get("years") or {}
        yblock = years.get(str(year))
        if not yblock:
            continue
        new_vals = {
            "revenue_idr": yblock.get("revenue"),
            "revenue_year": int(year),
            "net_profit_idr": yblock.get("net_profit"),
            "total_assets_idr": yblock.get("total_assets"),
        }
        # operating_profit derive
        gp = yblock.get("gross_profit")
        ga = yblock.get("ga_expenses")
        se = yblock.get("selling_expenses")
        if gp is not None and (ga is not None or se is not None):
            new_vals["operating_profit_idr"] = gp - (ga or 0) - (se or 0)
        changes: dict[str, dict] = {}
        for k, v in new_vals.items():
            if v is None:
                continue
            old = fi.get(k)
            if old != v:
                changes[k] = {"old": old, "new": v}
                fi[k] = v
        # XBRL source pill (parent_financial_sources)
        if changes:
            xbrl_src = {
                "url": f"https://www.idx.co.id/en/listed-companies/financial-statements-and-annual-report/?ticker={t}",
                "title": f"{t} FY{year} IDX XBRL Instance",
                "publisher": "IDX (Indonesia Stock Exchange)",
                "date_published": fetched_iso,
                "source_type": "IDX_XBRL",
            }
            pfs = fi.setdefault("parent_financial_sources", [])
            pfs[:] = [s for s in pfs if not (isinstance(s, dict) and s.get("source_type") == "IDX_XBRL")]
            pfs.insert(0, xbrl_src)
            fi["figure_origin"] = "IDX_XBRL"
            fi["last_verified"] = dt.date.today().isoformat()
            c["financials"] = fi
            propagated[t] = propagated.get(t, 0) + 1
            course_changes.append({"id": c.get("id"), "ticker": t, "changes": changes})

    md = data.setdefault("metadata", {})
    md["last_xbrl_update"] = fetched_iso

    if not dry_run:
        tmp = courses_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, courses_path)
    return {"propagated_per_ticker": propagated, "course_changes_count": len(course_changes)}


def run(
    year: int,
    period: str = DEFAULT_PERIOD,
    tickers: Optional[list[str]] = None,
    cache_dir: str = DEFAULT_CACHE,
    overwrite_cache: bool = False,
    log_dir: str = DEFAULT_LOGS,
    dry_run: bool = False,
    courses_path: str = COURSES_PATH,
    financials_path: str = FINANCIALS_PATH,
) -> dict:
    os.makedirs(cache_dir, exist_ok=True)
    os.makedirs(log_dir, exist_ok=True)

    target_tickers = tickers if tickers else collect_tickers(courses_path)
    print(f"[plan] year={year} period={period} tickers={len(target_tickers)}: {target_tickers}")

    session = make_session()
    per_ticker: dict[str, dict] = {}
    for i, t in enumerate(target_tickers, 1):
        print(f"[{i:>2}/{len(target_tickers)}] {t} {year} {period}…", flush=True)
        per_ticker[t] = process_ticker(
            t, year, period, session=session,
            cache_dir=cache_dir, overwrite_cache=overwrite_cache,
        )
        st = per_ticker[t]["status"]
        if st == "ok":
            print(f"          → ok ({per_ticker[t].get('zip_path')})")
        else:
            err = per_ticker[t].get("error", "")
            print(f"          → {st}: {err[:100]}")
        # 폴라이트 간격
        time.sleep(0.5)

    # 머지
    financials = load_financials(financials_path)
    backup_path = backup_financials(financials_path) if not dry_run else None
    fetched_iso = dt.datetime.now().isoformat(timespec="seconds")
    merge_stats: dict[str, dict] = {}
    new_companies: list[str] = []

    for t, res in per_ticker.items():
        if res["status"] != "ok":
            merge_stats[t] = {"status": res["status"], "error": res.get("error")}
            continue
        rec = res["parsed"]
        existed = any(c.get("ticker") == t for c in financials.get("companies", []))
        company = find_or_create_company(financials, t, rec.get("entity_name"))
        if not existed:
            new_companies.append(t)
        year_changes: dict[str, dict] = {}
        for y, yblock in rec.get("years", {}).items():
            ch = merge_year(
                company, y, yblock,
                fetched_iso=fetched_iso,
                period=res["period"],
                source_file=os.path.basename(res.get("zip_path") or ""),
            )
            if ch:
                year_changes[y] = ch
        company["last_verified"] = dt.date.today().isoformat()
        merge_stats[t] = {
            "status": "merged",
            "years_updated": list(year_changes.keys()),
            "field_changes": year_changes,
        }

    # metadata 업데이트
    md = financials.setdefault("metadata", {})
    passes = md.setdefault("xbrl_passes", [])
    passes.append({
        "fetched_at": fetched_iso,
        "year": year,
        "period": period,
        "tickers_attempted": target_tickers,
        "tickers_ok": [t for t, r in per_ticker.items() if r["status"] == "ok"],
        "tickers_failed": [
            {"ticker": t, "status": r["status"], "error": r.get("error")}
            for t, r in per_ticker.items() if r["status"] != "ok"
        ],
        "new_companies_added": new_companies,
    })
    md["last_xbrl_update"] = fetched_iso

    if dry_run:
        print(f"[dry-run] would save to {financials_path}; backup would be {backup_path}")
    else:
        save_financials(financials_path, financials)
        print(f"[save] {financials_path} (backup: {backup_path})")

    # Propagate to golf_courses.json so UI (finance table + price tab finance-col)
    # reads XBRL values directly from c.financials.
    prop_stats = propagate_to_courses(
        courses_path,
        per_ticker,
        year=str(year),
        fetched_iso=fetched_iso,
        dry_run=dry_run,
    )
    print(f"[propagate] courses updated: {prop_stats}")

    # 로그 작성
    ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = os.path.join(log_dir, f"xbrl_update_{ts}.json")
    log = {
        "started_at": fetched_iso,
        "year": year,
        "period": period,
        "target_tickers": target_tickers,
        "per_ticker": {
            t: {
                "status": r["status"],
                "zip_path": r.get("zip_path"),
                "error": r.get("error"),
                "years": list((r.get("parsed") or {}).get("years", {}).keys()),
            }
            for t, r in per_ticker.items()
        },
        "merge_stats": merge_stats,
        "backup_path": backup_path,
        "new_companies": new_companies,
        "propagation": prop_stats,
    }
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2, default=str)
    print(f"[log] {log_path}")

    # 요약
    ok = sum(1 for r in per_ticker.values() if r["status"] == "ok")
    print(f"[done] {ok}/{len(target_tickers)} merged; new={new_companies}")
    return log


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int, default=None, help="회계연도 (기본: 작년)")
    ap.add_argument("--period", default=DEFAULT_PERIOD, help="audit/tw1/tw2/tw3")
    ap.add_argument("--tickers", default=None, help="콤마구분 ticker 리스트 (생략 시 전체)")
    ap.add_argument("--cache-dir", default=DEFAULT_CACHE)
    ap.add_argument("--log-dir", default=DEFAULT_LOGS)
    ap.add_argument("--no-cache", action="store_true", help="기존 zip 무시하고 재다운로드")
    ap.add_argument("--dry-run", action="store_true", help="JSON 저장 안 함")
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    year = args.year if args.year else dt.date.today().year - 1
    tickers = [t.strip().upper() for t in args.tickers.split(",")] if args.tickers else None
    run(
        year=year,
        period=args.period,
        tickers=tickers,
        cache_dir=args.cache_dir,
        overwrite_cache=args.no_cache,
        log_dir=args.log_dir,
        dry_run=args.dry_run,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
