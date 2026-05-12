/* operations.js — table sort + search (currency toggle removed) */

(function(){
  'use strict';

  // === Table sorting ===
  function initSort() {
    document.querySelectorAll('table.ops-tbl').forEach(table => {
      const ths = table.querySelectorAll('thead th');
      ths.forEach((th, idx) => {
        if (th.dataset.noSort === 'true') return;
        th.style.cursor = 'pointer';
        th.title = '클릭으로 정렬';
        let direction = 0;
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
          ths.forEach(t2 => t2.dataset.sortDir = '');
          th.dataset.sortDir = direction === 1 ? 'asc' : 'desc';
        });
      });
    });
  }

  // === Search ===
  function initSearch() {
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
        document.querySelectorAll('table.ops-tbl tbody tr').forEach(r => { r.style.opacity = '1'; });
        document.querySelectorAll('.club-card').forEach(c => { c.style.display = ''; });
        document.querySelectorAll('.peer-card').forEach(c => { c.style.display = ''; });
        return;
      }
      document.querySelectorAll('table.ops-tbl tbody tr').forEach(r => {
        const txt = r.textContent.toLowerCase();
        r.style.opacity = txt.includes(q) ? '1' : '0.25';
      });
      document.querySelectorAll('.club-card, .peer-card').forEach(c => {
        const txt = c.textContent.toLowerCase();
        c.style.display = txt.includes(q) ? '' : 'none';
      });
    });
    const backLink = nav.querySelector('.back');
    if (backLink) nav.insertBefore(input, backLink);
    else nav.appendChild(input);
  }

  document.addEventListener('DOMContentLoaded', () => {
    initSort();
    initSearch();
  });
})();
