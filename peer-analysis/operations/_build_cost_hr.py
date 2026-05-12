"""Build cost-hr.html — full cost detail comparison: COGS lines + OpEx lines + 13-peer structure %."""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import json
import os

clubs = json.load(open('data/_clubs_meta.json','r',encoding='utf-8'))
d5y = json.load(open('../../data/company_financials_5y.json','r',encoding='utf-8'))
fin = {c['ticker']: c for c in d5y['companies'] if 'ticker' in c}

peers_v2 = ['DMIG','PIPG','GOLF','MDLN','KIJA','SMDM','KPIG','SMRA','BSDE','CTRA','ELTY','LPKR','PWON']

def torder(t): return {'pp':1,'resort':2,'twn':3}.get(clubs[t]['tier'], 9)
def fmt_bn(v, dp=1):
    if v is None: return '—'
    if abs(v) >= 1e12: return f'{v/1e12:,.{dp}f}T'
    if abs(v) >= 1e9: return f'{v/1e9:,.{dp}f}B'
    if abs(v) >= 1e6: return f'{v/1e6:,.{dp}f}M'
    return f'{v:,.0f}'
def fmt_pct(v, dp=1):
    if v is None: return '—'
    return f'{v:,.{dp}f}%'
def fmt_idr_mm(v):  # for IDR in million units
    if v is None: return '—'
    if abs(v) >= 1000: return f'{v/1000:,.1f}B'
    return f'{v:,.0f}M'

notes = {}
for t in peers_v2:
    path = f'data/{t.lower()}_notes.json'
    if os.path.exists(path):
        notes[t] = json.load(open(path,'r',encoding='utf-8'))

# ============================================================
# SECTION 1: 매출원가 (COGS) — line-level detail
# ============================================================
cogs_section = []

# DMIG cogs (3 lines, FY22-FY24)
d = notes['DMIG']['cogs_note']
rows = []
for ln in d['lines']:
    rows.append(f'''            <tr>
              <td>{ln["id_label"]}<br><span style="color:var(--ops-muted); font-size:11px;">{ln["en_label"]}</span></td>
              <td class="num">{fmt_bn(ln.get("FY2022"))}</td>
              <td class="num">{fmt_bn(ln.get("FY2023"))}</td>
              <td class="num"><strong>{fmt_bn(ln.get("FY2024"))}</strong></td>
            </tr>''')
total = d['total']
rows.append(f'''            <tr style="background:rgba(45,80,22,0.06); font-weight:700;">
              <td>합계</td>
              <td class="num">{fmt_bn(total.get("FY2022"))}</td>
              <td class="num">{fmt_bn(total.get("FY2023"))}</td>
              <td class="num">{fmt_bn(total.get("FY2024"))}</td>
            </tr>''')
cogs_section.append(f'''      <div style="margin-bottom:32px;">
        <h3 style="font-size:16px; margin:0 0 10px 0;">🟦 DMIG · 매출원가 (Note {notes["DMIG"]["cogs_note"]["note_number"]})</h3>
        <p style="font-size:12px; color:var(--ops-muted); margin:0 0 8px 0;">사업부별 직접원가 — 3 라인 공시</p>
        <div class="tbl-card scroll-x">
          <table class="ops-tbl">
            <thead><tr><th>비용 라인</th><th class="num">FY2022</th><th class="num">FY2023</th><th class="num">FY2024</th></tr></thead>
            <tbody>
{chr(10).join(rows)}
            </tbody>
          </table>
        </div>
      </div>''')

# PIPG cogs (11 lines, FY23-FY24)
d = notes['PIPG']['cogs_note_28']
rows = []
for ln in d['lines']:
    rows.append(f'''            <tr>
              <td>{ln["id_label"]}<br><span style="color:var(--ops-muted); font-size:11px;">{ln.get("en_label","—")}</span></td>
              <td class="num">{fmt_bn(ln.get("FY2023"))}</td>
              <td class="num"><strong>{fmt_bn(ln.get("FY2024"))}</strong></td>
            </tr>''')
total = d['total']
rows.append(f'''            <tr style="background:rgba(45,80,22,0.06); font-weight:700;">
              <td>합계</td>
              <td class="num">{fmt_bn(total.get("FY2023"))}</td>
              <td class="num">{fmt_bn(total.get("FY2024"))}</td>
            </tr>''')
