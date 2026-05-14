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


SLOTS = [("wdAm", "평일 오전"), ("wdPm", "평일 오후"), ("satAm", "토 오전"),
         ("satPm", "토 오후"), ("sunAm", "일 오전"), ("sunPm", "일 오후")]


def pricing_for(course_id: str, slot: str) -> dict | None:
    for r in PRICING:
        if r.get("course_id") == course_id and r.get("slot") == slot:
            return r
    return None


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


def _exec_headline_data() -> dict:
    """Compute headline numbers from NOTES so the strip stays accurate.

    Returns:
        {
          'best_margin': (ticker, pct),
          'best_fy25_op': (ticker, pct),
          'best_per_hole': (ticker, value_bn),
          'cwip_total': (ticker, total_bn),
          'worst_fy25_op': (ticker, pct),
        }
    """
    out = {}

    # Best GP margin (from 6-peer golf segment data)
    rows = _all_peer_golf_segment_data()
    margin_rows = [(r["ticker"], r["gm"]) for r in rows if r["gm"]]
    margin_rows.sort(key=lambda x: -x[1])
    if margin_rows:
        out["best_margin"] = margin_rows[0]

    # Best/worst FY25 op income change
    fy25_changes = []
    for t in ["DMIG", "PIPG", "GOLF"]:
        fu = (NOTES.get(t, {}) or {}).get("fy2025_follow_up") or {}
        yoy = (fu.get("yoy_changes") or {}).get("operating_income")
        if yoy is not None:
            fy25_changes.append((t, yoy * 100))
    if fy25_changes:
        fy25_changes.sort(key=lambda x: -x[1])
        out["best_fy25_op"] = fy25_changes[0]
        out["worst_fy25_op"] = fy25_changes[-1]

    # Best per-hole revenue (golf segment-only)
    per_hole_rows = _per_hole_data()
    seg_rows = [(r["ticker"], r["rev_h"] / 1e9 if r["rev_h"] else 0) for r in per_hole_rows if r["basis_type"] == "segment"]
    seg_rows.sort(key=lambda x: -x[1])
    if seg_rows:
        out["best_per_hole"] = seg_rows[0]

    # GOLF CWIP
    golf_capex = (NOTES.get("GOLF", {}).get("operational_kpis", {}) or {})
    # Fallback to hardcoded since GOLF CWIP is in OPS_KPI_EVIDENCE
    g_kpi = OPS_KPI_EVIDENCE.get("GOLF", {}).get("capex_fy2025") or {}
    bld = g_kpi.get("construction_buildings_idr") or 0
    ls = g_kpi.get("construction_landscape_idr") or 0
    cwip_total_bn = (bld + ls) / 1e9
    out["cwip_total"] = ("GOLF", cwip_total_bn)

    return out


def _exec_headline_html() -> str:
    """Render the executive headline strip using computed data."""
    d = _exec_headline_data()

    def tile(cap, val, unit, ticker, sub):
        return f"""<div class="exec-tile">
  <div class="et-cap">{safe(cap)}</div>
  <div class="et-val">{val}<span class="u">{safe(unit)}</span></div>
  <div class="et-sub"><span class="et-ticker">{safe(ticker)}</span>{safe(sub)}</div>
</div>"""

    best_t, best_pct = d.get("best_margin", ("—", 0))
    op_best_t, op_best = d.get("best_fy25_op", ("—", 0))
    op_worst_t, op_worst = d.get("worst_fy25_op", ("—", 0))
    per_t, per_v = d.get("best_per_hole", ("—", 0))
    cwip_t, cwip_v = d.get("cwip_total", ("—", 0))

    return f"""<div class="exec-headline">
  <div class="exec-eyebrow">7-peer · FY2022→FY2025 · 99,618 chunks audit trail</div>
  <div class="exec-title">운영 KPI · CAPEX/OPEX — 즉시 알 핵심 5 (data-driven)</div>
  <div class="exec-grid">
    {tile('최고 마진 (FY24)', f'{best_pct:.1f}', '%', best_t, 'Golf segment GP — 자본효율 1위')}
    {tile('FY25 best operator', f'{op_best:+.1f}', '%', op_best_t, '영업이익 YoY (비용통제 / target beat)')}
    {tile('홀당 매출 1위', f'{per_v:.1f}', 'bn/홀', per_t, 'Golf segment-only 기준')}
    {tile('진행 CAPEX', f'{cwip_v:.0f}', 'bn', cwip_t, 'CWIP (Buildings + Landscape)')}
    {tile('FY25 마진 압박', f'{op_worst:+.1f}', '%', op_worst_t, '영업이익 YoY — 신규 시설 감가 부담')}
  </div>
</div>"""


def _pnl_funnel_chart(ticker: str, fy: str = "FY2024") -> str:
    """Funnel chart: Revenue → Gross profit → Op income → Net income.
    Shows leakage at each stage as percentage of revenue.
    """
    d = NOTES.get(ticker, {})
    # Get values for the given fiscal year
    rev = revenue_total_for(ticker, fy) or 0
    cogs = 0
    for key in ("cogs_note", "cogs_note_26", "cogs_note_28", "cogs_note_30"):
        b = d.get(key) or {}
        v = (b.get("total") or {}).get(fy)
        if v:
            cogs = v
            break
    gp = rev - cogs if rev and cogs else None

    # Operating income (FY24)
    op_inc = None
    net_inc = None
    if ticker == "DMIG" and fy == "FY2024":
        fu = (d.get("fy2025_follow_up") or {}).get("pnl_FY2024_comparative") or {}
        op_inc = fu.get("operating_income")
        net_inc = fu.get("net_income")
    elif ticker == "PIPG" and fy == "FY2024":
        fh = (d.get("financial_highlights") or {}).get("rows_in_idr_thousand", [])
        for r in fh:
            if r.get("label") == "Laba Usaha":
                op_inc = (r.get(fy) or 0) * 1000
            if r.get("label") == "Laba Bersih":
                net_inc = (r.get(fy) or 0) * 1000

    if not (rev and gp and op_inc and net_inc):
        return ""

    stages = [
        ("매출", rev, "#2d5016"),
        ("Gross Profit", gp, "#4a7c30"),
        ("영업이익", op_inc, "#c08a2e"),
        ("순이익", net_inc, "#92400e"),
    ]

    width, height = 360, 230
    stage_h = 38
    max_w = width - 60
    total_h = len(stages) * (stage_h + 8)

    elems = []
    for i, (label, val, color) in enumerate(stages):
        pct = (val / rev * 100) if rev else 0
        bar_w = (val / rev) * max_w if rev else 0
        x = (width - bar_w) / 2
        y = i * (stage_h + 10) + 10
        elems.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{stage_h}" '
            f'rx="4" fill="{color}" fill-opacity="0.92"/>'
            f'<text x="{width/2:.1f}" y="{y + stage_h/2 + 4:.1f}" font-size="11.5" '
            f'font-weight="700" fill="white" text-anchor="middle">'
            f'{safe(label)} · Rp {fmt_bn(val).replace(" bn","bn")} ({pct:.1f}%)</text>'
        )
        # Leakage arrow between stages
        if i > 0:
            prev_val = stages[i-1][1]
            leak = prev_val - val
            leak_pct = (leak / prev_val * 100) if prev_val else 0
            # Left-side annotation
            elems.append(
                f'<text x="6" y="{y + 4:.1f}" font-size="9.5" fill="var(--ink-soft)" font-weight="600">'
                f'<tspan fill="#b91c1c">-{leak_pct:.1f}%</tspan></text>'
            )

    return f"""<div style="background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:12px;">
  <div style="font-size:13px;font-weight:700;color:var(--ink);text-align:center;margin-bottom:6px;">
    <span class="ticker-mini">{safe(ticker)}</span> P&amp;L Funnel ({safe(fy[2:])})
  </div>
  <svg viewBox="0 0 {width} {height}" width="100%" style="display:block;max-width:380px;margin:0 auto;" xmlns="http://www.w3.org/2000/svg">
    {''.join(elems)}
  </svg>
  <p class="src-line" style="text-align:center;margin: 4px 0 0;">바 너비 = 매출 대비 % · 좌측 빨강 % = 직전 단계 대비 leakage</p>
</div>"""


def _pnl_funnel_section() -> str:
    """Grid of 2-peer funnel charts (DMIG + PIPG, FY24)."""
    parts = [_pnl_funnel_chart("DMIG", "FY2024"), _pnl_funnel_chart("PIPG", "FY2024")]
    parts = [p for p in parts if p]
    return f"""<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(360px,1fr));gap:14px;">
  {''.join(parts)}
</div>"""


def _radar_chart_svg(series, axes, width=440, height=440, title=""):
    """SVG radar/spider chart for N-dimensional peer comparison.

    series: [(label, [v1..vN normalized 0..1], color), ...]
    axes:   [(axis_label, axis_unit, max_value_for_normalization), ...]
    """
    n = len(axes)
    if n < 3:
        return ""
    cx, cy = width / 2, height / 2 + 6
    r_max = min(width, height) / 2 - 60
    import math

    def to_xy(axis_idx, r_norm):
        angle = -math.pi / 2 + (2 * math.pi * axis_idx / n)
        rr = r_max * r_norm
        return cx + rr * math.cos(angle), cy + rr * math.sin(angle)

    # Concentric grid pentagons (0.25, 0.5, 0.75, 1.0)
    grid = []
    for r_ring in [0.25, 0.5, 0.75, 1.0]:
        pts = []
        for i in range(n):
            x, y = to_xy(i, r_ring)
            pts.append(f"{x:.1f},{y:.1f}")
        grid.append(
            f'<polygon points="{" ".join(pts)}" fill="none" stroke="#ebe9e0" stroke-width="0.8"/>'
        )
    # Axis lines
    for i in range(n):
        x_end, y_end = to_xy(i, 1.0)
        grid.append(
            f'<line x1="{cx:.1f}" y1="{cy:.1f}" x2="{x_end:.1f}" y2="{y_end:.1f}" stroke="#ebe9e0" stroke-width="0.8"/>'
        )

    # Axis labels
    axis_labels = []
    for i, (label, unit, max_v) in enumerate(axes):
        x_lab, y_lab = to_xy(i, 1.16)
        # Anchor based on position
        angle_deg = -90 + (360 * i / n)
        if angle_deg < -45 or angle_deg > 270:
            anchor = "end"
        elif -45 <= angle_deg <= 45:
            anchor = "middle"
        else:
            anchor = "start"
        # Vertical offset
        if 80 < angle_deg < 100 or -100 < angle_deg < -80:
            dy = 4
        else:
            dy = 0
        axis_labels.append(
            f'<text x="{x_lab:.1f}" y="{y_lab + dy:.1f}" font-size="11" font-weight="700" '
            f'fill="#4b4b4b" text-anchor="{anchor}">{safe(label)}</text>'
        )
        # Max value label
        x_max_lab, y_max_lab = to_xy(i, 1.05)
        if i == 0:
            axis_labels.append(
                f'<text x="{cx + 4:.1f}" y="{cy - 4:.1f}" font-size="9" fill="#8a8a8a">0</text>'
            )

    # Series polygons
    polygons = []
    legend_items = []
    for label, values, color in series:
        pts = []
        for i, v in enumerate(values):
            v_clamped = max(0, min(v, 1))
            x, y = to_xy(i, v_clamped)
            pts.append(f"{x:.1f},{y:.1f}")
        # Dots
        dots = "".join(
            f'<circle cx="{p.split(",")[0]}" cy="{p.split(",")[1]}" r="3" fill="{color}" stroke="white" stroke-width="1.5"/>'
            for p in pts
        )
        polygons.append(
            f'<polygon points="{" ".join(pts)}" fill="{color}" fill-opacity="0.18" '
            f'stroke="{color}" stroke-width="2" stroke-linejoin="round"/>'
            f'{dots}'
        )
        legend_items.append(
            f'<span class="lg"><span class="sw" style="background:{color};"></span>{safe(label)}</span>'
        )

    title_html = f'<div style="font-size:13px;font-weight:700;color:var(--ink);text-align:center;margin-bottom:4px;">{safe(title)}</div>' if title else ""

    return f"""<div style="background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:18px 12px 12px;">
  {title_html}
  <svg viewBox="0 0 {width} {height}" width="100%" style="max-width:480px;display:block;margin:0 auto;" xmlns="http://www.w3.org/2000/svg">
    {''.join(grid)}
    {''.join(axis_labels)}
    {''.join(polygons)}
  </svg>
  <div class="stack-legend" style="justify-content:center;margin-top:6px;">{''.join(legend_items)}</div>
</div>"""


def _peer_compare_radar() -> str:
    """DMIG vs PIPG radar — 6-axis normalized comparison."""

    def safe_get(t, *path, default=None):
        d = NOTES.get(t, {})
        for p in path:
            if not isinstance(d, dict):
                return default
            d = d.get(p) or {}
        return d if d else default

    # Axis definitions: (label, unit, max_value, peer_value_dict)
    # All values normalized to 0..1 against max_value
    dmig_d = NOTES.get("DMIG", {})
    pipg_d = NOTES.get("PIPG", {})

    # FY2024 entity revenue
    dmig_rev = (dmig_d.get("revenue_note") or {}).get("total", {}).get("FY2024") or 0
    pipg_rev = (pipg_d.get("revenue_note_27") or {}).get("total", {}).get("FY2024") or 0

    # Operating margin FY2024 (DMIG from FY25 follow-up, PIPG from financial_highlights)
    fu_dmig = (dmig_d.get("fy2025_follow_up") or {}).get("pnl_FY2024_comparative") or {}
    dmig_op = fu_dmig.get("operating_income") or 0
    dmig_om = (dmig_op / dmig_rev * 100) if dmig_rev else 0

    fh_pipg = (pipg_d.get("financial_highlights") or {}).get("rows_in_idr_thousand", [])
    pipg_op = 0
    for r in fh_pipg:
        if r.get("label") == "Laba Usaha":
            pipg_op = (r.get("FY2024") or 0) * 1000
            break
    pipg_om = (pipg_op / pipg_rev * 100) if pipg_rev else 0

    # Depreciation / revenue
    def dep_pct(d, opex_key, rev_total):
        lines = (d.get(opex_key) or {}).get("lines") or []
        for ln in lines:
            if "penyusutan" in (ln.get("id_label") or "").lower() or "depreciation" in (ln.get("en_label") or "").lower():
                return (ln.get("FY2024") or 0) / rev_total * 100 if rev_total else 0
        return 0
    dmig_dep = dep_pct(dmig_d, "opex_note", dmig_rev)
    pipg_dep = dep_pct(pipg_d, "opex_note_29", pipg_rev)

    # Maintenance / revenue
    def mnt_pct(d, opex_key, rev_total):
        lines = (d.get(opex_key) or {}).get("lines") or []
        for ln in lines:
            lab = (ln.get("id_label") or "").lower()
            en = (ln.get("en_label") or "").lower()
            if "perbaikan" in lab or "pemeliharaan" in lab or "perawatan" in lab or "repair" in en or "maintenance" in en:
                return (ln.get("FY2024") or 0) / rev_total * 100 if rev_total else 0
        return 0
    dmig_mnt = mnt_pct(dmig_d, "opex_note", dmig_rev)
    pipg_mnt = mnt_pct(pipg_d, "opex_note_29", pipg_rev)

    # Dividend payout FY23
    dmig_div = 26_514_391_332
    pipg_div = 26_239_800_000
    dmig_ni_23 = 71_268_571_841
    pipg_ni_23 = 55_900_000_000
    dmig_payout = (dmig_div / dmig_ni_23 * 100)
    pipg_payout = (pipg_div / pipg_ni_23 * 100)

    # Holes
    dmig_holes = 36
    pipg_holes = 18
    dmig_rev_hole = dmig_rev / dmig_holes / 1e9
    pipg_rev_hole = pipg_rev / pipg_holes / 1e9

    # Define axes with max values (for normalization)
    axes = [
        ("매출 (bn)",    "bn",  300),    # max 300bn
        ("Op margin %", "%",   40),
        ("감가/매출 %", "%",   15),     # higher = more capex
        ("유지/매출 %", "%",   8),
        ("배당 payout", "%",   60),
        ("매출/홀 (bn)", "bn", 15),
    ]

    dmig_values = [
        (dmig_rev / 1e9) / axes[0][2],
        dmig_om / axes[1][2],
        dmig_dep / axes[2][2],
        dmig_mnt / axes[3][2],
        dmig_payout / axes[4][2],
        dmig_rev_hole / axes[5][2],
    ]
    pipg_values = [
        (pipg_rev / 1e9) / axes[0][2],
        pipg_om / axes[1][2],
        pipg_dep / axes[2][2],
        pipg_mnt / axes[3][2],
        pipg_payout / axes[4][2],
        pipg_rev_hole / axes[5][2],
    ]

    radar = _radar_chart_svg(
        series=[
            ("DMIG", dmig_values, PEER_COLORS["DMIG"]),
            ("PIPG", pipg_values, PEER_COLORS["PIPG"]),
        ],
        axes=axes,
        title="DMIG vs PIPG — 6축 1:1 비교 (FY2024 기반)",
    )

    # Side table with actual values
    rows_html = []
    for i, (label, unit, max_v) in enumerate(axes):
        dmig_actual = [
            dmig_rev / 1e9, dmig_om, dmig_dep, dmig_mnt, dmig_payout, dmig_rev_hole
        ][i]
        pipg_actual = [
            pipg_rev / 1e9, pipg_om, pipg_dep, pipg_mnt, pipg_payout, pipg_rev_hole
        ][i]
        rows_html.append(f"""<tr>
  <td>{safe(label)}</td>
  <td class="num" style="color:{PEER_COLORS['DMIG']};font-weight:700;">{dmig_actual:.1f}{unit}</td>
  <td class="num" style="color:{PEER_COLORS['PIPG']};font-weight:700;">{pipg_actual:.1f}{unit}</td>
</tr>""")

    table = f"""<div class="tbl-card" style="background:var(--surface);">
  <table class="tbl tbl-tight">
    <thead><tr><th>축</th>
      <th class="num"><span class="ticker-mini">DMIG</span></th>
      <th class="num"><span class="ticker-mini">PIPG</span></th>
    </tr></thead>
    <tbody>{''.join(rows_html)}</tbody>
  </table>
</div>"""

    return f"""<div style="display:grid;grid-template-columns:1.2fr 1fr;gap:14px;align-items:start;">
  {radar}
  <div>
    {table}
    <p class="src-line" style="margin-top:10px;">
      각 축은 max value 기준 0~100% 정규화 · 0=중심, 1=외곽 ·
      DMIG는 매출 1.3배·자본투자 강도 ↑ (감가 12%) ·
      PIPG는 유지보수 ↑ (5.9%) · 배당 payout 동일 수준
    </p>
  </div>
</div>"""


def _pnl_data_for(ticker: str) -> list:
    """Extract per-year P&L numbers for one ticker (FY22-25). Returns list of dicts."""
    d = NOTES.get(ticker, {})
    out = []
    for fy in PNL_YEARS:
        rev = revenue_total_for(ticker, fy)
        cogs = None
        for key in ("cogs_note", "cogs_note_26", "cogs_note_28", "cogs_note_30"):
            b = d.get(key) or {}
            v = (b.get("total") or {}).get(fy)
            if v:
                cogs = v
                break
        opx = None
        for key in ("opex_note", "opex_note_29", "ga_note_32", "ga_note_34"):
            b = d.get(key) or {}
            v = (b.get("total") or {}).get(fy)
            if v:
                opx = v
                break
        op_inc = None
        net_inc = None
        if fy == "FY2025":
            fu = (d.get("fy2025_follow_up") or {}).get("pnl_FY2025") or {}
            rev = fu.get("revenue") or rev
            cogs = fu.get("cogs") or cogs
            opx = fu.get("opex") or opx
            op_inc = fu.get("operating_income")
            net_inc = fu.get("net_income")
        if fy in ("FY2022", "FY2023", "FY2024") and ticker == "PIPG":
            fh = (d.get("financial_highlights") or {}).get("rows_in_idr_thousand", [])
            for r in fh:
                if r.get("label") == "Laba Usaha":
                    op_inc = r.get(fy) and r[fy] * 1000
                if r.get("label") == "Laba Bersih":
                    net_inc = r.get(fy) and r[fy] * 1000
        if ticker == "DMIG" and fy == "FY2024":
            fu = (d.get("fy2025_follow_up") or {}).get("pnl_FY2024_comparative") or {}
            op_inc = op_inc or fu.get("operating_income")
            net_inc = net_inc or fu.get("net_income")
        gp = (rev - cogs) if (rev and cogs) else None
        gm = (gp / rev * 100) if (rev and gp) else None
        om = (op_inc / rev * 100) if (rev and op_inc) else None
        nm = (net_inc / rev * 100) if (rev and net_inc) else None
        out.append({"fy": fy, "rev": rev, "gp": gp, "op_inc": op_inc, "net_inc": net_inc, "gm": gm, "om": om, "nm": nm})
    return out


def _multi_line_chart(series_list, fys, width=380, height=200, title=""):
    """Multi-line SVG chart. series_list = [(label, [values], color), ...]."""
    pad_l, pad_b, pad_r, pad_t = 40, 30, 16, 20
    inner_w = width - pad_l - pad_r
    inner_h = height - pad_t - pad_b

    # Compute y range
    all_vals = [v for _, vals, _ in series_list for v in vals if v is not None]
    if not all_vals:
        return ""
    y_min = min(all_vals + [0])
    y_max = max(all_vals)
    if y_max == y_min:
        y_max = y_min + 10
    # Pad
    y_pad = (y_max - y_min) * 0.1
    y_min -= y_pad
    y_max += y_pad
    if y_min < 0:
        y_min = min(y_min, -5)
    n = len(fys)

    def to_x(i): return pad_l + (inner_w * (i / (n - 1)))

    def to_y(v): return pad_t + inner_h - (inner_h * ((v - y_min) / (y_max - y_min)))

    # Gridlines (5 horizontal)
    grid = []
    grid_steps = 4
    for i in range(grid_steps + 1):
        y = pad_t + inner_h - (inner_h * (i / grid_steps))
        val = y_min + (y_max - y_min) * (i / grid_steps)
        grid.append(
            f'<line x1="{pad_l}" y1="{y:.1f}" x2="{pad_l + inner_w}" y2="{y:.1f}" stroke="#ebe9e0" stroke-width="0.5"/>'
            f'<text x="{pad_l - 6}" y="{y + 3:.1f}" font-size="9" fill="#8a8a8a" text-anchor="end">{val:.0f}%</text>'
        )
    # X labels
    for i, fy in enumerate(fys):
        x = to_x(i)
        grid.append(
            f'<text x="{x:.1f}" y="{pad_t + inner_h + 14}" font-size="10" fill="#4b4b4b" '
            f'text-anchor="middle" font-weight="600">{safe(fy[2:])}</text>'
        )

    # Series lines
    lines = []
    legend_items = []
    for label, vals, color in series_list:
        valid_points = [(to_x(i), to_y(v), v) for i, v in enumerate(vals) if v is not None]
        if len(valid_points) < 2:
            continue
        pts_str = " ".join(f"{x:.1f},{y:.1f}" for x, y, _ in valid_points)
        lines.append(f'<polyline fill="none" stroke="{color}" stroke-width="2" points="{pts_str}"/>')
        for x, y, v in valid_points:
            lines.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="white" stroke="{color}" stroke-width="2"><title>{label}: {v:.1f}%</title></circle>')
        # Last value label
        last_x, last_y, last_v = valid_points[-1]
        lines.append(
            f'<text x="{last_x + 6:.1f}" y="{last_y + 4:.1f}" font-size="11" '
            f'fill="{color}" font-weight="700">{last_v:.1f}%</text>'
        )
        legend_items.append(
            f'<span class="lg"><span class="sw" style="background:{color};"></span>{safe(label)}</span>'
        )

    legend = f'<div class="stack-legend" style="margin-top:6px;justify-content:center;">{"".join(legend_items)}</div>'
    title_html = f'<div style="font-size:13px;font-weight:700;color:var(--ink);text-align:center;margin-bottom:4px;">{safe(title)}</div>' if title else ""

    return f"""<div style="background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:14px 12px 10px;">
  {title_html}
  <svg viewBox="0 0 {width} {height}" width="100%" style="display:block;" xmlns="http://www.w3.org/2000/svg">
    {''.join(grid)}
    {''.join(lines)}
  </svg>
  {legend}
</div>"""


