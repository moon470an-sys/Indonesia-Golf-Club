"""crawl_runner.py — Phase 1 of the price-data crawl loop.

Reads data/crawl_queue.json (produced by crawl_plan.py) and visits a small,
well-defined set of robots-permissive sources to extract Indonesian green-fee
price candidates. Writes raw findings to data/crawl_log_<ts>.json.

Hard contract:
    - 1-hour wall-clock cap (asyncio.wait_for, then graceful checkpoint flush)
    - robots.txt respected per host
    - per-host concurrency = 1 with >=1.0s polite delay between requests
    - global concurrency = 5 simultaneous hosts
    - per-request timeout = 12s, max 3 retries with exponential backoff
    - resumable: writes data/crawl_state.json every 30s; honors existing file
    - reads only the priority queue, never mutates the main golf_courses.json

Output schema (data/crawl_log_<ts>.json):
    {
      "started_at": ISO8601, "finished_at": ISO8601,
      "stats": { ... },
      "results": [
        {
          "course_id": "...",
          "name_en": "...",
          "candidates": [
            { "slot": "satAm", "value_idr": 1500000, "tier": 1,
              "publisher": "Royale Jakarta Official",
              "source_url": "https://...", "fetched_at": ISO8601,
              "published_date": "2026-04-15", "raw_excerpt": "..." },
            ...
          ],
          "attempted_urls": [ {"url": "...", "status": 200, "elapsed_ms": 234} ],
          "failed_urls":    [ {"url": "...", "error": "..."} ]
        }
      ]
    }

Run AFTER crawl_plan.py. The merge step (merge_crawled.py) consumes the log
and folds candidates into fees_2026_05.source_details (a NEW field — never
touches the existing fees_2026_05.sources string array).
"""

from __future__ import annotations

import asyncio
import json
import re
import signal
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from urllib import robotparser
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
QUEUE_FILE = DATA / "crawl_queue.json"
STATE_FILE = DATA / "crawl_state.json"
FAILED_FILE = DATA / "failed_urls.json"


# ============================================================================
# Configuration
# ============================================================================

HARD_CAP_SECONDS = 3600          # 1 hour wall-clock budget
PER_HOST_DELAY = 1.0             # min seconds between hits to same host
GLOBAL_CONCURRENCY = 5           # simultaneous hosts
PER_REQ_TIMEOUT = 12.0
MAX_RETRIES = 3
USER_AGENT = (
    "Mozilla/5.0 (compatible; IGCDataResearch/1.0; "
    "+https://github.com/moon470an-sys/Indonesia-Golf-Club; "
    "research-only, robots.txt respected)"
)
CHECKPOINT_INTERVAL = 30.0       # seconds between state-file writes
PROGRESS_INTERVAL = 300.0        # 5 minutes — console progress

# Tier scoring (higher = more trusted)
TIER_DEFAULT_SCORE = 35
TIER_SCORES = {1: 95, 2: 80, 3: 65, 4: 50, 5: 35}


def host_of(url: str) -> str:
    try:
        return urlparse(url).netloc.lower().lstrip("www.")
    except Exception:
        return ""


def classify_tier(url: str, course_website: Optional[str]) -> tuple[int, str]:
    """Return (tier, publisher_label)."""
    h = host_of(url)
    cw = host_of(course_website or "")
    if cw and (h == cw or h.endswith("." + cw) or cw.endswith("." + h)):
        return 1, "Official Site"
    if "idx.co.id" in h or "ojk.go.id" in h or h.endswith(".go.id") or h.endswith(".mil.id"):
        return 2, "Government / Disclosure"
    if "apglubindonesia" in h or "aplgi" in h:
        return 2, "APLGI"
    if "qaccess.asia" in h:
        return 3, "Q-Access"
    if "gogolf" in h:
        return 3, "GoGolf"
    if "playgolf" in h:
        return 3, "playgolf.id"
    if "golfpass" in h:
        return 3, "GolfPass"
    if "golfasian" in h:
        return 3, "GolfAsian"
    if "golflux" in h:
        return 3, "GolfLux"
    if "golfsavers" in h:
        return 3, "GolfSavers"
    if "hole19" in h:
        return 3, "Hole19"
    if "traveloka" in h or "tiket.com" in h or "klook" in h or "agoda" in h or "trip.com" in h:
        return 4, "Booking Platform"
    if "archive.org" in h or "wayback" in h:
        # tier follows the wrapped URL; treat as tier-2 conservative reference
        return 2, "Wayback Archive"
    return 5, h or "unknown"