cogs_section.append(f'''      <div style="margin-bottom:32px;">
        <h3 style="font-size:16px; margin:0 0 10px 0;">🟦 PIPG · 매출원가 (Note 28)</h3>
        <p style="font-size:12px; color:var(--ops-muted); margin:0 0 8px 0;">시설별 운영 비용 — 11 라인 공시</p>
        <div class="tbl-card scroll-x">
          <table class="ops-tbl">
            <thead><tr><th>비용 라인</th><th class="num">FY2023</th><th class="num">FY2024</th></tr></thead>
            <tbody>
{chr(10).join(rows)}
            </tbody>
          </table>
        </div>
      </div>''')

# GOLF cogs (4 lines)
d = notes['GOLF']['cogs_note_30']
rows = []
for ln in d['lines']:
    en_part = f'<br><span style="color:var(--ops-muted); font-size:11px;">{ln["en_label"]}</span>' if 'en_label' in ln else ''
    rows.append(f'''            <tr>
              <td>{ln["id_label"]}{en_part}</td>
              <td class="num">{fmt_bn(ln.get("FY2023"))}</td>
              <td class="num"><strong>{fmt_bn(ln.get("FY2024"))}</strong></td>
            </tr>''')
total = d.get('total',{})
rows.append(f'''            <tr style="background:rgba(45,80,22,0.06); font-weight:700;">
              <td>합계</td>
              <td class="num">{fmt_bn(total.get("FY2023"))}</td>
              <td class="num">{fmt_bn(total.get("FY2024"))}</td>
            </tr>''')
cogs_section.append(f'''      <div style="margin-bottom:32px;">
        <h3 style="font-size:16px; margin:0 0 10px 0;">🟨 GOLF · 매출원가 (Note 30)</h3>
        <p style="font-size:12px; color:var(--ops-muted); margin:0 0 8px 0;">사업부별 직접원가 (골프·부동산·호텔·F&B)</p>
        <div class="tbl-card scroll-x">
          <table class="ops-tbl">
            <thead><tr><th>비용 라인</th><th class="num">FY2023</th><th class="num">FY2024</th></tr></thead>
            <tbody>
{chr(10).join(rows)}
            </tbody>
          </table>
        </div>
      </div>''')

# MDLN cogs — golf + clubhouse breakdown
m = notes['MDLN']['cogs_note_26']
rows = []
rows.append('            <tr style="background:rgba(245,158,11,0.08); font-weight:700;"><td colspan="3">골프 코스 직접원가</td></tr>')
for ln in m.get('golf_course_direct_cost_lines',[]):
    rows.append(f'''            <tr>
              <td style="padding-left:24px;">{ln["id_label"]}</td>
              <td class="num">{fmt_bn(ln.get("FY2023"))}</td>
              <td class="num">{fmt_bn(ln.get("FY2024"))}</td>
            </tr>''')
gs = m.get('golf_course_subtotal',{})
rows.append(f'''            <tr style="font-weight:600;">
              <td style="padding-left:24px;">— 골프 소계</td>
              <td class="num">{fmt_bn(gs.get("FY2023"))}</td>
              <td class="num">{fmt_bn(gs.get("FY2024"))}</td>
            </tr>''')
rows.append('            <tr style="background:rgba(245,158,11,0.08); font-weight:700;"><td colspan="3">클럽하우스·F&B 직접원가</td></tr>')
for ln in m.get('club_house_restaurant_direct_cost_lines',[]):
    rows.append(f'''            <tr>
              <td style="padding-left:24px;">{ln["id_label"]}</td>
              <td class="num">{fmt_bn(ln.get("FY2023"))}</td>
              <td class="num">{fmt_bn(ln.get("FY2024"))}</td>
            </tr>''')
cs = m.get('club_house_restaurant_subtotal',{})
rows.append(f'''            <tr style="font-weight:600;">
              <td style="padding-left:24px;">— 클럽하우스 소계</td>
              <td class="num">{fmt_bn(cs.get("FY2023"))}</td>
              <td class="num">{fmt_bn(cs.get("FY2024"))}</td>
            </tr>''')
gcs = m.get('golf_plus_clubhouse_subtotal',{})
rows.append(f'''            <tr style="background:rgba(45,80,22,0.06); font-weight:700;">
              <td>골프+클럽하우스 합계</td>
              <td class="num">{fmt_bn(gcs.get("FY2023"))}</td>
              <td class="num">{fmt_bn(gcs.get("FY2024"))}</td>
            </tr>''')
