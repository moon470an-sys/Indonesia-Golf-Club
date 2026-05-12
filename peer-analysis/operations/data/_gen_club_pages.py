"""Generate 13 club detail pages from data + template."""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import json
import os

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
CLUBS_DIR = os.path.join(DATA_DIR, '..', 'clubs')
os.makedirs(CLUBS_DIR, exist_ok=True)

clubs = json.load(open(os.path.join(DATA_DIR, '_clubs_meta.json'), encoding='utf-8'))

# Load 5y data
d5y = json.load(open(os.path.join(DATA_DIR, '..', '..', '..', 'data', 'company_financials_5y.json'), encoding='utf-8'))
fin = {c['ticker']: c for c in d5y['companies'] if 'ticker' in c}

# Load operations notes
peers_v2 = ['DMIG','PIPG','GOLF','MDLN','KIJA','SMDM','KPIG','SMRA','BSDE','CTRA','ELTY','LPKR','PWON']
notes = {}
for t in peers_v2:
    fn = os.path.join(DATA_DIR, f'{t.lower()}_notes.json')
    if os.path.exists(fn):
        notes[t] = json.load(open(fn, encoding='utf-8'))

# Disclosure depth per peer (manual mapping based on what's actually in notes)
disclosure = {
    'DMIG': {'rev_seg': '✅', 'cost_lines': '✅', 'memb_price': '⚠️', 'land': '⚠️', 'going_concern': '✅', 'kam': '✅'},
    'PIPG': {'rev_seg': '✅', 'cost_lines': '✅', 'memb_price': '⚠️', 'land': '✅', 'going_concern': '⚠️', 'kam': '⚠️'},
    'GOLF': {'rev_seg': '✅', 'cost_lines': '✅', 'memb_price': '❌', 'land': '❌', 'going_concern': '⚠️', 'kam': '⚠️'},
    'MDLN': {'rev_seg': '✅', 'cost_lines': '✅', 'memb_price': '❌', 'land': '❌', 'going_concern': '⚠️', 'kam': '❌'},
    'KIJA': {'rev_seg': '✅', 'cost_lines': '⚠️', 'memb_price': '❌', 'land': '❌', 'going_concern': '⚠️', 'kam': '❌'},
    'SMDM': {'rev_seg': '✅', 'cost_lines': '⚠️', 'memb_price': '⚠️', 'land': '❌', 'going_concern': '⚠️', 'kam': '❌'},
    'KPIG': {'rev_seg': '⚠️', 'cost_lines': '❌', 'memb_price': '❌', 'land': '❌', 'going_concern': '⚠️', 'kam': '❌'},
    'SMRA': {'rev_seg': '⚠️', 'cost_lines': '❌', 'memb_price': '❌', 'land': '❌', 'going_concern': '⚠️', 'kam': '❌'},
    'BSDE': {'rev_seg': '❌', 'cost_lines': '❌', 'memb_price': '❌', 'land': '❌', 'going_concern': '⚠️', 'kam': '❌'},
    'CTRA': {'rev_seg': '❌', 'cost_lines': '❌', 'memb_price': '❌', 'land': '❌', 'going_concern': '⚠️', 'kam': '❌'},
    'ELTY': {'rev_seg': '❌', 'cost_lines': '❌', 'memb_price': '❌', 'land': '❌', 'going_concern': '⚠️', 'kam': '❌'},
    'LPKR': {'rev_seg': '❌', 'cost_lines': '❌', 'memb_price': '❌', 'land': '❌', 'going_concern': '⚠️', 'kam': '❌'},
    'PWON': {'rev_seg': '❌', 'cost_lines': '❌', 'memb_price': '❌', 'land': '❌', 'going_concern': '⚠️', 'kam': '❌'},
}

