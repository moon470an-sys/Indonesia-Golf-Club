"""Build revenue.html — revenue line breakdown + golf segment + 13-peer comparison."""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import json
import os

clubs = json.load(open('data/_clubs_meta.json','r',encoding='utf-8'))
d5y = json.load(open('../../data/company_financials_5y.json','r',encoding='utf-8'))
fin = {c['ticker']: c for c in d5y['companies'] if 'ticker' in c}
peers_v2 = ['DMIG','PIPG','GOLF','MDLN','KIJA','SMDM','KPIG','SMRA','BSDE','CTRA','ELTY','LPKR','PWON']
def torder(t): return {'pp':1,'resort':2,'twn':3}.get(clubs[t]['tier'], 9)
def fmt_bn(v):
    if v is None: return '—'
    if abs(v) >= 1e12: return f'{v/1e12:,.1f}T'
    if abs(v) >= 1e9: return f'{v/1e9:,.1f}B'
    if abs(v) >= 1e6: return f'{v/1e6:,.1f}M'
    return f'{v:,.0f}'
def fmt_pct(v, dp=1):
    if v is None: return '—'
    return f'{v:,.{dp}f}%'
def fmt_yoy(v):
    if v is None: return '—'
    col = '#16a34a' if v>0 else '#b91c1c' if v<0 else '#666'
    return f'<span style="color:{col}; font-weight:700;">{v:+.1f}%</span>'

notes = {}
for t in peers_v2:
    path = f'data/{t.lower()}_notes.json'
    if os.path.exists(path):
        notes[t] = json.load(open(path,'r',encoding='utf-8'))

# ============================================================
# TAB 1: Pure-play 매출 라인 — DMIG 7 + PIPG 11
# ============================================================
pp_section = []

# DMIG revenue (7 lines, FY22-FY24)
d = notes['DMIG']['revenue_note']
rows = []
tot24 = d['total'].get('FY2024',1)
for ln in d['lines']:
    pct = (ln.get('FY2024')/tot24*100) if (ln.get('FY2024') and tot24) else None
    y23 = ln.get('FY2023'); y24 = ln.get('FY2024')
    yoy = ((y24-y23)/y23*100) if (y23 and y24) else None
    rows.append(f'''            <tr>
              <td>{ln["id_label"]}<br><span style="color:var(--ops-muted); font-size:11px;">{ln.get("en_label","—")}</span></td>
              <td class="num">{fmt_bn(ln.get("FY2022"))}</td>
              <td class="num">{fmt_bn(y23)}</td>
              <td class="num"><strong>{fmt_bn(y24)}</strong></td>
              <td class="num">{fmt_pct(pct)}</td>
              <td class="num">{fmt_yoy(yoy)}</td>
            </tr>''')
total = d['total']
rows.append(f'''            <tr style="background:rgba(45,80,22,0.06); font-weight:700;">
              <td>합계</td>
              <td class="num">{fmt_bn(total.get("FY2022"))}</td>
              <td class="num">{fmt_bn(total.get("FY2023"))}</td>
              <td class="num">{fmt_bn(total.get("FY2024"))}</td>
              <td class="num">100.0%</td>
              <td class="num">{fmt_yoy((total.get("FY2024")-total.get("FY2023"))/total.get("FY2023")*100 if total.get("FY2023") else None)}</td>
            </tr>''')
pp_section.append(f'''      <div style="margin-bottom:32px;">
        <h3 style="font-size:16px; margin:0 0 10px 0;">🟦 DMIG · 매출 라인 (Note {d["note_number"]})</h3>
        <p style="font-size:12px; color:var(--ops-muted); margin:0 0 8px 0;">Pure-play — 골프장·F&B·회원권·스폰서·임대 등 7 라인</p>
        <div class="tbl-card scroll-x">
          <table class="ops-tbl">
            <thead><tr><th>매출 라인</th><th class="num">FY2022</th><th class="num">FY2023</th><th class="num">FY2024</th><th class="num">FY24 비중</th><th class="num">YoY</th></tr></thead>
            <tbody>
{chr(10).join(rows)}
            </tbody>
          </table>
        </div>
      </div>''')