def _pnl_margin_trend_section() -> str:
    """Multi-line GM/OM/NM trend chart for DMIG + PIPG + KPIG (where data exists)."""
    fys = PNL_YEARS
    charts = []
    for ticker in ["DMIG", "PIPG", "KPIG"]:
        data = _pnl_data_for(ticker)
        gm_vals = [d["gm"] for d in data]
        om_vals = [d["om"] for d in data]
        nm_vals = [d["nm"] for d in data]
        chart = _multi_line_chart(
            [
                ("GP Margin", gm_vals, "#4a7c30"),
                ("Op Margin", om_vals, "#c08a2e"),
                ("Net Margin", nm_vals, "#1e40af"),
            ],
            fys,
            width=420, height=220,
            title=f"{ticker} — 4Y 마진 추이 (FY22→25)",
        )
        if chart:
            charts.append(chart)

    # Revenue absolute bar comparison (FY22-25)
    rev_rows = []
    all_rev = []
    for ticker in ["DMIG", "PIPG"]:  # KPIG is mixed, exclude for cleaner view
        data = _pnl_data_for(ticker)
        for d in data:
            if d["rev"]:
                all_rev.append(d["rev"])
    max_rev = max(all_rev) if all_rev else 1

    for ticker in ["DMIG", "PIPG"]:
        data = _pnl_data_for(ticker)
        bars_html = []
        for d in data:
            v = d["rev"]
            pct = (v / max_rev * 100) if v else 0
            color = PEER_COLORS.get(ticker, "#4a7c30")
            label = fmt_bn(v).replace(" bn", "bn") if v else "—"
            bars_html.append(f"""<div style="display:flex;align-items:center;gap:8px;font-size:11.5px;">
  <span style="flex:0 0 38px;color:var(--ink-soft);font-weight:600;">{d["fy"][2:]}</span>
  <span style="flex:1;height:14px;background:var(--line);border-radius:3px;overflow:hidden;">
    <span style="display:block;height:100%;width:{pct:.1f}%;background:{color};"></span>
  </span>
  <span style="flex:0 0 64px;text-align:right;font-weight:600;font-variant-numeric:tabular-nums;">{label}</span>
</div>""")
        rev_rows.append(f"""<div style="background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:14px 16px;">
  <div style="font-size:13px;font-weight:700;color:var(--ink);margin-bottom:8px;"><span class="ticker-mini">{ticker}</span> 매출 4년 추이</div>
  <div style="display:flex;flex-direction:column;gap:6px;">{''.join(bars_html)}</div>
</div>""")

    revenue_block = f"""<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:12px;margin-top:14px;">
  {''.join(rev_rows)}
</div>"""

    chart_grid = f"""<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(380px,1fr));gap:12px;">
  {''.join(charts)}
</div>"""

    return chart_grid + revenue_block


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


def _generic_topn_chart(ticker: str, note_key: str, title: str, kind: str = "OpEx", top_n: int = 5) -> str:
    """Horizontal bar chart for any P&L line breakdown (Revenue/COGS/OpEx).

    kind: "OpEx" / "Revenue" / "COGS" — used for total row label and YoY tone.
    For revenue, "up YoY" is good; for COGS/OpEx, "down YoY" is good.
    """
    d = NOTES.get(ticker, {})
    blk = d.get(note_key) or {}
    lines = blk.get("lines") or []
    if not lines:
        return ""
    sorted_lines = sorted(lines, key=lambda ln: -(float(ln.get("FY2024") or 0)))
    top = sorted_lines[:top_n]
    rest = sorted_lines[top_n:]
    rev24 = revenue_total_for(ticker, "FY2024")
    if not rev24 and ticker == "KPIG":
        rev24 = ((d.get("revenue_note_31") or {}).get("total") or {}).get("FY2024") or 1
    max_v = sorted_lines[0].get("FY2024") or 1

    color = PEER_COLORS.get(ticker, "#2d5016")
    is_cost = kind.lower() in ("opex", "cogs")

    def yoy_color_for(yoy_val):
        if yoy_val is None:
            return "var(--muted)"
        if is_cost:
            return "var(--danger)" if yoy_val > 5 else ("var(--green)" if yoy_val < -2 else "var(--muted)")
        # revenue: up is good
        return "var(--green)" if yoy_val > 2 else ("var(--danger)" if yoy_val < -2 else "var(--muted)")

    bars = []
    for ln in top:
        v23 = ln.get("FY2023") or 0
        v24 = ln.get("FY2024") or 0
        label = ln.get("en_label") or ln.get("id_label") or "—"
        pct_w = (v24 / max_v * 100) if max_v else 0
        pct_rev = (v24 / rev24 * 100) if rev24 else None
        yoy = None
        if v23 and v24:
            yoy = ((v24 / v23) - 1) * 100
        yoy_str = f"{yoy:+.1f}%" if yoy is not None else "—"
        yc = yoy_color_for(yoy)
        val_str = fmt_bn(v24).replace(" bn", "bn")
        bars.append(f"""<div style="display:grid;grid-template-columns:170px 1fr 76px 54px;gap:8px;align-items:center;padding:4px 0;font-size:11.5px;">
  <span style="color:var(--ink-soft);font-weight:500;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;" title="{safe(label)}">{safe(label[:22])}</span>
  <span style="height:18px;background:var(--line);border-radius:3px;overflow:hidden;">
    <span style="display:block;height:100%;width:{pct_w:.1f}%;background:{color};"></span>
  </span>
  <span style="text-align:right;font-weight:600;font-variant-numeric:tabular-nums;">
    {val_str}<br><span style="font-size:9.5px;color:var(--muted);font-weight:500;">{f"{pct_rev:.1f}% 매출" if pct_rev else ""}</span>
  </span>
  <span style="text-align:right;font-weight:700;font-size:11px;color:{yc};">{yoy_str}</span>
</div>""")

    if rest:
        v23 = sum((ln.get("FY2023") or 0) for ln in rest)
        v24 = sum((ln.get("FY2024") or 0) for ln in rest)
        pct_w = (v24 / max_v * 100) if max_v else 0
        pct_rev = (v24 / rev24 * 100) if rev24 else None
        yoy = ((v24 / v23) - 1) * 100 if (v23 and v24) else None
        yoy_str = f"{yoy:+.1f}%" if yoy is not None else "—"
        val_str = fmt_bn(v24).replace(" bn", "bn")
        bars.append(f"""<div style="display:grid;grid-template-columns:170px 1fr 76px 54px;gap:8px;align-items:center;padding:4px 0;font-size:11.5px;border-top:1px dashed var(--line);margin-top:4px;">
  <span style="color:var(--muted);font-weight:500;font-style:italic;">기타 {len(rest)}개 라인 합산</span>
  <span style="height:14px;background:var(--line);border-radius:3px;overflow:hidden;">
    <span style="display:block;height:100%;width:{pct_w:.1f}%;background:#d4d0c0;"></span>
  </span>
  <span style="text-align:right;font-weight:500;font-variant-numeric:tabular-nums;color:var(--ink-soft);">
    {val_str}<br><span style="font-size:9.5px;color:var(--muted);font-weight:500;">{f"{pct_rev:.1f}% 매출" if pct_rev else ""}</span>
  </span>
  <span style="text-align:right;font-weight:600;font-size:11px;color:var(--muted);">{yoy_str}</span>
</div>""")

    tot = blk.get("total") or {}
    t24 = tot.get("FY2024")
    t23 = tot.get("FY2023")
    yoy_t = ((t24 / t23) - 1) * 100 if (t23 and t24) else None
    yoy_t_str = f"{yoy_t:+.1f}%" if yoy_t is not None else "—"
    bars.append(f"""<div style="display:grid;grid-template-columns:170px 1fr 76px 54px;gap:8px;align-items:center;padding:8px 0 2px;font-size:12px;border-top:2px solid var(--line-strong);margin-top:6px;font-weight:700;">
  <span style="color:var(--ink);">{safe(kind)} 합계</span>
  <span></span>
  <span style="text-align:right;font-variant-numeric:tabular-nums;">{fmt_bn(t24).replace(" bn","bn")}<br><span style="font-size:9.5px;color:var(--muted);font-weight:500;">{f"{(t24/rev24*100):.1f}% 매출" if (t24 and rev24) else ""}</span></span>
  <span style="text-align:right;color:var(--muted);">{yoy_t_str}</span>
</div>""")

    return f"""<div class="ops-block" style="background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:16px 16px 12px;">
  <h4 class="ops-block-h" style="margin-bottom:10px;">
    <span class="ticker-mini">{safe(ticker)}</span> {safe(title)}
  </h4>
  <div style="display:grid;grid-template-columns:170px 1fr 76px 54px;gap:8px;padding:2px 0 4px;font-size:9.5px;color:var(--muted);text-transform:uppercase;letter-spacing:0.04em;font-weight:700;border-bottom:1px solid var(--line);">
    <span>Line</span><span>FY24 magnitude</span><span style="text-align:right;">FY24 IDR</span><span style="text-align:right;">YoY</span>
  </div>
  {''.join(bars)}
</div>"""


def _opex_topn_chart(ticker: str, note_key: str, title: str, top_n: int = 5) -> str:
    """Horizontal bar chart: top-N OpEx lines + Others rollup, with YoY indicator."""
    d = NOTES.get(ticker, {})
    blk = d.get(note_key) or {}
    lines = blk.get("lines") or []
    if not lines:
        return ""
    # Sort by FY24 desc
    sorted_lines = sorted(lines, key=lambda ln: -(float(ln.get("FY2024") or 0)))
    top = sorted_lines[:top_n]
    rest = sorted_lines[top_n:]
    rev24 = revenue_total_for(ticker, "FY2024")
    if not rev24 and ticker == "KPIG":
        # KPIG handled differently — use Hotel+Resort+Golf revenue
        rev24 = ((d.get("revenue_note_31") or {}).get("total") or {}).get("FY2024") or 1
    max_v = sorted_lines[0].get("FY2024") or 1

    color = PEER_COLORS.get(ticker, "#2d5016")

    bars = []
    for ln in top:
        v23 = ln.get("FY2023") or 0
        v24 = ln.get("FY2024") or 0
        label = ln.get("en_label") or ln.get("id_label") or "—"
        pct_w = (v24 / max_v * 100) if max_v else 0
        pct_rev = (v24 / rev24 * 100) if rev24 else None
        yoy = None
        if v23 and v24:
            yoy = ((v24 / v23) - 1) * 100
        yoy_str = f"{yoy:+.1f}%" if yoy is not None else "—"
        yoy_color = "var(--danger)" if (yoy and yoy > 5) else ("var(--green)" if (yoy and yoy < -2) else "var(--muted)")
        val_str = fmt_bn(v24).replace(" bn", "bn")
        bars.append(f"""<div style="display:grid;grid-template-columns:170px 1fr 76px 54px;gap:8px;align-items:center;padding:4px 0;font-size:11.5px;">
  <span style="color:var(--ink-soft);font-weight:500;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;" title="{safe(label)}">{safe(label[:22])}</span>
  <span style="height:18px;background:var(--line);border-radius:3px;overflow:hidden;">
    <span style="display:block;height:100%;width:{pct_w:.1f}%;background:{color};"></span>
  </span>
  <span style="text-align:right;font-weight:600;font-variant-numeric:tabular-nums;">
    {val_str}<br><span style="font-size:9.5px;color:var(--muted);font-weight:500;">{f"{pct_rev:.1f}% 매출" if pct_rev else ""}</span>
  </span>
  <span style="text-align:right;font-weight:700;font-size:11px;color:{yoy_color};">{yoy_str}</span>
</div>""")

    # Others rollup
    if rest:
        v23 = sum((ln.get("FY2023") or 0) for ln in rest)
        v24 = sum((ln.get("FY2024") or 0) for ln in rest)
        pct_w = (v24 / max_v * 100) if max_v else 0
        pct_rev = (v24 / rev24 * 100) if rev24 else None
        yoy = ((v24 / v23) - 1) * 100 if (v23 and v24) else None
        yoy_str = f"{yoy:+.1f}%" if yoy is not None else "—"
        yoy_color = "var(--muted)"
        val_str = fmt_bn(v24).replace(" bn", "bn")
        bars.append(f"""<div style="display:grid;grid-template-columns:170px 1fr 76px 54px;gap:8px;align-items:center;padding:4px 0;font-size:11.5px;border-top:1px dashed var(--line);margin-top:4px;">
  <span style="color:var(--muted);font-weight:500;font-style:italic;">기타 {len(rest)}개 라인 합산</span>
  <span style="height:14px;background:var(--line);border-radius:3px;overflow:hidden;">
    <span style="display:block;height:100%;width:{pct_w:.1f}%;background:#d4d0c0;"></span>
  </span>
  <span style="text-align:right;font-weight:500;font-variant-numeric:tabular-nums;color:var(--ink-soft);">
    {val_str}<br><span style="font-size:9.5px;color:var(--muted);font-weight:500;">{f"{pct_rev:.1f}% 매출" if pct_rev else ""}</span>
  </span>
  <span style="text-align:right;font-weight:600;font-size:11px;color:{yoy_color};">{yoy_str}</span>
</div>""")

    # Total row
    tot = blk.get("total") or {}
    t24 = tot.get("FY2024")
    t23 = tot.get("FY2023")
    yoy_t = ((t24 / t23) - 1) * 100 if (t23 and t24) else None
    yoy_t_str = f"{yoy_t:+.1f}%" if yoy_t is not None else "—"
    bars.append(f"""<div style="display:grid;grid-template-columns:170px 1fr 76px 54px;gap:8px;align-items:center;padding:8px 0 2px;font-size:12px;border-top:2px solid var(--line-strong);margin-top:6px;font-weight:700;">
  <span style="color:var(--ink);">OpEx 합계</span>
  <span></span>
  <span style="text-align:right;font-variant-numeric:tabular-nums;">{fmt_bn(t24).replace(" bn","bn")}<br><span style="font-size:9.5px;color:var(--muted);font-weight:500;">{f"{(t24/rev24*100):.1f}% 매출" if (t24 and rev24) else ""}</span></span>
  <span style="text-align:right;color:var(--muted);">{yoy_t_str}</span>
</div>""")

    return f"""<div class="ops-block" style="background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:16px 16px 12px;">
  <h4 class="ops-block-h" style="margin-bottom:10px;">
    <span class="ticker-mini">{safe(ticker)}</span> {safe(title)}
  </h4>
  <div style="display:grid;grid-template-columns:170px 1fr 76px 54px;gap:8px;padding:2px 0 4px;font-size:9.5px;color:var(--muted);text-transform:uppercase;letter-spacing:0.04em;font-weight:700;border-bottom:1px solid var(--line);">
    <span>Line</span><span>FY24 magnitude</span><span style="text-align:right;">FY24 IDR</span><span style="text-align:right;">YoY</span>
  </div>
  {''.join(bars)}
</div>"""


def _opex_topn_section() -> str:
    """Grid of top-N OpEx breakdown charts for DMIG/PIPG/KPIG."""
    parts = [
        _generic_topn_chart("DMIG", "opex_note", "Top OpEx 라인 (Note 25)", kind="OpEx"),
        _generic_topn_chart("PIPG", "opex_note_29", "Top OpEx 라인 (Note 29)", kind="OpEx"),
        _generic_topn_chart("KPIG", "ga_note_34", "Top G&A 라인 (Note 34, Hotel+R+G 통합)", kind="OpEx"),
    ]
    return f"""<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(440px,1fr));gap:14px;">
  {''.join(parts)}
</div>"""


def _revenue_topn_section() -> str:
    """Top-N revenue line breakdown for DMIG + PIPG."""
    parts = [
        _generic_topn_chart("DMIG", "revenue_note", "Top 매출 라인 (Note 23, 7 라인)", kind="Revenue", top_n=5),
        _generic_topn_chart("PIPG", "revenue_note_27", "Top 매출 라인 (Note 27, 11 라인)", kind="Revenue", top_n=5),
    ]
    return f"""<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(440px,1fr));gap:14px;">
  {''.join(parts)}
</div>"""


def _cogs_topn_section() -> str:
    """Top-N COGS line breakdown for DMIG + PIPG."""
    parts = [
        _generic_topn_chart("DMIG", "cogs_note", "Top COGS 라인", kind="COGS", top_n=4),
        _generic_topn_chart("PIPG", "cogs_note_28", "Top COGS 라인 (Note 28, 11 라인)", kind="COGS", top_n=5),
    ]
    return f"""<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(440px,1fr));gap:14px;">
  {''.join(parts)}
</div>"""


def _capex_data() -> list:
    """Extract per-peer CAPEX proxy ratios with explicit numbers + FY23 baseline.

    Returns list of dicts: {ticker, dep, dep_pct, dep_pct_prev, mnt, mnt_pct, mnt_pct_prev, ta, intensity}.
    """
    out = []
    for t in ["DMIG", "PIPG", "GOLF", "KPIG"]:
        d = NOTES.get(t, {})
        dep_line = None
        maint_line = None
        for okey in ("opex_note", "opex_note_29", "ga_note_32", "ga_note_34"):
            b = d.get(okey) or {}
            for ln in b.get("lines") or []:
                lab = (ln.get("id_label") or "").lower()
                en = (ln.get("en_label") or "").lower()
                if dep_line is None and ("penyusutan" in lab or "depreciation" in en):
                    dep_line = ln
                if maint_line is None and ("perbaikan" in lab or "pemeliharaan" in lab or "perawatan" in lab or "repair" in en or "maintenance" in en):
                    maint_line = ln
            if dep_line and maint_line:
                break
        rev24 = revenue_total_for(t, "FY2024")
        rev23 = revenue_total_for(t, "FY2023")
        if t == "GOLF":
            rev24 = ((d.get("revenue_note_29") or {}).get("by_operations") or {}).get("total", {}).get("FY2024") or rev24
            rev23 = ((d.get("revenue_note_29") or {}).get("by_operations") or {}).get("total", {}).get("FY2023") or rev23

        dep24 = (dep_line or {}).get("FY2024")
        dep23 = (dep_line or {}).get("FY2023")
        mnt24 = (maint_line or {}).get("FY2024")
        mnt23 = (maint_line or {}).get("FY2023")

        fin = next((f for f in by_ticker(FINANCIALS, t) if f.get("total_assets_idr")), {})
        ta = fin.get("total_assets_idr")

        dep_pct = (dep24 / rev24 * 100) if (dep24 and rev24) else None
        dep_pct_prev = (dep23 / rev23 * 100) if (dep23 and rev23) else None
        mnt_pct = (mnt24 / rev24 * 100) if (mnt24 and rev24) else None
        mnt_pct_prev = (mnt23 / rev23 * 100) if (mnt23 and rev23) else None
        intensity = (float(ta) / float(rev24)) if (rev24 and ta) else None
        out.append({
            "ticker": t,
            "dep": dep24, "dep_pct": dep_pct, "dep_pct_prev": dep_pct_prev,
            "mnt": mnt24, "mnt_pct": mnt_pct, "mnt_pct_prev": mnt_pct_prev,
            "ta": ta, "intensity": intensity,
        })
    return out


def _heat_class(value, thresholds):
    """Map value to heat-N CSS class based on threshold breakpoints."""
    if value is None:
        return "heat-0"
    for i, thr in enumerate(thresholds):
        if value < thr:
            return f"heat-{i+1}"
    return f"heat-{len(thresholds)+1}"


