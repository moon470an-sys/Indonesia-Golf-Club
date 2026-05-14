"""Build the Pure-play 골프장 운영 비교 site as a single static index.html.

All data is read from raw_peer_data/*.csv at build time and embedded directly
into the HTML. The rendered page makes ZERO runtime fetch() calls — the prior
site failed because async JSON loading hung. JS is reserved for tab switching
and table sorting only.

Run:
    python _build.py

Output:
    index.html (sibling file)
"""
from __future__ import annotations

import csv
import datetime as dt
import html
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA_DIR = HERE.parent.parent.parent / "raw_peer_data"
OPS_NOTES_DIR = HERE.parent / "operations" / "data"
OPS_EVIDENCE_DIR = HERE.parent.parent.parent / "raw_peer_data" / "operations" / "evidence"

# Tier-A "Pure-play" peers we deep-compare in main tabs
PUREPLAY = ["DMIG", "PIPG", "KPIG"]
# Reference peers (incl. MKPI as PIPG parent context)
REFERENCE = ["MKPI", "BSDE", "DILD", "GOLF", "MDLN", "SMRA", "SMDM", "KIJA", "BKDP", "BKSL"]

# Supplementary numbers not in the curated CSV (extracted from operating_signals.notes
# text or annual report excerpts). Hard-coded so the build is reproducible.
SUPPLEMENT = {
    "DMIG": {
        "revenue_h1_2024_idr": 122_300_000_000,  # H1 audited per operating_signals notes
        "revenue_caveat": "FY 전체 미공시 (H1만 audited)",
    },
    "KPIG": {
        "golf_segment_2024_idr": 7_360_000_000,  # First-year golf membership only (related-party heavy)
        "golf_caveat": "회원제 전용 · 2023년말 개장 · 관계사 거래 비중 높음",
    },
    "PIPG": {
        # Full FY available in curated CSV — no supplement needed
    },
}

# Tier label for reference table (per peer_inventory.csv tier_hint)
TIER_LABEL = {
    "DMIG": "Pure-play",
    "PIPG": "Pure-play",
    "KPIG": "Resort/Lifestyle",
    "MKPI": "Township (PIPG 모회사)",
    "BSDE": "Township",
    "DILD": "Diversified Property",
    "GOLF": "Golf-Resort",
    "MDLN": "Diversified Property",
    "SMRA": "Township",
    "SMDM": "Diversified Property",
    "KIJA": "Industrial Estate",
    "BKDP": "Property (소형)",
    "BKSL": "Township",
}


# ─────────────────────────────────────────────────────────────────────────────
# CSV loading
# ─────────────────────────────────────────────────────────────────────────────

def load_csv(name: str) -> list[dict]:
    path = DATA_DIR / name
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


COURSE_FACTS = load_csv("peer_course_facts.csv")
MEMBERSHIP = load_csv("peer_membership.csv")
PRICING = load_csv("peer_pricing.csv")
OPERATING = load_csv("peer_operating_signals.csv")
FINANCIALS = load_csv("peer_financials_curated.csv")
INVENTORY = load_csv("peer_inventory.csv")


def load_notes(ticker: str) -> dict:
    """Load `operations/data/{ticker}_notes.json` if present (lower-case file name)."""
    p = OPS_NOTES_DIR / f"{ticker.lower()}_notes.json"
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


NOTES = {t: load_notes(t) for t in ["DMIG", "PIPG", "KPIG", "MDLN", "GOLF", "KIJA", "SMDM", "BSDE", "SMRA"]}


def by_ticker(rows: list[dict], ticker: str) -> list[dict]:
    return [r for r in rows if r.get("ticker") == ticker]


def first_by_ticker(rows: list[dict], ticker: str) -> dict | None:
    rs = by_ticker(rows, ticker)
    return rs[0] if rs else None


def first_inventory(ticker: str) -> dict | None:
    for r in INVENTORY:
        if r.get("ticker") == ticker:
            return r
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Formatters
# ─────────────────────────────────────────────────────────────────────────────

def fmt_idr(v) -> str:
    """Format IDR value into 'XXX bn' / 'X.XX tn' with proper unit."""
    if v in (None, "", "N/A"):
        return '<span class="na">N/A</span>'
    try:
        n = float(v)
    except (TypeError, ValueError):
        return f'<span class="na">{html.escape(str(v))}</span>'
    if n >= 1e12:
        return f'{n / 1e12:,.2f}<span class="u">조 IDR</span>'
    if n >= 1e9:
        return f'{n / 1e9:,.1f}<span class="u">10억 IDR</span>'
    if n >= 1e6:
        return f'{n / 1e6:,.1f}<span class="u">백만 IDR</span>'
    return f'{n:,.0f}<span class="u">IDR</span>'


def fmt_idr_compact(v) -> str:
    """Inline IDR formatter for table cells (no <span> wrapper, just unit suffix)."""
    if v in (None, "", "N/A"):
        return "N/A"
    try:
        n = float(v)
    except (TypeError, ValueError):
        return str(v)
    if n >= 1e12:
        return f"{n / 1e12:,.2f}조"
    if n >= 1e9:
        return f"{n / 1e9:,.1f}bn"
    if n >= 1e6:
        return f"{n / 1e6:,.1f}M"
    return f"{n:,.0f}"


def na_or(v, transform=None) -> str:
    if v in (None, "", "N/A"):
        return '<span class="na">N/A</span>'
    return html.escape(str(transform(v) if transform else v))


def safe(s) -> str:
    return html.escape(str(s)) if s is not None else ""


# ─────────────────────────────────────────────────────────────────────────────
# Section: Overview
# ─────────────────────────────────────────────────────────────────────────────

def courses_for(ticker: str) -> list[dict]:
    return [r for r in COURSE_FACTS if r.get("ticker") == ticker and r.get("holes") not in ("N/A", "", None)]


def total_holes(ticker: str) -> int:
    n = 0
    for c in courses_for(ticker):
        try:
            n += int(c["holes"])
        except (KeyError, ValueError, TypeError):
            pass
    return n


