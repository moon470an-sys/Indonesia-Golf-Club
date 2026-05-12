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
    <p style="font-size:12px; color:var(--ops-muted); margin:0 0 12px 0;">홀당·ha당 매출 = 골프 부문 매출 ÷ 단위 (Pure-play는 그룹 매출). 1인당 매출·영업이익은 그룹 P&L.</p>
    <div class="tbl-card scroll-x">
      <table class="ops-tbl">
        <thead>
          <tr>
            <th>Peer</th>
            <th>그룹명</th>
            <th class="num">홀</th>
            <th class="num">면적 (ha)</th>
            <th class="num">정직원</th>
            <th class="num">골프 매출</th>
            <th class="num">홀당 매출</th>
            <th class="num">ha당 매출</th>
            <th class="num">1인당 매출</th>
            <th class="num">영업이익률</th>
            <th class="num">1인당 영업이익</th>
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

function render(year){
  // Update year labels
  ['yr1','yr2','yr3'].forEach(id => { const el = document.getElementById(id); if (el) el.textContent = 'FY' + year; });

  // Section 1: main per-unit table
  const main = [];
  PEER_ORDER.forEach(t => {
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
    main.push(`<tr>
      <td class="peer"><a href="clubs/${t.toLowerCase()}.html" style="color:var(--ops-ink); font-weight:700; text-decoration:none;">${t}</a><span class="peer-tag peer-tag-${d.tier}">${d.tier_label}</span></td>
      <td>${d.name.slice(0,22)}</td>
      <td class="num">${fmtNum(d.holes)}</td>
      <td class="num">${fmtNum(d.area, 1)}</td>
      <td class="num">${fmtNum(emp)}</td>
      <td class="num">${golfRevBn !== null ? golfRevBn.toFixed(1)+'B' : '—'}</td>
      <td class="num"><strong>${fmtPerUnit(golfRevBn, d.holes)}</strong></td>
      <td class="num">${fmtPerUnit(golfRevBn, d.area)}</td>
      <td class="num">${fmtPerUnit(grpRevBn, emp)}</td>
      <td class="num">${fmtPct(opMargin)}</td>
      <td class="num">${fmtPerUnit(grpOpBn, emp)}</td>
    </tr>`);
  });
  document.getElementById('main-tbody').innerHTML = main.join('');

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

(function(){
  document.querySelectorAll('.year-btn').forEach(b => {
    b.addEventListener('click', () => {
      document.querySelectorAll('.year-btn').forEach(x => x.classList.remove('active'));
      b.classList.add('active');
      render(b.dataset.year);
    });
  });
  render('2024');
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