# PIPG revenue_27 (11 lines)
d = notes['PIPG']['revenue_note_27']
rows = []
tot24 = d['total'].get('FY2024',1)
for ln in d['lines']:
    pct = (ln.get('FY2024')/tot24*100) if (ln.get('FY2024') and tot24) else None
    y23 = ln.get('FY2023'); y24 = ln.get('FY2024')
    yoy = ((y24-y23)/y23*100) if (y23 and y24) else None
    rows.append(f'''            <tr>
              <td>{ln["id_label"]}<br><span style="color:var(--ops-muted); font-size:11px;">{ln.get("en_label","—")}</span></td>
              <td class="num">{fmt_bn(y23)}</td>
              <td class="num"><strong>{fmt_bn(y24)}</strong></td>
              <td class="num">{fmt_pct(pct)}</td>
              <td class="num">{fmt_yoy(yoy)}</td>
            </tr>''')
total = d['total']
yoy_tot = ((total.get("FY2024")-total.get("FY2023"))/total.get("FY2023")*100) if total.get("FY2023") else None
rows.append(f'''            <tr style="background:rgba(45,80,22,0.06); font-weight:700;">
              <td>합계</td>
              <td class="num">{fmt_bn(total.get("FY2023"))}</td>
              <td class="num">{fmt_bn(total.get("FY2024"))}</td>
              <td class="num">100.0%</td>
              <td class="num">{fmt_yoy(yoy_tot)}</td>
            </tr>''')
pp_section.append(f'''      <div style="margin-bottom:32px;">
        <h3 style="font-size:16px; margin:0 0 10px 0;">🟦 PIPG · 매출 라인 (Note 27)</h3>
        <p style="font-size:12px; color:var(--ops-muted); margin:0 0 8px 0;">Pure-play — 골프·F&B·회원권·아카데미·드라이빙·임대 등 11 라인</p>
        <div class="tbl-card scroll-x">
          <table class="ops-tbl">
            <thead><tr><th>매출 라인</th><th class="num">FY2023</th><th class="num">FY2024</th><th class="num">FY24 비중</th><th class="num">YoY</th></tr></thead>
            <tbody>
{chr(10).join(rows)}
            </tbody>
          </table>
        </div>
      </div>''')

# ============================================================
# TAB 2: Golf segment (peers with golf segment disclosed)
# ============================================================
seg_section = []

# GOLF revenue_29 by operations
g = notes['GOLF']['revenue_note_29']
by_ops = g.get('by_operations',{})
rows = []
go_total = by_ops.get('total',{}).get('FY2024',1)
for ln in by_ops.get('lines',[]):
    y23 = ln.get('FY2023'); y24 = ln.get('FY2024')
    yoy = ((y24-y23)/y23*100) if (y23 and y24) else None
    pct = (y24/go_total*100) if (y24 and go_total) else None
    rows.append(f'''            <tr>
              <td>{ln["id_label"]}<br><span style="color:var(--ops-muted); font-size:11px;">{ln.get("en_label","—")}</span></td>
              <td class="num">{fmt_bn(y23)}</td>
              <td class="num"><strong>{fmt_bn(y24)}</strong></td>
              <td class="num">{fmt_pct(pct)}</td>
              <td class="num">{fmt_yoy(yoy)}</td>
            </tr>''')
go_tot = by_ops.get('total',{})
yoy_t = ((go_tot.get("FY2024")-go_tot.get("FY2023"))/go_tot.get("FY2023")*100) if go_tot.get("FY2023") else None
rows.append(f'''            <tr style="background:rgba(45,80,22,0.06); font-weight:700;">
              <td>합계</td>
              <td class="num">{fmt_bn(go_tot.get("FY2023"))}</td>
              <td class="num">{fmt_bn(go_tot.get("FY2024"))}</td>
              <td class="num">100.0%</td>
              <td class="num">{fmt_yoy(yoy_t)}</td>
            </tr>''')