def overview_card(ticker: str) -> str:
    inv = first_inventory(ticker) or {}
    fin_rows = by_ticker(FINANCIALS, ticker)
    fin = next((f for f in fin_rows if f.get("revenue_idr") not in ("", None)), fin_rows[0] if fin_rows else {})
    courses = courses_for(ticker)
    course_count = len(courses)
    holes = total_holes(ticker)
    parent = inv.get("parent_group", "") or fin.get("parent_entity", "")
    region = inv.get("region", "")

    is_caveat = ticker == "KPIG"
    ticker_class = "ticker warn" if is_caveat else "ticker"

    # Revenue display: prefer entity revenue; fall back to supplement
    rev_html: str
    rev_label: str
    sup = SUPPLEMENT.get(ticker, {})
    if ticker == "DMIG":
        rev_label = "FY24 H1 매출 (audited)"
        rev_html = fmt_idr(sup.get("revenue_h1_2024_idr"))
    elif ticker == "KPIG":
        rev_label = "FY24 골프 매출"
        rev_html = fmt_idr(sup.get("golf_segment_2024_idr"))
    else:
        rev_label = "FY24 매출 (entity)"
        rev_html = fmt_idr(fin.get("revenue_idr"))

    profit_label = "FY24 H1 순이익" if ticker == "DMIG" else "FY24 순이익"
    if ticker == "DMIG":
        # DMIG H1 net profit not in curated CSV; mark N/A explicitly
        profit_html = '<span class="na">N/A (H1 미공개)</span>'
    elif ticker == "KPIG":
        profit_label = "FY24 모회사 순이익"
        profit_html = fmt_idr(fin.get("net_profit_idr"))
    else:
        profit_html = fmt_idr(fin.get("net_profit_idr"))

    if ticker == "KPIG":
        assets_label = "총자산 (모회사 연결)"
    else:
        assets_label = "총자산 (entity)"
    assets_html = fmt_idr(fin.get("total_assets_idr"))

    badge = ""
    if ticker == "KPIG":
        badge = ' <span class="pill pill-rsr">Resort · Members-only</span>'
    elif ticker in ("DMIG", "PIPG"):
        badge = ' <span class="pill pill-pp">Pure-play</span>'

    return f"""<div class="peer-card">
  <div class="top">
    <span class="{ticker_class}">{safe(ticker)}</span>
    <span class="pname">{safe(parent or '—')}</span>
    {badge}
  </div>
  <div class="pmeta">{safe(region or '—')} · 골프장 {course_count}개 · 총 {holes}홀</div>
  <dl>
    <dt>{rev_label}</dt><dd>{rev_html}</dd>
    <dt>{profit_label}</dt><dd>{profit_html}</dd>
    <dt>{assets_label}</dt><dd>{assets_html}</dd>
  </dl>
</div>"""


def section_overview() -> str:
    cards = "\n".join(overview_card(t) for t in PUREPLAY)
    kpig_caveat = """<div class="banner">
    <strong>주의 — KPIG (Trump Lido):</strong>
    회원제 전용 · 2023년말 개장 1년차 · FY2024 골프 매출 IDR 7.36bn은 first-year membership 매출로 관계사 거래 비중이 큼.
    Green fee 미공시 (members-only). 운영 시계열·단가 비교는 DMIG/PIPG 중심으로 해석할 것.
  </div>"""

    dmig_caveat = """<div class="banner info">
    <strong>참고 — DMIG:</strong> FY2024 전체 결산 미공시. H1 audited 수치만 공개됨 (IDR 122.3bn). 비교 시 PIPG의 연간 수치와 직접 비교 불가.
  </div>"""

    return f"""<section class="panel" data-panel="overview">
  <div class="hero">
    <div class="wrap">
      <div class="eyebrow">Pure-play 1:1·1·1 비교</div>
      <h1>골프장 운영 관리 — Pure-play Peer Group 종합</h1>
      <p class="lede">
        인도네시아 IDX 상장 13개 peer 중 골프장 직접 운영 비중이 의미 있는
        <strong>3개</strong>(DMIG · PIPG · KPIG)를 동일 기준으로 비교합니다.
        나머지 10개(MKPI 포함)는 <em>참고 탭</em>에서 요약합니다.
      </p>
    </div>
  </div>

  <div class="wrap">
    <div class="section">
      <h2>FY2024 핵심 KPI</h2>
      <h3>3-peer Head-to-Head</h3>
      <p class="lede">매출·순이익·총자산을 entity 기준으로 표시. 단위는 IDR. 미공시는 N/A로 표기 (추정 없음).</p>
      <div class="peer-grid">
        {cards}
      </div>
      {kpig_caveat}
      {dmig_caveat}
    </div>

    <div class="section">
      <h2>골프장 운영 자산 비교</h2>
      <h3>코스 수 · 총 홀 수 · 운영 형태</h3>
      <div class="tbl-card">
        <table class="tbl">
          <thead>
            <tr>
              <th>Peer</th>
              <th>운영사 (Entity)</th>
              <th>지역</th>
              <th class="num">코스 수</th>
              <th class="num">총 홀</th>
              <th>운영 형태</th>
            </tr>
          </thead>
          <tbody>
            {''.join(_overview_row(t) for t in PUREPLAY)}
          </tbody>
        </table>
      </div>

      <div class="src-block">
        <strong>출처:</strong>
        peer_financials_curated.csv (FY2024 audited),
        peer_course_facts.csv,
        peer_inventory.csv,
        peer_operating_signals.csv (보충 텍스트).
      </div>
    </div>
  </div>
</section>"""


def _overview_row(ticker: str) -> str:
    inv = first_inventory(ticker) or {}
    fin_rows = by_ticker(FINANCIALS, ticker)
    fin = next((f for f in fin_rows if f.get("parent_entity")), fin_rows[0] if fin_rows else {})
    courses = courses_for(ticker)
    region = inv.get("region", "")
    if ticker == "KPIG":
        op_form = "Members-only private (USD 70k Platinum)"
    elif ticker == "PIPG":
        op_form = "Public/Member (5분 CBD 접근)"
    elif ticker == "DMIG":
        op_form = "Public/Member (PTM + Share)"
    else:
        op_form = "—"
    return f"""<tr class="tier-a">
  <td><span class="ticker-mini">{safe(ticker)}</span></td>
  <td>{safe(fin.get('parent_entity', '—'))}</td>
  <td>{safe(region or '—')}</td>
  <td class="num">{len(courses)}</td>
  <td class="num">{total_holes(ticker)}</td>
  <td>{safe(op_form)}</td>
</tr>"""


# ─────────────────────────────────────────────────────────────────────────────
# Section: Course / Infra
# ─────────────────────────────────────────────────────────────────────────────

