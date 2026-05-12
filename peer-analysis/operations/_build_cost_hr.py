"""Build cost-hr.html — year selector + 13-peer cost structure + line detail (COGS·OpEx)."""
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

peers_sorted = sorted(peers_v2, key=lambda t: (torder(t), t))

# Build PEER_DATA for cost-structure comparison
peer_data = {}
for t in peers_sorted:
    c = clubs[t]
    cy = fin.get(t,{}).get('yearly',{})
    yearly = {}
    for y in ['2020','2021','2022','2023','2024']:
        yy = cy.get(y, {})
        yearly[y] = {
            'rev': yy.get('revenue'),
            'op': yy.get('operating_profit'),
            'np': yy.get('net_profit'),
            'ebitda': yy.get('ebitda'),
        }
    peer_data[t] = {
        'name': c['name'],
        'tier': c['tier'],
        'tier_label': c['tier_label'],
        'yearly': yearly,
    }

peer_data_json = json.dumps(peer_data, ensure_ascii=False)

# ============================================================
# Line detail tables — multi-year, selected year column gets yr-{year} class
# ============================================================
def fmt_bn(v):
    if v is None: return '—'
    if abs(v) >= 1e12: return f'{v/1e12:,.1f}T'
    if abs(v) >= 1e9: return f'{v/1e9:,.1f}B'
    if abs(v) >= 1e6: return f'{v/1e6:,.1f}M'
    return f'{v:,.0f}'

def build_cost_table(title, subtitle, lines_data, year_cols, tier_emoji, note_text=None):
    head_cells = ''.join(f'<th class="num yr-{y[-4:]}">{y}</th>' for y in year_cols)
    rows = []
    for ln in lines_data['lines']:
        cells = ''
        for y in year_cols:
            v = ln.get(y)
            cells += f'<td class="num yr-{y[-4:]}">{fmt_bn(v)}</td>'
        en_label = ln.get('en_label','—')
        rows.append(f'''            <tr>
              <td>{ln["id_label"]}<br><span style="color:var(--ops-muted); font-size:11px;">{en_label}</span></td>
              {cells}
            </tr>''')
    tot = lines_data.get('total',{})
    total_cells = ''.join(f'<td class="num yr-{y[-4:]}">{fmt_bn(tot.get(y))}</td>' for y in year_cols)
    rows.append(f'''            <tr style="background:rgba(45,80,22,0.06); font-weight:700;">
              <td>합계</td>
              {total_cells}
            </tr>''')
    extra = f'<p style="font-size:11.5px; color:var(--ops-muted); margin:4px 0 0 0; font-style:italic;">{note_text}</p>' if note_text else ''
    return f'''      <div style="margin-bottom:32px;">
        <h3 style="font-size:16px; margin:0 0 10px 0;">{tier_emoji} {title}</h3>
        <p style="font-size:12px; color:var(--ops-muted); margin:0 0 8px 0;">{subtitle}</p>
        <div class="tbl-card scroll-x">
          <table class="ops-tbl">
            <thead><tr><th>비용 라인</th>{head_cells}</tr></thead>
            <tbody>
{chr(10).join(rows)}
            </tbody>
          </table>
        </div>
        {extra}
      </div>'''

# ============================================================
# Section: COGS lines
# ============================================================
cogs_section = []

# DMIG cogs (3 lines, FY22-FY24)
cogs_section.append(build_cost_table(
    'DMIG · 매출원가 (Note 24)',
    '사업부별 직접원가 — 3 라인 공시',
    notes['DMIG']['cogs_note'],
    ['FY2022','FY2023','FY2024'],
    '🟦'
))

# PIPG cogs_28 (11 lines, FY23-FY24)
cogs_section.append(build_cost_table(
    'PIPG · 매출원가 (Note 28)',
    '시설별 운영 비용 — 11 라인 공시',
    notes['PIPG']['cogs_note_28'],
    ['FY2023','FY2024'],
    '🟦'
))

# GOLF cogs_30 (4 lines, FY23-FY24)
cogs_section.append(build_cost_table(
    'GOLF · 매출원가 (Note 30)',
    '사업부별 직접원가 (골프·부동산·F&B 등)',
    notes['GOLF']['cogs_note_30'],
    ['FY2023','FY2024'],
    '🟨'
))

# MDLN — special: golf + clubhouse breakdown
m = notes['MDLN']['cogs_note_26']
mdln_rows = []
mdln_rows.append('            <tr style="background:rgba(245,158,11,0.08); font-weight:700;"><td colspan="3">골프 코스 직접원가</td></tr>')
for ln in m.get('golf_course_direct_cost_lines',[]):
    mdln_rows.append(f'''            <tr>
              <td style="padding-left:24px;">{ln["id_label"]}</td>
              <td class="num yr-2023">{fmt_bn(ln.get("FY2023"))}</td>
              <td class="num yr-2024">{fmt_bn(ln.get("FY2024"))}</td>
            </tr>''')
