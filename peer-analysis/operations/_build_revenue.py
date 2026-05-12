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
</style>
</head>
<body>
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
  <div class="ops-wrap">
    <h1>매출 — 동급 비교</h1>
    <p class="lede">기준 연도 선택 → 13 peer 매출 비교. 라인 상세표는 선택 연도 컬럼 하이라이트.</p>
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

<section class="ops-section">
  <div class="ops-wrap">
    <div class="rev-panel active" id="panel-cmp">
      <h2 style="font-size:17px; margin:0 0 14px 0;">13-peer 매출 비교 — <span class="yr-label">FY2024</span></h2>
      <p style="font-size:12px; color:var(--ops-muted); margin:0 0 12px 0;">선택 연도 그룹 매출 + 골프 부문 매출(공시 peer) + 골프 비중 + YoY · <strong>5년 추이 sparkline</strong>(FY20→24, 호박색 점 = 선택 연도) · <strong>5Y CAGR</strong>(연평균 성장률).</p>
      <div class="tbl-card scroll-x">
        <table class="ops-tbl">
          <thead>
            <tr>
              <th>Peer</th>
              <th>그룹명</th>
              <th class="num">그룹 매출</th>
              <th class="num">5년 추이</th>
              <th class="num">5Y CAGR</th>
              <th class="num">골프 매출</th>
              <th class="num">골프 비중</th>
              <th class="num">YoY (그룹)</th>
              <th class="num">YoY (골프)</th>
            </tr>
          </thead>
          <tbody id="cmp-tbody"></tbody>
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

function render(year){
  document.querySelectorAll('.yr-label').forEach(el => el.textContent = 'FY' + year);

  // Cross-peer comparison
  const prevYear = String(parseInt(year)-1);
  const rows = PEER_ORDER.map(t => {
    const d = PEER_DATA[t];
    const rev = d.yearly[year] ? d.yearly[year].rev : null;
    const revPrev = d.yearly[prevYear] ? d.yearly[prevYear].rev : null;
    const golf = d.golf_seg[year];
    const golfPrev = d.golf_seg[prevYear];
    const share = (rev && golf) ? (golf/rev*100) : null;
    const yoyG = (rev && revPrev) ? ((rev-revPrev)/revPrev*100) : null;
    const yoyGolf = (golf && golfPrev) ? ((golf-golfPrev)/golfPrev*100) : null;
    const tierColor = d.tier === 'pp' ? '#3b82f6' : d.tier === 'resort' ? '#f59e0b' : '#16a34a';
    const cagr = calcCAGR(d.yearly);
    return `<tr>
      <td class="peer"><a href="clubs/${t.toLowerCase()}.html" style="color:var(--ops-ink); font-weight:700; text-decoration:none;">${t}</a><span class="peer-tag peer-tag-${d.tier}">${d.tier_label}</span></td>
      <td>${d.name.slice(0,24)}</td>
      <td class="num">${fmtBn(rev)}</td>
      <td class="num" style="padding:4px 8px;">${sparkline(d.yearly, year, tierColor)}</td>
      <td class="num">${fmtCAGR(cagr)}</td>
      <td class="num"><strong>${fmtBn(golf)}</strong></td>
      <td class="num">${fmtPct(share)}</td>
      <td class="num">${fmtYoY(yoyG)}</td>
      <td class="num">${fmtYoY(yoyGolf)}</td>
    </tr>`;
  });
  document.getElementById('cmp-tbody').innerHTML = rows.join('');

  // Highlight selected year columns in line tables
  document.querySelectorAll('[class*="yr-"]').forEach(el => {
    el.classList.remove('yr-hl');
  });
  document.querySelectorAll('.yr-' + year).forEach(el => el.classList.add('yr-hl'));
}

(function(){
  document.querySelectorAll('.year-btn').forEach(b => {
    b.addEventListener('click', () => {
      document.querySelectorAll('.year-btn').forEach(x => x.classList.remove('active'));
      b.classList.add('active');
      render(b.dataset.year);
    });
  });
  document.querySelectorAll('.rev-tab').forEach(t => t.addEventListener('click', () => {
    document.querySelectorAll('.rev-tab').forEach(x => x.classList.remove('active'));
    document.querySelectorAll('.rev-panel').forEach(p => p.classList.remove('active'));
    t.classList.add('active');
    document.getElementById('panel-' + t.dataset.panel).classList.add('active');
  }));
  render('2024');
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
