"""Build clubs/index.html with enhanced peer cards (merge of clubs + Peer card)."""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import json
import os

clubs = json.load(open('data/_clubs_meta.json','r',encoding='utf-8'))
d5y = json.load(open('../../data/company_financials_5y.json','r',encoding='utf-8'))
fin = {c['ticker']: c for c in d5y['companies'] if 'ticker' in c}

peers_v2 = ['DMIG','PIPG','GOLF','MDLN','KIJA','SMDM','KPIG','SMRA','BSDE','CTRA','ELTY','LPKR','PWON']

def torder(t):
    return {'pp':1,'resort':2,'twn':3}.get(clubs[t]['tier'], 9)

def fmtBn(v):
    if v is None: return '—'
    if abs(v) >= 1000: return f'Rp {v/1000:,.1f}T'
    return f'Rp {v:,.0f}B'

def fmtPct(v):
    if v is None: return '—'
    col = '#16a34a' if v > 0 else '#b91c1c' if v < 0 else '#666'
    return f'<span style="color:{col}; font-weight:700;">{v:+.1f}%</span>'

def build_sparkline(c5y, color):
    """5-year revenue sparkline (FY20-FY24) as inline SVG, 120×30."""
    years = ['2020','2021','2022','2023','2024']
    series = [c5y.get('yearly',{}).get(y,{}).get('revenue') for y in years]
    valid = [v for v in series if v]
    if len(valid) < 2:
        return '<span style="color:var(--ops-muted); font-size:11px;">—</span>'
    W, H, padX, padY = 120, 30, 3, 4
    mn, mx = min(valid), max(valid)
    rng = mx - mn if mx > mn else 1
    pts = []
    for i, v in enumerate(series):
        if v is None: continue
        x = padX + (W - 2*padX) * (i / (len(years)-1))
        y = H - padY - (H - 2*padY) * (v - mn) / rng
        pts.append((x, y, v, years[i]))
    if len(pts) < 2:
        return '<span style="color:var(--ops-muted); font-size:11px;">—</span>'
    path_d = 'M ' + ' L '.join(f'{x:.1f},{y:.1f}' for x,y,_,_ in pts)
    area_d = f'{path_d} L {pts[-1][0]:.1f},{H-padY} L {pts[0][0]:.1f},{H-padY} Z'
    # Mark last point larger
    last = pts[-1]
    dots = ''
    for i, (x, y, v, yr) in enumerate(pts):
        if i == len(pts) - 1:
            dots += f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.5" fill="{color}" stroke="white" stroke-width="1.2"><title>FY{yr}: {v/1e9:.1f}B</title></circle>'
        else:
            dots += f'<circle cx="{x:.1f}" cy="{y:.1f}" r="1.4" fill="{color}" stroke="white" stroke-width="0.8"><title>FY{yr}: {v/1e9:.1f}B</title></circle>'
    return (
        f'<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}" style="display:block;" aria-label="5년 매출 추이">'
        f'<path d="{area_d}" fill="{color}" opacity="0.16"/>'
        f'<path d="{path_d}" stroke="{color}" stroke-width="1.6" fill="none"/>'
        f'{dots}</svg>'
    )

cards_html = []
peers_sorted = sorted(peers_v2, key=lambda t: (torder(t), t))

for t in peers_sorted:
    c = clubs[t]
    c5y = fin.get(t,{})
    y24 = c5y.get('yearly',{}).get('2024',{})
    y23 = c5y.get('yearly',{}).get('2023',{})
    rev = y24.get('revenue')
    np_ = y24.get('net_profit')
    ta = y24.get('total_assets')
    ebitda = y24.get('ebitda')
    rev_prev = y23.get('revenue')
    rev_bn = rev/1e9 if rev else None
    ta_bn = ta/1e9 if ta else None
    margin = (np_/rev*100) if (rev and np_) else None
    roa = (np_/ta*100) if (ta and np_) else None
    eb_margin = (ebitda/rev*100) if (rev and ebitda is not None) else None
    yoy = ((rev - rev_prev)/rev_prev*100) if (rev and rev_prev) else None
    tier_color = {'pp':'#3b82f6','resort':'#f59e0b','twn':'#16a34a'}[c['tier']]

    # Sort keys (use raw numbers; null treated as -Infinity so they fall to bottom on desc sort)
    sort_rev = rev_bn if rev_bn is not None else -1e15
    sort_margin = margin if margin is not None else -1e15
    sort_roa = roa if roa is not None else -1e15
    sort_ta = ta_bn if ta_bn is not None else -1e15
    sort_eb = eb_margin if eb_margin is not None else -1e15
    sort_yoy = yoy if yoy is not None else -1e15
    # Search text (lowercase, concatenated)
    search_blob = f'{t} {c["name"]} {c["sub"]} {c["loc"]} {c["parent"]}'.lower()
    spark_svg = build_sparkline(c5y, tier_color)
    cards_html.append(
        f'      <a href="{t.lower()}.html" class="club-card" data-tier="{c["tier"]}" data-ticker="{t}" '
        f'data-search="{search_blob}" '
        f'data-rev="{sort_rev}" data-margin="{sort_margin}" data-roa="{sort_roa}" data-ta="{sort_ta}" data-ebmargin="{sort_eb}" data-yoy="{sort_yoy}" data-name="{c["name"]}" data-tier-label="{c["tier_label"]}" data-loc="{c["loc"]}" '
        f'style="background:var(--ops-surface); border:1px solid var(--ops-line); border-top:4px solid {tier_color}; '
        f'border-radius:10px; padding:18px 22px; text-decoration:none; color:inherit; display:flex; flex-direction:column; gap:10px; transition:all 0.2s;">\n'
        f'        <label class="compare-check" title="비교 추가/제거" onclick="event.stopPropagation()"><input type="checkbox" class="cmp-cb" data-ticker="{t}" onclick="event.stopPropagation(); event.preventDefault();" aria-label="비교 선택"></label>\n'
        f'        <div style="display:flex; justify-content:space-between; align-items:flex-start; padding-right:24px;">\n'
        f'          <div>\n'
        f'            <div style="font-size:11px; font-weight:700; color:var(--ops-muted); letter-spacing:0.06em;">{t} · IDX</div>\n'
        f'            <div style="font-size:17px; font-weight:700; margin-top:4px; color:var(--ops-ink); line-height:1.3;">{c["name"]}</div>\n'
        f'            <div style="font-size:12px; color:var(--ops-ink-soft); margin-top:2px;">{c["sub"]}</div>\n'
        f'          </div>\n'
        f'          <span class="peer-tag peer-tag-{c["tier"]}" style="font-size:10.5px; white-space:nowrap;">{c["tier_label"]}</span>\n'
        f'        </div>\n'
        f'        <div style="display:grid; grid-template-columns:repeat(2,1fr); gap:6px 14px; font-size:12px; color:var(--ops-ink-soft); margin-top:4px;">\n'
        f'          <div><strong style="color:var(--ops-muted);">위치</strong><br>{c["loc"]}</div>\n'
        f'          <div><strong style="color:var(--ops-muted);">홀</strong><br>{c["holes"]}</div>\n'
        f'          <div><strong style="color:var(--ops-muted);">면적</strong><br>{c["area"]}</div>\n'
        f'          <div><strong style="color:var(--ops-muted);">모회사</strong><br>{c["parent"][:30]}{"..." if len(c["parent"])>30 else ""}</div>\n'
        f'        </div>\n'
        f'        <div style="display:grid; grid-template-columns:repeat(2,1fr); gap:6px 14px; padding:10px 0; border-top:1px dashed var(--ops-line); border-bottom:1px dashed var(--ops-line); font-size:11.5px;">\n'
        f'          <div><strong style="color:var(--ops-muted);">FY24 매출</strong><br><span style="font-weight:700; color:var(--ops-ink);">{fmtBn(rev_bn)}</span></div>\n'
        f'          <div><strong style="color:var(--ops-muted);">매출 YoY</strong><br>{fmtPct(yoy)}</div>\n'
        f'          <div><strong style="color:var(--ops-muted);">순이익률</strong><br>{fmtPct(margin)}</div>\n'
        f'          <div><strong style="color:var(--ops-muted);">EBITDA 마진</strong><br>{fmtPct(eb_margin)}</div>\n'
        f'          <div><strong style="color:var(--ops-muted);">총자산</strong><br><span style="color:var(--ops-ink);">{fmtBn(ta_bn)}</span></div>\n'
        f'          <div><strong style="color:var(--ops-muted);">ROA</strong><br>{fmtPct(roa)}</div>\n'
        f'        </div>\n'
        f'        <div style="display:flex; justify-content:space-between; align-items:flex-end; font-size:11.5px;">\n'
        f'          <div style="flex:1;"><strong style="color:var(--ops-muted);">5년 매출 추이 (FY20→24)</strong><br>{spark_svg}</div>\n'
        f'          <div style="text-align:right; align-self:flex-end; font-weight:700; color:{tier_color};">상세 →</div>\n'
        f'        </div>\n'
        f'        <div style="font-size:11.5px; padding-top:4px; border-top:1px dashed var(--ops-line);">\n'
        f'          <strong style="color:var(--ops-muted);">골프 매출 FY24</strong>: <span style="font-weight:700; color:var(--ops-green);">Rp {c["golf_rev_fy24"]}</span>\n'
        f'        </div>\n'
        f'      </a>'
    )