# ============================================================================
# Price extraction
# ============================================================================

# IDR amounts: "Rp 1.500.000" / "Rp1,500,000" / "IDR 1.5jt" / "1,500K"
RE_IDR_FULL = re.compile(
    r"(?:Rp\.?|IDR)\s*([0-9][0-9.,\s]{2,12})(?!\s*(?:k|K|jt|JT|M|m\b))",
    re.IGNORECASE,
)
RE_IDR_K = re.compile(r"(?:Rp\.?|IDR)\s*([0-9]{1,4}(?:[.,][0-9]{1,3})?)\s*[kK]\b")
RE_IDR_JT = re.compile(r"(?:Rp\.?|IDR)?\s*([0-9]+(?:[.,][0-9]+)?)\s*(?:jt|JT|juta)\b",
                       re.IGNORECASE)
RE_USD = re.compile(r"(?:USD|US\$|\$)\s*([0-9]{1,4}(?:[.,][0-9]{1,3})?)")

# Slot keyword maps (lowercased haystack tokens around a price)
SLOT_KEYWORDS = {
    "wdAm": ["weekday morning", "weekday am", "mon-fri am", "monday-friday morning",
             "weekdays am", "senin-jumat pagi", "weekday-am"],
    "wdPm": ["weekday afternoon", "weekday pm", "mon-fri pm", "monday-friday afternoon",
             "weekdays pm", "senin-jumat siang", "weekday-pm", "weekday twilight"],
    "satAm": ["saturday morning", "sat am", "sabtu pagi", "saturday-am", "sat-am"],
    "satPm": ["saturday afternoon", "sat pm", "sabtu siang", "saturday-pm", "sat-pm"],
    "sunAm": ["sunday morning", "sun am", "minggu pagi", "sunday-am", "sun-am"],
    "sunPm": ["sunday afternoon", "sun pm", "minggu siang", "sunday-pm", "sun-pm"],
    # generic — only used as last-resort fallback when nothing more specific matched
    "weekday": ["weekday", "weekdays", "senin-jumat", "mon-fri", "monday-friday"],
    "weekend": ["weekend", "saturday-sunday", "sat-sun", "akhir pekan",
                "sabtu-minggu", "sabtu - minggu"],
}


def normalize_idr(raw: str) -> Optional[int]:
    """Parse an IDR digit string with thousand separators ('.' or ',' or space)."""
    s = re.sub(r"[^\d]", "", raw)
    if not s or len(s) > 10:
        return None
    n = int(s)
    # Heuristic sanity: green fees in Indonesia are 100K~5M typically
    if n < 50_000 or n > 20_000_000:
        return None
    return n


def normalize_idr_jt(raw: str) -> Optional[int]:
    try:
        v = float(raw.replace(",", "."))
    except ValueError:
        return None
    n = int(v * 1_000_000)
    if n < 50_000 or n > 20_000_000:
        return None
    return n


def normalize_idr_k(raw: str) -> Optional[int]:
    try:
        v = float(raw.replace(",", "."))
    except ValueError:
        return None
    n = int(v * 1_000)
    if n < 50_000 or n > 20_000_000:
        return None
    return n


def find_prices_with_context(text: str) -> list[dict]:
    """Walk through `text` finding price matches and grabbing ±60 chars of context."""
    out = []
    for m in RE_IDR_FULL.finditer(text):
        n = normalize_idr(m.group(1))
        if n is None:
            continue
        ctx = text[max(0, m.start() - 60):m.end() + 60].lower()
        out.append({"value_idr": n, "context": ctx, "raw": m.group(0)})
    for m in RE_IDR_JT.finditer(text):
        n = normalize_idr_jt(m.group(1))
        if n is None:
            continue
        ctx = text[max(0, m.start() - 60):m.end() + 60].lower()
        out.append({"value_idr": n, "context": ctx, "raw": m.group(0)})
    for m in RE_IDR_K.finditer(text):
        n = normalize_idr_k(m.group(1))
        if n is None:
            continue
        ctx = text[max(0, m.start() - 60):m.end() + 60].lower()
        out.append({"value_idr": n, "context": ctx, "raw": m.group(0)})
    return out