# Membership model per peer (curated/AR-known)
membership_model = {
    'DMIG': 'Refundable membership (30년 환매 가능). Iuran keanggotaan annual fee 별도. AR Note 17·18.',
    'PIPG': 'Permanent transferable + Refundable. Iuran keanggotaan dan pendaftaran 매출 라인 (Note 27).',
    'GOLF': 'New Kuta 회원권 + Black Rocks 호텔 통합 패키지 (BGR associate은 별도).',
    'MDLN': '"Keanggotaan golf" 라인 분리 공시 (Note 25 sub-line 4 of 4). 단가 미공시.',
    'KIJA': '회원권 정책 정성 공시 없음. Golf segment 1줄만.',
    'SMDM': 'Private members + Trial + MAP 카테고리. 단가 미공시.',
    'KPIG': 'Trump Lido membership (curated 7.36 bn FY24 — AR Note 31 분리 X).',
    'SMRA': '"800+" 회원 정성 (curated, AR 미공시).',
    'BSDE': '— (직접 운영 안 함, Sinarmas Land 브랜드 산하)',
    'CTRA': '— (Ciputra 부동산 회원제 미공시)',
    'ELTY': '— (Bakrieland resort 회원제 미공시)',
    'LPKR': 'Imperial Klub Golf membership (외부 공시 — AR 분리 미공시)',
    'PWON': '— (Pakuwon Group 회원제 미공시)',
}

# Risk flags per peer
risk_flags = {
    'DMIG': [('토지권 만료', '⚪', '미공시 (BSD·PIK 모두)'), ('우발 부채', '⚪', 'Note 28+ AR 미추출'), ('Going Concern', '⚪', 'Clean audit (Vision 검증 Cycle 167)'), ('Key Audit Matters', '✅', 'Revenue Recognition + Fixed Assets')],
    'PIPG': [('토지권 만료', '🔴', 'HGB 209,533 m² 만료 2025년·2055년 (Note 10)'), ('우발 부채', '⚪', 'Note 32 임대·임차 약정 5건 (관계사 MKPI 풀 관리)'), ('Going Concern', '🟡', '미추출 (image PDF)'), ('Key Audit Matters', '🟡', '미추출')],
    'GOLF': [('매출 집중', '🔴', 'Triniti Garam Properti FY24 34% (Real Estate segment)'), ('Going Concern', '🟡', '미추출'), ('토지권 만료', '🟡', '미공시')],
    'MDLN': [('손실 누적', '🔴', 'FY23·FY24 net loss -102 / -690 bn (누적 -792 bn)'), ('매입 집중', '🔴', 'PT Jumbo Power International 62 bn FY24'), ('Going Concern', '🟡', 'image-PDF (LIMITATIONS cat.1)')],
    'KIJA': [('Power 적자', '🟡', 'Listrik segment GP 17.2% only'), ('Tourism 적자', '🟡', 'Pariwisata G&A 49.5 bn > rev 69.5 bn')],
    'SMDM': [('Real Estat 단독 흑자', '🟡', 'Real Estat OpInc 27.1% (그룹 유일 흑자)'), ('Golf 마진 급락', '🟡', 'GP 마진 FY22 54.8% → FY24 38.9% (-15.9pp)'), ('BSDE 인수 후', '🟡', '2024-10 BSDE 인수 / FY25 restatement caveat')],
    'KPIG': [('회사명 변경', '⚪', '2025-07 PT MNC LAND → PT MNC TOURISM INDONESIA'), ('Golf 단독 분리 X', '🟡', 'Note 31 Hotel+resor+golf 통합')],
    'SMRA': [('Leisure 마진 -7.2pp', '🟡', 'FY25 Rekreasi GP 18.0% → 10.8%')],
    'BSDE': [('Hotel +193.7%', '⚪', 'FY25 저점 회복'), ('Jalan tol -85.0%', '🟡', 'FY24 689 → FY25 104 bn')],
    'CTRA': [('AR Golf 미공시', '🟡', '2 코스 운영 but segment 분리 X')],
    'ELTY': [('AR Golf 미공시', '🟡', '2 코스 운영 but segment 분리 X'), ('FY24 적자', '🔴', 'Net profit -68.5 bn (margin -5.7%)')],
    'LPKR': [('AR Golf 미공시', '🟡', 'Imperial Klub Golf segment 분리 X'), ('FY24 165% 순이익률', '🟡', '일회성 이익 추정 (자산 매각 가능성)')],
    'PWON': [('AR Golf 미공시', '🟡', 'Pakuwon Golf segment 분리 X')],
}

