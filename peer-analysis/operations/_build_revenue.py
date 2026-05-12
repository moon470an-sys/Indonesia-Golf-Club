"""Build revenue.html — year selector + 13-peer comparison + line breakdowns."""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import json
import os

clubs = json.load(open('data/_clubs_meta.json','r',encoding='utf-8'))
d5y = json.load(open('../../data/company_financials_5y.json','r',encoding='utf-8'))
fin = {c['ticker']: c for c in d5y['companies'] if 'ticker' in c}
peers_v2 = ['DMIG','PIPG','GOLF','MDLN','KIJA','SMDM','KPIG','SMRA','BSDE','CTRA','ELTY','LPKR','PWON']
def torder(t): return {'pp':1,'resort':2,'twn':3}.get(clubs[t]['tier'], 9)

notes = {}
for t in peers_v2:
    path = f'data/{t.lower()}_notes.json'
    if os.path.exists(path):
        notes[t] = json.load(open(path,'r',encoding='utf-8'))

# Golf segment revenue per year (IDR)
GOLF_SEG_REV = {
    'DMIG': 'pure-play',  # = group revenue all years
    'PIPG': 'pure-play',
    'GOLF': {'2023': 94436855876, '2024': 93042072774},
    'MDLN': {'2024': 74400000000},  # placeholder; check segment notes
    'KIJA': {'2024': 85019000000},
    'SMDM': {'2022': None, '2023': None, '2024': 63282214554},
    'SMRA': {'2024': 66672127000},  # FY2024_comparative * 1000
}

# Build PEER_DATA payload for JS
peers_sorted = sorted(peers_v2, key=lambda t: (torder(t), t))

peer_data = {}
for t in peers_sorted:
    c = clubs[t]
    cy = fin.get(t,{}).get('yearly',{})
    yearly = {}
    for y in ['2020','2021','2022','2023','2024']:
        yy = cy.get(y, {})
        yearly[y] = {'rev': yy.get('revenue')}
    # Golf seg
    seg = GOLF_SEG_REV.get(t)
    if seg == 'pure-play':
        golf_seg = {y: yearly[y]['rev'] for y in yearly}
    elif isinstance(seg, dict):
        golf_seg = seg
    else:
        golf_seg = {}
    peer_data[t] = {
        'name': c['name'],
        'tier': c['tier'],
        'tier_label': c['tier_label'],
        'yearly': yearly,
        'golf_seg': golf_seg,
        'pure_play': (seg == 'pure-play'),
    }

peer_data_json = json.dumps(peer_data, ensure_ascii=False)

# ============================================================
# Line detail tables — multi-year, selected year column gets "yr-{year}" class for JS highlight
# ============================================================
def fmt_bn_py(v):
    if v is None: return '—'
    if abs(v) >= 1e12: return f'{v/1e12:,.1f}T'
    if abs(v) >= 1e9: return f'{v/1e9:,.1f}B'
    if abs(v) >= 1e6: return f'{v/1e6:,.1f}M'
    return f'{v:,.0f}'
def fmt_pct_py(v):
    if v is None: return '—'
    return f'{v:,.1f}%'

def build_line_table(title, subtitle, lines_data, year_cols, tier_emoji):
    """lines_data: list of dicts with id_label/en_label/FY2022/FY2023/FY2024 keys.
       year_cols: list of years to render columns for, e.g. ['FY2022','FY2023','FY2024']."""
    head_cells = ''.join(f'<th class="num yr-{y[-4:]}">{y}</th>' for y in year_cols)
    head_cells += '<th class="num">FY24 비중</th><th class="num">YoY</th>'
    rows = []
    # total for share calc
    total_year = lines_data['total'].get('FY2024') if 'total' in lines_data else None
    for ln in lines_data['lines']:
        cells = ''
        for y in year_cols:
            v = ln.get(y)
            cells += f'<td class="num yr-{y[-4:]}">{fmt_bn_py(v)}</td>'
        share = (ln.get('FY2024')/total_year*100) if (total_year and ln.get('FY2024')) else None
        y23 = ln.get('FY2023'); y24 = ln.get('FY2024')
        yoy = ((y24-y23)/y23*100) if (y23 and y24) else None
        yoy_html = '—'
        if yoy is not None:
            col = '#16a34a' if yoy>0 else '#b91c1c'
            yoy_html = f'<span style="color:{col}; font-weight:700;">{yoy:+.1f}%</span>'
        rows.append(f'''            <tr>
              <td>{ln["id_label"]}<br><span style="color:var(--ops-muted); font-size:11px;">{ln.get("en_label","—")}</span></td>
              {cells}
              <td class="num">{fmt_pct_py(share)}</td>
              <td class="num">{yoy_html}</td>
            </tr>''')
    # total row
    tot = lines_data.get('total',{})
    total_cells = ''.join(f'<td class="num yr-{y[-4:]}">{fmt_bn_py(tot.get(y))}</td>' for y in year_cols)
    yoy_t = ((tot.get('FY2024')-tot.get('FY2023'))/tot.get('FY2023')*100) if tot.get('FY2023') else None
    yoy_t_html = '—'
    if yoy_t is not None:
        col = '#16a34a' if yoy_t>0 else '#b91c1c'
        yoy_t_html = f'<span style="color:{col}; font-weight:700;">{yoy_t:+.1f}%</span>'
    rows.append(f'''            <tr style="background:rgba(45,80,22,0.06); font-weight:700;">
              <td>합계</td>
              {total_cells}
              <td class="num">100.0%</td>
              <td class="num">{yoy_t_html}</td>
            </tr>''')
    return f'''      <div style="margin-bottom:32px;">
        <h3 style="font-size:16px; margin:0 0 10px 0;">{tier_emoji} {title}</h3>
        <p style="font-size:12px; color:var(--ops-muted); margin:0 0 8px 0;">{subtitle}</p>
        <div class="tbl-card scroll-x">
          <table class="ops-tbl">
            <thead><tr><th>매출 라인</th>{head_cells}</tr></thead>
            <tbody>
{chr(10).join(rows)}
            </tbody>
          </table>
        </div>
      </div>'''

# DMIG revenue (FY22-FY24, 7 lines)
dmig_table = build_line_table(
    'DMIG · 매출 라인 (Note 23)',
    'Pure-play — 골프장·F&B·회원권·스폰서·임대 등 7 라인',
    notes['DMIG']['revenue_note'],
    ['FY2022','FY2023','FY2024'],
    '🟦'
)

# PIPG revenue_27 (FY23-FY24, 11 lines)
pipg_table = build_line_table(
    'PIPG · 매출 라인 (Note 27)',
    'Pure-play — 골프·F&B·회원권·아카데미·드라이빙·임대 등 11 라인',
    notes['PIPG']['revenue_note_27'],
    ['FY2023','FY2024'],
    '🟦'
)

# Tab 2 panels = pp_section
pp_section = dmig_table + '\n' + pipg_table

# Segment tables for tab 3
seg_section_parts = []

# GOLF (4 sub-segments, FY23-FY24)
g = notes['GOLF']['revenue_note_29']
seg_section_parts.append(build_line_table(
    'GOLF · 사업부별 매출 (Note 29)',
    'Bali 리조트 — 골프·부동산·F&B·기타 사업부 분해',
    g['by_operations'],
    ['FY2023','FY2024'],
    '🟨'
))

# MDLN revenue_25 (11 lines, FY23-FY24)
seg_section_parts.append(build_line_table(
    'MDLN · 그룹 매출 라인 (Note 25)',
    'Township — 토지·주택·아파트·골프·F&B 등 11 라인 (골프 비중 작음)',
    notes['MDLN']['revenue_note_25'],
    ['FY2023','FY2024'],
    '🟩'
))

# KPIG revenue_31 (4 lines, FY23-FY24)
seg_section_parts.append(build_line_table(
    'KPIG · 그룹 매출 라인 (Note 31)',
    'Township — 호텔·리조트·골프 번들 / 부동산관리 / 임대 / 기타',
    notes['KPIG']['revenue_note_31'],
    ['FY2023','FY2024'],
    '🟩'
))