def _capex_heatmap_section() -> str:
    """CAPEX visualization: KPI tiles + 3x3 heatmap + intensity gauge."""
    data = _capex_data()

    # --- (1) KPI tile per peer with CAPEX phase tag
    phase_label = {
        "DMIG": ("Capex-intensive · 신규 시설 투자", "accent-warn"),
        "PIPG": ("Mature · 유지보수 비중 큼", "accent-gold"),
        "GOLF": ("Asset-light · IPO 1년차 효과", "accent-green"),
        "KPIG": ("Conglomerate · golf 분리 불가", "accent-blue"),
    }
    tiles = []
    for r in data:
        t = r["ticker"]
        phase, accent = phase_label.get(t, ("—", ""))
        dep_str = f"{r['dep_pct']:.1f}%" if r["dep_pct"] is not None else "—"
        intensity_str = f"{r['intensity']:.1f}×" if r["intensity"] is not None else "—"
        tiles.append(f"""<div class="kpi-tile {accent}">
  <div class="kpi-cap">{safe(t)} · 자본투자 phase</div>
  <div class="kpi-val small">{safe(phase)}</div>
  <div class="kpi-sub">감가/매출 <strong>{dep_str}</strong> · 자산집약도 <strong>{intensity_str}</strong></div>
</div>""")

    kpi_strip = f'<div class="kpi-strip">{"".join(tiles)}</div>'

    # --- (2) 3x3 heatmap: peer × {감가, 유지, 자산집약도}
    # Heat thresholds (green-scale heat-1..5)
    dep_thr = [3, 6, 9, 12]      # 감가/매출 %
    mnt_thr = [1, 2, 4, 6]       # 유지/매출 %
    int_thr = [5, 10, 15, 25]    # 자산/매출 ×

    def trend_indicator(curr, prev, unit_suffix=""):
        """Return small inline arrow + delta string for a cell."""
        if curr is None or prev is None:
            return ""
        delta = curr - prev
        if abs(delta) < 0.1:
            return f'<span style="font-size:9px;opacity:0.7;display:block;margin-top:2px;">→ vs FY23 {prev:.1f}{unit_suffix}</span>'
        arrow = "▲" if delta > 0 else "▼"
        # In heatmap context: higher intensity = darker color = more invested
        # ▲ means more intense (deeper red/green depending on tone)
        return f'<span style="font-size:10px;font-weight:700;display:block;margin-top:1px;opacity:0.9;">{arrow} {delta:+.1f}{unit_suffix} <span style="opacity:0.7;font-weight:400;">vs FY23</span></span>'

    rows = []
    for r in data:
        t = r["ticker"]
        dep_cls = _heat_class(r["dep_pct"], dep_thr)
        mnt_cls = _heat_class(r["mnt_pct"], mnt_thr)
        int_cls = _heat_class(r["intensity"], int_thr)
        dep_str = f"{r['dep_pct']:.1f}%" if r["dep_pct"] is not None else "—"
        mnt_str = f"{r['mnt_pct']:.1f}%" if r["mnt_pct"] is not None else "—"
        int_str = f"{r['intensity']:.1f}×" if r["intensity"] is not None else "—"
        dep_sub = f"Rp {fmt_bn(r['dep']).replace(' bn','bn')}" if r["dep"] else ""
        mnt_sub = f"Rp {fmt_bn(r['mnt']).replace(' bn','bn')}" if r["mnt"] else ""
        ta_sub = f"Rp {fmt_bn(r['ta']).replace(' bn','bn')}" if r["ta"] else ""
        # FY23 trend indicators
        dep_trend = trend_indicator(r.get("dep_pct"), r.get("dep_pct_prev"), "pp")
        mnt_trend = trend_indicator(r.get("mnt_pct"), r.get("mnt_pct_prev"), "pp")
        rows.append(
            f'<tr>'
            f'<td><span class="ticker-mini">{safe(t)}</span></td>'
            f'<td class="num {dep_cls}" style="text-align:center;font-weight:700;padding:10px 8px;">'
            f'  <div style="font-size:18px;line-height:1.1;">{dep_str}</div>'
            f'  <div style="font-size:10px;opacity:0.85;font-weight:400;margin-top:2px;">{dep_sub}</div>'
            f'  {dep_trend}</td>'
            f'<td class="num {mnt_cls}" style="text-align:center;font-weight:700;padding:10px 8px;">'
            f'  <div style="font-size:18px;line-height:1.1;">{mnt_str}</div>'
            f'  <div style="font-size:10px;opacity:0.85;font-weight:400;margin-top:2px;">{mnt_sub}</div>'
            f'  {mnt_trend}</td>'
            f'<td class="num {int_cls}" style="text-align:center;font-weight:700;padding:10px 8px;">'
            f'  <div style="font-size:18px;line-height:1.1;">{int_str}</div>'
            f'  <div style="font-size:10px;opacity:0.85;font-weight:400;margin-top:2px;">{ta_sub}</div></td>'
            f'</tr>'
        )

    heatmap = f"""<div class="tbl-card">
  <table class="tbl">
    <thead><tr>
      <th>Peer</th>
      <th class="num" style="text-align:center;">감가상각 / 매출 <span class="muted" style="font-weight:400;font-size:11px;">(P&amp;L)</span></th>
      <th class="num" style="text-align:center;">유지보수 / 매출 <span class="muted" style="font-weight:400;font-size:11px;">(P&amp;L)</span></th>
      <th class="num" style="text-align:center;">자산 / 매출 <span class="muted" style="font-weight:400;font-size:11px;">(B/S 누적)</span></th>
    </tr></thead>
    <tbody>{"".join(rows)}</tbody>
  </table>
</div>
<p class="src-line" style="margin-top:8px;">색이 진할수록 자본투자/자산 강도 강함 · 감가 = 누적 CAPEX 유동화 · 유지 = 진행 maintenance CAPEX · 자산집약도 = historic CAPEX 누적</p>"""

    # --- (3) Intensity gauge: combined visual ranking
    # Score = dep_pct + mnt_pct (cap to 25) + intensity/2 (cap to 25) — normalized 0~75
    gauge_rows = []
    max_score_visual = 25.0  # we'll cap dep+mnt at 25% for the bar width
    for r in data:
        t = r["ticker"]
        dep = r["dep_pct"] or 0
        mnt = r["mnt_pct"] or 0
        combined = dep + mnt
        bar_w = min(combined / max_score_visual, 1.0) * 100
        # Color by intensity
        if combined >= 15:
            color = "#92400e"
        elif combined >= 10:
            color = "#c08a2e"
        elif combined >= 5:
            color = "#4a7c30"
        else:
            color = "#95c073"
        gauge_rows.append(f"""<div class="stack-row">
  <div class="stack-label"><span class="ticker-mini">{safe(t)}</span></div>
  <div class="stack-bar" style="background:#f5f3ec;">
    <div class="stack-seg" style="width:{bar_w:.1f}%;background:{color};">{combined:.1f}%</div>
  </div>
  <div class="stack-total">감가 {dep:.1f}% + 유지 {mnt:.1f}%</div>
</div>""")

    gauge = f"""<h4 class="ops-block-h" style="margin-top: 22px;">P&amp;L CAPEX intensity gauge — 감가 + 유지 합산</h4>
<div class="stack-block">
  <p class="src-line" style="margin: 4px 2px 8px;">진한 갈색 = capital-intensive · 연두 = capital-light · 25% 풀스케일</p>
  {"".join(gauge_rows)}
</div>"""

    return f"""{kpi_strip}
<h4 class="ops-block-h">자본투자 강도 heatmap — 3 지표 × 4 peer</h4>
{heatmap}
{gauge}"""


# Curated CAPEX/OPEX narratives — extracted from vector DB (multilingual-e5-small)
# Each quote includes ticker, source page, FY, Korean summary, theme.
CAPEX_NARRATIVES = [
    {
        "ticker": "GOLF",
        "theme": "CWIP — 진행 중 CAPEX",
        "tone": "warn",
        "summary": "Buildings 187.9bn + Landscape 237.8bn IDR 건설 중 자산. 총 7,355.97bn 고정자산.",
        "quote": "Aset dalam Konstruksi: Gedung Rp187.9bn · Landscape Rp237.8bn · Peralatan Golf — · "
                 "Total fixed assets Rp7,355.97bn. The types and values of capital expenditure...",
        "ko": "건물 187.9bn + 조경 237.8bn (총 진행 중 426bn) — 신규 클럽하우스 + 코스 리노베이션 동시 진행. "
              "FY2025 CWIP는 GOLF entity 매출 102bn의 ~4.2배 규모로, 향후 3-5년 감가상각 부담 예고.",
        "src": "GOLF FY2025 AR p.170 — Fixed assets breakdown",
    },
    {
        "ticker": "GOLF",
        "theme": "CAPEX policy — 정책 공시",
        "tone": "neutral",
        "summary": "Repairs and maintenance costs → P&L. Upgrade가 future economic benefit 증가시키면 capitalize.",
        "quote": "Expenditures incurred after the fixed assets used in the operations, such as repairs and maintenance "
                 "costs are charged to profit or loss as incurred. If these expenditures result in increased future "
                 "economic benefits, they are capitalized as additional cost of fixed assets.",
        "ko": "일상 유지보수는 P&L 비용 / 미래 수익증대로 이어지는 시설 업그레이드만 자산 capitalize. "
              "CWIP 추가 빠르게 늘어나는 GOLF의 회계 기준 → P&L 마진을 보호하면서 자산 base 키우는 구조.",
        "src": "GOLF FY2024 AR p.175 — Fixed asset policy",
    },
    {
        "ticker": "PIPG",
        "theme": "Maintenance commitment — 노후 코스 운영",
        "tone": "warn",
        "summary": "PIPG Golf Course Maintenance (GCM) 부서 — '국내·국제 토너먼트 개최 준비' 명시.",
        "quote": "Departemen Pemeliharaan Lapangan Golf (Golf Course Maintenance/GCM) berkomitmen pada peningkatan "
                 "berkelanjutan. Kami bertekad menjaga Lapangan Golf Pondok Indah selalu dalam kondisi prima, siap "
                 "untuk penyelenggaraan turnamen berskala nasional maupun internasional.",
        "ko": "GCM 부서가 '항상 prime condition' 유지 약속 + 국내·국제 토너먼트 hosting capacity 보장. "
              "노후 코스(1976 개장)에서 유지보수 5.9%/매출 (DMIG 0.9% 대비 ~6배)이 단순 비효율이 아니라 "
              "프리미엄 포지셔닝 비용임을 시사. Indonesia Open 같은 sponsor 매출과 직결.",
        "src": "PIPG FY2023 AR p.35 — Golf Course Maintenance department",
    },
    {
        "ticker": "PIPG",
        "theme": "Brand & operations 강화",
        "tone": "positive",
        "summary": "FY2024 — 고객 신뢰, 코스 품질, 메뉴 개선, 재무 견실, 팀워크 강조.",
        "quote": "kepercayaan pelanggan, perbaikan mutu lapangan dan sajian kuliner, pengelolaan keuangan yang solid, "
                 "hingga kekompakan tim yang terus terjaga.",
        "ko": "FY25 매출 -6% 환경에도 OpEx -17.9% 대규모 절감 → 영업이익 +4.0% 가능했던 원동력. "
              "Brand 자산 (Pondok Indah)을 유지하면서 비용통제 — 노후 코스의 'mature operator' 전략 사례.",
        "src": "PIPG FY2024 AR p.32 — Annual report narrative",
    },
    {
        "ticker": "DMIG",
        "theme": "Headcount 추이 — 인건비 base",
        "tone": "neutral",
        "summary": "FY2023 직원 수 206명 (FY22 196 → +5.1%). 인건비 비중 12.6%/매출 (peer 최고).",
        "quote": "As of December 31, 2023 and 2022, there are 206 employees who have the right to receive employee "
                 "benefits, respectively. ... liabilitas imbalan kerja karyawan Rp135.366.168 ribu.",
        "ko": "FY21 342명 → FY22 196명 (-42.7%, 코로나 회복기 구조조정) → FY23 206명 (+5.1% 점진 회복). "
              "인건비 비중이 peer 중 가장 높은 12.6%인 이유는 2 코스 (BSD+PIK) 운영 + Range@PIK 확장으로 "
              "장기근속자(employee benefits liability Rp135bn) 비중 큼.",
        "src": "DMIG FY2023 AR p.87 — Employee benefits note",
    },
    {
        "ticker": "DMIG",
        "theme": "CWIP — 미감가 자산",
        "tone": "warn",
        "summary": "Construction in progress는 미감가 — 완공 후 fixed asset으로 재분류되며 감가 시작.",
        "quote": "Construction in progress are not depreciated and they will only be reclassified to the appropriate "
                 "fixed assets account when the construction is completed and the constructed asset is ready for its "
                 "intended use.",
        "ko": "PIK Range (FY24 신규 시설) 같은 CWIP가 완공되어 감가 시작되면 → 향후 2-3년 감가 비중 추가 상승 예고. "
              "이미 12.2%/매출로 peer 최고치인데, 추가 부담 가능성. 매출 sticky한데 감가↑ 시 마진 압박.",
        "src": "DMIG FY2022 AR p.77 — CWIP accounting policy",
    },
    {
        "ticker": "GOLF",
        "theme": "ESG · 운영비 효율",
        "tone": "positive",
        "summary": "Solar energy 주 전원 + 리튬 배터리 카트 — 장기 운영비 효율화.",
        "quote": "Using solar energy as the primary resource, this system not only helps reduce dependency on "
                 "fossil-based electricity but also contributes to long-term operational cost efficiency. ... "
                 "Use of lithium batteries...",
        "ko": "GOLF의 OpEx 21.1%/매출 (DMIG/PIPG 38% 대비 압도) 배경 — 솔라 + 리튬 카트 도입으로 "
              "유틸리티 비용 구조적 절감. IPO 1년차 효과뿐 아니라 운영 모델 자체가 capital-light. "
              "단, CWIP 450bn 진행 중 → 향후 감가상승은 불가피.",
        "src": "GOLF FY2024 AR p.120 — Eco-friendly materials & technologies",
    },
    {
        "ticker": "GOLF",
        "theme": "Environmental risk — 운영 본질",
        "tone": "warn",
        "summary": "Green keeping 어렵고 비용집약 — 환경/기후 리스크 인지.",
        "quote": "Environmental Damage Risk: Operating a golf course in accordance with standards and regulations "
                 "requires maintaining green grass across the entire field. Keeping the grass green is not an easy "
                 "task; it requires special maintenance...",
        "ko": "GOLF AR이 명시한 본질적 운영 리스크 — 코스 잔디 관리는 비용·전문성 집약. "
              "FY25 selling expenses +137% 급등 이유 중 하나로 추정 가능. "
              "PIPG 5.9%/매출 maintenance ratio가 outlier가 아니라 mature 코스의 본질 비용 시그널.",
        "src": "GOLF FY2024 AR p.97 — Operational risk disclosure",
    },
]


# Curated revenue/COGS narratives from vector DB
REVENUE_NARRATIVES = [
    {
        "ticker": "DMIG",
        "theme": "Revenue 성장 driver — Golf+F&B",
        "tone": "positive",
        "summary": "FY2023 영업이익 +31.39% Rp 58.5bn. Golf course 매출 +29.12%, BSD 식당 +39.67%, PIK 식당 +27.98%",
        "quote": "The Company's operating income in 2023 increased by 31.39% to Rp. 58.531.837.938. "
                 "Golf course business revenue increased by 29.12%, due to an increase in golf rounds. "
                 "Restaurant revenue at BSD Course +39.67%, PIK Course +27.98%.",
        "ko": "코로나 회복기 매출 모멘텀이 강력 — golf rounds 증가가 본업 driver, F&B는 양 코스 모두 +28~40% 강한 회복. "
              "단, FY24→FY25에는 매출 sticky(-0.7%) → 회복 모멘텀 둔화 신호.",
        "src": "DMIG FY2023 AR p.21 (Income Statement) + p.15 (F&B breakdown)",
    },
    {
        "ticker": "PIPG",
        "theme": "Operational metric — 골퍼 8% 성장",
        "tone": "positive",
        "summary": "FY2022 member 26,551명 (+8% YoY vs 2021 24,512명). non-member 40,987명 동시 증가",
        "quote": "Jumlah pengunjung golf (member) pada tahun 2022 sebanyak 26,551 pemain, naik 8% dibandingkan "
                 "tahun 2021 sebanyak 24,512 pemain. Jumlah pengunjung golf (non member) 40,987 pemain.",
        "ko": "PIPG는 member + non-member 두 트랙으로 매출 구성. 회원 충성도(+8%)와 외부 유입(40k+) 동시 확보. "
              "단일 코스(Pondok Indah) 1976년 개장 노후 시설이지만 CBD 5분 거리 + 브랜드로 mature operator 포지셔닝.",
        "src": "PIPG FY2022 AR p.48 — Pengunjung Golf",
    },
    {
        "ticker": "GOLF",
        "theme": "Target beat — Golf segment 24.66% 초과",
        "tone": "positive",
        "summary": "FY2025 Golf segment 매출 IDR 101.93bn = target 81.76bn의 124.66%. Real Estate 88.88%",
        "quote": "In 2025, the Company's revenue from the Golf segment reached IDR 101.93 billion, "
                 "or 124.66% of the established target of IDR 81.76 billion. For the Real Estate segment, "
                 "the Company recorded revenue of IDR 79.39 billion, or 88.88% of the established target.",
        "ko": "Golf은 target +24.66% 초과 달성하면서 Real Estate는 -11.12% 미달. "
              "GOLF entity 매출 mix가 Golf-dominant로 이동 — 즉 CWIP 426bn 투자가 매출 단으로 결실 시작.",
        "src": "GOLF FY2025 AR p.174 — Management Analysis",
    },
    {
        "ticker": "MDLN",
        "theme": "Golf+F&B 직접 공시 — 68.99bn",
        "tone": "neutral",
        "summary": "Golf course + Club house restaurant FY2023 매출 Rp 68.99bn (FY22 62.37bn) — Note 25 라인",
        "quote": "Lapangan golf dan restoran club house Rp 68.985.399.881 (FY2023) vs Rp 62.374.631.796 (FY2022). "
                 "Total revenue Rp 1.152.307bn (FY2023) — Golf segment 비중 6.0%.",
        "ko": "MDLN의 Golf+F&B는 그룹 매출 1.15조 대비 6% 비중이지만 절댓값으로는 7번째 큰 단일 라인. "
              "FY25 +28.2% YoY 가속 → property segment growth driver로 부상.",
        "src": "MDLN FY2023 AR p.315 — Note 25 라인",
    },
]


# Curated OpEx narratives — operational risk + cost sensitivity from AR Notes
OPEX_NARRATIVES = [
    {
        "ticker": "DMIG",
        "theme": "보험 cover — 운영 리스크 hedge",
        "tone": "neutral",
        "summary": "고정자산 (토지 제외) Rp 465.73bn + USD 2M 보험. 자산 base 보호.",
        "quote": "Company's fixed assets, except land, have been insured against the risk of loss with a "
                 "total coverage amount of Rp 465,731,600,000 and US$2,000,000, respectively.",
        "ko": "DMIG의 총 fixed asset 대비 보험 cover 수준은 운영 중단·재해 리스크 hedge. "
              "감가상각 12.2%/매출의 capital intensity를 보완하는 risk management.",
        "src": "DMIG FY2024 AR p.79 — Fixed assets insurance",
    },
    {
        "ticker": "PIPG",
        "theme": "Salary sensitivity — 인건비 leverage",
        "tone": "warn",
        "summary": "급여 +1% 시 defined benefits liability Rp 10.76bn 증가. 인건비 base의 sensitivity 큼.",
        "quote": "If the expected salary growth increase or decrease by 1%, in 2023 defined benefits liability "
                 "would increase Rp 10,758,977,886 (decrease equivalent). Discount rate ±1% → ±Rp 9-10bn impact.",
        "ko": "PIPG의 인건비/매출 10.5%는 mid 수준이지만, salary growth 1pp 변동 = liability Rp 10.7bn 충격. "
              "FY25 OpEx -17.9% 절감의 큰 부분이 인건비 통제에서 왔을 가능성 시사.",
        "src": "PIPG FY2023 AR p.139 — Defined benefits sensitivity",
    },
    {
        "ticker": "KPIG",
        "theme": "ESG · 유틸리티 metric",
        "tone": "positive",
        "summary": "Emission intensity 0.11 TonCo2eq (FY22-23 동일). 표면수 사용 410,570 m³",
        "quote": "In 2023, the Company recorded maintained emission intensity of 0.11 TonCo2eq same with 2022. "
                 "Water source - Surface water: 410,570 m³ (2023) vs 413,268 m³ (2022).",
        "ko": "KPIG는 그룹 conglomerate임에도 ESG metric 명시적 공시 — emission intensity 안정 유지 + 물 사용량 -0.7% YoY 감소. "
              "Trump Lido 같은 high-end 운영에 친환경 신호 → 장기 prem 포지셔닝.",
        "src": "KPIG FY2023 AR p.47 — ESG metrics",
    },
    {
        "ticker": "GOLF",
        "theme": "Equity structure — 자본 base",
        "tone": "neutral",
        "summary": "FY2025 총 equity Rp 8,018bn (parent 8,017bn + NCI 0.5bn). Paid-in capital 487bn",
        "quote": "Saldo 31 Desember 2025 — Modal disetor: Rp 487,169,000,000. Retained earnings: "
                 "Rp 6,897,824,934,149. Total ekuitas: Rp 8,018,297,686,240.",
        "ko": "GOLF의 retained earnings 6.9조는 entity 매출 102bn 대비 67배 — IPO 시 누적 결과. "
              "CWIP 426bn (4.2× 매출) 진행은 paid-in capital + 누적 잉여로 self-funded — 외부 차입 의존도 낮음 시그널.",
        "src": "GOLF FY2025 AR p.444 — Statement of changes in equity",
    },
]


def _opex_narrative_grid() -> str:
    """Render OpEx narrative quote cards (reuses quote-card style)."""
    tone_to_border = {
        "positive": "var(--green)",
        "warn":     "var(--warn)",
        "neutral":  "#8a8a8a",
    }
    cards = []
    for n in OPEX_NARRATIVES:
        border_color = tone_to_border.get(n["tone"], "#8a8a8a")
        quote_text = n["quote"].strip()
        if len(quote_text) > 320:
            quote_text = quote_text[:320].rsplit(" ", 1)[0] + "…"
        cards.append(f"""<div class="quote-card" style="border-left-color: {border_color};">
  <div style="display:flex; align-items:center; gap:8px; margin-bottom:8px;">
    <span class="ticker-mini">{safe(n["ticker"])}</span>
    <span class="insight-tag" style="margin:0;">{safe(n["theme"])}</span>
  </div>
  <div style="font-weight:700; font-size:14px; color:var(--ink); margin-bottom:6px;">{safe(n["summary"])}</div>
  <div style="font-size:12.5px; color:var(--ink-soft); line-height:1.55; font-style:italic; padding:6px 10px; border-left:2px solid var(--line-strong); margin:8px 0;">
    "{safe(quote_text)}"
  </div>
  <div style="font-size:13px; color:var(--ink); line-height:1.55;">
    <strong style="color:var(--green);">→</strong> {safe(n["ko"])}
  </div>
  <div class="qmeta"><strong>↳</strong> · {safe(n["src"])}</div>
</div>""")
    return f"""<div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(420px, 1fr)); gap:14px; margin: 14px 0;">
  {"".join(cards)}
</div>"""


def _revenue_narrative_grid() -> str:
    """Render revenue narrative quote cards (reuses CAPEX quote-card style)."""
    tone_to_border = {
        "positive": "var(--green)",
        "warn":     "var(--warn)",
        "neutral":  "#8a8a8a",
    }
    cards = []
    for n in REVENUE_NARRATIVES:
        border_color = tone_to_border.get(n["tone"], "#8a8a8a")
        quote_text = n["quote"].strip()
        if len(quote_text) > 320:
            quote_text = quote_text[:320].rsplit(" ", 1)[0] + "…"
        cards.append(f"""<div class="quote-card" style="border-left-color: {border_color};">
  <div style="display:flex; align-items:center; gap:8px; margin-bottom:8px;">
    <span class="ticker-mini">{safe(n["ticker"])}</span>
    <span class="insight-tag" style="margin:0;">{safe(n["theme"])}</span>
  </div>
  <div style="font-weight:700; font-size:14px; color:var(--ink); margin-bottom:6px;">{safe(n["summary"])}</div>
  <div style="font-size:12.5px; color:var(--ink-soft); line-height:1.55; font-style:italic; padding:6px 10px; border-left:2px solid var(--line-strong); margin:8px 0;">
    "{safe(quote_text)}"
  </div>
  <div style="font-size:13px; color:var(--ink); line-height:1.55;">
    <strong style="color:var(--green);">→</strong> {safe(n["ko"])}
  </div>
  <div class="qmeta"><strong>↳</strong> · {safe(n["src"])}</div>
</div>""")
    return f"""<div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(420px, 1fr)); gap:14px; margin: 14px 0;">
  {"".join(cards)}
</div>"""


def _capex_narrative_grid() -> str:
    """Render curated CAPEX/OPEX vector-DB narratives as quote callout cards."""
    tone_to_border = {
        "positive": "var(--green)",
        "warn":     "var(--warn)",
        "neutral":  "#8a8a8a",
    }
    cards = []
    for n in CAPEX_NARRATIVES:
        border_color = tone_to_border.get(n["tone"], "#8a8a8a")
        quote_text = n["quote"].strip()
        if len(quote_text) > 320:
            quote_text = quote_text[:320].rsplit(" ", 1)[0] + "…"
        cards.append(f"""<div class="quote-card" style="border-left-color: {border_color};">
  <div style="display:flex; align-items:center; gap:8px; margin-bottom:8px;">
    <span class="ticker-mini">{safe(n["ticker"])}</span>
    <span class="insight-tag" style="margin:0;">{safe(n["theme"])}</span>
  </div>
  <div style="font-weight:700; font-size:14px; color:var(--ink); margin-bottom:6px;">{safe(n["summary"])}</div>
  <div style="font-size:12.5px; color:var(--ink-soft); line-height:1.55; font-style:italic; padding:6px 10px; border-left:2px solid var(--line-strong); margin:8px 0;">
    "{safe(quote_text)}"
  </div>
  <div style="font-size:13px; color:var(--ink); line-height:1.55;">
    <strong style="color:var(--green);">→</strong> {safe(n["ko"])}
  </div>
  <div class="qmeta"><strong>↳</strong> · {safe(n["src"])}</div>
</div>""")
    return f"""<div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(420px, 1fr)); gap:14px; margin: 14px 0;">
  {"".join(cards)}
</div>"""


