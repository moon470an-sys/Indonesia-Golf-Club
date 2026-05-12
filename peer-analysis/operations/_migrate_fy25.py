"""One-time data migration: pull FY2025 from notes/*.json follow-up sections
into data/company_financials_5y.json yearly['2025'].

Idempotent — re-running fills missing fields without overwriting populated ones."""
import sys, json, os
sys.stdout.reconfigure(encoding='utf-8')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIN_PATH = os.path.join(os.path.dirname(ROOT), 'data', 'company_financials_5y.json')
NOTES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')

fin_doc = json.load(open(FIN_PATH, 'r', encoding='utf-8'))
fin_by_ticker = {c['ticker']: c for c in fin_doc.get('companies', []) if 'ticker' in c}

def set_y25(ticker, **fields):
    """Set FY2025 fields only when current value is None/missing."""
    c = fin_by_ticker.get(ticker)
    if not c: return
    yearly = c.setdefault('yearly', {})
    y = yearly.setdefault('2025', {})
    changes = []
    for k, v in fields.items():
        if v is None: continue
        if y.get(k) is None:
            y[k] = v
            changes.append(k)
    if changes:
        print(f'  {ticker} FY2025 ←', ', '.join(changes))

# === MDLN: notes/mdln_notes.json fy2025_follow_up ===
n = json.load(open(os.path.join(NOTES_DIR, 'mdln_notes.json'), 'r', encoding='utf-8'))
fu = n.get('fy2025_follow_up', {})
rev25 = fu.get('revenue_note_25_FY2025', {})
if isinstance(rev25, dict):
    # Total group revenue = sum of all line items
    total = sum(v for v in rev25.values() if isinstance(v, (int, float)))
    set_y25('MDLN', revenue=total if total > 0 else None)

# === SMDM: fy2025_follow_up.FY2025_Konsolidasian ===
n = json.load(open(os.path.join(NOTES_DIR, 'smdm_notes.json'), 'r', encoding='utf-8'))
fu = n.get('fy2025_follow_up', {})
kons = fu.get('FY2025_Konsolidasian', {})
if isinstance(kons, dict):
    rev_keys = ['Real_Estat_Properti_revenue', 'Golf_CC_revenue', 'Investasi_Hotel_revenue',
                'Layanan_Hari_Tua_revenue', 'Lain_lain_revenue']
    total = sum(kons.get(k, 0) or 0 for k in rev_keys)
    set_y25('SMDM', revenue=total if total > 0 else None)

# === KPIG: fy2025_follow_up.FY2025_revenue_note_31 ===
n = json.load(open(os.path.join(NOTES_DIR, 'kpig_notes.json'), 'r', encoding='utf-8'))
fu = n.get('fy2025_follow_up', {})
note31 = fu.get('FY2025_revenue_note_31', {})
hotel = note31.get('Hotel_resor_dan_golf')
if hotel:
    # KPIG's note 31 has Hotel+Resort+Golf as a single line item — that's a partial
    # group revenue line. For overall group revenue we don't have direct FY25 data;
    # we set this as the hotel/resort/golf segment line only (and leave group rev null).
    pass  # No clean group revenue available for KPIG FY25

# === Verify the integrations didn't already exist before ===
peers_v2 = ['DMIG','PIPG','GOLF','MDLN','KIJA','SMDM','KPIG','SMRA','BSDE','CTRA','ELTY','LPKR','PWON']
print('\\nPost-migration FY2025 coverage (13 peers):')
for t in peers_v2:
    y25 = fin_by_ticker.get(t, {}).get('yearly', {}).get('2025', {})
    rev = y25.get('revenue'); op_ = y25.get('operating_profit'); np_ = y25.get('net_profit')
    ta = y25.get('total_assets')
    marks = ''.join([
        'R' if rev else '·',
        'O' if op_ else '·',
        'N' if np_ else '·',
        'A' if ta else '·',
    ])
    rev_str = f'{rev/1e9:.1f}B' if rev else '—'
    print(f'  {t}: {marks}  rev={rev_str}')

# Save
json.dump(fin_doc, open(FIN_PATH, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print(f'\\nWrote {FIN_PATH}')