# Tier-3 segment summary (KIJA·SMDM·SMRA)
seg_summary_rows = []
kg = notes['KIJA']['segment_info_note_34']['golf_segment_FY2024']
seg_summary_rows.append(f'''            <tr>
              <td class="peer"><a href="clubs/kija.html" style="color:var(--ops-ink); font-weight:700; text-decoration:none;">KIJA</a><span class="peer-tag peer-tag-twn">🟩 Township</span></td>
              <td>Golf 세그먼트 (Jababeka + Borobudur)</td>
              <td class="num">FY2024</td>
              <td class="num"><strong>{fmt_bn_py(kg["revenue"]*1e6)}</strong></td>
              <td class="num">{fmt_bn_py(kg["cogs"]*1e6)}</td>
              <td class="num">{fmt_bn_py(kg["gross_profit"]*1e6)}</td>
              <td class="num">{fmt_pct_py(kg["gross_profit"]/kg["revenue"]*100)}</td>
            </tr>''')
sg = notes['SMDM']['segment_info_note_29']['FY2024']['Golf dan Country Club']
sg_cogs = abs(sg.get('cogs',0)) if sg.get('cogs') is not None else None
seg_summary_rows.append(f'''            <tr>
              <td class="peer"><a href="clubs/smdm.html" style="color:var(--ops-ink); font-weight:700; text-decoration:none;">SMDM</a><span class="peer-tag peer-tag-twn">🟩 Township</span></td>
              <td>Golf dan Country Club (Rancamaya)</td>
              <td class="num">FY2024</td>
              <td class="num"><strong>{fmt_bn_py(sg["revenue"])}</strong></td>
              <td class="num">{fmt_bn_py(sg_cogs)}</td>
              <td class="num">{fmt_bn_py(sg["gross_profit"])}</td>
              <td class="num">{fmt_pct_py(sg["gross_profit"]/sg["revenue"]*100)}</td>
            </tr>''')
sm = notes['SMRA']['revenue_note_31']['Rekreasi_Leisure']
sm_cogs_d = notes['SMRA']['cogs_note_32']['Rekreasi_Leisure_COGS']
sm_rev = sm.get('FY2024_comparative',0)*1000
sm_cogs = sm_cogs_d.get('FY2024_comparative',0)*1000
sm_gp = sm_rev - sm_cogs
seg_summary_rows.append(f'''            <tr>
              <td class="peer"><a href="clubs/smra.html" style="color:var(--ops-ink); font-weight:700; text-decoration:none;">SMRA</a><span class="peer-tag peer-tag-twn">🟩 Township</span></td>
              <td>Rekreasi/Leisure (Gading Raya 포함)</td>
              <td class="num">FY2024</td>
              <td class="num"><strong>{fmt_bn_py(sm_rev)}</strong></td>
              <td class="num">{fmt_bn_py(sm_cogs)}</td>
              <td class="num">{fmt_bn_py(sm_gp)}</td>
              <td class="num">{fmt_pct_py(sm_gp/sm_rev*100) if sm_rev else "—"}</td>
            </tr>''')
seg_section_parts.append(f'''      <div style="margin-bottom:32px;">
        <h3 style="font-size:16px; margin:0 0 10px 0;">🟩 Tier-3 골프 세그먼트 요약 (FY2024)</h3>
        <p style="font-size:12px; color:var(--ops-muted); margin:0 0 8px 0;">KIJA·SMDM·SMRA — segment note 기반 골프 부문 단년 공시</p>
        <div class="tbl-card scroll-x">
          <table class="ops-tbl">
            <thead><tr><th>Peer</th><th>세그먼트</th><th class="num">연도</th><th class="num">매출</th><th class="num">매출원가</th><th class="num">매출총이익</th><th class="num">GP 마진</th></tr></thead>
            <tbody>
{chr(10).join(seg_summary_rows)}
            </tbody>
          </table>
        </div>
      </div>''')

seg_section = '\n'.join(seg_section_parts)