cogs_section.append(f'''      <div style="margin-bottom:32px;">
        <h3 style="font-size:16px; margin:0 0 10px 0;">🟩 MDLN · 매출원가 (Note 26)</h3>
        <p style="font-size:12px; color:var(--ops-muted); margin:0 0 8px 0;">골프·클럽하우스 부문별 직접원가 (호텔 부문 제외)</p>
        <div class="tbl-card scroll-x">
          <table class="ops-tbl">
            <thead><tr><th>비용 라인</th><th class="num">FY2023</th><th class="num">FY2024</th></tr></thead>
            <tbody>
{chr(10).join(rows)}
            </tbody>
          </table>
        </div>
      </div>''')

# ============================================================
# SECTION 2: 판관비 (OpEx) — line-level detail
# ============================================================
opex_section = []

# DMIG opex (17 lines, FY22-FY24)
d = notes['DMIG']['opex_note']
rows = []
for ln in d['lines']:
    rows.append(f'''            <tr>
              <td>{ln["id_label"]}<br><span style="color:var(--ops-muted); font-size:11px;">{ln.get("en_label","—")}</span></td>
              <td class="num">{fmt_bn(ln.get("FY2022"))}</td>
              <td class="num">{fmt_bn(ln.get("FY2023"))}</td>
              <td class="num"><strong>{fmt_bn(ln.get("FY2024"))}</strong></td>
            </tr>''')
total = d['total']
rows.append(f'''            <tr style="background:rgba(45,80,22,0.06); font-weight:700;">
              <td>합계</td>
              <td class="num">{fmt_bn(total.get("FY2022"))}</td>
              <td class="num">{fmt_bn(total.get("FY2023"))}</td>
              <td class="num">{fmt_bn(total.get("FY2024"))}</td>
            </tr>''')
opex_section.append(f'''      <div style="margin-bottom:32px;">
        <h3 style="font-size:16px; margin:0 0 10px 0;">🟦 DMIG · 판관비 (Note {notes["DMIG"]["opex_note"]["note_number"]})</h3>
        <p style="font-size:12px; color:var(--ops-muted); margin:0 0 8px 0;">17 라인 — 인건비·시설관리·세금·감가상각 등</p>
        <div class="tbl-card scroll-x">
          <table class="ops-tbl">
            <thead><tr><th>비용 라인</th><th class="num">FY2022</th><th class="num">FY2023</th><th class="num">FY2024</th></tr></thead>
            <tbody>
{chr(10).join(rows)}
            </tbody>
          </table>
        </div>
      </div>''')

# PIPG opex_29 (17 lines)
d = notes['PIPG']['opex_note_29']
rows = []
for ln in d['lines']:
    rows.append(f'''            <tr>
              <td>{ln["id_label"]}<br><span style="color:var(--ops-muted); font-size:11px;">{ln.get("en_label","—")}</span></td>
              <td class="num">{fmt_bn(ln.get("FY2023"))}</td>
              <td class="num"><strong>{fmt_bn(ln.get("FY2024"))}</strong></td>
            </tr>''')
total = d['total']
rows.append(f'''            <tr style="background:rgba(45,80,22,0.06); font-weight:700;">
              <td>합계</td>
              <td class="num">{fmt_bn(total.get("FY2023"))}</td>
              <td class="num">{fmt_bn(total.get("FY2024"))}</td>
            </tr>''')
opex_section.append(f'''      <div style="margin-bottom:32px;">
        <h3 style="font-size:16px; margin:0 0 10px 0;">🟦 PIPG · 판관비 (Note 29)</h3>
        <p style="font-size:12px; color:var(--ops-muted); margin:0 0 8px 0;">17 라인 — 세금·인허가·인건비·법률·감가 등</p>
        <div class="tbl-card scroll-x">
          <table class="ops-tbl">
            <thead><tr><th>비용 라인</th><th class="num">FY2023</th><th class="num">FY2024</th></tr></thead>
            <tbody>
{chr(10).join(rows)}
            </tbody>
          </table>
        </div>
      </div>''')

# GOLF — Selling + G&A
sel = notes['GOLF']['selling_note_31']
ga = notes['GOLF']['ga_note_32']
rows = []
rows.append('            <tr style="background:rgba(245,158,11,0.08); font-weight:700;"><td colspan="3">판매비 (Note 31)</td></tr>')
for ln in sel['lines']:
    rows.append(f'''            <tr>
              <td style="padding-left:24px;">{ln["id_label"]}<br><span style="color:var(--ops-muted); font-size:11px;">{ln.get("en_label","—")}</span></td>
              <td class="num">{fmt_bn(ln.get("FY2023"))}</td>
              <td class="num">{fmt_bn(ln.get("FY2024"))}</td>
            </tr>''')