if rows:
    seg_section.append(f'''      <div style="margin-bottom:32px;">
        <h3 style="font-size:16px; margin:0 0 10px 0;">🟨 GOLF · 사업부별 매출 (Note 29)</h3>
        <p style="font-size:12px; color:var(--ops-muted); margin:0 0 8px 0;">Bali 리조트 — 골프·부동산·F&B 사업부 분해</p>
        <div class="tbl-card scroll-x">
          <table class="ops-tbl">
            <thead><tr><th>사업부</th><th class="num">FY2023</th><th class="num">FY2024</th><th class="num">FY24 비중</th><th class="num">YoY</th></tr></thead>
            <tbody>
{chr(10).join(rows)}
            </tbody>
          </table>
        </div>
      </div>''')

# MDLN revenue (segment level) + golf-specific from segment_note_32
m_rev = notes['MDLN']['revenue_note_25']
rows = []
tot24 = m_rev['total'].get('FY2024',1)
for ln in m_rev['lines']:
    pct = (ln.get('FY2024')/tot24*100) if (ln.get('FY2024') and tot24) else None
    y23 = ln.get('FY2023'); y24 = ln.get('FY2024')
    rows.append(f'''            <tr>
              <td>{ln["id_label"]}<br><span style="color:var(--ops-muted); font-size:11px;">{ln.get("en_label","—")} · {ln.get("category","")}</span></td>
              <td class="num">{fmt_bn(y23)}</td>
              <td class="num"><strong>{fmt_bn(y24)}</strong></td>
              <td class="num">{fmt_pct(pct)}</td>
            </tr>''')
total = m_rev['total']
rows.append(f'''            <tr style="background:rgba(45,80,22,0.06); font-weight:700;">
              <td>합계</td>
              <td class="num">{fmt_bn(total.get("FY2023"))}</td>
              <td class="num">{fmt_bn(total.get("FY2024"))}</td>
              <td class="num">100.0%</td>
            </tr>''')
seg_section.append(f'''      <div style="margin-bottom:32px;">
        <h3 style="font-size:16px; margin:0 0 10px 0;">🟩 MDLN · 그룹 매출 라인 (Note 25)</h3>
        <p style="font-size:12px; color:var(--ops-muted); margin:0 0 8px 0;">Township — 토지·주택·아파트·골프·F&B 등 11 라인 (골프는 비중 작음)</p>
        <div class="tbl-card scroll-x">
          <table class="ops-tbl">
            <thead><tr><th>매출 라인</th><th class="num">FY2023</th><th class="num">FY2024</th><th class="num">FY24 비중</th></tr></thead>
            <tbody>
{chr(10).join(rows)}
            </tbody>
          </table>
        </div>
      </div>''')

# KPIG revenue_31 (4 lines, golf bundled with hotel-resort)
k = notes['KPIG']['revenue_note_31']
rows = []
tot24 = k['total'].get('FY2024',1)
for ln in k['lines']:
    pct = (ln.get('FY2024')/tot24*100) if (ln.get('FY2024') and tot24) else None
    y23 = ln.get('FY2023'); y24 = ln.get('FY2024')
    note_extra = f' <span style="color:#b91c1c; font-size:10.5px;">※ 골프 별도 미공시</span>' if ln.get('note') else ''
    rows.append(f'''            <tr>
              <td>{ln["id_label"]}{note_extra}<br><span style="color:var(--ops-muted); font-size:11px;">{ln.get("en_label","—")}</span></td>
              <td class="num">{fmt_bn(y23)}</td>
              <td class="num"><strong>{fmt_bn(y24)}</strong></td>
              <td class="num">{fmt_pct(pct)}</td>
            </tr>''')