def label_slot(context: str) -> Optional[str]:
    """Map a price context window to a 6-slot key, or None if unclear.

    Falls back to "weekday"/"weekend" generic markers — those will be merged
    into wdAm+wdPm (or satAm+satPm+sunAm+sunPm) at the merge step, with a
    lower confidence note.
    """
    for slot in ("wdAm", "wdPm", "satAm", "satPm", "sunAm", "sunPm"):
        for kw in SLOT_KEYWORDS[slot]:
            if kw in context:
                return slot
    for kw in SLOT_KEYWORDS["weekday"]:
        if kw in context:
            return "weekday"  # generic
    for kw in SLOT_KEYWORDS["weekend"]:
        if kw in context:
            return "weekend"  # generic
    return None


def extract_candidates_from_html(html: str, source_url: str, tier: int,
                                 publisher: str) -> list[dict]:
    """Parse fetched HTML and return a list of slot-tagged candidate entries.

    Returns empty list if no IDR amount could be confidently mapped to a slot.
    """
    try:
        soup = BeautifulSoup(html, "lxml")
    except Exception:
        soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text(separator=" ", strip=True)
    if len(text) > 200_000:
        text = text[:200_000]

    raw = find_prices_with_context(text)
    out = []
    fetched_at = datetime.now(timezone.utc).isoformat()
    for r in raw:
        slot = label_slot(r["context"])
        if slot is None:
            continue
        out.append({
            "slot": slot,
            "value_idr": r["value_idr"],
            "tier": tier,
            "publisher": publisher,
            "source_url": source_url,
            "fetched_at": fetched_at,
            "raw_excerpt": r["context"][:200],
        })
    return out


# ============================================================================
# robots.txt cache
# ============================================================================

_robots_cache: dict[str, robotparser.RobotFileParser] = {}


async def can_fetch(client: httpx.AsyncClient, url: str) -> bool:
    h = host_of(url)
    if not h:
        return False
    if h not in _robots_cache:
        rp = robotparser.RobotFileParser()
        robots_url = f"{urlparse(url).scheme}://{h}/robots.txt"
        try:
            r = await client.get(robots_url, timeout=8.0,
                                 follow_redirects=True)
            if r.status_code == 200:
                rp.parse(r.text.splitlines())
            else:
                rp.parse([])  # empty — be permissive
        except Exception:
            rp.parse([])  # empty — be permissive
        _robots_cache[h] = rp
    return _robots_cache[h].can_fetch(USER_AGENT, url)


# ============================================================================
# Per-host scheduler (1 concurrent + 1s delay)
# ============================================================================

class HostThrottle:
    def __init__(self, delay: float = PER_HOST_DELAY) -> None:
        self.delay = delay
        self._locks: dict[str, asyncio.Lock] = {}
        self._last_hit: dict[str, float] = defaultdict(lambda: 0.0)

    def lock_for(self, host: str) -> asyncio.Lock:
        if host not in self._locks:
            self._locks[host] = asyncio.Lock()
        return self._locks[host]

    async def wait_turn(self, host: str) -> None:
        async with self.lock_for(host):
            since = time.monotonic() - self._last_hit[host]
            if since < self.delay:
                await asyncio.sleep(self.delay - since)
            self._last_hit[host] = time.monotonic()


# ============================================================================
# Single-URL fetch with retries
# ============================================================================