st = sel.get('total',{})
rows.append(f'''            <tr style="font-weight:600;">
              <td style="padding-left:24px;">— 판매비 소계</td>
              <td class="num">{fmt_bn(st.get("FY2023"))}</td>
              <td class="num">{fmt_bn(st.get("FY2024"))}</td>
            </tr>''')
rows.append('            <tr style="background:rgba(245,158,11,0.08); font-weight:700;"><td colspan="3">일반관리비 (Note 32)</td></tr>')
for ln in ga['lines']:
    rows.append(f'''            <tr>
              <td style="padding-left:24px;">{ln["id_label"]}<br><span style="color:var(--ops-muted); font-size:11px;">{ln.get("en_label","—")}</span></td>
              <td class="num">{fmt_bn(ln.get("FY2023"))}</td>
              <td class="num">{fmt_bn(ln.get("FY2024"))}</td>
            </tr>''')
gt = ga.get('total',{})
rows.append(f'''            <tr style="font-weight:600;">
              <td style="padding-left:24px;">— G&A 소계</td>
              <td class="num">{fmt_bn(gt.get("FY2023"))}</td>
              <td class="num">{fmt_bn(gt.get("FY2024"))}</td>
            </tr>''')
opex_section.append(f'''      <div style="margin-bottom:32px;">
        <h3 style="font-size:16px; margin:0 0 10px 0;">🟨 GOLF · 판매비 + 일반관리비 (Note 31·32)</h3>
        <p style="font-size:12px; color:var(--ops-muted); margin:0 0 8px 0;">판매비 5 라인 + G&A 16 라인</p>
        <div class="tbl-card scroll-x">
          <table class="ops-tbl">
            <thead><tr><th>비용 라인</th><th class="num">FY2023</th><th class="num">FY2024</th></tr></thead>
            <tbody>
{chr(10).join(rows)}
            </tbody>
          </table>
        </div>
      </div>''')

# KPIG — G&A note 34 (13 lines)
ga = notes['KPIG']['ga_note_34']
rows = []
for ln in ga['lines']:
    rows.append(f'''            <tr>
              <td>{ln["id_label"]}</td>
              <td class="num">{fmt_bn(ln.get("FY2023"))}</td>
              <td class="num"><strong>{fmt_bn(ln.get("FY2024"))}</strong></td>
            </tr>''')
gt = ga.get('total',{})
rows.append(f'''            <tr style="background:rgba(45,80,22,0.06); font-weight:700;">
              <td>합계</td>
              <td class="num">{fmt_bn(gt.get("FY2023"))}</td>
              <td class="num">{fmt_bn(gt.get("FY2024"))}</td>
            </tr>''')
opex_section.append(f'''      <div style="margin-bottom:32px;">
        <h3 style="font-size:16px; margin:0 0 10px 0;">🟩 KPIG · 일반관리비 (Note 34)</h3>
        <p style="font-size:12px; color:var(--ops-muted); margin:0 0 8px 0;">그룹 G&A 13 라인 — 골프 포함 전 사업부</p>
        <div class="tbl-card scroll-x">
          <table class="ops-tbl">
            <thead><tr><th>비용 라인</th><th class="num">FY2023</th><th class="num">FY2024</th></tr></thead>
            <tbody>
{chr(10).join(rows)}
            </tbody>
          </table>
        </div>
      </div>''')

# ============================================================
# SECTION 3: 13-peer 비용 구조 % (FY2024)
# ============================================================
structure_rows = []
peers_sorted = sorted(peers_v2, key=lambda t: (torder(t), t))
for t in peers_sorted:
    c = clubs[t]
    y24 = fin.get(t,{}).get('yearly',{}).get('2024',{})
    rev = y24.get('revenue')
    op = y24.get('operating_profit')
    np_ = y24.get('net_profit')
    ebitda = y24.get('ebitda')
    # COGS / OpEx not always directly in 5y — derive
    # gp_margin available if both rev and op
    if rev:
        op_margin = (op/rev*100) if op else None
        np_margin = (np_/rev*100) if np_ else None
        ebitda_margin = (ebitda/rev*100) if ebitda else None
        # Cost ratio = (rev - op)/rev
        cost_ratio = ((rev - op)/rev*100) if op is not None else None
    else:
        op_margin=np_margin=ebitda_margin=cost_ratio=None
    tier_color = {'pp':'#3b82f6','resort':'#f59e0b','twn':'#16a34a'}[c['tier']]
    structure_rows.append(f'''            <tr>
              <td class="peer"><a href="clubs/{t.lower()}.html" style="color:var(--ops-ink); font-weight:700; text-decoration:none;">{t}</a><span class="peer-tag peer-tag-{c["tier"]}">{c["tier_label"]}</span></td>
              <td>{c["name"][:24]}</td>
              <td class="num">{fmt_bn(rev)}</td>
              <td class="num">{fmt_pct(cost_ratio)}</td>
              <td class="num"><strong>{fmt_pct(op_margin)}</strong></td>
              <td class="num">{fmt_pct(ebitda_margin)}</td>
              <td class="num">{fmt_pct(np_margin)}</td>
            </tr>''')