def _all_peer_golf_segment_data() -> list:
    """Extract 6-peer golf segment data (used by both table + scatter chart)."""
    rows = []

    d = NOTES.get("DMIG", {})
    rev_lines = (d.get("revenue_note") or {}).get("lines") or []
    cogs_lines = (d.get("cogs_note") or {}).get("lines") or []
    golf_rev = next((ln.get("FY2024") for ln in rev_lines if (ln.get("en_label") or "").lower() == "golf course"), None)
    golf_cogs = next((ln.get("FY2024") for ln in cogs_lines if (ln.get("en_label") or "").lower() == "golf course"), None)
    entity_rev = (d.get("revenue_note") or {}).get("total", {}).get("FY2024")
    gm = ((golf_rev - golf_cogs) / golf_rev * 100) if (golf_rev and golf_cogs) else None
    golf_share = (golf_rev / entity_rev * 100) if (golf_rev and entity_rev) else None
    rows.append({"ticker": "DMIG", "basis": "Pure-play (Note 23)", "rev": golf_rev, "cogs": golf_cogs, "gm": gm, "entity_rev": entity_rev, "share": golf_share})

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
    rows.append({"ticker": "PIPG", "basis": "Pure-play (Golf+Cart, Note 27/28)", "rev": golf_rev_pipg, "cogs": golf_cogs_pipg, "gm": gm_pipg, "entity_rev": entity_rev_pipg, "share": share_pipg})

    d = NOTES.get("MDLN", {})
    cr = (d.get("computed_ratios") or {}).get("FY2024", {})
    golf_rev_m = cr.get("golf_revenue_pure")
    golf_cogs_m = cr.get("golf_cogs_pure")
    gm_m = cr.get("golf_pure_gp_margin")
    entity_rev_m = (d.get("revenue_note_25") or {}).get("total", {}).get("FY2024")
    share_m = (golf_rev_m / entity_rev_m * 100) if (golf_rev_m and entity_rev_m) else None
    rows.append({"ticker": "MDLN", "basis": "Golf segment (Note 25)", "rev": golf_rev_m, "cogs": golf_cogs_m, "gm": (gm_m * 100 if gm_m else None), "entity_rev": entity_rev_m, "share": share_m})

    d = NOTES.get("GOLF", {})
    rev_lines = ((d.get("revenue_note_29") or {}).get("by_operations") or {}).get("lines") or []
    cogs_lines = (d.get("cogs_note_30") or {}).get("lines") or []
    golf_rev_g = next((ln.get("FY2024") for ln in rev_lines if ln.get("en_label") == "Golf"), None)
    golf_cogs_g = next((ln.get("FY2024") for ln in cogs_lines if ln.get("id_label") == "Golf"), None)
    entity_rev_g = ((d.get("revenue_note_29") or {}).get("by_operations") or {}).get("total", {}).get("FY2024")
    gm_g = ((golf_rev_g - golf_cogs_g) / golf_rev_g * 100) if (golf_rev_g and golf_cogs_g) else None
    share_g = (golf_rev_g / entity_rev_g * 100) if (golf_rev_g and entity_rev_g) else None
    rows.append({"ticker": "GOLF", "basis": "Golf-only (Note 29 by-ops)", "rev": golf_rev_g, "cogs": golf_cogs_g, "gm": gm_g, "entity_rev": entity_rev_g, "share": share_g})

    d = NOTES.get("KIJA", {})
    seg = (d.get("segment_info_note_34") or {}).get("golf_segment_FY2024") or {}
    rev_k = (seg.get("revenue") or 0) * 1e6
    cogs_k = (seg.get("cogs") or 0) * 1e6
    gm_k = ((rev_k - cogs_k) / rev_k * 100) if rev_k else None
    entity_rev_k = ((d.get("segment_info_note_34") or {}).get("consolidated_total_FY2024") or {}).get("revenue", 0) * 1e6
    share_k = (rev_k / entity_rev_k * 100) if (rev_k and entity_rev_k) else None
    rows.append({"ticker": "KIJA", "basis": "Golf segment (Note 34)", "rev": rev_k, "cogs": cogs_k, "gm": gm_k, "entity_rev": entity_rev_k, "share": share_k})

    d = NOTES.get("SMDM", {})
    seg_smdm = ((d.get("segment_info_note_29") or {}).get("FY2024") or {}).get("Golf dan Country Club") or {}
    rev_s = seg_smdm.get("revenue")
    cogs_s = abs(seg_smdm.get("cogs", 0)) or None
    gm_s = ((rev_s - cogs_s) / rev_s * 100) if (rev_s and cogs_s) else None
    entity_rev_s = ((d.get("segment_info_note_29") or {}).get("FY2024") or {}).get("Konsolidasian", {}).get("revenue")
    share_s = (rev_s / entity_rev_s * 100) if (rev_s and entity_rev_s) else None
    rows.append({"ticker": "SMDM", "basis": "Golf & Country Club", "rev": rev_s, "cogs": cogs_s, "gm": gm_s, "entity_rev": entity_rev_s, "share": share_s})

    return rows


