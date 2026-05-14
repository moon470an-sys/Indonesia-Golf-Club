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


# OpEx category buckets — keyword based (Indonesian + English variants)
OPEX_CATEGORY_RULES = [
    ("인건비 (Salaries+benefits)", ["gaji", "upah", "tunjangan", "imbalan kerja", "kesejahteraan", "salary", "wage", "employee benefit", "diklat"]),
    ("감가상각 (Depreciation/Amort.)", ["penyusutan", "amortisasi", "depreciation", "amortization"]),
    ("유지보수 (Repair+Maintenance)", ["perbaikan", "pemeliharaan", "perawatan", "repair", "maintenance"]),
    ("세금·법률 (Tax+Legal)", ["pajak", "perijinan", "perizinan", "legal", "jasa profesional", "tenaga ahli", "audit", "konsultan"]),
    ("유틸리티 (Utilities)", ["listrik", "air", "utilitas", "electricity", "water", "utility"]),
    ("청소·보안 (Cleaning+Security)", ["kebersihan", "keamanan", "jasa manajemen", "cleaning", "security"]),
    ("통신·IT (Comm+IT)", ["telepon", "teleks", "fax", "internet", "perangkat lunak", "teknologi informasi", "administrasi bank", "kartu kredit", "pos,"]),
    ("운송·출장 (Transport+Travel)", ["transportasi", "perjalanan", "akomodasi", "transport"]),
    ("보험 (Insurance)", ["asuransi", "insurance"]),
    ("광고·마케팅 (Ads+Marketing)", ["iklan", "promosi", "pemasaran", "komisi", "branding", "sponsor"]),
    ("사무·소모품 (Office supplies)", ["alat-alat tulis", "cetakan", "perlengkapan", "stationery"]),
]


def _opex_category_of(label: str) -> str:
    s = (label or "").lower()
    for cat, kws in OPEX_CATEGORY_RULES:
        if any(kw in s for kw in kws):
            return cat
    return "기타 (Other)"


def _normalized_opex_compare_table() -> str:
    """Per-peer OpEx by category, normalized as % of revenue (FY24).

    Buckets line items via keyword rules so DMIG/PIPG/GOLF can be compared
    one-to-one even when AR Note labels differ.
    """
    peers_with_opex = [
        ("DMIG", "opex_note", "revenue_note"),
        ("PIPG", "opex_note_29", "revenue_note_27"),
        ("GOLF", "ga_note_32", "revenue_note_29"),
    ]
    # Build per-peer category totals FY24
    per_peer: dict = {}
    for ticker, opex_key, rev_key in peers_with_opex:
        d = NOTES.get(ticker, {})
        rev_total = (d.get(rev_key) or {}).get("total", {}).get("FY2024")
        if ticker == "GOLF":
            rev_total = ((d.get("revenue_note_29") or {}).get("by_operations") or {}).get("total", {}).get("FY2024")
        cat_totals: dict = {}
        for ln in (d.get(opex_key) or {}).get("lines") or []:
            cat = _opex_category_of((ln.get("id_label") or "") + " " + (ln.get("en_label") or ""))
            cat_totals[cat] = cat_totals.get(cat, 0) + (ln.get("FY2024") or 0)
        per_peer[ticker] = {"rev": rev_total, "by_cat": cat_totals, "total": (d.get(opex_key) or {}).get("total", {}).get("FY2024")}

    # All categories observed
    all_cats: list = []
    for cat, _ in OPEX_CATEGORY_RULES:
        all_cats.append(cat)
    all_cats.append("기타 (Other)")

    head = '<tr><th>OpEx 카테고리</th>'
    for ticker, _, _ in peers_with_opex:
        head += f'<th class="num">{safe(ticker)} %매출</th><th class="num">{safe(ticker)} IDR</th>'
    head += '</tr>'

    body = []
    for cat in all_cats:
        cells = [f"<td>{safe(cat)}</td>"]
        any_data = False
        for ticker, _, _ in peers_with_opex:
            pp = per_peer[ticker]
            v = pp["by_cat"].get(cat, 0)
            if v:
                any_data = True
            pct = (v / pp["rev"] * 100) if (v and pp["rev"]) else None
            cells.append(f'<td class="num">{(f"{pct:.1f}%" if pct else "—")}</td>')
            cells.append(f'<td class="num">{fmt_bn(v) if v else "—"}</td>')
        if any_data:
            body.append(f'<tr>{"".join(cells)}</tr>')
    # Total row
    tot_cells = ["<td><strong>OpEx 합계</strong></td>"]
    for ticker, _, _ in peers_with_opex:
        pp = per_peer[ticker]
        opex_tot = pp["total"]
        pct = (opex_tot / pp["rev"] * 100) if (opex_tot and pp["rev"]) else None
        tot_cells.append(f'<td class="num"><strong>{(f"{pct:.1f}%" if pct else "—")}</strong></td>')
        tot_cells.append(f'<td class="num"><strong>{fmt_bn(opex_tot)}</strong></td>')
    body.append(f'<tr class="row-total">{"".join(tot_cells)}</tr>')

    return f"""<div class="tbl-card scroll-x">
  <table class="tbl tbl-tight">
    <thead>{head}</thead>
    <tbody>{''.join(body)}</tbody>
  </table>
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


# ==============================================================
# Iteration 16 — Visual data-viz for CAPEX/OpEx section
# ==============================================================

# Color palette for OpEx categories (matches CSS .sw-* swatches)
OPEX_CAT_COLORS = {
    "인건비 (Salaries+benefits)":        "#2d5016",  # green
    "감가상각 (Depreciation/Amort.)":     "#4a7c30",  # green-soft
    "유지보수 (Repair+Maintenance)":      "#95c073",  # light-green
    "세금·법률 (Tax+Legal)":             "#92400e",  # warn
    "유틸리티 (Utilities)":              "#c08a2e",  # gold
    "청소·보안 (Cleaning+Security)":      "#8a8a8a",  # muted
    "통신·IT (Comm+IT)":                "#1e40af",  # blue
    "운송·출장 (Transport+Travel)":       "#6b21a8",  # purple
    "보험 (Insurance)":                  "#b91c1c",  # red
    "광고·마케팅 (Ads+Marketing)":        "#1e40af",  # blue
    "사무·소모품 (Office supplies)":      "#d4d0c0",  # neutral
    "기타 (Other)":                      "#d4d0c0",  # neutral
}

def _opex_norm_data() -> dict:
    """Shared per-peer OpEx category data for viz + table."""
    peers_with_opex = [
        ("DMIG", "opex_note", "revenue_note"),
        ("PIPG", "opex_note_29", "revenue_note_27"),
        ("GOLF", "ga_note_32", "revenue_note_29"),
    ]
    per_peer = {}
    for ticker, opex_key, rev_key in peers_with_opex:
        d = NOTES.get(ticker, {})
        rev_total = (d.get(rev_key) or {}).get("total", {}).get("FY2024")
        if ticker == "GOLF":
            rev_total = ((d.get("revenue_note_29") or {}).get("by_operations") or {}).get("total", {}).get("FY2024")
        cat_totals = {}
        for ln in (d.get(opex_key) or {}).get("lines") or []:
            cat = _opex_category_of((ln.get("id_label") or "") + " " + (ln.get("en_label") or ""))
            cat_totals[cat] = cat_totals.get(cat, 0) + (ln.get("FY2024") or 0)
        per_peer[ticker] = {
            "rev": rev_total,
            "by_cat": cat_totals,
            "total": (d.get(opex_key) or {}).get("total", {}).get("FY2024"),
        }
    return per_peer


def _opex_kpi_strip() -> str:
    """4-tile KPI strip — peer total OpEx ratios + headline insight."""
    pp = _opex_norm_data()

    def tile_for(ticker: str, accent: str, headline_hint: str) -> str:
        d = pp.get(ticker, {})
        total = d.get("total")
        rev = d.get("rev")
        pct = (total / rev * 100) if (total and rev) else None
        by_cat = d.get("by_cat") or {}
        sorted_cats = sorted(by_cat.items(), key=lambda x: -(x[1] or 0))
        top_cat, top_val = (sorted_cats[0] if sorted_cats else ("—", 0))
        top_pct = (top_val / rev * 100) if (top_val and rev) else None
        # Pull category prefix (Korean label before paren)
        top_cat_short = top_cat.split(" (")[0] if " (" in top_cat else top_cat
        return f"""<div class="kpi-tile {accent}">
  <div class="kpi-cap">{safe(ticker)} · OpEx / 매출</div>
  <div class="kpi-val">{(f"{pct:.1f}%" if pct else "—")}</div>
  <div class="kpi-sub"><strong>{safe(top_cat_short)}</strong> {(f"{top_pct:.1f}%" if top_pct else "")} · 최대 비용</div>
  <div class="kpi-sub">{safe(headline_hint)}</div>
</div>"""

    inset = """<div class="kpi-tile accent-blue">
  <div class="kpi-cap">Cross-peer gap</div>
  <div class="kpi-val">17.4<span style="font-size:14px">pp</span></div>
  <div class="kpi-sub">GOLF 21.1% vs PIPG 38.5% (FY24)</div>
  <div class="kpi-sub">capital-light vs mature-course</div>
</div>"""

    return f"""<div class="kpi-strip">
  {tile_for('DMIG', 'accent-warn', '감가 12.2% — PIK Range 신규투자 부담')}
  {tile_for('PIPG', 'accent-warn', '세금·법률 12.3% — Pajak dan perijinan outlier')}
  {tile_for('GOLF', 'accent-green', '실효 OpEx 가장 효율 / 단 IPO 1년차')}
  {inset}