gs = m.get('golf_course_subtotal',{})
mdln_rows.append(f'''            <tr style="font-weight:600;">
              <td style="padding-left:24px;">— 골프 소계</td>
              <td class="num yr-2023">{fmt_bn(gs.get("FY2023"))}</td>
              <td class="num yr-2024">{fmt_bn(gs.get("FY2024"))}</td>
            </tr>''')
mdln_rows.append('            <tr style="background:rgba(245,158,11,0.08); font-weight:700;"><td colspan="3">클럽하우스·F&B 직접원가</td></tr>')
for ln in m.get('club_house_restaurant_direct_cost_lines',[]):
    mdln_rows.append(f'''            <tr>
              <td style="padding-left:24px;">{ln["id_label"]}</td>
              <td class="num yr-2023">{fmt_bn(ln.get("FY2023"))}</td>
              <td class="num yr-2024">{fmt_bn(ln.get("FY2024"))}</td>
            </tr>''')
cs = m.get('club_house_restaurant_subtotal',{})
mdln_rows.append(f'''            <tr style="font-weight:600;">
              <td style="padding-left:24px;">— 클럽하우스 소계</td>
              <td class="num yr-2023">{fmt_bn(cs.get("FY2023"))}</td>
              <td class="num yr-2024">{fmt_bn(cs.get("FY2024"))}</td>
            </tr>''')
gcs = m.get('golf_plus_clubhouse_subtotal',{})
mdln_rows.append(f'''            <tr style="background:rgba(45,80,22,0.06); font-weight:700;">
              <td>골프+클럽하우스 합계</td>
              <td class="num yr-2023">{fmt_bn(gcs.get("FY2023"))}</td>
              <td class="num yr-2024">{fmt_bn(gcs.get("FY2024"))}</td>
            </tr>''')
cogs_section.append(f'''      <div style="margin-bottom:32px;">
        <h3 style="font-size:16px; margin:0 0 10px 0;">🟩 MDLN · 매출원가 (Note 26)</h3>
        <p style="font-size:12px; color:var(--ops-muted); margin:0 0 8px 0;">골프·클럽하우스 부문별 직접원가 (호텔 부문 제외)</p>
        <div class="tbl-card scroll-x">
          <table class="ops-tbl">
            <thead><tr><th>비용 라인</th><th class="num yr-2023">FY2023</th><th class="num yr-2024">FY2024</th></tr></thead>
            <tbody>
{chr(10).join(mdln_rows)}
            </tbody>
          </table>
        </div>
      </div>''')

cogs_html = '\n'.join(cogs_section)

# ============================================================
# Section: OpEx lines
# ============================================================
opex_section = []

# DMIG opex (17 lines, FY22-FY24)
opex_section.append(build_cost_table(
    'DMIG · 판관비 (Note 25)',
    '17 라인 — 인건비·시설관리·세금·감가상각 등',
    notes['DMIG']['opex_note'],
    ['FY2022','FY2023','FY2024'],
    '🟦'
))

# PIPG opex_29 (17 lines, FY23-FY24)
opex_section.append(build_cost_table(
    'PIPG · 판관비 (Note 29)',
    '17 라인 — 세금·인허가·인건비·법률·감가 등',
    notes['PIPG']['opex_note_29'],
    ['FY2023','FY2024'],
    '🟦'
))

# GOLF — Selling (Note 31) + G&A (Note 32) combined
sel = notes['GOLF']['selling_note_31']
ga = notes['GOLF']['ga_note_32']
golf_rows = []
golf_rows.append('            <tr style="background:rgba(245,158,11,0.08); font-weight:700;"><td colspan="3">판매비 (Note 31)</td></tr>')
for ln in sel['lines']:
    golf_rows.append(f'''            <tr>
              <td style="padding-left:24px;">{ln["id_label"]}<br><span style="color:var(--ops-muted); font-size:11px;">{ln.get("en_label","—")}</span></td>
              <td class="num yr-2023">{fmt_bn(ln.get("FY2023"))}</td>
              <td class="num yr-2024">{fmt_bn(ln.get("FY2024"))}</td>
            </tr>''')