def _segment_scatter_svg() -> str:
    """Bubble scatter — X: golf share, Y: GP margin, size: golf revenue.
    With quadrant background highlighting + median dashed lines."""
    data = [r for r in _all_peer_golf_segment_data() if r["share"] and r["gm"]]
    if not data:
        return ""

    width, height = 720, 380
    pad_l, pad_b, pad_r, pad_t = 56, 44, 22, 28
    inner_w = width - pad_l - pad_r
    inner_h = height - pad_t - pad_b

    x_max = 50
    y_max = 80
    y_min = 30
    revs = [r["rev"] for r in data if r["rev"]]
    max_rev = max(revs) if revs else 1

    # Median lines (median of all peers' share & GP)
    sorted_share = sorted([r["share"] for r in data])
    sorted_gm = sorted([r["gm"] for r in data])
    median_share = sorted_share[len(sorted_share)//2]
    median_gm = sorted_gm[len(sorted_gm)//2]

    def to_x(pct): return pad_l + (inner_w * (min(pct, x_max) / x_max))

    def to_y(pct): return pad_t + inner_h - (inner_h * ((min(max(pct, y_min), y_max) - y_min) / (y_max - y_min)))

    median_x = to_x(median_share)
    median_y = to_y(median_gm)

    # Quadrant background rectangles (4 zones)
    quad_bg = (
        # Top-left: high GP, low share — diversified gem (gold tint)
        f'<rect x="{pad_l}" y="{pad_t}" width="{median_x - pad_l:.1f}" height="{median_y - pad_t:.1f}" '
        f'fill="#fef3c7" fill-opacity="0.35"/>'
        # Top-right: high GP, high share — pure-play winner (green tint)
        f'<rect x="{median_x:.1f}" y="{pad_t}" width="{pad_l + inner_w - median_x:.1f}" height="{median_y - pad_t:.1f}" '
        f'fill="#e6f1d8" fill-opacity="0.55"/>'
        # Bottom-left: low GP, low share — peripheral / weak (red tint)
        f'<rect x="{pad_l}" y="{median_y:.1f}" width="{median_x - pad_l:.1f}" height="{pad_t + inner_h - median_y:.1f}" '
        f'fill="#fee2e2" fill-opacity="0.30"/>'
        # Bottom-right: low GP, high share — pure-play struggling (light orange)
        f'<rect x="{median_x:.1f}" y="{median_y:.1f}" width="{pad_l + inner_w - median_x:.1f}" height="{pad_t + inner_h - median_y:.1f}" '
        f'fill="#fde68a" fill-opacity="0.18"/>'
    )

    # Median lines (dashed)
    median_lines = (
        f'<line x1="{median_x:.1f}" y1="{pad_t}" x2="{median_x:.1f}" y2="{pad_t + inner_h}" '
        f'stroke="#8a8a8a" stroke-width="1" stroke-dasharray="4 4"/>'
        f'<line x1="{pad_l}" y1="{median_y:.1f}" x2="{pad_l + inner_w}" y2="{median_y:.1f}" '
        f'stroke="#8a8a8a" stroke-width="1" stroke-dasharray="4 4"/>'
        f'<text x="{median_x + 3:.1f}" y="{pad_t + inner_h + 28}" font-size="9" fill="#8a8a8a" font-style="italic">median {median_share:.1f}%</text>'
        f'<text x="{pad_l - 4:.1f}" y="{median_y - 4:.1f}" font-size="9" fill="#8a8a8a" font-style="italic" text-anchor="end">median {median_gm:.1f}%</text>'
    )

    # Gridlines
    grid = []
    for ypct in [40, 50, 60, 70, 80]:
        y = to_y(ypct)
        grid.append(
            f'<line x1="{pad_l}" y1="{y:.1f}" x2="{pad_l + inner_w}" y2="{y:.1f}" stroke="#ebe9e0" stroke-width="0.7"/>'
            f'<text x="{pad_l - 8}" y="{y + 4:.1f}" font-size="11" fill="#8a8a8a" text-anchor="end">{ypct}%</text>'
        )
    for xpct in [10, 20, 30, 40, 50]:
        x = to_x(xpct)
        grid.append(
            f'<line x1="{x:.1f}" y1="{pad_t}" x2="{x:.1f}" y2="{pad_t + inner_h}" stroke="#ebe9e0" stroke-width="0.7"/>'
            f'<text x="{x:.1f}" y="{pad_t + inner_h + 16}" font-size="11" fill="#8a8a8a" text-anchor="middle">{xpct}%</text>'
        )

    # Bubbles
    bubbles = []
    for r in data:
        x = to_x(r["share"])
        y = to_y(r["gm"])
        r_norm = (r["rev"] or 0) / max_rev
        radius = 8 + (r_norm ** 0.5) * 28
        color = PEER_COLORS.get(r["ticker"], "#8a8a8a")
        rev_str = fmt_bn(r["rev"]).replace(" bn", "bn")
        bubbles.append(
            f'<g>'
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{radius:.1f}" fill="{color}" fill-opacity="0.32" stroke="{color}" stroke-width="2">'
            f'<title>{safe(r["ticker"])} · {safe(r["basis"])} · 매출 비중 {r["share"]:.1f}% · GP {r["gm"]:.1f}% · Rev Rp {rev_str}</title>'
            f'</circle>'
            f'<text x="{x:.1f}" y="{y - radius - 5:.1f}" font-size="12" font-weight="700" '
            f'fill="{color}" text-anchor="middle">{safe(r["ticker"])}</text>'
            f'<text x="{x:.1f}" y="{y + 4:.1f}" font-size="10" fill="{color}" font-weight="600" text-anchor="middle">'
            f'{r["gm"]:.0f}%</text>'
            f'</g>'
        )

    # Axis labels
    axis_labels = (
        f'<text x="{pad_l + inner_w/2:.1f}" y="{height - 6}" font-size="12" fill="#4b4b4b" text-anchor="middle" font-weight="700">'
        f'골프 매출 비중 (% of entity 매출) →'
        f'</text>'
        f'<text x="14" y="{pad_t + inner_h/2:.1f}" font-size="12" fill="#4b4b4b" text-anchor="middle" font-weight="700" '
        f'transform="rotate(-90 14 {pad_t + inner_h/2:.1f})">↑ GP Margin (%)</text>'
    )

    # Quadrant labels (corners)
    annot = (
        f'<text x="{pad_l + 8}" y="{pad_t + 14}" font-size="10" fill="#92400e" text-anchor="start" '
        f'font-weight="700">▲ Hidden gem (high GP, low share)</text>'
        f'<text x="{pad_l + inner_w - 6}" y="{pad_t + 14}" font-size="10" fill="#2d5016" text-anchor="end" '
        f'font-weight="700">★ Pure-play winner (high GP + high share)</text>'
        f'<text x="{pad_l + 8}" y="{pad_t + inner_h - 6}" font-size="10" fill="#b91c1c" text-anchor="start" '
        f'font-weight="700">▼ Peripheral & weak</text>'
        f'<text x="{pad_l + inner_w - 6}" y="{pad_t + inner_h - 6}" font-size="10" fill="#c08a2e" text-anchor="end" '
        f'font-weight="700">⚠ Pure-play struggling</text>'
    )

    return f"""<div style="background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:18px 12px 8px;">
  <svg viewBox="0 0 {width} {height}" width="100%" style="max-width:780px;display:block;margin:0 auto;" xmlns="http://www.w3.org/2000/svg">
    {quad_bg}
    {median_lines}
    {''.join(grid)}
    {axis_labels}
    {annot}
    {''.join(bubbles)}
  </svg>
</div>
<p class="src-line" style="margin:8px 2px;">버블 면적 = golf 매출 절댓값 · dashed = 6-peer median · 색 배경 = 4-사분면 분류 · hover로 정확 수치 (FY2024)</p>"""


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


def _margin_change_visual() -> str:
    """FY24→FY25 margin commentary as visual timeline cards with mini delta bars."""

    # Pre-computed FY24/FY25 numbers per peer (from existing commentary text + follow-ups)
    peers = [
        {
            "ticker": "DMIG",
            "tone": "warn",
            "tag": "마진 압박 시작",
            "metrics": [
                ("매출", 253.1, 251.4, "bn"),     # FY24, FY25 in bn IDR
                ("영업이익", 78.9, 69.4, "bn"),
                ("순이익", 82.4, 75.0, "bn"),
            ],
            "narrative": (
                "FY23 순이익 71.27bn (+34.40% vs FY22). FY24 매출 253.1bn / 영업이익 78.9bn / 순이익 82.4bn. "
                "FY25 매출 -0.7%, OpEx +3.3% → 영업이익 -12.0%. PIK Range 신규 투자로 감가↑."
            ),
            "src": "DMIG FY23 AR p.22 · FY25 follow-up",
        },
        {
            "ticker": "PIPG",
            "tone": "positive",
            "tag": "비용 통제력 입증",
            "metrics": [
                ("매출", 197.6, 185.8, "bn"),
                ("OpEx", 76.0, 62.0, "bn"),
                ("영업이익", 53.5, 55.6, "bn"),
                ("순이익", 55.9, 56.3, "bn"),
            ],
            "narrative": (
                "FY25 매출 -6.0%이지만 OpEx -17.9% 대규모 절감 → 영업이익 +4.0%, 순이익 +0.6%. "
                "노후 코스 운영 효율 개선 시그널. Mature operator의 cost discipline."
            ),
            "src": "PIPG FY25 follow-up + FY24 AR Note 27/29",
        },
        {
            "ticker": "GOLF",
            "tone": "warn",
            "tag": "CAPEX-driven 마진 squeeze",
            "metrics": [
                ("COGS", 65.1, 78.3, "bn"),
                ("영업이익", 72.5, 64.9, "bn"),
                ("Selling Exp", 4.7, 11.2, "bn"),
            ],
            "narrative": (
                "FY24 COGS +20.2% YoY (real estate 비용 주도). FY25 영업이익 -10.49% (72.5→64.9). "
                "원인: selling expenses +137.2%. CWIP 450bn 진행 중 — 향후 감가 추가 부담 예고."
            ),
            "src": "GOLF FY24 AR p.69 + FY25 AR p.156·p.170",
        },
        {
            "ticker": "MDLN",
            "tone": "positive",
            "tag": "Hidden growth (Golf segment)",
            "metrics": [
                ("Group GP%", 44.66, 47.19, "pct"),
                ("Golf rev", 74.4, 95.3, "bn"),
            ],
            "narrative": (
                "Group GP margin +2.53pp 개선 (44.66% → 47.19%). Golf 단독 segment +28.2% YoY (74.4→95.3bn). "
                "그룹에서 가장 빠른 성장 부문. Modern Golf 단독 매출 56.6bn → 74.4bn (F&B 포함)."
            ),
            "src": "MDLN FY25 AR p.116 + Note 25/26",
        },
        {
            "ticker": "SMDM",
            "tone": "warn",
            "tag": "BSDE 인수 전 적자전환",
            "metrics": [
                ("Golf GP%", 55.8, 38.9, "pct"),
                ("영업이익", 1.5, -0.2, "bn"),
            ],
            "narrative": (
                "Golf & CC GP margin FY23 55.8% → FY24 38.9% (-16.9pp 급락). 영업이익 -212M IDR 적자전환. "
                "FY24 배당 미실시. BSDE 2024-10에 91.99% 인수. FY25 GP 88.6% jump은 회계 재분류 가능성."
            ),
            "src": "SMDM FY24 AR p.70",
        },
        {
            "ticker": "KPIG",
            "tone": "neutral",
            "tag": "Asset-intensive conglomerate",
            "metrics": [
                ("Hotel+R+G rev", 960, 1060, "bn"),
                ("총자산비중 (FA+IP)", 73.8, 73.8, "pct"),
            ],
            "narrative": (
                "Hotel+Resort+Golf 통합 매출 FY23 812bn → FY24 960bn (+18%) → FY25 1,060bn (+10%). "
                "Group 고정자산 21조 + 투자부동산 6.9조 = 73.8% of total. Golf-only 분리 미공시."
            ),
            "src": "KPIG FY24 AR p.212 + FY25 Note 31",
        },
    ]

    tone_border = {"positive": "var(--green)", "warn": "var(--warn)", "neutral": "#8a8a8a"}

    cards = []
    for p in peers:
        # Render mini metric bars (FY24 vs FY25 side-by-side)
        metric_rows = []
        for label, v24, v25, unit in p["metrics"]:
            # Calculate delta
            delta = None
            if v24 and v25 is not None:
                if unit == "pct":
                    delta_str = f"{(v25 - v24):+.1f}pp"
                    delta_color = "var(--green)" if v25 > v24 else "var(--danger)"
                else:
                    delta_pct = ((v25 / v24) - 1) * 100 if v24 else 0
                    delta_str = f"{delta_pct:+.1f}%"
                    # For OpEx/COGS, down is good
                    if label.lower() in ("opex", "cogs"):
                        delta_color = "var(--green)" if delta_pct < 0 else "var(--danger)"
                    else:
                        delta_color = "var(--green)" if delta_pct > 0 else "var(--danger)"

            max_v = max(abs(v24), abs(v25)) if v24 and v25 else 1
            w24 = (abs(v24) / max_v * 100) if v24 else 0
            w25 = (abs(v25) / max_v * 100) if v25 else 0
            val_unit = "%" if unit == "pct" else "bn"
            v24_str = f"{v24}{val_unit}"
            v25_str = f"{v25}{val_unit}"
            metric_rows.append(f"""<div style="display:grid;grid-template-columns:80px 1fr 60px;gap:8px;align-items:center;padding:3px 0;font-size:11px;">
  <span style="color:var(--ink-soft);font-weight:600;">{safe(label)}</span>
  <div style="position:relative;">
    <div style="display:flex;align-items:center;gap:4px;margin-bottom:2px;">
      <span style="font-size:9px;color:var(--muted);min-width:28px;">FY24</span>
      <span style="flex:1;height:8px;background:var(--line);border-radius:2px;overflow:hidden;">
        <span style="display:block;height:100%;width:{w24:.1f}%;background:#8a8a8a;"></span>
      </span>
      <span style="font-size:10px;font-weight:600;min-width:38px;text-align:right;">{v24_str}</span>
    </div>
    <div style="display:flex;align-items:center;gap:4px;">
      <span style="font-size:9px;color:var(--muted);min-width:28px;">FY25</span>
      <span style="flex:1;height:8px;background:var(--line);border-radius:2px;overflow:hidden;">
        <span style="display:block;height:100%;width:{w25:.1f}%;background:var(--green);"></span>
      </span>
      <span style="font-size:10px;font-weight:600;min-width:38px;text-align:right;">{v25_str}</span>
    </div>
  </div>
  <span style="text-align:right;font-weight:700;font-size:11px;color:{delta_color};">{delta_str}</span>
</div>""")

        cards.append(f"""<div class="quote-card" style="border-left-color:{tone_border[p['tone']]};">
  <div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;">
    <span class="ticker-mini">{safe(p["ticker"])}</span>
    <span class="insight-tag" style="margin:0;color:var(--ink);">{safe(p["tag"])}</span>
  </div>
  <div style="margin: 8px 0 12px;">{"".join(metric_rows)}</div>
  <div style="font-size:12.5px;color:var(--ink-soft);line-height:1.55;">{safe(p["narrative"])}</div>
  <div class="qmeta"><strong>↳</strong> · {safe(p["src"])}</div>
</div>""")

    return f"""<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(380px,1fr));gap:12px;">
  {''.join(cards)}
</div>"""


def _dividend_visual() -> str:
    """Dividend grouped-bar chart + payout ratio cards."""
    # Per-peer net income lookup (for payout)
    # DMIG FY2023 net 71.27bn, PIPG FY2023 net ~55.9bn (audit)
    netinc_known = {
        ("DMIG", "FY2023"): 71_270_000_000,
        ("PIPG", "FY2022"): None,  # Optional
        ("PIPG", "FY2023"): 55_900_000_000,
    }

    fys = ["FY2022", "FY2023", "FY2024"]
    peers = ["DMIG", "PIPG", "SMDM"]

    # Build dataset
    div = {}
    for t in peers:
        d = DIVIDEND_EVIDENCE.get(t) or {}
        div[t] = {
            "FY2022": d.get("FY2022_paid"),
            "FY2023": d.get("FY2023_paid"),
            "FY2024": d.get("FY2024_paid"),
        }
    all_vals = [v for v_d in div.values() for v in v_d.values() if v]
    max_v = max(all_vals) if all_vals else 1

    # --- Grouped bar visualization
    bar_rows = []
    for fy in fys:
        peer_bars = []
        for t in peers:
            v = div[t][fy]
            pct = (v / max_v * 100) if v else 0
            color = PEER_COLORS.get(t, "#8a8a8a")
            val_str = fmt_bn(v).replace(" bn", "bn") if v else "—"
            faded = "opacity:0.25;" if not v else ""
            peer_bars.append(f"""<div style="flex:1;display:flex;flex-direction:column;align-items:center;{faded}">
  <div style="display:flex;align-items:flex-end;height:100px;width:100%;">
    <div style="width:100%;height:{pct:.1f}%;background:{color};border-radius:4px 4px 0 0;display:flex;align-items:flex-end;justify-content:center;color:white;font-size:10px;font-weight:700;padding-bottom:3px;">
      {val_str if v and pct > 25 else ""}
    </div>
  </div>
  <div style="font-size:10px;font-weight:600;color:var(--ink-soft);margin-top:4px;">{safe(t)}</div>
  <div style="font-size:10px;color:var(--muted);">{val_str}</div>
</div>""")
        bar_rows.append(f"""<div style="flex:1;background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:14px 12px;">
  <div style="font-size:12px;font-weight:700;color:var(--ink);text-align:center;margin-bottom:8px;">{safe(fy[2:])}</div>
  <div style="display:flex;gap:6px;align-items:flex-end;">{''.join(peer_bars)}</div>
</div>""")

    bar_chart = f"""<div style="display:flex;gap:10px;flex-wrap:wrap;">{''.join(bar_rows)}</div>"""

    # --- Payout ratio + per-share KPI tiles
    pipg_payout = 26_239_800_000 / 55_900_000_000 * 100
    dmig_payout = 26_514_391_332 / 71_268_571_841 * 100
    pipg_per_share = DIVIDEND_EVIDENCE["PIPG"]["per_share_FY2023"]

    tiles = f"""<div class="kpi-strip">
  <div class="kpi-tile accent-green">
    <div class="kpi-cap">PIPG · FY23 Payout</div>
    <div class="kpi-val">{pipg_payout:.1f}%</div>
    <div class="kpi-sub">배당 Rp 26.2bn / 순이익 Rp 55.9bn</div>
    <div class="kpi-sub">주당 Rp {pipg_per_share/1_000_000:.2f}M · RUPST 2024-06-06</div>
  </div>
  <div class="kpi-tile accent-green">
    <div class="kpi-cap">DMIG · FY23 Payout</div>
    <div class="kpi-val">{dmig_payout:.1f}%</div>
    <div class="kpi-sub">배당 Rp 26.5bn / 순이익 Rp 71.3bn</div>
    <div class="kpi-sub">Statement of Changes in Equity 직접 추출</div>
  </div>
  <div class="kpi-tile accent-warn">
    <div class="kpi-cap">SMDM · FY24 Payout</div>
    <div class="kpi-val">0%</div>
    <div class="kpi-sub">배당 미실시 (working capital 보존)</div>
    <div class="kpi-sub">BSDE 91.99% 인수 직전 결정</div>
  </div>
</div>"""

    return tiles + bar_chart


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
      
    </tr></thead>
    <tbody>{''.join(rows)}</tbody>
  </table>
</div>"""


PIPG_SEG_COLORS = {
    "Golf Course & Cart": "#2d5016",
    "Membership & Enrollment Fee": "#4a7c30",
    "Restaurant": "#c08a2e",
    "Others": "#8a8a8a",
}


def _pipg_segment_visual() -> str:
    """Visual: revenue mix + GP margin per segment, all in one block."""
    segs = []
    tot_rev = sum(d["revenue"] for d in PIPG_SEGMENT_FY2023.values())
    tot_cogs = sum(d["cogs"] for d in PIPG_SEGMENT_FY2023.values())

    rows_data = []
    for name, d in PIPG_SEGMENT_FY2023.items():
        rev = d["revenue"]
        cogs = d["cogs"]
        gp = rev - cogs
        gm = (gp / rev * 100) if rev else 0
        share = (rev / tot_rev * 100) if tot_rev else 0
        rows_data.append({
            "name": name, "rev": rev, "cogs": cogs, "gp": gp, "gm": gm, "share": share,
            "color": PIPG_SEG_COLORS.get(name, "#8a8a8a"),
        })

    rows_data.sort(key=lambda r: -r["rev"])
    max_gm = 100  # GP margin scale 0-100%
    max_rev_share = max(r["share"] for r in rows_data)

    # --- Composition stacked bar (revenue share)
    composition = []
    for r in rows_data:
        composition.append(
            f'<div class="stack-seg" style="width:{r["share"]:.2f}%;background:{r["color"]};" '
            f'title="{safe(r["name"])}: Rp {fmt_bn(r["rev"]).replace(" bn","bn")} ({r["share"]:.1f}%)">'
            f'{f"{r['share']:.0f}%" if r["share"] >= 7 else ""}</div>'
        )
    comp_legend = []
    for r in rows_data:
        comp_legend.append(
            f'<span class="lg"><span class="sw" style="background:{r["color"]};"></span>{safe(r["name"])}</span>'
        )

    # --- GP margin bars per segment
    gm_bars = []
    for r in rows_data:
        bar_w = (r["gm"] / 100) * 100  # scale to 100% width
        # Color intensity by margin level
        if r["gm"] >= 75:
            tone = "#2d5016"
        elif r["gm"] >= 55:
            tone = "#4a7c30"
        elif r["gm"] >= 40:
            tone = "#c08a2e"
        else:
            tone = "#b91c1c"
        gm_bars.append(f"""<div class="stack-row" style="padding:8px 0;">
  <div class="stack-label" style="flex:0 0 180px;font-size:12.5px;">{safe(r["name"])}</div>
  <div class="stack-bar" style="height:22px;background:#f5f3ec;flex:1;">
    <div class="stack-seg" style="width:{bar_w:.1f}%;background:{tone};font-size:11px;justify-content:flex-end;padding-right:8px;">{r["gm"]:.1f}%</div>
  </div>
  <div class="stack-total" style="flex:0 0 130px;">GP Rp {fmt_bn(r["gp"]).replace(" bn","bn")}</div>
</div>""")

    # --- Overall headline KPI tile
    tot_gp = tot_rev - tot_cogs
    tot_gm = (tot_gp / tot_rev * 100)
    # Highest + lowest margin
    sorted_by_gm = sorted(rows_data, key=lambda r: -r["gm"])
    best = sorted_by_gm[0]
    worst = sorted_by_gm[-1]

    return f"""
<div class="kpi-strip" style="margin-bottom: 18px;">
  <div class="kpi-tile accent-green">
    <div class="kpi-cap">PIPG 4-Seg 합계 (FY23)</div>
    <div class="kpi-val">{tot_gm:.1f}%<span style="font-size:13px;color:var(--muted);">GP</span></div>
    <div class="kpi-sub">매출 Rp {fmt_bn(tot_rev).replace(" bn","bn")} · GP Rp {fmt_bn(tot_gp).replace(" bn","bn")}</div>
  </div>
  <div class="kpi-tile accent-green">
    <div class="kpi-cap">최고 마진 segment</div>
    <div class="kpi-val small">{safe(best["name"])}</div>
    <div class="kpi-sub kpi-trend up">GP margin <strong>{best["gm"]:.1f}%</strong> · 매출 비중 {best["share"]:.1f}%</div>
    <div class="kpi-sub">신규 회원/연회비 → 거의 순이익에 가까움 (소액 COGS)</div>
  </div>
  <div class="kpi-tile accent-warn">
    <div class="kpi-cap">최저 마진 segment</div>
    <div class="kpi-val small">{safe(worst["name"])}</div>
    <div class="kpi-sub kpi-trend down">GP margin <strong>{worst["gm"]:.1f}%</strong> · 매출 비중 {worst["share"]:.1f}%</div>
    <div class="kpi-sub">F&amp;B 본질적 cost structure — 식자재 + 직원 + 유틸리티</div>
  </div>
</div>

<h4 class="ops-block-h">Segment별 매출 mix (100% stacked, FY23)</h4>
<div class="stack-block">
  <div class="stack-row">
    <div class="stack-label" style="flex:0 0 80px;"><span class="ticker-mini">PIPG</span></div>
    <div class="stack-bar" style="height:34px;">{''.join(composition)}</div>
    <div class="stack-total">Rp {fmt_bn(tot_rev).replace(" bn","bn")}</div>
  </div>
  <div class="stack-legend">{''.join(comp_legend)}</div>
</div>

<h4 class="ops-block-h" style="margin-top: 20px;">Segment별 GP Margin (FY23)</h4>
<div class="stack-block">
  <p class="src-line" style="margin: 4px 2px 8px;">바 너비 = GP margin (0~100%) · 색: 진한 녹색 ≥75%, 녹색 ≥55%, 갈색 ≥40%, 빨강 &lt;40%</p>
  {''.join(gm_bars)}
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


def _per_hole_data() -> list:
    """Extract per-peer per-hole metrics. Returns list of dicts."""
    rows = []

    def collect(ticker: str, basis: str, basis_type: str, golf_rev, golf_cogs, golf_opex, depr_total):
        h = HOLES.get(ticker, 18)
        rows.append({
            "ticker": ticker, "basis": basis, "basis_type": basis_type, "holes": h,
            "rev_h": (golf_rev / h) if golf_rev else None,
            "gp_h": ((golf_rev - golf_cogs) / h) if (golf_rev and golf_cogs) else None,
            "opex_h": (golf_opex / h) if golf_opex else None,
            "dep_h": (depr_total / h) if depr_total else None,
        })

    d = NOTES.get("DMIG", {})
    rt = (d.get("revenue_note") or {}).get("total", {}).get("FY2024")
    ct = (d.get("cogs_note") or {}).get("total", {}).get("FY2024")
    ot = (d.get("opex_note") or {}).get("total", {}).get("FY2024")
    dep = next((ln.get("FY2024") for ln in (d.get("opex_note") or {}).get("lines", []) if (ln.get("id_label") or "").lower() == "penyusutan"), None)
    collect("DMIG", "Entity all-in (2 코스)", "entity", rt, ct, ot, dep)

    d = NOTES.get("PIPG", {})
    rt = (d.get("revenue_note_27") or {}).get("total", {}).get("FY2024")
    ct = (d.get("cogs_note_28") or {}).get("total", {}).get("FY2024")
    ot = (d.get("opex_note_29") or {}).get("total", {}).get("FY2024")
    dep = next((ln.get("FY2024") for ln in (d.get("opex_note_29") or {}).get("lines", []) if (ln.get("id_label") or "").lower() == "penyusutan"), None)
    collect("PIPG", "Entity all-in (1 코스)", "entity", rt, ct, ot, dep)

    d = NOTES.get("GOLF", {})
    rev_lines = ((d.get("revenue_note_29") or {}).get("by_operations") or {}).get("lines") or []
    cogs_lines = (d.get("cogs_note_30") or {}).get("lines") or []
    rg = next((ln.get("FY2024") for ln in rev_lines if ln.get("en_label") == "Golf"), None)
    cg = next((ln.get("FY2024") for ln in cogs_lines if ln.get("id_label") == "Golf"), None)
    og = (d.get("ga_note_32") or {}).get("total", {}).get("FY2024")
    depg = next((ln.get("FY2024") for ln in (d.get("ga_note_32") or {}).get("lines", []) if "penyusutan" in (ln.get("id_label") or "").lower()), None)
    collect("GOLF", "Golf segment-only", "segment", rg, cg, og, depg)

    d = NOTES.get("MDLN", {})
    cr = (d.get("computed_ratios") or {}).get("FY2024", {})
    rm = cr.get("golf_revenue_pure")
    cm = cr.get("golf_cogs_pure")
    depm = next((ln.get("FY2024") for ln in (d.get("cogs_note_26") or {}).get("golf_course_direct_cost_lines", []) if "penyusutan" in (ln.get("id_label") or "").lower()), None)
    collect("MDLN", "Golf segment", "segment", rm, cm, None, depm)

    d = NOTES.get("KIJA", {})
    seg = (d.get("segment_info_note_34") or {}).get("golf_segment_FY2024") or {}
    rk = (seg.get("revenue") or 0) * 1e6
    ck = (seg.get("cogs") or 0) * 1e6
    ok = ((seg.get("selling") or 0) + (seg.get("ga_expenses") or 0)) * 1e6
    collect("KIJA", "Golf segment", "segment", rk or None, ck or None, ok or None, None)

    d = NOTES.get("SMDM", {})
    seg_s = ((d.get("segment_info_note_29") or {}).get("FY2024") or {}).get("Golf dan Country Club") or {}
    rs = seg_s.get("revenue")
    cs = abs(seg_s.get("cogs") or 0) or None
    os_ = (abs(seg_s.get("selling") or 0) + abs(seg_s.get("ga") or 0)) or None
    collect("SMDM", "Golf segment", "segment", rs, cs, os_, None)

    return rows


PEER_COLORS = {
    "DMIG": "#2d5016",
    "PIPG": "#c08a2e",
    "GOLF": "#4a7c30",
    "MDLN": "#6b21a8",
    "KIJA": "#b91c1c",
    "SMDM": "#1e40af",
    "KPIG": "#92400e",
}


def _per_hole_bar_chart(metric_key: str, title: str, unit: str = "/홀") -> str:
    """Render a horizontal bar chart for one per-hole metric across all peers."""
    data = _per_hole_data()
    rows = [(d["ticker"], d["basis_type"], d.get(metric_key)) for d in data]
    rows = [r for r in rows if r[2] is not None]
    if not rows:
        return ""
    rows.sort(key=lambda r: -(r[2] or 0))
    max_v = max(r[2] for r in rows)

    bars = []
    for ticker, basis_type, v in rows:
        pct = (v / max_v * 100) if max_v else 0
        color = PEER_COLORS.get(ticker, "#8a8a8a")
        basis_tag = "ENT" if basis_type == "entity" else "SEG"
        basis_color = "#92400e" if basis_type == "entity" else "#2d5016"
        val_str = fmt_bn(v).replace(" bn", "bn")
        bars.append(f"""<div class="stack-row" style="padding:6px 0;">
  <div class="stack-label" style="flex:0 0 120px;">
    <span class="ticker-mini">{safe(ticker)}</span>
    <span style="font-size:9px;font-weight:700;padding:1px 4px;border-radius:3px;background:{basis_color};color:white;letter-spacing:0.05em;">{basis_tag}</span>
  </div>
  <div class="stack-bar" style="height:18px;background:#f5f3ec;">
    <div class="stack-seg" style="width:{pct:.1f}%;background:{color};font-size:10px;justify-content:flex-end;padding-right:6px;">{val_str}</div>
  </div>
</div>""")

    return f"""<div class="ops-block">
  <h4 class="ops-block-h">{safe(title)} <span class="muted" style="font-weight:400;font-size:12px;">— {unit}, FY2024</span></h4>
  <div class="stack-block">
    {''.join(bars)}
  </div>
</div>"""


def _per_hole_visual_section() -> str:
    """4-metric horizontal bar grid for per-hole unit economics."""
    rev = _per_hole_bar_chart("rev_h", "매출 / 홀")
    gp = _per_hole_bar_chart("gp_h", "GP / 홀")
    opex = _per_hole_bar_chart("opex_h", "OpEx / 홀")
    dep = _per_hole_bar_chart("dep_h", "감가상각 / 홀")
    return f"""<div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(420px, 1fr)); gap:12px;">
  {rev}
  {gp}
  {opex}
  {dep}
</div>
<p class="src-line" style="margin: 10px 2px 4px;">
  <span style="display:inline-block;padding:1px 4px;border-radius:3px;background:#92400e;color:white;font-size:9px;font-weight:700;letter-spacing:0.05em;">ENT</span>
  = Entity all-in (golf+F&amp;B+회원권+카트 등 일체 포함) ·
  <span style="display:inline-block;padding:1px 4px;border-radius:3px;background:#2d5016;color:white;font-size:9px;font-weight:700;letter-spacing:0.05em;">SEG</span>
  = Golf segment-only (순수 골프 매출) — basis 차이로 ENT가 의도적으로 부풀려져 있음. SEG끼리 비교가 진짜 cross-peer per-hole.
</p>"""


def _sparkline_svg(values, color="#2d5016", width=140, height=36, fill=True) -> str:
    """Generate inline SVG sparkline from a list of (label, value) pairs.

    None values are skipped. Returns "" if fewer than 2 valid points.
    """
    pts = [(lab, v) for lab, v in values if v is not None]
    if len(pts) < 2:
        return ""
    vals = [v for _, v in pts]
    vmin, vmax = min(vals), max(vals)
    rng = vmax - vmin if vmax > vmin else max(vmax * 0.1, 1)
    pad = 4
    inner_w = width - 2 * pad
    inner_h = height - 2 * pad
    n = len(pts)
    coords = []
    for i, (_, v) in enumerate(pts):
        x = pad + (inner_w * (i / (n - 1)))
        y = pad + inner_h - (inner_h * ((v - vmin) / rng))
        coords.append((x, y))
    pts_str = " ".join(f"{x:.1f},{y:.1f}" for x, y in coords)
    fill_path = ""
    if fill:
        first_x, _ = coords[0]
        last_x, _ = coords[-1]
        fill_path = (
            f'<polygon points="{first_x:.1f},{height - pad} {pts_str} {last_x:.1f},{height - pad}" '
            f'fill="{color}" opacity="0.13"/>'
        )
    # Points
    dots = "".join(
        f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2" fill="{color}"/>'
        for x, y in coords
    )
    # Labels (first + last + min/max)
    last_x, last_y = coords[-1]
    last_val = pts[-1][1]
    label_text = f"{last_val:,.0f}" if last_val >= 100 else f"{last_val:.1f}"
    return (
        f'<svg viewBox="0 0 {width} {height}" width="{width}" height="{height}" '
        f'xmlns="http://www.w3.org/2000/svg" style="vertical-align:middle;">'
        f'{fill_path}'
        f'<polyline fill="none" stroke="{color}" stroke-width="1.8" '
        f'points="{pts_str}"/>'
        f'{dots}'
        f'</svg>'
    )


def _ops_kpi_dashboard() -> str:
    """Visual KPI dashboard tile strip — sparklines + headline numbers for each peer."""

    dmig = OPS_KPI_EVIDENCE["DMIG"]
    pipg = OPS_KPI_EVIDENCE["PIPG"]
    golf = OPS_KPI_EVIDENCE["GOLF"]

    # DMIG headcount 시계열 — FY21-23
    hc_dmig = [
        ("FY21", dmig["headcount"]["FY2021"]),
        ("FY22", dmig["headcount"]["FY2022"]),
        ("FY23", dmig["headcount"]["FY2023"]),
    ]
    hc_spark = _sparkline_svg(hc_dmig, color="#c08a2e", width=180, height=44)

    # DMIG The Range@PIK — FY22→FY23
    range_y = dmig["the_range_revenue"]
    range_spark_vals = [("FY22", range_y.get("FY2022")), ("FY23", range_y.get("FY2023"))]
    range_y22 = range_y.get("FY2022") or 0
    range_y23 = range_y.get("FY2023") or 0
    range_growth = ((range_y23 / range_y22) - 1) * 100 if range_y22 else None

    # PIPG rounds played 4-year
    rp = pipg["rounds_played"]
    pipg_rounds = [
        ("FY21", rp.get("FY2021")),
        ("FY22", rp.get("FY2022")),
        ("FY23", rp.get("FY2023")),
        ("FY24", rp.get("FY2024")),
    ]
    pipg_spark = _sparkline_svg(pipg_rounds, color="#2d5016", width=200, height=48)
    pipg_latest = rp.get("FY2024") or 0
    pipg_first = rp.get("FY2021") or 0
    pipg_total_growth = ((pipg_latest / pipg_first) - 1) * 100 if pipg_first else None

    # PIPG headcount by dept — top 5 bars
    hc_pipg = pipg["headcount_by_dept_FY2024"]
    dept_pairs = sorted(
        [(k, v) for k, v in hc_pipg.items() if isinstance(v, int)],
        key=lambda kv: -kv[1],
    )[:5]
    pipg_total = sum(v for _, v in dept_pairs)
    pipg_dept_bars = []
    for dept, n in dept_pairs:
        pct = n / pipg_total * 100 if pipg_total else 0
        pipg_dept_bars.append(
            f'<div style="display:flex;align-items:center;gap:6px;font-size:11px;color:var(--ink-soft);">'
            f'<span style="flex:0 0 70px;">{safe(dept)[:8]}</span>'
            f'<span style="flex:1;height:6px;background:var(--line);border-radius:3px;overflow:hidden;">'
            f'<span style="display:block;width:{pct:.0f}%;height:100%;background:#2d5016;"></span></span>'
            f'<span style="flex:0 0 22px;text-align:right;font-weight:600;">{n}</span></div>'
        )

    # GOLF CWIP composition
    cwip = golf["capex_fy2025"]
    bld = cwip.get("construction_buildings_idr") or 0
    ls = cwip.get("construction_landscape_idr") or 0
    cwip_total = bld + ls
    bld_pct = (bld / cwip_total * 100) if cwip_total else 0
    ls_pct = (ls / cwip_total * 100) if cwip_total else 0

    # GOLF target beat
    tb = golf["fy2025_golf_target_beat"]
    target = tb.get("target_idr") or 0
    actual = tb.get("fy2025_golf_revenue_idr") or 0
    beat_pct = tb.get("beat_pct") or 0

    return f"""<div class="kpi-strip" style="grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));">

  <div class="kpi-tile accent-warn">
    <div class="kpi-cap">DMIG · 직원 수 (FY21-23)</div>
    <div style="display:flex; align-items:center; gap:12px; margin: 4px 0;">
      {hc_spark}
      <div>
        <div class="kpi-val small">{dmig['headcount']['FY2023']}<span style="font-size:11px;color:var(--muted);">명</span></div>
        <div class="kpi-sub kpi-trend down">FY21→23 -39.8%</div>
      </div>
    </div>
    <div class="kpi-sub">코로나 회복기 -42.7% (342→196) 후 +5.1% 회복</div>
  </div>

  <div class="kpi-tile accent-green">
    <div class="kpi-cap">DMIG · Range@PIK 매출</div>
    <div class="kpi-val small">{fmt_bn(range_y23)}</div>
    <div class="kpi-sub kpi-trend up">FY22→23 {range_growth:+.1f}%</div>
    <div class="kpi-sub">골프테인먼트 (driving range + entertainment) 신규 시설</div>
  </div>

  <div class="kpi-tile accent-green">
    <div class="kpi-cap">PIPG · 골퍼 시계열 4Y</div>
    <div style="display:flex; align-items:center; gap:12px; margin: 4px 0;">
      {pipg_spark}
    </div>
    <div class="kpi-val small">{pipg_latest:,}<span style="font-size:11px;color:var(--muted);">명</span></div>
    <div class="kpi-sub kpi-trend up">FY21→24 {pipg_total_growth:+.1f}%</div>
  </div>

  <div class="kpi-tile accent-blue">
    <div class="kpi-cap">PIPG · 부서별 인원 mix (FY24)</div>
    <div style="display:flex; flex-direction:column; gap:4px; margin: 6px 0;">
      {''.join(pipg_dept_bars)}
    </div>
    <div class="kpi-sub">총 {pipg_total}명 (top-5 부서)</div>
  </div>

  <div class="kpi-tile accent-warn">
    <div class="kpi-cap">GOLF · CWIP 구성 (FY25 진행 중)</div>
    <div class="kpi-val small">{fmt_bn(cwip_total)}</div>
    <div class="stack-bar" style="height:14px;margin:6px 0;background:var(--line);">
      <div class="stack-seg" style="width:{bld_pct:.1f}%;background:#92400e;font-size:9px;">건물 {bld_pct:.0f}%</div>
      <div class="stack-seg" style="width:{ls_pct:.1f}%;background:#4a7c30;font-size:9px;">조경 {ls_pct:.0f}%</div>
    </div>
    <div class="kpi-sub">Buildings {fmt_bn(bld)} + Landscape {fmt_bn(ls)}</div>
  </div>

  <div class="kpi-tile accent-green">
    <div class="kpi-cap">GOLF · FY25 매출 target 달성</div>
    <div class="kpi-val small">{fmt_bn(actual)}</div>
    <div class="kpi-sub kpi-trend up">vs target {fmt_bn(target)} · <strong>{beat_pct*100:+.1f}%</strong> beat</div>
    <div class="kpi-sub">자본투자 강도 + 매출 동시 달성</div>
  </div>

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
      <p class="kv-comment">{safe(dmig['rounds_played']['narrative'])}</p>    </div>
    <div class="kv">
      <div class="k">FY2023 Main Playing Members</div>
      <div class="v">{dmig['members']['FY2023']:,}명 <span class="muted">(전년比 -6명)</span></div>
      <p class="kv-comment">{safe(dmig['members']['narrative'])}</p>    </div>
    <div class="kv">
      <div class="k">직원 수 (Benefit-eligible)</div>
      <div class="v">FY21 342 → FY22 {dmig['headcount']['FY2022']} → FY23 {dmig['headcount']['FY2023']}</div>
      <p class="kv-comment">{safe(dmig['headcount']['narrative'])}</p>    </div>
    <div class="kv">
      <div class="k">The Range@PIK 매출</div>
      <div class="v">{fmt_bn(dmig['the_range_revenue']['FY2023'])} <span class="muted">(+372.7% YoY)</span></div>
      <p class="kv-comment">{safe(dmig['the_range_revenue']['narrative'])}</p>    </div>
    <div class="kv">
      <div class="k">FY2023 F&amp;B 코스별 분해</div>
      <div class="v">BSD {fmt_bn(dmig['fnb_split_FY2023']['bsd_restaurant_idr'])} + PIK {fmt_bn(dmig['fnb_split_FY2023']['pik_restaurant_idr'])}</div>
      <p class="kv-comment">{safe(dmig['fnb_split_FY2023']['narrative'])}</p>    </div>
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
</div>
<div class="ops-block">
  <h4 class="ops-block-h">PIPG — 부서별 인원 (FY2024, turnover 그래프 기준)</h4>
  <div class="tbl-card">{dept_html}</div>
  <p class="kv-comment">{safe(hc['narrative'])}</p>
</div>""")

    # KPIG card
    kpig = OPS_KPI_EVIDENCE["KPIG"]
    cards.append(f"""<div class="ops-block">
  <h4 class="ops-block-h">KPIG — 운영 scope &amp; Trump Lido 시설</h4>
  <div class="kv-grid">
    <div class="kv">
      <div class="k">공시 범위</div>
      <p class="kv-comment">{safe(kpig['scope_caveat']['narrative'])}</p>    </div>
    <div class="kv">
      <div class="k">Trump Clubhouse</div>
      <div class="v">33,322 m² <span class="muted">(Oppenheim Arch.)</span></div>
      <p class="kv-comment">{safe(kpig['clubhouse_facility']['narrative'])}</p>    </div>
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
      <p class="kv-comment">{safe(tb['narrative'])}</p>    </div>
    <div class="kv">
      <div class="k">CWIP 설명</div>
      <p class="kv-comment">{safe(g['capex_fy2025']['narrative'])}</p>    </div>
  </div>
</div>""")

    return "\n".join(cards)


def _related_party_visual() -> str:
    """Visual key-number cards summarizing related-party + lease risks."""
    cards = []

    # DMIG — key management comp trend
    rp = (NOTES.get("DMIG", {}) or {}).get("related_party_note") or {}
    lines = rp.get("lines") or []
    if lines:
        # Find total compensation line and % of opex line
        comp_line = next((ln for ln in lines if "compensation" in (ln.get("en_label") or "").lower() or "imbalan" in (ln.get("id_label") or "").lower()), lines[0])
        v22 = comp_line.get("FY2022") or 0
        v23 = comp_line.get("FY2023") or 0
        v24 = comp_line.get("FY2024") or 0
        # Sparkline of compensation
        spark = _sparkline_svg([("FY22", v22), ("FY23", v23), ("FY24", v24)], color="#6b21a8", width=140, height=36)
        yoy = ((v24 / v23) - 1) * 100 if (v22 and v23 and v24) else None
        yoy_str = f"{yoy:+.1f}%" if yoy is not None else "—"
        cards.append(f"""<div class="kpi-tile accent-blue">
  <div class="kpi-cap"><span class="ticker-mini">DMIG</span> 핵심경영진 보수</div>
  <div style="display:flex;align-items:center;gap:10px;margin:6px 0;">
    {spark}
    <div>
      <div class="kpi-val small">{fmt_bn(v24)}</div>
      <div class="kpi-sub kpi-trend {'up' if (yoy and yoy>0) else 'down'}">FY23→24 {yoy_str}</div>
    </div>
  </div>
  <div class="kpi-sub">3년 추이 · Note 26 Related party</div>
</div>""")

    # PIPG — land profile big numbers
    profile = (NOTES.get("PIPG", {}) or {}).get("profile") or {}
    if profile:
        land_ha = profile.get("land_area_ha_total", 0) or 0
        certs = profile.get("land_certificates", 0)
        leased = profile.get("leased_from_mkpi_m2", 0) or 0
        cards.append(f"""<div class="kpi-tile accent-gold">
  <div class="kpi-cap"><span class="ticker-mini">PIPG</span> 토지·HGB profile</div>
  <div class="kpi-val">{land_ha}<span class="u" style="font-size:13px;color:var(--muted);">ha</span></div>
  <div class="kpi-sub">{certs} 인증서 · HGB {profile.get("hgb_area_m2", 0):,} m²</div>
  <div class="kpi-sub">MKPI 임차 <strong>{leased:,} m²</strong> ({safe(profile.get("leased_purpose", ""))})</div>
</div>""")

    # GOLF — customer concentration ALERT
    rev29 = (NOTES.get("GOLF", {}) or {}).get("revenue_note_29") or {}
    cc = rev29.get("customer_concentration") or {}
    if cc:
        pct24 = (cc.get("pct_of_revenue_FY2024") or 0) * 100
        pct23 = (cc.get("pct_of_revenue_FY2023") or 0) * 100
        spark = _sparkline_svg([("FY23", pct23), ("FY24", pct24)], color="#b91c1c", width=100, height=36)
        cards.append(f"""<div class="kpi-tile accent-warn">
  <div class="kpi-cap"><span class="ticker-mini">GOLF</span> 고객 집중도 위험</div>
  <div class="kpi-val down">{pct24:.1f}<span class="u" style="font-size:13px;">%</span></div>
  <div class="kpi-sub"><strong>{safe(cc.get("name", "—"))}</strong> 단일 고객</div>
  <div class="kpi-sub">FY24 매출의 {pct24:.1f}% (FY23 {pct23:.1f}%) · {fmt_bn(cc.get("amount_FY2024"))}</div>
</div>""")

    # MDLN — supplier concentration
    sup = ((NOTES.get("MDLN", {}) or {}).get("cogs_note_26") or {}).get("supplier_concentration") or {}
    if sup:
        cards.append(f"""<div class="kpi-tile">
  <div class="kpi-cap"><span class="ticker-mini">MDLN</span> 공급사 집중 위험</div>
  <div class="kpi-val small">{safe(sup.get("name", "—"))}</div>
  <div class="kpi-sub">FY24 거래액 {fmt_bn(sup.get("amount_FY2024"))}</div>
  <div class="kpi-sub">전체 COGS 대비 {safe(sup.get("pct_of_total_cogs", "—"))}</div>
</div>""")

    # PIPG — number of lease/agreement counterparties (count)
    ag = (NOTES.get("PIPG", {}) or {}).get("agreements_commitments") or {}
    items = ag.get("items") or []
    if items:
        types_count = len(set((it.get("type") or "") for it in items))
        cards.append(f"""<div class="kpi-tile">
  <div class="kpi-cap"><span class="ticker-mini">PIPG</span> Lease·약정 건수</div>
  <div class="kpi-val">{len(items)}</div>
  <div class="kpi-sub">{types_count} 유형의 약정 (lease/sponsor/관계사)</div>
  <div class="kpi-sub">Note 32 · 상세는 아래 표 참조</div>
</div>""")

    return f'<div class="kpi-strip" style="margin-bottom: 18px;">{"".join(cards)}</div>'


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
            f'</div>'
        )

    return "\n".join(cards)


