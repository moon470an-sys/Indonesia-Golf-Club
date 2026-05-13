"""FY2025 comprehensive migration v2 — overwrites yearly['2025'] with
stockanalysis.com-sourced consolidated figures (FY2025 audited annual statements).

Source: stockanalysis.com/quote/idx/{TICKER}/financials/ + balance-sheet/
Fetched: 2026-05-13 (today)
Values are in IDR (converted from IDR millions in source).

DMIG/PIPG already had FY25 from AR notes follow-up; this script REPLACES with
stockanalysis figures for consistency across all 13 peers (similar magnitudes,
minor rounding from M vs full IDR).
"""
import sys, json, os
sys.stdout.reconfigure(encoding='utf-8')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIN_PATH = os.path.join(os.path.dirname(ROOT), 'data', 'company_financials_5y.json')

# Values in IDR millions (from stockanalysis.com)
# fields: revenue, operating_profit, net_profit, ebitda, total_assets, total_liabilities, total_equity
FY25_M = {
    'DMIG': {'revenue': 251254, 'operating_profit': 69447, 'net_profit': 75024, 'ebitda': None,    'total_assets': 719679, 'total_liabilities': 181428, 'total_equity': 538251},
    'PIPG': {'revenue': 185775, 'operating_profit': 55313, 'net_profit': 56000, 'ebitda': None,    'total_assets': 477919, 'total_liabilities':  90935, 'total_equity': 386984},
    'GOLF': {'revenue': 215520, 'operating_profit': 64868, 'net_profit':  51809, 'ebitda': 82673,    'total_assets':  8685571, 'total_liabilities':   666780, 'total_equity':  8018791},
    'MDLN': {'revenue': 1013159, 'operating_profit': 105167, 'net_profit': 241713, 'ebitda': 165928, 'total_assets': 13451083, 'total_liabilities':  9714483, 'total_equity':  3736601},
    'KIJA': {'revenue': 5149425, 'operating_profit': 1422399, 'net_profit': 423198, 'ebitda': 1607806, 'total_assets': 15056220, 'total_liabilities': 6911851, 'total_equity':  8144369},
    'SMDM': {'revenue': 386085, 'operating_profit': 49544, 'net_profit': 22110, 'ebitda': 64740,    'total_assets':  3531806, 'total_liabilities':   269513, 'total_equity':  3262293},
    'KPIG': {'revenue': 2615281, 'operating_profit': 685553, 'net_profit': 717222, 'ebitda': 829034, 'total_assets': 35994124, 'total_liabilities': 7226096, 'total_equity': 28768028},
    'SMRA': {'revenue': 8766927, 'operating_profit': 2517415, 'net_profit': 766550, 'ebitda': 2877557, 'total_assets': 38342512, 'total_liabilities': 22337631, 'total_equity': 16004880},
    'BSDE': {'revenue': 12788452, 'operating_profit': 3936274, 'net_profit': 2545381, 'ebitda': None, 'total_assets': 79268402, 'total_liabilities': 26599498, 'total_equity': 52668905},
    'CTRA': {'revenue': 12616695, 'operating_profit': 3829489, 'net_profit': 2663100, 'ebitda': 4241159, 'total_assets': 47988422, 'total_liabilities': 21069686, 'total_equity': 26918736},
    'ELTY': {'revenue': 1379377, 'operating_profit': 110234, 'net_profit': -16697, 'ebitda': 182258, 'total_assets': 8637625, 'total_liabilities': 2635123, 'total_equity': 6002502},
    'LPKR': {'revenue': 8843888, 'operating_profit': 720714, 'net_profit': 469535, 'ebitda': 917135, 'total_assets': 49247221, 'total_liabilities': 18196206, 'total_equity': 31051015},
    'PWON': {'revenue': 7111105, 'operating_profit': 2943746, 'net_profit': 2346120, 'ebitda': 3702881, 'total_assets': 36466038, 'total_liabilities': 9843195, 'total_equity': 26622844},
}

fin_doc = json.load(open(FIN_PATH, 'r', encoding='utf-8'))
fin_by_ticker = {c['ticker']: c for c in fin_doc.get('companies', []) if 'ticker' in c}

for ticker, vals_m in FY25_M.items():
    c = fin_by_ticker.get(ticker)
    if not c:
        print(f'⚠ {ticker} not in financials_5y.json — skipping')
        continue
    yearly = c.setdefault('yearly', {})
    y = yearly.setdefault('2025', {})
    changes = []
    for k, v_m in vals_m.items():
        if v_m is None: continue
        v_idr = v_m * 1_000_000  # millions → IDR
        old = y.get(k)
        if old != v_idr:
            y[k] = v_idr
            changes.append(f'{k}={v_idr/1e9:.1f}B')
    if changes:
        print(f'  {ticker} FY2025 ←', ', '.join(changes))

# Verify post-migration
print('\nPost-migration FY2025 coverage (13 peers):')
peers_v2 = ['DMIG','PIPG','GOLF','MDLN','KIJA','SMDM','KPIG','SMRA','BSDE','CTRA','ELTY','LPKR','PWON']
for t in peers_v2:
    y25 = fin_by_ticker.get(t, {}).get('yearly', {}).get('2025', {})
    rev = y25.get('revenue'); op_ = y25.get('operating_profit'); np_ = y25.get('net_profit')
    ta = y25.get('total_assets'); tl = y25.get('total_liabilities'); te = y25.get('total_equity')
    eb = y25.get('ebitda')
    marks = ''.join([
        'R' if rev else '·', 'O' if op_ else '·', 'N' if np_ is not None else '·',
        'E' if eb else '·', 'A' if ta else '·', 'L' if tl else '·', 'Q' if te else '·',
    ])
    rev_str = f'{rev/1e9:.1f}B' if rev else '—'
    print(f'  {t}: {marks}  rev={rev_str}')

json.dump(fin_doc, open(FIN_PATH, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print(f'\nWrote {FIN_PATH}')
