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

# ============================================================
# Category rules for OpEx line aggregation (peer × category matrix)
# Order matters — first match wins
# ============================================================
CATEGORY_RULES = [
    ('인건비',      ['gaji','upah','tunjangan','imbalan kerja','kesejahteraan','beban diklat']),
    ('감가상각',    ['penyusutan','amortisasi']),
    ('시설관리',    ['perbaikan','pemeliharaan','perawatan']),
    ('세금·법률',   ['pajak','perijinan','perizinan','jasa profesional','jasa tenaga ahli','audit','konsultan','legal']),
    ('수도광열',    ['listrik','air','utilitas']),
    ('광고·마케팅',  ['iklan','promosi','pemasaran','komisi penjualan','branding','sponsor','tournament']),
    ('보험',        ['asuransi']),
    ('통신·IT',     ['telepon','teleks','fax','komunikasi','internet','perangkat lunak','teknologi informasi','administrasi bank','biaya kartu','pos,']),
    ('사무·소모품', ['alat-alat tulis','cetakan','perlengkapan kantor','perlengkapan dan administrasi','perlengkapan dan peralatan','perlengkapan pemasaran']),
    ('청소·보안',   ['kebersihan','keamanan','jasa manajemen']),
    ('운송·출장',   ['transportasi','perjalanan','akomodasi']),
]
def categorize(label):
    s = label.lower()
    for cat, kws in CATEGORY_RULES:
        if any(kw in s for kw in kws):
            return cat
    return '기타'

# ============================================================
# Extract COGS / OpEx totals + by-category for each peer
# ============================================================
def extract_totals(t):
    """Return (cogs_total_by_year_dict, opex_total_by_year_dict)."""
    d = notes.get(t, {})
    cogs_total = {}
    opex_total = {}

    # COGS totals (multiple AR note key conventions)
    for key in ['cogs_note','cogs_note_28','cogs_note_30']:
        if key in d and 'total' in d[key]:
            for ykey, v in d[key]['total'].items():
                yr = ykey[-4:] if ykey.startswith('FY') else ykey
                if v: cogs_total[yr] = v
    # MDLN special: golf_plus_clubhouse_subtotal
    if 'cogs_note_26' in d:
        sub = d['cogs_note_26'].get('golf_plus_clubhouse_subtotal',{})
        for ykey, v in sub.items():
            yr = ykey[-4:] if ykey.startswith('FY') else ykey
            if v: cogs_total[yr] = v

    # OpEx totals (combine selling+G&A where split)
    if 'opex_note' in d and 'total' in d['opex_note']:
        for ykey, v in d['opex_note']['total'].items():
            yr = ykey[-4:] if ykey.startswith('FY') else ykey
            if v: opex_total[yr] = v
    if 'opex_note_29' in d and 'total' in d['opex_note_29']:
        for ykey, v in d['opex_note_29']['total'].items():
            yr = ykey[-4:] if ykey.startswith('FY') else ykey
            if v: opex_total[yr] = v
    # GOLF: Selling 31 + G&A 32
    if 'selling_note_31' in d and 'ga_note_32' in d:
        s_tot = d['selling_note_31'].get('total',{})
        g_tot = d['ga_note_32'].get('total',{})
        for ykey in set(list(s_tot.keys()) + list(g_tot.keys())):
            yr = ykey[-4:] if ykey.startswith('FY') else ykey
            sv = s_tot.get(ykey); gv = g_tot.get(ykey)
            if sv is not None or gv is not None:
                opex_total[yr] = (sv or 0) + (gv or 0)
    # KPIG: G&A note 34 only
    if 'ga_note_34' in d and 'total' in d['ga_note_34']:
        for ykey, v in d['ga_note_34']['total'].items():
            yr = ykey[-4:] if ykey.startswith('FY') else ykey
            if v: opex_total[yr] = v
    # KIJA golf segment FY24 (Rp million)
    if t == 'KIJA':
        seg = d.get('segment_info_note_34',{}).get('golf_segment_FY2024',{})
        if seg.get('cogs') is not None: cogs_total['2024'] = seg['cogs']*1e6
        if seg.get('selling') is not None or seg.get('ga_expenses') is not None:
            opex_total['2024'] = (seg.get('selling',0) + seg.get('ga_expenses',0)) * 1e6
    # SMDM golf segment FY24 (raw IDR; cogs has negative sign)
    if t == 'SMDM':
        seg = d.get('segment_info_note_29',{}).get('FY2024',{}).get('Golf dan Country Club',{})
        if seg.get('cogs') is not None: cogs_total['2024'] = abs(seg['cogs'])
        sel = seg.get('selling') or 0; ga = seg.get('ga') or 0
        if sel or ga: opex_total['2024'] = abs(sel) + abs(ga)
    # SMRA Rekreasi/Leisure FY24 (thousand → IDR)
    if t == 'SMRA':
        sm_cogs = d.get('cogs_note_32',{}).get('Rekreasi_Leisure_COGS',{}).get('FY2024_comparative')
        if sm_cogs: cogs_total['2024'] = sm_cogs * 1000
    return cogs_total, opex_total

def extract_opex_by_cat(t):
    """Return {year: {category: sum, ...}, ...} for OpEx lines."""
    d = notes.get(t, {})
    result = {}
    def add_lines(lines):
        for ln in lines:
            cat = categorize(ln['id_label'])
            for ykey, v in ln.items():
                if not ykey.startswith('FY') or v is None: continue
                yr = ykey[-4:]
                result.setdefault(yr, {}).setdefault(cat, 0)
                result[yr][cat] += v
    for key in ['opex_note','opex_note_29','selling_note_31','ga_note_32','ga_note_34']:
        if key in d and 'lines' in d[key]:
            add_lines(d[key]['lines'])
    return result

def extract_cogs_by_cat(t):
    """Categorize COGS lines where the AR breaks COGS down by cost-type rather than sub-segment.
    Only MDLN reports COGS as Gaji/Penyusutan/Lain-lain (cost-type within each sub-segment).
    DMIG/PIPG/GOLF report COGS as sub-segments (Lapangan golf, Restoran, ...) which cannot
    be mapped onto the 11-category cost-type scheme — those return empty dict."""
    d = notes.get(t, {})
    result = {}
    def add_lines(lines):
        for ln in lines:
            cat = categorize(ln['id_label'])
            for ykey, v in ln.items():
                if not ykey.startswith('FY') or v is None: continue
                yr = ykey[-4:]
                result.setdefault(yr, {}).setdefault(cat, 0)
                result[yr][cat] += v
    # MDLN — golf + clubhouse direct cost lines (cost-type within sub-segment)
    if t == 'MDLN' and 'cogs_note_26' in d:
        n = d['cogs_note_26']
        add_lines(n.get('golf_course_direct_cost_lines', []))
        add_lines(n.get('club_house_restaurant_direct_cost_lines', []))
    return result

# Categories order (display)
CAT_ORDER = ['인건비','감가상각','시설관리','세금·법률','수도광열','광고·마케팅','보험','통신·IT','사무·소모품','청소·보안','운송·출장','기타']

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
    cogs_tot, opex_tot = extract_totals(t)
    opex_cat = extract_opex_by_cat(t)
    cogs_cat = extract_cogs_by_cat(t)
    # Combined operating cost (COGS + OpEx) per year — neutralizes classification differences
    total_opcost = {}
    for yr in set(list(cogs_tot.keys()) + list(opex_tot.keys())):
        cv = cogs_tot.get(yr) or 0
        ov = opex_tot.get(yr) or 0
        if cv or ov:
            total_opcost[yr] = cv + ov
    # Scope revenue — what revenue the COGS/OpEx note actually covers (for honest ratio)
    SCOPE_REV_OVERLAY = {
        'KIJA': {'2024': 85019 * 1e6},                     # golf segment rev
        'SMDM': {'2024': 63282214554},                     # golf segment rev
        'SMRA': {'2024': 66672127 * 1000},                 # Rekreasi/Leisure segment
        'MDLN': {'2023': 68985399881, '2024': 74374916470},# golf+clubhouse subtotal
    }
    scope_rev = {}
    overlay = SCOPE_REV_OVERLAY.get(t, {})
    for yr in ['2020','2021','2022','2023','2024']:
        scope_rev[yr] = overlay.get(yr) or (yearly[yr]['rev'])
    # Coverage label — what does COGS/OpEx note actually represent
    cogs_cov = {
        'DMIG':'전사 (Pure-play)','PIPG':'전사 (Pure-play)',
        'GOLF':'사업부 합계','MDLN':'골프+클럽하우스 부문',
        'KIJA':'골프 segment FY24','SMDM':'골프 segment FY24','SMRA':'Rekreasi segment FY24',
    }.get(t,'—')
    opex_cov = {
        'DMIG':'전사 (Pure-play)','PIPG':'전사 (Pure-play)',
        'GOLF':'Selling+G&A','KPIG':'그룹 G&A 만',
        'KIJA':'골프 segment (Selling+G&A) FY24','SMDM':'골프 segment (Selling+G&A) FY24',
    }.get(t,'—')
    peer_data[t] = {
        'name': c['name'],
        'tier': c['tier'],
        'tier_label': c['tier_label'],
        'yearly': yearly,
        'cogs_total': cogs_tot,    # {'2022': val, ...}
        'opex_total': opex_tot,
        'total_opcost': total_opcost,  # COGS + OpEx (분류 체계 차이 상쇄용)
        'opex_by_cat': opex_cat,   # {'2023': {'인건비': val, ...}}
        'cogs_by_cat': cogs_cat,   # MDLN만 데이터 존재
        'scope_rev': scope_rev,
        'cogs_cov': cogs_cov,
        'opex_cov': opex_cov,
    }