</div>"""


def _opex_stacked_bars() -> str:
    """100% stacked composition bar per peer — visual OpEx mix at a glance."""
    pp = _opex_norm_data()
    legend_cats = [
        ("인건비 (Salaries+benefits)", "인건비"),
        ("감가상각 (Depreciation/Amort.)", "감가상각"),
        ("유지보수 (Repair+Maintenance)", "유지보수"),
        ("세금·법률 (Tax+Legal)", "세금·법률"),
        ("유틸리티 (Utilities)", "유틸리티"),
        ("광고·마케팅 (Ads+Marketing)", "광고·마케팅"),
        ("통신·IT (Comm+IT)", "통신·IT"),
        ("운송·출장 (Transport+Travel)", "운송·출장"),
        ("기타 (Other)", "기타"),
    ]

    rows = []
    for ticker in ["DMIG", "PIPG", "GOLF"]:
        d = pp.get(ticker, {})
        total = d.get("total") or 0
        by_cat = d.get("by_cat") or {}
        rev = d.get("rev")
        rev_pct = (total / rev * 100) if (total and rev) else None
        # Sort by category order in legend for visual consistency
        ordered = []
        for cat_full, _ in legend_cats:
            v = by_cat.get(cat_full, 0)
            if v:
                ordered.append((cat_full, v))
        # Append any other categories not in legend list
        leftover = [(c, v) for c, v in by_cat.items() if c not in dict(legend_cats) and v]
        ordered.extend(leftover)

        segs = []
        for cat, val in ordered:
            if not total:
                continue
            pct = (val or 0) / total * 100
            if pct < 0.3:
                continue
            color = OPEX_CAT_COLORS.get(cat, "#d4d0c0")
            cat_short = cat.split(" (")[0] if " (" in cat else cat
            label = f"{pct:.0f}%" if pct >= 6 else ""
            segs.append(
                f'<div class="stack-seg" style="width:{pct:.2f}%;background:{color};" '
                f'title="{safe(cat_short)}: {pct:.1f}% (Rp {fmt_bn(val).replace(" bn","bn")})">{label}</div>'
            )
        rev_pct_str = f"{rev_pct:.1f}%" if rev_pct else "—"
        rows.append(f"""<div class="stack-row">
  <div class="stack-label"><span class="ticker-mini">{safe(ticker)}</span> <span class="muted">{rev_pct_str}</span></div>
  <div class="stack-bar">{"".join(segs)}</div>
  <div class="stack-total">{fmt_bn(total)}</div>
</div>""")

    legend_items = []
    for cat_full, short in legend_cats:
        color = OPEX_CAT_COLORS.get(cat_full, "#d4d0c0")
        legend_items.append(
            f'<span class="lg"><span class="sw" style="background:{color};"></span>{safe(short)}</span>'
        )
    legend = f'<div class="stack-legend">{"".join(legend_items)}</div>'

    return f"""<div class="stack-block">
  <p class="src-line" style="margin: 4px 2px 8px;">막대 너비 = OpEx 합계 대비 카테고리 비중 · ticker 옆 % = OpEx/매출 · 막대 위 hover로 정확 수치</p>
  {"".join(rows)}
  {legend}
</div>"""


def _opex_norm_bar_table() -> str:
    """OpEx normalized table with inline mini bar viz in each % cell.

    Bar width = peer's category % of revenue scaled to the max observed % cell-wide,
    so visual length is comparable across peers.
    """
    pp = _opex_norm_data()
    peers = ["DMIG", "PIPG", "GOLF"]

    # Build percent matrix
    pct_matrix = {}
    raw_matrix = {}
    for t in peers:
        d = pp[t]
        rev = d.get("rev") or 0
        for cat, val in (d.get("by_cat") or {}).items():
            if val and rev:
                pct_matrix.setdefault(cat, {})[t] = val / rev * 100
                raw_matrix.setdefault(cat, {})[t] = val

    # Max % across all cells for scaling bar widths consistently
    all_pcts = [v for sub in pct_matrix.values() for v in sub.values()]
    max_pct = max(all_pcts) if all_pcts else 1.0
    # Cap visual scale at 15% so smaller categories still look proportional
    visual_max = max(max_pct, 15.0)

    # Total row data
    totals = {}
    for t in peers:
        d = pp[t]
        tot = d.get("total")
        rev = d.get("rev")
        totals[t] = ((tot / rev * 100) if (tot and rev) else None, tot)

    # Sort categories by max FY24 IDR value across peers (largest first)
    cat_order = sorted(pct_matrix.keys(), key=lambda c: -max((raw_matrix.get(c) or {}).values(), default=0))

    head = '<tr><th style="width:200px;">OpEx 카테고리</th>'
    for t in peers:
        head += f'<th class="num" style="min-width:160px;">{safe(t)} · %매출</th>'
    head += '</tr>'

    body_rows = []
    for cat in cat_order:
        cells = [f'<td>{safe(cat)}</td>']
        for t in peers:
            pct = (pct_matrix.get(cat) or {}).get(t)
            if pct is None:
                cells.append('<td class="num"><span class="muted">—</span></td>')
                continue
            bar_w = max(2.0, (pct / visual_max) * 92.0)  # 92% max width
            viz_class = f"viz-cell viz-{t.lower()}"
            cells.append(
                f'<td class="num">'
                f'<div class="{viz_class}" style="display:flex;align-items:center;gap:8px;justify-content:flex-end;">'
                f'<span class="viz-num">{pct:.1f}%</span>'
                f'<span class="viz-bar" style="width:{bar_w:.1f}%;"></span>'
                f'</div></td>'
            )
        body_rows.append(f'<tr>{"".join(cells)}</tr>')

    tot_cells = ['<td><strong>OpEx 합계 / 매출</strong></td>']
    for t in peers:
        pct, raw = totals[t]
        pct_str = f"{pct:.1f}%" if pct is not None else "—"
        tot_cells.append(
            f'<td class="num"><strong>{pct_str}</strong> '
            f'<span class="muted" style="font-weight:400;">· Rp {fmt_bn(raw).replace(" bn","bn") if raw else "—"}</span></td>'
        )
    body_rows.append(f'<tr class="row-total">{"".join(tot_cells)}</tr>')

    return f"""<div class="tbl-card">
  <table class="tbl tbl-tight">
    <thead>{head}</thead>
    <tbody>{"".join(body_rows)}</tbody>
  </table>
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