def section_course() -> str:
    rows = []
    for t in PUREPLAY:
        for c in courses_for(t):
            link = c.get("website") or ""
            link_html = f'<a href="{safe(link)}" target="_blank" rel="noopener">{safe(c.get("course_name", ""))}</a>' if link and link != "N/A" else safe(c.get("course_name", ""))
            facilities = c.get("facilities_summary", "")
            rows.append(f"""<tr class="tier-a">
  <td><span class="ticker-mini">{safe(t)}</span></td>
  <td class="peer-cell">{link_html}<span class="sub">{safe(c.get('region', ''))}</span></td>
  <td>{safe(c.get('designer', '—'))}</td>
  <td class="num">{safe(c.get('year_opened', '—'))}</td>
  <td class="num">{safe(c.get('holes', '—'))} / {safe(c.get('par', '—'))}</td>
  <td class="num">{safe(c.get('facilities_count', '—'))}</td>
  <td class="notes">{safe(facilities)}</td>
</tr>""")

    return f"""<section class="panel" data-panel="course">
  <div class="wrap">
    <div class="section">
      <h2>코스·인프라</h2>
      <h3>4개 코스의 사양·설계자·시설 비교</h3>
      <p class="lede">
        Pure-play 3개 peer가 운영하는 <strong>4개 코스</strong>(DMIG 2 + KPIG 1 + PIPG 1).
        설계자·개장연도·시설 수로 코스의 정체성과 노후도를 가늠합니다.
      </p>
      <div class="tbl-card">
        <table class="tbl">
          <thead>
            <tr>
              <th>Peer</th>
              <th>코스명 · 지역</th>
              <th>설계자</th>
              <th class="num">개장</th>
              <th class="num">홀 / Par</th>
              <th class="num">시설 수</th>
              <th>주요 부대시설</th>
            </tr>
          </thead>
          <tbody>{''.join(rows)}</tbody>
        </table>
      </div>

      <div class="banner info">
        <strong>관전 포인트:</strong>
        PIPG (1976년 개장) — 4개 중 가장 오래된 championship 코스, RTJ Jr. 설계 ·
        DMIG BSD (1992) — 인도네시아 최초 Jack Nicklaus 코스 ·
        KPIG Trump Lido (2023) — 4개 중 유일한 신규 / Ernie Els 설계, 600m 고원 입지.
      </div>

      <div class="src-block">
        <strong>출처:</strong> peer_course_facts.csv (라스트 검증 2026-04-29 ~ 2026-05-07).
      </div>
    </div>
  </div>
</section>"""


# ─────────────────────────────────────────────────────────────────────────────
# Section: Pricing / Membership
# ─────────────────────────────────────────────────────────────────────────────

SLOTS = [("wdAm", "평일 오전"), ("wdPm", "평일 오후"), ("satAm", "토 오전"),
         ("satPm", "토 오후"), ("sunAm", "일 오전"), ("sunPm", "일 오후")]


def pricing_for(course_id: str, slot: str) -> dict | None:
    for r in PRICING:
        if r.get("course_id") == course_id and r.get("slot") == slot:
            return r
    return None


def section_pricing() -> str:
    # Pricing table — 4 courses x 6 slots
    pricing_rows = []
    for t in PUREPLAY:
        for c in courses_for(t):
            cid = c["course_id"]
            cells = []
            for slot_key, _ in SLOTS:
                p = pricing_for(cid, slot_key)
                v = p.get("green_fee_value") if p else None
                cells.append(f'<td class="num">{fmt_idr_compact(v)}</td>')
            pricing_rows.append(f"""<tr class="tier-a">
  <td><span class="ticker-mini">{safe(t)}</span></td>
  <td class="peer-cell">{safe(c.get('course_name', ''))}<span class="sub">{safe(c.get('region', ''))}</span></td>
  {''.join(cells)}
</tr>""")

    pricing_header = "".join(f'<th class="num">{label}</th>' for _, label in SLOTS)

    # Membership table
    mem_rows = []
    for t in PUREPLAY:
        for m in by_ticker(MEMBERSHIP, t):
            price_idr = m.get("membership_price_idr", "N/A")
            price_usd = m.get("membership_price_usd", "")
            price_disp = "N/A"
            if price_idr and price_idr != "N/A":
                price_disp = fmt_idr_compact(price_idr)
            elif price_usd and price_usd != "N/A":
                price_disp = f"USD {int(float(price_usd)):,}"
            tiers = m.get("membership_tiers_disclosed", "")
            tiers_disp = safe(tiers) if tiers and tiers != "N/A" else '<span class="na">미공시</span>'
            src = m.get("source_strength", "")
            src_pill = '<span class="pill pill-yes">Tier-1</span>' if "tier-1" in (src or "") else (
                '<span class="pill pill-partial">Partial</span>' if src else '<span class="pill pill-na">—</span>')
            mem_rows.append(f"""<tr class="tier-a">
  <td><span class="ticker-mini">{safe(t)}</span></td>
  <td class="peer-cell">{safe(m.get('course_name', ''))}</td>
  <td class="num">{price_disp}</td>
  <td>{tiers_disp}</td>
  <td>{src_pill}</td>
  <td class="notes">{safe((m.get('notes') or '')[:280])}{'…' if len(m.get('notes') or '') > 280 else ''}</td>
</tr>""")

    return f"""<section class="panel" data-panel="pricing">
  <div class="wrap">
    <div class="section">
      <h2>가격 — Green Fee</h2>
      <h3>슬롯별 18홀 그린피 (IDR)</h3>
      <p class="lede">
        DMIG는 cart 별도, PIPG는 green fee + cart + caddy + tax 포함 단일가.
        KPIG는 members-only로 green fee 미공시 (요금 모두 회원권에 포함).
      </p>
      <div class="tbl-card">
        <table class="tbl">
          <thead>
            <tr>
              <th>Peer</th>
              <th>코스</th>
              {pricing_header}
            </tr>
          </thead>
          <tbody>{''.join(pricing_rows)}</tbody>
        </table>
      </div>

      <div class="banner info">
        <strong>관전 포인트:</strong>
        가장 비싼 슬롯은 PIPG 주말 IDR 3,968k (모두 포함) ·
        DMIG BSD 토요일 IDR 3,500k (cart 별도) ·
        DMIG PIK 평일은 IDR 1,034k로 PIPG의 64% 수준.
      </div>
    </div>

    <div class="section">
      <h2>회원권 (Membership)</h2>
      <h3>가격·티어 공시 매트릭스</h3>
      <p class="lede">
        Pure-play 3개 모두 일반인 대상 입회금/연회비 numeric 공시 부재 (contact-only).
        KPIG만 USD 70,000 Platinum tier가 보도자료로 공개됨.
      </p>
      <div class="tbl-card">
        <table class="tbl">
          <thead>
            <tr>
              <th>Peer</th>
              <th>코스</th>
              <th class="num">공시 가격</th>
              <th>티어 구조</th>
              <th>출처 강도</th>
              <th>비고</th>
            </tr>
          </thead>
          <tbody>{''.join(mem_rows)}</tbody>
        </table>
      </div>

      <div class="src-block">
        <strong>출처:</strong>
        peer_pricing.csv (각 클럽 공식 사이트 last verified 2026-04-29 ~ 2026-05-07),
        peer_membership.csv.
      </div>
    </div>
  </div>
</section>"""


# ─────────────────────────────────────────────────────────────────────────────
# Section: Operations + CAPEX/OPEX
# ─────────────────────────────────────────────────────────────────────────────

# Years displayed in the multi-year P&L / cost line tables
PNL_YEARS = ["FY2022", "FY2023", "FY2024", "FY2025"]
COST_YEARS = ["FY2022", "FY2023", "FY2024"]


def _line_year(line: dict, fy: str):
    """Resolve a year value from a line dict, handling FY23 'restated' fallback."""
    v = line.get(fy)
    if v is None and fy == "FY2023":
        v = line.get("FY2023_restated")
    return v