cards_section = '\n'.join(cards_html)

# ============================================================
# Compact table rows (mirrors card data for table view)
# ============================================================
table_rows = []
for t in peers_sorted:
    c = clubs[t]
    c5y = fin.get(t,{})
    y24 = c5y.get('yearly',{}).get('2024',{})
    y23 = c5y.get('yearly',{}).get('2023',{})
    rev = y24.get('revenue')
    np_ = y24.get('net_profit')
    ta = y24.get('total_assets')
    ebitda = y24.get('ebitda')
    rev_prev = y23.get('revenue')
    rev_bn = rev/1e9 if rev else None
    ta_bn = ta/1e9 if ta else None
    margin = (np_/rev*100) if (rev and np_) else None
    roa = (np_/ta*100) if (ta and np_) else None
    eb_margin = (ebitda/rev*100) if (rev and ebitda is not None) else None
    yoy = ((rev - rev_prev)/rev_prev*100) if (rev and rev_prev) else None
    tier_color = {'pp':'#3b82f6','resort':'#f59e0b','twn':'#16a34a'}[c['tier']]
    sort_rev = rev_bn if rev_bn is not None else -1e15
    sort_margin = margin if margin is not None else -1e15
    sort_roa = roa if roa is not None else -1e15
    sort_ta = ta_bn if ta_bn is not None else -1e15
    sort_eb = eb_margin if eb_margin is not None else -1e15
    sort_yoy = yoy if yoy is not None else -1e15
    search_blob = f'{t} {c["name"]} {c["sub"]} {c["loc"]} {c["parent"]}'.lower()
    table_rows.append(
        f'      <tr class="club-row" data-tier="{c["tier"]}" data-ticker="{t}" '
        f'data-search="{search_blob}" '
        f'data-rev="{sort_rev}" data-margin="{sort_margin}" data-roa="{sort_roa}" data-ta="{sort_ta}" data-ebmargin="{sort_eb}" data-yoy="{sort_yoy}" data-name="{c["name"]}">\n'
        f'        <td style="white-space:nowrap;"><span style="display:inline-block; width:3px; height:14px; background:{tier_color}; vertical-align:middle; margin-right:6px; border-radius:2px;"></span><a href="{t.lower()}.html" style="font-weight:700; color:var(--ops-ink); text-decoration:none;">{t}</a></td>\n'
        f'        <td><a href="{t.lower()}.html" style="color:var(--ops-ink); text-decoration:none;">{c["name"]}</a><br><span style="font-size:11px; color:var(--ops-muted);">{c["sub"]}</span></td>\n'
        f'        <td><span class="peer-tag peer-tag-{c["tier"]}" style="font-size:10px;">{c["tier_label"]}</span></td>\n'
        f'        <td style="font-size:12px;">{c["loc"]}</td>\n'
        f'        <td style="font-size:12px;">{c["holes"]}</td>\n'
        f'        <td style="font-size:12px;">{c["area"]}</td>\n'
        f'        <td class="num" style="font-weight:700;">{fmtBn(rev_bn)}</td>\n'
        f'        <td class="num">{fmtPct(yoy)}</td>\n'
        f'        <td class="num">{fmtPct(margin)}</td>\n'
        f'        <td class="num">{fmtPct(eb_margin)}</td>\n'
        f'        <td class="num">{fmtBn(ta_bn)}</td>\n'
        f'        <td class="num">{fmtPct(roa)}</td>\n'
        f'        <td class="num" style="color:var(--ops-green); font-weight:700;">Rp {c["golf_rev_fy24"]}</td>\n'
        f'      </tr>'
    )
table_section = '\n'.join(table_rows)

