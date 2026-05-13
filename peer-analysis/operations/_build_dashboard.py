"""Build dashboard.html — 13 peer side-by-side comparison dashboard.
Default scope: Direct (3 peers). Other scopes available via existing comp-scope pills.
Single-screen entry point for benchmarking; existing 6 tabs become drill-down."""
import sys, json, os, datetime
sys.stdout.reconfigure(encoding='utf-8')

OP = os.path.dirname(os.path.abspath(__file__))
clubs = json.load(open(os.path.join(OP, 'data', '_clubs_meta.json'), 'r', encoding='utf-8'))
fin_doc = json.load(open(os.path.join(os.path.dirname(os.path.dirname(OP)), 'data', 'company_financials_5y.json'), 'r', encoding='utf-8'))
fin = {c['ticker']: c for c in fin_doc.get('companies', []) if 'ticker' in c}

peers_v2 = ['DMIG','PIPG','GOLF','MDLN','KIJA','SMDM','KPIG','SMRA','BSDE','CTRA','ELTY','LPKR','PWON']
COMP_TIER = {
    'DMIG':'direct','PIPG':'direct','GOLF':'direct',
    'MDLN':'segment','KIJA':'segment','SMDM':'segment','KPIG':'segment','SMRA':'segment',
    'BSDE':'landscape','CTRA':'landscape','ELTY':'landscape','LPKR':'landscape','PWON':'landscape',
}
# Risk scores from risk.html (FY2024 static)
PEER_RISK = {
    'DMIG':1,'PIPG':4,'GOLF':2,'MDLN':7,'KIJA':3,'SMDM':4,'KPIG':6,'SMRA':4,
    'BSDE':4,'CTRA':6,'ELTY':8,'LPKR':5,'PWON':4,
}

def torder(t): return {'pp':1,'resort':2,'twn':3}.get(clubs[t]['tier'], 9)
peers_sorted = sorted(peers_v2, key=lambda t: (torder(t), t))

def fmtBn(v):
    if v is None: return '—'
    if abs(v) >= 1e12: return f'{v/1e12:,.1f}T'
    if abs(v) >= 1e9: return f'{v/1e9:,.0f}B'
    return f'{v:,.0f}'

def fmtPct(v, dp=1):
    if v is None: return '—'
    sign = '+' if v > 0 else ''
    col = '#16a34a' if v > 0 else '#b91c1c' if v < 0 else 'var(--ops-muted)'
    return f'<span style="color:{col}; font-weight:700;">{sign}{v:.{dp}f}%</span>'

# Build 6Y sparkline (FY20-FY25)
def build_sparkline(yearly, color, w=80, h=22):
    years = ['2020','2021','2022','2023','2024','2025']
    series = [(yearly.get(y) or {}).get('revenue') for y in years]
    valid = [v for v in series if v is not None and v > 0]
    if len(valid) < 2:
        return '<span style="color:var(--ops-muted); font-size:10px;">—</span>'
    mn, mx = min(valid), max(valid)
    rng = mx - mn or 1
    padX, padY = 2, 3
    pts = []
    for i, v in enumerate(series):
        if v is None or v <= 0: continue
        x = padX + (w - 2*padX) * (i / (len(years)-1))
        y = h - padY - (h - 2*padY) * (v - mn) / rng
        pts.append((x, y, years[i], v))
    if len(pts) < 2: return '—'
    path = 'M ' + ' L '.join(f'{p[0]:.1f},{p[1]:.1f}' for p in pts)
    dots = ''.join(
        f'<circle cx="{p[0]:.1f}" cy="{p[1]:.1f}" r="2.2" fill="{"#f59e0b" if p[2]=="2025" else color}" stroke="white" stroke-width="0.8"><title>FY{p[2]}: {p[3]/1e9:,.1f}B</title></circle>'
        for p in pts
    )
    return f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" style="display:inline-block; vertical-align:middle;"><path d="{path}" stroke="{color}" stroke-width="1.6" fill="none"/>{dots}</svg>'