def fmt_bn(v) -> str:
    """Format an absolute IDR value as 'XX.X bn' (or 'N/A')."""
    if v in (None, "", "N/A"):
        return '<span class="na">N/A</span>'
    try:
        n = float(v)
    except (TypeError, ValueError):
        return '<span class="na">N/A</span>'
    if abs(n) >= 1e12:
        return f"{n / 1e12:,.2f}조"
    if abs(n) >= 1e9:
        return f"{n / 1e9:,.1f}bn"
    if abs(n) >= 1e6:
        return f"{n / 1e6:,.1f}M"
    return f"{n:,.0f}"


def _pct_of_revenue(line_val, rev_val) -> str:
    if not line_val or not rev_val:
        return '<span class="na">—</span>'
    try:
        return f"{(float(line_val) / float(rev_val)) * 100:.1f}%"
    except (TypeError, ValueError, ZeroDivisionError):
        return '<span class="na">—</span>'


def revenue_total_for(ticker: str, fy: str):
    """Best-effort revenue total for a peer-year from notes JSON."""
    d = NOTES.get(ticker, {})
    # FY2025 pulled from fy2025_follow_up.pnl_FY2025
    if fy == "FY2025":
        fu = d.get("fy2025_follow_up", {}) or {}
        pnl = fu.get("pnl_FY2025") or {}
        return pnl.get("revenue")
    # Prefer revenue_note.total
    for key in ("revenue_note", "revenue_note_25", "revenue_note_27", "revenue_note_29",
                "revenue_note_30", "revenue_note_31"):
        b = d.get(key) or {}
        tot = (b.get("total") or {}).get(fy)
        if tot:
            return tot
    # PIPG financial_highlights uses thousand IDR — convert
    fh = d.get("financial_highlights", {}) or {}
    if "rows_in_idr_thousand" in fh:
        for r in fh["rows_in_idr_thousand"]:
            if r.get("label") in ("Pendapatan Usaha", "Revenue"):
                v = r.get(fy)
                return (v * 1000) if v else None
    return None


def _pnl_row(ticker: str) -> str:
    """Multi-year top-line P&L row (Revenue/COGS/Gross/OpEx/Op income/Net income)."""
    d = NOTES.get(ticker, {})
    cells = [f'<td><span class="ticker-mini">{safe(ticker)}</span></td>']
    for fy in PNL_YEARS:
        rev = revenue_total_for(ticker, fy)
        # COGS
        cogs = None
        for key in ("cogs_note", "cogs_note_26", "cogs_note_28", "cogs_note_30"):
            b = d.get(key) or {}
            v = (b.get("total") or {}).get(fy)
            if v:
                cogs = v
                break
        # OpEx
        opx = None
        for key in ("opex_note", "opex_note_29", "ga_note_32", "ga_note_34"):
            b = d.get(key) or {}
            v = (b.get("total") or {}).get(fy)
            if v:
                opx = v
                break
        # GP / Op inc / Net inc — from FY25 follow-up for FY25
        op_inc = None
        net_inc = None
        if fy == "FY2025":
            fu = (d.get("fy2025_follow_up") or {}).get("pnl_FY2025") or {}
            rev = fu.get("revenue") or rev
            cogs = fu.get("cogs") or cogs
            opx = fu.get("opex") or opx
            op_inc = fu.get("operating_income")
            net_inc = fu.get("net_income")
        gp = (rev - cogs) if (rev and cogs) else None
        gm = (gp / rev * 100) if (rev and gp) else None
        # PIPG financial_highlights — pull Laba Usaha, Laba Bersih
        if fy in ("FY2022", "FY2023", "FY2024") and ticker == "PIPG":
            fh = (d.get("financial_highlights") or {}).get("rows_in_idr_thousand", [])
            for r in fh:
                if r.get("label") == "Laba Usaha":
                    op_inc = r.get(fy) and r[fy] * 1000
                if r.get("label") == "Laba Bersih":
                    net_inc = r.get(fy) and r[fy] * 1000
        # DMIG FY2024 has op_income in fy25 fu
        if ticker == "DMIG" and fy == "FY2024":
            fu = (d.get("fy2025_follow_up") or {}).get("pnl_FY2024_comparative") or {}
            op_inc = op_inc or fu.get("operating_income")
            net_inc = net_inc or fu.get("net_income")
        cells.append(f'<td class="num">{fmt_bn(rev)}</td>')
        cells.append(f'<td class="num">{fmt_bn(cogs)}</td>')
        cells.append(f'<td class="num">{f"{gm:.1f}%" if gm is not None else "—"}</td>')
        cells.append(f'<td class="num">{fmt_bn(opx)}</td>')
        cells.append(f'<td class="num">{fmt_bn(op_inc)}</td>')
        cells.append(f'<td class="num">{fmt_bn(net_inc)}</td>')
    return f'<tr class="tier-a">{"".join(cells)}</tr>'


def _pnl_table() -> str:
    """Multi-year P&L table covering FY2022-FY2025 for DMIG, PIPG, KPIG."""
    rows = "".join(_pnl_row(t) for t in ["DMIG", "PIPG", "KPIG"])
    head_years = "".join(
        f'<th colspan="6" class="num">{fy[2:]}</th>' for fy in PNL_YEARS
    )
    sub_cols = "".join(
        '<th class="num">Rev</th><th class="num">COGS</th><th class="num">GM%</th>'
        '<th class="num">OpEx</th><th class="num">Op Inc</th><th class="num">Net Inc</th>'
        for _ in PNL_YEARS
    )
    return f"""<div class="tbl-card scroll-x">
  <table class="tbl tbl-tight">
    <thead>
      <tr><th rowspan="2">Peer</th>{head_years}</tr>
      <tr>{sub_cols}</tr>
    </thead>
    <tbody>{rows}</tbody>
  </table>
</div>"""


def _revenue_breakdown_row(ticker: str, line: dict, fy: str) -> str:
    """Single row: revenue line × FY value + share."""
    label = line.get("en_label") or line.get("id_label") or "—"
    v = _line_year(line, fy)
    rev = revenue_total_for(ticker, fy)
    return f'<tr><td>{safe(label)}</td><td class="num">{fmt_bn(v)}</td><td class="num">{_pct_of_revenue(v, rev)}</td></tr>'


