"""Build unit-economics·revenue·cost-hr with year selector + comparison table."""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import json
import os

clubs = json.load(open('data/_clubs_meta.json','r',encoding='utf-8'))
d5y = json.load(open('../../data/company_financials_5y.json','r',encoding='utf-8'))
fin = {c['ticker']: c for c in d5y['companies'] if 'ticker' in c}

peers_v2 = ['DMIG','PIPG','GOLF','MDLN','KIJA','SMDM','KPIG','SMRA','BSDE','CTRA','ELTY','LPKR','PWON']

# Golf segment data per peer (segment-only peers)
golf_segment = {
    'DMIG': {'2022': 217.7, '2023': 245.0, '2024': 253.1, '2025': 251.3},
    'PIPG': {'2022': 162.3, '2023': 177.2, '2024': 197.6, '2025': 185.8},
    'GOLF': {'2024': 93.0, '2025': 79.4},
    'MDLN': {'2022': None, '2023': 67.9, '2024': 74.4, '2025': 95.3},
    'KIJA': {'2024': 85.0},
    'SMDM': {'2022': 51.7, '2023': 60.9, '2024': 63.3},
}

# Build master peer data table: rows = peer, cols by FY
def build_peer_data():
    data = {}
    for t in peers_v2:
        c5y = fin.get(t,{})
        yearly = c5y.get('yearly',{})
        data[t] = {}
        for fy in ['2022','2023','2024','2025']:
            y = yearly.get(fy, {})
            rev = y.get('revenue')
            op = y.get('operating_profit')
            np_ = y.get('net_profit')
            ta = y.get('total_assets')
            te = y.get('total_equity')
            tl = y.get('total_liabilities')
            data[t][fy] = {
                'revenue': rev/1e9 if rev else None,
                'op': op/1e9 if op else None,
                'np': np_/1e9 if np_ else None,
                'ta': ta/1e9 if ta else None,
                'te': te/1e9 if te else None,
                'tl': tl/1e9 if tl else None,
                'margin': (np_/rev*100) if (rev and np_) else None,
                'opmargin': (op/rev*100) if (rev and op) else None,
                'roa': (np_/ta*100) if (ta and np_) else None,
                'debt_ratio': (tl/ta*100) if (ta and tl) else None,
                'golf_rev': golf_segment.get(t,{}).get(fy),
            }
    return data

peer_data = build_peer_data()