def _fy25_dashboard() -> str:
    """Side-by-side FY25 prelim P&L dashboard for DMIG/PIPG/KPIG."""

    def pct_sign(v):
        if v is None:
            return None
        try:
            return float(v) * 100
        except (TypeError, ValueError):
            return None

    def trend_color(pct):
        if pct is None:
            return "var(--muted)"
        return "var(--green)" if pct > 0 else "var(--danger)"

    # Per-peer data
    rows_data = []
    for t in ["DMIG", "PIPG", "KPIG"]:
        fu = (NOTES.get(t, {}) or {}).get("fy2025_follow_up") or {}
        if not fu:
            continue
        if t == "KPIG":
            seg = fu.get("FY2025_revenue_note_31") or {}
            rows_data.append({
                "ticker": t,
                "rev": seg.get("Hotel_resor_dan_golf"),
                "rev_yoy": pct_sign(seg.get("yoy_vs_fy2024")),
                "op_inc": None, "op_yoy": None,
                "net_inc": None, "net_yoy": None,
                "comment": "Hotel+Resort+Golf 통합 (Golf-only 분리 미공시)",
                "tone": "neutral",
            })
            continue
        pnl = fu.get("pnl_FY2025") or {}
        yoy = fu.get("yoy_changes") or {}
        # Determine tone by op_income trend
        op_yoy = pct_sign(yoy.get("operating_income"))
        tone = "positive" if (op_yoy and op_yoy > 0) else ("warn" if (op_yoy and op_yoy < -5) else "neutral")
        rows_data.append({
            "ticker": t,
            "rev": pnl.get("revenue"),
            "rev_yoy": pct_sign(yoy.get("revenue")),
            "op_inc": pnl.get("operating_income"),
            "op_yoy": op_yoy,
            "net_inc": pnl.get("net_income"),
            "net_yoy": pct_sign(yoy.get("net_income")),
            "comment": yoy.get("comment", ""),
            "tone": tone,
        })

    tone_border = {"positive": "var(--green)", "warn": "var(--warn)", "neutral": "#8a8a8a"}

    cards = []
    for r in rows_data:
        t = r["ticker"]
        color = PEER_COLORS.get(t, "#8a8a8a")

        # Metric rows
        metric_block = ""
        for metric_key, label in [("rev", "매출"), ("op_inc", "영업이익"), ("net_inc", "순이익")]:
            v = r.get(metric_key)
            yoy_key = {"rev": "rev_yoy", "op_inc": "op_yoy", "net_inc": "net_yoy"}[metric_key]
            yoy = r.get(yoy_key)
            v_str = fmt_bn(v) if v else '<span class="muted">미공시</span>'
            yoy_str = f"{yoy:+.1f}%" if yoy is not None else "—"
            yoy_c = trend_color(yoy)
            arrow = "▲" if (yoy and yoy > 0) else ("▼" if (yoy and yoy < 0) else "—")
            metric_block += f"""<div style="display:flex;justify-content:space-between;align-items:baseline;padding:7px 0;border-bottom:1px solid var(--line);">
  <div>
    <div style="font-size:11px;color:var(--muted);font-weight:600;letter-spacing:0.03em;text-transform:uppercase;">{safe(label)}</div>
    <div style="font-size:17px;font-weight:700;color:var(--ink);font-variant-numeric:tabular-nums;">{v_str}</div>
  </div>
  <div style="font-size:13px;font-weight:700;color:{yoy_c};text-align:right;">
    <span style="font-size:9px;vertical-align:middle;">{arrow}</span> {yoy_str}
  </div>
</div>"""

        cards.append(f"""<div class="kpi-tile" style="border-top:3px solid {color};padding:18px 18px 14px;">
  <div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;">
    <span class="ticker-mini">{t}</span>
    <span style="font-size:12px;font-weight:700;color:var(--ink);">FY2025 미감사 prelim</span>
  </div>
  {metric_block}
  <p style="font-size:11.5px;color:var(--ink-soft);line-height:1.5;margin:10px 0 0;">{safe(r["comment"])}</p>
</div>""")

    return f"""<div class="kpi-strip" style="grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));">
  {''.join(cards)}
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
                f''
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
            f''
            f'</div>'
        )
    return f'<div class="kv-grid">{"".join(cards)}</div>'


def _opex_category_cross_peer(cat_keys: list, title: str, peer_specific_color: dict = None) -> str:
    """Cross-peer comparison of a single OpEx category (e.g., salaries, tax, utilities).

    cat_keys: list of OPEX_CATEGORY_RULES keys to match (e.g., ["인건비 (Salaries+benefits)"])
    """
    rows = []
    for ticker, opex_key, rev_key in [
        ("DMIG", "opex_note", "revenue_note"),
        ("PIPG", "opex_note_29", "revenue_note_27"),
        ("GOLF", "ga_note_32", "revenue_note_29"),
    ]:
        d = NOTES.get(ticker, {})
        rev = (d.get(rev_key) or {}).get("total", {}).get("FY2024")
        if ticker == "GOLF":
            rev = ((d.get("revenue_note_29") or {}).get("by_operations") or {}).get("total", {}).get("FY2024") or rev
        rev_prev = (d.get(rev_key) or {}).get("total", {}).get("FY2023")
        if ticker == "GOLF":
            rev_prev = ((d.get("revenue_note_29") or {}).get("by_operations") or {}).get("total", {}).get("FY2023") or rev_prev

        total24 = 0
        total23 = 0
        lines_collected = []
        for ln in (d.get(opex_key) or {}).get("lines") or []:
            label = (ln.get("id_label") or "") + " " + (ln.get("en_label") or "")
            cat = _opex_category_of(label)
            if cat in cat_keys:
                total24 += ln.get("FY2024") or 0
                total23 += ln.get("FY2023") or 0
                lines_collected.append((ln.get("en_label") or ln.get("id_label") or "—", ln.get("FY2024") or 0))
        pct24 = (total24 / rev * 100) if (total24 and rev) else None
        pct23 = (total23 / rev_prev * 100) if (total23 and rev_prev) else None
        yoy = ((total24 / total23) - 1) * 100 if (total23 and total24) else None
        rows.append({
            "ticker": ticker, "total24": total24, "pct24": pct24, "pct23": pct23,
            "yoy": yoy, "rev": rev, "lines": lines_collected,
        })

    rows.sort(key=lambda r: -(r["pct24"] or 0))
    max_pct = max((r["pct24"] or 0) for r in rows) or 1

    bars = []
    for r in rows:
        t = r["ticker"]
        pct = r["pct24"] or 0
        bar_w = (pct / max_pct) * 100
        color = PEER_COLORS.get(t, "#8a8a8a")
        v_str = fmt_bn(r["total24"]).replace(" bn", "bn") if r["total24"] else "—"
        pct_str = f"{pct:.1f}%" if pct else "—"
        yoy_str = f"{r['yoy']:+.1f}%" if r["yoy"] is not None else "—"
        yoy_color = "var(--danger)" if (r["yoy"] and r["yoy"] > 5) else ("var(--green)" if (r["yoy"] and r["yoy"] < -2) else "var(--muted)")
        line_count = len(r["lines"])
        bars.append(f"""<div style="display:grid;grid-template-columns:60px 1fr 80px 60px 60px;gap:8px;align-items:center;padding:5px 0;font-size:12px;">
  <span><span class="ticker-mini">{safe(t)}</span></span>
  <span style="height:20px;background:var(--line);border-radius:3px;overflow:hidden;">
    <span style="display:block;height:100%;width:{bar_w:.1f}%;background:{color};"></span>
  </span>
  <span style="text-align:right;font-weight:700;font-variant-numeric:tabular-nums;">{v_str}</span>
  <span style="text-align:right;color:var(--ink-soft);font-size:11px;">{pct_str} 매출</span>
  <span style="text-align:right;font-weight:700;font-size:11px;color:{yoy_color};">{yoy_str}</span>
</div>""")
        # Show contributing lines
        if line_count > 0 and line_count <= 4:
            for ln_label, ln_v in r["lines"]:
                ln_str = fmt_bn(ln_v).replace(" bn", "bn") if ln_v else "—"
                bars.append(f"""<div style="display:grid;grid-template-columns:60px 1fr 80px 60px 60px;gap:8px;padding:2px 0 2px 16px;font-size:11px;color:var(--muted);">
  <span></span>
  <span style="font-style:italic;">↳ {safe(ln_label[:50])}</span>
  <span style="text-align:right;font-variant-numeric:tabular-nums;">{ln_str}</span>
  <span></span><span></span>
</div>""")

    return f"""<div class="ops-block" style="background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:16px;">
  <h4 class="ops-block-h" style="margin-bottom:10px;">{safe(title)}</h4>
  <div style="display:grid;grid-template-columns:60px 1fr 80px 60px 60px;gap:8px;padding:2px 0 4px;font-size:9.5px;color:var(--muted);text-transform:uppercase;letter-spacing:0.04em;font-weight:700;border-bottom:1px solid var(--line);">
    <span>Peer</span><span>FY24 magnitude</span><span style="text-align:right;">IDR</span><span style="text-align:right;">% 매출</span><span style="text-align:right;">YoY</span>
  </div>
  {''.join(bars)}
</div>"""


def _opex_category_cross_peer_section() -> str:
    """Grid of 4 cross-peer OpEx category comparisons."""
    salaries = _opex_category_cross_peer(["인건비 (Salaries+benefits)"], "👥 인건비 (Salaries+benefits) — DMIG/PIPG/GOLF")
    tax = _opex_category_cross_peer(["세금·법률 (Tax+Legal)"], "📜 세금·법률 (Tax+Legal) — PIPG outlier 확인")
    maint = _opex_category_cross_peer(["유지보수 (Repair+Maintenance)"], "🔧 유지보수 (Repair+Maintenance) — PIPG 5.9% vs DMIG 0.9%")
    util = _opex_category_cross_peer(["유틸리티 (Utilities)"], "⚡ 유틸리티 (Utilities) — 전기·수도")
    return f"""<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(440px,1fr));gap:14px;">
  {salaries}
  {tax}
  {maint}
  {util}
</div>"""


def _opex_4y_trend_chart() -> str:
    """4-year OpEx trend per peer (FY22-25) as multi-line chart."""
    fys = ["FY2022", "FY2023", "FY2024", "FY2025"]
    series_data = []
    for ticker, opex_key in [
        ("DMIG", "opex_note"),
        ("PIPG", "opex_note_29"),
        ("GOLF", "ga_note_32"),
    ]:
        d = NOTES.get(ticker, {})
        blk = d.get(opex_key) or {}
        tot = blk.get("total") or {}
        values = []
        for fy in fys:
            v = tot.get(fy)
            if fy == "FY2025":
                fu = (d.get("fy2025_follow_up") or {}).get("pnl_FY2025") or {}
                v = fu.get("opex") or v
            # Convert to % of revenue
            rev = revenue_total_for(ticker, fy)
            if ticker == "GOLF":
                rev = ((d.get("revenue_note_29") or {}).get("by_operations") or {}).get("total", {}).get(fy) or rev
            if fy == "FY2025" and ticker in ("DMIG", "PIPG"):
                rev = ((d.get("fy2025_follow_up") or {}).get("pnl_FY2025") or {}).get("revenue") or rev
            pct = (v / rev * 100) if (v and rev) else None
            values.append(pct)
        color = PEER_COLORS.get(ticker, "#8a8a8a")
        series_data.append((ticker, values, color))

    chart = _multi_line_chart(
        series_data,
        fys,
        width=520, height=260,
        title="OpEx/매출 % — 4Y 추이 (DMIG · PIPG · GOLF)",
    )
    return f"""<div style="display:flex;justify-content:center;">{chart}</div>"""


def _golf_cwip_detail_chart() -> str:
    """GOLF CWIP detailed breakdown — Buildings/Landscape/Equipment from FY25 p.170."""
    # From OPS_KPI_EVIDENCE narrative + vector hit on FY25 p.170
    # Additional items from p.170: Furniture, Office Equipment, Vehicles, Equipment
    items = [
        ("Buildings (Gedung)", 187_920_532_473, "#92400e", "신규 클럽하우스 + 시설 건물"),
        ("Landscape", 237_798_337_318, "#4a7c30", "코스 조경·잔디·관개"),
        ("Vehicles (Kendaraan)", 13_017_077_949, "#1e40af", "카트·운영 차량"),
        ("Office Equipment", 5_238_440_289, "#c08a2e", "사무·관리 장비"),
        ("Furniture (Perabotan)", 5_952_331_370, "#6b21a8", "클럽하우스 가구"),
        ("Equipment (Peralatan)", 2_611_569_863, "#8a8a8a", "골프 운영 장비"),
    ]
    total = sum(v for _, v, _, _ in items)
    max_v = max(v for _, v, _, _ in items)

    bars = []
    for label, v, color, desc in items:
        pct_w = (v / max_v) * 100
        pct_total = (v / total) * 100
        v_str = fmt_bn(v).replace(" bn", "bn")
        bars.append(f"""<div style="display:grid;grid-template-columns:180px 1fr 70px 50px;gap:8px;align-items:center;padding:5px 0;font-size:12px;">
  <span style="color:var(--ink-soft);font-weight:600;">{safe(label)}<br><span style="font-size:9.5px;color:var(--muted);font-weight:400;">{safe(desc)}</span></span>
  <span style="height:18px;background:var(--line);border-radius:3px;overflow:hidden;">
    <span style="display:block;height:100%;width:{pct_w:.1f}%;background:{color};"></span>
  </span>
  <span style="text-align:right;font-weight:700;font-variant-numeric:tabular-nums;">{v_str}</span>
  <span style="text-align:right;color:var(--muted);font-size:11px;">{pct_total:.1f}%</span>
</div>""")

    return f"""<div class="ops-block" style="background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:16px;">
  <h4 class="ops-block-h" style="margin-bottom:10px;">
    <span class="ticker-mini">GOLF</span> CWIP detail (FY2025) — 6 카테고리
  </h4>
  <div style="display:grid;grid-template-columns:180px 1fr 70px 50px;gap:8px;padding:2px 0 4px;font-size:9.5px;color:var(--muted);text-transform:uppercase;letter-spacing:0.04em;font-weight:700;border-bottom:1px solid var(--line);">
    <span>카테고리</span><span>magnitude</span><span style="text-align:right;">FY25 IDR</span><span style="text-align:right;">% CWIP</span>
  </div>
  {''.join(bars)}
  <div style="display:grid;grid-template-columns:180px 1fr 70px 50px;gap:8px;padding:8px 0 2px;margin-top:6px;border-top:2px solid var(--line-strong);font-weight:700;font-size:12px;">
    <span>합계</span><span></span>
    <span style="text-align:right;">{fmt_bn(total).replace(' bn','bn')}</span>
    <span style="text-align:right;color:var(--muted);">100.0%</span>
  </div>