def _revenue_breakdown_table(ticker: str, note_key: str, title: str) -> str:
    """Render a per-peer revenue breakdown table FY23 vs FY24."""
    d = NOTES.get(ticker, {})
    blk = d.get(note_key) or {}
    lines = blk.get("lines") or []
    if not lines:
        return ""
    # Use FY2024 as primary year; show FY2023 column too for trend
    rows = []
    for ln in lines:
        v23 = _line_year(ln, "FY2023")
        v24 = _line_year(ln, "FY2024")
        rev23 = revenue_total_for(ticker, "FY2023")
        rev24 = revenue_total_for(ticker, "FY2024")
        yoy = "—"
        if v23 and v24:
            try:
                yoy = f"{((float(v24) / float(v23)) - 1) * 100:+.1f}%"
            except (ValueError, ZeroDivisionError):
                pass
        label = ln.get("en_label") or ln.get("id_label") or "—"
        rows.append(
            f'<tr><td>{safe(label)}</td>'
            f'<td class="num">{fmt_bn(v23)}</td>'
            f'<td class="num">{_pct_of_revenue(v23, rev23)}</td>'
            f'<td class="num">{fmt_bn(v24)}</td>'
            f'<td class="num">{_pct_of_revenue(v24, rev24)}</td>'
            f'<td class="num">{yoy}</td></tr>'
        )
    tot = blk.get("total") or {}
    rev23 = tot.get("FY2023")
    rev24 = tot.get("FY2024")
    yoy_tot = "—"
    if rev23 and rev24:
        try:
            yoy_tot = f"{((float(rev24) / float(rev23)) - 1) * 100:+.1f}%"
        except (ValueError, ZeroDivisionError):
            pass
    rows.append(
        f'<tr class="row-total"><td><strong>합계</strong></td>'
        f'<td class="num"><strong>{fmt_bn(rev23)}</strong></td>'
        f'<td class="num">—</td>'
        f'<td class="num"><strong>{fmt_bn(rev24)}</strong></td>'
        f'<td class="num">—</td>'
        f'<td class="num"><strong>{yoy_tot}</strong></td></tr>'
    )
    src = blk.get("source_page", "")
    return f"""<div class="ops-block">
  <h4 class="ops-block-h">{safe(ticker)} — {safe(title)}</h4>
  <div class="tbl-card">
    <table class="tbl tbl-tight">
      <thead><tr>
        <th>Line</th>
        <th class="num">FY23 (IDR)</th><th class="num">FY23 %매출</th>
        <th class="num">FY24 (IDR)</th><th class="num">FY24 %매출</th>
        <th class="num">YoY</th>
      </tr></thead>
      <tbody>{''.join(rows)}</tbody>
    </table>
  </div>
  <p class="src-line">출처: {safe(src) or '—'}</p>
</div>"""


def _opex_breakdown_table(ticker: str, note_key: str, title: str) -> str:
    """OpEx line breakdown FY23 vs FY24 (sorted by FY24 desc)."""
    d = NOTES.get(ticker, {})
    blk = d.get(note_key) or {}
    lines = blk.get("lines") or []
    if not lines:
        return ""
    # Sort by FY24 value desc
    lines = sorted(lines, key=lambda ln: -(float(ln.get("FY2024") or 0)))
    rows = []
    rev24 = revenue_total_for(ticker, "FY2024")
    rev23 = revenue_total_for(ticker, "FY2023")
    for ln in lines:
        v23 = _line_year(ln, "FY2023")
        v24 = _line_year(ln, "FY2024")
        yoy = "—"
        if v23 and v24:
            try:
                yoy = f"{((float(v24) / float(v23)) - 1) * 100:+.1f}%"
            except (ValueError, ZeroDivisionError):
                pass
        label = ln.get("en_label") or ln.get("id_label") or "—"
        rows.append(
            f'<tr><td>{safe(label)}</td>'
            f'<td class="num">{fmt_bn(v23)}</td>'
            f'<td class="num">{fmt_bn(v24)}</td>'
            f'<td class="num">{_pct_of_revenue(v24, rev24)}</td>'
            f'<td class="num">{yoy}</td></tr>'
        )
    tot = blk.get("total") or {}
    rows.append(
        f'<tr class="row-total"><td><strong>합계</strong></td>'
        f'<td class="num"><strong>{fmt_bn(tot.get("FY2023"))}</strong></td>'
        f'<td class="num"><strong>{fmt_bn(tot.get("FY2024"))}</strong></td>'
        f'<td class="num"><strong>{_pct_of_revenue(tot.get("FY2024"), rev24)}</strong></td>'
        f'<td class="num">—</td></tr>'
    )
    src = blk.get("source_page", "")
    return f"""<div class="ops-block">
  <h4 class="ops-block-h">{safe(ticker)} — {safe(title)}</h4>
  <div class="tbl-card">
    <table class="tbl tbl-tight">
      <thead><tr>
        <th>Line (영문 label)</th>
        <th class="num">FY23 (IDR)</th>
        <th class="num">FY24 (IDR)</th>
        <th class="num">FY24 %매출</th>
        <th class="num">YoY</th>
      </tr></thead>
      <tbody>{''.join(rows)}</tbody>
    </table>
  </div>
  <p class="src-line">출처: {safe(src) or '—'}</p>
</div>"""


def _capex_proxy_table() -> str:
    """Per-peer CAPEX proxy: depreciation, maintenance, asset intensity."""
    rows = []
    for t in ["DMIG", "PIPG", "KPIG"]:
        d = NOTES.get(t, {})
        # Collect depreciation FY24 from opex
        dep_line = None
        maint_line = None
        for okey in ("opex_note", "opex_note_29", "ga_note_34"):
            b = d.get(okey) or {}
            for ln in b.get("lines") or []:
                lab = (ln.get("id_label") or "").lower()
                en = (ln.get("en_label") or "").lower()
                if "penyusutan" in lab or "depreciation" in en:
                    dep_line = ln
                if "perbaikan" in lab or "pemeliharaan" in lab or "perawatan" in lab or "repair" in en or "maintenance" in en:
                    maint_line = ln
                if dep_line and maint_line:
                    break
            if dep_line and maint_line:
                break
        rev24 = revenue_total_for(t, "FY2024")
        dep24 = (dep_line or {}).get("FY2024")
        mnt24 = (maint_line or {}).get("FY2024")
        # Try peer_financials_curated for total assets
        fin = next((f for f in by_ticker(FINANCIALS, t) if f.get("total_assets_idr")), {})
        ta = fin.get("total_assets_idr")
        dep_pct = _pct_of_revenue(dep24, rev24)
        mnt_pct = _pct_of_revenue(mnt24, rev24)
        intensity = "—"
        if rev24 and ta:
            try:
                intensity = f"{float(ta) / float(rev24):.2f}×"
            except (ValueError, ZeroDivisionError):
                pass
        rows.append(
            f'<tr class="tier-a">'
            f'<td><span class="ticker-mini">{safe(t)}</span></td>'
            f'<td class="num">{fmt_bn(dep24)}</td>'
            f'<td class="num">{dep_pct}</td>'
            f'<td class="num">{fmt_bn(mnt24)}</td>'
            f'<td class="num">{mnt_pct}</td>'
            f'<td class="num">{fmt_bn(ta)}</td>'
            f'<td class="num">{intensity}</td>'
            f'</tr>'
        )
    return f"""<div class="tbl-card">
  <table class="tbl">
    <thead><tr>
      <th>Peer</th>
      <th class="num">감가상각 (FY24)</th>
      <th class="num">감가/매출</th>
      <th class="num">유지보수 (FY24)</th>
      <th class="num">유지/매출</th>
      <th class="num">총자산 (entity)</th>
      <th class="num">자산/매출</th>
    </tr></thead>
    <tbody>{''.join(rows)}</tbody>
  </table>
</div>"""


