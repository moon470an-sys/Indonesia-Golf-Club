"""Build unit-economics.html — per-unit metrics across 13 peers."""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import json
import os

clubs = json.load(open('data/_clubs_meta.json','r',encoding='utf-8'))
d5y = json.load(open('../../data/company_financials_5y.json','r',encoding='utf-8'))
fin = {c['ticker']: c for c in d5y['companies'] if 'ticker' in c}
peers_v2 = ['DMIG','PIPG','GOLF','MDLN','KIJA','SMDM','KPIG','SMRA','BSDE','CTRA','ELTY','LPKR','PWON']
def torder(t): return {'pp':1,'resort':2,'twn':3}.get(clubs[t]['tier'], 9)

# Hard-coded numeric extractions from AR notes (sources: assets.html + clubs/{t}.html)
# Holes, course area in ha (golf-only — not estate), employees
unit_inputs = {
    # ticker: (holes, area_ha, employees, golf_rev_FY24_bn, golf_op_margin_pct_or_None)
    'DMIG': (36,   156.0, 198, 253.10, None),  # group=golf
    'PIPG': (18,    53.01, 254, 197.57, None),  # group=golf
    'GOLF': (36,   171.2, None, 93.04,  None),  # golf segment only (BGR excluded)
    'MDLN': (18,   None,  None, 74.4,  None),
    'KIJA': (None, None,  None, 85.02,  None),
    'SMDM': (18,   None,  None, 63.28,  None),  # estate is 400ha but not golf-only
    'KPIG': (18,   83.0,  None, None,   None),
    'SMRA': (18,   None,  None, 66.67,  None),
    'BSDE': (None, None,  None, None,   None),
    'CTRA': (36,   None,  None, None,   None),
    'ELTY': (36,   None,  None, None,   None),
    'LPKR': (18,   None,  None, None,   None),
    'PWON': (18,   None,  None, None,   None),
}

def fmt_num(v, dp=0):
    if v is None: return '—'
    return f'{v:,.{dp}f}'
def fmt_bn(v, dp=1):
    if v is None: return '—'
    if abs(v) >= 1000: return f'{v/1000:,.1f}T'
    return f'{v:,.{dp}f}B'
def fmt_pct(v, dp=1):
    if v is None: return '—'
    return f'{v:,.{dp}f}%'

def per_unit_bn(rev_bn, divisor):
    """rev_bn in billion IDR, divisor = holes/ha/employees → returns Rp B per unit (or M if small)"""
    if rev_bn is None or divisor is None or divisor == 0: return None
    return rev_bn / divisor  # in billion IDR per unit

def fmt_per_unit(v):
    if v is None: return '—'
    if abs(v) < 0.1:  # less than 100M → show in M
        return f'{v*1000:,.0f}M'
    if abs(v) < 1:
        return f'{v*1000:,.0f}M'
    return f'{v:,.2f}B'

peers_sorted = sorted(peers_v2, key=lambda t: (torder(t), t))

# Build per-unit table
rows = []
for t in peers_sorted:
    c = clubs[t]
    holes, area, emp, golf_rev, _ = unit_inputs[t]
    fy24 = fin.get(t,{}).get('yearly',{}).get('2024',{})
    if emp is None: emp = fy24.get('employees')

    # Group level metrics for context
    grp_rev = fy24.get('revenue')   # IDR
    grp_op = fy24.get('operating_profit')
    grp_rev_bn = grp_rev/1e9 if grp_rev else None
    op_margin = (grp_op/grp_rev*100) if (grp_rev and grp_op) else None

    # Per-unit (using golf_rev_bn where available, else group rev for pure-play)
    rev_per_hole = per_unit_bn(golf_rev, holes)
    rev_per_ha = per_unit_bn(golf_rev, area)
    rev_per_emp = per_unit_bn(grp_rev_bn, emp)
    op_per_emp = per_unit_bn(grp_op/1e9 if grp_op else None, emp)

    rows.append(f'''            <tr>
              <td class="peer"><a href="clubs/{t.lower()}.html" style="color:var(--ops-ink); font-weight:700; text-decoration:none;">{t}</a><span class="peer-tag peer-tag-{c["tier"]}">{c["tier_label"]}</span></td>
              <td>{c["name"][:22]}</td>
              <td class="num">{fmt_num(holes)}</td>
              <td class="num">{fmt_num(area, 1)}</td>
              <td class="num">{fmt_num(emp)}</td>
              <td class="num">{fmt_bn(golf_rev)}</td>
              <td class="num"><strong>{fmt_per_unit(rev_per_hole)}</strong></td>
              <td class="num">{fmt_per_unit(rev_per_ha)}</td>
              <td class="num">{fmt_per_unit(rev_per_emp)}</td>
              <td class="num">{fmt_pct(op_margin)}</td>
              <td class="num">{fmt_per_unit(op_per_emp)}</td>
            </tr>''')

# Hole-density / efficiency leaderboard — only peers with full data
leaderboard = []
for t in peers_v2:
    holes, area, emp, golf_rev, _ = unit_inputs[t]
    if not (holes and golf_rev): continue
    leaderboard.append((t, golf_rev/holes))
leaderboard.sort(key=lambda x: -x[1])
lb_rows = []
for rank, (t, val) in enumerate(leaderboard, 1):
    c = clubs[t]
    lb_rows.append(f'''            <tr>
              <td class="num"><strong>{rank}</strong></td>
              <td class="peer"><a href="clubs/{t.lower()}.html" style="color:var(--ops-ink); font-weight:700; text-decoration:none;">{t}</a><span class="peer-tag peer-tag-{c["tier"]}">{c["tier_label"]}</span></td>
              <td>{c["name"][:30]}</td>
              <td class="num">{unit_inputs[t][0]}</td>
              <td class="num">{fmt_bn(unit_inputs[t][3])}</td>
              <td class="num"><strong style="color:var(--ops-green);">{fmt_per_unit(val)}</strong></td>
            </tr>''')