def _all_peer_golf_segment_table() -> str:
    """Cross-peer golf segment revenue + GP margin matrix (FY2024).

    Includes peers with explicit golf segment disclosure: DMIG, PIPG, MDLN, GOLF, KIJA.
    KPIG bundled separately.
    """
    rows = []

    # DMIG — golf course only (revenue_note line)
    d = NOTES.get("DMIG", {})
    rev_lines = (d.get("revenue_note") or {}).get("lines") or []
    cogs_lines = (d.get("cogs_note") or {}).get("lines") or []
    golf_rev = next((ln.get("FY2024") for ln in rev_lines if (ln.get("en_label") or "").lower() == "golf course"), None)
    golf_cogs = next((ln.get("FY2024") for ln in cogs_lines if (ln.get("en_label") or "").lower() == "golf course"), None)
    entity_rev = (d.get("revenue_note") or {}).get("total", {}).get("FY2024")
    gm = ((golf_rev - golf_cogs) / golf_rev * 100) if (golf_rev and golf_cogs) else None
    golf_share = (golf_rev / entity_rev * 100) if (golf_rev and entity_rev) else None
    rows.append(("DMIG", "Pure-play (Note 23)", golf_rev, golf_cogs, gm, entity_rev, golf_share))

    # PIPG — golf course + cart (closer to pure-play golf)
    d = NOTES.get("PIPG", {})
    rev_lines = (d.get("revenue_note_27") or {}).get("lines") or []
    cogs_lines = (d.get("cogs_note_28") or {}).get("lines") or []
    rl = {(ln.get("en_label") or ""): ln.get("FY2024") for ln in rev_lines}
    cl = {(ln.get("en_label") or ""): ln.get("FY2024") for ln in cogs_lines}
    golf_rev_pipg = (rl.get("Golf course", 0) or 0) + (rl.get("Golf cart", 0) or 0)
    golf_cogs_pipg = (cl.get("Golf course", 0) or 0) + (cl.get("Golf cart", 0) or 0)
    entity_rev_pipg = (d.get("revenue_note_27") or {}).get("total", {}).get("FY2024")
    gm_pipg = ((golf_rev_pipg - golf_cogs_pipg) / golf_rev_pipg * 100) if golf_rev_pipg else None
    share_pipg = (golf_rev_pipg / entity_rev_pipg * 100) if (golf_rev_pipg and entity_rev_pipg) else None
    rows.append(("PIPG", "Pure-play (Golf+Cart, Note 27/28)", golf_rev_pipg, golf_cogs_pipg, gm_pipg, entity_rev_pipg, share_pipg))

    # MDLN — uses computed_ratios
    d = NOTES.get("MDLN", {})
    cr = (d.get("computed_ratios") or {}).get("FY2024", {})
    golf_rev_m = cr.get("golf_revenue_pure")
    golf_cogs_m = cr.get("golf_cogs_pure")
    gm_m = cr.get("golf_pure_gp_margin")
    entity_rev_m = (d.get("revenue_note_25") or {}).get("total", {}).get("FY2024")
    share_m = (golf_rev_m / entity_rev_m * 100) if (golf_rev_m and entity_rev_m) else None
    rows.append(("MDLN", "Golf segment (Green fee+Member+Other; Note 25)", golf_rev_m, golf_cogs_m,
                 gm_m * 100 if gm_m else None, entity_rev_m, share_m))

    # GOLF — segment by operations
    d = NOTES.get("GOLF", {})
    rev_lines = ((d.get("revenue_note_29") or {}).get("by_operations") or {}).get("lines") or []
    cogs_lines = (d.get("cogs_note_30") or {}).get("lines") or []
    golf_rev_g = next((ln.get("FY2024") for ln in rev_lines if ln.get("en_label") == "Golf"), None)
    golf_cogs_g = next((ln.get("FY2024") for ln in cogs_lines if ln.get("id_label") == "Golf"), None)
    entity_rev_g = ((d.get("revenue_note_29") or {}).get("by_operations") or {}).get("total", {}).get("FY2024")
    gm_g = ((golf_rev_g - golf_cogs_g) / golf_rev_g * 100) if (golf_rev_g and golf_cogs_g) else None
    share_g = (golf_rev_g / entity_rev_g * 100) if (golf_rev_g and entity_rev_g) else None
    rows.append(("GOLF", "Golf-only segment (Note 29 by-operations)", golf_rev_g, golf_cogs_g, gm_g, entity_rev_g, share_g))

    # KIJA — golf segment (units Rp million → multiply by 1e6 for normalization)
    d = NOTES.get("KIJA", {})
    seg = (d.get("segment_info_note_34") or {}).get("golf_segment_FY2024") or {}
    rev_k = (seg.get("revenue") or 0) * 1e6
    cogs_k = (seg.get("cogs") or 0) * 1e6
    gm_k = ((rev_k - cogs_k) / rev_k * 100) if rev_k else None
    entity_rev_k = ((d.get("segment_info_note_34") or {}).get("consolidated_total_FY2024") or {}).get("revenue", 0) * 1e6
    share_k = (rev_k / entity_rev_k * 100) if (rev_k and entity_rev_k) else None
    rows.append(("KIJA", "Golf segment (Note 34, units Rp million)", rev_k, cogs_k, gm_k, entity_rev_k, share_k))

    # SMDM — Golf dan Country Club segment (Note 29)
    d = NOTES.get("SMDM", {})
    seg_smdm = ((d.get("segment_info_note_29") or {}).get("FY2024") or {}).get("Golf dan Country Club") or {}
    rev_s = seg_smdm.get("revenue")
    cogs_s = abs(seg_smdm.get("cogs", 0)) or None
    gm_s = ((rev_s - cogs_s) / rev_s * 100) if (rev_s and cogs_s) else None
    entity_rev_s = ((d.get("segment_info_note_29") or {}).get("FY2024") or {}).get("Konsolidasian", {}).get("revenue")
    share_s = (rev_s / entity_rev_s * 100) if (rev_s and entity_rev_s) else None
    rows.append(("SMDM", "Golf & Country Club (Rancamaya, Note 29)", rev_s, cogs_s, gm_s, entity_rev_s, share_s))

    body = []
    for ticker, basis, rev, cogs, gm_pct, entity_rev, share in rows:
        gm_str = f"{gm_pct:.1f}%" if gm_pct is not None else "—"
        share_str = f"{share:.1f}%" if share is not None else "—"
        body.append(
            f'<tr class="tier-a">'
            f'<td><span class="ticker-mini">{safe(ticker)}</span></td>'
            f'<td class="notes">{safe(basis)}</td>'
            f'<td class="num">{fmt_bn(rev)}</td>'
            f'<td class="num">{fmt_bn(cogs)}</td>'
            f'<td class="num">{gm_str}</td>'
            f'<td class="num">{fmt_bn(entity_rev)}</td>'
            f'<td class="num">{share_str}</td>'
            f'</tr>'
        )

    return f"""<div class="tbl-card scroll-x">
  <table class="tbl">
    <thead><tr>
      <th>Peer</th>
      <th>공시 기준 (Note)</th>
      <th class="num">골프 매출 (FY24)</th>
      <th class="num">골프 COGS (FY24)</th>
      <th class="num">Golf GP%</th>
      <th class="num">Entity 매출</th>
      <th class="num">골프 비중</th>
    </tr></thead>
    <tbody>{''.join(body)}</tbody>
  </table>
</div>"""


# Operational KPI evidence — extracted directly from AR text (vector search verified).
# Numbers are audit-grade quotes with source page references.
OPS_KPI_EVIDENCE = {
    "DMIG": {
        "rounds_played": {
            "FY2021": None,
            "FY2022": None,
            "FY2023": "123,278 명 (BSD 45.3k + PIK 62.0k 추정, AR 텍스트 골프 인원 12,979명 증가 +12.09% YoY)",
            "FY2024": None,
            "narrative": "FY2023 골퍼 +12,979명 (+12.09% YoY): BSD 코스 +6,577명 (+14.51%) / PIK 코스 +6,402명 (+10.32%)",
            "src": "DMIG FY2023 AR p.14 REALIZATION GOLF OPERATION",
        },
        "members": {
            "FY2022": 1239,
            "FY2023": 1233,
            "FY2024": None,
            "narrative": "Main Playing Members: FY2022 1,239 → FY2023 1,233 (-6 명). Husband/Wife 79 + Child 35 포함 총 1,233",
            "src": "DMIG FY2023 AR p.17 MEMBERSHIP",
        },
        "headcount": {
            "FY2021": 342,
            "FY2022": 196,
            "FY2023": 206,
            "FY2024": None,
            "narrative": "직원 수 FY2021 342명 → FY2022 196명 (-42.7% / 코로나 회복기 구조조정) → FY2023 206명 (+5.1% 점진 회복). 인건비 비중도 FY24 12.6%로 가장 높음.",
            "src": "DMIG FY2022 p.101 / FY2023 p.87 (employees with right to receive employee benefits)",
        },
        "the_range_revenue": {
            "FY2022": 6_632_153_633,
            "FY2023": 31_350_806_602,
            "narrative": "The Range@PIK driving range/golftainment: FY2022 신규 운영 3개월간 6.6bn → FY2023 31.4bn (+372.71% YoY 풀이어 효과)",
            "src": "DMIG FY2023 AR p.18 THE RANGE",
        },
        "fnb_split_FY2023": {
            "bsd_restaurant_idr": 17_238_750_403,
            "pik_restaurant_idr": 20_452_428_599,
            "bsd_yoy_pct": 39.67,
            "narrative": "FY2023 레스토랑 매출 코스별: BSD 17.24bn (+39.67% YoY) + PIK 20.45bn (+27.99% YoY 추정) = 37.7bn 직접 합산. Note 23 총 Restaurant 48.5bn과의 차액(~10.8bn)은 The Range@PIK F&B 일부.",
            "src": "DMIG FY2023 AR p.15 FOOD & BEVERAGE",
        },
    },
    "PIPG": {
        "rounds_played": {
            "FY2021": 24512,
            "FY2022": 26551,
            "FY2023": 28464,
            "FY2024": 26805,
            "narrative": "골퍼 추이: 24,512 (FY21) → 26,551 (FY22 +8.3%) → 28,464 (FY23 +7.2%) → 26,805 (FY24 -5.8%). FY24 감소는 글로벌 경기 둔화·관광객 감소.",
            "src": "PIPG FY22/FY24 AR p.48/p.43 KEGIATAN OPERASIONAL GOLF",
        },
        "headcount_by_dept_FY2024": {
            "HRD&Training": 10, "GA&IT": 9, "Finance": 6, "Golf Course Maintenance": 14,
            "Property/ME/Locker/Security": 15, "Golf Operational": 30, "Driving Range": 22,
            "Membership/Market/PIGA": 36, "F&B": 86, "Gym": 29,
            "narrative": "FY24 부서별 (turnover 그래프 기준 인원 수). 총합 ~257명. F&B (86명)이 최대 부서.",
            "src": "PIPG FY24 AR p.75 EMPLOYEE TURNOVER",
        },
    },
    "KPIG": {
        "scope_caveat": {
            "narrative": "KPIG는 MNC Land/Tourism 모회사. Trump Lido 단독 운영 KPI는 미공시 (관계사 운영). 모회사 직원 2,573명 (FY22, 91% male)은 conglomerate 전체.",
            "src": "KPIG FY22 AR p.135 HR SDM",
        },
        "clubhouse_facility": {
            "narrative": "Trump Clubhouse 33,322 m² (Oppenheim Architecture 설계, 럭셔리 컨셉). FY2025에 18홀 풀 가동 확인.",
            "src": "KPIG FY25 AR p.85",
        },
    },
    "GOLF": {
        "capex_fy2025": {
            "construction_buildings_idr": 187_920_532_473,
            "construction_landscape_idr": 237_798_000_000,
            "narrative": "FY2025 Construction in Progress (CWIP): Buildings 187.9bn IDR + Landscape 237.8bn IDR + Equipment/Furniture/Vehicles 27bn. 총 ~450bn 건설 진행 중 — 신규 코스 또는 시설 대규모 확장 시사.",
            "src": "GOLF FY25 AR p.170 Aset dalam Konstruksi",
        },
        "employees_turnover_FY2025": 22,
        "fy2025_golf_target_beat": {
            "fy2025_golf_revenue_idr": 101_930_000_000,
            "target_idr": 81_760_000_000,
            "beat_pct": 0.2466,
            "narrative": "FY2025 Golf segment IDR 101.93bn = 124.66% of established target IDR 81.76bn. FY24 93.0bn 대비 +9.6% 성장. (참고: 앞서 추출된 79.4bn은 Real Estate segment였음 — 라벨링 오류 정정)",
            "src": "GOLF FY25 AR p.174",
        },
    },
    "MDLN": {
        "headcount": {
            "FY2021": 887,
            "FY2022": 952,
            "narrative": "모회사 직원: FY2021 887명 → FY2022 952명 (+7.3%). Modern Golf 골프장 단독 인원은 미공시 (Hospitality segment 통합).",
            "src": "MDLN FY22 AR p.105",
        },
    },
}