st = sel.get('total',{})
golf_rows.append(f'''            <tr style="font-weight:600;">
              <td style="padding-left:24px;">— 판매비 소계</td>
              <td class="num yr-2023">{fmt_bn(st.get("FY2023"))}</td>
              <td class="num yr-2024">{fmt_bn(st.get("FY2024"))}</td>
            </tr>''')
golf_rows.append('            <tr style="background:rgba(245,158,11,0.08); font-weight:700;"><td colspan="3">일반관리비 (Note 32)</td></tr>')
for ln in ga['lines']:
    golf_rows.append(f'''            <tr>
              <td style="padding-left:24px;">{ln["id_label"]}<br><span style="color:var(--ops-muted); font-size:11px;">{ln.get("en_label","—")}</span></td>
              <td class="num yr-2023">{fmt_bn(ln.get("FY2023"))}</td>
              <td class="num yr-2024">{fmt_bn(ln.get("FY2024"))}</td>
            </tr>''')
gt = ga.get('total',{})
golf_rows.append(f'''            <tr style="font-weight:600;">
              <td style="padding-left:24px;">— G&A 소계</td>
              <td class="num yr-2023">{fmt_bn(gt.get("FY2023"))}</td>
              <td class="num yr-2024">{fmt_bn(gt.get("FY2024"))}</td>
            </tr>''')
opex_section.append(f'''      <div style="margin-bottom:32px;">
        <h3 style="font-size:16px; margin:0 0 10px 0;">🟨 GOLF · 판매비 + 일반관리비 (Note 31·32)</h3>
        <p style="font-size:12px; color:var(--ops-muted); margin:0 0 8px 0;">판매비 5 라인 + G&A 16 라인</p>
        <div class="tbl-card scroll-x">
          <table class="ops-tbl">
            <thead><tr><th>비용 라인</th><th class="num yr-2023">FY2023</th><th class="num yr-2024">FY2024</th></tr></thead>
            <tbody>
{chr(10).join(golf_rows)}
            </tbody>
          </table>
        </div>
      </div>''')

# KPIG G&A note 34 (13 lines)
opex_section.append(build_cost_table(
    'KPIG · 일반관리비 (Note 34)',
    '그룹 G&A 13 라인 — 골프 포함 전 사업부',
    notes['KPIG']['ga_note_34'],
    ['FY2023','FY2024'],
    '🟩'
))

opex_html = '\n'.join(opex_section)