total = k['total']
rows.append(f'''            <tr style="background:rgba(45,80,22,0.06); font-weight:700;">
              <td>합계</td>
              <td class="num">{fmt_bn(total.get("FY2023"))}</td>
              <td class="num">{fmt_bn(total.get("FY2024"))}</td>
              <td class="num">100.0%</td>
            </tr>''')
seg_section.append(f'''      <div style="margin-bottom:32px;">
        <h3 style="font-size:16px; margin:0 0 10px 0;">🟩 KPIG · 그룹 매출 라인 (Note 31)</h3>
        <p style="font-size:12px; color:var(--ops-muted); margin:0 0 8px 0;">Township — 호텔·리조트·골프 번들 / 부동산관리 / 임대 / 기타</p>
        <div class="tbl-card scroll-x">
          <table class="ops-tbl">
            <thead><tr><th>매출 라인</th><th class="num">FY2023</th><th class="num">FY2024</th><th class="num">FY24 비중</th></tr></thead>
            <tbody>
{chr(10).join(rows)}
            </tbody>
          </table>
        </div>
      </div>''')

# Tier-3 골프 segment summary (KIJA · SMDM · SMRA)
seg_summary_rows = []
# KIJA golf segment_FY2024 (unit Rp million)
kg = notes['KIJA']['segment_info_note_34']['golf_segment_FY2024']
seg_summary_rows.append(f'''            <tr>
              <td class="peer"><a href="clubs/kija.html" style="color:var(--ops-ink); font-weight:700; text-decoration:none;">KIJA</a><span class="peer-tag peer-tag-twn">🟩 Township</span></td>
              <td>Golf 세그먼트 (Jababeka + Borobudur)</td>
              <td class="num"><strong>{fmt_bn(kg["revenue"]*1e6)}</strong></td>
              <td class="num">{fmt_bn(kg["cogs"]*1e6)}</td>
              <td class="num">{fmt_bn(kg["gross_profit"]*1e6)}</td>
              <td class="num">{fmt_bn(kg["operating_income_calc"]*1e6)}</td>
              <td class="num">{fmt_pct(kg["gross_profit"]/kg["revenue"]*100)}</td>
            </tr>''')
# SMDM golf segment (cogs is negative by sign convention)
sg = notes['SMDM']['segment_info_note_29']['FY2024']['Golf dan Country Club']
sg_rev = sg.get('revenue')
sg_cogs = abs(sg.get('cogs',0)) if sg.get('cogs') is not None else None
sg_gp = sg.get('gross_profit')
sg_op = None
if sg_rev and sg.get('selling') is not None and sg.get('ga') is not None:
    sg_op = sg_gp + sg.get('selling') + sg.get('ga')
if sg_rev:
    seg_summary_rows.append(f'''            <tr>
              <td class="peer"><a href="clubs/smdm.html" style="color:var(--ops-ink); font-weight:700; text-decoration:none;">SMDM</a><span class="peer-tag peer-tag-twn">🟩 Township</span></td>
              <td>Golf dan Country Club (Rancamaya)</td>
              <td class="num"><strong>{fmt_bn(sg_rev)}</strong></td>
              <td class="num">{fmt_bn(sg_cogs)}</td>
              <td class="num">{fmt_bn(sg_gp)}</td>
              <td class="num">{fmt_bn(sg_op)}</td>
              <td class="num">{fmt_pct(sg_gp/sg_rev*100) if (sg_gp and sg_rev) else "—"}</td>
            </tr>''')