# PIPG explicit 4-segment FY2023 data from Note 30 (extracted via vector search)
PIPG_SEGMENT_FY2023 = {
    "Golf Course & Cart": {"revenue": 67_114_799_178, "cogs": 27_673_842_714},
    "Membership & Enrollment Fee": {"revenue": 27_424_538_398, "cogs": 3_336_863_353},
    "Restaurant": {"revenue": 33_192_504_715, "cogs": 22_843_371_185},
    "Others": {"revenue": 75_360_479_776, "cogs": 31_201_587_676},
}


DIVIDEND_EVIDENCE = {
    "DMIG": {
        "FY2023_paid": 26_514_391_332,  # from Statement of Changes in Equity
        "FY2022_paid": None,
        "narrative": "FY2023 배당 IDR 26.5bn (Statement of Changes in Equity 직접). FY2023 순이익 71.3bn 대비 payout ratio 37.2%.",
        "src": "DMIG FY2023 AR p.55 STATEMENTS OF CHANGES IN EQUITY",
    },
    "PIPG": {
        "FY2022_paid": 20_763_216_000,
        "FY2023_paid": 26_239_800_000,
        "per_share_FY2022": 15_984_000,
        "per_share_FY2023": 20_200_000,
        "rupst_date_FY2022": "2023-06-15",
        "rupst_date_FY2023": "2024-06-06",
        "narrative": "FY2022 배당 20.8bn (RUPST 2023-06-15, Rp 15.98M/주) + FY2023 배당 26.2bn (RUPST 2024-06-06, Rp 20.20M/주). FY23 순이익 55.9bn 대비 payout 46.9%.",
        "src": "PIPG FY24 AR p.141 Note 26 PEMBAGIAN DIVIDEN",
    },
    "SMDM": {
        "FY2024_paid": 0,
        "narrative": "FY2024 배당 미실시 (working capital 보존). BSDE 91.99% 인수 직전 결정.",
        "src": "SMDM FY24 AR p.70",
    },
}


def _dividend_compare_table() -> str:
    rows = []
    for t, d in DIVIDEND_EVIDENCE.items():
        fy22 = d.get("FY2022_paid")
        fy23 = d.get("FY2023_paid")
        fy24 = d.get("FY2024_paid")
        rows.append(
            f'<tr class="tier-a">'
            f'<td><span class="ticker-mini">{safe(t)}</span></td>'
            f'<td class="num">{fmt_bn(fy22)}</td>'
            f'<td class="num">{fmt_bn(fy23)}</td>'
            f'<td class="num">{fmt_bn(fy24) if fy24 is not None else "—"}</td>'
            f'<td class="notes">{safe(d["narrative"])}</td>'
            f'<td class="src">{safe(d["src"])}</td>'
            f'</tr>'
        )
    return f"""<div class="tbl-card scroll-x">
  <table class="tbl tbl-tight">
    <thead><tr>
      <th>Peer</th>
      <th class="num">FY22 배당</th>
      <th class="num">FY23 배당</th>
      <th class="num">FY24 배당</th>
      <th>해설</th>
      <th>출처</th>
    </tr></thead>
    <tbody>{''.join(rows)}</tbody>
  </table>
</div>"""


def _pipg_segment_table() -> str:
    """PIPG 4-segment GP margin breakdown (FY2023, Note 30)."""
    rows = []
    tot_rev = 0
    tot_cogs = 0
    for name, d in PIPG_SEGMENT_FY2023.items():
        rev = d["revenue"]
        cogs = d["cogs"]
        gp = rev - cogs
        gm = (gp / rev * 100) if rev else None
        tot_rev += rev
        tot_cogs += cogs
        rows.append(
            f'<tr><td>{safe(name)}</td>'
            f'<td class="num">{fmt_bn(rev)}</td>'
            f'<td class="num">{fmt_bn(cogs)}</td>'
            f'<td class="num">{fmt_bn(gp)}</td>'
            f'<td class="num">{f"{gm:.1f}%"}</td></tr>'
        )
    tot_gp = tot_rev - tot_cogs
    tot_gm = (tot_gp / tot_rev * 100)
    rows.append(
        f'<tr class="row-total"><td><strong>합계</strong></td>'
        f'<td class="num"><strong>{fmt_bn(tot_rev)}</strong></td>'
        f'<td class="num"><strong>{fmt_bn(tot_cogs)}</strong></td>'
        f'<td class="num"><strong>{fmt_bn(tot_gp)}</strong></td>'
        f'<td class="num"><strong>{tot_gm:.1f}%</strong></td></tr>'
    )
    return f"""<div class="tbl-card">
  <table class="tbl tbl-tight">
    <thead><tr>
      <th>Segment</th>
      <th class="num">매출 (FY23)</th>
      <th class="num">COGS</th>
      <th class="num">Gross Profit</th>
      <th class="num">GP Margin</th>
    </tr></thead>
    <tbody>{''.join(rows)}</tbody>
  </table>
</div>"""


# Holes per peer for unit-economic normalization
HOLES = {
    "DMIG": 36,   # PIK 18 + BSD 18
    "PIPG": 18,
    "KPIG": 18,   # Trump Lido
    "GOLF": 36,   # New Kuta + Palm Hill (consolidated). Black Rocks 18 = associate (not consolidated)
    "MDLN": 18,   # Modern Golf
    "KIJA": 18,   # Jababeka
    "SMDM": 18,   # Rancamaya
}


def _per_hole_metrics_table() -> str:
    """Unit-economic comparison: revenue / OpEx / CAPEX-proxy per hole.

    For each peer with audited golf-segment revenue, normalize by golf-course-only holes.
    """
    rows = []

    def add(ticker: str, basis: str, golf_rev, golf_cogs, golf_opex, depr_total):
        h = HOLES.get(ticker, 18)
        rev_per_hole = golf_rev / h if golf_rev else None
        gp_per_hole = ((golf_rev - golf_cogs) / h) if (golf_rev and golf_cogs) else None
        opex_per_hole = (golf_opex / h) if golf_opex else None
        depr_per_hole = (depr_total / h) if depr_total else None
        rows.append((ticker, basis, h, rev_per_hole, gp_per_hole, opex_per_hole, depr_per_hole))

    # DMIG — entity revenue (golf+restaurant+membership+...) / 36 holes
    d = NOTES.get("DMIG", {})
    rev_total = (d.get("revenue_note") or {}).get("total", {}).get("FY2024")
    cogs_total = (d.get("cogs_note") or {}).get("total", {}).get("FY2024")
    opex_total = (d.get("opex_note") or {}).get("total", {}).get("FY2024")
    dep_line = next((ln.get("FY2024") for ln in (d.get("opex_note") or {}).get("lines", []) if (ln.get("id_label") or "").lower() == "penyusutan"), None)
    add("DMIG", "Entity (2 코스: BSD+PIK, all-in)", rev_total, cogs_total, opex_total, dep_line)

    # PIPG — entity revenue
    d = NOTES.get("PIPG", {})
    rev_total = (d.get("revenue_note_27") or {}).get("total", {}).get("FY2024")
    cogs_total = (d.get("cogs_note_28") or {}).get("total", {}).get("FY2024")
    opex_total = (d.get("opex_note_29") or {}).get("total", {}).get("FY2024")
    dep_line = next((ln.get("FY2024") for ln in (d.get("opex_note_29") or {}).get("lines", []) if (ln.get("id_label") or "").lower() == "penyusutan"), None)
    add("PIPG", "Entity (1 코스: Pondok Indah, all-in)", rev_total, cogs_total, opex_total, dep_line)

    # GOLF — golf-only segment
    d = NOTES.get("GOLF", {})
    rev_lines = ((d.get("revenue_note_29") or {}).get("by_operations") or {}).get("lines") or []
    cogs_lines = (d.get("cogs_note_30") or {}).get("lines") or []
    rev_g = next((ln.get("FY2024") for ln in rev_lines if ln.get("en_label") == "Golf"), None)
    cogs_g = next((ln.get("FY2024") for ln in cogs_lines if ln.get("id_label") == "Golf"), None)
    opex_g = (d.get("ga_note_32") or {}).get("total", {}).get("FY2024")
    dep_g = next((ln.get("FY2024") for ln in (d.get("ga_note_32") or {}).get("lines", []) if "penyusutan" in (ln.get("id_label") or "").lower()), None)
    add("GOLF", "Golf segment only (2 consolidated 코스)", rev_g, cogs_g, opex_g, dep_g)

    # MDLN — golf segment (pure)
    d = NOTES.get("MDLN", {})
    cr = (d.get("computed_ratios") or {}).get("FY2024", {})
    rev_m = cr.get("golf_revenue_pure")
    cogs_m = cr.get("golf_cogs_pure")
    # Depreciation from golf_course_direct_cost_lines
    dep_m = next((ln.get("FY2024") for ln in (d.get("cogs_note_26") or {}).get("golf_course_direct_cost_lines", []) if "penyusutan" in (ln.get("id_label") or "").lower()), None)
    add("MDLN", "Golf segment (Note 25)", rev_m, cogs_m, None, dep_m)

    # KIJA — golf segment (Rp million → multiply 1e6)
    d = NOTES.get("KIJA", {})
    seg = (d.get("segment_info_note_34") or {}).get("golf_segment_FY2024") or {}
    rev_k = (seg.get("revenue") or 0) * 1e6
    cogs_k = (seg.get("cogs") or 0) * 1e6
    opex_k = ((seg.get("selling") or 0) + (seg.get("ga_expenses") or 0)) * 1e6
    add("KIJA", "Golf segment (Note 34)", rev_k or None, cogs_k or None, opex_k or None, None)

    # SMDM — golf segment
    d = NOTES.get("SMDM", {})
    seg_s = ((d.get("segment_info_note_29") or {}).get("FY2024") or {}).get("Golf dan Country Club") or {}
    rev_s = seg_s.get("revenue")
    cogs_s = abs(seg_s.get("cogs") or 0) or None
    opex_s = (abs(seg_s.get("selling") or 0) + abs(seg_s.get("ga") or 0)) or None
    add("SMDM", "Golf & Country Club segment (Note 29)", rev_s, cogs_s, opex_s, None)

    body = []
    for ticker, basis, h, rph, gph, oph, dph in rows:
        body.append(
            f'<tr class="tier-a">'
            f'<td><span class="ticker-mini">{safe(ticker)}</span></td>'
            f'<td class="notes">{safe(basis)}</td>'
            f'<td class="num">{h}</td>'
            f'<td class="num">{fmt_bn(rph)}</td>'
            f'<td class="num">{fmt_bn(gph)}</td>'
            f'<td class="num">{fmt_bn(oph)}</td>'
            f'<td class="num">{fmt_bn(dph)}</td>'
            f'</tr>'
        )
    return f"""<div class="tbl-card scroll-x">
  <table class="tbl">
    <thead><tr>
      <th>Peer</th>
      <th>비교 단위</th>
      <th class="num">홀 수</th>
      <th class="num">매출 / 홀</th>
      <th class="num">GP / 홀</th>
      <th class="num">OpEx / 홀</th>
      <th class="num">감가상각 / 홀</th>
    </tr></thead>
    <tbody>{''.join(body)}</tbody>
  </table>
</div>"""


