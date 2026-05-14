/* Pure-play 골프장 운영 비교 — vanilla JS for tabs + sort.
   No fetch(). All data is pre-rendered in HTML by _build.py. */

(function () {
  'use strict';

  // === Tabs ===
  function initTabs() {
    const tabs = document.querySelectorAll('.tab');
    const panels = document.querySelectorAll('.panel');
    if (!tabs.length || !panels.length) return;

    function activate(name) {
      tabs.forEach(t => t.classList.toggle('active', t.dataset.tab === name));
      panels.forEach(p => p.classList.toggle('active', p.dataset.panel === name));
      // Reflect in URL hash without scrolling
      if (history.replaceState) history.replaceState(null, '', '#' + name);
      window.scrollTo({ top: 0, behavior: 'instant' in window ? 'instant' : 'auto' });
    }

    tabs.forEach(t => {
      t.addEventListener('click', () => activate(t.dataset.tab));
    });

    // Initial: from hash, else first tab
    const hash = (location.hash || '').replace('#', '');
    const initial = (hash && document.querySelector('.panel[data-panel="' + hash + '"]'))
      ? hash
      : (tabs[0] && tabs[0].dataset.tab);
    if (initial) activate(initial);
  }

  // === Table sorting ===
  function initSort() {
    document.querySelectorAll('table.tbl').forEach(table => {
      const ths = table.querySelectorAll('thead th');
      ths.forEach((th, idx) => {
        if (th.dataset.noSort === 'true') return;
        th.style.cursor = 'pointer';
        th.title = '클릭으로 정렬';
        let dir = 0;
        th.addEventListener('click', () => {
          dir = dir === 1 ? -1 : 1;
          const tbody = table.querySelector('tbody');
          if (!tbody) return;
          const rows = Array.from(tbody.querySelectorAll('tr'));
          rows.sort((a, b) => {
            const ac = a.cells[idx];
            const bc = b.cells[idx];
            const at = (ac?.textContent || '').trim();
            const bt = (bc?.textContent || '').trim();
            // Push N/A to bottom regardless of dir
            const aNA = /^N\/A$|^—$/.test(at);
            const bNA = /^N\/A$|^—$/.test(bt);
            if (aNA && !bNA) return 1;
            if (!aNA && bNA) return -1;
            const av = parseFloat(at.replace(/[^0-9.\-]/g, ''));
            const bv = parseFloat(bt.replace(/[^0-9.\-]/g, ''));
            if (!isNaN(av) && !isNaN(bv)) return (av - bv) * dir;
            return at.localeCompare(bt) * dir;
          });
          rows.forEach(r => tbody.appendChild(r));
          ths.forEach(t2 => t2.removeAttribute('data-sort-dir'));
          th.setAttribute('data-sort-dir', dir === 1 ? 'asc' : 'desc');
        });
      });
    });
  }

  // === Scroll progress bar (active on ops panel) ===
  function initScrollProgress() {
    let bar = document.querySelector('.scroll-progress');
    if (!bar) {
      bar = document.createElement('div');
      bar.className = 'scroll-progress hidden';
      document.body.insertBefore(bar, document.body.firstChild);
    }
    const opsPanel = document.querySelector('.panel[data-panel="ops"]');
    function update() {
      const opsActive = opsPanel && opsPanel.classList.contains('active');
      if (!opsActive) {
        bar.classList.add('hidden');
        bar.style.width = '0%';
        return;
      }
      bar.classList.remove('hidden');
      const doc = document.documentElement;
      const max = (doc.scrollHeight - window.innerHeight) || 1;
      const pct = Math.min(100, Math.max(0, (window.scrollY / max) * 100));
      bar.style.width = pct.toFixed(2) + '%';
    }
    window.addEventListener('scroll', update, { passive: true });
    window.addEventListener('resize', update, { passive: true });
    document.querySelectorAll('.tab').forEach(t => t.addEventListener('click', () => setTimeout(update, 60)));
    update();
  }

  // === Sub-nav active section highlighting (IntersectionObserver) ===
  function initSubnavActive() {
    const subnav = document.querySelector('.ops-subnav');
    if (!subnav || !('IntersectionObserver' in window)) return;
    const chips = Array.from(subnav.querySelectorAll('a.chip[href^="#"]'));
    if (!chips.length) return;
    const idToChip = {};
    chips.forEach(c => {
      const id = c.getAttribute('href').slice(1);
      idToChip[id] = c;
    });
    const sections = chips
      .map(c => document.getElementById(c.getAttribute('href').slice(1)))
      .filter(Boolean);
    if (!sections.length) return;

    const visibilityMap = new Map();
    sections.forEach(s => visibilityMap.set(s.id, 0));

    function setActive(id) {
      chips.forEach(c => c.classList.toggle('active', c === idToChip[id]));
      // Scroll the active chip into view inside subnav
      const chip = idToChip[id];
      if (chip) {
        const rect = chip.getBoundingClientRect();
        const navRect = subnav.getBoundingClientRect();
        if (rect.left < navRect.left || rect.right > navRect.right) {
          chip.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });
        }
      }
    }

    const io = new IntersectionObserver((entries) => {
      entries.forEach(e => visibilityMap.set(e.target.id, e.intersectionRatio));
      // Pick most-visible section
      let bestId = null;
      let bestRatio = 0;
      visibilityMap.forEach((r, id) => {
        if (r > bestRatio) { bestRatio = r; bestId = id; }
      });
      if (bestId && bestRatio > 0.05) setActive(bestId);
    }, {
      rootMargin: '-120px 0px -50% 0px',
      threshold: [0.05, 0.25, 0.5, 0.75, 1],
    });
    sections.forEach(s => io.observe(s));
  }

  // === Back-to-TOC floating button (ops tab only) ===
  function initBackToToc() {
    const btn = document.querySelector('.back-to-toc');
    if (!btn) return;
    const opsPanel = document.querySelector('.panel[data-panel="ops"]');
    function update() {
      const opsActive = opsPanel && opsPanel.classList.contains('active');
      const scrolled = window.scrollY > 700;
      btn.classList.toggle('visible', !!(opsActive && scrolled));
    }
    window.addEventListener('scroll', update, { passive: true });
    document.querySelectorAll('.tab').forEach(t => t.addEventListener('click', () => setTimeout(update, 60)));
    update();
  }

  document.addEventListener('DOMContentLoaded', () => {
    initTabs();
    initSort();
    initBackToToc();
    initSubnavActive();
    initScrollProgress();
  });
})();