# ============================================================
# Assemble HTML
# ============================================================
html = f'''<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>비용 — 인도네시아 골프 운영 벤치마크</title>
<link rel="icon" type="image/svg+xml" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Ccircle cx='32' cy='32' r='30' fill='%232D5016'/%3E%3Ccircle cx='32' cy='32' r='12' fill='%23F5F1E8'/%3E%3C/svg%3E" />
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Pretendard:wght@400;500;600;700&display=swap" rel="stylesheet" />
<link rel="stylesheet" href="ops-style.css?v=20260512c53" />
<style>
  .cost-tab-bar {{ display:flex; gap:6px; flex-wrap:wrap; margin:16px 0 24px 0; border-bottom:2px solid var(--ops-line); }}
  .cost-tab {{ padding:10px 18px; cursor:pointer; font-size:13px; font-weight:600; color:var(--ops-ink-soft); border-bottom:3px solid transparent; margin-bottom:-2px; }}
  .cost-tab.active {{ color:var(--ops-green); border-bottom-color:var(--ops-green); }}
  .cost-panel {{ display:none; }}
  .cost-panel.active {{ display:block; }}
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
    <h1>비용 상세 비교</h1>
    <p class="lede">라인 단위 매출원가 · 판관비 + 13 peer 비용 구조 비율. 단위 IDR (1B = 10억 루피아).</p>
    <div class="cost-tab-bar">
      <div class="cost-tab active" data-panel="cogs">① 매출원가 라인 (4 peer)</div>
      <div class="cost-tab" data-panel="opex">② 판관비 라인 (4 peer)</div>
      <div class="cost-tab" data-panel="ratio">③ 13-peer 비용 구조 %</div>
    </div>
  </div>
</section>

<section class="ops-section">
  <div class="ops-wrap">
    <div class="cost-panel active" id="panel-cogs">
{chr(10).join(cogs_section)}
    </div>
    <div class="cost-panel" id="panel-opex">
{chr(10).join(opex_section)}
    </div>
    <div class="cost-panel" id="panel-ratio">
      <p style="font-size:12px; color:var(--ops-muted); margin:0 0 12px 0;">FY2024 연결 P&L 기준. 비용 비율 = (매출 − 영업이익) / 매출. EBITDA 비율은 EBITDA / 매출.</p>
      <div class="tbl-card scroll-x">
        <table class="ops-tbl">
          <thead>
            <tr>
              <th>Peer</th>
              <th>그룹명</th>
              <th class="num">매출 (IDR)</th>
              <th class="num">총 비용 / 매출</th>
              <th class="num">영업이익률</th>
              <th class="num">EBITDA 마진</th>
              <th class="num">순이익률</th>
            </tr>
          </thead>
          <tbody>
{chr(10).join(structure_rows)}
          </tbody>
        </table>
      </div>
    </div>
  </div>
</section>

<footer class="ops-foot">
  <div class="ops-wrap">
    <p>매출원가·판관비 라인은 AR 주석(Note) 기반 — DMIG·PIPG·GOLF·MDLN·KPIG 라인 공시. 비율은 연결 P&L FY2024.</p>
  </div>
</footer>

<script src="operations.js?v=20260512c3" defer></script>
<script>
(function(){{
  const tabs = document.querySelectorAll('.cost-tab');
  tabs.forEach(t => t.addEventListener('click', () => {{
    tabs.forEach(x => x.classList.remove('active'));
    document.querySelectorAll('.cost-panel').forEach(p => p.classList.remove('active'));
    t.classList.add('active');
    document.getElementById('panel-' + t.dataset.panel).classList.add('active');
  }}));
}})();
</script>
</body>
</html>
'''

with open('cost-hr.html','w',encoding='utf-8') as f:
    f.write(html)
print(f'cost-hr.html: {os.path.getsize("cost-hr.html")/1024:.1f} KB')