peer_data_json = json.dumps(peer_data, ensure_ascii=False)
cat_order_json = json.dumps(CAT_ORDER, ensure_ascii=False)

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
<link rel="stylesheet" href="ops-style.css?v=20260513c82" />
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
  /* Sticky thead + first-column for wide cmp tables */
  .sticky-tbl thead th { position:sticky; top:0; background:var(--ops-bg); z-index:2; box-shadow:inset 0 -2px 0 var(--ops-line); }
  .sticky-tbl tbody td:first-child, .sticky-tbl thead th:first-child { position:sticky; left:0; background:var(--ops-surface); z-index:1; box-shadow:1px 0 0 var(--ops-line); }
  .sticky-tbl thead th:first-child { background:var(--ops-bg); z-index:3; }
  /* Sortable headers */
  .sortable { cursor:pointer; user-select:none; position:relative; padding-right:18px !important; }
  .sortable:hover { background:rgba(45,80,22,0.06); }
  .sortable::after { content:'⇅'; position:absolute; right:6px; top:50%; transform:translateY(-50%); opacity:0.25; font-size:10px; }
  .sortable.asc::after { content:'▲'; opacity:1; color:var(--ops-green); }
  .sortable.desc::after { content:'▼'; opacity:1; color:var(--ops-green); }
  /* Category mix stacked bar visualization */
  .mix-bar-section { background:var(--ops-surface); border:1px solid var(--ops-line); border-radius:10px; padding:18px 20px; margin:0 0 24px 0; }
  .mix-bar-row { display:grid; grid-template-columns: 120px 1fr 90px; gap:12px; align-items:center; margin:6px 0; font-size:12px; }
  .mix-bar-label { font-weight:700; color:var(--ops-ink); }
  .mix-bar-label .tag { display:inline-block; font-size:9.5px; font-weight:600; padding:1px 5px; border-radius:3px; margin-left:4px; vertical-align:middle; }
  .mix-bar-track { display:flex; height:22px; background:var(--ops-bg); border-radius:4px; overflow:hidden; }
  .mix-bar-seg { display:flex; align-items:center; justify-content:center; font-size:10px; color:white; font-weight:600; white-space:nowrap; cursor:default; transition:opacity 0.15s; }
  .mix-bar-seg:hover { opacity:0.85; }
  .mix-bar-total { text-align:right; font-weight:700; color:var(--ops-ink); font-size:12px; font-variant-numeric:tabular-nums; }
  .mix-legend { display:flex; flex-wrap:wrap; gap:8px 14px; margin:14px 0 4px 0; font-size:11.5px; color:var(--ops-ink-soft); }
  .mix-legend-item { display:inline-flex; align-items:center; gap:5px; }
  .mix-legend-swatch { width:11px; height:11px; border-radius:2px; display:inline-block; }
  @media (max-width: 720px) {
    .mix-bar-row { grid-template-columns: 80px 1fr 70px; gap:8px; font-size:11px; }
    .mix-bar-seg { font-size:9px; }
  }
  /* Tier benchmark rows */
  .bench-row td { background:rgba(45,80,22,0.04) !important; font-size:12px; color:var(--ops-ink-soft); border-top:2px solid var(--ops-line); }
  .bench-row td:first-child { font-weight:700; color:var(--ops-ink); }
  .bench-row.tier-pp    td:first-child { color:#3b82f6; }
  .bench-row.tier-resort td:first-child { color:#f59e0b; }
  .bench-row.tier-twn   td:first-child { color:#16a34a; }
  .bench-row.overall td:first-child { color:var(--ops-green); }
  /* Action bar */
  .action-bar { display:flex; gap:8px; flex-wrap:wrap; align-items:center; margin:6px 0 12px 0; }
  .action-btn { padding:6px 12px; border:1px solid var(--ops-line); background:var(--ops-surface); border-radius:6px; font-size:12px; font-weight:600; cursor:pointer; color:var(--ops-ink-soft); display:inline-flex; align-items:center; gap:4px; }
  .action-btn:hover { background:rgba(45,80,22,0.05); }
  .action-btn.success { background:#16a34a; color:white; border-color:#16a34a; }
  /* Highest-value cell in matrix row */
  #opex-cat-tbody td.row-max { background:rgba(245,158,11,0.10); font-weight:700; border-radius:3px; }
  /* Category matrix hover cross-highlight */
  #opex-cat-tbl tbody tr:hover td { background:rgba(45,80,22,0.04); }
  #opex-cat-tbl tbody tr:hover td:first-child { background:rgba(45,80,22,0.10); }
  body.theme-dark #opex-cat-tbl tbody tr:hover td { background:rgba(34,197,94,0.06); }
  body.theme-dark #opex-cat-tbl tbody tr:hover td:first-child { background:rgba(34,197,94,0.14); }
  #opex-cat-tbl td.col-highlight { outline:2px solid rgba(245,158,11,0.55); outline-offset:-2px; position:relative; z-index:1; }
  /* Cross-section peer highlight: 4개 peer-row 표 ↔ 카테고리 매트릭스 컬럼 sync */
  .ops-tbl tbody tr.peer-highlight td:first-child { background:rgba(245,158,11,0.18); box-shadow:inset 3px 0 0 #f59e0b; }
  #opex-cat-tbl td.peer-col-highlight { outline:2px dashed rgba(245,158,11,0.7); outline-offset:-2px; position:relative; z-index:1; background:rgba(245,158,11,0.08); }
  body.theme-dark .ops-tbl tbody tr.peer-highlight td:first-child { background:rgba(245,158,11,0.24); }
  body.theme-dark #opex-cat-tbl td.peer-col-highlight { background:rgba(245,158,11,0.16); }
  /* Theme toggle */
  .theme-toggle { position:absolute; top:14px; right:14px; padding:5px 10px; border:1px solid var(--ops-line); background:var(--ops-surface); border-radius:999px; font-size:13px; cursor:pointer; color:var(--ops-ink); z-index:10; }
  .theme-toggle:hover { background:rgba(45,80,22,0.06); }
  .ops-hero { position:relative; }
  body.theme-dark { --ops-bg:#0f172a; --ops-surface:#1e293b; --ops-ink:#e2e8f0; --ops-ink-soft:#cbd5e1; --ops-muted:#94a3b8; --ops-line:#334155; --ops-green:#22c55e; }
  body.theme-dark .ops-tbl thead th { background:#0f172a; }
  body.theme-dark .ops-tbl tbody tr:hover { background:rgba(34,197,94,0.06); }
  body.theme-dark .sticky-tbl tbody td:first-child, body.theme-dark .sticky-tbl thead th:first-child { background:#1e293b; }
  body.theme-dark .sticky-tbl thead th:first-child { background:#0f172a; }
  body.theme-dark .bench-row td { background:rgba(34,197,94,0.06) !important; }
  body.theme-dark #opex-cat-tbody td.row-max { background:rgba(245,158,11,0.18); }
  body.theme-dark .mix-bar-section, body.theme-dark .mix-bar-track { background:#1e293b; }
  body.theme-dark .mix-bar-track { background:#0f172a; }
  /* Tier filter pills (Tab ①, ④) */
  .tier-pills { display:flex; gap:8px; flex-wrap:wrap; align-items:center; margin:8px 0 4px 0; }
  .tier-pill { padding:5px 12px; border:1px solid var(--ops-line); background:var(--ops-surface); border-radius:999px; font-size:12px; font-weight:600; cursor:pointer; color:var(--ops-ink-soft); }
  .tier-pill.active { background:var(--ops-green); color:white; border-color:var(--ops-green); }
  .tier-pill:hover:not(.active) { background:rgba(45,80,22,0.05); }
  tr.tier-hidden { display:none; }
  /* Print */
  @media print {
    @page { size: A4 landscape; margin: 10mm; }
    body { background:white !important; color:black !important; }
    .ops-head, .ops-foot, .year-bar, .cost-tab-bar, .action-bar, .tier-pills, .theme-toggle, .trend-mode-toggle { display:none !important; }
    .ops-hero { padding:0 0 6px 0; }
    .ops-hero h1 { font-size:17px; margin:0 0 4px 0; }
    .ops-hero .lede, .ops-hero > .ops-wrap > div[style*="background:rgba(245"] { display:none; }
    .cost-panel { display:block !important; page-break-before:always; }
    .cost-panel:first-of-type { page-break-before:auto; }
    .ops-tbl { font-size:9px; }
    .ops-tbl thead th { background:white !important; border-bottom:1.5px solid black; padding:4px 5px; position:static !important; }
    .ops-tbl tbody td { border-bottom:0.5px solid #ccc; padding:3px 5px; }
    .sortable::after { display:none; }
    .peer-tag { border:0.5px solid #888; padding:0 3px; font-size:8px; }
    a { color:black !important; text-decoration:none !important; }
    .bench-row td { background:#f5f5f5 !important; }
    .mix-bar-seg, .row-max { -webkit-print-color-adjust:exact; print-color-adjust:exact; }
  }
  /* Mobile column priority */
  @media (max-width:720px) {
    .ops-tbl .col-low-prio { display:none; }
  }
  /* Top performer cards */
  .top-perf { display:grid; grid-template-columns:repeat(auto-fit, minmax(170px, 1fr)); gap:10px; margin:14px 0 10px 0; }
  .top-perf-card { background:linear-gradient(135deg, rgba(245,158,11,0.08), rgba(245,158,11,0.02)); border:1px solid var(--ops-line); border-left:3px solid #f59e0b; border-radius:8px; padding:8px 12px; }
  .top-perf-name { font-size:10.5px; font-weight:700; color:var(--ops-muted); letter-spacing:0.04em; text-transform:uppercase; margin-bottom:3px; }
  .top-perf-winner { font-size:14px; font-weight:700; color:var(--ops-ink); }
  .top-perf-winner a { color:inherit; text-decoration:none; }
  .top-perf-value { font-size:11.5px; color:#b45309; font-weight:700; font-variant-numeric:tabular-nums; }
  body.theme-dark .top-perf-card { background:linear-gradient(135deg, rgba(245,158,11,0.14), rgba(245,158,11,0.04)); }
  .data-meta { font-size:11px; color:var(--ops-muted); margin-top:6px; padding:6px 0 0 0; border-top:1px dashed var(--ops-line); }
  .data-meta strong { color:var(--ops-ink-soft); }
  .data-meta .sep { margin:0 8px; opacity:0.4; }
  @media print { .top-perf { display:none; } .data-meta { font-size:9px; } }
  /* Accessibility */
  *:focus-visible { outline:2px solid var(--ops-green); outline-offset:2px; border-radius:3px; }
  .year-btn:focus-visible, .cost-tab:focus-visible, .tier-pill:focus-visible { outline-offset:1px; }
  .skip-link { position:absolute; left:-1000px; top:8px; padding:6px 12px; background:var(--ops-green); color:white; border-radius:6px; font-weight:700; z-index:200; text-decoration:none; }
  .skip-link:focus { left:8px; }
  /* Help overlay */
  .help-overlay { position:fixed; inset:0; background:rgba(0,0,0,0.55); backdrop-filter:blur(2px); display:none; align-items:center; justify-content:center; z-index:300; padding:20px; }
  .help-overlay.open { display:flex; }
  .help-panel { background:var(--ops-surface); border-radius:12px; padding:24px 28px; max-width:520px; width:100%; max-height:80vh; overflow:auto; box-shadow:0 20px 40px rgba(0,0,0,0.25); }
  .help-panel h2 { margin:0 0 12px 0; font-size:18px; color:var(--ops-ink); }
  .help-panel .help-row { display:grid; grid-template-columns:1fr 110px; gap:10px; align-items:center; padding:7px 0; border-bottom:1px solid var(--ops-line); font-size:13px; color:var(--ops-ink-soft); }
  .help-panel .help-row:last-child { border-bottom:none; }
  .help-panel .help-row kbd { display:inline-block; padding:2px 8px; background:var(--ops-bg); border:1px solid var(--ops-line); border-radius:4px; font-family:monospace; font-size:11.5px; color:var(--ops-ink); font-weight:700; text-align:center; }
  .help-panel .close-btn { float:right; padding:4px 10px; border:1px solid var(--ops-line); background:var(--ops-surface); border-radius:5px; font-size:12px; cursor:pointer; color:var(--ops-ink-soft); margin-top:-8px; }
  body.theme-dark .help-panel { background:#1e293b; }
  body.theme-dark .help-panel .help-row kbd { background:#0f172a; }
  .help-fab { position:fixed; bottom:18px; right:18px; width:38px; height:38px; border-radius:50%; background:var(--ops-surface); border:1px solid var(--ops-line); cursor:pointer; font-size:16px; color:var(--ops-ink-soft); z-index:50; box-shadow:0 2px 8px rgba(0,0,0,0.10); }
  .help-fab:hover { background:rgba(45,80,22,0.06); color:var(--ops-ink); }
  @media print { .help-fab, .help-overlay { display:none !important; } }
  /* Auto-insight box */
  .insights { display:grid; grid-template-columns:1fr 1fr; gap:8px; margin:14px 0 6px 0; }
  .insight { background:linear-gradient(135deg, rgba(45,80,22,0.06), rgba(45,80,22,0.02)); border:1px solid var(--ops-line); border-left:3px solid var(--ops-green); border-radius:8px; padding:10px 14px; font-size:12.5px; color:var(--ops-ink-soft); }
  .insight strong { color:var(--ops-ink); }
  .insight .label { display:inline-block; font-size:10.5px; font-weight:700; color:var(--ops-green); letter-spacing:0.04em; text-transform:uppercase; margin-bottom:3px; }
  body.theme-dark .insight { background:linear-gradient(135deg, rgba(34,197,94,0.08), rgba(34,197,94,0.02)); }
  @media (max-width:720px) { .insights { grid-template-columns:1fr; } }
  @media print { .insights { display:none; } }
  /* Category matrix search */
  .cat-search-row { display:flex; gap:8px; align-items:center; margin:4px 0 8px 0; flex-wrap:wrap; }
  .cat-search-row label { font-size:11.5px; color:var(--ops-muted); font-weight:600; }
  .cat-search-row input { padding:5px 10px; border:1px solid var(--ops-line); background:var(--ops-surface); border-radius:6px; font-size:12px; color:var(--ops-ink); min-width:180px; }
  .cat-search-row input:focus { outline:none; border-color:var(--ops-green); box-shadow:0 0 0 3px rgba(45,80,22,0.12); }
  tr.cat-hidden { display:none; }
</style>
</head>
<body>
<a class="skip-link" href="#main-content">메인 콘텐츠로 건너뛰기</a>
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
  <button class="theme-toggle" id="theme-toggle" aria-label="다크모드 전환" title="다크/라이트 모드 (d)">🌙</button>
  <div class="ops-wrap">
    <h1>비용 — 동급 비교</h1>
    <p class="lede">기준 연도 선택 → 13 peer 비용 구조 비교. 라인 상세표는 선택 연도 컬럼 하이라이트.</p>
    <div style="background:rgba(245,158,11,0.08); border-left:3px solid #f59e0b; padding:10px 14px; margin:12px 0 6px 0; border-radius:4px; font-size:12px; line-height:1.6; color:var(--ops-ink-soft);">
      <strong>⚠ 매출원가·판관비 분류 체계 차이 안내</strong><br>
      peer별 AR 분류 관행이 달라 <strong>COGS 단독 비율</strong>·<strong>OpEx 단독 비율</strong>만으로는 동급 비교가 어렵습니다.<br>
      • DMIG·PIPG (Pure-play): 인건비·감가가 <em>판관비</em>에 분류, 매출원가는 사업부 직접 운영비만<br>
      • MDLN: 인건비·감가가 <em>매출원가</em>에 포함, 별도 판관비 공시 없음<br>
      • GOLF: 매출원가에 사업부 직접원가, 판관비에 Selling+G&amp;A<br>
      • KPIG: 그룹 G&amp;A만 공시 (매출원가 분리 없음)<br>
      <strong>해법</strong>: ④ 탭의 <strong>총 영업비용 (COGS+OpEx) / 매출</strong> 단일 지표는 분류 차이를 상쇄하며, ③ 탭의 <strong>카테고리 매트릭스는 COGS+OpEx 통합</strong>으로 인건비·감가 등 cost-type 동급 비교를 제공합니다.
    </div>
    <div class="top-perf" id="top-perf"></div>
    <div class="insights" id="insights"></div>
    <div class="data-meta">
      📅 데이터: <strong>FY2020-FY2024 연결 P&amp;L</strong>
      <span class="sep">·</span>
      COGS/OpEx: <strong>AR Note 25·26·28·29·30·31·32·34 / scope_rev 매칭</strong>
      <span class="sep">·</span>
      출처: <strong>IDX (idx.co.id)</strong>
    </div>
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
      <div class="cost-tab" data-panel="cogs">② 매출원가 라인</div>
      <div class="cost-tab" data-panel="opex">③ 판관비 + 통합 카테고리</div>
      <div class="cost-tab" data-panel="total">④ 총 영업비용 (COGS+OpEx)</div>
    </div>
  </div>
</section>

<section class="ops-section" id="main-content">
  <div class="ops-wrap">
    <div class="cost-panel active" id="panel-cmp">
      <h2 style="font-size:17px; margin:0 0 14px 0;">13-peer 비용 구조 — <span class="yr-label">FY2024</span></h2>
      <p style="font-size:12px; color:var(--ops-muted); margin:0 0 6px 0;">선택 연도 그룹 P&L 기반. 총 비용 = 매출 − 영업이익. EBITDA·순이익 마진 포함. <strong>Tier별 중위 벤치마크 행</strong> 포함 (3 tier + 전체).</p>
      <div class="tier-pills" data-target="cmp-tbody" role="group" aria-label="Tier 필터">
        <span style="font-size:11.5px; color:var(--ops-muted); font-weight:600;">Tier:</span>
        <button class="tier-pill active" data-tier="all">전체</button>
        <button class="tier-pill" data-tier="pp">🟦 Pure-play</button>
        <button class="tier-pill" data-tier="resort">🟨 Resort</button>
        <button class="tier-pill" data-tier="twn">🟩 Township</button>
      </div>
      <div class="action-bar">
        <button class="action-btn" id="cmp-copy-btn">📋 표 복사 (TSV)</button>
        <button class="action-btn" id="cmp-csv-btn">⬇ CSV 다운로드</button>
      </div>
      <div class="tbl-card scroll-x">
        <table class="ops-tbl sticky-tbl">
          <thead>
            <tr>
              <th>Peer</th>
              <th class="col-low-prio">그룹명</th>
              <th class="num sortable" data-sort="rev">매출</th>
              <th class="num sortable col-low-prio" data-sort="totalCost">총 비용</th>
              <th class="num sortable" data-sort="costRatio">총 비용 / 매출</th>
              <th class="num sortable" data-sort="opMargin">영업이익률</th>
              <th class="num sortable col-low-prio" data-sort="ebMargin">EBITDA 마진</th>
              <th class="num sortable col-low-prio" data-sort="npMargin">순이익률</th>
            </tr>
          </thead>
          <tbody id="cmp-tbody"></tbody>
        </table>
      </div>
    </div>

    <div class="cost-panel" id="panel-cogs">
      <h2 style="font-size:17px; margin:0 0 14px 0;">매출원가 동급 비교 — <span class="yr-label">FY2024</span></h2>
      <p style="font-size:12px; color:var(--ops-muted); margin:0 0 12px 0;">선택 연도 매출원가 합계 + 동일 범위 매출 대비 비율. 비율은 공시 범위에 맞는 매출 (Pure-play: 그룹 매출, MDLN: 골프+클럽 매출, Tier-3: 골프 segment 매출)로 계산해 동급 비교 가능.</p>
      <div class="tier-pills" data-target="cogs-cmp-tbody" role="group" aria-label="Tier 필터">
        <span style="font-size:11.5px; color:var(--ops-muted); font-weight:600;">Tier:</span>
        <button class="tier-pill active" data-tier="all">전체</button>
        <button class="tier-pill" data-tier="pp">🟦 Pure-play</button>
        <button class="tier-pill" data-tier="resort">🟨 Resort</button>
        <button class="tier-pill" data-tier="twn">🟩 Township</button>
      </div>
      <div class="tbl-card scroll-x" style="margin-bottom:28px;">
        <table class="ops-tbl">
          <thead>
            <tr>
              <th>Peer</th>
              <th>그룹명</th>
              <th class="num">매출원가</th>
              <th class="num">대응 매출</th>
              <th class="num">COGS / 매출</th>
              <th>공시 범위</th>
            </tr>
          </thead>
          <tbody id="cogs-cmp-tbody"></tbody>
        </table>
      </div>
      <h3 style="font-size:15px; margin:24px 0 10px 0;">peer별 매출원가 라인 상세</h3>
__COGS_SECTION__
    </div>

    <div class="cost-panel" id="panel-opex">
      <h2 style="font-size:17px; margin:0 0 14px 0;">판관비 동급 비교 — <span class="yr-label">FY2024</span></h2>
      <p style="font-size:12px; color:var(--ops-muted); margin:0 0 12px 0;">선택 연도 판관비 합계 (Selling + G&A) + 동일 범위 매출 대비 비율. 비율은 공시 범위에 맞는 매출로 계산.</p>
      <div class="tier-pills" data-target="opex-cmp-tbody" role="group" aria-label="Tier 필터">
        <span style="font-size:11.5px; color:var(--ops-muted); font-weight:600;">Tier:</span>
        <button class="tier-pill active" data-tier="all">전체</button>
        <button class="tier-pill" data-tier="pp">🟦 Pure-play</button>
        <button class="tier-pill" data-tier="resort">🟨 Resort</button>
        <button class="tier-pill" data-tier="twn">🟩 Township</button>
      </div>
      <div class="tbl-card scroll-x" style="margin-bottom:24px;">
        <table class="ops-tbl">
          <thead>
            <tr>
              <th>Peer</th>
              <th>그룹명</th>
              <th class="num">판관비</th>
              <th class="num">대응 매출</th>
              <th class="num">OpEx / 매출</th>
              <th>공시 범위</th>
            </tr>
          </thead>
          <tbody id="opex-cmp-tbody"></tbody>
        </table>
      </div>

      <h3 style="font-size:15px; margin:24px 0 10px 0;">📊 비용 구성 시각화 (COGS+OpEx) — <span class="yr-label">FY2024</span></h3>
      <p style="font-size:12px; color:var(--ops-muted); margin:0 0 12px 0;">각 peer 운영비의 카테고리별 100% 누적 막대. 호버 시 카테고리별 절대값·비중 툴팁. peer별 비용 프로필을 즉시 시각 인식 가능.</p>
      <div class="mix-bar-section" id="mix-bar-section">
        <div class="mix-legend" id="mix-legend"></div>
        <div id="mix-bar-rows"></div>
      </div>

      <h3 style="font-size:15px; margin:24px 0 6px 0;">운영비 카테고리 매트릭스 (COGS+OpEx 통합) — <span class="yr-label">FY2024</span></h3>
      <p style="font-size:12px; color:var(--ops-muted); margin:0 0 6px 0;">peer × 12 카테고리. <strong>분류 체계 차이 상쇄용</strong>: MDLN처럼 인건비·감가를 매출원가에 분류하는 peer는 COGS 라인도 카테고리화해서 합산 → DMIG/PIPG(판관비에 분류)와 같은 차원에서 비교. <strong>각 행의 최대값</strong>은 호박색 배경으로 강조. <span style="color:var(--ops-green); font-weight:600;">ⓒ = COGS+OpEx 합산, ⓞ = OpEx만</span>.</p>
      <div class="cat-search-row">
        <label for="cat-search">🔍 카테고리 필터:</label>
        <input type="search" id="cat-search" placeholder="예: 인건비, 감가, 세금…" aria-label="카테고리 검색">
        <button class="action-btn" id="cat-copy-btn">📋 매트릭스 복사 (TSV)</button>
        <button class="action-btn" id="cat-csv-btn">⬇ 매트릭스 CSV</button>
      </div>
      <div class="tbl-card scroll-x" style="margin-bottom:28px;">
        <table class="ops-tbl" id="opex-cat-tbl">
          <thead id="opex-cat-thead"></thead>
          <tbody id="opex-cat-tbody"></tbody>
        </table>
      </div>

      <h3 style="font-size:15px; margin:24px 0 10px 0;">peer별 판관비 라인 상세</h3>
__OPEX_SECTION__
    </div>

    <div class="cost-panel" id="panel-total">
      <h2 style="font-size:17px; margin:0 0 14px 0;">총 영업비용 (COGS + OpEx) 동급 비교 — <span class="yr-label">FY2024</span></h2>
      <p style="font-size:12px; color:var(--ops-muted); margin:0 0 12px 0;">매출원가와 판관비의 <strong>합계</strong>를 동일 범위 매출(scope_rev)로 나눈 비율. peer별 분류 체계 차이(인건비·감가가 COGS에 있는지 OpEx에 있는지)와 무관하게 <strong>총 영업비용 부담</strong>을 동일 차원에서 비교할 수 있습니다.</p>
      <div style="background:rgba(45,80,22,0.05); padding:8px 12px; margin:0 0 14px 0; border-radius:4px; font-size:11.5px; color:var(--ops-ink-soft);">
        <strong>해석 가이드</strong>: 비율이 낮을수록 매출 대비 영업비용 효율성이 높음.
        Pure-play(DMIG·PIPG)는 전사 기준, GOLF는 사업부 합계, MDLN/KIJA/SMDM은 골프 segment 기준 →
        모두 <em>해당 공시 범위의 매출</em>로 나누어 동일 차원 비교 성립.
        <strong>주의</strong>: KPIG는 COGS 공시 없이 그룹 G&amp;A만이므로 합산 비율 비교에서 제외.
      </div>
      <div class="tier-pills" data-target="total-cmp-tbody" role="group" aria-label="Tier 필터">
        <span style="font-size:11.5px; color:var(--ops-muted); font-weight:600;">Tier:</span>
        <button class="tier-pill active" data-tier="all">전체</button>
        <button class="tier-pill" data-tier="pp">🟦 Pure-play</button>
        <button class="tier-pill" data-tier="resort">🟨 Resort</button>
        <button class="tier-pill" data-tier="twn">🟩 Township</button>
      </div>
      <div class="action-bar">
        <button class="action-btn" id="total-copy-btn">📋 표 복사 (TSV)</button>
        <button class="action-btn" id="total-csv-btn">⬇ CSV 다운로드</button>
      </div>
      <div class="tbl-card scroll-x" style="margin-bottom:24px;">
        <table class="ops-tbl sticky-tbl">
          <thead>
            <tr>
              <th>Peer</th>
              <th class="col-low-prio">그룹명</th>
              <th class="num sortable col-low-prio" data-sort="cogs">매출원가</th>
              <th class="num sortable col-low-prio" data-sort="opex">판관비</th>
              <th class="num sortable" data-sort="tot">합계 (COGS+OpEx)</th>
              <th class="num sortable col-low-prio" data-sort="scopeRev">대응 매출</th>
              <th class="num sortable" data-sort="ratio">합계 / 매출</th>
              <th class="col-low-prio">공시 범위</th>
            </tr>
          </thead>
          <tbody id="total-cmp-tbody"></tbody>
        </table>
      </div>
    </div>
  </div>
</section>

<button class="help-fab" id="help-fab" aria-label="키보드 단축키 도움말" title="키보드 단축키 (?)">?</button>
<div class="help-overlay" id="help-overlay" role="dialog" aria-modal="true" aria-labelledby="help-title">
  <div class="help-panel">
    <button class="close-btn" id="help-close" aria-label="도움말 닫기">✕</button>
    <h2 id="help-title">⌨️ 키보드 단축키</h2>
    <div class="help-row"><span>다크/라이트 모드</span><kbd>d</kbd></div>
    <div class="help-row"><span>빠른 연도 선택 (FY20-24)</span><kbd>1</kbd>-<kbd>5</kbd></div>
    <div class="help-row"><span>연도·탭·tier 이동</span><kbd>←</kbd> <kbd>→</kbd></div>
    <div class="help-row"><span>도움말 토글</span><kbd>?</kbd> <kbd>Esc</kbd></div>
    <div style="margin-top:12px; padding-top:10px; border-top:1px dashed var(--ops-line); font-size:11.5px; color:var(--ops-muted);">
      🔗 URL hash (#year=, #tab=) 공유. ⬇ CSV/매트릭스 CSV 내보내기 지원.
    </div>
  </div>
</div>

<footer class="ops-foot">
  <div class="ops-wrap">
    <p>비용 구조 비율: 연결 P&L FY2020-FY2024. 라인 상세: AR Note 23·24·26·28·29·30·31·32·34. 단위 IDR.</p>
  </div>
</footer>

<script src="operations.js?v=20260512c3" defer></script>
<script>
const PEER_DATA = __PEER_DATA__;
const PEER_ORDER = __PEER_ORDER__;
const CAT_ORDER = __CAT_ORDER__;

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

// Category color palette — semantic + accessible
const CAT_COLORS = {
  '인건비':      '#2563eb',  // blue (people)
  '감가상각':    '#7c3aed',  // purple (capital)
  '시설관리':    '#0891b2',  // cyan (maintenance)
  '세금·법률':   '#dc2626',  // red (compliance)
  '수도광열':    '#f59e0b',  // amber (utility)
  '광고·마케팅': '#ec4899',  // pink (sales)
  '보험':        '#84cc16',  // lime
  '통신·IT':     '#06b6d4',  // teal
  '사무·소모품': '#f97316',  // orange
  '청소·보안':   '#10b981',  // emerald (services)
  '운송·출장':   '#8b5cf6',  // violet
  '기타':        '#9ca3af',  // gray
};

function renderMixBars(year, peers, mergedByPeer){
  const legendEl = document.getElementById('mix-legend');
  const rowsEl = document.getElementById('mix-bar-rows');
  if (!legendEl || !rowsEl) return;
  // Legend (only categories that appear in at least one peer this year)
  const usedCats = new Set();
  peers.forEach(t => {
    Object.keys(mergedByPeer[t] || {}).forEach(c => {
      if ((mergedByPeer[t][c] || 0) > 0) usedCats.add(c);
    });
  });
  const orderedUsed = CAT_ORDER.filter(c => usedCats.has(c));
  legendEl.innerHTML = orderedUsed.map(c =>
    `<span class="mix-legend-item"><span class="mix-legend-swatch" style="background:${CAT_COLORS[c]||'#888'};"></span>${c}</span>`
  ).join('');
  // Rows: peer per row, stacked bar segments by category share
  rowsEl.innerHTML = peers.map(t => {
    const d = PEER_DATA[t];
    const cats = mergedByPeer[t] || {};
    const total = Object.values(cats).reduce((s,v) => s+(v||0), 0);
    if (total === 0) return '';
    // Build segments in CAT_ORDER, only positive
    const segs = orderedUsed.map(c => {
      const v = cats[c] || 0;
      if (v <= 0) return null;
      const pct = (v/total*100);
      const valStr = (v >= 1e12) ? (v/1e12).toFixed(1)+'T' : (v >= 1e9) ? (v/1e9).toFixed(1)+'B' : (v/1e6).toFixed(0)+'M';
      const showText = pct >= 6;  // hide label in tiny slices
      return `<div class="mix-bar-seg" style="width:${pct.toFixed(2)}%; background:${CAT_COLORS[c]||'#888'};" title="${c}: ${valStr} (${pct.toFixed(1)}%)">${showText ? c.replace(/·.+/,'')+' '+pct.toFixed(0)+'%' : ''}</div>`;
    }).filter(Boolean).join('');
    const totalStr = (total >= 1e12) ? (total/1e12).toFixed(1)+'T' : (total >= 1e9) ? (total/1e9).toFixed(0)+'B' : (total/1e6).toFixed(0)+'M';
    return `<div class="mix-bar-row">
      <div class="mix-bar-label"><a href="clubs/${t.toLowerCase()}.html" style="color:inherit; text-decoration:none;">${t}</a> <span class="peer-tag peer-tag-${d.tier}" style="font-size:9px; padding:1px 5px;">${d.tier_label.replace(/^[^ ]+ /,'')}</span></div>
      <div class="mix-bar-track">${segs}</div>
      <div class="mix-bar-total">${totalStr}</div>
    </div>`;
  }).join('');
}

// Compute median of numeric array (null-aware)
function median(xs){
  const v = xs.filter(x => x !== null && x !== undefined).sort((a,b) => a-b);
  if (!v.length) return null;
  return v.length % 2 === 1 ? v[Math.floor(v.length/2)] : (v[v.length/2-1] + v[v.length/2]) / 2;
}
const TIER_LABEL = { pp:'🟦 Pure-play 중위', resort:'🟨 Resort 중위', twn:'🟩 Township 중위' };

let cmpSortState = { key: null, dir: 'desc' };
let totalSortState = { key: null, dir: 'desc' };

function renderTopPerf(year) {
  const fmtPct = v => (v === null || v === undefined) ? '—' : `${v >= 0 ? '+' : ''}${v.toFixed(1)}%`;
  function bestLow(metricFn, fmt) {
    let best = null, bestV = Infinity;
    PEER_ORDER.forEach(t => {
      const v = metricFn(t);
      if (v !== null && v !== undefined && v < bestV) { bestV = v; best = t; }
    });
    return best ? { ticker: best, display: fmt(bestV) } : null;
  }
  function bestHigh(metricFn, fmt) {
    let best = null, bestV = -Infinity;
    PEER_ORDER.forEach(t => {
      const v = metricFn(t);
      if (v !== null && v !== undefined && v > bestV) { bestV = v; best = t; }
    });
    return best ? { ticker: best, display: fmt(bestV) } : null;
  }
  // Total cost ratio = (rev - op) / rev
  const totalCostRatio = (t) => {
    const y = PEER_DATA[t].yearly[year] || {};
    return (y.rev && y.op !== null && y.op !== undefined) ? ((y.rev - y.op)/y.rev*100) : null;
  };
  const opMarginFn = (t) => {
    const y = PEER_DATA[t].yearly[year] || {};
    return (y.rev && y.op !== null && y.op !== undefined) ? (y.op/y.rev*100) : null;
  };
  const ebMarginFn = (t) => {
    const y = PEER_DATA[t].yearly[year] || {};
    return (y.rev && y.ebitda !== null && y.ebitda !== undefined) ? (y.ebitda/y.rev*100) : null;
  };
  const totRatioFn = (t) => {
    const d = PEER_DATA[t];
    const sr = d.scope_rev[year]; const tot = d.total_opcost[year];
    return (sr && tot) ? (tot/sr*100) : null;
  };
  const perfs = [
    { label: '🏆 최저 총비용률', data: bestLow(totalCostRatio, fmtPct) },
    { label: '🏆 최고 영업이익률', data: bestHigh(opMarginFn, fmtPct) },
    { label: '🏆 최고 EBITDA 마진', data: bestHigh(ebMarginFn, fmtPct) },
    { label: '🏆 최저 (COGS+OpEx)/매출', data: bestLow(totRatioFn, fmtPct) },
  ];
  const root = document.getElementById('top-perf');
  if (!root) return;
  root.innerHTML = perfs.filter(p => p.data).map(p => `<div class="top-perf-card">
    <div class="top-perf-name">${p.label}</div>
    <div class="top-perf-winner"><a href="clubs/${p.data.ticker.toLowerCase()}.html">${p.data.ticker}</a></div>
    <div class="top-perf-value">${p.data.display}</div>
  </div>`).join('');
}

function renderInsights(year) {
  const root = document.getElementById('insights');
  if (!root) return;
  function median(arr) {
    const v = arr.filter(x => x !== null && x !== undefined && !isNaN(x)).sort((a,b)=>a-b);
    return v.length ? (v.length%2 ? v[Math.floor(v.length/2)] : (v[v.length/2-1]+v[v.length/2])/2) : null;
  }
  // Tier median op margin and cost ratio
  const opMarginFor = (t) => {
    const y = PEER_DATA[t].yearly[year] || {};
    return (y.rev && y.op !== null && y.op !== undefined) ? (y.op/y.rev*100) : null;
  };
  const ppOM = median(PEER_ORDER.filter(t => PEER_DATA[t].tier === 'pp').map(opMarginFor));
  const twnOM = median(PEER_ORDER.filter(t => PEER_DATA[t].tier === 'twn').map(opMarginFor));
  // (COGS+OpEx)/scope_rev coverage
  let totWithCogsOpex = 0;
  PEER_ORDER.forEach(t => { if (PEER_DATA[t].total_opcost[year]) totWithCogsOpex++; });
  const insights = [];
  if (ppOM !== null && twnOM !== null) {
    const diff = ppOM - twnOM;
    insights.push({
      label: '💡 영업이익률 격차',
      text: `<strong>Pure-play 중위 ${ppOM.toFixed(1)}%</strong> vs Township 중위 ${twnOM.toFixed(1)}% — ${Math.abs(diff).toFixed(1)}%p ${diff >= 0 ? '높음' : '낮음'}.`
    });
  }
  insights.push({
    label: '📊 COGS+OpEx 공시',
    text: `<strong>${totWithCogsOpex} / 13 peer</strong>가 매출원가 또는 판관비 공시 (Tab ④ 통합 비교 가능 peer 수).`
  });
  root.innerHTML = insights.map(i => `<div class="insight"><div class="label">${i.label}</div>${i.text}</div>`).join('');
}

function render(year){
  document.querySelectorAll('.yr-label').forEach(el => el.textContent = 'FY' + year);
  renderTopPerf(year);
  renderInsights(year);

  // === Tab 1: 비용 구조 % (group P&L) ===
  const cmpData = [];
  PEER_ORDER.forEach(t => {
    const d = PEER_DATA[t];
    const y = d.yearly[year] || {};
    const rev = y.rev; const op = y.op; const np = y.np; const ebitda = y.ebitda;
    const totalCost = (rev !== null && rev !== undefined && op !== null && op !== undefined) ? (rev - op) : null;
    const costRatio = (rev && totalCost !== null) ? (totalCost/rev*100) : null;
    const opMargin = (rev && op !== null && op !== undefined) ? (op/rev*100) : null;
    const ebMargin = (rev && ebitda !== null && ebitda !== undefined) ? (ebitda/rev*100) : null;
    const npMargin = (rev && np !== null && np !== undefined) ? (np/rev*100) : null;
    cmpData.push({ t, d, tier:d.tier, name:d.name, rev, totalCost, costRatio, opMargin, ebMargin, npMargin });
  });
  // Sort cmpData if requested
  const cmpSorted = cmpData.slice();
  if (cmpSortState.key) {
    cmpSorted.sort((a,b) => {
      const va = a[cmpSortState.key]; const vb = b[cmpSortState.key];
      if (va === null || va === undefined) return 1;
      if (vb === null || vb === undefined) return -1;
      return cmpSortState.dir === 'desc' ? (vb - va) : (va - vb);
    });
  }
  const rows = cmpSorted.map(r => {
    const { t, d, rev, totalCost, costRatio, opMargin, ebMargin, npMargin } = r;
    return `<tr data-tier="${d.tier}">
      <td class="peer"><a href="clubs/${t.toLowerCase()}.html" style="color:var(--ops-ink); font-weight:700; text-decoration:none;">${t}</a><span class="peer-tag peer-tag-${d.tier}">${d.tier_label}</span></td>
      <td class="col-low-prio">${d.name.slice(0,24)}</td>
      <td class="num">${fmtBn(rev)}</td>
      <td class="num col-low-prio">${fmtBn(totalCost)}</td>
      <td class="num">${fmtPct(costRatio)}</td>
      <td class="num"><strong>${fmtPct(opMargin)}</strong></td>
      <td class="num col-low-prio">${fmtPct(ebMargin)}</td>
      <td class="num col-low-prio">${fmtPct(npMargin)}</td>
    </tr>`;
  });
  // Tier median benchmark rows + overall
  const benchRows = [];
  ['pp','resort','twn'].forEach(tk => {
    const tdata = cmpData.filter(r => r.tier === tk);
    if (!tdata.length) return;
    const med = (key) => median(tdata.map(r => r[key]));
    benchRows.push(`<tr class="bench-row tier-${tk}"><td>${TIER_LABEL[tk]}</td><td class="col-low-prio">N=${tdata.length}</td><td class="num">${fmtBn(med('rev'))}</td><td class="num col-low-prio">${fmtBn(med('totalCost'))}</td><td class="num">${fmtPct(med('costRatio'))}</td><td class="num"><strong>${fmtPct(med('opMargin'))}</strong></td><td class="num col-low-prio">${fmtPct(med('ebMargin'))}</td><td class="num col-low-prio">${fmtPct(med('npMargin'))}</td></tr>`);
  });
  const medAll = (key) => median(cmpData.map(r => r[key]));
  benchRows.push(`<tr class="bench-row overall"><td>📊 전체 중위</td><td class="col-low-prio">N=${cmpData.length}</td><td class="num">${fmtBn(medAll('rev'))}</td><td class="num col-low-prio">${fmtBn(medAll('totalCost'))}</td><td class="num">${fmtPct(medAll('costRatio'))}</td><td class="num"><strong>${fmtPct(medAll('opMargin'))}</strong></td><td class="num col-low-prio">${fmtPct(medAll('ebMargin'))}</td><td class="num col-low-prio">${fmtPct(medAll('npMargin'))}</td></tr>`);
  document.getElementById('cmp-tbody').innerHTML = rows.join('') + benchRows.join('');
  window._cmpData = cmpData;
  // Update Tab ① sort header indicators
  document.querySelectorAll('#panel-cmp .sortable').forEach(th => {
    th.classList.remove('asc','desc');
    if (th.dataset.sort === cmpSortState.key) th.classList.add(cmpSortState.dir);
  });

  // === Tab 2: 매출원가 동급 비교 (top) ===
  // Ratio uses scope_rev (matches the actual coverage of the COGS note) for honest comparison
  const cogsRows = PEER_ORDER.map(t => {
    const d = PEER_DATA[t];
    const scopeRev = d.scope_rev[year];
    const cogs = d.cogs_total[year];
    const ratio = (scopeRev && cogs) ? (cogs/scopeRev*100) : null;
    return `<tr data-tier="${d.tier}">
      <td class="peer"><a href="clubs/${t.toLowerCase()}.html" style="color:var(--ops-ink); font-weight:700; text-decoration:none;">${t}</a><span class="peer-tag peer-tag-${d.tier}">${d.tier_label}</span></td>
      <td>${d.name.slice(0,24)}</td>
      <td class="num"><strong>${fmtBn(cogs)}</strong></td>
      <td class="num">${fmtBn(scopeRev)}</td>
      <td class="num">${fmtPct(ratio)}</td>
      <td style="font-size:11.5px; color:var(--ops-muted);">${d.cogs_cov}</td>
    </tr>`;
  });
  document.getElementById('cogs-cmp-tbody').innerHTML = cogsRows.join('');

  // === Tab 3: 판관비 동급 비교 (top) ===
  const opexRows = PEER_ORDER.map(t => {
    const d = PEER_DATA[t];
    const scopeRev = d.scope_rev[year];
    const opex = d.opex_total[year];
    const ratio = (scopeRev && opex) ? (opex/scopeRev*100) : null;
    return `<tr data-tier="${d.tier}">
      <td class="peer"><a href="clubs/${t.toLowerCase()}.html" style="color:var(--ops-ink); font-weight:700; text-decoration:none;">${t}</a><span class="peer-tag peer-tag-${d.tier}">${d.tier_label}</span></td>
      <td>${d.name.slice(0,24)}</td>
      <td class="num"><strong>${fmtBn(opex)}</strong></td>
      <td class="num">${fmtBn(scopeRev)}</td>
      <td class="num">${fmtPct(ratio)}</td>
      <td style="font-size:11.5px; color:var(--ops-muted);">${d.opex_cov}</td>
    </tr>`;
  });
  document.getElementById('opex-cmp-tbody').innerHTML = opexRows.join('');

  // === Tab 3: 운영비 카테고리 매트릭스 (peer × category, COGS+OpEx 통합) ===
  // Combine cogs_by_cat (MDLN only) + opex_by_cat for each peer; include peers with either
  const opexCatPeers = PEER_ORDER.filter(t => {
    const o = PEER_DATA[t].opex_by_cat[year] || {};
    const c = PEER_DATA[t].cogs_by_cat[year] || {};
    return Object.keys(o).length > 0 || Object.keys(c).length > 0;
  });
  // Build merged category map per peer
  const mergedByPeer = {};   // {peer: {cat: sum}}
  const sourceByPeer = {};   // {peer: 'C+O' | 'O' | 'C'} (for header annotation)
  opexCatPeers.forEach(t => {
    const o = PEER_DATA[t].opex_by_cat[year] || {};
    const c = PEER_DATA[t].cogs_by_cat[year] || {};
    const m = {};
    Object.keys(o).forEach(k => { m[k] = (m[k]||0) + o[k]; });
    Object.keys(c).forEach(k => { m[k] = (m[k]||0) + c[k]; });
    mergedByPeer[t] = m;
    const hasC = Object.keys(c).length > 0;
    const hasO = Object.keys(o).length > 0;
    sourceByPeer[t] = (hasC && hasO) ? 'C+O' : (hasC ? 'C' : 'O');
  });
  const srcTag = s => s === 'C+O' ? '<span style="font-size:9px; color:var(--ops-green); font-weight:700;">ⓒ</span>' : '<span style="font-size:9px; color:var(--ops-muted);">ⓞ</span>';
  const theadCells = ['<th>카테고리</th>'].concat(opexCatPeers.map((t, i) => {
    const d = PEER_DATA[t];
    return `<th class="num" data-col="${i}"><a href="clubs/${t.toLowerCase()}.html" style="color:inherit; text-decoration:none;">${t}</a> ${srcTag(sourceByPeer[t])} <span class="peer-tag peer-tag-${d.tier}" style="font-size:9px; padding:1px 5px;">${d.tier_label.replace(/^[^ ]+ /,'')}</span></th>`;
  })).join('');
  document.getElementById('opex-cat-thead').innerHTML = '<tr>' + theadCells + '</tr>';
  // Body rows — use scope_rev for ratio (same as ② ③ tabs, honest comparison)
  // Track max value per row for highlighting
  const bodyRows = CAT_ORDER.map(cat => {
    // Find max value in this row across peers
    let maxVal = 0;
    opexCatPeers.forEach(t => { const v = (mergedByPeer[t] || {})[cat] || 0; if (v > maxVal) maxVal = v; });
    const cells = opexCatPeers.map((t, i) => {
      const v = (mergedByPeer[t] || {})[cat];
      const scopeRev = PEER_DATA[t].scope_rev[year];
      const pct = (v && scopeRev) ? (v/scopeRev*100) : null;
      const pctTxt = pct !== null ? `<br><span style="color:var(--ops-muted); font-size:10.5px;">${pct.toFixed(2)}%</span>` : '';
      const isMax = (v && v === maxVal && maxVal > 0) ? ' row-max' : '';
      return `<td class="num${isMax}" data-col="${i}">${fmtBn(v)}${pctTxt}</td>`;
    }).join('');
    return `<tr><td><strong>${cat}</strong></td>${cells}</tr>`;
  });
  // Stash for CSV export
  window._matrixCtx = { cats: CAT_ORDER, peers: opexCatPeers, merged: mergedByPeer, year };
  // Total row — COGS + OpEx grand total (total_opcost)
  const totalCells = opexCatPeers.map((t, i) => {
    const tot = PEER_DATA[t].total_opcost[year];
    const scopeRev = PEER_DATA[t].scope_rev[year];
    const pct = (tot && scopeRev) ? (tot/scopeRev*100) : null;
    const pctTxt = pct !== null ? `<br><span style="color:var(--ops-muted); font-size:10.5px;">${pct.toFixed(2)}%</span>` : '';
    return `<td class="num" data-col="${i}"><strong>${fmtBn(tot)}</strong>${pctTxt}</td>`;
  }).join('');
  bodyRows.push(`<tr style="background:rgba(45,80,22,0.06); font-weight:700;"><td>합계 (COGS+OpEx)</td>${totalCells}</tr>`);
  document.getElementById('opex-cat-tbody').innerHTML = bodyRows.join('');

  // === Tab 3: 비용 구성 시각화 (stacked horizontal bar) ===
  renderMixBars(year, opexCatPeers, mergedByPeer);

  // === Tab 4: 총 영업비용 (COGS+OpEx) 동급 비교 ===
  const totalData = [];
  PEER_ORDER.forEach(t => {
    const d = PEER_DATA[t];
    const scopeRev = d.scope_rev[year];
    const cogs = d.cogs_total[year];
    const opex = d.opex_total[year];
    const tot = d.total_opcost[year];
    const ratio = (scopeRev && tot) ? (tot/scopeRev*100) : null;
    const cov = (d.cogs_cov !== '—' && d.opex_cov !== '—') ? `${d.cogs_cov} / ${d.opex_cov}` : (d.cogs_cov !== '—' ? d.cogs_cov : d.opex_cov);
    totalData.push({ t, d, tier:d.tier, name:d.name, cogs, opex, tot, scopeRev, ratio, cov });
  });
  // Sort if requested
  const totalSorted = totalData.slice();
  if (totalSortState.key) {
    totalSorted.sort((a,b) => {
      const va = a[totalSortState.key]; const vb = b[totalSortState.key];
      if (va === null || va === undefined) return 1;
      if (vb === null || vb === undefined) return -1;
      return totalSortState.dir === 'desc' ? (vb - va) : (va - vb);
    });
  }
  const totalRows = totalSorted.map(r => {
    const { t, d, cogs, opex, tot, scopeRev, ratio, cov } = r;
    return `<tr data-tier="${d.tier}">
      <td class="peer"><a href="clubs/${t.toLowerCase()}.html" style="color:var(--ops-ink); font-weight:700; text-decoration:none;">${t}</a><span class="peer-tag peer-tag-${d.tier}">${d.tier_label}</span></td>
      <td class="col-low-prio">${d.name.slice(0,24)}</td>
      <td class="num col-low-prio">${fmtBn(cogs)}</td>
      <td class="num col-low-prio">${fmtBn(opex)}</td>
      <td class="num"><strong>${fmtBn(tot)}</strong></td>
      <td class="num col-low-prio">${fmtBn(scopeRev)}</td>
      <td class="num"><strong>${fmtPct(ratio)}</strong></td>
      <td class="col-low-prio" style="font-size:11px; color:var(--ops-muted);">${cov}</td>
    </tr>`;
  });
  // Tier median benchmark rows for Tab ④ (only peers with data)
  const totalBenchRows = [];
  ['pp','resort','twn'].forEach(tk => {
    const tdata = totalData.filter(r => r.tier === tk && r.tot);
    if (!tdata.length) return;
    const med = key => median(tdata.map(r => r[key]));
    totalBenchRows.push(`<tr class="bench-row tier-${tk}"><td>${TIER_LABEL[tk]}</td><td class="col-low-prio">N=${tdata.length}</td><td class="num col-low-prio">${fmtBn(med('cogs'))}</td><td class="num col-low-prio">${fmtBn(med('opex'))}</td><td class="num"><strong>${fmtBn(med('tot'))}</strong></td><td class="num col-low-prio">${fmtBn(med('scopeRev'))}</td><td class="num"><strong>${fmtPct(med('ratio'))}</strong></td><td class="col-low-prio">—</td></tr>`);
  });
  const totalAvail = totalData.filter(r => r.tot);
  if (totalAvail.length) {
    const medAll = key => median(totalAvail.map(r => r[key]));
    totalBenchRows.push(`<tr class="bench-row overall"><td>📊 전체 중위</td><td class="col-low-prio">N=${totalAvail.length}</td><td class="num col-low-prio">${fmtBn(medAll('cogs'))}</td><td class="num col-low-prio">${fmtBn(medAll('opex'))}</td><td class="num"><strong>${fmtBn(medAll('tot'))}</strong></td><td class="num col-low-prio">${fmtBn(medAll('scopeRev'))}</td><td class="num"><strong>${fmtPct(medAll('ratio'))}</strong></td><td class="col-low-prio">—</td></tr>`);
  }
  document.getElementById('total-cmp-tbody').innerHTML = totalRows.join('') + totalBenchRows.join('');
  window._totalData = totalData;
  // Update Tab ④ sort header indicators
  document.querySelectorAll('#panel-total .sortable').forEach(th => {
    th.classList.remove('asc','desc');
    if (th.dataset.sort === totalSortState.key) th.classList.add(totalSortState.dir);
  });

  // Highlight selected year columns in line tables
  document.querySelectorAll('.yr-hl').forEach(el => el.classList.remove('yr-hl'));
  document.querySelectorAll('.yr-' + year).forEach(el => el.classList.add('yr-hl'));
  // Re-apply tier filters to all pill groups (year change rebuilt the tbodies)
  if (typeof applyTierFiltersFromUI === 'function') applyTierFiltersFromUI();
}

let currentYear = '2024';

// Build TSV/CSV exporter for cmp/total tables
function buildExport(which, sep) {
  const esc = v => {
    if (v === null || v === undefined) return '';
    const s = String(v);
    if (sep === ',' && (s.includes(',') || s.includes('"') || s.includes('\n'))) return '"' + s.replace(/"/g,'""') + '"';
    return s;
  };
  const num = v => (v === null || v === undefined) ? '' : v;
  const pct = v => (v === null || v === undefined) ? '' : v.toFixed(2);
  let headers, rowsFn;
  if (which === 'cmp') {
    headers = ['Peer','그룹명','Tier','매출(IDR)','총비용(IDR)','총비용/매출(%)','영업이익률(%)','EBITDA마진(%)','순이익률(%)'];
    rowsFn = () => (window._cmpData || []).map(r => [esc(r.t), esc(r.name), esc(r.tier), num(r.rev), num(r.totalCost), pct(r.costRatio), pct(r.opMargin), pct(r.ebMargin), pct(r.npMargin)]);
  } else {
    headers = ['Peer','그룹명','Tier','매출원가(IDR)','판관비(IDR)','합계COGS+OpEx(IDR)','대응매출(IDR)','합계/매출(%)','공시범위'];
    rowsFn = () => (window._totalData || []).map(r => [esc(r.t), esc(r.name), esc(r.tier), num(r.cogs), num(r.opex), num(r.tot), num(r.scopeRev), pct(r.ratio), esc(r.cov)]);
  }
  const lines = [headers.map(esc).join(sep)];
  rowsFn().forEach(row => lines.push(row.join(sep)));
  return lines.join('\n');
}
function flashSuccess(btn, label){
  const orig = btn.textContent;
  btn.textContent = label;
  btn.classList.add('success');
  setTimeout(() => { btn.textContent = orig; btn.classList.remove('success'); }, 1500);
}
function wireExport(copyId, csvId, which, csvName) {
  const cb = document.getElementById(copyId);
  if (cb) cb.addEventListener('click', async (e) => {
    const tsv = buildExport(which, '\t');
    try { await navigator.clipboard.writeText(tsv); }
    catch (err) { const ta = document.createElement('textarea'); ta.value = tsv; document.body.appendChild(ta); ta.select(); document.execCommand('copy'); document.body.removeChild(ta); }
    flashSuccess(e.currentTarget, '✓ 복사됨');
  });
  const db = document.getElementById(csvId);
  if (db) db.addEventListener('click', (e) => {
    const csv = '﻿' + buildExport(which, ',');
    const blob = new Blob([csv], { type:'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url; a.download = `${csvName}_FY${currentYear}.csv`;
    document.body.appendChild(a); a.click(); document.body.removeChild(a); URL.revokeObjectURL(url);
    flashSuccess(e.currentTarget, '✓ 다운로드');
  });
}

(function(){
  document.querySelectorAll('.year-btn').forEach(b => {
    b.addEventListener('click', () => {
      document.querySelectorAll('.year-btn').forEach(x => x.classList.remove('active'));
      b.classList.add('active');
      currentYear = b.dataset.year;
      render(currentYear);
    });
  });
  document.querySelectorAll('.cost-tab').forEach(t => t.addEventListener('click', () => {
    document.querySelectorAll('.cost-tab').forEach(x => x.classList.remove('active'));
    document.querySelectorAll('.cost-panel').forEach(p => p.classList.remove('active'));
    t.classList.add('active');
    document.getElementById('panel-' + t.dataset.panel).classList.add('active');
  }));
  wireExport('cmp-copy-btn', 'cmp-csv-btn', 'cmp', 'cost-structure');
  wireExport('total-copy-btn', 'total-csv-btn', 'total', 'cost-total-cogs-opex');
  // Matrix CSV export
  function buildMatrixExport(sep) {
    const ctx = window._matrixCtx; if (!ctx) return '';
    const esc = v => {
      if (v === null || v === undefined) return '';
      const s = String(v);
      if (sep === ',' && (s.includes(',') || s.includes('"') || s.includes('\n'))) return '"' + s.replace(/"/g,'""') + '"';
      return s;
    };
    const headers = ['카테고리'].concat(ctx.peers);
    const lines = [headers.map(esc).join(sep)];
    ctx.cats.forEach(cat => {
      const row = [esc(cat)];
      ctx.peers.forEach(t => {
        const v = (ctx.merged[t] || {})[cat];
        row.push(v === undefined || v === null ? '' : v);
      });
      lines.push(row.join(sep));
    });
    return lines.join('\n');
  }
  const catCopyBtn = document.getElementById('cat-copy-btn');
  if (catCopyBtn) catCopyBtn.addEventListener('click', async (e) => {
    const tsv = buildMatrixExport('\t');
    try { await navigator.clipboard.writeText(tsv); }
    catch (err) { const ta = document.createElement('textarea'); ta.value = tsv; document.body.appendChild(ta); ta.select(); document.execCommand('copy'); document.body.removeChild(ta); }
    flashSuccess(e.currentTarget, '✓ 복사됨');
  });
  const catCsvBtn = document.getElementById('cat-csv-btn');
  if (catCsvBtn) catCsvBtn.addEventListener('click', (e) => {
    const csv = '﻿' + buildMatrixExport(',');
    const blob = new Blob([csv], { type:'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url; a.download = `cost-category-matrix_FY${currentYear}.csv`;
    document.body.appendChild(a); a.click(); document.body.removeChild(a); URL.revokeObjectURL(url);
    flashSuccess(e.currentTarget, '✓ 다운로드');
  });
  // Tier filter pills — each pill group has data-target pointing to a tbody
  function applyTierToTbody(targetId, tier) {
    const tbody = document.getElementById(targetId);
    if (!tbody) return;
    tbody.querySelectorAll('tr').forEach(row => {
      const rowTier = row.dataset.tier;
      let show = false;
      if (tier === 'all') show = true;
      else if (rowTier === tier) show = true;
      else if (row.classList.contains('bench-row')) {
        show = row.classList.contains('tier-' + tier);
      }
      row.classList.toggle('tier-hidden', !show);
    });
  }
  // Expose for render() to call after rebuilding tbodies
  window.applyTierFiltersFromUI = function() {
    document.querySelectorAll('.tier-pills').forEach(group => {
      const active = group.querySelector('.tier-pill.active');
      const tier = active ? active.dataset.tier : 'all';
      applyTierToTbody(group.dataset.target, tier);
    });
  };
  document.querySelectorAll('.tier-pills').forEach(group => {
    const targetId = group.dataset.target;
    group.querySelectorAll('.tier-pill').forEach(pill => {
      pill.addEventListener('click', () => {
        group.querySelectorAll('.tier-pill').forEach(x => x.classList.remove('active'));
        pill.classList.add('active');
        applyTierToTbody(targetId, pill.dataset.tier);
      });
    });
  });
  // Dark mode + system pref auto-follow
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
  // Help overlay
  const helpOverlay = document.getElementById('help-overlay');
  const helpClose = document.getElementById('help-close');
  const helpFab = document.getElementById('help-fab');
  function toggleHelp(show) {
    if (show === undefined) show = !helpOverlay.classList.contains('open');
    helpOverlay.classList.toggle('open', show);
  }
  if (helpClose) helpClose.addEventListener('click', () => toggleHelp(false));
  if (helpFab) helpFab.addEventListener('click', () => toggleHelp());
  if (helpOverlay) helpOverlay.addEventListener('click', (e) => { if (e.target === helpOverlay) toggleHelp(false); });
  document.addEventListener('keydown', (e) => {
    if (helpOverlay.classList.contains('open') && e.key === 'Escape') { e.preventDefault(); toggleHelp(false); return; }
    if (e.target.matches('input,textarea,select')) return;
    if (e.key === 'd') themeBtn.click();
    else if (e.key === '?') { e.preventDefault(); toggleHelp(); }
    else if (/^[1-5]$/.test(e.key)) {
      const yr = String(2019 + parseInt(e.key));
      const btn = document.querySelector(`.year-btn[data-year="${yr}"]`);
      if (btn) btn.click();
    }
  });
  // Keyboard arrow nav
  function wireArrowNav(selector) {
    const items = Array.from(document.querySelectorAll(selector));
    items.forEach((el, i) => {
      el.setAttribute('tabindex', '0');
      el.addEventListener('keydown', (e) => {
        if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') {
          e.preventDefault();
          const next = e.key === 'ArrowRight' ? (i + 1) % items.length : (i - 1 + items.length) % items.length;
          items[next].focus();
          items[next].click();
        }
      });
    });
  }
  wireArrowNav('.year-btn');
  wireArrowNav('.cost-tab');
  // Each tier-pill group separately
  document.querySelectorAll('.tier-pills').forEach(group => {
    const pills = Array.from(group.querySelectorAll('.tier-pill'));
    pills.forEach((el, i) => {
      el.setAttribute('tabindex', '0');
      el.addEventListener('keydown', (e) => {
        if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') {
          e.preventDefault();
          const next = e.key === 'ArrowRight' ? (i + 1) % pills.length : (i - 1 + pills.length) % pills.length;
          pills[next].focus();
          pills[next].click();
        }
      });
    });
  });
  // Category search filter (matrix body rows)
  const catSearch = document.getElementById('cat-search');
  if (catSearch) {
    catSearch.addEventListener('input', () => {
      const q = catSearch.value.trim().toLowerCase();
      document.querySelectorAll('#opex-cat-tbody tr').forEach(row => {
        if (!q) { row.classList.remove('cat-hidden'); return; }
        const label = row.querySelector('td:first-child')?.textContent?.toLowerCase() || '';
        row.classList.toggle('cat-hidden', !label.includes(q));
      });
    });
  }
  // localStorage state: year + active tab
  function saveCostState() {
    const tab = document.querySelector('.cost-tab.active');
    try {
      localStorage.setItem('cost-state', JSON.stringify({
        year: currentYear,
        tab: tab ? tab.dataset.panel : 'cmp',
      }));
    } catch (e) {}
  }
  function loadCostState() {
    try {
      const s = JSON.parse(localStorage.getItem('cost-state') || 'null');
      if (!s) return;
      if (s.year && ['2020','2021','2022','2023','2024'].includes(s.year)) {
        currentYear = s.year;
        document.querySelectorAll('.year-btn').forEach(b => b.classList.toggle('active', b.dataset.year === s.year));
      }
      if (s.tab) {
        document.querySelectorAll('.cost-tab').forEach(x => x.classList.toggle('active', x.dataset.panel === s.tab));
        document.querySelectorAll('.cost-panel').forEach(p => p.classList.toggle('active', p.id === 'panel-' + s.tab));
      }
    } catch (e) {}
  }
  loadCostState();
  // URL hash overrides (shareable links)
  function readCostHash() {
    const h = (location.hash || '').replace(/^#/, '');
    if (!h) return null;
    const p = new URLSearchParams(h);
    return { year: p.get('year'), tab: p.get('tab') };
  }
  function syncCostHash() {
    const parts = [];
    if (currentYear && currentYear !== '2024') parts.push('year=' + currentYear);
    const active = document.querySelector('.cost-tab.active');
    const tabKey = active ? active.dataset.panel : 'cmp';
    if (tabKey && tabKey !== 'cmp') parts.push('tab=' + tabKey);
    const h = parts.join('&');
    history.replaceState(null, '', h ? '#' + h : location.pathname + location.search);
  }
  const fromHash = readCostHash();
  if (fromHash) {
    if (fromHash.year && ['2020','2021','2022','2023','2024'].includes(fromHash.year)) {
      currentYear = fromHash.year;
      document.querySelectorAll('.year-btn').forEach(b => b.classList.toggle('active', b.dataset.year === currentYear));
    }
    if (fromHash.tab && ['cmp','cogs','opex','total'].includes(fromHash.tab)) {
      document.querySelectorAll('.cost-tab').forEach(x => x.classList.toggle('active', x.dataset.panel === fromHash.tab));
      document.querySelectorAll('.cost-panel').forEach(p => p.classList.toggle('active', p.id === 'panel-' + fromHash.tab));
    }
  }
  document.querySelectorAll('.year-btn, .cost-tab').forEach(el => {
    el.addEventListener('click', () => setTimeout(() => { saveCostState(); syncCostHash(); }, 0));
  });
  // Sortable headers — Tab ① and Tab ④
  document.querySelectorAll('#panel-cmp .sortable').forEach(th => {
    th.addEventListener('click', () => {
      const k = th.dataset.sort;
      if (cmpSortState.key === k) cmpSortState.dir = (cmpSortState.dir === 'desc') ? 'asc' : 'desc';
      else { cmpSortState.key = k; cmpSortState.dir = 'desc'; }
      render(currentYear);
    });
  });
  // Category matrix column hover (event delegation on thead since matrix is re-rendered)
  const catTbl = document.getElementById('opex-cat-tbl');
  if (catTbl) {
    catTbl.addEventListener('mouseover', (e) => {
      const th = e.target.closest('thead th[data-col]');
      if (!th) return;
      const col = th.dataset.col;
      catTbl.querySelectorAll(`tbody td[data-col="${col}"]`).forEach(c => c.classList.add('col-highlight'));
    });
    catTbl.addEventListener('mouseout', (e) => {
      const th = e.target.closest('thead th[data-col]');
      if (!th) return;
      const col = th.dataset.col;
      catTbl.querySelectorAll(`tbody td[data-col="${col}"]`).forEach(c => c.classList.remove('col-highlight'));
    });
  }
  document.querySelectorAll('#panel-total .sortable').forEach(th => {
    th.addEventListener('click', () => {
      const k = th.dataset.sort;
      if (totalSortState.key === k) totalSortState.dir = (totalSortState.dir === 'desc') ? 'asc' : 'desc';
      else { totalSortState.key = k; totalSortState.dir = 'desc'; }
      render(currentYear);
    });
  });
  // Cross-section peer highlight: 4개 peer-row 표 (cmp/cogs/opex/total) + 카테고리 매트릭스 컬럼
  function getTickerFromTr(tr) {
    if (!tr) return null;
    const a = tr.querySelector('a[href^="clubs/"]');
    if (!a) return null;
    const m = a.getAttribute('href').match(/clubs\/([a-z]+)\.html/i);
    return m ? m[1].toUpperCase() : null;
  }
  function getMatrixColIdx(ticker) {
    const ths = document.querySelectorAll('#opex-cat-thead th[data-col]');
    for (const th of ths) {
      const a = th.querySelector('a[href^="clubs/"]');
      if (a) {
        const m = a.getAttribute('href').match(/clubs\/([a-z]+)\.html/i);
        if (m && m[1].toUpperCase() === ticker) return th.dataset.col;
      }
    }
    return null;
  }
  const PEER_TBODIES = ['cmp-tbody','cogs-cmp-tbody','opex-cmp-tbody','total-cmp-tbody'];
  function clearPeerHighlight() {
    document.querySelectorAll('.peer-highlight').forEach(r => r.classList.remove('peer-highlight'));
    document.querySelectorAll('.peer-col-highlight').forEach(c => c.classList.remove('peer-col-highlight'));
  }
  function applyPeerHighlight(ticker) {
    if (!ticker) return;
    PEER_TBODIES.forEach(id => {
      const tb = document.getElementById(id);
      if (!tb) return;
      tb.querySelectorAll('tr').forEach(r => {
        if (getTickerFromTr(r) === ticker) r.classList.add('peer-highlight');
      });
    });
    const colIdx = getMatrixColIdx(ticker);
    if (colIdx !== null) {
      document.querySelectorAll(`#opex-cat-tbody td[data-col="${colIdx}"]`).forEach(c => c.classList.add('peer-col-highlight'));
    }
  }
  PEER_TBODIES.forEach(id => {
    const tb = document.getElementById(id);
    if (!tb) return;
    tb.addEventListener('mouseover', (e) => {
      const tr = e.target.closest('tr');
      const ticker = getTickerFromTr(tr);
      if (!ticker) return;
      const same = e.relatedTarget && e.relatedTarget.closest && e.relatedTarget.closest('tr');
      if (same && getTickerFromTr(same) === ticker) return;
      clearPeerHighlight();
      applyPeerHighlight(ticker);
    });
    tb.addEventListener('mouseleave', () => clearPeerHighlight());
  });
  // Also let hovering the matrix column header drive the highlight
  const catThead = document.getElementById('opex-cat-thead');
  if (catThead) {
    catThead.addEventListener('mouseover', (e) => {
      const th = e.target.closest('th[data-col]');
      if (!th) return;
      const a = th.querySelector('a[href^="clubs/"]');
      if (!a) return;
      const m = a.getAttribute('href').match(/clubs\/([a-z]+)\.html/i);
      if (!m) return;
      clearPeerHighlight();
      applyPeerHighlight(m[1].toUpperCase());
    });
    catThead.addEventListener('mouseleave', () => clearPeerHighlight());
  }
  render(currentYear);
})();
</script>
</body>
</html>
'''

html = html.replace('__PEER_DATA__', peer_data_json)
html = html.replace('__PEER_ORDER__', json.dumps(peers_sorted))
html = html.replace('__CAT_ORDER__', cat_order_json)
html = html.replace('__COGS_SECTION__', cogs_html)
html = html.replace('__OPEX_SECTION__', opex_html)

with open('cost-hr.html','w',encoding='utf-8') as f:
    f.write(html)
print(f'cost-hr.html: {os.path.getsize("cost-hr.html")/1024:.1f} KB')