# IR URLs / AR source links
ar_sources = {
    'DMIG': 'https://www.damaiindahgolf.com/index.asp?fuseaction=annual_report',
    'PIPG': 'https://www.golfpondokindah.com/index_sub.asp?fuseaction=annual_report',
    'GOLF': 'https://www.golflinkresorts.co.id/investor/annual-and-sustainability-report/id',
    'MDLN': 'IDX MDLN 공시 (annual_reports/MDLN/)',
    'KIJA': 'https://www.jababeka.com/investor-relations/annual-report',
    'SMDM': 'IDX SMDM 공시',
    'KPIG': 'https://mnctourismindonesia.com/annualreport',
    'SMRA': 'https://www.summarecon.com/investor-relations',
    'BSDE': 'https://www.sinarmasland.com/',
    'CTRA': 'https://www.ciputradevelopment.com/',
    'ELTY': 'https://www.bakrieland.com/',
    'LPKR': 'https://www.lippokarawaci.com/',
    'PWON': 'https://www.pakuwon.com/',
}

TEMPLATE = '''<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>{name} ({ticker}) — 클럽 상세</title>
<meta name="description" content="{name} ({ticker}) 운영 프로파일: 코스 사양·3년 추이·골프 공시 수준·회원권·리스크 플래그." />
<link rel="icon" type="image/svg+xml" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Ccircle cx='32' cy='32' r='30' fill='%232D5016'/%3E%3Ccircle cx='32' cy='32' r='12' fill='%23F5F1E8'/%3E%3C/svg%3E" />
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Pretendard:wght@400;500;600;700&display=swap" rel="stylesheet" />
<link rel="stylesheet" href="../ops-style.css?v=20260512c52" />
<style>
  .club-hero {{ background: {hero_bg}; padding: 32px 0 28px; border-bottom: 1px solid var(--ops-line); }}
  .club-hero h1 {{ font-size: 28px; margin: 12px 0 4px; }}
  .spec-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; margin-top: 16px; }}
  .spec-cell {{ background: var(--ops-surface); border: 1px solid var(--ops-line); border-radius: 8px; padding: 12px 16px; }}
  .spec-cell .l {{ font-size: 11px; color: var(--ops-muted); font-weight: 600; letter-spacing: 0.04em; text-transform: uppercase; }}
  .spec-cell .v {{ font-size: 17px; color: var(--ops-ink); font-weight: 700; margin-top: 4px; }}
  .spec-cell .sub {{ font-size: 12px; color: var(--ops-ink-soft); margin-top: 2px; }}
  .trend-tbl {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  .trend-tbl th, .trend-tbl td {{ padding: 8px 10px; text-align: right; border-bottom: 1px solid var(--ops-line); }}
  .trend-tbl th:first-child, .trend-tbl td:first-child {{ text-align: left; font-weight: 600; }}
  .trend-tbl thead th {{ background: var(--ops-surface); color: var(--ops-muted); font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em; }}
  .disc-row {{ display: flex; justify-content: space-between; align-items: center; padding: 10px 14px; border: 1px solid var(--ops-line); border-radius: 8px; background: var(--ops-surface); margin-bottom: 6px; }}
  .disc-row .lab {{ font-size: 13.5px; color: var(--ops-ink); }}
  .disc-row .val {{ font-size: 17px; font-weight: 700; }}
  .risk-item {{ padding: 10px 14px; border-left: 3px solid var(--ops-line); margin-bottom: 8px; background: var(--ops-surface); border-radius: 0 6px 6px 0; }}
  .risk-item.r-red {{ border-left-color: #b91c1c; background: #fef2f2; }}
  .risk-item.r-yellow {{ border-left-color: #f59e0b; background: #fffbeb; }}
  .risk-item.r-gray {{ border-left-color: #94a3b8; }}
</style>
</head>
<body>
<header class="ops-head">
  <div class="ops-wrap ops-head-row">
    <a href="../index.html" class="ops-brand">
      <div class="mark">⛳</div>
      <div>
        <div class="name">인도네시아 골프 운영 벤치마크</div>
        <div class="sub">13개 IDX 상장사 · Annual Report Note 직접 인용</div>
      </div>
    </a>
    <nav class="ops-nav">
      <a href="../index.html">한눈에</a><a href="../overview.html">TLDR</a><a href="../unit-economics.html">단위 경제</a><a href="../revenue.html">매출 믹스</a><a href="../cost-hr.html">비용 구조</a><a href="../assets.html">시설</a><a href="../risk.html">위험</a><a href="index.html">⛳ 클럽</a><a href="../../../index.html" class="back">← 지도</a>
    </nav>
  </div>
</header>

<section class="club-hero">
  <div class="ops-wrap">
    <div style="display:flex; gap:10px; align-items:center; font-size:12.5px; color:var(--ops-muted);">
      <a href="index.html" style="color:var(--ops-green);">⛳ 클럽 일람</a>
      <span>›</span>
      <span>{ticker}</span>
    </div>
    <h1>{name} <span class="peer-tag {tier_class}" style="font-size:13px; vertical-align:middle; margin-left:8px;">{tier_label}</span></h1>
    <div style="font-size:14px; color:var(--ops-ink-soft); margin-bottom:8px;">{sub}</div>
    <div style="display:flex; gap:24px; flex-wrap:wrap; font-size:13px; color:var(--ops-ink-soft); margin-top:6px;">
      <div><strong style="color:var(--ops-muted);">IDX 티커</strong> {ticker}</div>
      <div><strong style="color:var(--ops-muted);">위치</strong> {loc}</div>
      <div><strong style="color:var(--ops-muted);">모회사</strong> {parent}</div>
    </div>
  </div>
</section>

<section class="ops-section">
  <div class="ops-wrap">
    <h2>1. 코스 사양</h2>
    <div class="spec-grid">
      <div class="spec-cell"><div class="l">홀 수</div><div class="v">{holes}</div></div>
      <div class="spec-cell"><div class="l">토지 면적</div><div class="v">{area}</div></div>
      <div class="spec-cell"><div class="l">운영 모델</div><div class="v">{tier_label}</div></div>
      <div class="spec-cell"><div class="l">FY24 골프 매출</div><div class="v">Rp {golf_rev}</div></div>
    </div>
  </div>
</section>

<section class="ops-section">
  <div class="ops-wrap">
    <h2>2. 3년 추이 (FY2022 → FY2024)</h2>
    <h3>그룹 차원 P&amp;L · 자산 (curated 5y JSON)</h3>
    {trend_table}
  </div>
</section>

<section class="ops-section">
  <div class="ops-wrap">
    <h2>3. 골프 부문 공시 수준</h2>
    <p class="lede">AR Note에서 골프 사업 정보의 공시 깊이를 6 항목으로 측정. ✅ 공시 / ⚠️ 부분 / ❌ 미공시.</p>
    <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(280px, 1fr)); gap:8px; margin-top:14px;">
      <div class="disc-row"><span class="lab">매출 세그먼트 분리</span><span class="val">{rev_seg}</span></div>
      <div class="disc-row"><span class="lab">매출원가 라인 분해</span><span class="val">{cost_lines}</span></div>
      <div class="disc-row"><span class="lab">회원권 단가</span><span class="val">{memb_price}</span></div>
      <div class="disc-row"><span class="lab">토지권 만료년</span><span class="val">{land}</span></div>
      <div class="disc-row"><span class="lab">Going Concern (audit)</span><span class="val">{going_concern}</span></div>
      <div class="disc-row"><span class="lab">Key Audit Matters</span><span class="val">{kam}</span></div>
    </div>
  </div>
</section>

<section class="ops-section">
  <div class="ops-wrap">
    <h2>4. 회원권 모델</h2>
    <p style="font-size:14px; line-height:1.7; color:var(--ops-ink); background:var(--ops-surface); border:1px solid var(--ops-line); border-radius:8px; padding:14px 18px;">{membership}</p>
  </div>
</section>

<section class="ops-section">
  <div class="ops-wrap">
    <h2>5. 리스크 플래그</h2>
    <p class="lede">AR 공시 + Cycle 추출 결과 기반. 🔴 명시 위험 / 🟡 부분 공시 / ⚪ 정상 또는 미공시.</p>
    {risk_items}
  </div>
</section>

<section class="ops-section">
  <div class="ops-wrap">
    <h2>6. 원자료</h2>
    <ul style="font-size:13.5px; line-height:1.8; color:var(--ops-ink-soft);">
      <li><strong>AR 출처</strong>: {ar_source}</li>
      <li><strong>operations/data JSON</strong>: <code>{ticker_lower}_notes.json</code></li>
      <li><strong>5y curated</strong>: <code>site/data/company_financials_5y.json</code></li>
      <li><strong>골프 코스 inventory</strong>: <code>site/data/golf_courses.json</code></li>
    </ul>
  </div>
</section>

<footer class="ops-foot">
  <div class="ops-wrap">
    <p>{name} ({ticker}) 클럽 상세. 출처: 공개 IDX 연차보고서 (FY2022–FY2025) + Phase A/B 큐레이션. 마지막 갱신 2026-05-12 (Cycle 170).</p>
  </div>
</footer>
</body>
</html>
'''

