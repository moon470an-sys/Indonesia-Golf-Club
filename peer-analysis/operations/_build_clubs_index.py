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

cards_html = []
peers_sorted = sorted(peers_v2, key=lambda t: (torder(t), t))

for t in peers_sorted:
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
        f'      <a href="{t.lower()}.html" class="club-card" data-tier="{c["tier"]}" data-ticker="{t}" '
        f'style="background:var(--ops-surface); border:1px solid var(--ops-line); border-top:4px solid {tier_color}; '
        f'border-radius:10px; padding:18px 22px; text-decoration:none; color:inherit; display:flex; flex-direction:column; gap:10px; transition:all 0.2s;">\n'
        f'        <div style="display:flex; justify-content:space-between; align-items:flex-start;">\n'
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
        f'          <div><strong style="color:var(--ops-muted);">순이익률</strong><br>{fmtPct(margin)}</div>\n'
        f'          <div><strong style="color:var(--ops-muted);">총자산</strong><br><span style="color:var(--ops-ink);">{fmtBn(ta_bn)}</span></div>\n'
        f'          <div><strong style="color:var(--ops-muted);">ROA</strong><br>{fmtPct(roa)}</div>\n'
        f'        </div>\n'
        f'        <div style="display:flex; justify-content:space-between; font-size:11.5px;">\n'
        f'          <div><strong style="color:var(--ops-muted);">골프 매출 FY24</strong><br><span style="font-weight:700; color:var(--ops-green);">Rp {c["golf_rev_fy24"]}</span></div>\n'
        f'          <div style="text-align:right; align-self:flex-end; font-weight:700; color:{tier_color};">상세 →</div>\n'
        f'        </div>\n'
        f'      </a>'
    )

cards_section = '\n'.join(cards_html)

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
  .filter-bar { display: flex; gap: 10px; flex-wrap: wrap; margin: 12px 0; }
  .filter-btn { padding: 6px 14px; border: 1px solid var(--ops-line); background: var(--ops-surface); border-radius: 999px; font-size: 12.5px; font-weight: 600; cursor: pointer; color: var(--ops-ink-soft); }
  .filter-btn.active { background: var(--ops-green); color: white; border-color: var(--ops-green); }
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
  <div class="ops-wrap">
    <h1>13 클럽 일람</h1>
    <p class="lede">IDX 상장 13개 골프 운영사. 클럽명·시설·재무 한 카드. 카드 클릭으로 클럽 상세.</p>
    <div class="filter-bar" id="tier-filter">
      <button class="filter-btn active" data-filter="all">전체 (13)</button>
      <button class="filter-btn" data-filter="pp">🟦 Pure-play (2)</button>
      <button class="filter-btn" data-filter="resort">🟨 Resort (1)</button>
      <button class="filter-btn" data-filter="twn">🟩 Township (10)</button>
    </div>
  </div>
</section>

<section class="ops-section">
  <div class="ops-wrap">
    <div class="club-grid" id="club-grid">
__CARDS__
    </div>
  </div>
</section>

<footer class="ops-foot">
  <div class="ops-wrap">
    <p>Peer Group v2 · FY2024 audited · IDR.</p>
  </div>
</footer>

<script src="../operations.js?v=20260512c3" defer></script>
<script>
(function(){
  const buttons = document.querySelectorAll('#tier-filter .filter-btn');
  const grid = document.getElementById('club-grid');
  buttons.forEach(b => {
    b.addEventListener('click', () => {
      buttons.forEach(x => x.classList.remove('active'));
      b.classList.add('active');
      const f = b.dataset.filter;
      grid.querySelectorAll('.club-card').forEach(c => {
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
with open('clubs/index.html','w',encoding='utf-8') as f:
    f.write(html)
print(f'clubs/index.html: {os.path.getsize("clubs/index.html")/1024:.1f} KB')