html = '''<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>매출 — 인도네시아 골프 운영 벤치마크</title>
<link rel="icon" type="image/svg+xml" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Ccircle cx='32' cy='32' r='30' fill='%232D5016'/%3E%3Ccircle cx='32' cy='32' r='12' fill='%23F5F1E8'/%3E%3C/svg%3E" />
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Pretendard:wght@400;500;600;700&display=swap" rel="stylesheet" />
<link rel="stylesheet" href="ops-style.css?v=20260512c54" />
<style>
  .year-bar { display:flex; align-items:center; gap:10px; flex-wrap:wrap; margin:14px 0 4px 0; }
  .year-bar label { font-size:13px; font-weight:600; color:var(--ops-ink-soft); }
  .year-btn { padding:6px 14px; border:1px solid var(--ops-line); background:var(--ops-surface); border-radius:6px; font-size:12.5px; font-weight:600; cursor:pointer; color:var(--ops-ink-soft); }
  .year-btn.active { background:var(--ops-green); color:white; border-color:var(--ops-green); }
  .rev-tab-bar { display:flex; gap:6px; flex-wrap:wrap; margin:16px 0 24px 0; border-bottom:2px solid var(--ops-line); }
  .rev-tab { padding:10px 18px; cursor:pointer; font-size:13px; font-weight:600; color:var(--ops-ink-soft); border-bottom:3px solid transparent; margin-bottom:-2px; }
  .rev-tab.active { color:var(--ops-green); border-bottom-color:var(--ops-green); }
  .rev-panel { display:none; }
  .rev-panel.active { display:block; }
  /* Selected-year column highlighting in line detail tables */
  .yr-hl { background:rgba(245,158,11,0.10); font-weight:700; }
  /* Sparklines */
  .spark { display:inline-block; vertical-align:middle; }
  .spark-line { fill:none; stroke-width:1.6; }
  .spark-area { opacity:0.18; }
  .spark-dot { stroke:white; stroke-width:1; }
  .spark-current { stroke:#f59e0b; stroke-width:2; fill:#f59e0b; }
  /* CAGR colour-coding */
  .cagr-pos { color:#16a34a; font-weight:700; }
  .cagr-neg { color:#b91c1c; font-weight:700; }
  .cagr-zero { color:#666; }
  /* Term hint pill */
  .tip { cursor:help; font-size:9px; vertical-align:super; opacity:0.7; }
  /* Peak position pill */
  .peak-pill { display:inline-block; padding:1px 6px; border-radius:999px; font-size:11px; font-weight:700; font-variant-numeric:tabular-nums; }
  .peak-pill.at-peak  { background:rgba(22,163,74,0.15); color:#16a34a; }
  .peak-pill.near     { background:rgba(245,158,11,0.15); color:#b45309; }
  .peak-pill.down     { background:rgba(185,28,28,0.12); color:#b91c1c; }
  /* Top performer cards (consistent with clubs/unit-econ) */
  .top-perf { display:grid; grid-template-columns:repeat(auto-fit, minmax(170px, 1fr)); gap:10px; margin:14px 0 10px 0; }
  .top-perf-card { background:linear-gradient(135deg, rgba(245,158,11,0.08), rgba(245,158,11,0.02)); border:1px solid var(--ops-line); border-left:3px solid #f59e0b; border-radius:8px; padding:8px 12px; }
  .top-perf-name { font-size:10.5px; font-weight:700; color:var(--ops-muted); letter-spacing:0.04em; text-transform:uppercase; margin-bottom:3px; }
  .top-perf-winner { font-size:14px; font-weight:700; color:var(--ops-ink); }
  .top-perf-winner a { color:inherit; text-decoration:none; }
  .top-perf-value { font-size:11.5px; color:#b45309; font-weight:700; font-variant-numeric:tabular-nums; }
  body.theme-dark .top-perf-card { background:linear-gradient(135deg, rgba(245,158,11,0.14), rgba(245,158,11,0.04)); }
  .data-meta { font-size:11px; color:var(--ops-muted); margin-top:6px; padding:6px 0 0 0; border-top:1px dashed var(--ops-line); }
  .data-meta strong { color:var(--ops-ink-soft); }
  .data-meta .sep { margin:0 8px; opacity:0.4; }
  @media print { .top-perf { display:none; } .data-meta { font-size:9px; } }
  /* Accessibility */
  *:focus-visible { outline:2px solid var(--ops-green); outline-offset:2px; border-radius:3px; }
  .year-btn:focus-visible, .rev-tab:focus-visible, .trend-mode-toggle button:focus-visible { outline-offset:1px; }
  .skip-link { position:absolute; left:-1000px; top:8px; padding:6px 12px; background:var(--ops-green); color:white; border-radius:6px; font-weight:700; z-index:200; text-decoration:none; }
  .skip-link:focus { left:8px; }
  /* Help overlay */
  .help-overlay { position:fixed; inset:0; background:rgba(0,0,0,0.55); backdrop-filter:blur(2px); display:none; align-items:center; justify-content:center; z-index:300; padding:20px; }
  .help-overlay.open { display:flex; }
  .help-panel { background:var(--ops-surface); border-radius:12px; padding:24px 28px; max-width:520px; width:100%; max-height:80vh; overflow:auto; box-shadow:0 20px 40px rgba(0,0,0,0.25); }
  .help-panel h2 { margin:0 0 12px 0; font-size:18px; color:var(--ops-ink); }
  .help-panel .help-row { display:grid; grid-template-columns:1fr 110px; gap:10px; align-items:center; padding:7px 0; border-bottom:1px solid var(--ops-line); font-size:13px; color:var(--ops-ink-soft); }
  .help-panel .help-row:last-child { border-bottom:none; }
  .help-panel .help-row kbd { display:inline-block; padding:2px 8px; background:var(--ops-bg); border:1px solid var(--ops-line); border-radius:4px; font-family:monospace; font-size:11.5px; color:var(--ops-ink); font-weight:700; text-align:center; }
  .help-panel .close-btn { float:right; padding:4px 10px; border:1px solid var(--ops-line); background:var(--ops-surface); border-radius:5px; font-size:12px; cursor:pointer; color:var(--ops-ink-soft); margin-top:-8px; }
  body.theme-dark .help-panel { background:#1e293b; }
  body.theme-dark .help-panel .help-row kbd { background:#0f172a; }
  .help-fab { position:fixed; bottom:18px; right:18px; width:38px; height:38px; border-radius:50%; background:var(--ops-surface); border:1px solid var(--ops-line); cursor:pointer; font-size:16px; color:var(--ops-ink-soft); z-index:50; box-shadow:0 2px 8px rgba(0,0,0,0.10); }
  .help-fab:hover { background:rgba(45,80,22,0.06); color:var(--ops-ink); }
  @media print { .help-fab, .help-overlay { display:none !important; } }
  /* YoY heatmap matrix */
  .yoy-matrix { width:100%; border-collapse:separate; border-spacing:1px; background:var(--ops-line); font-size:12px; }
  .yoy-matrix th, .yoy-matrix td { background:var(--ops-surface); padding:8px 6px; }
  .yoy-matrix thead th { font-size:11px; font-weight:700; color:var(--ops-muted); letter-spacing:0.04em; text-transform:uppercase; }
  .yoy-matrix tbody td { text-align:center; font-variant-numeric:tabular-nums; }
  .yoy-matrix tbody td.peer-cell { text-align:left; font-weight:700; }
  .yoy-cell { color:var(--ops-ink); font-weight:600; }
  /* Action bar */
  .action-bar { display:flex; gap:8px; flex-wrap:wrap; align-items:center; margin:6px 0 12px 0; }
  .action-btn { padding:6px 12px; border:1px solid var(--ops-line); background:var(--ops-surface); border-radius:6px; font-size:12px; font-weight:600; cursor:pointer; color:var(--ops-ink-soft); display:inline-flex; align-items:center; gap:4px; }
  .action-btn:hover { background:rgba(45,80,22,0.05); }
  .action-btn.success { background:#16a34a; color:white; border-color:#16a34a; }
  /* Theme toggle (shared 'ops-theme' across pages) */
  .theme-toggle { position:absolute; top:14px; right:14px; padding:5px 10px; border:1px solid var(--ops-line); background:var(--ops-surface); border-radius:999px; font-size:13px; cursor:pointer; color:var(--ops-ink); z-index:10; }
  .theme-toggle:hover { background:rgba(45,80,22,0.06); }
  .ops-hero { position:relative; }
  body.theme-dark { --ops-bg:#0f172a; --ops-surface:#1e293b; --ops-ink:#e2e8f0; --ops-ink-soft:#cbd5e1; --ops-muted:#94a3b8; --ops-line:#334155; --ops-green:#22c55e; }
  body.theme-dark .ops-tbl thead th { background:#0f172a; }
  body.theme-dark .ops-tbl tbody tr:hover { background:rgba(34,197,94,0.06); }
  body.theme-dark .yoy-matrix th, body.theme-dark .yoy-matrix td { background:#1e293b; }
  body.theme-dark .yoy-matrix tbody td.peer-cell { background:#1e293b; }
  /* Tier trend chart */
  .tier-trend-card { background:var(--ops-surface); border:1px solid var(--ops-line); border-radius:10px; padding:16px 18px; margin:14px 0 24px 0; }
  .tier-trend-svg { width:100%; max-width:720px; height:260px; display:block; margin:0 auto; }
  .tier-trend-svg .axis line, .tier-trend-svg .axis path { stroke:var(--ops-line); }
  .tier-trend-svg .axis text { fill:var(--ops-muted); font-size:10.5px; }
  .tier-trend-svg .gridline { stroke:var(--ops-line); stroke-dasharray:2 3; opacity:0.5; }
  .tier-trend-svg .trend-line { fill:none; stroke-width:2.2; }
  .tier-trend-svg .trend-dot { stroke:white; stroke-width:1.5; }
  .tier-trend-legend { display:flex; flex-wrap:wrap; gap:14px; justify-content:center; margin-top:8px; font-size:11.5px; color:var(--ops-ink-soft); }
  .trend-mode-toggle { display:inline-flex; border:1px solid var(--ops-line); border-radius:6px; overflow:hidden; vertical-align:middle; margin-left:8px; }
  .trend-mode-toggle button { padding:5px 10px; border:none; background:var(--ops-surface); font-size:11.5px; font-weight:600; cursor:pointer; color:var(--ops-ink-soft); }
  .trend-mode-toggle button.active { background:var(--ops-green); color:white; }
  .trend-mode-toggle button + button { border-left:1px solid var(--ops-line); }
  /* Sortable headers */
  .sortable { cursor:pointer; user-select:none; position:relative; padding-right:18px !important; }
  .sortable:hover { background:rgba(45,80,22,0.06); }
  .sortable::after { content:'⇅'; position:absolute; right:6px; top:50%; transform:translateY(-50%); opacity:0.25; font-size:10px; }
  .sortable.asc::after { content:'▲'; opacity:1; color:var(--ops-green); }
  .sortable.desc::after { content:'▼'; opacity:1; color:var(--ops-green); }
  /* Mobile column priority */
  @media (max-width:720px) {
    .ops-tbl .col-low-prio { display:none; }
  }
  /* In-page anchor nav */
  .anchor-nav { display:flex; flex-wrap:wrap; gap:6px; margin:10px 0 4px 0; font-size:11.5px; }
  .anchor-nav a { padding:4px 10px; border:1px solid var(--ops-line); background:var(--ops-surface); border-radius:6px; text-decoration:none; color:var(--ops-ink-soft); transition:all 0.15s; }
  .anchor-nav a:hover { background:rgba(45,80,22,0.06); color:var(--ops-ink); }
  .anchor-nav a.active { background:var(--ops-green); color:white; border-color:var(--ops-green); }
  body.theme-dark .anchor-nav a:hover { background:rgba(34,197,94,0.08); }
  /* Smooth scroll + anchor offset (account for header) */
  html { scroll-behavior:smooth; }
  .anchor-target { scroll-margin-top:80px; }
  /* Print */
  @media print {
    @page { size: A4 landscape; margin: 10mm; }
    body { background:white !important; color:black !important; }
    .ops-head, .ops-foot, .year-bar, .rev-tab-bar, .action-bar, .theme-toggle, .anchor-nav, .trend-mode-toggle { display:none !important; }
    .ops-hero { padding:0 0 6px 0; }
    .ops-hero h1 { font-size:17px; margin:0 0 4px 0; }
    .ops-hero .lede { display:none; }
    .ops-section h2 { font-size:14px; margin:8px 0 4px 0; page-break-after:avoid; }
    .ops-section h3 { font-size:12px; margin:6px 0 3px 0; page-break-after:avoid; }
    .rev-panel { display:block !important; }
    .ops-tbl { font-size:9px; }
    .ops-tbl thead th { background:white !important; border-bottom:1.5px solid black; padding:4px 5px; position:static !important; }
    .ops-tbl tbody td { border-bottom:0.5px solid #ccc; padding:3px 5px; }
    .peer-tag { border:0.5px solid #888; padding:0 3px; font-size:8px; }
    a { color:black !important; text-decoration:none !important; }
    .tier-trend-svg, .spark { background:white; }
    .yoy-cell { -webkit-print-color-adjust:exact; print-color-adjust:exact; }
  }
</style>
</head>
<body>
<a class="skip-link" href="#main-content">메인 콘텐츠로 건너뛰기</a>
<header class="ops-head">
  <div class="ops-wrap ops-head-row">
    <a href="clubs/index.html" class="ops-brand">
      <div class="mark">⛳</div>
      <div>
        <div class="name">인도네시아 골프 운영 벤치마크</div>
        <div class="sub">13개 IDX 상장사</div>
      </div>
    </a>
    <nav class="ops-nav"><a href="clubs/index.html">⛳ 클럽</a><a href="unit-economics.html">단위 경제</a><a href="revenue.html" class="active">매출</a><a href="cost-hr.html">비용</a><a href="assets.html">시설</a><a href="risk.html">위험</a><a href="../../index.html" class="back">← 지도</a></nav>
  </div>
</header>

<section class="ops-hero">
  <button class="theme-toggle" id="theme-toggle" aria-label="다크모드 전환" title="다크/라이트 모드 전환 (d)">🌙</button>
  <div class="ops-wrap">
    <h1>매출 — 동급 비교</h1>
    <p class="lede">기준 연도 선택 → 13 peer 매출 비교. 라인 상세표는 선택 연도 컬럼 하이라이트.</p>
    <div class="top-perf" id="top-perf"></div>
    <div class="data-meta">
      📅 데이터: <strong>FY2020-FY2024 연결 P&amp;L</strong>
      <span class="sep">·</span>
      골프 부문: <strong>segment note 공시 또는 Pure-play 그룹 매출</strong>
      <span class="sep">·</span>
      출처: <strong>IDX (idx.co.id)</strong>
    </div>
    <div class="year-bar">
      <label>기준 연도:</label>
      <button class="year-btn" data-year="2020">FY2020</button>
      <button class="year-btn" data-year="2021">FY2021</button>
      <button class="year-btn" data-year="2022">FY2022</button>
      <button class="year-btn" data-year="2023">FY2023</button>
      <button class="year-btn active" data-year="2024">FY2024</button>
    </div>
    <div class="rev-tab-bar">
      <div class="rev-tab active" data-panel="cmp">① 13-peer 동급 비교</div>
      <div class="rev-tab" data-panel="pp">② Pure-play 매출 라인</div>
      <div class="rev-tab" data-panel="seg">③ 골프 세그먼트 라인</div>
    </div>
  </div>
</section>

<section class="ops-section" id="main-content">
  <div class="ops-wrap">
    <div class="rev-panel active" id="panel-cmp">
      <h2 class="anchor-target" id="sec-table" style="font-size:17px; margin:0 0 6px 0;">13-peer 매출 비교 — <span class="yr-label">FY2024</span></h2>
      <nav class="anchor-nav" aria-label="페이지 내 점프">
        <a href="#sec-table">📋 비교 표</a>
        <a href="#sec-trend">📈 Tier 추세 차트</a>
        <a href="#sec-yoy">🌡️ YoY 히트맵</a>
      </nav>
      <p style="font-size:12px; color:var(--ops-muted); margin:0 0 6px 0;">선택 연도 그룹 매출 + 골프 부문 매출(공시 peer) + 골프 비중 + YoY · <strong>5년 추이 sparkline</strong>(FY20→24, 호박색 점 = 선택 연도) · <strong>5Y CAGR</strong>(연평균 성장률).</p>
      <div class="action-bar">
        <button class="action-btn" id="copy-tsv-btn" aria-label="현재 표를 TSV로 클립보드 복사">📋 표 복사 (TSV)</button>
        <button class="action-btn" id="download-csv-btn" aria-label="CSV 파일 다운로드">⬇ CSV 다운로드</button>
      </div>
      <div class="tbl-card scroll-x">
        <table class="ops-tbl">
          <thead>
            <tr>
              <th>Peer</th>
              <th class="col-low-prio">그룹명</th>
              <th class="num sortable" data-sort="rev">그룹 매출</th>
              <th class="num col-low-prio">5년 추이</th>
              <th class="num sortable" data-sort="cagr">5Y CAGR</th>
              <th class="num sortable col-low-prio" data-sort="peak">5Y 위치 <span class="tip" title="FY24 매출이 FY20-24 최고치 대비 어디에 있는지 — 100% = 5년 최고, 작을수록 정점 후 감소">?</span></th>
              <th class="num sortable" data-sort="golf">골프 매출</th>
              <th class="num sortable col-low-prio" data-sort="share">골프 비중</th>
              <th class="num sortable" data-sort="yoyG">YoY (그룹)</th>
              <th class="num sortable col-low-prio" data-sort="yoyGolf">YoY (골프)</th>
            </tr>
          </thead>
          <tbody id="cmp-tbody"></tbody>
        </table>
      </div>

      <h3 class="anchor-target" id="sec-trend" style="font-size:15px; margin:24px 0 6px 0;">📈 Tier 추세 차트 (FY2020→2024)
        <span class="trend-mode-toggle" role="group" aria-label="추세 모드">
          <button class="active" data-mode="median">중위</button>
          <button data-mode="sum">합계</button>
          <button data-mode="indexed">FY20=100</button>
        </span>
      </h3>
      <p style="font-size:12px; color:var(--ops-muted); margin:0 0 12px 0;">tier별 그룹 매출 시계열 — 중위/합계/지수(FY20=100) 모드 전환. peer 규모 차이가 큰 township은 합계 모드에서, 추세 비교는 지수 모드에서 가장 명확.</p>
      <div class="tier-trend-card">
        <svg id="tier-trend-svg" class="tier-trend-svg" viewBox="0 0 720 260" preserveAspectRatio="xMidYMid meet" aria-label="Tier 추세 차트"></svg>
        <div class="tier-trend-legend">
          <span style="display:inline-flex; align-items:center; gap:6px;"><span style="width:14px; height:3px; background:#3b82f6; display:inline-block;"></span>🟦 Pure-play</span>
          <span style="display:inline-flex; align-items:center; gap:6px;"><span style="width:14px; height:3px; background:#f59e0b; display:inline-block;"></span>🟨 Resort</span>
          <span style="display:inline-flex; align-items:center; gap:6px;"><span style="width:14px; height:3px; background:#16a34a; display:inline-block;"></span>🟩 Township</span>
        </div>
      </div>

      <h3 class="anchor-target" id="sec-yoy" style="font-size:15px; margin:24px 0 6px 0;">🌡️ YoY 성장 히트맵 (그룹 매출)</h3>
      <p style="font-size:12px; color:var(--ops-muted); margin:0 0 12px 0;">peer × 연도 매트릭스. 셀 색상은 YoY %를 나타냄 — <span style="color:#16a34a; font-weight:700;">진녹색=고성장</span> · <span style="color:#b91c1c; font-weight:700;">진빨강=감소</span>. 한눈에 성장 패턴 파악.</p>
      <div style="overflow-x:auto;">
        <table class="yoy-matrix" id="yoy-matrix">
          <thead>
            <tr>
              <th style="text-align:left;">Peer</th>
              <th>FY20→21</th>
              <th>FY21→22</th>
              <th>FY22→23</th>
              <th>FY23→24</th>
              <th>5Y CAGR</th>
            </tr>
          </thead>
          <tbody id="yoy-matrix-body"></tbody>
        </table>
      </div>
    </div>

    <div class="rev-panel" id="panel-pp">
__PP_SECTION__
    </div>

    <div class="rev-panel" id="panel-seg">
__SEG_SECTION__
    </div>
  </div>
</section>

<button class="help-fab" id="help-fab" aria-label="키보드 단축키 도움말" title="키보드 단축키 (?)">?</button>
<div class="help-overlay" id="help-overlay" role="dialog" aria-modal="true" aria-labelledby="help-title">
  <div class="help-panel">
    <button class="close-btn" id="help-close" aria-label="도움말 닫기">✕</button>
    <h2 id="help-title">⌨️ 키보드 단축키</h2>
    <div class="help-row"><span>다크/라이트 모드 전환</span><kbd>d</kbd></div>
    <div class="help-row"><span>연도·탭·모드 이동</span><kbd>←</kbd> <kbd>→</kbd></div>
    <div class="help-row"><span>이 도움말 열기/닫기</span><kbd>?</kbd> <kbd>Esc</kbd></div>
    <div style="margin-top:12px; padding-top:10px; border-top:1px dashed var(--ops-line); font-size:11.5px; color:var(--ops-muted);">
      🔗 URL hash (#year=, #tab=)로 현재 상태 공유. ⬇ CSV 내보내기로 데이터 추출.
    </div>
  </div>
</div>

<footer class="ops-foot">
  <div class="ops-wrap">
    <p>그룹 매출: 연결 P&L FY2020-FY2024. 골프 매출: segment note 공시 또는 pure-play. 라인 상세: AR Note 22·25·27·29·31.</p>
  </div>
</footer>

<script src="operations.js?v=20260512c3" defer></script>
<script>
const PEER_DATA = __PEER_DATA__;
const PEER_ORDER = __PEER_ORDER__;

function fmtBn(v, dp){
  if (v === null || v === undefined) return '—';
  dp = (dp === undefined) ? 1 : dp;
  if (Math.abs(v) >= 1e12) return (v/1e12).toFixed(dp) + 'T';
  if (Math.abs(v) >= 1e9)  return (v/1e9).toFixed(dp) + 'B';
  if (Math.abs(v) >= 1e6)  return (v/1e6).toFixed(dp) + 'M';
  return Math.round(v).toLocaleString();
}
function fmtPct(v, dp){
  if (v === null || v === undefined) return '—';
  dp = (dp === undefined) ? 1 : dp;
  return v.toFixed(dp) + '%';
}
function fmtYoY(v){
  if (v === null || v === undefined) return '—';
  const col = v > 0 ? '#16a34a' : v < 0 ? '#b91c1c' : '#666';
  return `<span style="color:${col}; font-weight:700;">${v>=0?'+':''}${v.toFixed(1)}%</span>`;
}

// CAGR = (end/start)^(1/n) - 1.  Skips null endpoints, uses first/last available.
function calcCAGR(yearly){
  const years = ['2020','2021','2022','2023','2024'];
  const series = years.map(y => (yearly[y] ? yearly[y].rev : null));
  // Find first and last non-null
  let firstIdx = -1, lastIdx = -1;
  for (let i = 0; i < series.length; i++) {
    if (series[i] !== null && series[i] !== undefined && series[i] > 0) {
      if (firstIdx === -1) firstIdx = i;
      lastIdx = i;
    }
  }
  if (firstIdx === -1 || lastIdx === firstIdx) return { cagr: null, span: 0 };
  const span = lastIdx - firstIdx;
  const cagr = (Math.pow(series[lastIdx] / series[firstIdx], 1/span) - 1) * 100;
  return { cagr, span };
}

function fmtCAGR(c){
  if (c.cagr === null) return '—';
  const cls = c.cagr > 0 ? 'cagr-pos' : c.cagr < 0 ? 'cagr-neg' : 'cagr-zero';
  return `<span class="${cls}" title="${c.span}년 구간">${c.cagr>=0?'+':''}${c.cagr.toFixed(1)}%</span>`;
}

// SVG sparkline: 5-year revenue series. Width 80px, height 26px.
// Highlights the dot at the selected year in amber.
function sparkline(yearly, currentYear, color){
  const years = ['2020','2021','2022','2023','2024'];
  const series = years.map(y => (yearly[y] ? yearly[y].rev : null));
  const valid = series.filter(v => v !== null && v !== undefined);
  if (valid.length < 2) return '<span style="color:var(--ops-muted); font-size:11px;">—</span>';
  const W = 80, H = 26, padX = 3, padY = 4;
  const min = Math.min(...valid), max = Math.max(...valid);
  const range = max - min || 1;
  const points = [];
  series.forEach((v, i) => {
    if (v === null || v === undefined) return;
    const x = padX + (W - 2*padX) * (i / (years.length - 1));
    const y = H - padY - (H - 2*padY) * (v - min) / range;
    points.push({x, y, year: years[i], val: v, idx: i});
  });
  if (points.length < 2) return '<span style="color:var(--ops-muted); font-size:11px;">—</span>';
  const pathD = 'M ' + points.map(p => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' L ');
  const areaD = `${pathD} L ${points[points.length-1].x.toFixed(1)},${H-padY} L ${points[0].x.toFixed(1)},${H-padY} Z`;
  const dots = points.map(p => {
    const isCurrent = p.year === currentYear;
    if (isCurrent) {
      return `<circle class="spark-current" cx="${p.x.toFixed(1)}" cy="${p.y.toFixed(1)}" r="3"><title>FY${p.year}: ${(p.val/1e9).toFixed(1)}B</title></circle>`;
    }
    return `<circle class="spark-dot" cx="${p.x.toFixed(1)}" cy="${p.y.toFixed(1)}" r="1.6" fill="${color}"><title>FY${p.year}: ${(p.val/1e9).toFixed(1)}B</title></circle>`;
  }).join('');
  return `<svg class="spark" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" aria-label="5년 매출 추이">
    <path class="spark-area" d="${areaD}" fill="${color}"/>
    <path class="spark-line" d="${pathD}" stroke="${color}"/>
    ${dots}
  </svg>`;
}

let cmpSortState = { key: null, dir: 'desc' };

function renderTopPerf(year) {
  const prevYear = String(parseInt(year)-1);
  const fmtBn = v => (v === null || v === undefined) ? '—' : (Math.abs(v) >= 1e12 ? 'Rp '+(v/1e12).toFixed(1)+'T' : 'Rp '+(v/1e9).toFixed(0)+'B');
  const fmtPct = v => (v === null || v === undefined) ? '—' : `${v >= 0 ? '+' : ''}${v.toFixed(1)}%`;
  function top(metricFn, fmt) {
    let best = null, bestV = -Infinity;
    PEER_ORDER.forEach(t => {
      const v = metricFn(t);
      if (v !== null && v !== undefined && v > bestV) { bestV = v; best = t; }
    });
    return best ? { ticker: best, display: fmt(bestV) } : null;
  }
  const perfs = [
    { label: '🏆 최대 그룹 매출', data: top(t => PEER_DATA[t].yearly[year]?.rev, fmtBn) },
    { label: '🏆 최고 5Y CAGR', data: top(t => { const c = calcCAGR(PEER_DATA[t].yearly); return c.cagr; }, fmtPct) },
    { label: '🏆 최고 매출 YoY', data: top(t => {
      const r = PEER_DATA[t].yearly[year]?.rev; const p = PEER_DATA[t].yearly[prevYear]?.rev;
      return (r && p) ? (r - p) / p * 100 : null;
    }, fmtPct) },
    { label: '🏆 최대 골프 매출', data: top(t => PEER_DATA[t].golf_seg[year], fmtBn) },
  ];
  const root = document.getElementById('top-perf');
  if (!root) return;
  root.innerHTML = perfs.filter(p => p.data).map(p => `<div class="top-perf-card">
    <div class="top-perf-name">${p.label}</div>
    <div class="top-perf-winner"><a href="clubs/${p.data.ticker.toLowerCase()}.html">${p.data.ticker}</a></div>
    <div class="top-perf-value">${p.data.display}</div>
  </div>`).join('');
}

function render(year){
  renderTopPerf(year);
  document.querySelectorAll('.yr-label').forEach(el => el.textContent = 'FY' + year);

  // Cross-peer comparison
  const prevYear = String(parseInt(year)-1);
  const rowData = PEER_ORDER.map(t => {
    const d = PEER_DATA[t];
    const rev = d.yearly[year] ? d.yearly[year].rev : null;
    const revPrev = d.yearly[prevYear] ? d.yearly[prevYear].rev : null;
    const golf = d.golf_seg[year];
    const golfPrev = d.golf_seg[prevYear];
    const share = (rev && golf) ? (golf/rev*100) : null;
    const yoyG = (rev && revPrev) ? ((rev-revPrev)/revPrev*100) : null;
    const yoyGolf = (golf && golfPrev) ? ((golf-golfPrev)/golfPrev*100) : null;
    const cagr = calcCAGR(d.yearly);
    const fy5 = ['2020','2021','2022','2023','2024'].map(y => d.yearly[y] ? d.yearly[y].rev : null).filter(v => v && v > 0);
    const peak = (fy5.length >= 2 && rev) ? (rev / Math.max(...fy5) * 100) : null;
    return { t, d, rev, golf, share, yoyG, yoyGolf, cagr: cagr.cagr, peak };
  });
  if (cmpSortState.key) {
    rowData.sort((a, b) => {
      const va = a[cmpSortState.key]; const vb = b[cmpSortState.key];
      if (va === null || va === undefined) return 1;
      if (vb === null || vb === undefined) return -1;
      return cmpSortState.dir === 'desc' ? (vb - va) : (va - vb);
    });
  }
  const rows = rowData.map(r => {
    const { t, d, rev, golf, share, yoyG, yoyGolf } = r;
    const tierColor = d.tier === 'pp' ? '#3b82f6' : d.tier === 'resort' ? '#f59e0b' : '#16a34a';
    const cagr = calcCAGR(d.yearly);
    let peakHtml = '—';
    if (r.peak !== null) {
      let cls = 'down';
      if (r.peak >= 99.5) cls = 'at-peak';
      else if (r.peak >= 90) cls = 'near';
      const lbl = r.peak >= 99.5 ? '⭐ 정점' : (r.peak.toFixed(0)+'%');
      peakHtml = `<span class="peak-pill ${cls}" title="FY${year} 매출 = 5Y 최고치의 ${r.peak.toFixed(1)}%">${lbl}</span>`;
    }
    return `<tr>
      <td class="peer"><a href="clubs/${t.toLowerCase()}.html" style="color:var(--ops-ink); font-weight:700; text-decoration:none;">${t}</a><span class="peer-tag peer-tag-${d.tier}">${d.tier_label}</span></td>
      <td class="col-low-prio">${d.name.slice(0,24)}</td>
      <td class="num">${fmtBn(rev)}</td>
      <td class="num col-low-prio" style="padding:4px 8px;">${sparkline(d.yearly, year, tierColor)}</td>
      <td class="num">${fmtCAGR(cagr)}</td>
      <td class="num col-low-prio">${peakHtml}</td>
      <td class="num"><strong>${fmtBn(golf)}</strong></td>
      <td class="num col-low-prio">${fmtPct(share)}</td>
      <td class="num">${fmtYoY(yoyG)}</td>
      <td class="num col-low-prio">${fmtYoY(yoyGolf)}</td>
    </tr>`;
  });
  document.getElementById('cmp-tbody').innerHTML = rows.join('');
  // Update sort header indicators
  document.querySelectorAll('#panel-cmp .sortable').forEach(th => {
    th.classList.remove('asc','desc');
    if (th.dataset.sort === cmpSortState.key) th.classList.add(cmpSortState.dir);
  });

  // Tier trend chart
  renderTierTrend();
  // YoY heatmap matrix
  renderYoYMatrix();

  // Highlight selected year columns in line tables
  document.querySelectorAll('[class*="yr-"]').forEach(el => {
    el.classList.remove('yr-hl');
  });
  document.querySelectorAll('.yr-' + year).forEach(el => el.classList.add('yr-hl'));
}

// YoY color: green for growth, red for decline; gray for null
function yoyColor(pct) {
  if (pct === null || pct === undefined || isNaN(pct)) return { bg:'transparent', fg:'var(--ops-muted)', txt:'—' };
  // Cap at ±100% for color intensity, full saturation at ±50%
  const k = Math.max(-1, Math.min(1, pct / 50));
  let r, g, b;
  if (k >= 0) {
    // 0..1 -> white-ish to deep green
    r = Math.round(255 - (255 - 22)  * k);
    g = Math.round(255 - (255 - 163) * k);
    b = Math.round(255 - (255 - 74)  * k);
  } else {
    const ak = Math.abs(k);
    // 0..1 -> white-ish to deep red
    r = Math.round(255 - (255 - 185) * ak);
    g = Math.round(255 - (255 - 28)  * ak);
    b = Math.round(255 - (255 - 28)  * ak);
  }
  const luminance = (0.299*r + 0.587*g + 0.114*b);
  const fg = (Math.abs(k) > 0.45) ? 'white' : 'var(--ops-ink)';
  return { bg:`rgb(${r},${g},${b})`, fg, txt:`${pct >= 0 ? '+' : ''}${pct.toFixed(1)}%` };
}

function renderYoYMatrix() {
  const body = document.getElementById('yoy-matrix-body');
  if (!body) return;
  const yrSpans = [['2020','2021'],['2021','2022'],['2022','2023'],['2023','2024']];
  const html = PEER_ORDER.map(t => {
    const d = PEER_DATA[t];
    const cells = yrSpans.map(([y0, y1]) => {
      const r0 = d.yearly[y0] ? d.yearly[y0].rev : null;
      const r1 = d.yearly[y1] ? d.yearly[y1].rev : null;
      const pct = (r0 && r1) ? ((r1 - r0)/r0 * 100) : null;
      const c = yoyColor(pct);
      return `<td class="yoy-cell" style="background:${c.bg}; color:${c.fg};" title="FY${y0} → FY${y1}">${c.txt}</td>`;
    }).join('');
    const cagr = calcCAGR(d.yearly);
    const ccol = cagr.cagr === null ? {bg:'transparent', fg:'var(--ops-muted)', txt:'—'} : yoyColor(cagr.cagr);
    return `<tr>
      <td class="peer-cell"><a href="clubs/${t.toLowerCase()}.html" style="color:inherit; text-decoration:none;">${t}</a> <span class="peer-tag peer-tag-${d.tier}" style="font-size:9px; padding:1px 5px;">${d.tier_label.replace(/^[^ ]+ /,'')}</span></td>
      ${cells}
      <td class="yoy-cell" style="background:${ccol.bg}; color:${ccol.fg}; font-weight:700;" title="${cagr.span}년 연평균">${ccol.txt}</td>
    </tr>`;
  }).join('');
  body.innerHTML = html;
}

// CSV/TSV export of 13-peer comparison table (selected year)
function buildExport(year, sep) {
  const prevYear = String(parseInt(year)-1);
  const esc = v => {
    if (v === null || v === undefined) return '';
    const s = String(v);
    if (sep === ',' && (s.includes(',') || s.includes('"') || s.includes('\n'))) {
      return '"' + s.replace(/"/g,'""') + '"';
    }
    return s;
  };
  const headers = ['Peer','그룹명','Tier','그룹매출(IDR)','5Y_CAGR(%)','5Y_위치(%)','골프매출(IDR)','골프비중(%)','YoY_그룹(%)','YoY_골프(%)','FY20','FY21','FY22','FY23','FY24'];
  const lines = [headers.map(esc).join(sep)];
  PEER_ORDER.forEach(t => {
    const d = PEER_DATA[t];
    const rev = d.yearly[year] ? d.yearly[year].rev : null;
    const revPrev = d.yearly[prevYear] ? d.yearly[prevYear].rev : null;
    const golf = d.golf_seg[year];
    const golfPrev = d.golf_seg[prevYear];
    const share = (rev && golf) ? (golf/rev*100) : null;
    const yoyG = (rev && revPrev) ? ((rev-revPrev)/revPrev*100) : null;
    const yoyGolf = (golf && golfPrev) ? ((golf-golfPrev)/golfPrev*100) : null;
    const cagr = calcCAGR(d.yearly);
    const num = v => v === null || v === undefined ? '' : v;
    const pct = v => v === null || v === undefined ? '' : v.toFixed(2);
    // Peak position
    const fy5vals = ['2020','2021','2022','2023','2024'].map(y => d.yearly[y] ? d.yearly[y].rev : null).filter(v => v && v > 0);
    const peakRatio = (rev && fy5vals.length) ? (rev / Math.max(...fy5vals) * 100) : null;
    lines.push([
      esc(t), esc(d.name), esc(d.tier_label),
      num(rev), pct(cagr.cagr), pct(peakRatio), num(golf), pct(share), pct(yoyG), pct(yoyGolf),
      num(d.yearly['2020']?.rev), num(d.yearly['2021']?.rev), num(d.yearly['2022']?.rev),
      num(d.yearly['2023']?.rev), num(d.yearly['2024']?.rev),
    ].join(sep));
  });
  return lines.join('\n');
}

function flashSuccess(btn, label){
  const orig = btn.textContent;
  btn.textContent = label;
  btn.classList.add('success');
  setTimeout(() => { btn.textContent = orig; btn.classList.remove('success'); }, 1500);
}

// Tier trend chart — median/sum/indexed across FY2020-2024 per tier
let trendMode = 'median';
const TIER_COLOR = { pp:'#3b82f6', resort:'#f59e0b', twn:'#16a34a' };

function renderTierTrend() {
  const svg = document.getElementById('tier-trend-svg');
  if (!svg) return;
  const years = ['2020','2021','2022','2023','2024'];
  const med = arr => {
    const v = arr.filter(x => x !== null && x !== undefined && x > 0).sort((a,b)=>a-b);
    if (!v.length) return null;
    return v.length % 2 ? v[Math.floor(v.length/2)] : (v[v.length/2-1]+v[v.length/2])/2;
  };
  const sum = arr => arr.filter(x => x !== null && x !== undefined && x > 0).reduce((s,x)=>s+x,0) || null;
  // Build series per tier
  const tierSeries = {};
  ['pp','resort','twn'].forEach(tk => {
    const peers = PEER_ORDER.filter(t => PEER_DATA[t].tier === tk);
    if (!peers.length) return;
    const series = years.map(y => {
      const vals = peers.map(t => PEER_DATA[t].yearly[y] ? PEER_DATA[t].yearly[y].rev : null);
      return trendMode === 'sum' ? sum(vals) : med(vals);
    });
    // Indexed: divide by first non-null and ×100
    if (trendMode === 'indexed') {
      const base = series.find(v => v !== null);
      if (!base) return;
      tierSeries[tk] = series.map(v => v !== null ? (v / base * 100) : null);
    } else {
      tierSeries[tk] = series;
    }
  });
  const W = 720, H = 260, M = { l:62, r:18, t:14, b:34 };
  const allVals = [];
  Object.values(tierSeries).forEach(s => s.forEach(v => { if (v !== null) allVals.push(v); }));
  if (!allVals.length) { svg.innerHTML = ''; return; }
  const yMin = trendMode === 'indexed' ? Math.min(...allVals, 100) * 0.95 : 0;
  const yMax = Math.max(...allVals) * 1.05;
  const xScale = i => M.l + i / (years.length - 1) * (W - M.l - M.r);
  const yScale = v => H - M.b - (v - yMin) / (yMax - yMin) * (H - M.t - M.b);
  const fmtVal = v => {
    if (trendMode === 'indexed') return v.toFixed(0);
    if (v >= 1e12) return (v/1e12).toFixed(1) + 'T';
    if (v >= 1e9) return (v/1e9).toFixed(0) + 'B';
    return v.toFixed(0);
  };
  // Y ticks (5)
  const yTicks = [];
  for (let i = 0; i <= 4; i++) yTicks.push(yMin + (yMax - yMin) * i/4);
  let html = '';
  // Grid + Y labels
  yTicks.forEach(v => {
    html += `<line class="gridline" x1="${M.l}" y1="${yScale(v)}" x2="${W-M.r}" y2="${yScale(v)}"/>`;
    html += `<text class="axis" x="${M.l-6}" y="${yScale(v)+4}" text-anchor="end">${fmtVal(v)}</text>`;
  });
  // X labels
  years.forEach((y, i) => {
    html += `<text class="axis" x="${xScale(i)}" y="${H-M.b+18}" text-anchor="middle">FY${y.slice(2)}</text>`;
  });
  // Axes
  html += `<line class="axis" x1="${M.l}" y1="${H-M.b}" x2="${W-M.r}" y2="${H-M.b}" stroke-width="1"/>`;
  html += `<line class="axis" x1="${M.l}" y1="${M.t}" x2="${M.l}" y2="${H-M.b}" stroke-width="1"/>`;
  // Lines + dots per tier
  ['pp','resort','twn'].forEach(tk => {
    const s = tierSeries[tk];
    if (!s) return;
    const pts = [];
    s.forEach((v, i) => { if (v !== null) pts.push({ x: xScale(i), y: yScale(v), v, year: years[i] }); });
    if (pts.length < 2) return;
    const path = 'M ' + pts.map(p => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' L ');
    const col = TIER_COLOR[tk];
    html += `<path class="trend-line" d="${path}" stroke="${col}"/>`;
    pts.forEach(p => {
      html += `<circle class="trend-dot" cx="${p.x.toFixed(1)}" cy="${p.y.toFixed(1)}" r="3.5" fill="${col}"><title>FY${p.year}: ${fmtVal(p.v)}</title></circle>`;
    });
    // End label
    const last = pts[pts.length-1];
    html += `<text x="${last.x+5}" y="${last.y+4}" font-size="11" font-weight="700" fill="${col}">${fmtVal(last.v)}</text>`;
  });
  svg.innerHTML = html;
}

let currentYear = '2024';
(function(){
  document.querySelectorAll('.year-btn').forEach(b => {
    b.addEventListener('click', () => {
      document.querySelectorAll('.year-btn').forEach(x => x.classList.remove('active'));
      b.classList.add('active');
      currentYear = b.dataset.year;
      render(currentYear);
    });
  });
  document.querySelectorAll('.rev-tab').forEach(t => t.addEventListener('click', () => {
    document.querySelectorAll('.rev-tab').forEach(x => x.classList.remove('active'));
    document.querySelectorAll('.rev-panel').forEach(p => p.classList.remove('active'));
    t.classList.add('active');
    document.getElementById('panel-' + t.dataset.panel).classList.add('active');
  }));
  const copyBtn = document.getElementById('copy-tsv-btn');
  if (copyBtn) copyBtn.addEventListener('click', async (e) => {
    const tsv = buildExport(currentYear, '\t');
    try { await navigator.clipboard.writeText(tsv); }
    catch (err) { const ta = document.createElement('textarea'); ta.value = tsv; document.body.appendChild(ta); ta.select(); document.execCommand('copy'); document.body.removeChild(ta); }
    flashSuccess(e.currentTarget, '✓ 복사됨');
  });
  const dlBtn = document.getElementById('download-csv-btn');
  if (dlBtn) dlBtn.addEventListener('click', (e) => {
    const csv = '﻿' + buildExport(currentYear, ',');
    const blob = new Blob([csv], { type:'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = `revenue_FY${currentYear}.csv`;
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
    URL.revokeObjectURL(url);
    flashSuccess(e.currentTarget, '✓ 다운로드');
  });
  // Trend mode toggle
  document.querySelectorAll('.trend-mode-toggle button').forEach(b => {
    b.addEventListener('click', () => {
      document.querySelectorAll('.trend-mode-toggle button').forEach(x => x.classList.remove('active'));
      b.classList.add('active');
      trendMode = b.dataset.mode;
      renderTierTrend();
    });
  });
  // Dark mode + system pref auto-follow
  const themeBtn = document.getElementById('theme-toggle');
  function applyTheme(theme) {
    if (theme === 'dark') { document.body.classList.add('theme-dark'); themeBtn.textContent = '☀️'; }
    else                  { document.body.classList.remove('theme-dark'); themeBtn.textContent = '🌙'; }
  }
  const saved = localStorage.getItem('ops-theme');
  const mql = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)');
  applyTheme(saved || (mql && mql.matches ? 'dark' : 'light'));
  if (mql && mql.addEventListener) {
    mql.addEventListener('change', (e) => { if (!localStorage.getItem('ops-theme')) applyTheme(e.matches ? 'dark' : 'light'); });
  }
  themeBtn.addEventListener('click', () => {
    const newT = document.body.classList.contains('theme-dark') ? 'light' : 'dark';
    localStorage.setItem('ops-theme', newT);
    applyTheme(newT);
  });
  // Help overlay
  const helpOverlay = document.getElementById('help-overlay');
  const helpClose = document.getElementById('help-close');
  const helpFab = document.getElementById('help-fab');
  function toggleHelp(show) {
    if (show === undefined) show = !helpOverlay.classList.contains('open');
    helpOverlay.classList.toggle('open', show);
  }
  if (helpClose) helpClose.addEventListener('click', () => toggleHelp(false));
  if (helpFab) helpFab.addEventListener('click', () => toggleHelp());
  if (helpOverlay) helpOverlay.addEventListener('click', (e) => { if (e.target === helpOverlay) toggleHelp(false); });

  document.addEventListener('keydown', (e) => {
    if (helpOverlay.classList.contains('open') && e.key === 'Escape') { e.preventDefault(); toggleHelp(false); return; }
    if (e.target.matches('input,textarea,select')) return;
    if (e.key === 'd') themeBtn.click();
    else if (e.key === '?') { e.preventDefault(); toggleHelp(); }
  });
  // Scroll-spy for anchor nav
  const anchorLinks = document.querySelectorAll('.anchor-nav a');
  const anchorTargets = Array.from(anchorLinks).map(a => document.querySelector(a.getAttribute('href'))).filter(Boolean);
  function updateActiveAnchor() {
    let activeIdx = 0;
    const scrollY = window.scrollY + 120;
    anchorTargets.forEach((el, i) => {
      if (el && el.offsetTop <= scrollY) activeIdx = i;
    });
    anchorLinks.forEach((a, i) => a.classList.toggle('active', i === activeIdx));
  }
  if (anchorTargets.length) {
    updateActiveAnchor();
    window.addEventListener('scroll', updateActiveAnchor, { passive: true });
  }
  // Keyboard arrow nav
  function wireArrowNav(selector) {
    const items = Array.from(document.querySelectorAll(selector));
    items.forEach((el, i) => {
      el.setAttribute('tabindex', '0');
      el.addEventListener('keydown', (e) => {
        if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') {
          e.preventDefault();
          const next = e.key === 'ArrowRight' ? (i + 1) % items.length : (i - 1 + items.length) % items.length;
          items[next].focus();
          items[next].click();
        }
      });
    });
  }
  wireArrowNav('.year-btn');
  wireArrowNav('.rev-tab');
  wireArrowNav('.trend-mode-toggle button');
  // localStorage state: year + active tab + trend mode
  function saveRevState() {
    const tab = document.querySelector('.rev-tab.active');
    try {
      localStorage.setItem('rev-state', JSON.stringify({
        year: currentYear,
        tab: tab ? tab.dataset.panel : 'cmp',
        trend: trendMode,
      }));
    } catch (e) {}
  }
  function loadRevState() {
    try {
      const s = JSON.parse(localStorage.getItem('rev-state') || 'null');
      if (!s) return;
      if (s.year && ['2020','2021','2022','2023','2024'].includes(s.year)) {
        currentYear = s.year;
        document.querySelectorAll('.year-btn').forEach(b => b.classList.toggle('active', b.dataset.year === s.year));
      }
      if (s.tab) {
        document.querySelectorAll('.rev-tab').forEach(x => x.classList.toggle('active', x.dataset.panel === s.tab));
        document.querySelectorAll('.rev-panel').forEach(p => p.classList.toggle('active', p.id === 'panel-' + s.tab));
      }
      if (s.trend && ['median','sum','indexed'].includes(s.trend)) {
        trendMode = s.trend;
        document.querySelectorAll('.trend-mode-toggle button').forEach(b => b.classList.toggle('active', b.dataset.mode === s.trend));
      }
    } catch (e) {}
  }
  loadRevState();
  // URL hash overrides (shareable links)
  function readRevHash() {
    const h = (location.hash || '').replace(/^#/, '');
    if (!h) return null;
    const p = new URLSearchParams(h);
    return { year: p.get('year'), tab: p.get('tab') };
  }
  function syncRevHash() {
    const parts = [];
    if (currentYear && currentYear !== '2024') parts.push('year=' + currentYear);
    const activeTab = document.querySelector('.rev-tab.active');
    const tabKey = activeTab ? activeTab.dataset.panel : 'cmp';
    if (tabKey && tabKey !== 'cmp') parts.push('tab=' + tabKey);
    const h = parts.join('&');
    history.replaceState(null, '', h ? '#' + h : location.pathname + location.search);
  }
  const fromHash = readRevHash();
  if (fromHash) {
    if (fromHash.year && ['2020','2021','2022','2023','2024'].includes(fromHash.year)) {
      currentYear = fromHash.year;
      document.querySelectorAll('.year-btn').forEach(b => b.classList.toggle('active', b.dataset.year === currentYear));
    }
    if (fromHash.tab && ['cmp','pp','seg'].includes(fromHash.tab)) {
      document.querySelectorAll('.rev-tab').forEach(x => x.classList.toggle('active', x.dataset.panel === fromHash.tab));
      document.querySelectorAll('.rev-panel').forEach(p => p.classList.toggle('active', p.id === 'panel-' + fromHash.tab));
    }
  }
  document.querySelectorAll('.year-btn, .rev-tab, .trend-mode-toggle button').forEach(el => {
    el.addEventListener('click', () => setTimeout(() => { saveRevState(); syncRevHash(); }, 0));
  });
  // Sortable header click
  document.querySelectorAll('#panel-cmp .sortable').forEach(th => {
    th.addEventListener('click', () => {
      const k = th.dataset.sort;
      if (cmpSortState.key === k) cmpSortState.dir = (cmpSortState.dir === 'desc') ? 'asc' : 'desc';
      else { cmpSortState.key = k; cmpSortState.dir = 'desc'; }
      render(currentYear);
    });
  });
  render(currentYear);
})();
</script>
</body>
</html>
'''

html = html.replace('__PEER_DATA__', peer_data_json)
html = html.replace('__PEER_ORDER__', json.dumps(peers_sorted))
html = html.replace('__PP_SECTION__', pp_section)
html = html.replace('__SEG_SECTION__', seg_section)

with open('revenue.html','w',encoding='utf-8') as f:
    f.write(html)
print(f'revenue.html: {os.path.getsize("revenue.html")/1024:.1f} KB')