# Compute per-peer dashboard cells
def peer_card(t):
    c = clubs[t]
    f = fin.get(t, {})
    y25 = (f.get('yearly', {}) or {}).get('2025', {})
    y24 = (f.get('yearly', {}) or {}).get('2024', {})
    rev = y25.get('revenue')
    op_ = y25.get('operating_profit')
    np_ = y25.get('net_profit')
    ta = y25.get('total_assets')
    tl = y25.get('total_liabilities')
    te = y25.get('total_equity')
    rev_prev = y24.get('revenue')

    yoy = ((rev - rev_prev)/rev_prev*100) if (rev and rev_prev) else None
    op_margin = (op_/rev*100) if (rev and op_) else None
    np_margin = (np_/rev*100) if (rev and np_ is not None) else None
    roa = (np_/ta*100) if (ta and np_ is not None) else None
    turnover = (rev/ta) if (rev and ta) else None
    debt_ratio = (tl/ta*100) if (tl and ta) else None
    tier_color = {'pp':'#3b82f6','resort':'#f59e0b','twn':'#16a34a'}[c['tier']]
    risk_score = PEER_RISK.get(t, '—')
    risk_cls = 'risk-low' if isinstance(risk_score, int) and risk_score <= 2 else ('risk-med' if isinstance(risk_score, int) and risk_score <= 5 else 'risk-high')

    sparkline = build_sparkline(f.get('yearly', {}), tier_color)

    turnover_str = f'{turnover:.2f}×' if turnover is not None else '—'
    return f'''
    <div class="peer-col" data-comp="{COMP_TIER.get(t,'landscape')}" data-ticker="{t}" data-tier="{c['tier']}">
      <div class="peer-head" style="border-top:4px solid {tier_color};">
        <div class="peer-tk">{t}</div>
        <div class="peer-nm">{c['name']}</div>
        <div class="peer-tier"><span class="peer-tag peer-tag-{c['tier']}">{c['tier_label']}</span></div>
        <div class="peer-loc">{c['loc'][:35]}</div>
      </div>

      <div class="kpi-section">
        <div class="kpi-label">📈 매출 (FY2025)</div>
        <div class="kpi-main">Rp {fmtBn(rev)}</div>
        <div class="kpi-sub">YoY {fmtPct(yoy)}</div>
        <div class="kpi-spark">{sparkline}</div>
      </div>

      <div class="kpi-section">
        <div class="kpi-label">💰 수익성</div>
        <div class="kpi-row"><span>영업이익률</span><span class="kpi-val">{fmtPct(op_margin)}</span></div>
        <div class="kpi-row"><span>순이익률</span><span class="kpi-val">{fmtPct(np_margin)}</span></div>
        <div class="kpi-row"><span>ROA</span><span class="kpi-val">{fmtPct(roa)}</span></div>
      </div>

      <div class="kpi-section">
        <div class="kpi-label">🏗 자산</div>
        <div class="kpi-row"><span>총자산</span><span class="kpi-val">Rp {fmtBn(ta)}</span></div>
        <div class="kpi-row"><span>부채비율</span><span class="kpi-val">{fmtPct(debt_ratio, 0)}</span></div>
        <div class="kpi-row"><span>자산회전율</span><span class="kpi-val" style="color:var(--ops-ink); font-weight:700;">{turnover_str}</span></div>
      </div>

      <div class="kpi-section">
        <div class="kpi-label">⛳ 시설</div>
        <div class="kpi-row"><span>홀</span><span class="kpi-val">{c['holes']}</span></div>
        <div class="kpi-row"><span>면적</span><span class="kpi-val">{c['area']}</span></div>
      </div>

      <div class="kpi-section">
        <div class="kpi-label">⚠ 위험</div>
        <div class="risk-box {risk_cls}"><span class="risk-num">{risk_score}</span><span class="risk-max"> / 12</span></div>
      </div>

      <a class="detail-link" href="clubs/{t.lower()}.html">상세 페이지 →</a>
    </div>
    '''

# Generate page
build_date = datetime.date.today().strftime('%Y-%m-%d')
cards = [peer_card(t) for t in peers_sorted]