# Hero bg by tier
hero_bg_map = {
    'pp': 'linear-gradient(135deg, #dbeafe 0%, #f0f9ff 100%)',
    'resort': 'linear-gradient(135deg, #fef3c7 0%, #fffbeb 100%)',
    'twn': 'linear-gradient(135deg, #dcfce7 0%, #f0fdf4 100%)',
}

generated = 0
for t in peers_v2:
    c = clubs[t]
    c5y = fin.get(t, {})
    yearly = c5y.get('yearly', {})

    # Trend table (FY22-FY25)
    trend_rows = []
    for fy in ['2022','2023','2024','2025']:
        y = yearly.get(fy, {})
        rev = y.get('revenue')
        op = y.get('operating_profit')
        np_ = y.get('net_profit')
        ta = y.get('total_assets')
        fmt = lambda v: f'{v/1e9:,.1f}' if isinstance(v,(int,float)) and v is not None else '—'
        if any([rev, op, np_, ta]):
            trend_rows.append(f'<tr><td>FY{fy}</td><td>{fmt(rev)}</td><td>{fmt(op)}</td><td>{fmt(np_)}</td><td>{fmt(ta)}</td></tr>')

    if trend_rows:
        trend_table = f'''<div class="tbl-card scroll-x"><table class="trend-tbl">
        <thead><tr><th>Fiscal Year</th><th>매출 (Rp bn)</th><th>영업이익 (Rp bn)</th><th>순이익 (Rp bn)</th><th>총자산 (Rp bn)</th></tr></thead>
        <tbody>{"".join(trend_rows)}</tbody></table></div>
        <p class="src" style="margin-top:8px;">출처: site/data/company_financials_5y.json (curated). FY25는 Cycle 167-168 AR 직접 추출 데이터 (가용 peer만).</p>'''
    else:
        trend_table = '<p style="color:var(--ops-muted); font-style:italic;">5y curated 데이터 미수집.</p>'

    # Risk items
    risk_html = []
    for label, sym, detail in risk_flags.get(t, []):
        color_class = {'🔴':'r-red', '🟡':'r-yellow', '⚪':'r-gray'}.get(sym, 'r-gray')
        risk_html.append(f'''<div class="risk-item {color_class}">
          <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:12px;">
            <strong style="font-size:13.5px; color:var(--ops-ink);">{label}</strong>
            <span style="font-size:14px;">{sym}</span>
          </div>
          <div style="font-size:12.5px; color:var(--ops-ink-soft); margin-top:4px;">{detail}</div>
        </div>''')
    risk_items = '\n'.join(risk_html) if risk_html else '<p style="color:var(--ops-muted);">리스크 공시 데이터 미추출.</p>'

    disc = disclosure.get(t, {})

    html = TEMPLATE.format(
        ticker=t, ticker_lower=t.lower(),
        name=c['name'], sub=c['sub'], loc=c['loc'], parent=c['parent'],
        tier_class=f'peer-tag-{c["tier"]}', tier_label=c['tier_label'],
        holes=c['holes'], area=c['area'],
        golf_rev=c['golf_rev_fy24'],
        hero_bg=hero_bg_map[c['tier']],
        trend_table=trend_table,
        rev_seg=disc.get('rev_seg','—'), cost_lines=disc.get('cost_lines','—'),
        memb_price=disc.get('memb_price','—'), land=disc.get('land','—'),
        going_concern=disc.get('going_concern','—'), kam=disc.get('kam','—'),
        membership=membership_model.get(t, '— 미공시'),
        risk_items=risk_items,
        ar_source=ar_sources.get(t, '—'),
    )

    out_path = os.path.join(CLUBS_DIR, f'{t.lower()}.html')
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(html)
    generated += 1
    print(f'  {t}: {os.path.getsize(out_path)/1024:.1f} KB')

print(f'\n{generated}/13 club detail pages generated → {CLUBS_DIR}')