async def fetch_one(client: httpx.AsyncClient, url: str,
                    throttle: HostThrottle) -> tuple[Optional[str], dict]:
    """Returns (html_text_or_None, attempt_log_entry).

    attempt_log_entry: {"url", "status", "elapsed_ms", "error"}
    """
    h = host_of(url)
    if not h:
        return None, {"url": url, "status": 0, "elapsed_ms": 0,
                      "error": "invalid host"}
    if not await can_fetch(client, url):
        return None, {"url": url, "status": 0, "elapsed_ms": 0,
                      "error": "robots.txt disallow"}
    last_err = None
    for attempt in range(MAX_RETRIES):
        await throttle.wait_turn(h)
        t0 = time.monotonic()
        try:
            r = await client.get(url, timeout=PER_REQ_TIMEOUT,
                                 follow_redirects=True,
                                 headers={"User-Agent": USER_AGENT,
                                          "Accept-Language": "id,en;q=0.9"})
            dt = int((time.monotonic() - t0) * 1000)
            if r.status_code in (200, 203):
                return r.text, {"url": url, "status": r.status_code,
                                "elapsed_ms": dt}
            if r.status_code in (404, 410):
                return None, {"url": url, "status": r.status_code,
                              "elapsed_ms": dt, "error": "not found"}
            last_err = f"HTTP {r.status_code}"
        except (httpx.TimeoutException, httpx.NetworkError, httpx.RemoteProtocolError) as e:
            last_err = type(e).__name__
        except Exception as e:
            last_err = f"{type(e).__name__}: {e}"
        await asyncio.sleep(min(2 ** attempt, 4))
    return None, {"url": url, "status": 0,
                  "elapsed_ms": int((time.monotonic() - t0) * 1000) if "t0" in dir() else 0,
                  "error": last_err or "unknown"}


# ============================================================================
# Course processing
# ============================================================================

async def process_course(client: httpx.AsyncClient, throttle: HostThrottle,
                         entry: dict) -> dict:
    """Process one course: fetch each seed URL, extract candidates, return result."""
    out = {
        "course_id": entry["id"],
        "name_en": entry["name_en"],
        "region": entry.get("region"),
        "priority": entry.get("priority"),
        "candidates": [],
        "attempted_urls": [],
        "failed_urls": [],
    }
    for kind, url in entry.get("seed_urls", []):
        html, log = await fetch_one(client, url, throttle)
        out["attempted_urls"].append(log)
        if html is None:
            out["failed_urls"].append({"url": url, "error": log.get("error")})
            continue
        tier, publisher = classify_tier(url, entry.get("website"))
        cands = extract_candidates_from_html(html, url, tier, publisher)
        out["candidates"].extend(cands)
    return out


# ============================================================================
# Driver
# ============================================================================