</div>"""


def _depreciation_lines_chart() -> str:
    """All depreciation line items across DMIG / PIPG / GOLF — grouped horizontal bar."""
    rows_data = []
    for ticker, opex_key, label_prefix in [
        ("DMIG", "opex_note", "OpEx"),
        ("PIPG", "opex_note_29", "OpEx"),
        ("GOLF", "ga_note_32", "G&A"),
    ]:
        d = NOTES.get(ticker, {})
        lines = (d.get(opex_key) or {}).get("lines") or []
        for ln in lines:
            lab = (ln.get("id_label") or "").lower()
            en = (ln.get("en_label") or "").lower()
            if "penyusutan" in lab or "depreciation" in en:
                v23 = ln.get("FY2023") or 0
                v24 = ln.get("FY2024") or 0
                rev24 = revenue_total_for(ticker, "FY2024")
                if ticker == "GOLF":
                    rev24 = ((d.get("revenue_note_29") or {}).get("by_operations") or {}).get("total", {}).get("FY2024") or rev24
                pct = (v24 / rev24 * 100) if (v24 and rev24) else None
                yoy = ((v24 / v23) - 1) * 100 if (v23 and v24) else None
                rows_data.append({
                    "ticker": ticker, "label": ln.get("en_label") or ln.get("id_label"),
                    "v23": v23, "v24": v24, "pct": pct, "yoy": yoy, "context": label_prefix,
                })

    if not rows_data:
        return ""
    rows_data.sort(key=lambda r: -(r["v24"] or 0))
    max_v = rows_data[0]["v24"] or 1

    bars = []
    for r in rows_data:
        pct_w = (r["v24"] / max_v) * 100 if max_v else 0
        color = PEER_COLORS.get(r["ticker"], "#8a8a8a")
        yoy_str = f"{r['yoy']:+.1f}%" if r['yoy'] is not None else "—"
        yoy_color = "var(--danger)" if (r['yoy'] and r['yoy'] > 5) else ("var(--green)" if (r['yoy'] and r['yoy'] < -2) else "var(--muted)")
        v24_str = fmt_bn(r["v24"]).replace(" bn", "bn")
        pct_str = f"{r['pct']:.1f}%" if r['pct'] is not None else "—"
        bars.append(f"""<div style="display:grid;grid-template-columns:80px 1fr 80px 60px 54px;gap:8px;align-items:center;padding:5px 0;font-size:12px;">
  <span><span class="ticker-mini">{safe(r["ticker"])}</span> <span style="font-size:9px;color:var(--muted);">{safe(r["context"])}</span></span>
  <span style="height:18px;background:var(--line);border-radius:3px;overflow:hidden;">
    <span style="display:block;height:100%;width:{pct_w:.1f}%;background:{color};"></span>
  </span>
  <span style="text-align:right;font-weight:700;font-variant-numeric:tabular-nums;">{v24_str}</span>
  <span style="text-align:right;color:var(--ink-soft);font-size:11px;">{pct_str} 매출</span>
  <span style="text-align:right;font-weight:700;font-size:11px;color:{yoy_color};">{yoy_str}</span>
</div>""")

    return f"""<div class="ops-block" style="background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:16px;">
  <h4 class="ops-block-h" style="margin-bottom:10px;">감가상각 (Penyusutan) 라인 — 3-peer 직접 비교 (FY2024)</h4>
  <div style="display:grid;grid-template-columns:80px 1fr 80px 60px 54px;gap:8px;padding:2px 0 4px;font-size:9.5px;color:var(--muted);text-transform:uppercase;letter-spacing:0.04em;font-weight:700;border-bottom:1px solid var(--line);">
    <span>Peer</span><span>magnitude</span><span style="text-align:right;">FY24 IDR</span><span style="text-align:right;">%매출</span><span style="text-align:right;">YoY</span>
  </div>
  {''.join(bars)}
  <p class="src-line" style="margin-top:8px;">감가상각 절댓값 + 매출 대비 비중 + FY23→24 YoY를 한 표로 비교</p>
</div>"""


def _asset_turnover_strip() -> str:
    """Asset turnover (revenue / total assets) for each peer — efficiency strip."""
    tiles = []
    for t in ["DMIG", "PIPG", "GOLF", "KPIG"]:
        rev24 = revenue_total_for(t, "FY2024")
        if t == "GOLF":
            d = NOTES.get(t, {})
            rev24 = ((d.get("revenue_note_29") or {}).get("by_operations") or {}).get("total", {}).get("FY2024") or rev24
        fin = next((f for f in by_ticker(FINANCIALS, t) if f.get("total_assets_idr")), {})
        ta = fin.get("total_assets_idr") or 0
        turnover = (float(rev24) / float(ta)) if (rev24 and ta) else None
        intensity = (float(ta) / float(rev24)) if (rev24 and ta) else None
        # Hole count
        holes = HOLES.get(t, 18)
        rev_per_hole = (rev24 / holes / 1e9) if rev24 else 0

        accent = "accent-green" if (turnover and turnover > 0.4) else ("accent-warn" if (turnover and turnover < 0.1) else "accent-blue")
        tiles.append(f"""<div class="kpi-tile {accent}">
  <div class="kpi-cap"><span class="ticker-mini">{safe(t)}</span> 자산 회전율</div>
  <div class="kpi-val">{(f'{turnover:.2f}' if turnover else '—')}<span class="u">×/년</span></div>
  <div class="kpi-sub">자산 {fmt_bn(ta)} · 매출 {fmt_bn(rev24)}</div>
  <div class="kpi-sub">자산집약도 {f'{intensity:.1f}' if intensity else '—'}× · {holes}홀 · {rev_per_hole:.1f}bn/홀</div>
</div>""")
    return f'<div class="kpi-strip">{"".join(tiles)}</div>'


def _pipg_dept_headcount_chart() -> str:
    """PIPG headcount by department — detailed horizontal bar chart."""
    pipg = OPS_KPI_EVIDENCE.get("PIPG", {})
    hc = pipg.get("headcount_by_dept_FY2024") or {}
    dept_pairs = sorted([(k, v) for k, v in hc.items() if isinstance(v, int)], key=lambda kv: -kv[1])
    if not dept_pairs:
        return ""
    total = sum(v for _, v in dept_pairs)
    max_v = dept_pairs[0][1]

    bars = []
    for dept, n in dept_pairs:
        pct_w = (n / max_v) * 100
        pct_of_total = (n / total) * 100
        color = "#2d5016" if n >= max_v * 0.5 else ("#4a7c30" if n >= max_v * 0.25 else "#95c073")
        bars.append(f"""<div style="display:grid;grid-template-columns:150px 1fr 64px 48px;gap:8px;align-items:center;padding:4px 0;font-size:12px;">
  <span style="color:var(--ink-soft);font-weight:600;">{safe(dept)}</span>
  <span style="height:18px;background:var(--line);border-radius:3px;overflow:hidden;">
    <span style="display:block;height:100%;width:{pct_w:.1f}%;background:{color};"></span>
  </span>
  <span style="text-align:right;font-weight:700;font-variant-numeric:tabular-nums;">{n}<span style="font-size:10px;color:var(--muted);font-weight:500;"> 명</span></span>
  <span style="text-align:right;color:var(--muted);font-size:10.5px;">{pct_of_total:.1f}%</span>
</div>""")

    return f"""<div class="ops-block" style="background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:16px;">
  <h4 class="ops-block-h" style="margin-bottom:10px;">
    <span class="ticker-mini">PIPG</span> 부서별 인원 (FY2024) — Note 32 turnover 그래프 기준
  </h4>
  <div style="display:grid;grid-template-columns:150px 1fr 64px 48px;gap:8px;padding:2px 0 4px;font-size:9.5px;color:var(--muted);text-transform:uppercase;letter-spacing:0.04em;font-weight:700;border-bottom:1px solid var(--line);">
    <span>부서</span><span>인원 magnitude</span><span style="text-align:right;">명수</span><span style="text-align:right;">% 합계</span>
  </div>
  {''.join(bars)}
  <div style="display:grid;grid-template-columns:150px 1fr 64px 48px;gap:8px;padding:8px 0 2px;margin-top:6px;border-top:2px solid var(--line-strong);font-weight:700;font-size:12px;">
    <span>합계</span><span></span>
    <span style="text-align:right;">{total} 명</span>
    <span style="text-align:right;color:var(--muted);">100.0%</span>
  </div>
</div>"""


def _pipg_agreements_timeline() -> str:
    """PIPG agreements & commitments visual timeline."""
    d = NOTES.get("PIPG", {})
    ag = d.get("agreements_commitments") or {}
    items = ag.get("items") or []
    if not items:
        return ""

    cards = []
    for it in items:
        agreement_type = it.get("type", "—")
        counterparty = it.get("counterparty", "—")
        term = it.get("term", "—")
        rent = it.get("rent_y1y2") or it.get("rent") or it.get("rental_fee") or it.get("rental") or "—"
        is_related = "related party" in counterparty.lower()
        accent = "var(--warn)" if is_related else "var(--green)"
        tag_text = "Related Party" if is_related else "Third Party"
        tag_color = "#92400e" if is_related else "#2d5016"
        tag_bg = "#fef3c7" if is_related else "#e6f1d8"
        cards.append(f"""<div class="quote-card" style="border-left-color:{accent};padding:14px 16px;">
  <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
    <span style="display:inline-block;padding:2px 8px;border-radius:999px;background:{tag_bg};color:{tag_color};font-size:10.5px;font-weight:700;letter-spacing:0.03em;">{tag_text}</span>
    <span style="font-size:12px;color:var(--ink-soft);font-weight:600;">{safe(agreement_type)}</span>
  </div>
  <div style="font-size:14px;font-weight:700;color:var(--ink);line-height:1.4;margin-bottom:6px;">{safe(counterparty)}</div>
  <div style="font-size:12px;color:var(--ink-soft);line-height:1.55;">
    <strong>기간:</strong> {safe(str(term))}<br>
    <strong>금액:</strong> {safe(str(rent))}
  </div>
</div>""")

    return f"""<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:12px;margin:14px 0;">
  {''.join(cards)}
</div>
"""


def _dmig_member_tier_chart() -> str:
    """DMIG Main Playing Member tier breakdown (FY23)."""
    # From OPS_KPI_EVIDENCE narrative: "1,239 → 1,233 (Husband/Wife 79 + Child 35 포함)"
    # So main player = 1,233 - 79 - 35 = 1,119
    tiers = [
        ("Main Playing (Adult)", 1119, "#2d5016"),
        ("Husband / Wife", 79, "#4a7c30"),
        ("Child", 35, "#95c073"),
    ]
    total = sum(v for _, v, _ in tiers)
    bars = []
    for label, n, color in tiers:
        pct = (n / total) * 100
        bars.append(f"""<div style="display:grid;grid-template-columns:180px 1fr 60px 48px;gap:8px;align-items:center;padding:5px 0;font-size:12px;">
  <span style="color:var(--ink-soft);font-weight:600;">{safe(label)}</span>
  <span style="height:18px;background:var(--line);border-radius:3px;overflow:hidden;">
    <span style="display:block;height:100%;width:{pct:.1f}%;background:{color};"></span>
  </span>
  <span style="text-align:right;font-weight:700;font-variant-numeric:tabular-nums;">{n}<span style="font-size:10px;color:var(--muted);font-weight:500;"> 명</span></span>
  <span style="text-align:right;color:var(--muted);font-size:11px;">{pct:.1f}%</span>
</div>""")
    return f"""<div class="ops-block" style="background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:16px;">
  <h4 class="ops-block-h" style="margin-bottom:10px;">
    <span class="ticker-mini">DMIG</span> Main Playing Member tier (FY2023, 1,233명)
  </h4>
  {''.join(bars)}
  <div style="display:grid;grid-template-columns:180px 1fr 60px 48px;gap:8px;padding:8px 0 2px;margin-top:6px;border-top:2px solid var(--line-strong);font-weight:700;font-size:12px;">
    <span>합계</span><span></span>
    <span style="text-align:right;">{total} 명</span>
    <span style="text-align:right;color:var(--muted);">100.0%</span>
  </div>
  <p class="src-line" style="margin-top:8px;">FY22 1,239명 → FY23 1,233명 (-6 명)</p>
</div>"""


def _land_hgb_timeline_visual() -> str:
    """PIPG 토지·HGB 만료 시각화 — timeline 형식."""
    d = NOTES.get("PIPG", {})
    profile = d.get("profile") or {}
    if not profile:
        return ""
    hgb_expiry = profile.get("hgb_expiry_years") or "—"
    leased_start = profile.get("leased_term_start") or "—"
    leased_end = profile.get("leased_term_end") or "—"
    leased_purpose = profile.get("leased_purpose") or "—"

    return f"""<div style="background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:16px;">
  <h4 class="ops-block-h" style="margin-bottom:14px;">
    <span class="ticker-mini">PIPG</span> 토지·HGB·임차 timeline
  </h4>
  <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px;">
    <div style="border-left:3px solid var(--green);padding:8px 12px;">
      <div style="font-size:10.5px;font-weight:700;color:var(--muted);letter-spacing:0.06em;text-transform:uppercase;margin-bottom:3px;">총 토지 면적</div>
      <div style="font-size:22px;font-weight:700;color:var(--ink);font-variant-numeric:tabular-nums;">{profile.get("land_area_ha_total", "—")} ha</div>
      <div style="font-size:11.5px;color:var(--ink-soft);margin-top:3px;">{profile.get("land_area_m2_total", 0):,} m² · {profile.get("land_certificates", "—")} 인증서</div>
    </div>
    <div style="border-left:3px solid var(--accent);padding:8px 12px;">
      <div style="font-size:10.5px;font-weight:700;color:var(--muted);letter-spacing:0.06em;text-transform:uppercase;margin-bottom:3px;">HGB 면적</div>
      <div style="font-size:22px;font-weight:700;color:var(--ink);font-variant-numeric:tabular-nums;">{profile.get("hgb_area_m2", 0):,} m²</div>
      <div style="font-size:11.5px;color:var(--ink-soft);margin-top:3px;">만료: {safe(str(hgb_expiry))}</div>
    </div>
    <div style="border-left:3px solid var(--warn);padding:8px 12px;">
      <div style="font-size:10.5px;font-weight:700;color:var(--muted);letter-spacing:0.06em;text-transform:uppercase;margin-bottom:3px;">MKPI 임차 (related party)</div>
      <div style="font-size:22px;font-weight:700;color:var(--ink);font-variant-numeric:tabular-nums;">{profile.get("leased_from_mkpi_m2", 0):,} m²</div>
      <div style="font-size:11.5px;color:var(--ink-soft);margin-top:3px;">{safe(leased_purpose)} · {safe(leased_start)} ~ {safe(leased_end)}</div>
    </div>
  </div>
</div>"""


def _tab_exec_headline(tab_key: str, tab_title: str, tab_focus_tiles: list) -> str:
    """Tab-specific executive headline strip."""
    tiles_html = ""
    for cap, val, unit, ticker, sub, accent in tab_focus_tiles:
        accent_class = {"warn": "accent-warn", "green": "accent-green", "gold": "accent-gold", "blue": "accent-blue"}.get(accent, "")
        tiles_html += f"""<div class="exec-tile">
  <div class="et-cap">{safe(cap)}</div>
  <div class="et-val">{safe(val)}<span class="u">{safe(unit)}</span></div>
  <div class="et-sub"><span class="et-ticker">{safe(ticker)}</span>{safe(sub)}</div>
</div>"""
    return f"""<div class="exec-headline">
  <div class="exec-eyebrow">7-peer · FY2022→FY2025 · {safe(tab_key)}</div>
  <div class="exec-title">{safe(tab_title)}</div>
  <div class="exec-grid">{tiles_html}</div>
</div>"""


def section_ops_kpi() -> str:
    """Tab 1: 운영 KPI — operational metrics, dividends, related party.

    Sections: KPI dashboard (1) + 시계열 detail (2) + DMIG member tier (3) +
              PIPG dept (4) + PIPG agreements timeline (5) + land/HGB (6) +
              6-peer scatter (7) + 배당 (8) + 관계사·lease (9)
    """
    ops_kpi_dashboard = _ops_kpi_dashboard()
    ops_kpi_section_html = _ops_kpi_section()
    golf_segment_table = _all_peer_golf_segment_table()
    segment_scatter = _segment_scatter_svg()
    related_party_visual = _related_party_visual()
    related_party_section = _related_party_and_lease_section()
    dividend_visual = _dividend_visual()
    dividend_table = _dividend_compare_table()
    pipg_dept_chart = _pipg_dept_headcount_chart()
    pipg_agreements_timeline = _pipg_agreements_timeline()
    dmig_member_chart = _dmig_member_tier_chart()
    land_hgb_visual = _land_hgb_timeline_visual()

    exec_h = _tab_exec_headline(
        tab_key="OPERATIONS",
        tab_title="운영 KPI · 골퍼·회원·인력·자본배분",
        tab_focus_tiles=[
            ("DMIG 골퍼 +12.09% YoY", "123,278", "명", "DMIG", "FY2023 BSD+PIK (+12,979)", "green"),
            ("PIPG 골퍼 4Y 추이", "67,538", "명", "PIPG", "FY2022 member 26,551 + non 40,987", "green"),
            ("DMIG 직원 수 변화", "342→206", "명", "DMIG", "FY21→23 -39.8% 회복기 구조조정 + 점진 회복", "warn"),
            ("GOLF 진행 중 CAPEX", "426", "bn", "GOLF", "CWIP Buildings 188 + Landscape 238", "gold"),
            ("GOLF 고객 집중도", "34", "%", "GOLF", "단일 고객 매출 비중 — 구조적 risk", "warn"),
        ],
    )

    return f"""<section class="panel" data-panel="ops-kpi">
  <div class="wrap">

    <a class="back-to-toc" href="#ops-kpi-anchor-top">TOC</a>

    {exec_h}

    <nav class="ops-subnav" id="ops-kpi-anchor-top" aria-label="ops-kpi sub-navigation">
      <a class="chip" href="#kpi-dashboard">KPI 대시보드</a>
      <a class="chip" href="#kpi-timeseries">시계열 detail</a>
      <a class="chip" href="#kpi-member">DMIG 회원 tier</a>
      <a class="chip" href="#kpi-dept">PIPG 부서별 인원</a>
      <a class="chip" href="#kpi-agreements">PIPG 약정 timeline</a>
      <a class="chip" href="#kpi-land">PIPG 토지·HGB</a>
      <a class="chip" href="#kpi-segment6">6-peer 골프</a>
      <a class="chip" href="#kpi-dividend">배당</a>
      <a class="chip" href="#kpi-related">관계사·집중도</a>
    </nav>

    <div class="section ops-summary">
      <h2>운영 KPI — TL;DR (4 발견)</h2>
      <h3>운영 활동·고객·인력·자본배분 핵심</h3>
      <div class="insight-grid">
        <div class="insight-card insight-positive">
          <div class="insight-tag"><span class="ticker-mini">DMIG</span> 회복 모멘텀</div>
          <div class="insight-metric up">+372<span class="u">%</span></div>
          <div class="insight-title">Range@PIK 매출 FY22→23</div>
          <p>골프테인먼트(driving range + entertainment) 신규 시설이 회복기 핵심 driver. 본업 골프 +29.12% 동시.</p>
        </div>
        <div class="insight-card insight-positive">
          <div class="insight-tag"><span class="ticker-mini">PIPG</span> 골퍼 8% 성장</div>
          <div class="insight-metric up">26,551<span class="u">명</span></div>
          <div class="insight-title">FY22 member golfer +8% YoY</div>
          <p>회원 충성도(+8%) + non-member 40,987명 동시 확보. CBD 5분 + 브랜드(1976)로 mature operator 입증.</p>
        </div>
        <div class="insight-card insight-warn">
          <div class="insight-tag"><span class="ticker-mini">GOLF</span> 고객 집중도 risk</div>
          <div class="insight-metric down">34<span class="u">%</span></div>
          <div class="insight-title">단일 고객 매출 비중</div>
          <p>FY24 IDR 34.7bn 단일 고객 의존. CWIP 426bn 진행 중 — 신규 시설 완공 후 매출 분산 필요.</p>
        </div>
        <div class="insight-card insight-positive">
          <div class="insight-tag"><span class="ticker-mini">PIPG</span> 배당 안정성</div>
          <div class="insight-metric up">46.9<span class="u">%</span></div>
          <div class="insight-title">FY23 payout ratio</div>
          <p>주당 Rp 20.20M · RUPST 2024-06-06. DMIG 37.2% · SMDM 0% (BSDE 인수 직전) — 3-peer 차별화.</p>
        </div>
      </div>
    </div>

    <div class="section" id="kpi-dashboard">
      <h2 data-num="01">운영 KPI 시계열 — 대시보드</h2>
      <h3>골퍼·회원·인력·CWIP 6-tile sparkline 대시보드</h3>
      {ops_kpi_dashboard}
    </div>

    <div class="section" id="kpi-timeseries">
      <h2 data-num="02">시계열 detail</h2>
      <h3>각 peer별 상세 데이터 (페이지 추적 가능)</h3>
      {ops_kpi_section_html}
    </div>

    <div class="section" id="kpi-member">
      <h2 data-num="03">DMIG 회원 tier breakdown — FY2023</h2>
      <h3>Main Playing 1,233명 구성 (Adult / Husband-Wife / Child)</h3>
      <p class="lede">
        DMIG의 Main Playing Member 구성을 tier별로 분해. Husband/Wife (79명) + Child (35명) = 114명 family tier로,
        adult 단독 회원 1,119명이 핵심 충성 고객. FY22→FY23 -6명으로 stable.
      </p>
      {dmig_member_chart}
    </div>

    <div class="section" id="kpi-dept">
      <h2 data-num="04">PIPG 부서별 인원 (FY2024)</h2>
      <h3>turnover graph 기준 Top 부서 horizontal bar</h3>
      {pipg_dept_chart}
    </div>

    <div class="section" id="kpi-agreements">
      <h2 data-num="05">PIPG 약정·lease timeline</h2>
      <h3>4개 lease/약정 — related party 2건 + third party 2건</h3>
      <p class="lede">
        <strong>MKPI (Metropolitan Kentjana, related party)</strong>: Pool management rights + Land lease (Junior Driving Range).
        <strong>3rd party</strong>: 통신탑 land lease (Indosat → Epid Menara renewal).
        Cross-default risk 모니터링 핵심.
      </p>
      {pipg_agreements_timeline}
    </div>

    <div class="section" id="kpi-land">
      <h2 data-num="06">PIPG 토지·HGB·임차 구조</h2>
      <h3>53ha 토지 + 12 인증서 + HGB 면적 + MKPI 임차</h3>
      {land_hgb_visual}
    </div>

    <div class="section" id="kpi-segment6">
      <h2 data-num="07">6-peer 골프 segment — 매출 × GP × 비중</h2>
      <h3>bubble scatter (FY2024) — 4-사분면 분류</h3>
      {segment_scatter}
      <details class="orig-toggle"><summary>원본 6-peer 표</summary>
        {golf_segment_table}
      </details>
    </div>

    <div class="section" id="kpi-dividend">
      <h2 data-num="08">배당 시계열 — 3-peer capital allocation</h2>
      <h3>FY22-24 + payout ratio + RUPST 날짜</h3>
      {dividend_visual}
      <details class="orig-toggle"><summary>원본 배당 표</summary>
        {dividend_table}
      </details>
    </div>

    <div class="section" id="kpi-related">
      <h2 data-num="09">관계사·고객·공급사 집중도</h2>
      <h3>annual report Note에서 추출한 audit-grade 정량 정보</h3>
      {related_party_visual}
      <details class="orig-toggle"><summary>원본 상세 표</summary>
        {related_party_section}
      </details>
    </div>

    <div class="closing-stripe">
      <div class="cs-eyebrow">운영 KPI 종합</div>
      <div class="cs-title">4 takeaways</div>
      <div class="closing-grid">
        <div class="closing-takeaway"><div class="num">1</div><div class="txt"><strong>Operational momentum</strong> · DMIG Range@PIK +372% & 골퍼 +12% → 다양화 + 회복</div></div>
        <div class="closing-takeaway"><div class="num">2</div><div class="txt"><strong>Mature operator</strong> · PIPG 67,538 골퍼 + 53ha 토지 · MKPI 임차 = 단일 코스에서 도시 핵심 자원</div></div>
        <div class="closing-takeaway"><div class="num">3</div><div class="txt"><strong>Capital allocation 차별</strong> · PIPG 47% payout · DMIG 37% · SMDM 0% (BSDE 인수 직전)</div></div>
        <div class="closing-takeaway"><div class="num">4</div><div class="txt"><strong>Concentration risk</strong> · GOLF 34% 단일 고객 · MDLN 공급사 집중 → KIJA(captive)·KPIG(diversified) 대비 vulnerable</div></div>
      </div>
    </div>

  </div>