# Tier-summary roll-up (average per tier for peers w/ data)
from collections import defaultdict
tier_acc = defaultdict(lambda: {'holes':[],'area':[],'rev_per_hole':[],'rev_per_ha':[]})
for t in peers_v2:
    c = clubs[t]
    holes, area, emp, golf_rev, _ = unit_inputs[t]
    tier = c['tier']
    if holes: tier_acc[tier]['holes'].append(holes)
    if area: tier_acc[tier]['area'].append(area)
    if holes and golf_rev: tier_acc[tier]['rev_per_hole'].append(golf_rev/holes)
    if area and golf_rev: tier_acc[tier]['rev_per_ha'].append(golf_rev/area)

tier_label_map = {'pp':'🟦 Pure-play','resort':'🟨 Resort','twn':'🟩 Township'}
tier_rows = []
for tk in ['pp','resort','twn']:
    a = tier_acc[tk]
    def avg(lst): return sum(lst)/len(lst) if lst else None
    tier_rows.append(f'''            <tr>
              <td><strong>{tier_label_map[tk]}</strong></td>
              <td class="num">{len([t for t in peers_v2 if clubs[t]["tier"]==tk])}</td>
              <td class="num">{fmt_num(avg(a["holes"]))}</td>
              <td class="num">{fmt_num(avg(a["area"]), 1)}</td>
              <td class="num"><strong>{fmt_per_unit(avg(a["rev_per_hole"]))}</strong></td>
              <td class="num">{fmt_per_unit(avg(a["rev_per_ha"]))}</td>
            </tr>''')

# Assemble HTML
html = f'''<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>단위 경제 — 인도네시아 골프 운영 벤치마크</title>
<link rel="icon" type="image/svg+xml" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Ccircle cx='32' cy='32' r='30' fill='%232D5016'/%3E%3Ccircle cx='32' cy='32' r='12' fill='%23F5F1E8'/%3E%3C/svg%3E" />
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Pretendard:wght@400;500;600;700&display=swap" rel="stylesheet" />
<link rel="stylesheet" href="ops-style.css?v=20260512c53" />
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
    <p class="lede">홀 · ha · 정직원 대비 매출/이익 — 13 peer FY2024. 일부 peer는 정직원·면적 미공시.</p>
  </div>
</section>

<section class="ops-section">
  <div class="ops-wrap">
    <h2 style="font-size:17px; margin:0 0 14px 0;">① 13-peer 단위 경제 (FY2024)</h2>
    <p style="font-size:12px; color:var(--ops-muted); margin:0 0 12px 0;">홀당·ha당 매출은 골프 부문 매출 / 해당 단위. 1인당 매출·영업이익은 그룹 연결 P&L 기준 (그룹 직원 수). Pure-play의 골프 매출은 곧 그룹 매출.</p>
    <div class="tbl-card scroll-x">
      <table class="ops-tbl">
        <thead>
          <tr>
            <th>Peer</th>
            <th>그룹명</th>
            <th class="num">홀</th>
            <th class="num">면적 (ha)</th>
            <th class="num">정직원</th>
            <th class="num">골프 매출 FY24</th>
            <th class="num">홀당 매출</th>
            <th class="num">ha당 매출</th>
            <th class="num">1인당 매출</th>
            <th class="num">영업이익률</th>
            <th class="num">1인당 영업이익</th>
          </tr>
        </thead>
        <tbody>
{chr(10).join(rows)}
        </tbody>
      </table>
    </div>
  </div>
</section>

<section class="ops-section">
  <div class="ops-wrap">
    <h2 style="font-size:17px; margin:0 0 14px 0;">② 홀당 매출 리더보드</h2>
    <p style="font-size:12px; color:var(--ops-muted); margin:0 0 12px 0;">골프 부문 매출/홀 수 기준 (공시된 peer만).</p>
    <div class="tbl-card scroll-x">
      <table class="ops-tbl">
        <thead>
          <tr>
            <th class="num">#</th>
            <th>Peer</th>
            <th>그룹명</th>
            <th class="num">홀</th>
            <th class="num">골프 매출 FY24</th>
            <th class="num">홀당 매출</th>
          </tr>
        </thead>
        <tbody>
{chr(10).join(lb_rows)}
        </tbody>
      </table>
    </div>
  </div>
</section>

<section class="ops-section">
  <div class="ops-wrap">
    <h2 style="font-size:17px; margin:0 0 14px 0;">③ Tier 평균</h2>
    <p style="font-size:12px; color:var(--ops-muted); margin:0 0 12px 0;">Tier별 공시 peer 평균. N개 peer 중 면적·홀 미공시는 제외.</p>
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
        <tbody>
{chr(10).join(tier_rows)}
        </tbody>
      </table>
    </div>
  </div>
</section>

<footer class="ops-foot">
  <div class="ops-wrap">
    <p>홀·면적·정직원은 AR Profile + 자사 공시. 골프 매출은 segment note (있을 때) / 그룹 매출 (pure-play).</p>
  </div>
</footer>

<script src="operations.js?v=20260512c3" defer></script>
</body>
</html>
'''

with open('unit-economics.html','w',encoding='utf-8') as f:
    f.write(html)
print(f'unit-economics.html: {os.path.getsize("unit-economics.html")/1024:.1f} KB')