# SMRA Rekreasi (Leisure) — values are in thousand IDR per unit_after_conversion note
sm = notes['SMRA']['revenue_note_31']['Rekreasi_Leisure']
sm_cogs_d = notes['SMRA']['cogs_note_32']['Rekreasi_Leisure_COGS']
sm_rev = sm.get('FY2024_comparative')  # FY2024
sm_cogs = sm_cogs_d.get('FY2024_comparative')
if sm_rev: sm_rev *= 1000  # thousand → IDR
if sm_cogs: sm_cogs *= 1000
sm_gp = (sm_rev - sm_cogs) if (sm_rev and sm_cogs) else None
if sm_rev:
    seg_summary_rows.append(f'''            <tr>
              <td class="peer"><a href="clubs/smra.html" style="color:var(--ops-ink); font-weight:700; text-decoration:none;">SMRA</a><span class="peer-tag peer-tag-twn">🟩 Township</span></td>
              <td>Rekreasi/Leisure (Gading Raya 포함)</td>
              <td class="num"><strong>{fmt_bn(sm_rev)}</strong></td>
              <td class="num">{fmt_bn(sm_cogs)}</td>
              <td class="num">{fmt_bn(sm_gp)}</td>
              <td class="num">—</td>
              <td class="num">{fmt_pct(sm_gp/sm_rev*100) if (sm_gp and sm_rev) else "—"}</td>
            </tr>''')

if seg_summary_rows:
    seg_section.append(f'''      <div style="margin-bottom:32px;">
        <h3 style="font-size:16px; margin:0 0 10px 0;">🟩 Tier-3 골프 세그먼트 요약</h3>
        <p style="font-size:12px; color:var(--ops-muted); margin:0 0 8px 0;">KIJA·SMDM·SMRA — segment note 기반 골프 부문 매출/원가/마진</p>
        <div class="tbl-card scroll-x">
          <table class="ops-tbl">
            <thead><tr><th>Peer</th><th>세그먼트</th><th class="num">매출 FY24</th><th class="num">매출원가</th><th class="num">매출총이익</th><th class="num">영업이익</th><th class="num">GP 마진</th></tr></thead>
            <tbody>
{chr(10).join(seg_summary_rows)}
            </tbody>
          </table>
        </div>
      </div>''')

# ============================================================
# TAB 3: 13-peer 그룹 매출 + 골프 매출 비중 (5Y)
# ============================================================
peers_sorted = sorted(peers_v2, key=lambda t: (torder(t), t))
ratio_rows = []
for t in peers_sorted:
    c = clubs[t]
    cy = fin.get(t,{}).get('yearly',{})
    y24 = cy.get('2024',{}).get('revenue')
    y23 = cy.get('2023',{}).get('revenue')
    y22 = cy.get('2022',{}).get('revenue')
    y21 = cy.get('2021',{}).get('revenue')
    y20 = cy.get('2020',{}).get('revenue')
    cagr = ((y24/y20)**(1/4) - 1)*100 if (y24 and y20 and y20>0) else None
    yoy = ((y24-y23)/y23*100) if (y23 and y24) else None
    # Golf rev FY24 (from clubs meta as string)
    golf_rev_str = c.get('golf_rev_fy24','—')
    ratio_rows.append(f'''            <tr>
              <td class="peer"><a href="clubs/{t.lower()}.html" style="color:var(--ops-ink); font-weight:700; text-decoration:none;">{t}</a><span class="peer-tag peer-tag-{c["tier"]}">{c["tier_label"]}</span></td>
              <td>{c["name"][:24]}</td>
              <td class="num">{fmt_bn(y20)}</td>
              <td class="num">{fmt_bn(y21)}</td>
              <td class="num">{fmt_bn(y22)}</td>
              <td class="num">{fmt_bn(y23)}</td>
              <td class="num"><strong>{fmt_bn(y24)}</strong></td>
              <td class="num">{fmt_yoy(yoy)}</td>
              <td class="num">{fmt_pct(cagr)}</td>
              <td>{golf_rev_str}</td>
            </tr>''')