def _fy25_delta_cards() -> str:
    """FY2025 (Cycle 167) preliminary delta callouts for DMIG, PIPG, KPIG."""
    cards = []

    def _sign_pct(v):
        if v is None:
            return '<span class="na">N/A</span>'
        try:
            return f"{float(v) * 100:+.1f}%"
        except (TypeError, ValueError):
            return '<span class="na">N/A</span>'

    for t in ["DMIG", "PIPG", "KPIG"]:
        fu = (NOTES.get(t, {}) or {}).get("fy2025_follow_up") or {}
        if not fu:
            continue
        # KPIG: only segment revenue available (no full P&L)
        if t == "KPIG":
            seg = fu.get("FY2025_revenue_note_31") or {}
            seg_rev = seg.get("Hotel_resor_dan_golf")
            seg_yoy = seg.get("yoy_vs_fy2024")
            disclosure_note = fu.get("golf_segment_disclosure", "")
            cards.append(
                f'<div class="kv">'
                f'<div class="k">{safe(t)} — FY2025 segment 매출</div>'
                f'<dl class="kv-mini">'
                f'<dt>Hotel+Resort+Golf</dt><dd>{fmt_bn(seg_rev)} <span class="muted">({_sign_pct(seg_yoy)} YoY)</span></dd>'
                f'<dt>Golf-only</dt><dd><span class="na">미공시 (segment 통합)</span></dd>'
                f'</dl>'
                f'<p class="kv-comment">{safe(disclosure_note)}</p>'
                f'<span class="src">출처: {safe(fu.get("source", ""))[:120]}</span>'
                f'</div>'
            )
            continue
        pnl = fu.get("pnl_FY2025") or {}
        yoy = fu.get("yoy_changes") or {}
        comment = yoy.get("comment", "")
        rev = pnl.get("revenue")
        op_inc = pnl.get("operating_income")
        net_inc = pnl.get("net_income")
        rev_d = yoy.get("revenue")
        op_d = yoy.get("operating_income")
        net_d = yoy.get("net_income")
        cards.append(
            f'<div class="kv">'
            f'<div class="k">{safe(t)} — FY2025 미감사 P&L</div>'
            f'<dl class="kv-mini">'
            f'<dt>매출</dt><dd>{fmt_bn(rev)} <span class="muted">({_sign_pct(rev_d)} YoY)</span></dd>'
            f'<dt>영업이익</dt><dd>{fmt_bn(op_inc)} <span class="muted">({_sign_pct(op_d)} YoY)</span></dd>'
            f'<dt>순이익</dt><dd>{fmt_bn(net_inc)} <span class="muted">({_sign_pct(net_d)} YoY)</span></dd>'
            f'</dl>'
            f'<p class="kv-comment">{safe(comment)}</p>'
            f'<span class="src">출처: {safe(fu.get("source", ""))[:120]}</span>'
            f'</div>'
        )
    return f'<div class="kv-grid">{"".join(cards)}</div>'