# ============================================================
# Tier summary statistics (FY2024, computed at build time)
# ============================================================
def median(xs):
    xs = sorted(x for x in xs if x is not None)
    n = len(xs)
    if n == 0: return None
    return xs[n//2] if n % 2 == 1 else (xs[n//2-1] + xs[n//2]) / 2

tier_stats = {}
for tier_key in ['pp','resort','twn']:
    tier_peers = [t for t in peers_sorted if clubs[t]['tier'] == tier_key]
    revs = []; margins = []; roas = []; tas = []
    for t in tier_peers:
        y24 = fin.get(t,{}).get('yearly',{}).get('2024',{})
        rev = y24.get('revenue'); np_ = y24.get('net_profit'); ta = y24.get('total_assets')
        if rev: revs.append(rev/1e9)
        if rev and np_: margins.append(np_/rev*100)
        if ta and np_: roas.append(np_/ta*100)
        if ta: tas.append(ta/1e9)
    tier_stats[tier_key] = {
        'count': len(tier_peers),
        'median_rev': median(revs),
        'median_margin': median(margins),
        'median_roa': median(roas),
        'median_ta': median(tas),
        'min_rev': min(revs) if revs else None,
        'max_rev': max(revs) if revs else None,
    }

tier_stats_json = json.dumps(tier_stats, ensure_ascii=False)

# ============================================================
# Top performer extraction (FY2024) — #1 per metric
# ============================================================
def top_performer(metric_fn, label, fmt_fn):
    best = None
    best_v = None
    for t in peers_sorted:
        v = metric_fn(t)
        if v is None: continue
        if best_v is None or v > best_v:
            best_v = v; best = t
    return { 'ticker': best, 'value': best_v, 'label': label, 'display': fmt_fn(best_v) if best_v is not None else '—' }

def get_y24(t, key):
    return fin.get(t,{}).get('yearly',{}).get('2024',{}).get(key)
def get_y23(t, key):
    return fin.get(t,{}).get('yearly',{}).get('2023',{}).get(key)

def fmt_bn_val(v):
    if v is None: return '—'
    if abs(v) >= 1e12: return f'Rp {v/1e12:.1f}T'
    return f'Rp {v/1e9:.0f}B'
def fmt_pct_val(v):
    if v is None: return '—'
    return f'{v:+.1f}%'

top_performers = {
    'rev': top_performer(lambda t: get_y24(t, 'revenue'), '최대 매출 (FY24)', fmt_bn_val),
    'margin': top_performer(lambda t: ((get_y24(t,'net_profit') or 0) / get_y24(t,'revenue') * 100) if get_y24(t,'revenue') and get_y24(t,'net_profit') is not None else None, '최고 순이익률', fmt_pct_val),
    'roa': top_performer(lambda t: ((get_y24(t,'net_profit') or 0) / get_y24(t,'total_assets') * 100) if get_y24(t,'total_assets') and get_y24(t,'net_profit') is not None else None, '최고 ROA', fmt_pct_val),
    'yoy': top_performer(lambda t: ((get_y24(t,'revenue') - get_y23(t,'revenue')) / get_y23(t,'revenue') * 100) if get_y24(t,'revenue') and get_y23(t,'revenue') else None, '최고 매출 YoY', fmt_pct_val),
}
top_performers_json = json.dumps(top_performers, ensure_ascii=False)

import datetime
build_date = datetime.date.today().strftime('%Y-%m-%d')

html = '''<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>클럽 — 인도네시아 골프 운영 벤치마크</title>
<link rel="icon" type="image/svg+xml" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Ccircle cx='32' cy='32' r='30' fill='%232D5016'/%3E%3Ccircle cx='32' cy='32' r='12' fill='%23F5F1E8'/%3E%3C/svg%3E" />
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Pretendard:wght@400;500;600;700&display=swap" rel="stylesheet" />
<link rel="stylesheet" href="../ops-style.css?v=20260512c53" />
<style>
  .club-card:hover { transform: translateY(-2px); box-shadow: 0 8px 24px rgba(0,0,0,0.08); }
  .club-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(360px, 1fr)); gap: 16px; margin-top: 20px; }
  .filter-bar { display: flex; gap: 10px; flex-wrap: wrap; margin: 12px 0; align-items:center; }
  .filter-btn { padding: 6px 14px; border: 1px solid var(--ops-line); background: var(--ops-surface); border-radius: 999px; font-size: 12.5px; font-weight: 600; cursor: pointer; color: var(--ops-ink-soft); }
  .filter-btn.active { background: var(--ops-green); color: white; border-color: var(--ops-green); }
  .control-bar { display:flex; gap:10px; flex-wrap:wrap; align-items:center; margin:14px 0 4px 0; }
  .control-bar input[type="search"] { padding:7px 12px; border:1px solid var(--ops-line); border-radius:6px; font-size:13px; min-width:240px; color:var(--ops-ink); background:var(--ops-surface); }
  .control-bar input[type="search"]:focus { outline:none; border-color:var(--ops-green); box-shadow:0 0 0 3px rgba(45,80,22,0.12); }
  .control-bar select { padding:7px 10px; border:1px solid var(--ops-line); border-radius:6px; font-size:12.5px; background:var(--ops-surface); color:var(--ops-ink); cursor:pointer; }
  .control-bar label { font-size:12px; font-weight:600; color:var(--ops-muted); }
  .view-toggle { display:inline-flex; border:1px solid var(--ops-line); border-radius:6px; overflow:hidden; }
  .view-toggle button { padding:7px 14px; border:none; background:var(--ops-surface); font-size:12.5px; font-weight:600; cursor:pointer; color:var(--ops-ink-soft); }
  .view-toggle button.active { background:var(--ops-green); color:white; }
  .view-toggle button + button { border-left:1px solid var(--ops-line); }
  .results-info { font-size:12px; color:var(--ops-muted); margin-left:auto; }
  .club-table { width:100%; border-collapse:collapse; font-size:13px; }
  .club-table thead th { text-align:left; padding:10px 8px; background:var(--ops-bg); border-bottom:2px solid var(--ops-line); font-size:11.5px; font-weight:700; color:var(--ops-muted); letter-spacing:0.04em; text-transform:uppercase; position:sticky; top:0; }
  .club-table thead th.num { text-align:right; }
  .club-table tbody td { padding:10px 8px; border-bottom:1px solid var(--ops-line); vertical-align:middle; }
  .club-table tbody td.num { text-align:right; white-space:nowrap; }
  .club-table tbody tr:hover { background:rgba(45,80,22,0.03); }
  .table-wrap { display:none; margin-top:20px; overflow-x:auto; background:var(--ops-surface); border:1px solid var(--ops-line); border-radius:10px; }
  .table-wrap.active { display:block; }
  .club-grid.hidden { display:none; }
  .empty-state { text-align:center; padding:60px 20px; color:var(--ops-muted); font-size:14px; display:none; }
  .empty-state.active { display:block; }
  @media (max-width: 720px) {
    .control-bar input[type="search"] { min-width:0; flex:1 1 100%; }
    .results-info { margin-left:0; flex:1 1 100%; text-align:right; }
  }
  /* Tier statistic summary cards */
  .tier-stats { display:grid; grid-template-columns:repeat(3, 1fr); gap:12px; margin:18px 0 4px 0; }
  .tier-stat-card { background:var(--ops-surface); border:1px solid var(--ops-line); border-radius:10px; padding:12px 14px; border-left:4px solid; transition:all 0.15s; cursor:pointer; }
  .tier-stat-card:hover { transform:translateY(-1px); box-shadow:0 4px 12px rgba(0,0,0,0.06); }
  .tier-stat-card.active-filter { background:rgba(45,80,22,0.04); box-shadow:0 0 0 2px var(--ops-green) inset; }
  .tier-stat-card.tier-pp     { border-left-color:#3b82f6; }
  .tier-stat-card.tier-resort { border-left-color:#f59e0b; }
  .tier-stat-card.tier-twn    { border-left-color:#16a34a; }
  .tier-stat-head { display:flex; justify-content:space-between; align-items:baseline; margin-bottom:6px; }
  .tier-stat-name { font-size:12.5px; font-weight:700; color:var(--ops-ink); }
  .tier-stat-count { font-size:11px; color:var(--ops-muted); font-weight:600; }
  .tier-stat-grid { display:grid; grid-template-columns:1fr 1fr; gap:4px 12px; font-size:11px; }
  .tier-stat-grid .lbl { color:var(--ops-muted); }
  .tier-stat-grid .val { color:var(--ops-ink); font-weight:700; text-align:right; font-variant-numeric:tabular-nums; }
  .tier-stat-grid .val.pos { color:#16a34a; }
  .tier-stat-grid .val.neg { color:#b91c1c; }
  .tier-stat-range { font-size:10.5px; color:var(--ops-muted); margin-top:6px; padding-top:6px; border-top:1px dashed var(--ops-line); }
  @media (max-width: 720px) {
    .tier-stats { grid-template-columns:1fr; }
  }
  /* Share / export buttons */
  .share-btn, .export-btn { padding:6px 12px; border:1px solid var(--ops-line); background:var(--ops-surface); border-radius:6px; font-size:12px; font-weight:600; cursor:pointer; color:var(--ops-ink-soft); }
  .share-btn:hover, .export-btn:hover { background:rgba(45,80,22,0.05); }
  .share-btn.copied, .export-btn.copied { background:#16a34a; color:white; border-color:#16a34a; }
  /* Theme toggle button (floats at top-right of hero) */
  .theme-toggle { position:absolute; top:14px; right:14px; padding:5px 10px; border:1px solid var(--ops-line); background:var(--ops-surface); border-radius:999px; font-size:13px; cursor:pointer; color:var(--ops-ink); z-index:10; }
  .theme-toggle:hover { background:rgba(45,80,22,0.06); }
  .ops-hero { position:relative; }
  /* Dark mode — invert key tokens; data viz colors preserved */
  body.theme-dark {
    --ops-bg:#0f172a;
    --ops-surface:#1e293b;
    --ops-ink:#e2e8f0;
    --ops-ink-soft:#cbd5e1;
    --ops-muted:#94a3b8;
    --ops-line:#334155;
    --ops-green:#22c55e;
  }
  body.theme-dark .club-card { background:#1e293b !important; }
  body.theme-dark .club-card .ops-ink, body.theme-dark .club-card span { color:inherit; }
  body.theme-dark .club-card div[style*="color:var(--ops-ink)"] { color:#e2e8f0 !important; }
  body.theme-dark .club-card div[style*="color:var(--ops-muted)"] { color:#94a3b8 !important; }
  body.theme-dark .club-card div[style*="color:var(--ops-ink-soft)"] { color:#cbd5e1 !important; }
  body.theme-dark .club-table tbody tr:hover { background:rgba(34,197,94,0.06); }
  body.theme-dark .club-table thead th { background:#0f172a; }
  body.theme-dark .table-wrap { background:#1e293b; }
  body.theme-dark .empty-state { color:#94a3b8; }
  body.theme-dark .tier-stat-card.active-filter { background:rgba(34,197,94,0.08); }
  /* Print: minimal, content-only, force table view, expand for paper */
  @media print {
    @page { size: A4 landscape; margin: 12mm; }
    body { background: white !important; color: black !important; }
    .ops-head, .ops-nav, .control-bar, .filter-bar, .tier-stats, .empty-state,
    .results-info, .share-btn, .theme-toggle, .ops-foot { display: none !important; }
    .ops-hero { padding: 0 0 8px 0; }
    .ops-hero .lede { display: none; }
    .ops-hero h1 { font-size: 18px; margin: 0 0 4px 0; }
    .ops-hero::after { content: '인쇄 시점: ' attr(data-print-date); display: block; font-size: 10px; color: #555; margin-top: 2px; }
    /* Force table-only view on print, hide cards (data already in table) */
    .club-grid { display: none !important; }
    .table-wrap { display: block !important; border: none; background: transparent; overflow: visible; }
    .club-table { font-size: 9.5px; width: 100%; }
    .club-table thead th { position: static !important; background: white !important; border-bottom: 1.5px solid black; }
    .club-table tbody td { border-bottom: 0.5px solid #ccc; padding: 4px 6px; }
    .club-table tbody tr:hover { background: white !important; }
    .peer-tag { border: 0.5px solid #888; padding: 0 4px; }
    a { color: black !important; text-decoration: none !important; }
  }
  /* Peer compare: checkbox on each card */
  .compare-check { position:absolute; top:8px; right:8px; width:22px; height:22px; cursor:pointer; opacity:0.55; transition:opacity 0.15s; z-index:2; }
  .compare-check:hover { opacity:1; }
  .compare-check input { width:100%; height:100%; margin:0; cursor:pointer; }
  .club-card { position:relative; }
  .club-row.compared, .club-card.compared { box-shadow:0 0 0 2px var(--ops-green) inset; }
  /* Sticky compare bar */
  .compare-bar { position:fixed; bottom:0; left:0; right:0; background:var(--ops-surface); border-top:3px solid var(--ops-green); box-shadow:0 -4px 16px rgba(0,0,0,0.10); padding:10px 16px; z-index:100; max-height:42vh; overflow-y:auto; transform:translateY(105%); transition:transform 0.25s ease; }
  .compare-bar.open { transform:translateY(0); }
  .compare-bar-head { display:flex; align-items:center; justify-content:space-between; gap:10px; margin-bottom:8px; }
  .compare-bar-title { font-size:13px; font-weight:700; color:var(--ops-ink); }
  .compare-bar-title .count { font-size:11.5px; color:var(--ops-muted); font-weight:600; margin-left:6px; }
  .compare-bar-clear { padding:4px 10px; border:1px solid var(--ops-line); background:var(--ops-surface); border-radius:5px; font-size:11.5px; cursor:pointer; color:var(--ops-ink-soft); }
  .compare-bar-clear:hover { background:rgba(185,28,28,0.08); color:#b91c1c; border-color:#b91c1c; }
  .compare-bar-export { padding:4px 10px; border:1px solid var(--ops-line); background:var(--ops-surface); border-radius:5px; font-size:11.5px; cursor:pointer; color:var(--ops-ink-soft); margin-right:6px; }
  .compare-bar-export:hover { background:rgba(45,80,22,0.06); color:var(--ops-green); border-color:var(--ops-green); }
  .compare-bar-export.copied { background:#16a34a; color:white; border-color:#16a34a; }
  /* Focus indicators (accessibility) */
  *:focus-visible { outline:2px solid var(--ops-green); outline-offset:2px; border-radius:3px; }
  .filter-btn:focus-visible, .tier-pill:focus-visible { outline-offset:1px; }
  .compare-grid { display:grid; grid-template-columns:repeat(auto-fit, minmax(140px, 1fr)); gap:8px; }
  .compare-col { background:var(--ops-bg); border:1px solid var(--ops-line); border-radius:6px; padding:8px 10px; position:relative; }
  .compare-col-head { display:flex; justify-content:space-between; align-items:center; margin-bottom:6px; }
  .compare-col-ticker { font-size:13px; font-weight:700; color:var(--ops-ink); }
  .compare-col-rm { background:none; border:none; color:var(--ops-muted); cursor:pointer; font-size:14px; padding:0; line-height:1; }
  .compare-col-rm:hover { color:#b91c1c; }
  .compare-col dl { margin:0; font-size:11px; }
  .compare-col dl div { display:flex; justify-content:space-between; padding:2px 0; border-bottom:1px dashed var(--ops-line); }
  .compare-col dl div:last-child { border-bottom:none; }
  .compare-col dt { color:var(--ops-muted); }
  .compare-col dd { margin:0; font-weight:700; color:var(--ops-ink); font-variant-numeric:tabular-nums; }
  body.theme-dark .compare-bar { background:#1e293b; border-top-color:#22c55e; }
  body.theme-dark .compare-col { background:#0f172a; }
  /* compare bar hidden on print */
  @media print {
    .compare-bar, .compare-check { display:none !important; }
  }
  /* Top performers row */
  .top-perf { display:grid; grid-template-columns:repeat(auto-fit, minmax(160px, 1fr)); gap:10px; margin:14px 0 4px 0; }
  .top-perf-card { background:linear-gradient(135deg, rgba(245,158,11,0.08), rgba(245,158,11,0.02)); border:1px solid var(--ops-line); border-left:3px solid #f59e0b; border-radius:8px; padding:8px 12px; }
  .top-perf-name { font-size:10.5px; font-weight:700; color:var(--ops-muted); letter-spacing:0.04em; text-transform:uppercase; margin-bottom:3px; }
  .top-perf-winner { font-size:14px; font-weight:700; color:var(--ops-ink); }
  .top-perf-winner a { color:inherit; text-decoration:none; }
  .top-perf-winner a:hover { color:var(--ops-green); }
  .top-perf-value { font-size:11.5px; color:#b45309; font-weight:700; font-variant-numeric:tabular-nums; }
  body.theme-dark .top-perf-card { background:linear-gradient(135deg, rgba(245,158,11,0.14), rgba(245,158,11,0.04)); }
  /* Data meta footer text */
  .data-meta { font-size:11px; color:var(--ops-muted); margin-top:6px; padding:6px 0 0 0; border-top:1px dashed var(--ops-line); }
  .data-meta strong { color:var(--ops-ink-soft); }
  .data-meta .sep { margin:0 8px; opacity:0.4; }
  @media print {
    .top-perf { display:none; }
    .data-meta { font-size:9px; }
  }
</style>
</head>
<body>
<header class="ops-head">
  <div class="ops-wrap ops-head-row">
    <a href="index.html" class="ops-brand">
      <div class="mark">⛳</div>
      <div>
        <div class="name">인도네시아 골프 운영 벤치마크</div>
        <div class="sub">13개 IDX 상장사</div>
      </div>
    </a>
    <nav class="ops-nav"><a href="index.html" class="active">⛳ 클럽</a><a href="../unit-economics.html">단위 경제</a><a href="../revenue.html">매출</a><a href="../cost-hr.html">비용</a><a href="../assets.html">시설</a><a href="../risk.html">위험</a><a href="../../../index.html" class="back">← 지도</a></nav>
  </div>
</header>

<section class="ops-hero">
  <button class="theme-toggle" id="theme-toggle" aria-label="다크모드 전환" title="다크/라이트 모드 전환 (단축키: d)">🌙</button>
  <div class="ops-wrap">
    <h1>13 클럽 일람</h1>
    <p class="lede">IDX 상장 13개 골프 운영사. 검색·정렬·뷰 전환으로 빠르게 비교. 카드/행 클릭으로 클럽 상세.</p>
    <div class="top-perf" id="top-perf"></div>
    <div class="tier-stats" id="tier-stats"></div>
    <div class="filter-bar" id="tier-filter">
      <button class="filter-btn active" data-filter="all">전체 (13)</button>
      <button class="filter-btn" data-filter="pp">🟦 Pure-play (2)</button>
      <button class="filter-btn" data-filter="resort">🟨 Resort (1)</button>
      <button class="filter-btn" data-filter="twn">🟩 Township (10)</button>
    </div>
    <div class="control-bar">
      <input type="search" id="club-search" placeholder="🔍 검색: 티커·이름·위치·모회사…" aria-label="클럽 검색" autocomplete="off">
      <label for="club-sort">정렬:</label>
      <select id="club-sort" aria-label="정렬 기준">
        <option value="tier">기본 (Tier 순)</option>
        <option value="rev-desc">매출 ↓</option>
        <option value="rev-asc">매출 ↑</option>
        <option value="yoy-desc">매출 YoY ↓</option>
        <option value="margin-desc">순이익률 ↓</option>
        <option value="margin-asc">순이익률 ↑</option>
        <option value="ebmargin-desc">EBITDA 마진 ↓</option>
        <option value="roa-desc">ROA ↓</option>
        <option value="roa-asc">ROA ↑</option>
        <option value="ta-desc">총자산 ↓</option>
        <option value="name-asc">이름 A→Z</option>
      </select>
      <div class="view-toggle" role="tablist" aria-label="뷰 전환">
        <button class="active" data-view="cards" role="tab" aria-selected="true">🃏 카드</button>
        <button data-view="table" role="tab" aria-selected="false">📋 표</button>
      </div>
      <button class="share-btn" id="share-btn" aria-label="현재 필터 링크 복사">🔗 링크 복사</button>
      <button class="export-btn" id="export-all-btn" aria-label="전체 데이터 CSV 다운로드">⬇ 전체 CSV</button>
      <div class="results-info" id="results-info">13 / 13 표시</div>
    </div>
    <div class="data-meta">
      📅 데이터 빌드: <strong>__BUILD_DATE__</strong>
      <span class="sep">·</span>
      재무 데이터: <strong>FY2020-FY2024 연결 P&amp;L · 대차대조표</strong>
      <span class="sep">·</span>
      출처: <strong>IDX 공시 (idx.co.id) · 연차보고서</strong>
    </div>
  </div>
</section>

<section class="ops-section">
  <div class="ops-wrap">
    <div class="club-grid" id="club-grid">
__CARDS__
    </div>
    <div class="table-wrap" id="club-table-wrap">
      <table class="club-table" id="club-table">
        <thead>
          <tr>
            <th>Ticker</th>
            <th>클럽명</th>
            <th>Tier</th>
            <th>위치</th>
            <th>홀</th>
            <th>면적</th>
            <th class="num">FY24 매출</th>
            <th class="num">매출 YoY</th>
            <th class="num">순이익률</th>
            <th class="num">EBITDA 마진</th>
            <th class="num">총자산</th>
            <th class="num">ROA</th>
            <th class="num">골프 매출 FY24</th>
          </tr>
        </thead>
        <tbody id="club-tbody">
__TABLE_ROWS__
        </tbody>
      </table>
    </div>
    <div class="empty-state" id="empty-state">🔍 검색 결과가 없습니다. 다른 키워드로 시도해보세요.</div>
  </div>
</section>

<aside class="compare-bar" id="compare-bar" aria-label="Peer 비교 패널">
  <div class="ops-wrap">
    <div class="compare-bar-head">
      <div class="compare-bar-title">⚖️ Peer 비교 <span class="count" id="compare-count">0/4</span></div>
      <div>
        <button class="compare-bar-export" id="compare-export" aria-label="비교 데이터를 클립보드로 복사">📋 비교 복사</button>
        <button class="compare-bar-clear" id="compare-clear" aria-label="비교 모두 해제">모두 해제</button>
      </div>
    </div>
    <div class="compare-grid" id="compare-grid"></div>
  </div>
</aside>

<footer class="ops-foot">
  <div class="ops-wrap">
    <p>Peer Group v2 · FY2024 audited · IDR.</p>
  </div>
</footer>

<script src="../operations.js?v=20260512c3" defer></script>
<script>
const TIER_STATS = __TIER_STATS__;
const TOP_PERFORMERS = __TOP_PERFORMERS__;

function renderTopPerf() {
  const root = document.getElementById('top-perf');
  if (!root) return;
  root.innerHTML = Object.values(TOP_PERFORMERS).map(p => {
    if (!p.ticker) return '';
    return `<div class="top-perf-card">
      <div class="top-perf-name">🏆 ${p.label}</div>
      <div class="top-perf-winner"><a href="${p.ticker.toLowerCase()}.html">${p.ticker}</a></div>
      <div class="top-perf-value">${p.display}</div>
    </div>`;
  }).join('');
}
const TIER_LABEL = { pp: '🟦 Pure-play', resort: '🟨 Resort', twn: '🟩 Township' };

function renderTierStats(activeTier) {
  const root = document.getElementById('tier-stats');
  const fmtBn = (v, dp) => {
    if (v === null || v === undefined) return '—';
    if (Math.abs(v) >= 1000) return (v/1000).toFixed(dp === undefined ? 2 : dp) + 'T';
    return v.toFixed(dp === undefined ? 0 : dp) + 'B';
  };
  const fmtPct = (v) => {
    if (v === null || v === undefined) return '—';
    const cls = v > 0 ? 'pos' : v < 0 ? 'neg' : '';
    return `<span class="val ${cls}">${v >= 0 ? '+' : ''}${v.toFixed(1)}%</span>`;
  };
  root.innerHTML = ['pp','resort','twn'].map(k => {
    const s = TIER_STATS[k];
    const isActive = activeTier === k;
    return `<div class="tier-stat-card tier-${k} ${isActive ? 'active-filter' : ''}" data-tier="${k}" role="button" tabindex="0" aria-pressed="${isActive}">
      <div class="tier-stat-head">
        <span class="tier-stat-name">${TIER_LABEL[k]}</span>
        <span class="tier-stat-count">N=${s.count}</span>
      </div>
      <div class="tier-stat-grid">
        <span class="lbl">중위 매출</span><span class="val">Rp ${fmtBn(s.median_rev, 1)}</span>
        <span class="lbl">중위 순이익률</span>${fmtPct(s.median_margin)}
        <span class="lbl">중위 ROA</span>${fmtPct(s.median_roa)}
        <span class="lbl">중위 총자산</span><span class="val">Rp ${fmtBn(s.median_ta, 1)}</span>
      </div>
      <div class="tier-stat-range">매출 범위: ${fmtBn(s.min_rev,1)} – ${fmtBn(s.max_rev,1)}</div>
    </div>`;
  }).join('');
  // Click handler on tier-stat-card to filter
  root.querySelectorAll('.tier-stat-card').forEach(card => {
    const handler = () => {
      const t = card.dataset.tier;
      // Toggle: if already active, clear filter; otherwise set
      const newTier = (state.tier === t) ? 'all' : t;
      setTier(newTier);
    };
    card.addEventListener('click', handler);
    card.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); handler(); } });
  });
}

function setTier(tier) {
  state.tier = tier;
  // Sync tier filter buttons
  document.querySelectorAll('#tier-filter .filter-btn').forEach(b => {
    b.classList.toggle('active', b.dataset.filter === tier);
  });
  applyState();
  renderTierStats(tier === 'all' ? null : tier);
  syncURL();
}

// URL state persistence — hash-based so it survives page refresh and can be shared
function readURL() {
  const hash = (location.hash || '').replace(/^#/, '');
  const params = new URLSearchParams(hash);
  return {
    tier: params.get('tier') || 'all',
    q: params.get('q') || '',
    sort: params.get('sort') || 'tier',
    view: params.get('view') || 'cards',
  };
}
function syncURL() {
  const parts = [];
  if (state.tier !== 'all') parts.push('tier=' + encodeURIComponent(state.tier));
  if (state.q) parts.push('q=' + encodeURIComponent(state.q));
  if (state.sort !== 'tier') parts.push('sort=' + encodeURIComponent(state.sort));
  if (state.view !== 'cards') parts.push('view=' + encodeURIComponent(state.view));
  const h = parts.join('&');
  history.replaceState(null, '', h ? '#' + h : location.pathname + location.search);
}

(function(){
  const tierButtons = document.querySelectorAll('#tier-filter .filter-btn');
  const viewButtons = document.querySelectorAll('.view-toggle button');
  const grid = document.getElementById('club-grid');
  const tableWrap = document.getElementById('club-table-wrap');
  const tbody = document.getElementById('club-tbody');
  const searchInput = document.getElementById('club-search');
  const sortSelect = document.getElementById('club-sort');
  const resultsInfo = document.getElementById('results-info');
  const emptyState = document.getElementById('empty-state');
  const shareBtn = document.getElementById('share-btn');

  // Read initial state from URL hash
  window.state = readURL();
  var state = window.state;

  // Preserve original DOM order for "tier" (default) sort
  const cardOriginalOrder = Array.from(grid.children).filter(el => el.classList.contains('club-card'));
  const rowOriginalOrder = Array.from(tbody.children).filter(el => el.classList.contains('club-row'));

  function sortElements(elems, mode) {
    if (mode === 'tier') return elems;  // original order
    const [key, dir] = mode.split('-');
    const sign = dir === 'desc' ? -1 : 1;
    return elems.slice().sort((a, b) => {
      if (key === 'name') {
        return sign * a.dataset.name.localeCompare(b.dataset.name, 'ko');
      }
      return sign * (parseFloat(a.dataset[key]) - parseFloat(b.dataset[key]));
    });
  }

  function applyState() {
    // 1) Sort
    const sortedCards = sortElements(cardOriginalOrder, state.sort);
    const sortedRows = sortElements(rowOriginalOrder, state.sort);
    // Re-attach in sorted order
    sortedCards.forEach(el => grid.appendChild(el));
    sortedRows.forEach(el => tbody.appendChild(el));

    // 2) Filter (tier + search) — apply to both views; track visible count
    const q = state.q.trim().toLowerCase();
    let visible = 0;
    const matches = (el) => {
      const tierOk = (state.tier === 'all' || el.dataset.tier === state.tier);
      const searchOk = (!q || el.dataset.search.includes(q));
      return tierOk && searchOk;
    };
    sortedCards.forEach(el => {
      const ok = matches(el);
      el.style.display = ok ? '' : 'none';
      if (ok) visible++;
    });
    sortedRows.forEach(el => {
      el.style.display = matches(el) ? '' : 'none';
    });
    resultsInfo.textContent = `${visible} / ${cardOriginalOrder.length} 표시`;
    emptyState.classList.toggle('active', visible === 0);

    // 3) View toggle
    if (state.view === 'cards') {
      grid.classList.remove('hidden');
      tableWrap.classList.remove('active');
    } else {
      grid.classList.add('hidden');
      tableWrap.classList.add('active');
    }
  }

  tierButtons.forEach(b => b.addEventListener('click', () => {
    tierButtons.forEach(x => x.classList.remove('active'));
    b.classList.add('active');
    state.tier = b.dataset.filter;
    applyState();
    renderTierStats(state.tier === 'all' ? null : state.tier);
    syncURL();
  }));

  viewButtons.forEach(b => b.addEventListener('click', () => {
    viewButtons.forEach(x => { x.classList.remove('active'); x.setAttribute('aria-selected','false'); });
    b.classList.add('active'); b.setAttribute('aria-selected','true');
    state.view = b.dataset.view;
    applyState();
    syncURL();
  }));

  searchInput.addEventListener('input', (e) => {
    state.q = e.target.value;
    applyState();
    syncURL();
  });

  sortSelect.addEventListener('change', (e) => {
    state.sort = e.target.value;
    applyState();
    syncURL();
  });

  shareBtn.addEventListener('click', async () => {
    try {
      await navigator.clipboard.writeText(location.href);
      const orig = shareBtn.textContent;
      shareBtn.textContent = '✓ 복사됨';
      shareBtn.classList.add('copied');
      setTimeout(() => { shareBtn.textContent = orig; shareBtn.classList.remove('copied'); }, 1600);
    } catch (err) {
      // Fallback: select-and-copy via temp input
      const ta = document.createElement('textarea');
      ta.value = location.href; document.body.appendChild(ta);
      ta.select(); document.execCommand('copy'); document.body.removeChild(ta);
      shareBtn.textContent = '✓ 복사됨'; shareBtn.classList.add('copied');
      setTimeout(() => { shareBtn.textContent = '🔗 링크 복사'; shareBtn.classList.remove('copied'); }, 1600);
    }
  });

  // Keyboard shortcuts: '/' focus search, 'g' grid, 't' table, 'Esc' clear search
  document.addEventListener('keydown', (e) => {
    if (e.target.matches('input,textarea,select')) {
      if (e.key === 'Escape' && e.target === searchInput) {
        searchInput.value = ''; state.q = ''; applyState(); syncURL(); e.target.blur();
      }
      return;
    }
    if (e.key === '/') { e.preventDefault(); searchInput.focus(); }
    else if (e.key === 'g') { document.querySelector('.view-toggle button[data-view="cards"]').click(); }
    else if (e.key === 't') { document.querySelector('.view-toggle button[data-view="table"]').click(); }
  });

  // Sync initial UI state from URL
  searchInput.value = state.q;
  sortSelect.value = state.sort;
  tierButtons.forEach(b => b.classList.toggle('active', b.dataset.filter === state.tier));
  viewButtons.forEach(b => {
    const a = b.dataset.view === state.view;
    b.classList.toggle('active', a); b.setAttribute('aria-selected', a ? 'true' : 'false');
  });

  // Dark mode toggle (persists in localStorage, follows system pref + auto-update if user hasn't chosen)
  const themeBtn = document.getElementById('theme-toggle');
  function applyTheme(theme) {
    if (theme === 'dark') { document.body.classList.add('theme-dark'); themeBtn.textContent = '☀️'; themeBtn.setAttribute('title','라이트 모드로 전환 (d)'); }
    else                  { document.body.classList.remove('theme-dark'); themeBtn.textContent = '🌙'; themeBtn.setAttribute('title','다크 모드로 전환 (d)'); }
  }
  const savedTheme = localStorage.getItem('ops-theme');
  const mqlDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)');
  applyTheme(savedTheme || (mqlDark && mqlDark.matches ? 'dark' : 'light'));
  // Auto-follow system pref changes while user hasn't explicitly chosen
  if (mqlDark && mqlDark.addEventListener) {
    mqlDark.addEventListener('change', (e) => {
      if (!localStorage.getItem('ops-theme')) applyTheme(e.matches ? 'dark' : 'light');
    });
  }
  themeBtn.addEventListener('click', () => {
    const newT = document.body.classList.contains('theme-dark') ? 'light' : 'dark';
    localStorage.setItem('ops-theme', newT);
    applyTheme(newT);
  });
  // 'd' key shortcut
  document.addEventListener('keydown', (e) => {
    if (e.target.matches('input,textarea,select')) return;
    if (e.key === 'd') { themeBtn.click(); }
  });

  renderTopPerf();
  renderTierStats(state.tier === 'all' ? null : state.tier);
  // Annotate hero with print-date for the @media print rule
  const hero = document.querySelector('.ops-hero');
  if (hero) {
    const d = new Date();
    hero.setAttribute('data-print-date', `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`);
  }

  // Compare mode — max 4 peers, sticky bottom bar
  const MAX_COMPARE = 4;
  const cmpBar = document.getElementById('compare-bar');
  const cmpGrid = document.getElementById('compare-grid');
  const cmpCount = document.getElementById('compare-count');
  const cmpClear = document.getElementById('compare-clear');
  const compared = new Set();

  function cardDataFor(ticker) {
    const card = grid.querySelector(`.club-card[data-ticker="${ticker}"]`);
    if (!card) return null;
    const num = v => (v === '' || v === undefined || v === null) ? null : parseFloat(v);
    const fmtB = v => { if (v === null || isNaN(v) || v <= -1e14) return '—'; if (Math.abs(v) >= 1000) return (v/1000).toFixed(2)+'T'; return v.toFixed(0)+'B'; };
    const fmtP = v => { if (v === null || isNaN(v) || v <= -1e14) return '—'; const c = v > 0 ? '#16a34a' : v < 0 ? '#b91c1c' : '#666'; return `<span style="color:${c};">${v >= 0 ? '+' : ''}${v.toFixed(1)}%</span>`; };
    // Clone the existing 5Y revenue sparkline SVG from the card
    const sparkSvg = card.querySelector('svg[aria-label="5년 매출 추이"]');
    return {
      ticker,
      name: card.dataset.name,
      tierLabel: card.dataset.tierLabel,
      tier: card.dataset.tier,
      loc: card.dataset.loc,
      rev: fmtB(num(card.dataset.rev)),
      yoy: fmtP(num(card.dataset.yoy)),
      margin: fmtP(num(card.dataset.margin)),
      ebmargin: fmtP(num(card.dataset.ebmargin)),
      ta: fmtB(num(card.dataset.ta)),
      roa: fmtP(num(card.dataset.roa)),
      sparkHTML: sparkSvg ? sparkSvg.outerHTML : '',
    };
  }
  function updateRowStates(ticker, on) {
    grid.querySelectorAll(`.club-card[data-ticker="${ticker}"]`).forEach(c => c.classList.toggle('compared', on));
    tbody.querySelectorAll(`.club-row[data-ticker="${ticker}"]`).forEach(r => r.classList.toggle('compared', on));
  }
  function renderCompare() {
    cmpCount.textContent = `${compared.size}/${MAX_COMPARE}`;
    if (compared.size === 0) {
      cmpBar.classList.remove('open');
      cmpGrid.innerHTML = '';
      return;
    }
    cmpBar.classList.add('open');
    const cols = Array.from(compared).map(t => {
      const d = cardDataFor(t);
      if (!d) return '';
      return `<div class="compare-col">
        <div class="compare-col-head">
          <a class="compare-col-ticker" href="${t.toLowerCase()}.html" style="text-decoration:none; color:inherit;">${t}</a>
          <button class="compare-col-rm" data-ticker="${t}" title="제거">✕</button>
        </div>
        <div style="font-size:10.5px; color:var(--ops-muted); margin-bottom:4px;">${d.tierLabel} · ${d.loc}</div>
        <div style="text-align:center; margin-bottom:4px;">${d.sparkHTML}</div>
        <dl>
          <div><dt>FY24 매출</dt><dd>${d.rev}</dd></div>
          <div><dt>매출 YoY</dt><dd>${d.yoy}</dd></div>
          <div><dt>순이익률</dt><dd>${d.margin}</dd></div>
          <div><dt>EBITDA 마진</dt><dd>${d.ebmargin}</dd></div>
          <div><dt>총자산</dt><dd>${d.ta}</dd></div>
          <div><dt>ROA</dt><dd>${d.roa}</dd></div>
        </dl>
      </div>`;
    }).join('');
    cmpGrid.innerHTML = cols;
    cmpGrid.querySelectorAll('.compare-col-rm').forEach(btn => {
      btn.addEventListener('click', () => toggleCompare(btn.dataset.ticker, false));
    });
  }
  function saveCompare() {
    try { localStorage.setItem('clubs-compare', JSON.stringify(Array.from(compared))); } catch (e) {}
  }
  function toggleCompare(ticker, on) {
    if (on === undefined) on = !compared.has(ticker);
    if (on) {
      if (compared.size >= MAX_COMPARE) {
        // Pop oldest
        const first = compared.values().next().value;
        compared.delete(first); updateRowStates(first, false);
        grid.querySelectorAll(`.cmp-cb[data-ticker="${first}"]`).forEach(cb => cb.checked = false);
      }
      compared.add(ticker);
    } else {
      compared.delete(ticker);
    }
    updateRowStates(ticker, compared.has(ticker));
    grid.querySelectorAll(`.cmp-cb[data-ticker="${ticker}"]`).forEach(cb => cb.checked = compared.has(ticker));
    renderCompare();
    saveCompare();
  }
  // Restore from localStorage
  try {
    const saved = JSON.parse(localStorage.getItem('clubs-compare') || '[]');
    if (Array.isArray(saved)) {
      saved.slice(0, MAX_COMPARE).forEach(t => {
        // Only re-add if peer exists in grid
        if (grid.querySelector(`.club-card[data-ticker="${t}"]`)) {
          compared.add(t);
          updateRowStates(t, true);
          grid.querySelectorAll(`.cmp-cb[data-ticker="${t}"]`).forEach(cb => cb.checked = true);
        }
      });
      if (compared.size > 0) renderCompare();
    }
  } catch (e) {}
  // Wire card checkboxes (label/input click triggers via JS to bypass the parent <a>)
  grid.querySelectorAll('.compare-check').forEach(lbl => {
    const cb = lbl.querySelector('.cmp-cb');
    lbl.addEventListener('click', (e) => {
      e.preventDefault(); e.stopPropagation();
      toggleCompare(cb.dataset.ticker);
    });
  });
  cmpClear.addEventListener('click', () => {
    Array.from(compared).forEach(t => toggleCompare(t, false));
  });
  // Compare panel CSV/TSV export to clipboard
  const cmpExport = document.getElementById('compare-export');
  if (cmpExport) cmpExport.addEventListener('click', async () => {
    if (compared.size === 0) return;
    const headers = ['Ticker','Name','Tier','Location','FY24매출','매출YoY','순이익률','EBITDA마진','총자산','ROA'];
    const lines = [headers.join('\t')];
    Array.from(compared).forEach(t => {
      const card = grid.querySelector(`.club-card[data-ticker="${t}"]`);
      if (!card) return;
      const stripHtml = s => s.replace(/<[^>]+>/g, '').trim();
      const num = v => (v === '' || v === undefined || v === null || parseFloat(v) <= -1e14) ? '' : v;
      lines.push([
        t,
        card.dataset.name || '',
        (card.dataset.tierLabel || '').replace(/^[^ ]+ /,''),
        card.dataset.loc || '',
        num(card.dataset.rev),
        num(card.dataset.yoy),
        num(card.dataset.margin),
        num(card.dataset.ebmargin),
        num(card.dataset.ta),
        num(card.dataset.roa),
      ].join('\t'));
    });
    const tsv = lines.join('\n');
    try { await navigator.clipboard.writeText(tsv); }
    catch (err) {
      const ta = document.createElement('textarea'); ta.value = tsv; document.body.appendChild(ta); ta.select(); document.execCommand('copy'); document.body.removeChild(ta);
    }
    cmpExport.textContent = '✓ 복사됨'; cmpExport.classList.add('copied');
    setTimeout(() => { cmpExport.textContent = '📋 비교 복사'; cmpExport.classList.remove('copied'); }, 1600);
  });
  // Keyboard arrow nav for filter pills
  const filterPills = Array.from(tierButtons);
  filterPills.forEach((p, i) => {
    p.setAttribute('tabindex', '0');
    p.addEventListener('keydown', (e) => {
      if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') {
        e.preventDefault();
        const next = e.key === 'ArrowRight' ? (i + 1) % filterPills.length : (i - 1 + filterPills.length) % filterPills.length;
        filterPills[next].focus();
        filterPills[next].click();
      }
    });
  });
  // Full 13-peer CSV export
  const exportAllBtn = document.getElementById('export-all-btn');
  if (exportAllBtn) exportAllBtn.addEventListener('click', (e) => {
    const headers = ['Ticker','Name','Tier','Location','Holes','Area','FY24Rev(B)','매출YoY(%)','순이익률(%)','EBITDA마진(%)','총자산(B)','ROA(%)'];
    const lines = [headers.join(',')];
    cardOriginalOrder.forEach(card => {
      const csvEsc = s => { const v = String(s || ''); return v.includes(',') || v.includes('"') ? '"' + v.replace(/"/g,'""') + '"' : v; };
      const num = v => (v === '' || v === undefined || v === null || parseFloat(v) <= -1e14) ? '' : v;
      const holes = card.querySelector('div[style*="홀"]')?.parentElement?.textContent?.replace(/홀/,'').trim() || '';
      lines.push([
        csvEsc(card.dataset.ticker),
        csvEsc(card.dataset.name),
        csvEsc((card.dataset.tierLabel || '').replace(/^[^ ]+ /,'')),
        csvEsc(card.dataset.loc),
        '', '',
        num(card.dataset.rev), num(card.dataset.yoy), num(card.dataset.margin),
        num(card.dataset.ebmargin), num(card.dataset.ta), num(card.dataset.roa),
      ].join(','));
    });
    const csv = '﻿' + lines.join('\n');
    const blob = new Blob([csv], { type:'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url; a.download = 'clubs_fy2024.csv';
    document.body.appendChild(a); a.click(); document.body.removeChild(a); URL.revokeObjectURL(url);
    const orig = exportAllBtn.textContent; exportAllBtn.textContent = '✓ 다운로드'; exportAllBtn.classList.add('copied');
    setTimeout(() => { exportAllBtn.textContent = orig; exportAllBtn.classList.remove('copied'); }, 1600);
  });

  applyState();
})();
</script>
</body>
</html>
'''

html = html.replace('__CARDS__', cards_section)
html = html.replace('__TABLE_ROWS__', table_section)
html = html.replace('__TIER_STATS__', tier_stats_json)
html = html.replace('__TOP_PERFORMERS__', top_performers_json)
html = html.replace('__BUILD_DATE__', build_date)
with open('clubs/index.html','w',encoding='utf-8') as f:
    f.write(html)
print(f'clubs/index.html: {os.path.getsize("clubs/index.html")/1024:.1f} KB')