# Common page template
def make_page(title_h1, lede, page_id, table_cols, row_data_fn, active_tab, page_file):
    """
    title_h1: H1 text
    lede: lede paragraph
    page_id: short id (ue / rev / cost / assets)
    table_cols: list of (key, label, num_format) for columns
    row_data_fn: function(ticker, fy_data) -> dict of values per col key
    active_tab: nav active class anchor text
    """
    # Build all-FY rows JSON for client-side switching
    rows_data = {}
    for fy in ['2022','2023','2024','2025']:
        rows = []
        for t in peers_v2:
            c = clubs[t]
            d = peer_data[t].get(fy, {})
            row_vals = row_data_fn(t, d)
            row_vals['_ticker'] = t
            row_vals['_name'] = c['name']
            row_vals['_tier'] = c['tier']
            row_vals['_tier_label'] = c['tier_label']
            rows.append(row_vals)
        rows_data[fy] = rows

    # Tier sort
    def torder(t):
        return {'pp':1,'resort':2,'twn':3}.get(clubs[t]['tier'],9)
    for fy in rows_data:
        rows_data[fy].sort(key=lambda r: (torder(r['_ticker']), r['_ticker']))

    # Build columns headers
    headers = ''.join(f'<th{(" class=\"num\"" if col[2] else "")}>{col[1]}</th>' for col in table_cols)

    # Inline data
    data_js = json.dumps(rows_data, ensure_ascii=False)

    # JS to render rows
    cols_js = json.dumps([col[0] for col in table_cols])

    nav_anchors = {
        'unit-economics.html': '단위 경제',
        'revenue.html': '매출',
        'cost-hr.html': '비용',
        'assets.html': '시설',
    }
    # Build nav with active class
    nav_items = [
        ('clubs/index.html','⛳ 클럽별'),
        ('overview.html','Peer 카드'),
        ('unit-economics.html','단위 경제'),
        ('revenue.html','매출'),
        ('cost-hr.html','비용'),
        ('assets.html','시설'),
        ('risk.html','위험'),
    ]
    nav_html = ''
    for href, label in nav_items:
        cls = ' class="active"' if label == active_tab else ''
        nav_html += f'<a href="{href}"{cls}>{label}</a>'
    nav_html += '<a href="../../index.html" class="back">← 지도</a>'

    template = '''<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>__TITLE__ — 인도네시아 골프 운영 벤치마크</title>
<link rel="icon" type="image/svg+xml" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Ccircle cx='32' cy='32' r='30' fill='%232D5016'/%3E%3Ccircle cx='32' cy='32' r='12' fill='%23F5F1E8'/%3E%3C/svg%3E" />
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Pretendard:wght@400;500;600;700&display=swap" rel="stylesheet" />
<link rel="stylesheet" href="ops-style.css?v=20260512c52" />
<style>
  .year-selector { display: flex; gap: 6px; margin: 16px 0; }
  .year-btn { padding: 8px 18px; border: 1px solid var(--ops-line); background: var(--ops-surface); border-radius: 6px; font-size: 13px; font-weight: 700; cursor: pointer; color: var(--ops-ink-soft); transition: all 0.15s; }
  .year-btn.active { background: var(--ops-green); color: white; border-color: var(--ops-green); }
  .year-btn:hover:not(.active) { border-color: var(--ops-green); color: var(--ops-green); }
  .year-btn:disabled { opacity: 0.4; cursor: not-allowed; }
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
    <nav class="ops-nav">__NAV__</nav>
  </div>
</header>

<section class="ops-hero">
  <div class="ops-wrap">
    <h1>__TITLE__</h1>
    <p class="lede">__LEDE__</p>
    <div class="year-selector" id="year-selector">
      <button class="year-btn" data-year="2022">FY2022</button>
      <button class="year-btn" data-year="2023">FY2023</button>
      <button class="year-btn active" data-year="2024">FY2024</button>
      <button class="year-btn" data-year="2025">FY2025</button>
    </div>
  </div>
</section>

<section class="ops-section">
  <div class="ops-wrap">
    <div class="tbl-card scroll-x">
      <table class="ops-tbl" id="peer-tbl">
        <thead>
          <tr>
            <th>Peer</th>
            <th>분류</th>
__HEADERS__
          </tr>
        </thead>
        <tbody id="peer-tbody"></tbody>
      </table>
    </div>
  </div>
</section>

<footer class="ops-foot">
  <div class="ops-wrap">
    <p>Peer Group v2 · IDR · 13 peer 비교.</p>
  </div>
</footer>

<script src="operations.js?v=20260512c2" defer></script>
<script>
(function(){
  const data = __DATA__;
  const cols = __COLS__;
  const tbody = document.getElementById('peer-tbody');

  function fmt(v) {
    if (v === null || v === undefined) return '<span style="color:#94a3b8;">—</span>';
    if (typeof v !== 'number') return v;
    if (Math.abs(v) >= 1000) return (v/1000).toFixed(2) + 'T';
    if (Math.abs(v) >= 10) return v.toFixed(1);
    return v.toFixed(2);
  }
  function fmtPct(v) {
    if (v === null || v === undefined) return '<span style="color:#94a3b8;">—</span>';
    var col = v > 0 ? 'color:#16a34a;' : (v < 0 ? 'color:#b91c1c;' : '');
    return '<span style="' + col + 'font-weight:700;">' + v.toFixed(1) + '%</span>';
  }

  function render(year) {
    const rows = data[year] || [];
    tbody.innerHTML = rows.map(function(r) {
      var tdPeer = '<td class="peer"><a href="clubs/' + r._ticker.toLowerCase() + '.html" style="color:var(--ops-ink); font-weight:700; text-decoration:none;">' + r._ticker + '</a><span class="peer-tag peer-tag-' + r._tier + '">' + r._tier_label + '</span></td>';
      var tdName = '<td><a href="clubs/' + r._ticker.toLowerCase() + '.html" style="color:var(--ops-ink-soft); font-size:11.5px; text-decoration:none;">' + r._name + '</a></td>';
      var tdData = cols.map(function(k){
        var v = r[k];
        if (k === 'margin' || k === 'opmargin' || k === 'roa' || k === 'debt_ratio') {
          return '<td class="num">' + fmtPct(v) + '</td>';
        }
        return '<td class="num">' + fmt(v) + '</td>';
      }).join('');
      return '<tr>' + tdPeer + tdName + tdData + '</tr>';
    }).join('');
  }

  document.querySelectorAll('.year-btn').forEach(function(b){
    b.addEventListener('click', function(){
      document.querySelectorAll('.year-btn').forEach(function(x){x.classList.remove('active');});
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

    html = template
    html = html.replace('__TITLE__', title_h1)
    html = html.replace('__LEDE__', lede)
    html = html.replace('__NAV__', nav_html)
    html = html.replace('__HEADERS__', headers)
    html = html.replace('__DATA__', data_js)
    html = html.replace('__COLS__', cols_js)

    with open(page_file,'w',encoding='utf-8') as f:
        f.write(html)
    return os.path.getsize(page_file)/1024

# === unit-economics.html ===
def ue_row(t, d):
    holes_map = {'DMIG':36, 'PIPG':18, 'GOLF':36, 'MDLN':18, 'KIJA':None, 'SMDM':18, 'KPIG':18, 'SMRA':18, 'BSDE':None, 'CTRA':36, 'ELTY':36, 'LPKR':18, 'PWON':18}
    holes = holes_map.get(t)
    golf_rev_bn = d.get('golf_rev')
    return {
        'rev': d.get('revenue'),
        'op': d.get('op'),
        'np': d.get('np'),
        'margin': d.get('margin'),
        'rev_per_hole': (golf_rev_bn*1000/holes) if (golf_rev_bn and holes) else None,
    }

ue_cols = [
    ('rev', '그룹 매출 (Rp bn)', True),
    ('op', '영업이익 (Rp bn)', True),
    ('np', '순이익 (Rp bn)', True),
    ('margin', '순이익률', True),
    ('rev_per_hole', '홀당 골프 매출 (Rp m)', True),
]
sz = make_page('단위 경제', '13 peer 그룹 P&L + 골프 부문 단위 경제. 연도 선택으로 시계열 비교.', 'ue', ue_cols, ue_row, '단위 경제', 'unit-economics.html')
print(f'  unit-economics.html: {sz:.1f} KB')

# === revenue.html ===
def rev_row(t, d):
    return {
        'rev': d.get('revenue'),
        'golf_rev': d.get('golf_rev'),
        'golf_pct': (d.get('golf_rev')/d.get('revenue')*100) if (d.get('golf_rev') and d.get('revenue')) else None,
        'op': d.get('op'),
        'np': d.get('np'),
        'margin': d.get('margin'),
    }
rev_cols = [
    ('rev', '그룹 매출 (Rp bn)', True),
    ('golf_rev', '골프 부문 매출 (Rp bn)', True),
    ('golf_pct', '골프 비중', True),
    ('op', '영업이익', True),
    ('np', '순이익', True),
    ('margin', '순이익률', True),
]
sz = make_page('매출', '그룹 매출 vs 골프 부문 매출 분리. 연도 선택으로 시계열 비교.', 'rev', rev_cols, rev_row, '매출', 'revenue.html')
print(f'  revenue.html: {sz:.1f} KB')

# === cost-hr.html ===
def cost_row(t, d):
    rev = d.get('revenue')
    op = d.get('op')
    np_ = d.get('np')
    cogs_estimate = (rev - op) if (rev and op) else None  # rough proxy when not Tier 1
    return {
        'rev': rev,
        'op': op,
        'np': np_,
        'opmargin': d.get('opmargin'),
        'margin': d.get('margin'),
        'cogs_est': cogs_estimate,
    }
cost_cols = [
    ('rev', '매출 (Rp bn)', True),
    ('cogs_est', '매출원가+OpEx 합산 추정 (Rp bn)', True),
    ('op', '영업이익 (Rp bn)', True),
    ('opmargin', '영업이익률', True),
    ('np', '순이익', True),
    ('margin', '순이익률', True),
]
sz = make_page('비용', '매출 대비 비용 구조 (영업이익률 + 순이익률). 연도 선택으로 시계열 비교.', 'cost', cost_cols, cost_row, '비용', 'cost-hr.html')
print(f'  cost-hr.html: {sz:.1f} KB')