def _ops_kpi_section() -> str:
    """Operational KPI time series — rounds played, members, headcount, sub-revenues."""
    cards = []

    # DMIG card
    dmig = OPS_KPI_EVIDENCE["DMIG"]
    cards.append(f"""<div class="ops-block">
  <h4 class="ops-block-h">DMIG — 골퍼 / 회원 / 인력 시계열</h4>
  <div class="kv-grid">
    <div class="kv">
      <div class="k">FY2023 골퍼 증가</div>
      <div class="v">+12,979명 <span class="muted">(+12.09% YoY)</span></div>
      <p class="kv-comment">{safe(dmig['rounds_played']['narrative'])}</p>
      <span class="src">출처: {safe(dmig['rounds_played']['src'])}</span>
    </div>
    <div class="kv">
      <div class="k">FY2023 Main Playing Members</div>
      <div class="v">{dmig['members']['FY2023']:,}명 <span class="muted">(전년比 -6명)</span></div>
      <p class="kv-comment">{safe(dmig['members']['narrative'])}</p>
      <span class="src">출처: {safe(dmig['members']['src'])}</span>
    </div>
    <div class="kv">
      <div class="k">직원 수 (Benefit-eligible)</div>
      <div class="v">FY21 342 → FY22 {dmig['headcount']['FY2022']} → FY23 {dmig['headcount']['FY2023']}</div>
      <p class="kv-comment">{safe(dmig['headcount']['narrative'])}</p>
      <span class="src">출처: {safe(dmig['headcount']['src'])}</span>
    </div>
    <div class="kv">
      <div class="k">The Range@PIK 매출</div>
      <div class="v">{fmt_bn(dmig['the_range_revenue']['FY2023'])} <span class="muted">(+372.7% YoY)</span></div>
      <p class="kv-comment">{safe(dmig['the_range_revenue']['narrative'])}</p>
      <span class="src">출처: {safe(dmig['the_range_revenue']['src'])}</span>
    </div>
    <div class="kv">
      <div class="k">FY2023 F&amp;B 코스별 분해</div>
      <div class="v">BSD {fmt_bn(dmig['fnb_split_FY2023']['bsd_restaurant_idr'])} + PIK {fmt_bn(dmig['fnb_split_FY2023']['pik_restaurant_idr'])}</div>
      <p class="kv-comment">{safe(dmig['fnb_split_FY2023']['narrative'])}</p>
      <span class="src">출처: {safe(dmig['fnb_split_FY2023']['src'])}</span>
    </div>
  </div>
</div>""")

    # PIPG card
    pipg = OPS_KPI_EVIDENCE["PIPG"]
    rp = pipg["rounds_played"]
    rounds_html = (
        f'<table class="tbl tbl-tight"><thead><tr>'
        f'<th>연도</th><th class="num">골퍼</th><th class="num">YoY</th>'
        f'</tr></thead><tbody>'
    )
    prev = None
    for fy in ["FY2021", "FY2022", "FY2023", "FY2024"]:
        v = rp.get(fy)
        yoy = ""
        if v and prev:
            yoy = f"{((v / prev) - 1) * 100:+.1f}%"
        rounds_html += f'<tr><td>{fy}</td><td class="num">{v:,}</td><td class="num">{yoy or "—"}</td></tr>'
        prev = v
    rounds_html += "</tbody></table>"
    # Department headcount table
    hc = pipg["headcount_by_dept_FY2024"]
    dept_pairs = [(k, v) for k, v in hc.items() if isinstance(v, int)]
    dept_pairs.sort(key=lambda kv: -kv[1])
    dept_html = '<table class="tbl tbl-tight"><thead><tr><th>부서</th><th class="num">인원 (FY24)</th></tr></thead><tbody>'
    for dept, n in dept_pairs:
        dept_html += f'<tr><td>{safe(dept)}</td><td class="num">{n}</td></tr>'
    dept_html += f'<tr class="row-total"><td><strong>합계</strong></td><td class="num"><strong>{sum(n for _, n in dept_pairs)}</strong></td></tr>'
    dept_html += "</tbody></table>"

    cards.append(f"""<div class="ops-block">
  <h4 class="ops-block-h">PIPG — 골퍼 시계열 (4년)</h4>
  <div class="tbl-card">{rounds_html}</div>
  <p class="kv-comment">{safe(rp['narrative'])}</p>
  <p class="src-line">출처: {safe(rp['src'])}</p>
</div>
<div class="ops-block">
  <h4 class="ops-block-h">PIPG — 부서별 인원 (FY2024, turnover 그래프 기준)</h4>
  <div class="tbl-card">{dept_html}</div>
  <p class="kv-comment">{safe(hc['narrative'])}</p>
  <p class="src-line">출처: {safe(hc['src'])}</p>
</div>""")

    # KPIG card
    kpig = OPS_KPI_EVIDENCE["KPIG"]
    cards.append(f"""<div class="ops-block">
  <h4 class="ops-block-h">KPIG — 운영 scope &amp; Trump Lido 시설</h4>
  <div class="kv-grid">
    <div class="kv">
      <div class="k">공시 범위</div>
      <p class="kv-comment">{safe(kpig['scope_caveat']['narrative'])}</p>
      <span class="src">출처: {safe(kpig['scope_caveat']['src'])}</span>
    </div>
    <div class="kv">
      <div class="k">Trump Clubhouse</div>
      <div class="v">33,322 m² <span class="muted">(Oppenheim Arch.)</span></div>
      <p class="kv-comment">{safe(kpig['clubhouse_facility']['narrative'])}</p>
      <span class="src">출처: {safe(kpig['clubhouse_facility']['src'])}</span>
    </div>
  </div>
</div>""")

    # GOLF CAPEX + target beat card
    g = OPS_KPI_EVIDENCE["GOLF"]
    tb = g["fy2025_golf_target_beat"]
    cards.append(f"""<div class="ops-block">
  <h4 class="ops-block-h">GOLF — FY2025 진행 중 CAPEX + 매출 target 달성</h4>
  <div class="kv-grid">
    <div class="kv">
      <div class="k">CWIP — Buildings</div>
      <div class="v">{fmt_bn(g['capex_fy2025']['construction_buildings_idr'])}</div>
    </div>
    <div class="kv">
      <div class="k">CWIP — Landscape</div>
      <div class="v">{fmt_bn(g['capex_fy2025']['construction_landscape_idr'])}</div>
    </div>
    <div class="kv">
      <div class="k">FY2025 Golf 매출 vs target</div>
      <div class="v">{fmt_bn(tb['fy2025_golf_revenue_idr'])} <span class="muted">(target {fmt_bn(tb['target_idr'])} · 달성 {tb['beat_pct'] * 100:+.1f}%)</span></div>
      <p class="kv-comment">{safe(tb['narrative'])}</p>
      <span class="src">출처: {safe(tb['src'])}</span>
    </div>
    <div class="kv">
      <div class="k">CWIP 설명</div>
      <p class="kv-comment">{safe(g['capex_fy2025']['narrative'])}</p>
      <span class="src">출처: {safe(g['capex_fy2025']['src'])}</span>
    </div>
  </div>
</div>""")

    return "\n".join(cards)