def section_ops() -> str:
    # Disclosure matrix
    rows = []
    for t in PUREPLAY:
        op = first_by_ticker(OPERATING, t) or {}
        fin = first_by_ticker(FINANCIALS, t) or {}
        seg = op.get("segment_revenue_disclosure", "")
        seg_short = "Full" if "full" in seg.lower() or "explicitly" in seg.lower() else (
            "Partial" if seg and seg != "N/A" else "N/A")
        seg_pill = (
            '<span class="pill pill-yes">Full disclosure</span>' if seg_short == "Full"
            else '<span class="pill pill-partial">Partial</span>' if seg_short == "Partial"
            else '<span class="pill pill-na">N/A</span>'
        )
        seg_year = op.get("segment_year", "")
        rows.append(f"""<tr class="tier-a">
  <td><span class="ticker-mini">{safe(t)}</span></td>
  <td>{seg_pill}</td>
  <td class="num">{safe(seg_year or '—')}</td>
  <td class="notes">{safe(seg[:200])}{'…' if len(seg) > 200 else ''}</td>
</tr>""")

    # Asset intensity & margin
    perf_rows = []
    for t in PUREPLAY:
        fin_rows = by_ticker(FINANCIALS, t)
        fin = next((f for f in fin_rows if f.get("revenue_idr") not in ("", None)),
                   fin_rows[0] if fin_rows else {})
        rev = float(fin.get("revenue_idr") or 0)
        prof = float(fin.get("net_profit_idr") or 0)
        assets = float(fin.get("total_assets_idr") or 0)

        # DMIG: use H1 supplement
        if t == "DMIG":
            rev = SUPPLEMENT["DMIG"]["revenue_h1_2024_idr"]
            rev_label = f"{fmt_idr_compact(rev)} (H1)"
        else:
            rev_label = fmt_idr_compact(rev) if rev else "N/A"

        margin = f"{(prof / rev * 100):.1f}%" if rev and prof else "N/A"
        intensity = f"{(assets / rev):.2f}×" if rev and assets else "N/A"
        perf_rows.append(f"""<tr class="tier-a">
  <td><span class="ticker-mini">{safe(t)}</span></td>
  <td class="num">{rev_label}</td>
  <td class="num">{fmt_idr_compact(prof) if prof else 'N/A'}</td>
  <td class="num">{fmt_idr_compact(assets) if assets else 'N/A'}</td>
  <td class="num">{margin}</td>
  <td class="num">{intensity}</td>
</tr>""")

    # Capex narrative — extracted from operating_signals.notes
    capex_notes = []
    for t in PUREPLAY:
        op = first_by_ticker(OPERATING, t)
        if not op:
            continue
        notes = (op.get("operational_notes") or "").strip()
        if not notes or notes == "N/A":
            continue
        capex_notes.append(f"""<div class="kv">
  <div class="k">{safe(t)} — 운영/CAPEX 메모</div>
  <div class="v small">{safe(notes)}</div>
  <span class="src">출처: peer_operating_signals.csv</span>
</div>""")

    # ── New sub-sections built from operations/data/*_notes.json
    pnl_table = _pnl_table()
    capex_proxy_table = _capex_proxy_table()
    fy25_cards = _fy25_delta_cards()

    rev_blocks = "\n".join(filter(None, [
        _revenue_breakdown_table("DMIG", "revenue_note", "매출 라인 분해"),
        _revenue_breakdown_table("PIPG", "revenue_note_27", "매출 라인 분해 (Note 27)"),
    ]))
    cogs_blocks = "\n".join(filter(None, [
        _revenue_breakdown_table("DMIG", "cogs_note", "COGS 라인 분해"),
        _revenue_breakdown_table("PIPG", "cogs_note_28", "COGS 라인 분해 (Note 28)"),
    ]))
    opex_blocks = "\n".join(filter(None, [
        _opex_breakdown_table("DMIG", "opex_note", "OpEx 라인 분해 (Note 25)"),
        _opex_breakdown_table("PIPG", "opex_note_29", "OpEx 라인 분해 (Note 29)"),
        _opex_breakdown_table("KPIG", "ga_note_34", "G&A 비용 라인 (Note 34) — Hotel+Resort+Golf 통합"),
    ]))

    return f"""<section class="panel" data-panel="ops">
  <div class="wrap">

    <div class="section">
      <h2>4년 통합 P&L — Pure-play 3-peer</h2>
      <h3>FY2022 → FY2025 (FY25는 미감사 prelim)</h3>
      <p class="lede">
        DMIG/PIPG는 FY22~FY25 4개년 P&L 라인 전체 추출 가능 (annual report Note 23/24/25 또는 Note 27/28/29).
        KPIG는 Hotel+Resort+Golf 통합 라인이므로 golf-only 비교 불가하나, 그룹 효율 추이는 참고 가능.
      </p>
      {pnl_table}
      <div class="banner info">
        <strong>주의:</strong> KPIG 매출은 Hotel+Resort+Golf 통합 (Note 31 'Hotel, resor dan golf' = FY24 IDR 960bn).
        KPIG의 COGS/OpEx는 그룹 전체 (Property management 포함) — golf-only 비교에는 부적합.
        DMIG/PIPG가 1:1 비교 valid pair.
      </div>
    </div>

    <div class="section">
      <h2>매출 라인 분해 — Pure-play</h2>
      <h3>골프 / F&amp;B / 회원권 / 부대시설 별 매출 (FY23→FY24)</h3>
      <p class="lede">
        annual report Note에서 라인별 매출을 직접 추출. 각 라인의 매출 비중과 YoY 증감을 표시합니다.
        <strong>DMIG</strong>는 7개 라인 (Note 23), <strong>PIPG</strong>는 11개 라인 (Note 27).
      </p>
      {rev_blocks}
    </div>

    <div class="section">
      <h2>COGS (매출원가) 라인 분해</h2>
      <h3>골프 코스 / 레스토랑 / 카트 / 드라이빙 레인지 등</h3>
      <p class="lede">
        매출원가는 segment별로 cost of revenue가 분리 공시됩니다.
        DMIG는 3개 라인 (Golf course / Restaurant / Recreation), PIPG는 11개 라인 (Restaurant, Golf course, Cart, Driving range, Membership, Academy 등).
      </p>
      {cogs_blocks}
    </div>

    <div class="section">
      <h2>OpEx 라인 분해 — CAPEX/OPEX 핵심</h2>
      <h3>인건비 · 감가상각 · 유지보수 · 세금 · 유틸리티 등</h3>
      <p class="lede">
        AR Note 25 (DMIG) / Note 29 (PIPG) / Note 34 (KPIG)에서 OpEx 라인 단위 분해. 매출 대비 %와 YoY 증감 표시.
        가장 큰 비용 항목: <strong>인건비 (Salaries+benefits)</strong> 및 <strong>감가상각 (Depreciation)</strong>.
        PIPG는 추가로 Pajak dan perijinan (Tax+legal) 비중이 매우 높음 (FY24 IDR 24.2bn).
      </p>
      {opex_blocks}
    </div>

    <div class="section">
      <h2>CAPEX proxy — 감가상각·유지보수·자산집약도</h2>
      <h3>Audited CAPEX 미공시 → P&L proxy + B/S proxy로 추정</h3>
      <p class="lede">
        CAPEX 직접 공시는 없으나 다음 3개 indicator로 자본투자 강도를 추정:
        <strong>(1) 감가상각비/매출</strong> — 누적 CAPEX의 유동화 비율,
        <strong>(2) 유지보수/매출</strong> — 진행 중 maintenance CAPEX,
        <strong>(3) 총자산/매출</strong> — historic CAPEX 누적 (B/S 기준).
      </p>
      {capex_proxy_table}
      <div class="banner info">
        <strong>해석:</strong> DMIG는 감가상각/매출 ≈ 11%, PIPG ≈ 5.7%. DMIG가 신규 시설 (Range@PIK 골프테인먼트 등)에 더 공격적으로 투자한 것으로 보임.
        PIPG는 유지보수/매출 ≈ 5.9%로 DMIG (0.9%)보다 5~6배 높아 노후 코스 (1976년 개장) 유지비용 부담을 시사.
      </div>
    </div>

    <div class="section">
      <h2>FY2025 미감사 prelim — 마진 압박 신호</h2>
      <h3>각 peer가 발표한 FY2025 unaudited P&L (2026-05-12 Cycle 167)</h3>
      <p class="lede">
        DMIG/PIPG/KPIG 모두 FY2025 unaudited financial statement를 공시. 라인 단위 추이로 마진 변화 감지 가능.
      </p>
      {fy25_cards}
    </div>

    <div class="section">
      <h2>골프 segment 매출 disclosure 강도</h2>
      <h3>annual report에서 골프장만 떼어내 공시하는가?</h3>
      <p class="lede">
        Pure-play 3개의 segment 공시 강도. <em>Full</em>은 골프장 매출/비용을 segment로 분리 공시,
        <em>Partial</em>은 일부만, <em>N/A</em>는 모회사 합산만 공시.
      </p>
      <div class="tbl-card">
        <table class="tbl">
          <thead>
            <tr>
              <th>Peer</th>
              <th>공시 강도</th>
              <th class="num">기준 FY</th>
              <th>공시 형태</th>
            </tr>
          </thead>
          <tbody>{''.join(rows)}</tbody>
        </table>
      </div>
    </div>

    <div class="section">
      <h2>운영 효율 KPI — 마진·자산효율</h2>
      <h3>FY2024 순이익률 · 자산집약도</h3>
      <div class="tbl-card">
        <table class="tbl">
          <thead>
            <tr>
              <th>Peer</th>
              <th class="num">매출 (FY24)</th>
              <th class="num">순이익</th>
              <th class="num">총자산</th>
              <th class="num">순이익률</th>
              <th class="num">자산/매출</th>
            </tr>
          </thead>
          <tbody>{''.join(perf_rows)}</tbody>
        </table>
      </div>

      <div class="banner">
        <strong>해석 주의:</strong> KPIG 매출·순이익·자산은 <strong>모회사 연결 기준</strong>(non-golf 사업 포함).
        DMIG 매출은 H1만 audited (curated CSV). 본 페이지의 FY24 4년 P&L 표는 Note 추출본 (FY24 full year)을 사용 — 이 KPI 표는 curated CSV의 단일 entry만 표시.
        PIPG만 entity 기준 FY 전체 일관.
      </div>
    </div>

    <div class="section">
      <h2>운영 narrative — Annual Report 메모</h2>
      <h3>peer_operating_signals.csv 텍스트 발췌</h3>
      <div class="kv-grid">
        {''.join(capex_notes)}
      </div>

      <div class="src-block">
        <strong>출처:</strong>
        DMIG/PIPG/KPIG annual reports (FY22–FY25), 라인별 추출 = <code>site/peer-analysis/operations/data/{{ticker}}_notes.json</code> ·
        peer_financials_curated.csv ·
        peer_operating_signals.csv (segment_revenue_disclosure, operational_notes 필드).
      </div>
    </div>
  </div>
</section>"""


