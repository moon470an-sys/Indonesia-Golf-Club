"""IDX e-laporan에서 XBRL 인스턴스 zip을 다운로드.

엔드포인트:
  GET https://www.idx.co.id/primary/ListedCompany/GetFinancialReport
      ?indexFrom=1&pageSize=10
      &year={YEAR}
      &reportType=rdf            # rdf = XBRL instance
      &periode={PERIOD}          # audit=감사필 연간 · tw1/tw2/tw3=분기
      &kodeEmiten={TICKER}
      &SortColumn=KodeEmiten&SortOrder=asc

응답 구조:
  { "Results": [
      { "KodeEmiten": "BSDE", "NamaEmiten": "...",
        "Attachments": [
          { "Emiten_Code": "BSDE", "File_Name": "instance.xbrl",
            "File_Path": "/staticdata/.../FinancialStatement-2024-Tahunan-BSDE.zip",
            "File_Size": 124000, "File_Type": "rdf",
            "File_Modified": "2025-03-25T12:34:56" },
          ...
        ]
      }
    ]
  }

XBRL zip은 `File_Path` 그대로 https://www.idx.co.id 에 붙이면 됨.
"""
from __future__ import annotations

import json
import os
import time
from typing import Optional
from urllib.parse import urlparse

import cloudscraper
import requests

IDX_BASE = "https://www.idx.co.id"
SEARCH_ENDPOINT = "/primary/ListedCompany/GetFinancialReport"
WARMUP_URL = "https://www.idx.co.id/en/listed-companies/financial-statements-and-annual-report/"
DEFAULT_PERIOD = "audit"  # 연간 감사필
DEFAULT_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": WARMUP_URL,
    "X-Requested-With": "XMLHttpRequest",
}


def make_session() -> "cloudscraper.CloudScraper":
    """IDX 접근용 Cloudflare-bypassing 세션 (warmup 완료)."""
    s = cloudscraper.create_scraper(
        browser={"browser": "chrome", "platform": "windows", "desktop": True}
    )
    # warmup: __cf_bm 쿠키 획득
    s.get(WARMUP_URL, timeout=60)
    return s


class IDXDownloadError(Exception):
    pass


def search_reports(
    ticker: str,
    year: int,
    period: str = DEFAULT_PERIOD,
    session: Optional[requests.Session] = None,
    timeout: float = 30.0,
) -> list[dict]:
    """ticker/year/period에 매칭되는 IDX 보고서 메타데이터 목록."""
    sess = session or make_session()
    params = {
        "indexFrom": 1,
        "pageSize": 10,
        "year": year,
        "reportType": "rdf",
        "periode": period,
        "kodeEmiten": ticker,
        "SortColumn": "KodeEmiten",
        "SortOrder": "asc",
    }
    resp = sess.get(
        IDX_BASE + SEARCH_ENDPOINT,
        params=params,
        headers=DEFAULT_HEADERS,
        timeout=timeout,
    )
    if resp.status_code != 200:
        raise IDXDownloadError(
            f"IDX search HTTP {resp.status_code} for {ticker} {year} {period}"
        )
    try:
        data = resp.json()
    except Exception as e:
        raise IDXDownloadError(f"IDX search not JSON: {e}; body={resp.text[:200]!r}")
    return data.get("Results", []) or []


def find_xbrl_attachment(reports: list[dict]) -> Optional[dict]:
    """Results에서 XBRL instance zip attachment를 찾는다.

    IDX는 보고서별로 'instance.zip' (XBRL) 과 'inlineXBRL.zip' (iXBRL HTML 포함) 두 가지를 올린다.
    instance.zip을 우선 — 가벼우면서 파싱이 단순.
    """
    instance_candidates: list[dict] = []
    inline_candidates: list[dict] = []
    for r in reports:
        for a in r.get("Attachments", []) or []:
            file_name = (a.get("File_Name") or "").lower().strip()
            file_path = (a.get("File_Path") or "").lower()
            if not (file_path.endswith(".zip") or file_name.endswith(".zip")):
                continue
            size = a.get("File_Size") or 0
            if size <= 0:
                continue
            if file_name == "instance.zip" or file_name.startswith("instance"):
                instance_candidates.append(a)
            elif "inlinexbrl" in file_name.replace(" ", "").replace("-", "").replace("_", ""):
                inline_candidates.append(a)
    # 최신 modified 우선
    instance_candidates.sort(key=lambda a: a.get("File_Modified") or "", reverse=True)
    inline_candidates.sort(key=lambda a: a.get("File_Modified") or "", reverse=True)
    if instance_candidates:
        return instance_candidates[0]
    if inline_candidates:
        return inline_candidates[0]
    return None


def download_attachment(
    attachment: dict,
    dest_path: str,
    session: Optional[requests.Session] = None,
    timeout: float = 120.0,
) -> str:
    sess = session or make_session()
    file_path = attachment.get("File_Path") or ""
    if not file_path:
        raise IDXDownloadError("attachment has no File_Path")
    if file_path.startswith("http"):
        url = file_path
    else:
        if not file_path.startswith("/"):
            file_path = "/" + file_path
        url = IDX_BASE + file_path
    resp = sess.get(url, headers=DEFAULT_HEADERS, timeout=timeout, stream=True)
    if resp.status_code != 200:
        raise IDXDownloadError(f"download HTTP {resp.status_code} url={url}")
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    with open(dest_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=64 * 1024):
            if chunk:
                f.write(chunk)
    return dest_path


def fetch_xbrl_zip(
    ticker: str,
    year: int,
    period: str = DEFAULT_PERIOD,
    cache_dir: str = "cache",
    overwrite: bool = False,
    session: Optional[requests.Session] = None,
    sleep_between: float = 1.5,
) -> Optional[str]:
    """단일 ticker에 대해 zip을 다운로드하여 캐시 경로를 반환.

    캐시 적중 시 다운로드 생략. 보고서가 없으면 None.
    """
    os.makedirs(cache_dir, exist_ok=True)
    cache_name = f"{ticker}_{year}_{period}.zip"
    cache_path = os.path.join(cache_dir, cache_name)
    if os.path.exists(cache_path) and not overwrite:
        return cache_path
    sess = session or make_session()
    reports = search_reports(ticker, year, period, session=sess)
    if not reports:
        return None
    att = find_xbrl_attachment(reports)
    if not att:
        return None
    download_attachment(att, cache_path, session=sess)
    if sleep_between > 0:
        time.sleep(sleep_between)
    return cache_path


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("ticker")
    ap.add_argument("--year", type=int, default=2024)
    ap.add_argument("--period", default=DEFAULT_PERIOD)
    ap.add_argument("--cache-dir", default="cache")
    args = ap.parse_args()
    path = fetch_xbrl_zip(
        args.ticker, args.year, args.period, cache_dir=args.cache_dir
    )
    print("downloaded:" if path else "NOT FOUND:", path or f"{args.ticker} {args.year} {args.period}")