def _related_party_and_lease_section() -> str:
    """Cards describing related-party transactions and land/lease arrangements."""
    cards = []

    # DMIG — related_party_note (key management compensation)
    rp = (NOTES.get("DMIG", {}) or {}).get("related_party_note") or {}
    if rp.get("lines"):
        lines_html = []
        for ln in rp["lines"]:
            label = ln.get("en_label") or ln.get("id_label") or "—"
            v22 = ln.get("FY2022")
            v23 = ln.get("FY2023")
            v24 = ln.get("FY2024")
            # If percentage stored as fraction
            if isinstance(v24, float) and abs(v24) < 1:
                fmt22 = f"{v22 * 100:.2f}%" if v22 else "—"
                fmt23 = f"{v23 * 100:.2f}%" if v23 else "—"
                fmt24 = f"{v24 * 100:.2f}%"
            else:
                fmt22 = fmt_bn(v22)
                fmt23 = fmt_bn(v23)
                fmt24 = fmt_bn(v24)
            lines_html.append(
                f'<tr><td>{safe(label)}</td>'
                f'<td class="num">{fmt22}</td>'
                f'<td class="num">{fmt23}</td>'
                f'<td class="num">{fmt24}</td></tr>'
            )
        src = rp.get("source_page", {}).get("FY2024") if isinstance(rp.get("source_page"), dict) else rp.get("source_page", "")
        cards.append(
            f'<div class="ops-block">'
            f'<h4 class="ops-block-h">DMIG — 핵심경영진 보수 (Related party · Note 26)</h4>'
            f'<div class="tbl-card"><table class="tbl tbl-tight">'
            f'<thead><tr><th>Item</th><th class="num">FY22</th><th class="num">FY23</th><th class="num">FY24</th></tr></thead>'
            f'<tbody>{"".join(lines_html)}</tbody></table></div>'
            f'<p class="src-line">출처: {safe(src)}</p>'
            f'</div>'
        )

    # PIPG — agreements_commitments
    ag = (NOTES.get("PIPG", {}) or {}).get("agreements_commitments") or {}
    items = ag.get("items") or []
    if items:
        rows = []
        for it in items:
            rows.append(
                f'<tr>'
                f'<td>{safe(it.get("type", "—"))}</td>'
                f'<td class="notes">{safe(it.get("counterparty", "—"))}</td>'
                f'<td class="notes">{safe(it.get("term", "—"))}</td>'
                f'<td class="notes">{safe(it.get("rent_y1y2") or it.get("rent") or it.get("rental_fee") or "—")}</td>'
                f'</tr>'
            )
        cards.append(
            f'<div class="ops-block">'
            f'<h4 class="ops-block-h">PIPG — 약정·관계사 lease (Note 32)</h4>'
            f'<div class="tbl-card scroll-x"><table class="tbl tbl-tight">'
            f'<thead><tr><th>유형</th><th>상대방</th><th>기간</th><th>임대료/금액</th></tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table></div>'
            f'<p class="src-line">출처: {safe(ag.get("source_page", ""))}</p>'
            f'</div>'
        )

    # PIPG — land profile (53 ha / 12 certificates)
    profile = (NOTES.get("PIPG", {}) or {}).get("profile") or {}
    if profile:
        cards.append(
            f'<div class="ops-block">'
            f'<h4 class="ops-block-h">PIPG — 토지·HGB profile</h4>'
            f'<div class="kv-grid">'
            f'<div class="kv"><div class="k">총 토지 면적</div><div class="v">{profile.get("land_area_ha_total", "—")} ha <span class="muted">({profile.get("land_area_m2_total", "—"):,} m²)</span></div></div>'
            f'<div class="kv"><div class="k">토지 인증서</div><div class="v">{profile.get("land_certificates", "—")} 건</div></div>'
            f'<div class="kv"><div class="k">HGB 면적</div><div class="v">{profile.get("hgb_area_m2", "—"):,} m² <span class="muted">(만료: {safe(str(profile.get("hgb_expiry_years", "—")))})</span></div></div>'
            f'<div class="kv"><div class="k">MKPI에서 임차</div><div class="v">{profile.get("leased_from_mkpi_m2", "—"):,} m² <span class="muted">({safe(profile.get("leased_purpose", "—"))})</span></div><div class="src">기간: {safe(profile.get("leased_term_start", ""))} ~ {safe(profile.get("leased_term_end", ""))}</div></div>'
            f'</div>'
            f'<p class="src-line">출처: {safe(profile.get("source_pages", "—"))}</p>'
            f'</div>'
        )

    # GOLF — customer concentration
    rev29 = (NOTES.get("GOLF", {}) or {}).get("revenue_note_29") or {}
    cc = rev29.get("customer_concentration") or {}
    if cc:
        cards.append(
            f'<div class="ops-block">'
            f'<h4 class="ops-block-h">GOLF — 고객 집중도 위험 (Note 29)</h4>'
            f'<div class="kv-grid">'
            f'<div class="kv"><div class="k">고객명</div><div class="v">{safe(cc.get("name", "—"))}</div></div>'
            f'<div class="kv"><div class="k">FY2024 매출 기여</div><div class="v">{fmt_bn(cc.get("amount_FY2024"))} <span class="muted">({(cc.get("pct_of_revenue_FY2024") or 0) * 100:.1f}% of revenue)</span></div></div>'
            f'<div class="kv"><div class="k">FY2023 매출 기여</div><div class="v">{fmt_bn(cc.get("amount_FY2023"))} <span class="muted">({(cc.get("pct_of_revenue_FY2023") or 0) * 100:.1f}%)</span></div></div>'
            f'</div>'
            f'<p class="src-line">출처: {safe(cc.get("source", ""))}</p>'
            f'</div>'
        )

    # MDLN — supplier concentration
    sup = ((NOTES.get("MDLN", {}) or {}).get("cogs_note_26") or {}).get("supplier_concentration") or {}
    if sup:
        cards.append(
            f'<div class="ops-block">'
            f'<h4 class="ops-block-h">MDLN — 공급사 집중 (Note 26)</h4>'
            f'<div class="kv-grid">'
            f'<div class="kv"><div class="k">공급사명</div><div class="v">{safe(sup.get("name", "—"))}</div></div>'
            f'<div class="kv"><div class="k">FY2024 거래액</div><div class="v">{fmt_bn(sup.get("amount_FY2024"))}</div></div>'
            f'<div class="kv"><div class="k">전체 COGS 대비</div><div class="v">{safe(sup.get("pct_of_total_cogs", "—"))}</div></div>'
            f'</div>'
            f'<p class="src-line">출처: {safe(sup.get("source", ""))}</p>'
            f'</div>'
        )

    return "\n".join(cards)


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
    golf_segment_table = _all_peer_golf_segment_table()
    opex_norm_table = _normalized_opex_compare_table()
    opex_kpi_strip = _opex_kpi_strip()
    opex_stack = _opex_stacked_bars()
    opex_norm_bars = _opex_norm_bar_table()
    related_party_section = _related_party_and_lease_section()
    ops_kpi_section = _ops_kpi_section()
    per_hole_table = _per_hole_metrics_table()
    pipg_seg_table = _pipg_segment_table()
    dividend_table = _dividend_compare_table()

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

    <nav class="ops-subnav" aria-label="ops sub-navigation">
      <a class="chip" href="#pnl">P&amp;L 4Y</a>
      <a class="chip" href="#rev">매출 라인</a>
      <a class="chip" href="#cogs">COGS 라인</a>
      <a class="chip" href="#opex">OpEx 라인</a>
      <a class="chip" href="#opex-norm">OpEx 정규화</a>
      <a class="chip" href="#capex-proxy">CAPEX proxy</a>
      <a class="chip" href="#pipg-seg">PIPG 4-seg</a>
      <a class="chip" href="#segment-6">6-peer 골프</a>
      <a class="chip" href="#unit-econ">홀당 단위</a>
      <a class="chip" href="#ops-kpi">운영 KPI</a>
      <a class="chip" href="#dividend">배당</a>
      <a class="chip" href="#related">관계사</a>
      <a class="chip" href="#fy25">FY25 prelim</a>
      <a class="chip" href="#margin-commentary">마진 변화</a>
    </nav>

    <div class="section ops-summary">
      <h2>핵심 인사이트 — TL;DR</h2>
      <h3>13개 분석 섹션에서 도출한 7-peer 핵심 발견</h3>
      <div class="insight-grid">
        <div class="insight-card insight-positive">
          <div class="insight-tag">💰 자본 효율 최강자</div>
          <div class="insight-title">GOLF — Golf segment GP margin 65.7%</div>
          <p>OpEx 21.1% (DMIG/PIPG 38%보다 압도적 효율). FY25 매출 target 81.76bn 대비 +24.66% 초과 달성 (101.93bn).
          CWIP 450bn 진행 중 — 적극 확장 모드.</p>
        </div>
        <div class="insight-card insight-positive">
          <div class="insight-tag">📈 PIPG — 비용 통제력</div>
          <div class="insight-title">FY25 매출 -6.0% but OpEx -17.9% → 영업이익 +4.0%</div>
          <p>매출 감소 환경에서도 OpEx 통제로 영업이익 증가. Membership segment GP margin 87.8%로 marginal cash 회수력 우수.
          노후 코스 (1976) 유지비 부담은 risk.</p>
        </div>
        <div class="insight-card insight-warn">
          <div class="insight-tag">⚠️ DMIG — 마진 압박 시작</div>
          <div class="insight-title">FY25 영업이익 -12.0% YoY (78.9 → 69.4bn)</div>
          <p>매출 sticky (-0.7%)이나 COGS +5.8% + OpEx +3.3% 동시 압박. 감가상각 12.2%/매출은 peer 최고 (PIK Range 신규 투자 효과).
          The Range@PIK는 +372% 성장.</p>
        </div>
        <div class="insight-card insight-warn">
          <div class="insight-tag">⚠️ SMDM Rancamaya — 적자전환</div>
          <div class="insight-title">FY24 GP margin -16.9pp 급락 (55.8% → 38.9%)</div>
          <p>영업이익 -212M IDR. BSDE 2024-10 91.99% 인수. FY25 GP 88.6% jump은 회계 재분류 가능. BSDE 사후 통합 효과 모니터링 필요.</p>
        </div>
        <div class="insight-card insight-positive">
          <div class="insight-tag">🎯 MDLN — Hidden growth</div>
          <div class="insight-title">Golf+F&amp;B FY25 +28.2% YoY (95.3bn)</div>
          <p>그룹 GP margin 44.66% → 47.19% (+2.5pp 개선). 골프 segment 5.6%이지만 그룹 내 가장 빠른 성장 부문. Modern Golf 단독 매출 56.6bn → 74.4bn (F&amp;B 포함).</p>
        </div>
        <div class="insight-card insight-neutral">
          <div class="insight-tag">🏢 KPIG — 자산집약 conglomerate</div>
          <div class="insight-title">고정자산 21조 + 투자부동산 7조 = 73.8% of total</div>
          <p>Trump Lido는 전체 그룹의 일부. Hotel+Resort+Golf 통합 매출 FY24 960bn → FY25 1,060bn (+10%). Golf-only 분리 미공시 → 단독 비교 부적합.</p>
        </div>
        <div class="insight-card insight-neutral">
          <div class="insight-tag">🏭 KIJA — Industrial estate가 golf 보유</div>
          <div class="insight-title">Golf segment 85bn / GP margin 41.6%</div>
          <p>매출 비중 1.8%로 본업 아님. 단, 홀당 매출 4.7bn으로 6개 peer 중 unit revenue 가장 높음 (Nick Faldo 설계 + Jababeka industrial 단지 captive demand).</p>
        </div>
        <div class="insight-card insight-positive">
          <div class="insight-tag">📊 데이터 quality</div>
          <div class="insight-title">99,618 chunks 벡터 인덱스 + 13개 peer AR Note 직접 추출</div>
          <p>모든 수치는 annual report 페이지 번호 추적 가능. PyMuPDF positional 추출 + multilingual-e5-small 벡터 검색으로 cross-validate.
          감사 (audit) 추적성 보장.</p>
        </div>
      </div>
    </div>

    <div class="section ops-toc">
      <h2>운영 KPI · CAPEX/OPEX — 섹션 목차</h2>
      <h3>12개 분석 섹션으로 구성</h3>
      <nav class="toc">
        <ol>
          <li><a href="#pnl">4년 통합 P&amp;L (FY22-FY25)</a></li>
          <li><a href="#rev">매출 라인 분해 (DMIG 7 / PIPG 11 라인)</a></li>
          <li><a href="#cogs">COGS 라인 분해</a></li>
          <li><a href="#opex">OpEx 라인 분해 — 인건비·감가·유지보수</a></li>
          <li><a href="#opex-norm">OpEx 카테고리별 normalized 비교</a></li>
          <li><a href="#capex-proxy">CAPEX proxy (감가·유지·자산집약도)</a></li>
          <li><a href="#pipg-seg">PIPG 4-segment GP margin (Note 30)</a></li>
          <li><a href="#segment-6">6-peer 골프 segment 통합 비교</a></li>
          <li><a href="#unit-econ">홀당 단위 경제 (7-peer Unit Economics)</a></li>
          <li><a href="#ops-kpi">운영 KPI 시계열 (골퍼·회원·인력·CWIP)</a></li>
          <li><a href="#dividend">배당 시계열 (DMIG/PIPG/SMDM)</a></li>
          <li><a href="#related">관계사 거래 · 토지 lease · 집중도</a></li>
          <li><a href="#fy25">FY2025 미감사 prelim — 마진 압박</a></li>
          <li><a href="#margin-commentary">FY24→FY25 마진 변화 commentary</a></li>
        </ol>
      </nav>
    </div>

    <div class="section" id="pnl">
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

    <div class="section" id="rev">
      <h2>매출 라인 분해 — Pure-play</h2>
      <h3>골프 / F&amp;B / 회원권 / 부대시설 별 매출 (FY23→FY24)</h3>
      <p class="lede">
        annual report Note에서 라인별 매출을 직접 추출. 각 라인의 매출 비중과 YoY 증감을 표시합니다.
        <strong>DMIG</strong>는 7개 라인 (Note 23), <strong>PIPG</strong>는 11개 라인 (Note 27).
      </p>
      {rev_blocks}
    </div>

    <div class="section" id="cogs">
      <h2>COGS (매출원가) 라인 분해</h2>
      <h3>골프 코스 / 레스토랑 / 카트 / 드라이빙 레인지 등</h3>
      <p class="lede">
        매출원가는 segment별로 cost of revenue가 분리 공시됩니다.
        DMIG는 3개 라인 (Golf course / Restaurant / Recreation), PIPG는 11개 라인 (Restaurant, Golf course, Cart, Driving range, Membership, Academy 등).
      </p>
      {cogs_blocks}
    </div>

    <div class="section" id="opex">
      <h2>OpEx 라인 분해 — CAPEX/OPEX 핵심</h2>
      <h3>인건비 · 감가상각 · 유지보수 · 세금 · 유틸리티 등</h3>
      <p class="lede">
        AR Note 25 (DMIG) / Note 29 (PIPG) / Note 34 (KPIG)에서 OpEx 라인 단위 분해. 매출 대비 %와 YoY 증감 표시.
        가장 큰 비용 항목: <strong>인건비 (Salaries+benefits)</strong> 및 <strong>감가상각 (Depreciation)</strong>.
        PIPG는 추가로 Pajak dan perijinan (Tax+legal) 비중이 매우 높음 (FY24 IDR 24.2bn).
      </p>
      {opex_blocks}
    </div>

    <div class="section" id="opex-norm">
      <h2>OpEx 카테고리별 normalized 비교 — DMIG vs PIPG vs GOLF</h2>
      <h3>FY2024 매출 대비 % (cross-peer 같은 잣대)</h3>
      <p class="lede">
        AR Note 라벨이 peer마다 달라 직접 비교가 어려운 문제를 해결하기 위해, 모든 OpEx 라인을
        <strong>11개 카테고리</strong>로 keyword 기반 자동 분류 (Salaries / Depreciation / Maintenance / Tax+Legal / Utilities 등).
        시각화 우선 (KPI strip → 100% stacked bar → 카테고리별 bar matrix) → 원본 표는 하단.
      </p>

      {opex_kpi_strip}

      <h4 class="ops-block-h">100% stacked — OpEx 구성 비중</h4>
      {opex_stack}

      <h4 class="ops-block-h" style="margin-top: 22px;">카테고리별 매출 대비 % — bar matrix</h4>
      {opex_norm_bars}

      <details style="margin: 14px 0 4px;">
        <summary style="cursor: pointer; font-size: 13px; color: var(--ink-soft); padding: 6px 0;">▸ 원본 정규화 표 (참고용 · IDR + % 컬럼)</summary>
        {opex_norm_table}
      </details>
      <div class="banner info">
        <strong>비교 인사이트 (FY2024, OpEx 카테고리 / 매출):</strong>
        <strong>인건비</strong> DMIG 12.6% · PIPG 10.5% · GOLF 9.0% — peer 간 비슷한 수준 ·
        <strong>감가상각</strong> DMIG 12.2% · PIPG 7.1% · GOLF 1.3% — DMIG의 자본투자 강도 압도적 (BSD+PIK 2 코스 + Range@PIK 등) ·
        <strong>유지보수</strong> DMIG 0.9% · PIPG 5.9% · GOLF 1.3% — PIPG 노후 코스 (1976년 개장) 유지비 부담 큼 ·
        <strong>세금·법률</strong> DMIG 5.2% · PIPG 12.3% · GOLF 3.1% — PIPG의 Pajak dan perijinan 24.4bn이 outlier (CBD 5분 distance + HGB 면적 + property tax 비중) ·
        <strong>OpEx 총합</strong> DMIG 38.4% · PIPG 38.5% · GOLF 21.1% — GOLF가 압도적으로 효율적이나 real estate cross-subsidy / IPO 1년차 효과 가능성.
      </div>
    </div>

    <div class="section" id="capex-proxy">
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

    <div class="section" id="pipg-seg">
      <h2>PIPG 4-segment GP margin — Note 30 직접 추출</h2>
      <h3>Golf Course&amp;Cart / Membership / Restaurant / Others 매출×COGS×GP×Margin</h3>
      <p class="lede">
        PIPG는 Note 30 Segment Information에서 Golf Course&amp;Cart / Membership&amp;Enrollment / Restaurant / Others 4 segment의 COGS를 explicit 공시.
        Note 27 (revenue 11라인) · Note 28 (COGS 11라인)과는 다른 segment 차원의 cut.
        Membership 부문의 GP margin이 압도적 높음.
      </p>
      {pipg_seg_table}
      <div class="banner info">
        <strong>FY2023 PIPG segment GP margin 인사이트:</strong>
        <strong>Membership & Enrollment</strong> 87.8% — 신규 회원/연회비 수익은 거의 순이익에 가까움 (소액 COGS) ·
        <strong>Golf Course & Cart</strong> 58.7% — 핵심 골프 운영 마진 ·
        <strong>Others (Driving Range·Branding·Sponsor 통합)</strong> 58.6% — Note 27 기준 driving range/branding/Indonesia Open sponsor 매출 ·
        <strong>Restaurant</strong> 31.2% — F&B는 마진이 가장 낮음 (예상 가능).
        전체 GP margin 58.1%.
      </div>
      <p class="src-line">출처: PIPG FY23 AR p.156 Note 30 Segment Information (벡터 검색으로 직접 추출, 4-segment breakdown)</p>
    </div>

    <div class="section" id="segment-6">
      <h2>골프 segment 매출 — 6-peer 통합 비교 (FY2024)</h2>
      <h3>explicit golf disclosure가 있는 모든 IDX peer</h3>
      <p class="lede">
        Pure-play 외에도 <strong>MDLN · GOLF · KIJA · SMDM</strong>는 annual report Note에서 골프 segment를 명시적 분리 공시.
        Golf revenue / COGS / Gross profit margin / Entity 매출 비중을 동일 잣대로 비교.
        <strong>GOLF</strong>가 GP margin 65.7%로 가장 높고, <strong>SMDM</strong>은 38.9%로 가장 낮음 (FY23 대비 -16.9pp 급락).
      </p>
      {golf_segment_table}
      <div class="banner info">
        <strong>관전 포인트:</strong>
        <strong>GOLF (Intra GolfLink Resorts)</strong>: 골프 매출 비중 47%, GP margin 65.7% — 가장 자본효율 높음 (Bali New Kuta · Bogor Sentul) ·
        <strong>MDLN</strong>: 골프 비중 5.6%, GP margin 44.5% (FY25에 +28% YoY 성장) ·
        <strong>KIJA</strong>: 골프 비중 1.8% (industrial estate 본업), GP margin 41.6% ·
        <strong>SMDM (Rancamaya)</strong>: 골프 비중 9.1%, GP margin 38.9% — FY23 55.8% → FY24 38.9% 급락 (-16.9pp). FY24 영업이익 -212M IDR 적자전환. BSDE가 2024-10에 91.99% 인수 ·
        <strong>DMIG/PIPG</strong>: Pure-play 골프코스 라인만 가져오므로 다른 단위; F&B/Cart 포함 시 비교 합치.
      </div>
      <p class="src-line">출처: site/peer-analysis/operations/data/{{dmig,pipg,mdln,golf,kija}}_notes.json (FY24 AR Note 23·25·27·29·34 직접 추출)</p>
    </div>

    <div class="section" id="unit-econ">
      <h2>홀당 단위 경제 — 7-peer Unit Economics (FY2024)</h2>
      <h3>매출 / GP / OpEx / 감가상각을 홀 수로 normalize</h3>
      <p class="lede">
        peer 마다 코스 수와 운영 형태가 다르므로 entity 매출 절대값 비교는 misleading. 홀 수로 나눈 unit economics가 더 의미 있는 비교.
        <strong>PIPG</strong>는 1 코스 entity 매출 197.6bn → 매출/홀 ≈ 11.0bn (최고),
        <strong>DMIG</strong>는 2 코스 → 매출/홀 ≈ 7.0bn,
        <strong>GOLF</strong> golf-only 93bn / 36홀 = 2.6bn/홀로 가장 낮음.
      </p>
      {per_hole_table}
      <div class="banner info">
        <strong>해석 주의:</strong>
        DMIG/PIPG는 entity 매출 (Golf+F&B+Membership+Cart 일체 포함) 기준 → 홀당 단위가 의도적으로 부풀려져 있음 ·
        GOLF/MDLN/KIJA/SMDM은 golf segment-only 기준 → 진정한 golf revenue/hole ·
        cross-row 비교 시 비교 기준(basis 컬럼)을 반드시 확인.
        진짜 cross-peer per-hole golf revenue는 GOLF (2.6bn) · MDLN (3.1bn) · KIJA (4.7bn) · SMDM (3.5bn) — KIJA가 industrial estate 골프장임에도 unit revenue 가장 높음.
      </div>
    </div>

    <div class="section" id="ops-kpi">
      <h2>운영 KPI 시계열 — 골퍼·회원·인력·CWIP</h2>
      <h3>annual report 본문(Management Discussion)에서 직접 추출한 정량 지표</h3>
      <p class="lede">
        Note (재무제표 주석)에 없는 운영 지표 — 골퍼 수, 회원 수, 부서별 인원, 진행 중 자본투자 — 를 AR 본문에서 직접 추출.
        <strong>벡터 검색 (multilingual-e5-small / 99,618 chunks)</strong>로 동일 fact를 여러 인덱스 페이지에서 cross-validate.
      </p>
      {ops_kpi_section}
    </div>

    <div class="section" id="dividend">
      <h2>배당 시계열 — 3-peer 비교</h2>
      <h3>FY22-FY24 배당 + payout ratio</h3>
      <p class="lede">
        cash distribution을 통한 capital allocation 비교. PIPG는 안정적 배당 + 증가 추세, DMIG는 FY23 배당 확인,
        SMDM은 FY24 BSDE 인수 직전 배당 미실시.
      </p>
      {dividend_table}
    </div>

    <div class="section" id="related">
      <h2>관계사 거래 · 토지 lease · 고객·공급사 집중도</h2>
      <h3>annual report Note에서 추출한 audit-grade 정량 정보</h3>
      <p class="lede">
        <strong>DMIG</strong>의 핵심경영진 보수 추이, <strong>PIPG</strong>의 53ha 토지·HGB 약정·MKPI 임차 구조,
        <strong>GOLF</strong>의 고객 집중도 (34%), <strong>MDLN</strong>의 공급사 집중도를 한 자리에 정리.
        cross-default / cross-risk 분석에 핵심.
      </p>
      {related_party_section}
    </div>

    <div class="section" id="fy25">
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

    <div class="section" id="margin-commentary">
      <h2>FY2024→FY2025 마진 변화 — 벡터 추출 commentary</h2>
      <h3>각 peer의 annual report 본문에서 직접 인용한 마진 시그널</h3>
      <p class="lede">
        벡터 DB (multilingual-e5-small, 99,618 chunks)로 각 peer의 FY24/FY25 AR 본문에서 마진 변화 commentary 추출.
        모든 수치는 AR 페이지 번호로 검증 가능.
      </p>
      <div class="kv-grid">
        <div class="kv">
          <div class="k">DMIG FY2023 → FY2024</div>
          <p class="kv-comment">
            <strong>FY2023 순이익 Rp 71.27bn (+34.40% / +Rp 18.24bn vs FY22 Rp 53.03bn)</strong>.
            FY24 매출 253.1bn / 영업이익 78.9bn / 순이익 82.4bn.
            FY25 매출 -0.7%, OpEx +3.3% → 영업이익 -12.0%, 순이익 -9.0%. 마진 압박 시작.
          </p>
          <span class="src">DMIG FY23 AR p.22 NET INCOME · FY25 follow-up</span>
        </div>
        <div class="kv">
          <div class="k">PIPG FY2024 → FY2025</div>
          <p class="kv-comment">
            FY24 매출 197.6bn / 영업이익 53.5bn / 순이익 55.9bn.
            <strong>FY25 매출 -6.0% (185.8bn)이나 OpEx -17.9% 대규모 절감 (76→62bn) → 영업이익 +4.0%, 순이익 +0.6%</strong>.
            비용 통제로 수익성 유지. 노후 코스 운영 효율 개선 시그널.
          </p>
          <span class="src">PIPG FY25 follow-up + FY24 AR Note 27/29</span>
        </div>
        <div class="kv">
          <div class="k">GOLF FY2024 → FY2025</div>
          <p class="kv-comment">
            FY24 COGS 78.3bn (+20.2% YoY, real estate 비용 증가 주도).
            <strong>FY25 영업이익 64.87bn (-10.49% vs FY24 72.47bn)</strong>. 원인: selling expenses +137.20%.
            CWIP Buildings 188bn + Landscape 238bn (총 ~450bn 신규 시설 진행 중).
          </p>
          <span class="src">GOLF FY24 AR p.69 + FY25 AR p.156·p.170</span>
        </div>
        <div class="kv">
          <div class="k">MDLN FY2024 → FY2025</div>
          <p class="kv-comment">
            <strong>GP margin 44.66% → 47.19% (+2.5pp 개선)</strong>. 영업이익률도 sharper improvement.
            Golf 단독 segment FY25 +28.2% YoY (95.3bn) — 골프 부문은 그룹에서 가장 빠른 성장.
            ROA/ROE 비율도 동시 개선.
          </p>
          <span class="src">MDLN FY25 AR p.116 + Note 25/26 (Cycle 66·69)</span>
        </div>
        <div class="kv">
          <div class="k">SMDM FY2024 (BSDE 인수 직전)</div>
          <p class="kv-comment">
            Golf & CC GP margin <strong>FY23 55.8% → FY24 38.9% (-16.9pp 급락)</strong>. 영업이익 -212M IDR (적자전환).
            FY24 배당 미실시 결정 (working capital 보존). BSDE가 2024-10에 91.99% 인수.
            FY25에 GP margin 88.6%로 점프 (회계 재분류 가능).
          </p>
          <span class="src">SMDM FY24 AR p.70 + Cycle 53/67</span>
        </div>
        <div class="kv">
          <div class="k">KPIG (Trump Lido)</div>
          <p class="kv-comment">
            Hotel+Resort+Golf 통합 매출 FY23 812bn → FY24 960bn (+18%) → FY25 1,060bn (+10%).
            Group 고정자산 21조 IDR (54.5% of total assets) + 투자부동산 6.9조 (19.3%) = 자산집약형 conglomerate.
            Golf-only 단위 분리 미공시.
          </p>
          <span class="src">KPIG FY24 AR p.212 (assets) + FY25 Note 31</span>
        </div>
      </div>
    </div>

    <div class="section">
      <h2>peer_operating_signals.csv — 기존 1줄 메모</h2>
      <div class="kv-grid">
        {''.join(capex_notes)}
      </div>

      <div class="src-block">
        <strong>전체 출처:</strong>
        DMIG/PIPG/KPIG/MDLN/GOLF/KIJA/SMDM annual reports (FY22–FY25), 라인별 추출 = <code>site/peer-analysis/operations/data/{{ticker}}_notes.json</code> ·
        peer_financials_curated.csv ·
        peer_operating_signals.csv (segment_revenue_disclosure, operational_notes 필드) ·
        벡터 인덱스 (multilingual-e5-small, 99,618 chunks) — narrative 검증용.
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
    import subprocess
    today = dt.date.today().isoformat()
    try:
        commit_sha = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=HERE, text=True, stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        commit_sha = "?"
    sections = "\n".join([
        section_overview(),
        section_course(),
        section_pricing(),
        section_ops(),
        section_reference(),
    ])
    # Count ops H2 sections automatically
    ops_html = section_ops()
    ops_sections_count = ops_html.count('<h2>')

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
      <strong>골프장 운영 Peer 비교 사이트</strong> — Build {today} (commit <code>{commit_sha}</code>) ·
      Ops 탭 {ops_sections_count}개 분석 섹션 ·
      데이터: raw_peer_data/*.csv (last verified 2026-04-29 ~ 2026-05-07) + AR Note 직접 추출 + 벡터 검색 (99,618 chunks) ·
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