# ─────────────────────────────────────────────────────────────────────────────
# Section: Reference (10 other peers)
# ─────────────────────────────────────────────────────────────────────────────

def section_reference() -> str:
    rows = []
    for t in REFERENCE:
        inv = first_inventory(t) or {}
        fin_rows = by_ticker(FINANCIALS, t)
        fin = next((f for f in fin_rows if f.get("revenue_idr") not in ("", None)),
                   fin_rows[0] if fin_rows else {})
        op = first_by_ticker(OPERATING, t) or {}
        courses = [c for c in courses_for(t)]
        course_names = " · ".join(c.get("course_name", "") for c in courses) or '<span class="na">N/A</span>'
        holes = sum(int(c["holes"]) for c in courses if c.get("holes") and c["holes"] != "N/A")
        seg = op.get("segment_revenue_disclosure", "") or ""
        if "explicitly" in seg.lower() or "full" in seg.lower():
            seg_pill = '<span class="pill pill-yes">Full</span>'
        elif "not separately" in seg.lower() or seg.strip() == "":
            seg_pill = '<span class="pill pill-no">미공시</span>'
        elif "n/a" in seg.lower() and "township" in (inv.get("notes", "") or "").lower():
            seg_pill = '<span class="pill pill-na">No golf</span>'
        elif seg.strip() and seg != "N/A":
            seg_pill = '<span class="pill pill-partial">Partial</span>'
        else:
            seg_pill = '<span class="pill pill-na">—</span>'
        parent_rev = fin.get("revenue_idr")
        seg_rev = op.get("course_segment_revenue_idr")
        rows.append(f"""<tr>
  <td><span class="ticker-mini">{safe(t)}</span></td>
  <td>{safe(TIER_LABEL.get(t, '—'))}</td>
  <td class="peer-cell">{course_names}<span class="sub">{safe(inv.get('region', ''))}</span></td>
  <td class="num">{holes if holes else '<span class="na">—</span>'}</td>
  <td>{seg_pill}</td>
  <td class="num">{fmt_idr_compact(parent_rev)}</td>
  <td class="num">{fmt_idr_compact(seg_rev) if seg_rev else '<span class="na">—</span>'}</td>
</tr>""")

    return f"""<section class="panel" data-panel="reference">
  <div class="wrap">
    <div class="section">
      <h2>참고 — 비-Pure-play Peer</h2>
      <h3>10개 (MKPI · 9 diversified) 요약 매트릭스</h3>
      <p class="lede">
        골프장 운영이 본업이 아닌 모회사 또는 segment 미공시 peer.
        Pure-play 3개와 직접 비교 부적합하지만, 시장 컨텍스트 파악용 1줄 요약.
        <strong>MKPI</strong>는 township 개발사로 PIPG 0.38% 지분만 보유 (직접 골프 운영 없음).
      </p>
      <div class="tbl-card">
        <table class="tbl">
          <thead>
            <tr>
              <th>Peer</th>
              <th>분류</th>
              <th>골프장 · 지역</th>
              <th class="num">총 홀</th>
              <th>골프 segment 공시</th>
              <th class="num">모회사 매출 (FY24)</th>
              <th class="num">골프 segment 매출</th>
            </tr>
          </thead>
          <tbody>{''.join(rows)}</tbody>
        </table>
      </div>

      <div class="banner info">
        <strong>골프 segment 공시가 명시적인 peer:</strong>
        <strong>MDLN</strong> (Modern Golf IDR 74.3bn FY24) · <strong>KIJA</strong> (Jababeka 골프 IDR 47.92bn FY24) ·
        <strong>GOLF</strong> (Bali Beach Golf — 전체 매출의 47%).
        이 3개는 후속 deep-dive 후보.
      </div>

      <div class="src-block">
        <strong>출처:</strong>
        peer_inventory.csv,
        peer_course_facts.csv,
        peer_operating_signals.csv,
        peer_financials_curated.csv.
      </div>
    </div>
  </div>
</section>"""


# ─────────────────────────────────────────────────────────────────────────────
# Page assembly
# ─────────────────────────────────────────────────────────────────────────────

def build_html() -> str:
    today = dt.date.today().isoformat()
    sections = "\n".join([
        section_overview(),
        section_course(),
        section_pricing(),
        section_ops(),
        section_reference(),
    ])

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>골프장 운영 Peer 비교 — Pure-play 중심 (DMIG · PIPG · KPIG)</title>
<meta name="description" content="인도네시아 IDX 상장 골프장 운영 peer 비교. Pure-play 3개 (DMIG, PIPG, KPIG) 심층 + 10개 reference.">
<link rel="stylesheet" href="style.css">
</head>
<body>

<header class="head">
  <div class="wrap">
    <div class="head-row">
      <div class="brand">
        <span class="mark">⛳</span>
        <div>
          <div class="name">골프장 운영 Peer 비교</div>
          <div class="sub">Pure-play 중심 · DMIG · PIPG · KPIG · 인도네시아 IDX</div>
        </div>
      </div>
      <div class="head-actions">
        <a class="btn-link" href="../operations/dashboard.html">기존 13-peer 운영 대시보드 ↗</a>
        <a class="btn-link" href="../../index.html">← 지도</a>
      </div>
    </div>
    <nav class="tabs" role="tablist">
      <button class="tab" data-tab="overview" type="button">📊 종합</button>
      <button class="tab" data-tab="course" type="button">⛳ 코스·인프라</button>
      <button class="tab" data-tab="pricing" type="button">💰 가격·회원권</button>
      <button class="tab" data-tab="ops" type="button">⚙️ 운영 KPI · CAPEX/OPEX</button>
      <button class="tab" data-tab="reference" type="button">📋 참고 (10 peer)</button>
    </nav>
  </div>
</header>

<main>
{sections}
</main>

<footer class="foot">
  <div class="wrap">
    <p>
      <strong>골프장 운영 Peer 비교 사이트</strong> — Build {today} ·
      데이터: raw_peer_data/*.csv (last verified 2026-04-29 ~ 2026-05-07) ·
      추정/보간 없음. 미공시는 N/A로 표기.
    </p>
    <p>
      <a href="https://github.com/moon470an-sys/Indonesia-Golf-Club">소스 GitHub</a> ·
      <a href="../operations/dashboard.html">기존 운영 대시보드 (13 peer 전체)</a>
    </p>
  </div>
</footer>

<script src="app.js"></script>
</body>
</html>
"""


def main() -> None:
    out = HERE / "index.html"
    out.write_text(build_html(), encoding="utf-8")
    print(f"OK: wrote {out} ({out.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