html = '''<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>비교 대시보드 — 인도네시아 골프 운영 벤치마크</title>
<link rel="icon" type="image/svg+xml" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Ccircle cx='32' cy='32' r='30' fill='%232D5016'/%3E%3Ccircle cx='32' cy='32' r='12' fill='%23F5F1E8'/%3E%3C/svg%3E" />
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Pretendard:wght@400;500;600;700&display=swap" rel="stylesheet" />
<link rel="stylesheet" href="ops-style.css?v=20260513scope1" />
<style>
  /* Comparison scope pills */
  .comp-pills { display:flex; gap:8px; flex-wrap:wrap; align-items:center; margin:14px 0 8px; }
  .comp-pill { padding:7px 16px; border:1px solid var(--ops-line); background:var(--ops-surface); border-radius:999px; font-size:13px; font-weight:700; cursor:pointer; color:var(--ops-ink-soft); }
  .comp-pill.active { background:var(--ops-green); color:white; border-color:var(--ops-green); }
  .comp-pill:hover:not(.active) { background:rgba(45,80,22,0.05); }
  .comp-hidden { display:none !important; }
  /* Peer comparison grid */
  .peer-grid { display:grid; grid-template-columns:repeat(auto-fit, minmax(240px, 1fr)); gap:16px; margin:20px 0; }
  .peer-col { background:var(--ops-surface); border:1px solid var(--ops-line); border-radius:10px; padding:0 0 12px 0; display:flex; flex-direction:column; min-width:0; transition:all 0.15s; }
  .peer-col:hover { box-shadow:0 4px 16px rgba(0,0,0,0.06); transform:translateY(-1px); }
  .peer-head { padding:14px 16px 10px; border-bottom:1px dashed var(--ops-line); margin-bottom:6px; }
  .peer-tk { font-size:11px; font-weight:700; color:var(--ops-muted); letter-spacing:0.06em; }
  .peer-nm { font-size:15.5px; font-weight:700; margin-top:3px; color:var(--ops-ink); line-height:1.3; }
  .peer-tier { margin-top:6px; }
  .peer-loc { font-size:11.5px; color:var(--ops-ink-soft); margin-top:4px; }
  .kpi-section { padding:8px 16px; border-bottom:1px dashed var(--ops-line); }
  .kpi-section:last-of-type { border-bottom:none; }
  .kpi-label { font-size:11px; font-weight:700; color:var(--ops-muted); letter-spacing:0.04em; margin-bottom:6px; }
  .kpi-main { font-size:18px; font-weight:700; color:var(--ops-ink); font-variant-numeric:tabular-nums; }
  .kpi-sub { font-size:11.5px; color:var(--ops-ink-soft); margin-top:1px; }
  .kpi-spark { margin-top:5px; }
  .kpi-row { display:flex; justify-content:space-between; align-items:center; padding:3px 0; font-size:12px; color:var(--ops-ink-soft); }
  .kpi-row .kpi-val { color:var(--ops-ink); font-weight:600; font-variant-numeric:tabular-nums; }
  .risk-box { font-size:18px; font-weight:700; font-variant-numeric:tabular-nums; padding:6px 10px; border-radius:6px; display:inline-block; }
  .risk-box.risk-low { background:rgba(22,163,74,0.12); color:#16a34a; }
  .risk-box.risk-med { background:rgba(245,158,11,0.14); color:#b45309; }
  .risk-box.risk-high { background:rgba(185,28,28,0.12); color:#b91c1c; }
  .risk-num { font-size:22px; }
  .risk-max { font-size:13px; opacity:0.7; font-weight:500; }
  .detail-link { display:block; margin:10px 16px 0; padding:7px 0; text-align:center; background:rgba(45,80,22,0.06); color:var(--ops-green); border-radius:6px; font-size:12px; font-weight:600; text-decoration:none; transition:all 0.12s; }
  .detail-link:hover { background:var(--ops-green); color:white; }
  /* Drill-down nav */
  .drill-grid { display:grid; grid-template-columns:repeat(auto-fit, minmax(200px, 1fr)); gap:10px; margin:20px 0 8px; }
  .drill-card { background:linear-gradient(135deg, rgba(45,80,22,0.06), rgba(45,80,22,0.01)); border:1px solid var(--ops-line); border-left:3px solid var(--ops-green); border-radius:8px; padding:12px 14px; text-decoration:none; color:var(--ops-ink); transition:all 0.12s; }
  .drill-card:hover { background:rgba(45,80,22,0.06); transform:translateY(-1px); }
  .drill-icon { font-size:18px; }
  .drill-title { font-size:14px; font-weight:700; margin-top:2px; }
  .drill-desc { font-size:11.5px; color:var(--ops-ink-soft); margin-top:3px; line-height:1.4; }
  /* Theme + responsive */
  .theme-toggle { position:absolute; top:14px; right:14px; padding:5px 10px; border:1px solid var(--ops-line); background:var(--ops-surface); border-radius:999px; font-size:13px; cursor:pointer; color:var(--ops-ink); z-index:10; }
  .ops-hero { position:relative; }
  body.theme-dark { --ops-bg:#0f172a; --ops-surface:#1e293b; --ops-ink:#e2e8f0; --ops-ink-soft:#cbd5e1; --ops-muted:#94a3b8; --ops-line:#334155; --ops-green:#22c55e; }
  body.theme-dark .drill-card { background:linear-gradient(135deg, rgba(34,197,94,0.10), rgba(34,197,94,0.02)); }
  @media (max-width:720px) {
    .peer-grid { grid-template-columns:1fr; }
    .drill-grid { grid-template-columns:1fr; }
  }
  @media print {
    .theme-toggle, .comp-pills, .drill-grid, .detail-link { display:none !important; }
    @page { size: A4 landscape; margin: 10mm; }
    body { background:white !important; }
  }
</style>
</head>
<body>
<header class="ops-head">
  <div class="ops-wrap ops-head-row">
    <a href="clubs/index.html" class="ops-brand">
      <div class="mark">⛳</div>
      <div>
        <div class="name">인도네시아 골프 운영 벤치마크</div>
        <div class="sub">3·8·13 peer scoped comparison</div>
      </div>
    </a>
    <nav class="ops-nav"><a href="dashboard.html" class="active">🎯 비교</a><a href="clubs/index.html">⛳ 클럽</a><a href="unit-economics.html">단위 경제</a><a href="revenue.html">매출</a><a href="cost-hr.html">비용</a><a href="assets.html">시설</a><a href="risk.html">위험</a><a href="../../index.html" class="back">← 지도</a></nav>
  </div>
</header>

<section class="ops-hero">
  <button class="theme-toggle" id="theme-toggle" aria-label="다크모드 전환" title="다크/라이트 모드 전환 (d)">🌙</button>
  <div class="ops-wrap">
    <h1>🎯 비교 대시보드 — FY2025</h1>
    <p class="lede">3 peer (default) side-by-side. 매출 · 수익성 · 자산 · 시설 · 위험 통합 화면. 더 깊이 보려면 ↓ 상세 탭 이동.</p>
    <div class="comp-pills" id="comp-scope" role="group" aria-label="비교 범위">
      <span style="font-size:11.5px; color:var(--ops-muted); font-weight:600;">비교 범위:</span>
      <button class="comp-pill active" data-scope="direct" title="DMIG·PIPG·GOLF — 골프가 주력 사업">🥇 직접 비교 (3)</button>
      <button class="comp-pill" data-scope="segment" title="+ MDLN·KIJA·SMDM·KPIG·SMRA — 골프 세그먼트 공시">🥇+🥈 세그먼트 (8)</button>
      <button class="comp-pill" data-scope="all" title="+ BSDE·CTRA·ELTY·LPKR·PWON — 부동산 대기업 (참고용)">전체 산업 (13)</button>
    </div>
  </div>
</section>

<section class="ops-section">
  <div class="ops-wrap">
    <div class="peer-grid" id="peer-grid">
__PEER_CARDS__
    </div>
  </div>
</section>

<section class="ops-section">
  <div class="ops-wrap">
    <h2 style="font-size:17px; margin:0 0 8px 0;">📊 깊이 분석 — 상세 탭으로 이동</h2>
    <p class="lede" style="font-size:12px; margin-bottom:4px;">각 영역의 시계열 · 부문 분해 · 정렬 · 검색은 상세 탭에서 제공.</p>
    <div class="drill-grid">
      <a class="drill-card" href="unit-economics.html"><span class="drill-icon">📈</span><div class="drill-title">단위 경제</div><div class="drill-desc">홀당·ha당·1인당 매출/이익 · 5Y CAGR · sparkline</div></a>
      <a class="drill-card" href="revenue.html"><span class="drill-icon">💰</span><div class="drill-title">매출 분석</div><div class="drill-desc">그룹/골프 매출 · YoY 히트맵 · 부문 분해 (PIPG 12 부문 14년)</div></a>
      <a class="drill-card" href="cost-hr.html"><span class="drill-icon">💸</span><div class="drill-title">비용·인력</div><div class="drill-desc">매출원가·판관비 · 카테고리 매트릭스 · 총영업비용 비율</div></a>
      <a class="drill-card" href="assets.html"><span class="drill-icon">🏗</span><div class="drill-title">시설·생산성</div><div class="drill-desc">홀·면적·총자산 · 자산회전율 · log-log 산점도</div></a>
      <a class="drill-card" href="risk.html"><span class="drill-icon">⚠</span><div class="drill-title">위험 매트릭스</div><div class="drill-desc">6 항목 × 13 peer · 토지권·세무·BPJS 공시</div></a>
      <a class="drill-card" href="clubs/index.html"><span class="drill-icon">⛳</span><div class="drill-title">클럽 카드</div><div class="drill-desc">즐겨찾기 · 검색 · 정렬 · CSV 내보내기 · 13 peer 카드/표 view</div></a>
    </div>
  </div>
</section>

<footer class="ops-foot">
  <div class="ops-wrap">
    <p>FY2025 audited consolidated P&L + Balance Sheet · 데이터 갱신 __BUILD_DATE__ · localStorage 'peer-comp-scope' cross-page sync</p>
  </div>
</footer>

<script>
const COMP_TIER = {DMIG:'direct',PIPG:'direct',GOLF:'direct',MDLN:'segment',KIJA:'segment',SMDM:'segment',KPIG:'segment',SMRA:'segment',BSDE:'landscape',CTRA:'landscape',ELTY:'landscape',LPKR:'landscape',PWON:'landscape'};
let compScope = 'direct';
try { const s = localStorage.getItem('peer-comp-scope'); if (['direct','segment','all'].includes(s)) compScope = s; } catch(e){}
function compMatches(c) {
  if (compScope === 'all') return true;
  if (compScope === 'segment') return c === 'direct' || c === 'segment';
  return c === 'direct';
}
function applyCompScope() {
  document.querySelectorAll('.peer-col').forEach(el => {
    el.classList.toggle('comp-hidden', !compMatches(el.dataset.comp));
  });
}
document.querySelectorAll('#comp-scope .comp-pill').forEach(p => {
  p.classList.toggle('active', p.dataset.scope === compScope);
  p.addEventListener('click', () => {
    document.querySelectorAll('#comp-scope .comp-pill').forEach(x => x.classList.remove('active'));
    p.classList.add('active');
    compScope = p.dataset.scope;
    try { localStorage.setItem('peer-comp-scope', compScope); } catch(e){}
    applyCompScope();
  });
});
// Dark mode (shared 'ops-theme')
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
document.addEventListener('keydown', (e) => {
  if (e.target.matches('input,textarea,select')) return;
  if (e.key === 'd') themeBtn.click();
});
applyCompScope();
</script>
</body>
</html>
'''.replace('__PEER_CARDS__', '\n'.join(cards)).replace('__BUILD_DATE__', build_date)

OUT_PATH = os.path.join(OP, 'dashboard.html')
with open(OUT_PATH, 'w', encoding='utf-8') as f:
    f.write(html)
print(f'dashboard.html: {os.path.getsize(OUT_PATH)/1024:.1f} KB')
