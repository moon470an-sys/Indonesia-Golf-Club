"""Build unit-economics.html — per-unit metrics with year selector (FY2020-FY2024)."""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import json
import os

clubs = json.load(open('data/_clubs_meta.json','r',encoding='utf-8'))
d5y = json.load(open('../../data/company_financials_5y.json','r',encoding='utf-8'))
fin = {c['ticker']: c for c in d5y['companies'] if 'ticker' in c}
peers_v2 = ['DMIG','PIPG','GOLF','MDLN','KIJA','SMDM','KPIG','SMRA','BSDE','CTRA','ELTY','LPKR','PWON']
def torder(t): return {'pp':1,'resort':2,'twn':3}.get(clubs[t]['tier'], 9)

# Per-peer fixed inputs (holes, area_ha — golf course only)
# Pure-play has golf_rev == group_rev; otherwise golf segment if disclosed (year-dependent)
UNIT_INPUTS = {
    'DMIG': {'holes':36,   'area':156.0, 'employees':198,  'pure_play':True},
    'PIPG': {'holes':18,   'area':53.01, 'employees':254,  'pure_play':True},
    'GOLF': {'holes':36,   'area':171.2, 'employees':None, 'pure_play':False},
    'MDLN': {'holes':18,   'area':None,  'employees':None, 'pure_play':False},
    'KIJA': {'holes':None, 'area':None,  'employees':None, 'pure_play':False},
    'SMDM': {'holes':18,   'area':None,  'employees':None, 'pure_play':False},
    'KPIG': {'holes':18,   'area':83.0,  'employees':None, 'pure_play':False},
    'SMRA': {'holes':18,   'area':None,  'employees':None, 'pure_play':False},
    'BSDE': {'holes':None, 'area':None,  'employees':None, 'pure_play':False},
    'CTRA': {'holes':36,   'area':None,  'employees':None, 'pure_play':False},
    'ELTY': {'holes':36,   'area':None,  'employees':None, 'pure_play':False},
    'LPKR': {'holes':18,   'area':None,  'employees':None, 'pure_play':False},
    'PWON': {'holes':18,   'area':None,  'employees':None, 'pure_play':False},
}

# Golf segment revenue per year (IDR) where disclosed in AR segment notes
# Pure-play: leave None — JS will fallback to group revenue
GOLF_SEG_REV = {
    'GOLF': {'2023': 94436855876, '2024': 93042072774},  # Note 29 by_operations Golf
    'MDLN': {'2023': None,        '2024': 74400000000},   # approximate via segment note (placeholder)
    'KIJA': {'2024': 85019000000},   # segment_info_note_34 golf_segment_FY2024 (Rp m → IDR)
    'SMDM': {'2024': 63282214554},
    'SMRA': {'2024': 66672127000},   # FY2024_comparative * 1000 (thousand→IDR)
}

# Build PEER_DATA payload for JS
peers_sorted = sorted(peers_v2, key=lambda t: (torder(t), t))

peer_data = {}
for t in peers_sorted:
    c = clubs[t]
    u = UNIT_INPUTS[t]
    cy = fin.get(t,{}).get('yearly',{})
    yearly = {}
    for y in ['2020','2021','2022','2023','2024']:
        yy = cy.get(y, {})
        emp = yy.get('employees') or u['employees']
        yearly[y] = {
            'rev': yy.get('revenue'),
            'op': yy.get('operating_profit'),
            'np': yy.get('net_profit'),
            'ebitda': yy.get('ebitda'),
            'emp': emp,
        }
    # Golf segment per year (overlay)
    if u['pure_play']:
        golf_seg = {y: yearly[y]['rev'] for y in yearly}  # pure-play: group=golf
    else:
        golf_seg = GOLF_SEG_REV.get(t, {})
    peer_data[t] = {
        'name': c['name'],
        'tier': c['tier'],
        'tier_label': c['tier_label'],
        'holes': u['holes'],
        'area': u['area'],
        'pure_play': u['pure_play'],
        'yearly': yearly,
        'golf_seg': golf_seg,
    }

peer_data_json = json.dumps(peer_data, ensure_ascii=False)