# ============================================================
# Assemble HTML
# ============================================================
html = '''<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>비용 — 인도네시아 골프 운영 벤치마크</title>
<link rel="icon" type="image/svg+xml" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Ccircle cx='32' cy='32' r='30' fill='%232D5016'/%3E%3Ccircle cx='32' cy='32' r='12' fill='%23F5F1E8'/%3E%3C/svg%3E" />
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Pretendard:wght@400;500;600;700&display=swap" rel="stylesheet" />
<link rel="stylesheet" href="ops-style.css?v=20260512c54" />
<style>
  .year-bar { display:flex; align-items:center; gap:10px; flex-wrap:wrap; margin:14px 0 4px 0; }
  .year-bar label { font-size:13px; font-weight:600; color:var(--ops-ink-soft); }
  .year-btn { padding:6px 14px; border:1px solid var(--ops-line); background:var(--ops-surface); border-radius:6px; font-size:12.5px; font-weight:600; cursor:pointer; color:var(--ops-ink-soft); }
  .year-btn.active { background:var(--ops-green); color:white; border-color:var(--ops-green); }
  .cost-tab-bar { display:flex; gap:6px; flex-wrap:wrap; margin:16px 0 24px 0; border-bottom:2px solid var(--ops-line); }
  .cost-tab { padding:10px 18px; cursor:pointer; font-size:13px; font-weight:600; color:var(--ops-ink-soft); border-bottom:3px solid transparent; margin-bottom:-2px; }
  .cost-tab.active { color:var(--ops-green); border-bottom-color:var(--ops-green); }
  .cost-panel { display:none; }
  .cost-panel.active { display:block; }
  .yr-hl { background:rgba(245,158,11,0.10); font-weight:700; }
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
    <nav class="ops-nav"><a href="clubs/index.html">⛳ 클럽</a><a href="unit-economics.html">단위 경제</a><a href="revenue.html">매출</a><a href="cost-hr.html" class="active">비용</a><a href="assets.html">시설</a><a href="risk.html">위험</a><a href="../../index.html" class="back">← 지도</a></nav>
  </div>
</header>

<section class="ops-hero">
  <div class="ops-wrap">
    <h1>비용 — 동급 비교</h1>
    <p class="lede">기준 연도 선택 → 13 peer 비용 구조 비교. 라인 상세표는 선택 연도 컬럼 하이라이트.</p>
    <div class="year-bar">
      <label>기준 연도:</label>
      <button class="year-btn" data-year="2020">FY2020</button>
      <button class="year-btn" data-year="2021">FY2021</button>
      <button class="year-btn" data-year="2022">FY2022</button>
      <button class="year-btn" data-year="2023">FY2023</button>
      <button class="year-btn active" data-year="2024">FY2024</button>
    </div>
    <div class="cost-tab-bar">
      <div class="cost-tab active" data-panel="cmp">① 13-peer 비용 구조 %</div>
      <div class="cost-tab" data-panel="cogs">② 매출원가 라인 (4 peer)</div>
      <div class="cost-tab" data-panel="opex">③ 판관비 라인 (4 peer)</div>
    </div>
  </div>
</section>

<section class="ops-section">
  <div class="ops-wrap">
    <div class="cost-panel active" id="panel-cmp">
      <h2 style="font-size:17px; margin:0 0 14px 0;">13-peer 비용 구조 — <span class="yr-label">FY2024</span></h2>
      <p style="font-size:12px; color:var(--ops-muted); margin:0 0 12px 0;">선택 연도 그룹 P&L 기반. 총 비용 = 매출 − 영업이익. EBITDA·순이익 마진 포함.</p>
      <div class="tbl-card scroll-x">
        <table class="ops-tbl">
          <thead>
            <tr>
              <th>Peer</th>
              <th>그룹명</th>
              <th class="num">매출</th>
              <th class="num">총 비용</th>
              <th class="num">총 비용 / 매출</th>
              <th class="num">영업이익률</th>
              <th class="num">EBITDA 마진</th>
              <th class="num">순이익률</th>
            </tr>
          </thead>
          <tbody id="cmp-tbody"></tbody>
        </table>
      </div>
    </div>

    <div class="cost-panel" id="panel-cogs">
__COGS_SECTION__
    </div>

    <div class="cost-panel" id="panel-opex">
__OPEX_SECTION__
    </div>
  </div>
</section>

<footer class="ops-foot">
  <div class="ops-wrap">
    <p>비용 구조 비율: 연결 P&L FY2020-FY2024. 라인 상세: AR Note 23·24·26·28·29·30·31·32·34. 단위 IDR.</p>
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

function render(year){
  document.querySelectorAll('.yr-label').forEach(el => el.textContent = 'FY' + year);

  const rows = PEER_ORDER.map(t => {
    const d = PEER_DATA[t];
    const y = d.yearly[year] || {};
    const rev = y.rev; const op = y.op; const np = y.np; const ebitda = y.ebitda;
    const totalCost = (rev !== null && rev !== undefined && op !== null && op !== undefined) ? (rev - op) : null;
    const costRatio = (rev && totalCost !== null) ? (totalCost/rev*100) : null;
    const opMargin = (rev && op !== null && op !== undefined) ? (op/rev*100) : null;
    const ebMargin = (rev && ebitda !== null && ebitda !== undefined) ? (ebitda/rev*100) : null;
    const npMargin = (rev && np !== null && np !== undefined) ? (np/rev*100) : null;
    return `<tr>
      <td class="peer"><a href="clubs/${t.toLowerCase()}.html" style="color:var(--ops-ink); font-weight:700; text-decoration:none;">${t}</a><span class="peer-tag peer-tag-${d.tier}">${d.tier_label}</span></td>
      <td>${d.name.slice(0,24)}</td>
      <td class="num">${fmtBn(rev)}</td>
      <td class="num">${fmtBn(totalCost)}</td>
      <td class="num">${fmtPct(costRatio)}</td>
      <td class="num"><strong>${fmtPct(opMargin)}</strong></td>
      <td class="num">${fmtPct(ebMargin)}</td>
      <td class="num">${fmtPct(npMargin)}</td>
    </tr>`;
  });
  document.getElementById('cmp-tbody').innerHTML = rows.join('');

  // Highlight selected year columns in line tables
  document.querySelectorAll('.yr-hl').forEach(el => el.classList.remove('yr-hl'));
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
  document.querySelectorAll('.cost-tab').forEach(t => t.addEventListener('click', () => {
    document.querySelectorAll('.cost-tab').forEach(x => x.classList.remove('active'));
    document.querySelectorAll('.cost-panel').forEach(p => p.classList.remove('active'));
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
html = html.replace('__COGS_SECTION__', cogs_html)
html = html.replace('__OPEX_SECTION__', opex_html)

with open('cost-hr.html','w',encoding='utf-8') as f:
    f.write(html)
print(f'cost-hr.html: {os.path.getsize("cost-hr.html")/1024:.1f} KB')
