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
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA_DIR = HERE.parent.parent.parent / "raw_peer_data"

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

    return f"""<section class="panel" data-panel="ops">
  <div class="wrap">
    <div class="section">
      <h2>골프 segment 매출 disclosure</h2>
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
      <h2>운영 효율 — OPEX proxy</h2>
      <h3>순이익률 · 자산집약도</h3>
      <p class="lede">
        직접적인 OPEX/CAPEX 라인은 audited segment에서 미공시.
        대신 <strong>순이익률 = 순이익/매출</strong>을 OPEX 효율 proxy로,
        <strong>자산집약도 = 총자산/매출</strong>을 CAPEX 누적 proxy로 사용.
      </p>
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
        DMIG 매출은 H1만 audited. PIPG만 entity 기준 FY 전체. 직접 비교 시 KPIG 수치는 conglomerate 효과,
        DMIG는 반기 효과를 감안해야 함.
      </div>
    </div>

    <div class="section">
      <h2>CAPEX·운영 메모</h2>
      <h3>annual report 텍스트 발췌</h3>
      <p class="lede">numeric CAPEX/OPEX 라인 미공시 환경에서, 각 peer의 운영 narrative와 시설 변경 단서.</p>
      <div class="kv-grid">
        {''.join(capex_notes)}
      </div>

      <div class="src-block">
        <strong>출처:</strong>
        peer_financials_curated.csv (FY2024),
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