async def main_async(time_budget: float = HARD_CAP_SECONDS) -> dict:
    if not QUEUE_FILE.exists():
        print(f"ERROR: {QUEUE_FILE} not found. Run crawl_plan.py first.",
              file=sys.stderr)
        sys.exit(2)

    plan = json.loads(QUEUE_FILE.read_text(encoding="utf-8"))

    # Flatten queue in priority order, attaching priority tag
    all_entries = []
    for level in ("P0", "P1", "P2"):
        for e in plan["queue"].get(level, []):
            entry = dict(e)
            entry["priority"] = level
            all_entries.append(entry)

    # Resume support: skip already-completed course_ids in state file
    done_ids = set()
    prior_results = []
    if STATE_FILE.exists():
        try:
            st = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            done_ids = set(st.get("done_ids") or [])
            prior_results = st.get("results") or []
            print(f"[resume] found {len(done_ids)} already-completed courses")
        except Exception:
            pass
    pending = [e for e in all_entries if e["id"] not in done_ids]

    started_at = datetime.now(timezone.utc).isoformat()
    deadline = time.monotonic() + time_budget
    print(f"[{started_at}] starting crawl for {len(pending)} courses "
          f"(skipping {len(done_ids)} resumed)")

    throttle = HostThrottle()
    sem = asyncio.Semaphore(GLOBAL_CONCURRENCY)
    results = list(prior_results)
    counters = {"processed": 0, "with_candidates": 0,
                "total_candidates": 0, "failed_courses": 0}

    last_checkpoint = time.monotonic()
    last_progress = time.monotonic()

    async with httpx.AsyncClient(http2=False, headers={"User-Agent": USER_AGENT}) as client:

        async def worker(entry):
            async with sem:
                if time.monotonic() >= deadline:
                    return None
                try:
                    return await process_course(client, throttle, entry)
                except Exception as e:
                    return {
                        "course_id": entry["id"],
                        "name_en": entry["name_en"],
                        "candidates": [],
                        "attempted_urls": [],
                        "failed_urls": [{"url": "", "error": f"worker exc: {e}"}],
                    }

        # Schedule all tasks; gather as they complete
        tasks = [asyncio.create_task(worker(e)) for e in pending]
        try:
            for coro in asyncio.as_completed(tasks):
                if time.monotonic() >= deadline:
                    print("[hard cap] deadline reached, stopping launches")
                    break
                r = await coro
                if r is None:
                    continue
                results.append(r)
                done_ids.add(r["course_id"])
                counters["processed"] += 1
                if r["candidates"]:
                    counters["with_candidates"] += 1
                    counters["total_candidates"] += len(r["candidates"])
                if not r["candidates"] and r.get("failed_urls"):
                    counters["failed_courses"] += 1

                now = time.monotonic()
                if now - last_checkpoint > CHECKPOINT_INTERVAL:
                    STATE_FILE.write_text(json.dumps(
                        {"done_ids": sorted(done_ids), "results": results},
                        ensure_ascii=False, indent=1), encoding="utf-8")
                    last_checkpoint = now
                if now - last_progress > PROGRESS_INTERVAL:
                    remaining = max(0, int(deadline - now))
                    print(f"[progress] {counters['processed']}/{len(pending)} | "
                          f"with-candidates: {counters['with_candidates']} | "
                          f"total candidates: {counters['total_candidates']} | "
                          f"~{remaining // 60}m {remaining % 60}s left")
                    last_progress = now
        finally:
            # cancel any still-running tasks past the deadline
            for t in tasks:
                if not t.done():
                    t.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

    finished_at = datetime.now(timezone.utc).isoformat()

    log = {
        "started_at": started_at,
        "finished_at": finished_at,
        "stats": {
            "courses_in_queue": len(all_entries),
            "courses_attempted": counters["processed"],
            "courses_with_candidates": counters["with_candidates"],
            "candidates_total": counters["total_candidates"],
            "courses_no_findings": counters["failed_courses"],
            "resumed_from_state": len(prior_results),
        },
        "results": results,
    }

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = DATA / f"crawl_log_{ts}.json"
    log_file.write_text(json.dumps(log, ensure_ascii=False, indent=2),
                        encoding="utf-8")

    # Persist failed URLs (cumulative)
    failed_acc = {}
    if FAILED_FILE.exists():
        try:
            failed_acc = json.loads(FAILED_FILE.read_text(encoding="utf-8"))
        except Exception:
            failed_acc = {}
    for r in results:
        for fail in r.get("failed_urls", []):
            url = fail.get("url") or ""
            if not url:
                continue
            failed_acc[url] = {
                "course_id": r.get("course_id"),
                "error": fail.get("error"),
                "last_attempted": finished_at,
            }
    FAILED_FILE.write_text(json.dumps(failed_acc, ensure_ascii=False, indent=2),
                           encoding="utf-8")

    # Clear resumable state on clean finish
    if STATE_FILE.exists() and counters["processed"] >= len(pending):
        STATE_FILE.unlink()

    print()
    print("=== Crawl Complete ===")
    print(f"Log file: {log_file}")
    for k, v in log["stats"].items():
        print(f"  {k}: {v}")
    return log


def main():
    # Optional CLI: --budget <seconds>
    budget = HARD_CAP_SECONDS
    args = sys.argv[1:]
    if "--budget" in args:
        i = args.index("--budget")
        try:
            budget = int(args[i + 1])
        except (IndexError, ValueError):
            pass

    # Graceful Ctrl+C: just exit; state file is checkpointed on the way
    def _on_sig(*_):
        print("\n[signal] interrupt received — exiting (state file preserved)")
        sys.exit(130)

    if hasattr(signal, "SIGINT"):
        signal.signal(signal.SIGINT, _on_sig)

    asyncio.run(main_async(time_budget=budget))


if __name__ == "__main__":
    main()
