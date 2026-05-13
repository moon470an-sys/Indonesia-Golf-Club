/* Tab router + theme toggle.
   - Tabs read their id from the data-tab attribute and the URL hash routes
     to that panel. Panels lazily call their `init` callback once. */
(function (global) {
  'use strict';

  const TABS = ['cockpit','balance-sheet','profitability','growth',
                'capex','cost','segment','peer-context'];

  const initialised = {};
  const initRegistry = {};

  /* Register the renderer for a given tab id. */
  function register(id, fn) {
    initRegistry[id] = fn;
    if (location.hash.replace('#','') === id && PurePlayApp.dataReady) {
      ensureInit(id);
    }
  }

  function ensureInit(id) {
    if (initialised[id]) return;
    const fn = initRegistry[id];
    if (typeof fn === 'function') {
      try { fn(global.PurePlayApp.data); } catch (err) { console.error('Tab init failed:', id, err); }
    }
    initialised[id] = true;
  }

  function activate(id) {
    if (!TABS.includes(id)) id = 'cockpit';
    document.querySelectorAll('.tab').forEach(b => {
      b.classList.toggle('active', b.dataset.tab === id);
    });
    document.querySelectorAll('.panel').forEach(p => {
      p.classList.toggle('active', p.dataset.tab === id);
    });
    if (location.hash.replace('#','') !== id) {
      history.replaceState(null, '', '#' + id);
    }
    if (global.PurePlayApp.dataReady) ensureInit(id);
  }

  function onClick(e) {
    const t = e.target.closest('.tab');
    if (!t) return;
    e.preventDefault();
    activate(t.dataset.tab);
  }

  function init() {
    document.querySelector('.tabs').addEventListener('click', onClick);
    window.addEventListener('hashchange', () => activate(location.hash.replace('#','')));
    const id = location.hash.replace('#','') || 'cockpit';
    activate(id);
  }

  /* Theme toggle */
  function setTheme(t) {
    document.documentElement.setAttribute('data-theme', t);
    try { localStorage.setItem('pureplay-theme', t); } catch (e) {}
    if (global.PurePlayCharts && global.PurePlayCharts.refreshAll) {
      global.PurePlayCharts.refreshAll();
    }
  }
  function toggleTheme() {
    const cur = document.documentElement.getAttribute('data-theme') || 'light';
    setTheme(cur === 'light' ? 'dark' : 'light');
  }
  function restoreTheme() {
    let t = 'light';
    try { t = localStorage.getItem('pureplay-theme') || 'light'; } catch (e) {}
    document.documentElement.setAttribute('data-theme', t);
  }

  /* CSV download helper (used by tab panels) */
  function downloadCSV(filename, rows) {
    const csv = rows.map(r => r.map(c => {
      if (c === null || c === undefined) return '';
      const s = String(c);
      if (/[,"\n]/.test(s)) return '"' + s.replace(/"/g, '""') + '"';
      return s;
    }).join(',')).join('\n');
    const blob = new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = filename;
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  function downloadJSON(filename, obj) {
    const blob = new Blob([JSON.stringify(obj, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = filename;
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  global.PurePlayTabs = {
    init, register, activate, restoreTheme, toggleTheme, setTheme,
    downloadCSV, downloadJSON,
  };
})(window);