html = '''<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>단위 경제 — 인도네시아 골프 운영 벤치마크</title>
<link rel="icon" type="image/svg+xml" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Ccircle cx='32' cy='32' r='30' fill='%232D5016'/%3E%3Ccircle cx='32' cy='32' r='12' fill='%23F5F1E8'/%3E%3C/svg%3E" />
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Pretendard:wght@400;500;600;700&display=swap" rel="stylesheet" />
<link rel="stylesheet" href="ops-style.css?v=20260512c54" />
<style>
  .year-bar { display:flex; align-items:center; gap:10px; flex-wrap:wrap; margin:14px 0 4px 0; }
  .year-bar label { font-size:13px; font-weight:600; color:var(--ops-ink-soft); }
  .year-btn { padding:6px 14px; border:1px solid var(--ops-line); background:var(--ops-surface); border-radius:6px; font-size:12.5px; font-weight:600; cursor:pointer; color:var(--ops-ink-soft); }
  .year-btn.active { background:var(--ops-green); color:white; border-color:var(--ops-green); }
  .year-btn:hover:not(.active) { background:rgba(45,80,22,0.05); }
  /* Sortable headers */
  .sortable { cursor:pointer; user-select:none; position:relative; padding-right:18px !important; }
  .sortable:hover { background:rgba(45,80,22,0.06); }
  .sortable::after { content:'⇅'; position:absolute; right:6px; top:50%; transform:translateY(-50%); opacity:0.25; font-size:10px; }
  .sortable.asc::after { content:'▲'; opacity:1; color:var(--ops-green); }
  .sortable.desc::after { content:'▼'; opacity:1; color:var(--ops-green); }
  /* Heat-map cells — better = greener, worse = redder, null = neutral */
  .heat { position:relative; }
  .heat-bar { position:absolute; left:4px; right:4px; bottom:2px; height:2px; border-radius:1px; }
  /* Term tooltip — dotted underline + native title */
  .tip { border-bottom:1px dotted var(--ops-muted); cursor:help; }
  /* Sticky first column on wide tables */
  .sticky-first th:first-child, .sticky-first td:first-child { position:sticky; left:0; background:var(--ops-surface); z-index:1; box-shadow:1px 0 0 var(--ops-line); }
  .sticky-first thead th:first-child { background:var(--ops-bg); z-index:2; }
  /* Tier filter pills */
  .tier-pills { display:flex; gap:8px; flex-wrap:wrap; align-items:center; margin:10px 0 4px 0; }
  .tier-pill { padding:5px 12px; border:1px solid var(--ops-line); background:var(--ops-surface); border-radius:999px; font-size:12px; font-weight:600; cursor:pointer; color:var(--ops-ink-soft); }
  .tier-pill.active { background:var(--ops-green); color:white; border-color:var(--ops-green); }
  .tier-pill:hover:not(.active) { background:rgba(45,80,22,0.05); }
  /* Action bar with export */
  .action-bar { display:flex; gap:8px; flex-wrap:wrap; align-items:center; margin:6px 0 12px 0; }
  .action-btn { padding:6px 12px; border:1px solid var(--ops-line); background:var(--ops-surface); border-radius:6px; font-size:12px; font-weight:600; cursor:pointer; color:var(--ops-ink-soft); display:inline-flex; align-items:center; gap:4px; }
  .action-btn:hover { background:rgba(45,80,22,0.05); }
  .action-btn.success { background:#16a34a; color:white; border-color:#16a34a; }
  .row-count { font-size:12px; color:var(--ops-muted); margin-left:auto; }
  /* Hidden rows (filtered out) */
  tr.tier-hidden { display:none; }
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
    <nav class="ops-nav"><a href="clubs/index.html">⛳ 클럽</a><a href="unit-economics.html" class="active">단위 경제</a><a href="revenue.html">매출</a><a href="cost-hr.html">비용</a><a href="assets.html">시설</a><a href="risk.html">위험</a><a href="../../index.html" class="back">← 지도</a></nav>
  </div>
</header>

<section class="ops-hero">
  <div class="ops-wrap">
    <h1>단위 경제 (Per-unit Economics)</h1>
    <p class="lede">기준 연도 선택 → 13 peer 동급 비교. 홀·면적·정직원은 고정값, 매출·이익은 연도별.</p>
    <div class="year-bar">
      <label>기준 연도:</label>
      <button class="year-btn" data-year="2020">FY2020</button>
      <button class="year-btn" data-year="2021">FY2021</button>
      <button class="year-btn" data-year="2022">FY2022</button>
      <button class="year-btn" data-year="2023">FY2023</button>
      <button class="year-btn active" data-year="2024">FY2024</button>
    </div>
  </div>
</section>

<section class="ops-section">
  <div class="ops-wrap">
    <h2 style="font-size:17px; margin:0 0 14px 0;">① 13-peer 단위 경제 — <span id="yr1">FY2024</span></h2>
    <p style="font-size:12px; color:var(--ops-muted); margin:0 0 6px 0;">
      홀당·<span class="tip" title="ha = 헥타르 (10,000 m²). 1 ha ≈ 3,025 평">ha</span>당 매출 = 골프 부문 매출 ÷ 단위
      (<span class="tip" title="Pure-play = 그룹 매출 거의 전부가 골프 사업인 회사 (DMIG, PIPG). Township/Resort에서는 골프 segment 매출만 사용.">Pure-play</span>는 그룹 매출).
      1인당 매출·영업이익은 그룹 <span class="tip" title="Profit &amp; Loss statement, 손익계산서">P&amp;L</span>.
      <strong style="margin-left:8px;">💡 헤더 클릭 정렬</strong> · <strong>히트맵 막대</strong>: 진할수록 우수 (회색=데이터 없음).
    </p>
    <div class="tier-pills" id="tier-pills" role="group" aria-label="Tier 필터">
      <span style="font-size:11.5px; color:var(--ops-muted); font-weight:600;">Tier:</span>
      <button class="tier-pill active" data-tier="all">전체 (13)</button>
      <button class="tier-pill" data-tier="pp">🟦 Pure-play (2)</button>
      <button class="tier-pill" data-tier="resort">🟨 Resort (1)</button>
      <button class="tier-pill" data-tier="twn">🟩 Township (10)</button>
    </div>
    <div class="action-bar">
      <button class="action-btn" id="copy-tsv-btn" aria-label="현재 표를 TSV로 클립보드 복사">📋 표 복사 (TSV)</button>
      <button class="action-btn" id="download-csv-btn" aria-label="현재 표를 CSV 파일로 다운로드">⬇ CSV 다운로드</button>
      <span class="row-count" id="row-count">13 / 13 표시</span>
    </div>
    <div class="tbl-card scroll-x">
      <table class="ops-tbl sticky-first" id="main-table">
        <thead>
          <tr>
            <th>Peer</th>
            <th>그룹명</th>
            <th class="num sortable" data-sort="holes">홀</th>
            <th class="num sortable" data-sort="area">면적 (ha)</th>
            <th class="num sortable" data-sort="emp">정직원</th>
            <th class="num sortable" data-sort="golfRev">골프 매출</th>
            <th class="num sortable desc" data-sort="revPerHole">홀당 매출</th>
            <th class="num sortable" data-sort="revPerHa">ha당 매출</th>
            <th class="num sortable" data-sort="revPerEmp">1인당 매출</th>
            <th class="num sortable" data-sort="opMargin">영업이익률</th>
            <th class="num sortable" data-sort="opPerEmp">1인당 영업이익</th>
          </tr>
        </thead>
        <tbody id="main-tbody"></tbody>
      </table>
    </div>
  </div>
</section>

<section class="ops-section">
  <div class="ops-wrap">
    <h2 style="font-size:17px; margin:0 0 14px 0;">② 홀당 매출 리더보드 — <span id="yr2">FY2024</span></h2>
    <p style="font-size:12px; color:var(--ops-muted); margin:0 0 12px 0;">선택 연도 골프 부문 매출 ÷ 홀 수. 공시된 peer만 표시.</p>
    <div class="tbl-card scroll-x">
      <table class="ops-tbl">
        <thead>
          <tr>
            <th class="num">#</th>
            <th>Peer</th>
            <th>그룹명</th>
            <th class="num">홀</th>
            <th class="num">골프 매출</th>
            <th class="num">홀당 매출</th>
          </tr>
        </thead>
        <tbody id="lb-tbody"></tbody>
      </table>
    </div>
  </div>
</section>

<section class="ops-section">
  <div class="ops-wrap">
    <h2 style="font-size:17px; margin:0 0 14px 0;">③ Tier 평균 — <span id="yr3">FY2024</span></h2>
    <p style="font-size:12px; color:var(--ops-muted); margin:0 0 12px 0;">Tier별 공시 peer 평균.</p>
    <div class="tbl-card scroll-x">
      <table class="ops-tbl">
        <thead>
          <tr>
            <th>Tier</th>
            <th class="num">N</th>
            <th class="num">평균 홀</th>
            <th class="num">평균 면적 (ha)</th>
            <th class="num">평균 홀당 매출</th>
            <th class="num">평균 ha당 매출</th>
          </tr>
        </thead>
        <tbody id="tier-tbody"></tbody>
      </table>
    </div>
  </div>
</section>

<footer class="ops-foot">
  <div class="ops-wrap">
    <p>홀·면적·정직원: AR Profile + 자사 공시 (고정). 매출·이익: 연결 P&L FY2020-FY2024. 골프 매출은 segment note 또는 그룹 매출(pure-play).</p>
  </div>
</footer>

<script src="operations.js?v=20260512c3" defer></script>
<script>
const PEER_DATA = __PEER_DATA__;
const PEER_ORDER = __PEER_ORDER__;
const TIER_LABEL = {pp:'🟦 Pure-play', resort:'🟨 Resort', twn:'🟩 Township'};

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
function fmtNum(v, dp){
  if (v === null || v === undefined) return '—';
  dp = (dp === undefined) ? 0 : dp;
  return v.toFixed(dp);
}
function fmtPerUnit(rev_bn, divisor){
  if (rev_bn === null || rev_bn === undefined || !divisor) return '—';
  const v = rev_bn / divisor;
  if (Math.abs(v) < 1) return (v*1000).toFixed(0) + 'M';
  return v.toFixed(2) + 'B';
}

// State for sorting + tier filter (persists across year changes)
let sortState = { key: 'revPerHole', dir: 'desc' };
let tierFilter = 'all';

function computeMainRows(year){
  return PEER_ORDER.map(t => {
    const d = PEER_DATA[t];
    const yy = d.yearly[year] || {};
    const golfRev = (d.golf_seg && d.golf_seg[year]) ? d.golf_seg[year] : null;
    const grpRev = yy.rev;
    const grpOp = yy.op;
    const emp = yy.emp;
    const opMargin = (grpRev && grpOp !== null && grpOp !== undefined) ? (grpOp/grpRev*100) : null;
    const golfRevBn = golfRev ? golfRev/1e9 : null;
    const grpRevBn = grpRev ? grpRev/1e9 : null;
    const grpOpBn = (grpOp !== null && grpOp !== undefined) ? grpOp/1e9 : null;
    return {
      t, d,
      holes: d.holes, area: d.area, emp,
      golfRev: golfRevBn,
      revPerHole: (golfRevBn && d.holes) ? golfRevBn / d.holes : null,
      revPerHa:   (golfRevBn && d.area)  ? golfRevBn / d.area  : null,
      revPerEmp:  (grpRevBn  && emp)     ? grpRevBn  / emp     : null,
      opMargin,
      opPerEmp:   (grpOpBn !== null && grpOpBn !== undefined && emp) ? grpOpBn / emp : null,
    };
  });
}

// Build heat-map color band per metric (green high → red low for "higher is better" metrics)
function heatBar(value, min, max, higherBetter){
  if (value === null || value === undefined || min === max) return '';
  let t = (value - min) / (max - min);  // 0..1
  if (!higherBetter) t = 1 - t;
  // green (good) #16a34a → amber #f59e0b → red #b91c1c
  let r, g, b;
  if (t >= 0.5) {
    const k = (t - 0.5) * 2;  // 0..1 amber→green
    r = Math.round(245 + (22  - 245) * k);
    g = Math.round(158 + (163 - 158) * k);
    b = Math.round(11  + (74  - 11)  * k);
  } else {
    const k = t * 2;  // 0..1 red→amber
    r = Math.round(185 + (245 - 185) * k);
    g = Math.round(28  + (158 - 28)  * k);
    b = Math.round(28  + (11  - 28)  * k);
  }
  const w = (t * 100).toFixed(0);
  return `<div class="heat-bar" style="width:${w}%; background:rgb(${r},${g},${b});"></div>`;
}

function renderMain(year){
  const allRows = computeMainRows(year);
  // Filter by tier
  const rows = (tierFilter === 'all') ? allRows : allRows.filter(r => r.d.tier === tierFilter);
  // Update count
  const rc = document.getElementById('row-count');
  if (rc) rc.textContent = `${rows.length} / ${allRows.length} 표시`;
  // Determine min/max per heat-map metric (over filtered rows so heat reflects current peer-group)
  const metrics = {
    revPerHole: { higher:true },
    revPerHa:   { higher:true },
    revPerEmp:  { higher:true },
    opMargin:   { higher:true },
    opPerEmp:   { higher:true },
  };
  const stats = {};
  Object.keys(metrics).forEach(k => {
    const vals = rows.map(r => r[k]).filter(v => v !== null && v !== undefined);
    stats[k] = vals.length ? { min: Math.min(...vals), max: Math.max(...vals) } : null;
  });
  // Sort
  const sorted = rows.slice();
  if (sortState.key) {
    sorted.sort((a, b) => {
      const va = a[sortState.key]; const vb = b[sortState.key];
      // Nulls always to bottom regardless of direction
      if (va === null || va === undefined) return 1;
      if (vb === null || vb === undefined) return -1;
      return sortState.dir === 'desc' ? (vb - va) : (va - vb);
    });
  }
  // Build cells
  const heat = (key, val, fmt) => {
    const s = stats[key];
    const bar = (s && val !== null && val !== undefined) ? heatBar(val, s.min, s.max, metrics[key].higher) : '';
    return `<td class="num heat">${fmt}${bar}</td>`;
  };
  const html = sorted.map(r => {
    return `<tr>
      <td class="peer"><a href="clubs/${r.t.toLowerCase()}.html" style="color:var(--ops-ink); font-weight:700; text-decoration:none;">${r.t}</a><span class="peer-tag peer-tag-${r.d.tier}">${r.d.tier_label}</span></td>
      <td>${r.d.name.slice(0,22)}</td>
      <td class="num">${fmtNum(r.holes)}</td>
      <td class="num">${fmtNum(r.area, 1)}</td>
      <td class="num">${fmtNum(r.emp)}</td>
      <td class="num">${r.golfRev !== null ? r.golfRev.toFixed(1)+'B' : '—'}</td>
      ${heat('revPerHole', r.revPerHole, `<strong>${r.revPerHole !== null ? (r.revPerHole < 1 ? (r.revPerHole*1000).toFixed(0)+'M' : r.revPerHole.toFixed(2)+'B') : '—'}</strong>`)}
      ${heat('revPerHa',   r.revPerHa,   r.revPerHa !== null ? (r.revPerHa < 1 ? (r.revPerHa*1000).toFixed(0)+'M' : r.revPerHa.toFixed(2)+'B') : '—')}
      ${heat('revPerEmp',  r.revPerEmp,  r.revPerEmp !== null ? (r.revPerEmp < 1 ? (r.revPerEmp*1000).toFixed(0)+'M' : r.revPerEmp.toFixed(2)+'B') : '—')}
      ${heat('opMargin',   r.opMargin,   fmtPct(r.opMargin))}
      ${heat('opPerEmp',   r.opPerEmp,   r.opPerEmp !== null ? (Math.abs(r.opPerEmp) < 1 ? (r.opPerEmp*1000).toFixed(0)+'M' : r.opPerEmp.toFixed(2)+'B') : '—')}
    </tr>`;
  });
  document.getElementById('main-tbody').innerHTML = html.join('');
  // Update header indicators
  document.querySelectorAll('#main-table .sortable').forEach(th => {
    th.classList.remove('asc','desc');
    if (th.dataset.sort === sortState.key) th.classList.add(sortState.dir);
  });
}

function render(year){
  // Update year labels
  ['yr1','yr2','yr3'].forEach(id => { const el = document.getElementById(id); if (el) el.textContent = 'FY' + year; });
  renderMain(year);

  // Section 2: leaderboard (rev/hole, only peers w/ both)
  const lb = [];
  PEER_ORDER.forEach(t => {
    const d = PEER_DATA[t];
    const golfRev = (d.golf_seg && d.golf_seg[year]) ? d.golf_seg[year] : null;
    if (!d.holes || !golfRev) return;
    lb.push({t, d, val: (golfRev/1e9)/d.holes});
  });
  lb.sort((a,b) => b.val - a.val);
  document.getElementById('lb-tbody').innerHTML = lb.map((row, i) => `<tr>
      <td class="num"><strong>${i+1}</strong></td>
      <td class="peer"><a href="clubs/${row.t.toLowerCase()}.html" style="color:var(--ops-ink); font-weight:700; text-decoration:none;">${row.t}</a><span class="peer-tag peer-tag-${row.d.tier}">${row.d.tier_label}</span></td>
      <td>${row.d.name.slice(0,30)}</td>
      <td class="num">${row.d.holes}</td>
      <td class="num">${(row.d.golf_seg[year]/1e9).toFixed(1)}B</td>
      <td class="num"><strong style="color:var(--ops-green);">${row.val.toFixed(2)}B</strong></td>
    </tr>`).join('');

  // Section 3: tier average
  const tierAcc = {pp:{holes:[],area:[],rh:[],ra:[]}, resort:{holes:[],area:[],rh:[],ra:[]}, twn:{holes:[],area:[],rh:[],ra:[]}};
  PEER_ORDER.forEach(t => {
    const d = PEER_DATA[t];
    const tk = d.tier;
    if (d.holes) tierAcc[tk].holes.push(d.holes);
    if (d.area) tierAcc[tk].area.push(d.area);
    const golfRev = (d.golf_seg && d.golf_seg[year]) ? d.golf_seg[year] : null;
    if (d.holes && golfRev) tierAcc[tk].rh.push((golfRev/1e9)/d.holes);
    if (d.area && golfRev) tierAcc[tk].ra.push((golfRev/1e9)/d.area);
  });
  const avg = (arr) => arr.length ? arr.reduce((s,x)=>s+x,0)/arr.length : null;
  const tierRows = ['pp','resort','twn'].map(tk => {
    const a = tierAcc[tk];
    const count = PEER_ORDER.filter(t => PEER_DATA[t].tier === tk).length;
    return `<tr>
      <td><strong>${TIER_LABEL[tk]}</strong></td>
      <td class="num">${count}</td>
      <td class="num">${fmtNum(avg(a.holes))}</td>
      <td class="num">${fmtNum(avg(a.area), 1)}</td>
      <td class="num"><strong>${avg(a.rh) !== null ? avg(a.rh).toFixed(2)+'B' : '—'}</strong></td>
      <td class="num">${avg(a.ra) !== null ? avg(a.ra).toFixed(2)+'B' : '—'}</td>
    </tr>`;
  });
  document.getElementById('tier-tbody').innerHTML = tierRows.join('');
}

let currentYear = '2024';

// Export currently rendered Section 1 table as TSV/CSV
function buildTableExport(year, sep) {
  const allRows = computeMainRows(year);
  const rows = (tierFilter === 'all') ? allRows : allRows.filter(r => r.d.tier === tierFilter);
  // Sort same as render
  const sorted = rows.slice();
  if (sortState.key) {
    sorted.sort((a,b) => {
      const va = a[sortState.key]; const vb = b[sortState.key];
      if (va === null || va === undefined) return 1;
      if (vb === null || vb === undefined) return -1;
      return sortState.dir === 'desc' ? (vb - va) : (va - vb);
    });
  }
  const headers = ['Peer','그룹명','Tier','홀','면적(ha)','정직원','골프매출(B IDR)','홀당매출(B IDR)','ha당매출(B IDR)','1인당매출(B IDR)','영업이익률(%)','1인당영업이익(B IDR)'];
  const esc = (v) => {
    if (v === null || v === undefined) return '';
    const s = String(v);
    if (sep === ',' && (s.includes(',') || s.includes('"') || s.includes('\n'))) {
      return '"' + s.replace(/"/g,'""') + '"';
    }
    return s;
  };
  const fmt = (v, dp) => (v === null || v === undefined) ? '' : v.toFixed(dp === undefined ? 2 : dp);
  const lines = [headers.map(esc).join(sep)];
  sorted.forEach(r => {
    lines.push([
      esc(r.t),
      esc(r.d.name),
      esc(r.d.tier_label),
      fmt(r.holes, 0),
      fmt(r.area, 1),
      fmt(r.emp, 0),
      fmt(r.golfRev, 2),
      fmt(r.revPerHole, 3),
      fmt(r.revPerHa, 3),
      fmt(r.revPerEmp, 3),
      fmt(r.opMargin, 2),
      fmt(r.opPerEmp, 3),
    ].join(sep));
  });
  return lines.join('\n');
}

async function flashSuccess(btn, label){
  const orig = btn.textContent;
  btn.textContent = label;
  btn.classList.add('success');
  setTimeout(() => { btn.textContent = orig; btn.classList.remove('success'); }, 1500);
}

(function(){
  document.querySelectorAll('.year-btn').forEach(b => {
    b.addEventListener('click', () => {
      document.querySelectorAll('.year-btn').forEach(x => x.classList.remove('active'));
      b.classList.add('active');
      currentYear = b.dataset.year;
      render(currentYear);
    });
  });
  // Sortable header click
  document.querySelectorAll('#main-table .sortable').forEach(th => {
    th.addEventListener('click', () => {
      const k = th.dataset.sort;
      if (sortState.key === k) {
        sortState.dir = (sortState.dir === 'desc') ? 'asc' : 'desc';
      } else {
        sortState.key = k;
        sortState.dir = 'desc';
      }
      renderMain(currentYear);
    });
  });
  // Tier filter pills
  document.querySelectorAll('#tier-pills .tier-pill').forEach(p => {
    p.addEventListener('click', () => {
      document.querySelectorAll('#tier-pills .tier-pill').forEach(x => x.classList.remove('active'));
      p.classList.add('active');
      tierFilter = p.dataset.tier;
      renderMain(currentYear);
    });
  });
  // Copy TSV (clipboard-friendly for spreadsheets)
  document.getElementById('copy-tsv-btn').addEventListener('click', async (e) => {
    const tsv = buildTableExport(currentYear, '\t');
    try {
      await navigator.clipboard.writeText(tsv);
      flashSuccess(e.currentTarget, '✓ 복사됨');
    } catch (err) {
      const ta = document.createElement('textarea');
      ta.value = tsv; document.body.appendChild(ta); ta.select(); document.execCommand('copy'); document.body.removeChild(ta);
      flashSuccess(e.currentTarget, '✓ 복사됨');
    }
  });
  // CSV download
  document.getElementById('download-csv-btn').addEventListener('click', (e) => {
    const csv = '﻿' + buildTableExport(currentYear, ',');  // BOM for Excel ko-KR
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    const tierTag = tierFilter === 'all' ? 'all' : tierFilter;
    a.href = url; a.download = `unit-economics_FY${currentYear}_${tierTag}.csv`;
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
    URL.revokeObjectURL(url);
    flashSuccess(e.currentTarget, '✓ 다운로드');
  });
  render(currentYear);
})();
</script>
</body>
</html>
'''

html = html.replace('__PEER_DATA__', peer_data_json)
html = html.replace('__PEER_ORDER__', json.dumps(peers_sorted))
with open('unit-economics.html','w',encoding='utf-8') as f:
    f.write(html)
print(f'unit-economics.html: {os.path.getsize("unit-economics.html")/1024:.1f} KB')
