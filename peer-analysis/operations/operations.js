/* operations.js — interactive features for Phase 3-3·3-4·3-5
   - Column sorting (data-sortable on th)
   - Currency toggle (IDR / USD / KRW) via header button
   - Search box (header)
   Loaded by all 7 ops pages + clubs/ pages.
*/

(function(){
  'use strict';

  // === Config ===
  // Reference exchange rates (update via this object). Display only — not for trading.
  const FX = {
    base: 'IDR',
    asOf: '2026-05-01',
    rates: {
      'IDR': 1,
      'USD': 1 / 16100,     // 1 USD = 16,100 IDR
      'KRW': 12 / 16100,    // 1 KRW ≈ 12 IDR
    },
    symbols: { 'IDR': 'Rp', 'USD': '$', 'KRW': '₩' },
  };

  let currentCurrency = localStorage.getItem('ops-currency') || 'IDR';

  // === Currency toggle ===
  function fmtCurrency(idrBn, currency) {
    // idrBn: amount in "Rp X bn" (i.e. multiply by 1e9 internally)
    const idr = idrBn * 1e9;
    const rate = FX.rates[currency];
    const converted = idr * rate;
    const sym = FX.symbols[currency];
    if (currency === 'IDR') {
      if (Math.abs(idrBn) >= 1000) return `${sym} ${(idrBn/1000).toFixed(2)} T`;
      return `${sym} ${idrBn.toFixed(1)} bn`;
    }
    if (currency === 'USD') {
      if (Math.abs(converted) >= 1e9) return `${sym}${(converted/1e9).toFixed(2)} B`;
      if (Math.abs(converted) >= 1e6) return `${sym}${(converted/1e6).toFixed(1)} M`;
      return `${sym}${(converted/1e3).toFixed(0)} K`;
    }
    if (currency === 'KRW') {
      if (Math.abs(converted) >= 1e12) return `${sym}${(converted/1e12).toFixed(2)}조`;
      if (Math.abs(converted) >= 1e8) return `${sym}${(converted/1e8).toFixed(1)}억`;
      return `${sym}${(converted/1e4).toFixed(0)}만`;
    }
  }

  function applyCurrency(currency) {
    currentCurrency = currency;
    localStorage.setItem('ops-currency', currency);
    document.querySelectorAll('[data-idr-bn]').forEach(el => {
      const idrBn = parseFloat(el.dataset.idrBn);
      if (!isNaN(idrBn)) el.textContent = fmtCurrency(idrBn, currency);
    });
    document.querySelectorAll('.fx-toggle-btn').forEach(b => {
      b.classList.toggle('active', b.dataset.fx === currency);
    });
  }

  function injectCurrencyToggle() {
    // Inject into header nav (left of "← 지도" if exists)
    const nav = document.querySelector('.ops-nav');
    if (!nav || document.querySelector('.fx-toggle')) return;
    const toggle = document.createElement('div');
    toggle.className = 'fx-toggle';
    toggle.style.cssText = 'display:inline-flex; gap:2px; margin: 0 8px; align-items:center; padding: 2px; background: var(--ops-bg); border-radius: 6px; border: 1px solid var(--ops-line);';
    ['IDR','USD','KRW'].forEach(c => {
      const b = document.createElement('button');
      b.className = 'fx-toggle-btn' + (c === currentCurrency ? ' active' : '');
      b.dataset.fx = c;
      b.textContent = c;
      b.style.cssText = 'border:none; background:transparent; padding:3px 8px; font-size:11px; font-weight:600; cursor:pointer; border-radius:4px; color:var(--ops-ink-soft);';
      b.addEventListener('click', () => applyCurrency(c));
      toggle.appendChild(b);
    });
    // Insert before "← 지도" or at end
    const backLink = nav.querySelector('.back');
    if (backLink) nav.insertBefore(toggle, backLink);
    else nav.appendChild(toggle);

    // Style active state via CSS injection
    if (!document.querySelector('#fx-style')) {
      const st = document.createElement('style');
      st.id = 'fx-style';
      st.textContent = '.fx-toggle-btn.active { background: var(--ops-green); color: white !important; }';
      document.head.appendChild(st);
    }
  }

  // === Table sorting ===
  function injectSortableSort() {
    document.querySelectorAll('table.ops-tbl').forEach(table => {
      const ths = table.querySelectorAll('thead th');
      ths.forEach((th, idx) => {
        if (th.dataset.noSort === 'true') return;
        th.style.cursor = 'pointer';
        th.title = '클릭으로 정렬';
        let direction = 0; // 0 none, 1 asc, -1 desc
        th.addEventListener('click', () => {
          direction = direction === 1 ? -1 : 1;
          const tbody = table.querySelector('tbody');
          const rows = Array.from(tbody.querySelectorAll('tr'));
          rows.sort((a,b) => {
            const aCell = a.cells[idx];
            const bCell = b.cells[idx];
            const aVal = parseFloat((aCell?.textContent || '').replace(/[^0-9.\-]/g,''));
            const bVal = parseFloat((bCell?.textContent || '').replace(/[^0-9.\-]/g,''));
            if (!isNaN(aVal) && !isNaN(bVal)) {
              return (aVal - bVal) * direction;
            }
            return (aCell?.textContent || '').localeCompare(bCell?.textContent || '') * direction;
          });
          rows.forEach(r => tbody.appendChild(r));
          // visual indicator
          ths.forEach(t2 => t2.dataset.sortDir = '');
          th.dataset.sortDir = direction === 1 ? 'asc' : 'desc';
        });
      });
    });
  }

  // === Search ===
  function injectSearch() {
    const nav = document.querySelector('.ops-nav');
    if (!nav || document.querySelector('.ops-search')) return;
    const input = document.createElement('input');
    input.type = 'search';
    input.placeholder = '클럽·티커·지역 검색';
    input.className = 'ops-search';
    input.style.cssText = 'padding:5px 10px; border:1px solid var(--ops-line); border-radius:6px; font-size:12px; width:180px; margin:0 8px;';
    input.addEventListener('input', () => {
      const q = input.value.trim().toLowerCase();
      if (!q) {
        // clear search highlights
        document.querySelectorAll('table.ops-tbl tbody tr').forEach(r => { r.style.opacity = '1'; r.style.background = ''; });
        return;
      }
      // Filter rows in any ops-tbl + club-grid
      document.querySelectorAll('table.ops-tbl tbody tr').forEach(r => {
        const txt = r.textContent.toLowerCase();
        r.style.opacity = txt.includes(q) ? '1' : '0.25';
      });
      // Filter club cards if on clubs page
      document.querySelectorAll('.club-card').forEach(c => {
        const txt = c.textContent.toLowerCase();
        c.style.display = txt.includes(q) ? '' : 'none';
      });
    });
    const backLink = nav.querySelector('.back');
    if (backLink) nav.insertBefore(input, backLink);
    else nav.appendChild(input);
  }

  // === Footer note (currency rate disclosure) ===
  function injectFXFooter() {
    const foot = document.querySelector('.ops-foot');
    if (!foot || foot.querySelector('.fx-disclosure')) return;
    const note = document.createElement('p');
    note.className = 'fx-disclosure';
    note.style.cssText = 'font-size:10.5px; color:rgba(255,255,255,0.55); margin-top:6px;';
    note.innerHTML = `기준 환율: 1 USD = IDR 16,100 / 1 KRW ≈ IDR 12 (as of ${FX.asOf}). 표시 전용 — 거래·평가용 아님.`;
    foot.querySelector('.ops-wrap').appendChild(note);
  }

  // === Init ===
  document.addEventListener('DOMContentLoaded', () => {
    injectCurrencyToggle();
    injectSortableSort();
    injectSearch();
    injectFXFooter();
    applyCurrency(currentCurrency);
  });
})();