# Assemble HTML
html = f'''<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>매출 — 인도네시아 골프 운영 벤치마크</title>
<link rel="icon" type="image/svg+xml" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Ccircle cx='32' cy='32' r='30' fill='%232D5016'/%3E%3Ccircle cx='32' cy='32' r='12' fill='%23F5F1E8'/%3E%3C/svg%3E" />
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Pretendard:wght@400;500;600;700&display=swap" rel="stylesheet" />
<link rel="stylesheet" href="ops-style.css?v=20260512c53" />
<style>
  .rev-tab-bar {{ display:flex; gap:6px; flex-wrap:wrap; margin:16px 0 24px 0; border-bottom:2px solid var(--ops-line); }}
  .rev-tab {{ padding:10px 18px; cursor:pointer; font-size:13px; font-weight:600; color:var(--ops-ink-soft); border-bottom:3px solid transparent; margin-bottom:-2px; }}
  .rev-tab.active {{ color:var(--ops-green); border-bottom-color:var(--ops-green); }}
  .rev-panel {{ display:none; }}
  .rev-panel.active {{ display:block; }}
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
    <nav class="ops-nav"><a href="clubs/index.html">⛳ 클럽</a><a href="unit-economics.html">단위 경제</a><a href="revenue.html" class="active">매출</a><a href="cost-hr.html">비용</a><a href="assets.html">시설</a><a href="risk.html">위험</a><a href="../../index.html" class="back">← 지도</a></nav>
  </div>
</header>

<section class="ops-hero">
  <div class="ops-wrap">
    <h1>매출 라인 분해</h1>
    <p class="lede">Pure-play AR 매출 주석 라인별 분해 + 골프 세그먼트 + 13-peer 그룹 매출 5년.</p>
    <div class="rev-tab-bar">
      <div class="rev-tab active" data-panel="pp">① Pure-play 매출 라인 (DMIG·PIPG)</div>
      <div class="rev-tab" data-panel="seg">② 골프 세그먼트 (GOLF·MDLN·KPIG·Tier3)</div>
      <div class="rev-tab" data-panel="grp">③ 13-peer 그룹 매출 5Y</div>
    </div>
  </div>
</section>

<section class="ops-section">
  <div class="ops-wrap">
    <div class="rev-panel active" id="panel-pp">
{chr(10).join(pp_section)}
    </div>
    <div class="rev-panel" id="panel-seg">
{chr(10).join(seg_section)}
    </div>
    <div class="rev-panel" id="panel-grp">
      <p style="font-size:12px; color:var(--ops-muted); margin:0 0 12px 0;">그룹 연결 매출 (IDR). 골프 매출은 segment note 직접 공시 (DMIG·PIPG·GOLF·MDLN·KIJA·SMDM) 또는 라인 추정 (KPIG·SMRA).</p>
      <div class="tbl-card scroll-x">
        <table class="ops-tbl">
          <thead>
            <tr>
              <th>Peer</th>
              <th>그룹명</th>
              <th class="num">FY2020</th>
              <th class="num">FY2021</th>
              <th class="num">FY2022</th>
              <th class="num">FY2023</th>
              <th class="num">FY2024</th>
              <th class="num">YoY</th>
              <th class="num">4Y CAGR</th>
              <th>골프 매출 FY24</th>
            </tr>
          </thead>
          <tbody>
{chr(10).join(ratio_rows)}
          </tbody>
        </table>
      </div>
    </div>
  </div>
</section>

<footer class="ops-foot">
  <div class="ops-wrap">
    <p>매출 라인은 AR 주석 (Note). 그룹 매출은 연결 P&L. 골프 매출은 segment note 또는 라인 합산.</p>
  </div>
</footer>

<script src="operations.js?v=20260512c3" defer></script>
<script>
(function(){{
  const tabs = document.querySelectorAll('.rev-tab');
  tabs.forEach(t => t.addEventListener('click', () => {{
    tabs.forEach(x => x.classList.remove('active'));
    document.querySelectorAll('.rev-panel').forEach(p => p.classList.remove('active'));
    t.classList.add('active');
    document.getElementById('panel-' + t.dataset.panel).classList.add('active');
  }}));
}})();
</script>
</body>
</html>
'''

with open('revenue.html','w',encoding='utf-8') as f:
    f.write(html)
print(f'revenue.html: {os.path.getsize("revenue.html")/1024:.1f} KB')
