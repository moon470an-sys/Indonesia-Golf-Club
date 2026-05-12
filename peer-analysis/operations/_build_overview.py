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
    if v is None: return '<span style="color:#94a3b8;">—</span>'
    if abs(v) >= 1000: return f'Rp {v/1000:,.2f}T'
    return f'Rp {v:,.1f}B'

def fmtPct(v):
    if v is None: return '<span style="color:#94a3b8;">—</span>'
    col = 'color:#16a34a;' if v > 0 else ('color:#b91c1c;' if v < 0 else '')
    return f'<span style="{col}font-weight:700;">{v:+.1f}%</span>'

cards_html = []
for t in sorted(peers_v2, key=lambda x: (torder(x), x)):
    c = clubs[t]
    c5y = fin.get(t,{})
    y24 = c5y.get('yearly',{}).get('2024',{})
    rev = y24.get('revenue')
    np_ = y24.get('net_profit')
    ta = y24.get('total_assets')
    rev_bn = rev/1e9 if rev else None
    ta_bn = ta/1e9 if ta else None
    margin = (np_/rev*100) if (rev and np_) else None
    roa = (np_/ta*100) if (ta and np_) else None
    tier_color = {'pp':'#3b82f6','resort':'#f59e0b','twn':'#16a34a'}[c['tier']]
    cards_html.append(
        f'      <a href="clubs/{t.lower()}.html" class="peer-card" data-tier="{c["tier"]}" data-ticker="{t}" '
        f'style="background:var(--ops-surface); border:1px solid var(--ops-line); border-top:3px solid {tier_color}; '
        f'border-radius:10px; padding:16px 18px; text-decoration:none; color:inherit; display:block; transition:all 0.2s;">\n'
        f'        <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:8px;">\n'
        f'          <div>\n'
        f'            <div style="font-size:10.5px; font-weight:700; color:var(--ops-muted); letter-spacing:0.06em;">{t} · IDX</div>\n'
        f'            <div style="font-size:15px; font-weight:700; color:var(--ops-ink); line-height:1.3; margin-top:2px;">{c["name"]}</div>\n'
        f'          </div>\n'
        f'          <span class="peer-tag peer-tag-{c["tier"]}" style="white-space:nowrap;">{c["tier_label"]}</span>\n'
        f'        </div>\n'
        f'        <div style="display:grid; grid-template-columns:1fr 1fr; gap:6px 10px; margin-top:12px; font-size:11.5px;">\n'
        f'          <div><div style="color:var(--ops-muted);">FY24 매출</div><div style="font-weight:700; color:var(--ops-ink);">{fmtBn(rev_bn)}</div></div>\n'
        f'          <div><div style="color:var(--ops-muted);">순이익률</div><div>{fmtPct(margin)}</div></div>\n'
        f'          <div><div style="color:var(--ops-muted);">총자산</div><div style="color:var(--ops-ink);">{fmtBn(ta_bn)}</div></div>\n'
        f'          <div><div style="color:var(--ops-muted);">ROA</div><div>{fmtPct(roa)}</div></div>\n'
        f'        </div>\n'
        f'        <div style="font-size:11px; color:{tier_color}; font-weight:700; margin-top:10px;">상세 →</div>\n'
        f'      </a>'
    )

cards_section = '\n'.join(cards_html)

html = '''<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>Peer 카드 — 인도네시아 골프 운영 벤치마크</title>
<link rel="icon" type="image/svg+xml" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Ccircle cx='32' cy='32' r='30' fill='%232D5016'/%3E%3Ccircle cx='32' cy='32' r='12' fill='%23F5F1E8'/%3E%3C/svg%3E" />
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Pretendard:wght@400;500;600;700&display=swap" rel="stylesheet" />
<link rel="stylesheet" href="ops-style.css?v=20260512c52" />
<style>
  .peer-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 14px; margin-top: 20px; }
  .peer-card:hover { transform: translateY(-2px); box-shadow: 0 6px 18px rgba(0,0,0,0.08); }
  .filter-bar { display: flex; gap: 8px; flex-wrap: wrap; margin: 12px 0; }
  .filter-btn { padding: 5px 12px; border: 1px solid var(--ops-line); background: var(--ops-surface); border-radius: 999px; font-size: 12px; font-weight: 600; cursor: pointer; color: var(--ops-ink-soft); }
  .filter-btn.active { background: var(--ops-green); color: white; border-color: var(--ops-green); }
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
    <nav class="ops-nav">
      <a href="clubs/index.html">⛳ 클럽별</a><a href="overview.html" class="active">Peer 카드</a><a href="unit-economics.html">단위 경제</a><a href="revenue.html">매출</a><a href="cost-hr.html">비용</a><a href="assets.html">시설</a><a href="risk.html">위험</a><a href="../../index.html" class="back">← 지도</a>
    </nav>
  </div>
</header>

<section class="ops-hero">
  <div class="ops-wrap">
    <h1>Peer 카드 요약</h1>
    <p class="lede">13 peer FY24 핵심 지표 한 화면. 카드 클릭으로 클럽 상세.</p>
    <div class="filter-bar">
      <button class="filter-btn active" data-filter="all">전체 (13)</button>
      <button class="filter-btn" data-filter="pp">🟦 Pure-play (2)</button>
      <button class="filter-btn" data-filter="resort">🟨 Resort (1)</button>
      <button class="filter-btn" data-filter="twn">🟩 Township (10)</button>
    </div>
  </div>
</section>

<section class="ops-section">
  <div class="ops-wrap">
    <div class="peer-grid" id="peer-grid">
__CARDS__
    </div>
  </div>
</section>

<footer class="ops-foot">
  <div class="ops-wrap">
    <p>Peer Group v2 · FY2024 audited · IDR.</p>
  </div>
</footer>

<script src="operations.js?v=20260512c2" defer></script>
<script>
(function(){
  const buttons = document.querySelectorAll('.filter-btn');
  const grid = document.getElementById('peer-grid');
  buttons.forEach(b => {
    b.addEventListener('click', () => {
      buttons.forEach(x => x.classList.remove('active'));
      b.classList.add('active');
      const f = b.dataset.filter;
      grid.querySelectorAll('.peer-card').forEach(c => {
        c.style.display = (f === 'all' || c.dataset.tier === f) ? '' : 'none';
      });
    });
  });
})();
</script>
</body>
</html>
'''

html = html.replace('__CARDS__', cards_section)
with open('overview.html','w',encoding='utf-8') as f:
    f.write(html)
print(f'overview.html rewritten: {os.path.getsize("overview.html")/1024:.1f} KB')