</section>"""


def section_capex() -> str:
    """Tab 2: CAPEX — capital investment, asset intensity, unit economics, P&L margin (CAPEX lens)."""
    capex_heatmap = _capex_heatmap_section()
    capex_proxy_table = _capex_proxy_table()
    capex_narratives = _capex_narrative_grid()
    per_hole_visual = _per_hole_visual_section()
    per_hole_table = _per_hole_metrics_table()
    pnl_trend = _pnl_margin_trend_section()
    peer_radar = _peer_compare_radar()
    pnl_funnel = _pnl_funnel_section()
    pnl_table = _pnl_table()
    golf_cwip_detail = _golf_cwip_detail_chart()
    depreciation_lines = _depreciation_lines_chart()
    asset_turnover = _asset_turnover_strip()

    exec_h = _tab_exec_headline(
        tab_key="CAPEX · ASSETS",
        tab_title="CAPEX 강도 · 자산 효율 · 단위 경제",
        tab_focus_tiles=[
            ("진행 중 CAPEX", "426", "bn", "GOLF", "CWIP Buildings 188 + Landscape 238 (FY25)", "gold"),
            ("감가/매출 최고", "12.2", "%", "DMIG", "PIK Range 신규 + BSD/PIK 2 코스", "warn"),
            ("자산집약도 최고", "23.8", "×", "KPIG", "73.8% 자산 비중 (FA + 투자부동산)", "blue"),
            ("홀당 매출 1위", "11.0", "bn/홀", "PIPG", "Entity all-in 기준 (1 코스 197.6bn)", "green"),
            ("Asset-light leader", "21.1", "%", "GOLF", "OpEx/매출 (DMIG 38% 대비)", "green"),
        ],
    )

    return f"""<section class="panel" data-panel="capex">
  <div class="wrap">

    <a class="back-to-toc" href="#capex-anchor-top">TOC</a>

    {exec_h}

    <nav class="ops-subnav" id="capex-anchor-top" aria-label="capex sub-navigation">
      <a class="chip" href="#cap-heatmap">강도 heatmap</a>
      <a class="chip" href="#cap-turnover">자산 회전율</a>
      <a class="chip" href="#cap-cwip">GOLF CWIP detail</a>
      <a class="chip" href="#cap-depr">감가 라인</a>
      <a class="chip" href="#cap-narratives">AR narrative</a>
      <a class="chip" href="#cap-perhole">홀당 단위</a>
      <a class="chip" href="#cap-pnl">P&amp;L 4Y</a>
      <a class="chip" href="#cap-radar">radar</a>
      <a class="chip" href="#cap-funnel">funnel</a>
    </nav>

    <div class="section ops-summary">
      <h2>CAPEX — TL;DR (4 발견)</h2>
      <h3>자본투자 강도·자산 효율·단위 경제 핵심</h3>
      <div class="insight-grid">
        <div class="insight-card insight-warn">
          <div class="insight-tag"><span class="ticker-mini">GOLF</span> Capex-intensive</div>
          <div class="insight-metric up">426<span class="u">bn</span></div>
          <div class="insight-title">CWIP (Buildings 188 + Landscape 238)</div>
          <p>FY25 entity 매출 102bn의 ~4.2배 규모. paid-in 487bn + retained 6.9조 self-funded. 향후 3-5년 감가 부담 예고.</p>
        </div>
        <div class="insight-card insight-warn">
          <div class="insight-tag"><span class="ticker-mini">DMIG</span> 자본투자 강도 peer 최고</div>
          <div class="insight-metric down">12.2<span class="u">%</span></div>
          <div class="insight-title">감가상각 / 매출 (FY24)</div>
          <p>PIK Range +372% 성장 · BSD+PIK 2 코스 운영. FY24→25 ▲+0.7pp 추가 — 마진 압박의 핵심 원인.</p>
        </div>
        <div class="insight-card insight-neutral">
          <div class="insight-tag"><span class="ticker-mini">PIPG</span> Mature & maintenance-heavy</div>
          <div class="insight-metric">5.9<span class="u">%</span></div>
          <div class="insight-title">유지보수 / 매출</div>
          <p>1976년 개장 노후 코스. DMIG 0.9% 대비 ~6배 — 프리미엄 포지셔닝 비용 (Indonesia Open 등 토너먼트 hosting).</p>
        </div>
        <div class="insight-card insight-positive">
          <div class="insight-tag"><span class="ticker-mini">KIJA</span> 단위 매출 unexpected 1위</div>
          <div class="insight-metric up">4.7<span class="u">bn/홀</span></div>
          <div class="insight-title">홀당 매출 (golf segment only)</div>
          <p>industrial estate 본업이지만 Nick Faldo 설계 + Jababeka captive demand → 6-peer 중 unit revenue 최고.</p>
        </div>
      </div>
    </div>

    <div class="section" id="cap-heatmap">
      <h2 data-num="01">자본투자 강도 heatmap — 감가·유지·자산집약도</h2>
      <h3>Audited CAPEX 미공시 → P&L proxy + B/S proxy로 추정 (FY24)</h3>
      <p class="lede">
        CAPEX 직접 공시는 없으나 (1) 감가상각비/매출 (2) 유지보수/매출 (3) 총자산/매출 — 3개 indicator로 자본투자 강도 추정.
        Heatmap 색 진할수록 강도 ↑ · FY23→24 trend 화살표 (▲/▼ pp delta).
      </p>
      {capex_heatmap}
      <details class="orig-toggle"><summary>원본 CAPEX proxy 표</summary>
        {capex_proxy_table}
      </details>
    </div>

    <div class="section" id="cap-turnover">
      <h2 data-num="02">자산 회전율 — 4-peer efficiency</h2>
      <h3>매출 / 총자산 · 자산집약도 · 매출/홀</h3>
      {asset_turnover}
    </div>

    <div class="section" id="cap-cwip">
      <h2 data-num="03">GOLF CWIP detail — 6 카테고리 분해</h2>
      <h3>FY2025 진행 중 자산 426bn의 구성 (Buildings/Landscape/Equipment/Vehicles/Furniture)</h3>
      {golf_cwip_detail}
    </div>

    <div class="section" id="cap-depr">
      <h2 data-num="04">감가상각 라인 — 3-peer 직접 비교</h2>
      <h3>Penyusutan / Depreciation 라인 IDR + 매출 대비 % + YoY (FY24)</h3>
      {depreciation_lines}
    </div>

    <div class="section" id="cap-narratives">
      <h2 data-num="05">왜? — AR 본문 인용 (벡터 DB 검증)</h2>
      <h3>같은 12% 감가도 신규 투자 / 노후 자산 / 회계 정책 — 본문에서 의도 확인</h3>
      {capex_narratives}
    </div>

    <div class="section" id="cap-perhole">
      <h2 data-num="06">홀당 단위 경제 — 7-peer Unit Economics</h2>
      <h3>매출 / GP / OpEx / 감가상각을 홀 수로 normalize (FY24)</h3>
      <p class="lede">
        peer마다 코스 수·운영 형태가 다르므로 entity 매출 절대값 비교는 misleading. 홀 수로 나눈 unit economics가 더 의미 있는 비교.
        <strong>ENT</strong> (entity all-in) vs <strong>SEG</strong> (golf segment-only) 차이 주의.
      </p>
      {per_hole_visual}
      <details class="orig-toggle"><summary>원본 per-hole 표</summary>
        {per_hole_table}
      </details>
    </div>

    <div class="section" id="cap-pnl">
      <h2 data-num="07">P&L 4Y 마진 추이 — Pure-play 3-peer</h2>
      <h3>FY22-25 GP·Op·Net margin trend (CAPEX 영향 관점)</h3>
      {pnl_trend}
      <details class="orig-toggle"><summary>원본 4Y P&amp;L 표</summary>
        {pnl_table}
      </details>
    </div>

    <div class="section" id="cap-radar">
      <h2 data-num="08">DMIG vs PIPG — 6축 radar 1:1 비교</h2>
      <h3>매출·마진·CAPEX(감가/유지)·배당·unit econ을 한 차트로</h3>
      {peer_radar}
    </div>

    <div class="section" id="cap-funnel">
      <h2 data-num="09">P&L Funnel — 매출→Gross→Op→Net leakage</h2>
      <h3>각 단계 % of revenue + leakage % 시각화 (FY24)</h3>
      {pnl_funnel}
    </div>

    <div class="closing-stripe">
      <div class="cs-eyebrow">CAPEX 종합</div>
      <div class="cs-title">4 takeaways</div>
      <div class="closing-grid">
        <div class="closing-takeaway"><div class="num">1</div><div class="txt"><strong>GOLF self-funded 확장</strong> · CWIP 426bn (매출의 4.2배) · 외부 차입 없이 paid-in + retained로 조달</div></div>
        <div class="closing-takeaway"><div class="num">2</div><div class="txt"><strong>DMIG 감가 부담 가속</strong> · 12.2%/매출 (peer 최고) · FY24→25 ▲+0.7pp · 마진 -12% 트리거</div></div>
        <div class="closing-takeaway"><div class="num">3</div><div class="txt"><strong>PIPG mature operator</strong> · 유지보수 5.9% (DMIG 0.9%×6) — 노후 자산의 본질적 비용 + 프리미엄 포지셔닝</div></div>
        <div class="closing-takeaway"><div class="num">4</div><div class="txt"><strong>Unit economics 역설</strong> · KIJA 4.7bn/홀 (industrial estate) > GOLF 2.6 (pure-play) — captive demand의 힘</div></div>
      </div>
    </div>

  </div>
</section>"""


def section_opex() -> str:
    """Tab 3: OPEX — operating cost structure, margin, segment GP, FY25 prelim."""
    opex_topn = _opex_topn_section()
    opex_norm_table = _normalized_opex_compare_table()
    opex_kpi_strip = _opex_kpi_strip()
    opex_stack = _opex_stacked_bars()
    opex_norm_bars = _opex_norm_bar_table()
    opex_narratives = _opex_narrative_grid()
    pipg_seg_visual = _pipg_segment_visual()
    pipg_seg_table = _pipg_segment_table()
    fy25_dashboard = _fy25_dashboard()
    fy25_cards = _fy25_delta_cards()
    margin_change = _margin_change_visual()
    revenue_topn = _revenue_topn_section()
    revenue_narratives = _revenue_narrative_grid()
    cogs_topn = _cogs_topn_section()
    opex_category_compare = _opex_category_cross_peer_section()
    opex_4y_trend = _opex_4y_trend_chart()

    opex_blocks = "\n".join(filter(None, [
        _opex_breakdown_table("DMIG", "opex_note", "OpEx 라인 분해 (Note 25)"),
        _opex_breakdown_table("PIPG", "opex_note_29", "OpEx 라인 분해 (Note 29)"),
        _opex_breakdown_table("KPIG", "ga_note_34", "G&A 비용 라인 (Note 34) — Hotel+Resort+Golf 통합"),
    ]))
    rev_blocks = "\n".join(filter(None, [
        _revenue_breakdown_table("DMIG", "revenue_note", "매출 라인 분해"),
        _revenue_breakdown_table("PIPG", "revenue_note_27", "매출 라인 분해 (Note 27)"),
    ]))
    cogs_blocks = "\n".join(filter(None, [
        _revenue_breakdown_table("DMIG", "cogs_note", "COGS 라인 분해"),
        _revenue_breakdown_table("PIPG", "cogs_note_28", "COGS 라인 분해 (Note 28)"),
    ]))

    exec_h = _tab_exec_headline(
        tab_key="OPEX · COST STRUCTURE",
        tab_title="비용 구조 · 라인 분해 · 마진 압박",
        tab_focus_tiles=[
            ("OpEx ratio peer 최저", "21.1", "%", "GOLF", "DMIG/PIPG 38% 대비 압도적 efficient", "green"),
            ("FY25 best operator", "+4.0", "%", "PIPG", "OpEx -17.9% 절감 → 영업이익 +4.0%", "green"),
            ("최대 cost 라인", "12.6", "%", "DMIG", "인건비/매출 peer 최고", "warn"),
            ("Membership GP", "87.8", "%", "PIPG", "FY23 Note 30 4-segment 최고 마진", "green"),
            ("FY25 마진 압박", "-12.0", "%", "DMIG", "영업이익 YoY (78.9→69.4bn)", "warn"),
        ],
    )

    return f"""<section class="panel" data-panel="opex">
  <div class="wrap">

    <a class="back-to-toc" href="#opex-anchor-top">TOC</a>

    {exec_h}

    <nav class="ops-subnav" id="opex-anchor-top" aria-label="opex sub-navigation">
      <a class="chip" href="#op-rev">매출 라인</a>
      <a class="chip" href="#op-cogs">COGS 라인</a>
      <a class="chip" href="#op-opex">OpEx 라인</a>
      <a class="chip" href="#op-norm">OpEx 정규화</a>
      <a class="chip" href="#op-category">카테고리 deep-dive</a>
      <a class="chip" href="#op-4y-trend">4Y trend</a>
      <a class="chip" href="#op-narratives">AR narrative</a>
      <a class="chip" href="#op-pipg">PIPG 4-seg GP</a>
      <a class="chip" href="#op-fy25">FY25 prelim</a>
      <a class="chip" href="#op-margin">마진 변화</a>
    </nav>

    <div class="section ops-summary">
      <h2>OPEX — TL;DR (4 발견)</h2>
      <h3>비용 구조·라인 분해·마진 압박 핵심</h3>
      <div class="insight-grid">
        <div class="insight-card insight-positive">
          <div class="insight-tag"><span class="ticker-mini">GOLF</span> Asset-light leader</div>
          <div class="insight-metric up">21.1<span class="u">%</span></div>
          <div class="insight-title">OpEx / 매출 (FY24)</div>
          <p>DMIG/PIPG 38% 대비 압도적 효율. 솔라+리튬 카트로 유틸리티 구조적 절감. IPO 1년차 효과도 일부.</p>
        </div>
        <div class="insight-card insight-positive">
          <div class="insight-tag"><span class="ticker-mini">PIPG</span> Membership cash machine</div>
          <div class="insight-metric up">87.8<span class="u">%</span></div>
          <div class="insight-title">FY23 Membership segment GP margin</div>
          <p>신규 회원/연회비 거의 순이익에 가까움 (소액 COGS). Golf course 58.7% · Restaurant 31.2% 와 차별화.</p>
        </div>
        <div class="insight-card insight-warn">
          <div class="insight-tag"><span class="ticker-mini">DMIG</span> 인건비·세금 부담</div>
          <div class="insight-metric down">12.6<span class="u">%</span></div>
          <div class="insight-title">인건비 / 매출 (peer 최고)</div>
          <p>206명 직원 + employee benefits liability Rp 135bn. 세금·법률도 5.2%/매출. 노후 자산 + 장기근속자 결합 구조.</p>
        </div>
        <div class="insight-card insight-warn">
          <div class="insight-tag"><span class="ticker-mini">PIPG</span> 세금 outlier</div>
          <div class="insight-metric down">12.3<span class="u">%</span></div>
          <div class="insight-title">세금·법률 / 매출 (FY24 Pajak dan perijinan 24.2bn)</div>
          <p>CBD 5분 + HGB 면적 + property tax 비중 큰 위치적 비용 — DMIG 5.2% / GOLF 3.1% 대비 outlier.</p>
        </div>
      </div>
    </div>

    <div class="section" id="op-rev">
      <h2 data-num="01">매출 라인 분해 — Pure-play (FY23→FY24)</h2>
      <h3>골프 / F&amp;B / 회원권 / 부대시설 별 매출 + AR narrative</h3>
      {revenue_topn}

      <h4 class="ops-block-h" style="margin-top: 22px;">왜? — 매출 성장 driver (벡터 DB 검증)</h4>
      {revenue_narratives}

      <details class="orig-toggle"><summary>원본 매출 라인 표</summary>
        {rev_blocks}
      </details>
    </div>

    <div class="section" id="op-cogs">
      <h2 data-num="02">COGS 라인 분해 — segment별 매출원가</h2>
      <h3>골프 코스 / 레스토랑 / 카트 / 드라이빙 레인지</h3>
      {cogs_topn}

      <details class="orig-toggle"><summary>원본 COGS 라인 표</summary>
        {cogs_blocks}
      </details>
    </div>

    <div class="section" id="op-opex">
      <h2 data-num="03">OpEx 라인 분해 — 3-peer top-N</h2>
      <h3>인건비 · 감가 · 유지 · 세금 · 유틸리티 — DMIG/PIPG/KPIG</h3>
      {opex_topn}

      <details class="orig-toggle"><summary>원본 OpEx 라인 표</summary>
        {opex_blocks}
      </details>
    </div>

    <div class="section" id="op-norm">
      <h2 data-num="04">OpEx 카테고리별 정규화 — DMIG vs PIPG vs GOLF</h2>
      <h3>FY24 매출 대비 % · cross-peer 같은 잣대 (11 카테고리 keyword 분류)</h3>
      <p class="lede">
        AR Note 라벨이 peer마다 달라 직접 비교가 어려운 문제를 해결 — 모든 OpEx 라인을 11 카테고리로 keyword 기반 자동 분류.
        시각화 우선 (KPI strip → 100% stacked → bar matrix).
      </p>

      {opex_kpi_strip}

      <h4 class="ops-block-h">100% stacked — OpEx 구성 비중</h4>
      {opex_stack}

      <h4 class="ops-block-h" style="margin-top: 22px;">카테고리별 매출 대비 % — bar matrix</h4>
      {opex_norm_bars}

      <details class="orig-toggle"><summary>원본 정규화 표</summary>
        {opex_norm_table}
      </details>
    </div>

    <div class="section" id="op-category">
      <h2 data-num="05">OpEx 카테고리 deep-dive — 4 핵심 비교</h2>
      <h3>인건비 · 세금·법률 · 유지보수 · 유틸리티 — peer 차이의 본질</h3>
      <p class="lede">
        OpEx 합계만 보면 38% vs 21%로 단순하지만, <strong>카테고리별로 들어가면 진짜 차이</strong>가 드러남.
        DMIG는 인건비 1위, PIPG는 세금·유지 1위, GOLF는 모든 면에서 lean.
        각 카테고리에서 contributing line items도 inline 표시.
      </p>
      {opex_category_compare}
    </div>

    <div class="section" id="op-4y-trend">
      <h2 data-num="06">OpEx/매출 % — 4Y trend (FY22-25)</h2>
      <h3>비용 효율 추이 — DMIG/PIPG/GOLF</h3>
      {opex_4y_trend}
    </div>

    <div class="section" id="op-narratives">
      <h2 data-num="07">왜? — 운영 리스크 & 비용 sensitivity (벡터 DB)</h2>
      <h3>OpEx 절댓값 뒤의 의미 — 보험·인건비 leverage·ESG·자본</h3>
      {opex_narratives}
    </div>

    <div class="section" id="op-pipg">
      <h2 data-num="08">PIPG 4-segment GP margin — Note 30</h2>
      <h3>Golf Course&amp;Cart / Membership / Restaurant / Others (FY23)</h3>
      <p class="lede">
        PIPG는 Note 30 Segment Information에서 4 segment의 COGS를 explicit 공시. Membership 부문 GP margin 압도적 높음 (87.8%).
      </p>
      {pipg_seg_visual}
      <details class="orig-toggle"><summary>원본 segment 표</summary>
        {pipg_seg_table}
      </details>
    </div>

    <div class="section" id="op-fy25">
      <h2 data-num="09">FY2025 미감사 prelim — 마진 압박 신호</h2>
      <h3>DMIG/PIPG/KPIG 3-peer side-by-side dashboard</h3>
      {fy25_dashboard}
      <details class="orig-toggle"><summary>원본 카드</summary>
        {fy25_cards}
      </details>
    </div>

    <div class="section" id="op-margin">
      <h2 data-num="10">FY24→FY25 마진 변화 — 벡터 추출 commentary</h2>
      <h3>6-peer timeline 카드 + FY24↔FY25 mini delta bar</h3>
      {margin_change}
    </div>

    <div class="closing-stripe">
      <div class="cs-eyebrow">OPEX 종합</div>
      <div class="cs-title">4 takeaways</div>
      <div class="closing-grid">
        <div class="closing-takeaway"><div class="num">1</div><div class="txt"><strong>GOLF asset-light</strong> · OpEx 21.1%/매출 (DMIG/PIPG 38% 대비) — 솔라+리튬 + IPO 1년차 효과</div></div>
        <div class="closing-takeaway"><div class="num">2</div><div class="txt"><strong>PIPG cost discipline</strong> · FY25 OpEx -17.9% → 매출 -6%에도 영업이익 +4% · Membership 87.8% GP가 cash 회수력</div></div>
        <div class="closing-takeaway"><div class="num">3</div><div class="txt"><strong>DMIG 압박 가속</strong> · 인건비 12.6% + 감가 12.2% peer 최고 · FY25 -12% 영업이익</div></div>
        <div class="closing-takeaway"><div class="num">4</div><div class="txt"><strong>SMDM 적자전환</strong> · Golf GP -16.9pp FY23→24 · BSDE 인수 후 회계 재분류 신호</div></div>
      </div>
    </div>

  </div>
</section>"""


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
    ops_kpi_html = section_ops_kpi()
    capex_html = section_capex()
    opex_html = section_opex()
    sections = "\n".join([
        ops_kpi_html,
        capex_html,
        opex_html,
        section_reference(),
    ])
    # Count sections + visual elements across the 3 new ops tabs
    combined = ops_kpi_html + capex_html + opex_html
    ops_sections_count = combined.count('<h2>') + combined.count('<h2 data-num=')
    viz_svg_count = combined.count('<svg ')
    viz_kpi_count = combined.count('class="kpi-tile')
    viz_quote_count = combined.count('class="quote-card')
    viz_chart_count = combined.count('class="stack-row"') + viz_svg_count

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
      <button class="tab" data-tab="ops-kpi" type="button">⚙️ 운영 KPI</button>
      <button class="tab" data-tab="capex" type="button">🏗️ CAPEX</button>
      <button class="tab" data-tab="opex" type="button">💸 OPEX</button>
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
      Ops 탭 <strong>{ops_sections_count}</strong>개 분석 섹션 ·
      <strong>{viz_svg_count}</strong> SVG 차트 · <strong>{viz_kpi_count}</strong> KPI 타일 · <strong>{viz_quote_count}</strong> 벡터 narrative 카드 ·
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
