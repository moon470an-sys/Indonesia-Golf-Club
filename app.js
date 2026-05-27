// === State ===
let allCourses = [];
let filteredCourses = [];
let markers = {};
let markerCluster;
let map;
const PRICE_MAX = 3000000;
let currentFilter = {
  search: '',
  regions: new Set(),   // empty = all
  holes: 'all',
  status: 'all',
  priceMin: 0,
  priceMax: PRICE_MAX,
  priceIncludeUnknown: true,
};

// Approximate Sat AM green fee for slider filter & price-band features.
function getSatAmIDR(c) {
  const f = c.fees_2026_05 || {};
  const sd = f.schedule_detailed || {};
  const sat = sd.weekend_saturday;
  if (sat && typeof sat === 'object') {
    const morning = sat.morning;
    if (typeof morning === 'number') return morning;
    if (morning && typeof morning === 'object') {
      for (const k of ['visitor', 'green_fee_idr', 'guest', 'public_rate', 'guest_fee_idr']) {
        if (typeof morning[k] === 'number') return morning[k];
      }
      for (const v of Object.values(morning)) {
        if (typeof v === 'number') return v;
      }
    }
  }
  const we = f.weekend;
  if (we && typeof we === 'object') {
    return we.green_fee_idr ?? we.guest_fee_idr ?? we.member_fee_idr ?? null;
  }
  return null;
}

// === Init Map ===
function initMap() {
  map = L.map('map', {
    zoomControl: true,
    attributionControl: true,
  }).setView([-2.5, 118], 5);

  L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
    attribution: '© <a href="https://www.openstreetmap.org/copyright">OSM</a> contributors © <a href="https://carto.com/attributions">CARTO</a>',
    subdomains: 'abcd',
    maxZoom: 19,
  }).addTo(map);

  markerCluster = L.markerClusterGroup({
    showCoverageOnHover: false,
    maxClusterRadius: 45,
    spiderfyOnMaxZoom: true,
  });
  map.addLayer(markerCluster);

  map.on('click', () => {
    const panel = document.getElementById('detailPanel');
    if (panel && panel.classList.contains('open')) {
      panel.classList.remove('open');
      panel.setAttribute('aria-hidden', 'true');
      document.body.classList.remove('detail-open');
      document.querySelectorAll('.course-item').forEach(el => el.classList.remove('active'));
    }
  });
}

// === Load Data ===
function computeStatusCounts(courses) {
  const counts = { total: courses.length, operating: 0, closed: 0, uncertain: 0 };
  for (const c of courses) {
    const s = c.operating_status?.status || 'operating';
    if (s === 'operating') counts.operating += 1;
    else if (s === 'closed_temporary' || s === 'closed_permanent') counts.closed += 1;
    else if (s === 'uncertain') counts.uncertain += 1;
  }
  return counts;
}

function renderHeaderSubtitle(counts) {
  const sub = document.getElementById('headerSubtitle');
  if (sub) {
    sub.innerHTML = t('header.totalLine', counts);
  }
  const foot = document.getElementById('footerCount');
  if (foot) {
    foot.textContent = t('header.totalText', counts);
  }
}

async function loadData() {
  try {
    const res = await fetch('data/golf_courses.json');
    const doc = await res.json();
    allCourses = doc.courses.filter(c => c.lat != null && c.lng != null);
    const counts = computeStatusCounts(allCourses);
    document.getElementById('totalCount').textContent = t('header.counterPill', counts);
    const pill = document.getElementById('counterPill');
    if (pill) pill.hidden = false;
    renderHeaderSubtitle(counts);
    renderRegionMulti();
    wireRegionMulti();
    wirePriceSlider();
    wireFilterSummary();
    updateFilterSummary();
    applyFilter();
  } catch (e) {
    console.error('Failed to load data:', e);
    alert(t('common.dataLoadFailed'));
  }
}

// === Region Multiselect ===
let _regionSearchQuery = '';

function renderRegionMulti() {
  const counts = {};
  for (const c of allCourses) counts[c.region] = (counts[c.region] || 0) + 1;
  const regions = Object.keys(counts).sort();
  const list = document.getElementById('regionMultiList');
  if (!list) return;

  const q = _regionSearchQuery.trim().toLowerCase();
  const filtered = q ? regions.filter(r => r.toLowerCase().includes(q)) : regions;

  if (filtered.length === 0) {
    list.innerHTML = `<div class="region-empty">${t('common.noResults')}</div>`;
  } else {
    list.innerHTML = filtered.map(r => {
      const checked = currentFilter.regions.has(r) ? ' checked' : '';
      return `<label><input type="checkbox" value="${escapeHtml(r)}"${checked} />` +
        `<span>${escapeHtml(r)}</span><span class="region-count">${counts[r]}</span></label>`;
    }).join('');
  }
  updateRegionTriggerLabel();
}

function updateRegionTriggerLabel() {
  const text = document.querySelector('#regionMultiTrigger .region-multi-text');
  if (!text) return;
  const n = currentFilter.regions.size;
  if (n === 0) {
    text.textContent = t('region.all');
    text.classList.remove('has-selection');
  } else if (n === 1) {
    text.textContent = [...currentFilter.regions][0];
    text.classList.add('has-selection');
  } else {
    text.textContent = t('region.selectedSummary', { first: [...currentFilter.regions][0], extra: n - 1 });
    text.classList.add('has-selection');
  }
}

function wireRegionMulti() {
  const trigger = document.getElementById('regionMultiTrigger');
  const popover = document.getElementById('regionMultiPopover');
  const search = document.getElementById('regionMultiSearch');
  const list = document.getElementById('regionMultiList');
  if (!trigger || !popover) return;

  const close = () => {
    popover.hidden = true;
    trigger.setAttribute('aria-expanded', 'false');
    document.removeEventListener('click', onDocClick);
  };
  const onDocClick = (e) => {
    if (!popover.contains(e.target) && !trigger.contains(e.target)) close();
  };
  trigger.addEventListener('click', () => {
    const isOpen = !popover.hidden;
    if (isOpen) { close(); return; }
    popover.hidden = false;
    trigger.setAttribute('aria-expanded', 'true');
    setTimeout(() => document.addEventListener('click', onDocClick), 0);
    if (search) search.focus();
  });
  search?.addEventListener('input', () => {
    _regionSearchQuery = search.value;
    renderRegionMulti();
  });
  list?.addEventListener('change', (e) => {
    const cb = e.target.closest('input[type="checkbox"]');
    if (!cb) return;
    if (cb.checked) currentFilter.regions.add(cb.value);
    else currentFilter.regions.delete(cb.value);
    updateRegionTriggerLabel();
    applyFilter();
  });
  document.querySelectorAll('#regionMulti [data-region-action]').forEach(btn => {
    btn.addEventListener('click', () => {
      const act = btn.dataset.regionAction;
      if (act === 'all') {
        for (const c of allCourses) currentFilter.regions.add(c.region);
      } else {
        currentFilter.regions.clear();
      }
      renderRegionMulti();
      applyFilter();
    });
  });
}

// === Price slider ===
function fmtPriceLabel(v) {
  if (v >= PRICE_MAX) return `Rp ${PRICE_MAX / 1e6}M+`;
  if (v >= 1e6) return `Rp ${(v / 1e6).toFixed(v % 1e6 === 0 ? 0 : 1)}M`;
  if (v >= 1000) return `Rp ${(v / 1000).toFixed(0)}K`;
  return `Rp ${v}`;
}
function updatePriceSliderUI() {
  const minEl = document.getElementById('priceMin');
  const maxEl = document.getElementById('priceMax');
  const fill = document.getElementById('priceSliderFill');
  const minRO = document.getElementById('priceMinReadout');
  const maxRO = document.getElementById('priceMaxReadout');
  if (!minEl || !maxEl) return;
  const lo = Math.min(+minEl.value, +maxEl.value);
  const hi = Math.max(+minEl.value, +maxEl.value);
  const span = +maxEl.max - +maxEl.min;
  if (fill) {
    fill.style.left = `${((lo - +maxEl.min) / span) * 100}%`;
    fill.style.right = `${100 - ((hi - +maxEl.min) / span) * 100}%`;
  }
  if (minRO) minRO.textContent = fmtPriceLabel(lo);
  if (maxRO) maxRO.textContent = fmtPriceLabel(hi);
  currentFilter.priceMin = lo;
  currentFilter.priceMax = hi;
}
function wirePriceSlider() {
  const minEl = document.getElementById('priceMin');
  const maxEl = document.getElementById('priceMax');
  const includeEl = document.getElementById('priceIncludeUnknown');
  if (!minEl || !maxEl) return;
  const onChange = () => {
    updatePriceSliderUI();
    applyFilter();
  };
  ['input', 'change'].forEach(ev => {
    minEl.addEventListener(ev, onChange);
    maxEl.addEventListener(ev, onChange);
  });
  includeEl?.addEventListener('change', () => {
    currentFilter.priceIncludeUnknown = includeEl.checked;
    applyFilter();
  });
  updatePriceSliderUI();
}

// === Filter summary & reset ===
function isPriceFiltered() {
  return currentFilter.priceMin > 0 || currentFilter.priceMax < PRICE_MAX;
}
function updateFilterSummary() {
  let n = 0;
  if (currentFilter.search) n++;
  if (currentFilter.regions.size > 0) n++;
  if (currentFilter.holes !== 'all') n++;
  if (currentFilter.status !== 'all') n++;
  if (isPriceFiltered()) n++;
  if (!currentFilter.priceIncludeUnknown) n++;
  const badge = document.getElementById('activeFilterBadge');
  if (badge) {
    badge.textContent = n;
    badge.classList.toggle('active', n > 0);
  }
}
function wireFilterSummary() {
  document.getElementById('filterResetBtn')?.addEventListener('click', () => {
    currentFilter.search = '';
    currentFilter.regions.clear();
    currentFilter.holes = 'all';
    currentFilter.status = 'all';
    currentFilter.priceMin = 0;
    currentFilter.priceMax = PRICE_MAX;
    currentFilter.priceIncludeUnknown = true;
    document.getElementById('searchInput').value = '';
    document.getElementById('priceMin').value = 0;
    document.getElementById('priceMax').value = PRICE_MAX;
    document.getElementById('priceIncludeUnknown').checked = true;
    document.querySelectorAll('#holesChips .chip').forEach(b => b.classList.toggle('active', b.dataset.holes === 'all'));
    document.querySelectorAll('#statusChips .chip').forEach(b => b.classList.toggle('active', b.dataset.status === 'all'));
    renderRegionMulti();
    updatePriceSliderUI();
    applyFilter();
  });
}

// === Holes filter ===
document.getElementById('holesChips').addEventListener('click', e => {
  if (!e.target.classList.contains('chip')) return;
  document.querySelectorAll('#holesChips .chip').forEach(b => b.classList.remove('active'));
  e.target.classList.add('active');
  currentFilter.holes = e.target.dataset.holes;
  applyFilter();
});

// === Status filter ===
document.getElementById('statusChips').addEventListener('click', e => {
  if (!e.target.classList.contains('chip')) return;
  document.querySelectorAll('#statusChips .chip').forEach(b => b.classList.remove('active'));
  e.target.classList.add('active');
  currentFilter.status = e.target.dataset.status;
  applyFilter();
});

// === Search ===
document.getElementById('searchInput').addEventListener('input', e => {
  currentFilter.search = e.target.value.trim().toLowerCase();
  applyFilter();
});

// === Apply Filter ===
function applyFilter() {
  filteredCourses = allCourses.filter(c => {
    const status = c.operating_status?.status || 'operating';
    if (currentFilter.status === 'operating-only' && status !== 'operating') return false;
    if (currentFilter.status === 'closed_temporary' && !(status === 'closed_temporary' || status === 'closed_permanent')) return false;
    if (currentFilter.status !== 'all' && currentFilter.status !== 'operating-only' && currentFilter.status !== 'closed_temporary' && status !== currentFilter.status) return false;

    if (currentFilter.regions.size > 0 && !currentFilter.regions.has(c.region)) return false;
    if (currentFilter.holes !== 'all') {
      const h = c.holes;
      if (currentFilter.holes === '9' && h !== 9) return false;
      if (currentFilter.holes === '18' && h !== 18) return false;
      if (currentFilter.holes === '27+' && (h == null || h < 27)) return false;
    }
    if (currentFilter.search) {
      const q = currentFilter.search;
      const haystack = [
        c.name_en, c.region, c.province, c.designer, c.address,
      ].filter(Boolean).join(' ').toLowerCase();
      if (!haystack.includes(q)) return false;
    }
    // Price filter (Sat AM proxy). Only apply when slider is moved or include-unknown is off.
    const priceFiltered = isPriceFiltered();
    if (priceFiltered || !currentFilter.priceIncludeUnknown) {
      const p = getSatAmIDR(c);
      if (p == null) {
        if (!currentFilter.priceIncludeUnknown) return false;
      } else {
        // PRICE_MAX position means "no upper cap" — accept anything ≥ priceMin
        const upper = currentFilter.priceMax >= PRICE_MAX ? Infinity : currentFilter.priceMax;
        if (p < currentFilter.priceMin || p > upper) return false;
      }
    }
    return true;
  });

  document.getElementById('visibleCount').textContent = filteredCourses.length;
  updateFilterSummary();
  renderMarkers();
  renderCourseList();
}

// === Render Markers ===
function statusLabelOf(status) {
  const map = {
    operating: 'status.operating',
    closed_temporary: 'status.closedTemp',
    closed_permanent: 'status.closedPerm',
    uncertain: 'status.uncertain',
  };
  return map[status] ? t(map[status]) : status;
}

function membershipAvailLabel(avail) {
  const map = {
    'true': 'member.recruiting',
    true: 'member.recruiting',
    'false': 'common.none',
    false: 'common.none',
    'by_invitation_only': 'member.invitationOnly',
    'employees_only': 'member.employees',
    'military_personnel': 'member.militaryPersonnel',
    'members_only': 'member.membersOnlyShort',
    'unknown': 'common.unknown',
  };
  return map[avail] ? t(map[avail]) : null;
}

// Build a Google Maps URL that lands on the actual course listing
// (not just the lat/lng coords). Uses place_id when available, otherwise
// queries by name + region + country so Google's place search resolves it.
function googleMapsPlaceUrl(c) {
  if (c?.google_place_id) {
    return `https://www.google.com/maps/place/?q=place_id:${encodeURIComponent(c.google_place_id)}`;
  }
  const parts = [c?.name_en, c?.region, 'Indonesia'].filter(Boolean);
  const q = parts.join(', ');
  return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(q)}`;
}

function buildMarkerPopupHtml(c) {
  const status = c.operating_status?.status || 'operating';
  const statusLabel = statusLabelOf(status);
  const f = c.fees_2026_05 || {};
  const wd = f.weekday?.green_fee_idr ?? f.weekday?.guest_fee_idr ?? f.weekday?.member_fee_idr;
  const we = f.weekend?.green_fee_idr ?? f.weekend?.guest_fee_idr ?? f.weekend?.member_fee_idr;
  const wdUSD = f.weekday?.green_fee_usd;
  const weUSD = f.weekend?.green_fee_usd;
  const fmtFee = (idr, usd) => idr ? fmtIDR(idr) : (usd ? fmtUSD(usd) : '—');

  const designer = c.designer ? escapeHtml(c.designer.split(',')[0].trim().split('(')[0].trim()) : null;
  const m = c.membership || {};
  let membershipLine = '';
  if (m.available === true || m.available === 'true') membershipLine = t('member.recruiting');
  else if (m.available === 'employees_only') membershipLine = t('member.employees');
  else if (m.available === 'military_personnel') membershipLine = t('member.military');
  else if (m.available === 'by_invitation_only') membershipLine = t('member.invitation');
  else if (m.available === 'members_only') membershipLine = t('member.membersOnly');
  else if (m.available === false) membershipLine = t('common.none');

  const matoaTag = c.id === 'matoa-nasional' ? ' <span class="matoa-tag">★</span>' : '';
  const mapsUrl = googleMapsPlaceUrl(c);
  const websiteLink = c.website ? `<a href="${escapeHtml(c.website)}" target="_blank" rel="noopener">${t('popup.officialWeb')}</a>` : '';
  const mapsLink = `<a href="${mapsUrl}" target="_blank" rel="noopener">${t('popup.googleMap')}</a>`;
  const yearText = c.year_opened ? `${c.year_opened}${t('common.year') ? t('common.year') : ''}` : '—';

  const rows = [
    [t('popup.region'), `${escapeHtml(c.region || '—')}, ${escapeHtml(c.province || '—')}`],
    [t('popup.operating'), `<span class="popup-status ${status}">${statusLabel}</span>`],
    [t('popup.holesPar'), `${c.holes ?? '—'}${t('common.holesUnit')}${c.par ? ` · Par ${c.par}` : ''}`],
    [t('popup.opened'), yearText],
    [t('popup.designer'), designer || '—'],
    [t('popup.weekdayWeekend'), `${fmtFee(wd, wdUSD)} / ${fmtFee(we, weUSD)}`],
    membershipLine ? [t('popup.membership'), membershipLine] : null,
  ].filter(Boolean);

  return `
    <div class="marker-popup">
      <div class="popup-name">${escapeHtml(c.name_en)}${matoaTag}</div>
      ${c.address ? `<div class="popup-addr">${escapeHtml(c.address)}</div>` : ''}
      <table class="popup-table">${rows.map(([k, v]) => `<tr><th>${k}</th><td>${v}</td></tr>`).join('')}</table>
      <div class="popup-links">${[websiteLink, mapsLink].filter(Boolean).join(' · ')}</div>
      <button class="popup-detail-btn" data-detail-id="${escapeHtml(c.id)}">${t('popup.detailBtn')}</button>
    </div>
  `;
}

function getMarkerStatusClass(c) {
  const s = c.operating_status?.status || 'operating';
  if (s === 'closed_temporary' || s === 'closed_permanent') return 'status-closed';
  if (s === 'uncertain') return 'status-uncertain';
  return 'status-operating';
}

function getMarkerSizeClass(c) {
  const h = c.holes;
  if (h == null) return 'size-md';
  if (h <= 9) return 'size-sm';
  if (h <= 18) return 'size-md';
  return 'size-lg';
}

const MARKER_DIMS = {
  'size-sm': { size: 22, anchor: [11, 22] },
  'size-md': { size: 28, anchor: [14, 28] },
  'size-lg': { size: 36, anchor: [18, 36] },
};

function renderMarkers() {
  markerCluster.clearLayers();
  markers = {};

  filteredCourses.forEach(c => {
    const isMatoa = c.id === 'matoa-nasional';
    const statusClass = getMarkerStatusClass(c);
    const sizeClass = getMarkerSizeClass(c);
    const dim = MARKER_DIMS[sizeClass];

    const icon = L.divIcon({
      className: '',
      html: `<div class="golf-marker ${statusClass} ${sizeClass}${isMatoa ? ' matoa' : ''}"></div>`,
      iconSize: [dim.size, dim.size],
      iconAnchor: dim.anchor,
      popupAnchor: [0, -dim.size],
    });

    const marker = L.marker([c.lat, c.lng], { icon })
      .bindTooltip(c.name_en, { direction: 'top', offset: [0, -dim.size + 4] })
      .bindPopup(buildMarkerPopupHtml(c), { minWidth: 280, maxWidth: 320, className: 'course-popup' });

    markers[c.id] = marker;
    markerCluster.addLayer(marker);
  });
}

// === Map Controls: Legend + Zoom Presets ===
const ZOOM_PRESETS = [
  { key: 'all',         labelKey: 'map.zoomAll', bounds: [[-10.5, 95], [6, 141]] },
  { key: 'jabodetabek', label: 'Jabodetabek',    bounds: [[-6.7, 106.3], [-6.0, 107.3]] },
  { key: 'balikpapan',  label: 'Balikpapan',     bounds: [[-1.45, 116.6], [-1.0, 117.1]] },
  { key: 'bali',        label: 'Bali',           bounds: [[-8.85, 114.4], [-8.05, 115.7]] },
];

let _legendEl = null;
let _zoomPresetsEl = null;

function _renderLegendInner() {
  if (!_legendEl) return;
  _legendEl.innerHTML = `
      <div class="legend-title">${t('map.legendStatus')}</div>
      <div class="legend-row"><span class="legend-swatch op"></span>${t('status.operating')}</div>
      <div class="legend-row"><span class="legend-swatch cl"></span>${t('status.closed')}</div>
      <div class="legend-row"><span class="legend-swatch un"></span>${t('status.uncertain')}</div>
      <div class="legend-title">${t('map.legendHoles')}</div>
      <div class="legend-row"><span class="legend-size sm"></span>${t('map.legend9')}</div>
      <div class="legend-row"><span class="legend-size md"></span>${t('map.legend18')}</div>
      <div class="legend-row"><span class="legend-size lg"></span>${t('map.legend27')}</div>
    `;
}

function _renderZoomPresetsInner() {
  if (!_zoomPresetsEl) return;
  const activeKey = _zoomPresetsEl.querySelector('button.active')?.dataset.preset || 'all';
  _zoomPresetsEl.innerHTML = ZOOM_PRESETS.map(p => {
    const label = p.labelKey ? t(p.labelKey) : p.label;
    return `<button data-preset="${p.key}"${p.key === activeKey ? ' class="active"' : ''}>${label}</button>`;
  }).join('');
}

function _refreshMapControls() {
  _renderLegendInner();
  _renderZoomPresetsInner();
}

function addLegendControl() {
  const ctrl = L.control({ position: 'bottomright' });
  ctrl.onAdd = function () {
    const el = L.DomUtil.create('div', 'map-legend');
    _legendEl = el;
    _renderLegendInner();
    L.DomEvent.disableClickPropagation(el);
    L.DomEvent.disableScrollPropagation(el);
    return el;
  };
  ctrl.addTo(map);
}

function addZoomPresetsControl() {
  const ctrl = L.control({ position: 'topright' });
  ctrl.onAdd = function () {
    const el = L.DomUtil.create('div', 'zoom-presets');
    _zoomPresetsEl = el;
    _renderZoomPresetsInner();
    L.DomEvent.disableClickPropagation(el);
    L.DomEvent.disableScrollPropagation(el);
    el.addEventListener('click', e => {
      const btn = e.target.closest('button');
      if (!btn) return;
      const preset = ZOOM_PRESETS.find(p => p.key === btn.dataset.preset);
      if (!preset) return;
      el.querySelectorAll('button').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      map.flyToBounds(preset.bounds, { padding: [40, 40], duration: 0.6 });
    });
    return el;
  };
  ctrl.addTo(map);
}

// === Course List ===
function renderCourseListSkeleton() {
  const list = document.getElementById('courseList');
  if (!list) return;
  const items = Array.from({ length: 8 }, () =>
    `<div class="skeleton-item">
      <div class="skeleton-line" style="width:70%"></div>
      <div class="skeleton-line short"></div>
      <div class="skeleton-line tiny"></div>
    </div>`).join('');
  list.innerHTML = `<div class="skeleton-list">${items}</div>`;
}

function renderCourseList() {
  const list = document.getElementById('courseList');
  list.innerHTML = '';

  if (filteredCourses.length === 0) {
    list.innerHTML = `<div class="empty-state">
      <div class="empty-emoji">🔍</div>
      <div class="empty-title">${t('empty.title')}</div>
      <div class="empty-hint">${t('empty.hint')}</div>
      <button class="empty-cta" id="emptyResetBtn" type="button">${t('empty.cta')}</button>
    </div>`;
    document.getElementById('emptyResetBtn')?.addEventListener('click', () => {
      document.getElementById('filterResetBtn')?.click();
    });
    return;
  }

  // Sort: by name (ascending)
  const sorted = [...filteredCourses].sort((a, b) =>
    a.name_en.localeCompare(b.name_en));

  sorted.forEach(c => {
    const item = document.createElement('div');
    item.className = 'course-item';
    item.dataset.id = c.id;

    const holesText = c.holes ? `${c.holes}${t('common.holesUnit')}` : '';
    const parText = c.par ? `Par ${c.par}` : '';
    const designerBadge = c.designer ? `<span class="badge">${escapeHtml(c.designer.split(',')[0].trim().split('(')[0].trim())}</span>` : '';

    // Fee preview (weekday green fee)
    const f = c.fees_2026_05;
    let feePreview = '';
    if (f && f.weekday) {
      const wd = f.weekday.green_fee_idr ?? f.weekday.guest_fee_idr ?? f.weekday.member_fee_idr;
      if (wd != null) {
        feePreview = `<span class="fee-badge">${t('list.weekdayPrefix')} ${fmtIDR(wd)}~</span>`;
      } else if (f.weekday.green_fee_usd) {
        feePreview = `<span class="fee-badge">${t('list.weekdayPrefix')} ${fmtUSD(f.weekday.green_fee_usd)}~</span>`;
      }
    }

    // Status badge
    const status = c.operating_status?.status || 'operating';
    let statusBadge = '';
    if (status === 'closed_temporary') statusBadge = `<span class="status-badge closed">${t('status.closed')}</span>`;
    else if (status === 'uncertain') statusBadge = `<span class="status-badge uncertain">${t('status.uncertain')}</span>`;

    item.innerHTML = `
      <h4>${escapeHtml(c.name_en)} ${statusBadge}</h4>
      <div class="meta">
        <span>📍 ${escapeHtml(c.region)}</span>
        ${holesText ? `<span>⛳ ${holesText}</span>` : ''}
        ${parText ? `<span>${parText}</span>` : ''}
        ${designerBadge}
        ${feePreview}
      </div>
    `;

    item.addEventListener('click', () => {
      showDetail(c);
      map.flyTo([c.lat, c.lng], 13, { duration: 0.6 });
      const marker = markers[c.id];
      if (marker) {
        markerCluster.zoomToShowLayer(marker, () => marker.openTooltip());
      }
    });

    list.appendChild(item);
  });
}

// === Detail Panel ===
function showDetail(c) {
  document.querySelectorAll('.course-item').forEach(el => {
    el.classList.toggle('active', el.dataset.id === c.id);
  });

  const panel = document.getElementById('detailPanel');
  const content = document.getElementById('detailContent');

  const holesText = c.holes ? `${c.holes}${t('common.holesUnit')}` : '—';
  const parText = c.par != null ? c.par : '—';
  const yearText = c.year_opened || '—';

  const facilities = (c.facilities || []).map(f => `<li>${escapeHtml(f)}</li>`).join('');
  const approxTag = c.coord_approximate ? `<span class="approx-tag">${t('detail.coordApprox')}</span>` : '';
  const priceMatrixHtml = renderPriceMatrix(c);
  const sourceHistoryHtml = renderSourceHistory(c);
  const feesHtml = renderFees(c.fees_2026_05);
  const membershipHtml = renderMembership(c.membership);

  // Operating status banner + name-adjacent badge
  const opStatus = c.operating_status?.status || 'operating';
  const verifiedTitle = c.operating_status?.last_verified ? t('detail.verifiedDate', { date: c.operating_status.last_verified }) : '';
  const detailStatusBadge = `<span class="detail-status-badge ${opStatus}" title="${escapeHtml(verifiedTitle)}">${statusLabelOf(opStatus)}</span>`;
  let statusBanner = '';
  if (opStatus === 'closed_temporary' || opStatus === 'closed_permanent') {
    const reason = c.operating_status?.closure_reason || (opStatus === 'closed_permanent' ? t('status.reasonPerm') : t('status.reasonReno'));
    const reopened = c.operating_status?.reopened_as ? ` (${escapeHtml(c.operating_status.reopened_as)})` : '';
    statusBanner = `<div class="status-banner closed">${t('status.banner.closed', { label: statusLabelOf(opStatus), reason: escapeHtml(reason), reopened })}</div>`;
  } else if (opStatus === 'uncertain') {
    statusBanner = `<div class="status-banner uncertain">${t('status.banner.uncertain')}</div>`;
  }

  content.innerHTML = `
    <h2 class="name">${escapeHtml(c.name_en)} ${detailStatusBadge}${approxTag}</h2>
    <div class="region-line">${escapeHtml(c.region)} · ${escapeHtml(c.province)}</div>
    ${statusBanner}

    <div class="stats">
      <div class="stat">
        <div class="label">${t('detail.holes')}</div>
        <div class="value">${holesText}</div>
      </div>
      <div class="stat">
        <div class="label">${t('detail.par')}</div>
        <div class="value">${parText}</div>
      </div>
      <div class="stat">
        <div class="label">${t('detail.opened')}</div>
        <div class="value">${yearText}</div>
      </div>
    </div>

    ${c.address ? `
    <section>
      <h3>${t('detail.address')}</h3>
      <p>${escapeHtml(c.address)}</p>
      ${(c.operating_status?.coord_notes) ? `<details class="coord-notes-block"><summary>${t('detail.coordNotes')}</summary><p>${escapeHtml(c.operating_status.coord_notes)}</p></details>` : ''}
    </section>` : ''}

    ${renderOperatingEvidence(c)}

    ${c.designer ? `
    <section>
      <h3>${t('detail.designer')}</h3>
      <p>${escapeHtml(c.designer)}</p>
    </section>` : ''}

    ${c.course_layout ? `
    <section>
      <h3>${t('detail.layout')}</h3>
      <p>${escapeHtml(c.course_layout)}</p>
    </section>` : ''}

    ${priceMatrixHtml}
    ${sourceHistoryHtml}
    ${feesHtml}

    ${membershipHtml}

    ${renderFinancials(c.financials)}

    ${facilities ? `
    <section>
      <h3>${t('detail.facilities')}</h3>
      <ul class="facility-list">${facilities}</ul>
    </section>` : ''}

    ${c.notes ? `
    <section>
      <div class="notes">${escapeHtml(c.notes)}</div>
    </section>` : ''}

    ${c.website ? `
    <section>
      <a class="website-link" href="${escapeHtml(c.website)}" target="_blank" rel="noopener">${t('detail.officialWebLink')}</a>
    </section>` : ''}

    <section>
      <a class="website-link" style="background:#475569" href="${escapeHtml(googleMapsPlaceUrl(c))}" target="_blank" rel="noopener">${t('detail.googleMapOpen')}</a>
    </section>
  `;

  panel.classList.add('open');
  panel.setAttribute('aria-hidden', 'false');
  document.body.classList.add('detail-open');
}

document.getElementById('closeDetail').addEventListener('click', () => {
  const panel = document.getElementById('detailPanel');
  panel.classList.remove('open');
  panel.setAttribute('aria-hidden', 'true');
  document.body.classList.remove('detail-open');
  document.querySelectorAll('.course-item').forEach(el => el.classList.remove('active'));
});

// Wire up the "상세 정보" button inside marker popups
document.addEventListener('click', e => {
  const btn = e.target.closest('.popup-detail-btn');
  if (!btn) return;
  const id = btn.dataset.detailId;
  const c = allCourses.find(x => x.id === id);
  if (c) {
    showDetail(c);
    if (map) map.closePopup();
  }
});

// === Mobile sidebar toggle ===
document.getElementById('sidebarToggle').addEventListener('click', () => {
  document.getElementById('sidebar').classList.toggle('open');
});

// === Membership Rendering ===
function fmtMoney(amt, cur) {
  if (amt == null) return null;
  const c = (cur || 'IDR').toUpperCase();
  if (c === 'USD') return fmtK(amt, '$');
  if (c === 'SGD') return fmtK(amt, 'S$');
  if (c === 'IDR') return fmtIDR(amt);
  return fmtK(amt, '') + ' ' + c;
}

function renderMembership(m) {
  if (!m || typeof m !== 'object') return '';
  const avail = m.available;
  const cats = Array.isArray(m.categories) ? m.categories : [];

  const availLabel = membershipAvailLabel(avail) ?? t('common.unknown');

  // Build category rows
  const catRows = cats.map(cat => {
    if (!cat || typeof cat !== 'object') return '';
    const init = cat.initiation_fee || {};
    const ann = cat.annual_fee || {};
    const mon = cat.monthly_fee || {};
    const dep = cat.refundable_deposit || {};
    const initT = fmtMoney(init.amount, init.currency);
    const annT = fmtMoney(ann.amount, ann.currency);
    const monT = fmtMoney(mon.amount, mon.currency);
    const depT = fmtMoney(dep.amount, dep.currency);
    const term = cat.term_years ? `${cat.term_years}${t('common.year')}` : '';
    const detail = [
      initT ? `${t('member.initFee')} ${initT}` : null,
      annT ? `${t('member.annualFee')} ${annT}` : null,
      monT ? `${t('member.monthlyFee')} ${monT}` : null,
      depT ? `${t('member.deposit')} ${depT}` : null,
      term,
    ].filter(Boolean).join(' · ');
    if (!cat.name && !detail) return '';
    return `<tr>
      <td>${escapeHtml(cat.name || '—')}</td>
      <td>${detail || `<span class="muted">${t('common.private')}</span>`}</td>
    </tr>`;
  }).filter(Boolean).join('');

  const sources = (m.sources || []).filter(Boolean);
  const sourcesHtml = sources.length
    ? `<div class="fee-sources">${t('fee.sources')}: ${sources.slice(0, 4).map((u, i) =>
        `<a href="${escapeHtml(u)}" target="_blank" rel="noopener" title="${escapeHtml(u)}">[${i + 1}]</a>`
      ).join(' ')}</div>`
    : '';

  const notes = m.notes ? `<div class="fee-notes">${escapeHtml(m.notes)}</div>` : '';
  const verifiedDate = m.last_verified ? `<span class="verified-date">${t('detail.verifiedDate', { date: escapeHtml(m.last_verified) })}</span>` : '';

  if (catRows) {
    return `
      <section class="membership-section">
        <h3>${t('member.section')} <span class="member-status-pill ${avail}">${availLabel}</span> ${verifiedDate}</h3>
        <table class="member-table">
          <thead><tr><th>${t('member.grade')}</th><th>${t('member.cost')}</th></tr></thead>
          <tbody>${catRows}</tbody>
        </table>
        ${notes}
        ${sourcesHtml}
      </section>`;
  }

  // No priced categories — show status only
  return `
    <section class="membership-section minimal">
      <h3>${t('member.section')} <span class="member-status-pill ${avail}">${availLabel}</span></h3>
      ${notes || `<p class="muted">${t('member.noDataNote')}</p>`}
      ${sourcesHtml}
    </section>`;
}

// === Financials Rendering ===
function listedStatusLabel(status) {
  const map = {
    'listed': 'listed.listed',
    'subsidiary-of-listed': 'listed.subsidiary-of-listed',
    'private': 'listed.private',
    'state-owned': 'listed.state-owned',
    'government': 'listed.government',
    'local-government': 'listed.local-government',
    'military': 'listed.military',
    'foundation': 'listed.foundation',
    'joint-venture': 'listed.joint-venture',
    'plantation-soe': 'listed.plantation-soe',
    'tbk-reporting-not-yet-traded': 'listed.tbk-reporting-not-yet-traded',
    'subsidiary-of-state-owned (BUMN holding, unlisted)': 'listed.bumn-subsidiary',
    'unknown': 'listed.unknown',
  };
  return map[status] ? t(map[status]) : status;
}

const LISTED_STATUS_LABEL = new Proxy({}, {
  get(_, status) { return listedStatusLabel(status); },
});

function fmtBigIDR(n) {
  if (n == null) return null;
  const num = Number(n);
  if (!isFinite(num)) return null;
  const abs = Math.abs(num);
  if (abs >= 1e12) return `Rp ${(num / 1e12).toFixed(2).replace(/\.?0+$/, '')}T`;
  if (abs >= 1e9)  return `Rp ${(num / 1e9).toFixed(2).replace(/\.?0+$/, '')}B`;
  if (abs >= 1e6)  return `Rp ${(num / 1e6).toFixed(0)}M`;
  return `Rp ${num.toLocaleString('en-US')}`;
}

// Build a Yahoo Finance URL for an IDX or foreign ticker.
// Foreign tickers may come prefixed with an exchange code (e.g., "SGX:BN4",
// "TYO:7868") and may have parenthesized commentary appended.
function yahooFinanceUrl(rawTicker, isIDX) {
  if (!rawTicker) return null;
  const t = String(rawTicker).split('(')[0].trim();
  if (!t) return null;
  if (isIDX) {
    return `https://finance.yahoo.com/quote/${encodeURIComponent(t)}.JK`;
  }
  if (t.includes(':')) {
    const [prefix, codeRaw] = t.split(':').map(s => s.trim());
    const code = (codeRaw || '').split(/\s+/)[0];
    const SUFFIX = {
      SGX: '.SI', TYO: '.T', TSE: '.T', HKEX: '.HK', HKG: '.HK',
      KLSE: '.KL', BSE: '.BO', NSE: '.NS', LSE: '.L', ASX: '.AX',
      KRX: '.KS', KOSPI: '.KS', KOSDAQ: '.KQ',
      NYSE: '', NASDAQ: '', AMEX: '',
    };
    const suffix = SUFFIX[prefix.toUpperCase()];
    if (code && suffix !== undefined) {
      return `https://finance.yahoo.com/quote/${encodeURIComponent(code)}${suffix}`;
    }
  }
  return `https://finance.yahoo.com/quote/${encodeURIComponent(t.split(/\s+/)[0])}`;
}

function renderFinancials(fin) {
  if (!fin || typeof fin !== 'object') return '';

  const ticker = fin.idx_ticker || fin.foreign_ticker;
  const status = fin.listed_status || 'unknown';
  const statusLabel = listedStatusLabel(status);
  const parent = fin.parent_company_full_name || fin.parent_group;
  const op = fin.operating_company;

  const rows = [];
  if (op) rows.push([t('fin.opCompany'), escapeHtml(op)]);
  if (parent) rows.push([t('fin.parent'), escapeHtml(parent)]);
  if (ticker) {
    const cls = fin.idx_ticker ? 'idx' : 'foreign';
    const yhUrl = yahooFinanceUrl(ticker, !!fin.idx_ticker);
    const tickerHtml = yhUrl
      ? `<a class="ticker-pill ${cls} ticker-link" href="${escapeHtml(yhUrl)}" target="_blank" rel="noopener" title="${escapeHtml(t('finance.tickerOpen', { ticker }))}">${escapeHtml(ticker)} <span class="ticker-ext">↗</span></a>`
      : `<span class="ticker-pill ${cls}">${escapeHtml(ticker)}</span>`;
    rows.push([t('fin.ticker'), tickerHtml]);
  }
  rows.push([t('fin.listedStatus'), `<span class="listed-status ${escapeHtml(status)}">${escapeHtml(statusLabel)}</span>`]);

  // Revenue (full-year preferred, else H1)
  const rev = fin.revenue_idr;
  const revH1 = fin.revenue_idr_h1;
  const revYear = fin.revenue_year;
  if (rev != null) {
    rows.push([revYear ? t('fin.revenueWith', { year: escapeHtml(String(revYear)) }) : t('fin.revenue'), fmtBigIDR(rev)]);
  } else if (revH1 != null) {
    rows.push([t('fin.revenueH1', { year: escapeHtml(String(revYear || '2024')) }), fmtBigIDR(revH1)]);
  }
  if (fin.net_profit_idr != null) {
    const np = fin.net_profit_idr;
    const sign = np < 0 ? '<span class="neg">−</span>' : '';
    rows.push([t('fin.netProfit'), sign + fmtBigIDR(Math.abs(np))]);
  } else if (fin.net_profit_idr_h1 != null) {
    rows.push([t('fin.netProfitH1'), fmtBigIDR(fin.net_profit_idr_h1)]);
  }
  if (fin.total_assets_idr != null) rows.push([t('fin.totalAssets'), fmtBigIDR(fin.total_assets_idr)]);
  if (fin.employees != null) rows.push([t('fin.employees'), `${fin.employees.toLocaleString('en-US')}${t('common.peopleUnit')}`]);
  if (fin.investment_idr != null) rows.push([t('fin.investment'), fmtBigIDR(fin.investment_idr)]);
  if (fin.investment_usd != null) rows.push([t('fin.investmentUsd'), `$${fin.investment_usd.toLocaleString('en-US')}`]);

  if (fin.course_segment_disclosed === true && fin.course_segment_revenue_idr != null) {
    rows.push([t('fin.golfSegment'), `<span class="seg-disclosed">${fmtBigIDR(fin.course_segment_revenue_idr)}</span> <span class="muted">${t('fin.segDisclosedNote')}</span>`]);
  } else if (fin.course_segment_disclosed === true) {
    rows.push([t('fin.golfSegmentLabel'), `<span class="seg-disclosed">${t('fin.segDisclosed')}</span>`]);
  }

  // Membership pricing
  if (fin.membership_price_idr != null) {
    rows.push([t('fin.membership'), `${fmtBigIDR(fin.membership_price_idr)}`]);
  } else if (fin.membership_price_usd != null) {
    rows.push([t('fin.membership'), `$${fin.membership_price_usd.toLocaleString('en-US')}`]);
  }

  if (fin.figure_origin) {
    rows.push([t('fin.dataReliability'), `<span class="origin-pill">${escapeHtml(fin.figure_origin)}</span>`]);
  }

  if (fin.recent_news) {
    rows.push([t('fin.recentNews'), `<span class="news-line">${escapeHtml(fin.recent_news)}</span>`]);
  }

  // Notes
  let notesHtml = '';
  if (fin.membership_price_notes) notesHtml += `<div class="fin-note"><span class="note-label">${t('fin.memberNote')}</span> ${escapeHtml(fin.membership_price_notes)}</div>`;
  if (fin.ownership_notes) notesHtml += `<div class="fin-note"><span class="note-label">${t('fin.ownerNote')}</span> ${escapeHtml(fin.ownership_notes)}</div>`;

  // Sources — combine sources + parent_financial_sources + membership_sources
  const collectSources = () => {
    const items = [];
    const seenUrls = new Set();
    const addOne = (s, kind) => {
      if (typeof s === 'string') {
        if (seenUrls.has(s)) return;
        seenUrls.add(s);
        items.push({ url: s, title: null, publisher: null, date_published: null, kind });
        return;
      }
      if (s && typeof s === 'object' && s.url) {
        if (seenUrls.has(s.url)) return;
        seenUrls.add(s.url);
        items.push({
          url: s.url,
          title: s.title || null,
          publisher: s.publisher || null,
          date_published: s.date_published || null,
          date_accessed: s.date_accessed || null,
          kind
        });
      }
    };
    (fin.sources || []).forEach(s => addOne(s, 'general'));
    (fin.parent_financial_sources || []).forEach(s => addOne(s, 'parent'));
    (fin.membership_sources || []).forEach(s => addOne(s, 'membership'));
    return items;
  };
  const allSources = collectSources();

  let sourcesHtml = '';
  if (allSources.length) {
    const items = allSources.slice(0, 12).map((s, i) => {
      const kindBadge = s.kind === 'parent' ? `<span class="kind-pill parent">${t('fin.kindParent')}</span>`
        : s.kind === 'membership' ? `<span class="kind-pill membership">${t('fin.kindMember')}</span>`
        : '';
      const label = s.publisher || (() => {
        try { return new URL(s.url).hostname.replace(/^www\./, ''); }
        catch { return `[${i+1}]`; }
      })();
      const dateInfo = s.date_published ? ` <span class="src-date">${escapeHtml(s.date_published)}</span>` : '';
      const titleAttr = s.title ? `${s.title} — ${s.url}` : s.url;
      return `<a class="fin-src" href="${escapeHtml(s.url)}" target="_blank" rel="noopener" title="${escapeHtml(titleAttr)}">${kindBadge}${escapeHtml(label)}${dateInfo}</a>`;
    }).join(' ');
    sourcesHtml = `<div class="fin-sources">${t('fin.sources', { n: allSources.length })}: ${items}</div>`;
  }

  const verifiedDate = fin.last_verified ? `<span class="verified-date">${t('detail.verifiedDate', { date: escapeHtml(fin.last_verified) })}</span>` : '';

  return `
    <section class="financials-section">
      <h3>${t('fin.section')} ${verifiedDate}</h3>
      <table class="fin-table">${rows.map(([k, v]) => `<tr><th>${k}</th><td>${v}</td></tr>`).join('')}</table>
      ${notesHtml}
      ${sourcesHtml}
    </section>`;
}

// === Fee Rendering ===
function fmtK(n, prefix) {
  const num = Number(n);
  if (!isFinite(num)) return null;
  if (num === 0) return `${prefix}0K`;
  const inK = num / 1000;
  // Show 1 decimal if not a clean integer in K, otherwise no decimal
  const rounded = Math.abs(inK - Math.round(inK)) < 0.05 ? Math.round(inK) : Math.round(inK * 10) / 10;
  return `${prefix}${rounded.toLocaleString('en-US')}K`;
}
function fmtIDR(n) {
  if (n == null) return null;
  return fmtK(n, 'Rp ');
}
function fmtUSD(n) {
  if (n == null) return null;
  return fmtK(n, '$');
}

function renderFees(f) {
  if (!f) return '';

  const isObject = v => v && typeof v === 'object' && !Array.isArray(v);
  const wd = isObject(f.weekday) ? f.weekday : null;
  const we = isObject(f.weekend) ? f.weekend : null;
  const anc = isObject(f.ancillary) ? f.ancillary : {};

  const wdGreen = wd ? (wd.green_fee_idr ?? wd.guest_fee_idr ?? wd.member_fee_idr) : null;
  const weGreen = we ? (we.green_fee_idr ?? we.guest_fee_idr ?? we.member_fee_idr) : null;
  const wdUSD = wd ? wd.green_fee_usd : null;
  const weUSD = we ? we.green_fee_usd : null;

  // Coalesce ancillary from new schema (anc.*) or legacy top-level (f.*)
  const caddy = anc.caddy_idr ?? f.caddy_idr;
  const cart = anc.cart_idr ?? f.cart_idr;
  const insurance = anc.insurance_idr ?? f.insurance_idr;
  const taxPct = anc.tax_pct ?? f.tax_pct;
  const taxIncluded = anc.tax_included ?? f.tax_included;
  const rateIncludes = f.rate_includes;

  const fmtFee = v => (typeof v === 'number') ? fmtIDR(v) : (v ? String(v) : null);

  const hasAny = wdGreen != null || weGreen != null || wdUSD != null || weUSD != null
                 || caddy != null || cart != null || insurance != null
                 || f.twilight_idr != null || isObject(f.schedule_detailed);

  if (!hasAny && !f.notes) return '';

  const rows = [];
  if (wdGreen != null || wdUSD != null) {
    const idr = fmtIDR(wdGreen);
    const usd = fmtUSD(wdUSD);
    rows.push(`<tr><td>${t('fee.weekday')}</td><td class="amt">${[idr, usd].filter(Boolean).join(' / ') || '—'}</td></tr>`);
  }
  if (weGreen != null || weUSD != null) {
    const idr = fmtIDR(weGreen);
    const usd = fmtUSD(weUSD);
    rows.push(`<tr><td>${t('fee.weekend')}</td><td class="amt">${[idr, usd].filter(Boolean).join(' / ') || '—'}</td></tr>`);
  }
  if (f.twilight_idr != null) rows.push(`<tr><td>${t('fee.twilight')}</td><td class="amt">${fmtIDR(f.twilight_idr)}</td></tr>`);
  if (caddy != null) rows.push(`<tr><td>${t('fee.caddy')}</td><td class="amt">${fmtFee(caddy)}</td></tr>`);
  if (cart != null) rows.push(`<tr><td>${t('fee.cart')}</td><td class="amt">${fmtFee(cart)}</td></tr>`);
  if (insurance != null) rows.push(`<tr><td>${t('fee.insurance')}</td><td class="amt">${fmtFee(insurance)}</td></tr>`);
  if (taxPct != null) rows.push(`<tr><td>${t('fee.tax')}</td><td class="amt">${taxPct}%${taxIncluded ? ' ' + t('fee.taxIncluded') : ''}</td></tr>`);
  if (rateIncludes) rows.push(`<tr><td>${t('fee.rateIncludes')}</td><td class="amt note-cell">${escapeHtml(rateIncludes)}</td></tr>`);

  const detailed = f.schedule_detailed;
  let detailedHtml = '';
  if (isObject(detailed)) {
    const slotLabels = { weekday: t('slot.weekday'), weekend_saturday: t('slot.weekendSat'), weekend_sunday: t('slot.weekendSun'), public_holiday: t('slot.holiday') };
    const blocks = [];
    for (const [slot, slotLabel] of Object.entries(slotLabels)) {
      const slotData = detailed[slot];
      if (!isObject(slotData)) continue;
      const lines = [];
      const flatten = (obj, prefix = '') => {
        for (const [k, v] of Object.entries(obj)) {
          if (typeof v === 'number') {
            lines.push(`<li><span class="seg-key">${escapeHtml(prefix + k)}</span><span class="seg-val">${fmtIDR(v)}</span></li>`);
          } else if (typeof v === 'string') {
            lines.push(`<li><span class="seg-key">${escapeHtml(prefix + k)}</span><span class="seg-val">${escapeHtml(v)}</span></li>`);
          } else if (isObject(v)) {
            flatten(v, prefix ? `${prefix}${k} / ` : `${k} / `);
          }
        }
      };
      flatten(slotData);
      if (lines.length) blocks.push(`<div class="slot-block"><h4>${slotLabel}</h4><ul class="slot-list">${lines.join('')}</ul></div>`);
    }
    if (blocks.length) detailedHtml = `<details class="schedule-detailed"><summary>${t('fee.detailed')}</summary>${blocks.join('')}</details>`;
  }

  const sources = (f.sources || []).filter(Boolean);
  const idUrls = new Set((f.indonesian_sources || []).map(e => e?.url).filter(Boolean));
  const sourcesHtml = sources.length
    ? `<div class="fee-sources">${t('fee.sources')}: ${sources.slice(0, 8).map((u, i) => {
        const langTag = idUrls.has(u) ? '<span class="lang-tag">ID</span>' : '<span class="lang-tag en">EN</span>';
        return `<a href="${escapeHtml(u)}" target="_blank" rel="noopener" title="${escapeHtml(u)}">[${i + 1}]${langTag}</a>`;
      }).join(' ')}</div>`
    : '';

  const verifiedDate = f.last_verified ? `<span class="verified-date">${t('detail.verifiedDate', { date: escapeHtml(f.last_verified) })}</span>` : '';
  const basedOn = f.based_on ? `<div class="fee-warning">⚠ ${escapeHtml(f.based_on)}</div>` : '';
  const notes = f.notes ? `<div class="fee-notes">${escapeHtml(f.notes)}</div>` : '';
  const feeTitle = t('fee.title', { date: t('fee.dateMay') });

  if (rows.length === 0) {
    // Notes-only fee section (for closed courses or member-only)
    return `
      <section class="fees-section">
        <h3>${feeTitle} ${verifiedDate}</h3>
        ${basedOn}
        ${detailedHtml}
        ${notes}
        ${sourcesHtml}
      </section>`;
  }

  return `
    <section class="fees-section">
      <h3>${feeTitle} ${verifiedDate}</h3>
      ${basedOn}
      <table class="fee-table">${rows.join('')}</table>
      ${detailedHtml}
      ${notes}
      ${sourcesHtml}
    </section>`;
}

// === Helpers ===
function escapeHtml(s) {
  if (s == null) return '';
  return String(s)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

// === Tabs ===
let tableSort = { key: 'name_en', dir: 'asc' };

document.querySelectorAll('.tab').forEach(btn => {
  btn.addEventListener('click', () => {
    const target = btn.dataset.tab;
    document.querySelectorAll('.tab').forEach(b => {
      const active = b.dataset.tab === target;
      b.classList.toggle('active', active);
      b.setAttribute('aria-selected', active);
    });
    const mapView = document.getElementById('mapView');
    const tableView = document.getElementById('tableView');
    const financeView = document.getElementById('financeView');
    const analyticsView = document.getElementById('analyticsView');
    const showMap = target === 'map';
    const showTable = target === 'table';
    const showFinance = target === 'finance';
    const showAnalytics = target === 'analytics';

    mapView.hidden = !showMap;
    tableView.hidden = !showTable;
    if (financeView) financeView.hidden = !showFinance;
    if (analyticsView) analyticsView.hidden = !showAnalytics;
    mapView.style.display = showMap ? '' : 'none';
    tableView.style.display = showTable ? '' : 'none';
    if (financeView) financeView.style.display = showFinance ? '' : 'none';
    if (analyticsView) analyticsView.style.display = showAnalytics ? '' : 'none';

    if (showTable) {
      renderTable();
      if (!document.getElementById('tableRegionFilter').dataset.populated) {
        populateTableRegions();
      }
    }
    if (showFinance) renderFinanceTable();
    if (showAnalytics) renderAnalytics();
    if (showMap && map) setTimeout(() => map.invalidateSize(), 100);
  });
});

function populateTableRegions() {
  const sel = document.getElementById('tableRegionFilter');
  const regions = [...new Set(allCourses.map(c => c.region))].sort();
  regions.forEach(r => {
    const opt = document.createElement('option');
    opt.value = r;
    opt.textContent = r;
    sel.appendChild(opt);
  });
  sel.dataset.populated = '1';
}

document.getElementById('tableSearch').addEventListener('input', renderTable);
document.getElementById('tableStatusFilter').addEventListener('change', renderTable);
document.getElementById('tableRegionFilter').addEventListener('change', renderTable);

// Source-category sub-tab switching — re-renders the unified table with
// rates and sources scoped to the selected category.
document.querySelectorAll('.src-tab').forEach(btn => {
  btn.addEventListener('click', () => {
    const tab = btn.dataset.srcTab;
    if (!tab) return;
    currentSourceCat = tab;
    document.querySelectorAll('.src-tab').forEach(b => {
      const on = b === btn;
      b.classList.toggle('active', on);
      b.setAttribute('aria-selected', on ? 'true' : 'false');
    });
    renderTable();
  });
});

document.querySelectorAll('.course-table th[data-sort]').forEach(th => {
  th.addEventListener('click', () => {
    const key = th.dataset.sort;
    if (tableSort.key === key) {
      tableSort.dir = tableSort.dir === 'asc' ? 'desc' : 'asc';
    } else {
      tableSort.key = key;
      tableSort.dir = 'asc';
    }
    document.querySelectorAll('.course-table th').forEach(h => {
      h.classList.remove('sort-asc', 'sort-desc');
    });
    th.classList.add(tableSort.dir === 'asc' ? 'sort-asc' : 'sort-desc');
    renderTable();
  });
});

function getTableRows() {
  const search = (document.getElementById('tableSearch').value || '').trim().toLowerCase();
  const statusF = document.getElementById('tableStatusFilter').value;
  const regionF = document.getElementById('tableRegionFilter').value;

  let rows = allCourses.filter(c => {
    const status = c.operating_status?.status || 'operating';
    if (statusF === 'operating-only' && status !== 'operating') return false;
    if (statusF !== 'all' && statusF !== 'operating-only' && status !== statusF) return false;
    if (regionF !== 'all' && c.region !== regionF) return false;
    if (search) {
      const hay = [c.name_en, c.region, c.province, c.designer, c.address]
        .filter(Boolean).join(' ').toLowerCase();
      if (!hay.includes(search)) return false;
    }
    return true;
  });

  // Sort
  const k = tableSort.key;
  const dir = tableSort.dir === 'asc' ? 1 : -1;
  const slotMap = {
    weekday_am:    ['weekday', 'am'],
    weekday_pm:    ['weekday', 'pm'],
    saturday_am:   ['weekend_saturday', 'am'],
    saturday_pm:   ['weekend_saturday', 'pm'],
    sunday_am:     ['weekend_sunday', 'am'],
    sunday_pm:     ['weekend_sunday', 'pm'],
  };
  rows.sort((a, b) => {
    let va, vb;
    if (slotMap[k]) {
      const [slot, half] = slotMap[k];
      const fa = extractAmPm(a.fees_2026_05?.schedule_detailed?.[slot]);
      const fb = extractAmPm(b.fees_2026_05?.schedule_detailed?.[slot]);
      const fallbackA = slot === 'weekday' ? (a.fees_2026_05?.weekday?.green_fee_idr ?? a.fees_2026_05?.weekday?.guest_fee_idr) : (a.fees_2026_05?.weekend?.green_fee_idr ?? a.fees_2026_05?.weekend?.guest_fee_idr);
      const fallbackB = slot === 'weekday' ? (b.fees_2026_05?.weekday?.green_fee_idr ?? b.fees_2026_05?.weekday?.guest_fee_idr) : (b.fees_2026_05?.weekend?.green_fee_idr ?? b.fees_2026_05?.weekend?.guest_fee_idr);
      va = fa[half] ?? fallbackA ?? null;
      vb = fb[half] ?? fallbackB ?? null;
    } else if (k === 'weekday_fee') {
      va = a.fees_2026_05?.weekday?.green_fee_idr ?? a.fees_2026_05?.weekday?.guest_fee_idr ?? null;
      vb = b.fees_2026_05?.weekday?.green_fee_idr ?? b.fees_2026_05?.weekday?.guest_fee_idr ?? null;
    } else if (k === 'weekend_fee') {
      va = a.fees_2026_05?.weekend?.green_fee_idr ?? a.fees_2026_05?.weekend?.guest_fee_idr ?? null;
      vb = b.fees_2026_05?.weekend?.green_fee_idr ?? b.fees_2026_05?.weekend?.guest_fee_idr ?? null;
    } else if (k === 'membership_fee') {
      va = lowestMembershipFee(a.membership);
      vb = lowestMembershipFee(b.membership);
    } else if (k === 'membership_type') {
      const firstName = mm => {
        const cats = Array.isArray(mm?.categories) ? mm.categories.filter(c => c && c.name) : [];
        return cats.length ? cats[0].name : (mm?.available || '');
      };
      va = firstName(a.membership);
      vb = firstName(b.membership);
    } else if (k === 'status') {
      va = a.operating_status?.status || 'operating';
      vb = b.operating_status?.status || 'operating';
    } else if (k === 'parent_group') {
      va = a.financials?.parent_group || a.financials?.parent_company_full_name || '';
      vb = b.financials?.parent_group || b.financials?.parent_company_full_name || '';
    } else if (k === 'idx_ticker') {
      va = a.financials?.idx_ticker || a.financials?.foreign_ticker || '';
      vb = b.financials?.idx_ticker || b.financials?.foreign_ticker || '';
    } else if (k === 'parent_revenue') {
      va = a.financials?.revenue_idr ?? a.financials?.revenue_idr_h1 ?? null;
      vb = b.financials?.revenue_idr ?? b.financials?.revenue_idr_h1 ?? null;
    } else {
      va = a[k];
      vb = b[k];
    }
    if (va == null && vb == null) return 0;
    if (va == null) return 1;
    if (vb == null) return -1;
    if (typeof va === 'number' && typeof vb === 'number') return (va - vb) * dir;
    return String(va).localeCompare(String(vb), 'ko') * dir;
  });
  return rows;
}

function lowestMembershipFee(m) {
  if (!m || !Array.isArray(m.categories)) return null;
  let lowest = null;
  for (const cat of m.categories) {
    if (!cat || typeof cat !== 'object') continue;
    const init = (cat.initiation_fee || {});
    const ann = (cat.annual_fee || {});
    // Convert USD/SGD to approximate IDR for sorting (rough rates)
    const toIDR = (amt, cur) => {
      if (amt == null) return null;
      const c = (cur || 'IDR').toUpperCase();
      if (c === 'USD') return amt * 16200;
      if (c === 'SGD') return amt * 12000;
      return amt;
    };
    for (const v of [toIDR(init.amount, init.currency), toIDR(ann.amount, ann.currency)]) {
      if (v != null && (lowest == null || v < lowest)) lowest = v;
    }
  }
  return lowest;
}

function membershipCellText(m) {
  if (!m) return '—';
  const cats = Array.isArray(m.categories) ? m.categories : [];
  for (const cat of cats) {
    if (!cat) continue;
    const init = cat.initiation_fee || {};
    const ann = cat.annual_fee || {};
    if (init.amount != null) {
      return `<span class="member-amt">${t('member.cellInit', { amt: fmtMoney(init.amount, init.currency) })}</span>`;
    }
    if (ann.amount != null) {
      return `<span class="member-amt">${t('member.cellAnnual', { amt: fmtMoney(ann.amount, ann.currency) })}</span>`;
    }
  }
  const avail = m.available;
  const label = membershipAvailLabel(avail);
  if (label && avail !== 'unknown' && avail !== false) {
    return `<span class="member-status-pill ${avail}">${label}</span>`;
  }
  return `<span class="muted">${t('common.private')}</span>`;
}

function membershipTypeCell(m) {
  if (!m) return '<span class="muted">—</span>';
  const cats = Array.isArray(m.categories) ? m.categories.filter(c => c && typeof c === 'object') : [];
  if (cats.length) {
    const names = cats.map(c => c.name || '').filter(Boolean);
    if (names.length) {
      const visible = names.slice(0, 3).map(n => escapeHtml(n)).join(', ');
      const more = names.length > 3 ? ` <span class="muted">+${names.length - 3}</span>` : '';
      return `<span class="member-type-list" title="${escapeHtml(names.join(' · '))}">${visible}${more}</span>`;
    }
  }
  const avail = m.available;
  const label = membershipAvailLabel(avail);
  if (label && avail !== 'unknown' && avail !== false) {
    return `<span class="member-status-pill ${avail}">${label}</span>`;
  }
  return `<span class="muted">${t('common.private')}</span>`;
}

function membershipAmountCell(m) {
  if (!m) return '<span class="muted">—</span>';
  const cats = Array.isArray(m.categories) ? m.categories.filter(c => c && typeof c === 'object') : [];
  const parts = [];
  for (const cat of cats) {
    const init = cat.initiation_fee || {};
    const ann = cat.annual_fee || {};
    const mo = cat.monthly_fee || {};
    if (init.amount != null) parts.push(`<span class="member-amt">${t('member.cellInit', { amt: fmtMoney(init.amount, init.currency) })}</span>`);
    if (ann.amount != null) parts.push(`<span class="member-amt">${t('member.cellAnnual', { amt: fmtMoney(ann.amount, ann.currency) })}</span>`);
    if (mo.amount != null) parts.push(`<span class="member-amt">${t('member.cellMonthly', { amt: fmtMoney(mo.amount, mo.currency) })}</span>`);
    if (parts.length >= 3) break;
  }
  if (parts.length) return parts.slice(0, 3).join('<br>');
  return `<span class="muted">${t('common.private')}</span>`;
}

function extractAmPm(slotData) {
  if (!slotData || typeof slotData !== 'object') return { am: null, pm: null };
  const amVals = [], pmVals = [], allDayVals = [];
  const findNumeric = (obj) => {
    if (typeof obj === 'number') return [obj];
    if (!obj || typeof obj !== 'object' || Array.isArray(obj)) return [];
    const out = [];
    for (const k of ['visitor', 'visitor_18h', 'visitor_min', 'visitor_max', 'green_fee_idr', 'guest_fee_idr', 'all_inclusive']) {
      if (typeof obj[k] === 'number') out.push(obj[k]);
    }
    if (out.length) return out;
    for (const [k, v] of Object.entries(obj)) {
      if (k.toLowerCase().includes('visitor') && typeof v === 'number') out.push(v);
    }
    if (out.length) return out;
    for (const v of Object.values(obj)) {
      if (typeof v === 'number') out.push(v);
    }
    return out;
  };
  const walk = (obj, depth = 0) => {
    if (depth > 5 || !obj || typeof obj !== 'object' || Array.isArray(obj)) return;
    for (const [k, v] of Object.entries(obj)) {
      const lk = k.toLowerCase();
      const isAm = lk.includes('morning') || lk.endsWith('_am') || lk === 'am';
      const isPm = lk.includes('afternoon') || lk.endsWith('_pm') || lk === 'pm' || lk.includes('twilight') || lk.includes('sunset');
      const isAllDay = lk.includes('all_day');
      if (isAm) amVals.push(...findNumeric(v));
      else if (isPm) pmVals.push(...findNumeric(v));
      else if (isAllDay) allDayVals.push(...findNumeric(v));
      else if (v && typeof v === 'object' && !Array.isArray(v)) walk(v, depth + 1);
      else if (typeof v === 'number') allDayVals.push(v);
    }
  };
  walk(slotData);
  const max = arr => arr.length ? Math.max(...arr) : null;
  const allDay = max(allDayVals);
  return {
    am: max(amVals) ?? allDay,
    pm: max(pmVals) ?? allDay,
  };
}

function flattenSlotToLines(slot) {
  if (!slot || typeof slot !== 'object') return [];
  const lines = [];
  const walk = (obj, prefix = '') => {
    for (const [k, v] of Object.entries(obj)) {
      const label = prefix ? `${prefix} / ${k}` : k;
      if (typeof v === 'number') {
        lines.push({ label, val: fmtIDR(v) });
      } else if (typeof v === 'string') {
        lines.push({ label, val: v });
      } else if (typeof v === 'boolean') {
        lines.push({ label, val: v ? '✓' : '✗' });
      } else if (v && typeof v === 'object' && !Array.isArray(v)) {
        walk(v, label);
      }
    }
  };
  walk(slot);
  return lines;
}

function renderRateCell(slots, fallbackIdr, fallbackUsd) {
  // slots: array of [label, slotData] tuples
  const lines = [];
  for (const [hdr, data] of slots) {
    const slotLines = flattenSlotToLines(data);
    if (!slotLines.length) continue;
    if (hdr) lines.push(`<div class="fee-line-hdr">${hdr}</div>`);
    for (const ln of slotLines) {
      lines.push(`<div class="fee-line"><span class="fee-key">${escapeHtml(ln.label)}</span><span class="fee-val">${escapeHtml(ln.val)}</span></div>`);
    }
  }
  if (lines.length) return lines.join('');
  if (fallbackIdr) return `<div class="fee-val-only">${fmtIDR(fallbackIdr)}</div>`;
  if (fallbackUsd) return `<div class="fee-val-only">${fmtUSD(fallbackUsd)}</div>`;
  return '—';
}

// === Source labeler (categorize URL → human label + kind for color) ===
function getHostname(url) {
  try { return new URL(url).hostname.replace(/^www\./, '').toLowerCase(); }
  catch (e) { return null; }
}
function labelSource(url, courseWebsite) {
  const host = getHostname(url) || url;
  // Official site match
  if (courseWebsite) {
    const wh = getHostname(courseWebsite);
    if (wh && (host === wh || host.endsWith('.' + wh) || wh.endsWith('.' + host))) {
      return { label: t('src.official'), kind: 'official', host, url };
    }
  }
  if (host.includes('qaccess.asia')) return { label: 'Q-Access', kind: 'qaccess', host, url };
  if (host.includes('gogolf')) return { label: 'GoGolf', kind: 'gogolf', host, url };
  if (host.includes('playgolf')) return { label: 'playgolf.id', kind: 'playgolf', host, url };
  if (host.includes('golfsavers')) return { label: 'GolfSavers', kind: 'aggregator', host, url };
  if (host.includes('golfasian')) return { label: 'GolfAsian', kind: 'aggregator', host, url };
  if (host.includes('golfpass')) return { label: 'GolfPass', kind: 'aggregator', host, url };
  if (host.includes('golflux')) return { label: 'GolfLux', kind: 'aggregator', host, url };
  if (host.includes('hole19')) return { label: 'Hole19', kind: 'aggregator', host, url };
  if (host.includes('greenfee365')) return { label: 'GreenFee365', kind: 'aggregator', host, url };
  if (host.includes('golfshake')) return { label: 'Golfshake', kind: 'aggregator', host, url };
  if (host.includes('klook') || host.includes('traveloka') || host.includes('agoda') || host.includes('tiket.com') || host.includes('trip.com')) return { label: t('src.reservation'), kind: 'booking', host, url };
  if (host.includes('facebook') || host === 'fb.com' || host.includes('instagram') || host.includes('twitter') || host === 'x.com' || host.includes('tiktok') || host.includes('threads')) return { label: t('src.sns'), kind: 'sns', host, url };
  if (host.includes('idnfinancials') || host.includes('kontan') || host.includes('bisnis') || host.includes('kompas') || host.includes('detik') || host.includes('tempo.co') || host.includes('tribun') || host.includes('liputan6') || host.includes('voi.id') || host.includes('cnbcindonesia') || host.includes('jawapos') || host.includes('suaramerdeka') || host.includes('antaranews') || host.includes('golftimes') || host.includes('obgolf') || host.includes('xplorewisata') || host.includes('antorij')) return { label: t('src.news'), kind: 'news', host, url };
  if (host.includes('idx.co.id') || host.includes('ojk.go.id') || host.includes('sec.gov') || host.includes('sgx.com')) return { label: t('src.disclosure'), kind: 'official', host, url };
  if (host.includes('archive.org') || host.includes('wayback')) return { label: 'Wayback', kind: 'archive', host, url };
  if (host.includes('tni-au.mil') || host.includes('tniad') || host.includes('tnial') || host.endsWith('.mil.id') || host.endsWith('.go.id')) return { label: t('src.gov'), kind: 'gov', host, url };
  return { label: host, kind: 'other', host, url };
}

// === Source-tab category mapping ===
// Maps labelSource kind → tab key. 'gov' is grouped under official (1차 출처).
const SRC_TAB_OF_KIND = {
  official: 'official',
  gov: 'official',
  sns: 'sns',
  qaccess: 'platform',
  gogolf: 'platform',
  playgolf: 'platform',
  aggregator: 'aggregator',
  news: 'news',
  booking: 'news',
  archive: 'news',
  other: 'news',
};

function collectCategorizedSources(c) {
  // Returns { official: [info...], sns: [...], platform: [...], aggregator: [...], news: [...] }
  const buckets = { official: [], sns: [], platform: [], aggregator: [], news: [] };
  const seen = new Map(); // key: tab + '|' + host → bool

  const f = c.fees_2026_05 || {};
  const m = c.membership || {};
  const opEv = (c.operating_status?.evidence || []).filter(s => typeof s === 'string' && /^https?:/.test(s));

  const allUrls = []
    .concat(c.website ? [c.website] : [])
    .concat(f.sources || [])
    .concat(m.sources || [])
    .concat(opEv);
  if (c.fees_gogolf_reference?.source_url) allUrls.push(c.fees_gogolf_reference.source_url);

  for (const u of allUrls) {
    if (typeof u !== 'string' || !/^https?:/.test(u)) continue;
    const info = labelSource(u, c.website);
    const tab = SRC_TAB_OF_KIND[info.kind] || 'news';
    const key = tab + '|' + info.host;
    if (seen.has(key)) continue;
    seen.set(key, true);
    buckets[tab].push(info);
  }
  return buckets;
}

// === Multi-source price collection ===
// For each time slot (wdAm, wdPm, satAm, satPm, sunAm, sunPm), assemble all
// candidate (price, source-info) tuples we can find across fees_2026_05 (primary,
// often official/Q-Access) and fees_gogolf_reference (gogolf.co.id).
const SLOT_KEYS = ['wdAm', 'wdPm', 'satAm', 'satPm', 'sunAm', 'sunPm'];
const SLOT_LABEL = new Proxy({}, {
  get(_, key) {
    return t('slot.' + key);
  },
});

function _firstNumber(obj, keys) {
  if (typeof obj === 'number') return obj;
  if (!obj || typeof obj !== 'object') return null;
  for (const k of keys) if (typeof obj[k] === 'number') return obj[k];
  for (const v of Object.values(obj)) if (typeof v === 'number') return v;
  return null;
}

function getPrimaryRates(c) {
  const f = c.fees_2026_05 || {};
  const sd = f.schedule_detailed || {};
  const wd = extractAmPm(sd.weekday);
  const sat = extractAmPm(sd.weekend_saturday);
  const sun = extractAmPm(sd.weekend_sunday);
  const out = {
    wdAm: wd.am, wdPm: wd.pm,
    satAm: sat.am, satPm: sat.pm,
    sunAm: sun.am, sunPm: sun.pm,
  };
  // Fallbacks from coarse weekday/weekend aggregates if AM/PM missing.
  const wdFb = f.weekday?.green_fee_idr ?? f.weekday?.guest_fee_idr ?? null;
  const weFb = f.weekend?.green_fee_idr ?? f.weekend?.guest_fee_idr ?? null;
  if (out.wdAm == null && out.wdPm == null && wdFb != null) {
    out.wdAm = out.wdPm = wdFb;
  }
  if (out.satAm == null && out.satPm == null && weFb != null) {
    out.satAm = out.satPm = weFb;
  }
  if (out.sunAm == null && out.sunPm == null && weFb != null) {
    out.sunAm = out.sunPm = weFb;
  }
  return out;
}

function getGoGolfRates(c) {
  const sch = c.fees_gogolf_reference?.schedule;
  if (!sch) return null;
  return {
    wdAm: sch.weekday?.am ?? null,
    wdPm: sch.weekday?.pm ?? null,
    satAm: sch.saturday?.am ?? null,
    satPm: sch.saturday?.pm ?? null,
    sunAm: sch.sunday?.am ?? null,
    sunPm: sch.sunday?.pm ?? null,
  };
}

// Categorize a primary fee source URL into one of: official|platform|aggregator|sns|news.
function primarySourceCategory(c) {
  const f = c.fees_2026_05 || {};
  const urls = (f.sources || []).filter(u => typeof u === 'string' && /^https?:/.test(u));
  if (urls.length === 0) return { kind: 'official', label: t('src.official'), host: '' };
  // Use the first URL as the dominant primary source. Map to a 5-bucket category.
  const info = labelSource(urls[0], c.website);
  const cat = SRC_TAB_OF_KIND[info.kind] || 'news';
  return { kind: cat, label: info.label, host: info.host, url: urls[0],
           date: f.last_verified || null };
}

function gogolfSourceInfo(c) {
  const gg = c.fees_gogolf_reference;
  if (!gg) return null;
  const url = gg.source_url || '';
  const host = url ? (getHostname(url) || '') : 'gogolf.co.id';
  return { kind: 'platform', label: 'GoGolf', host, url, date: gg.last_verified || null };
}

// For a single slot, return all (price, srcInfo) candidates.
// Sources combine, in order:
//   1. fees_2026_05 primary rates (legacy / hand-curated)
//   2. fees_gogolf_reference (legacy / curated)
//   3. fees_2026_05.source_details — populated by the crawl pipeline (v3+),
//      one entry per (source_url × slot) after per-URL median collapse.
function getSlotCandidates(c, slot) {
  const out = [];
  const seenUrls = new Set();

  const pri = getPrimaryRates(c);
  const priInfo = primarySourceCategory(c);
  if (pri[slot] != null) {
    out.push({ price: pri[slot], src: priInfo, origin: 'primary' });
    if (priInfo.url) seenUrls.add(priInfo.url);
  }
  const gg = getGoGolfRates(c);
  const ggInfo = gogolfSourceInfo(c);
  if (gg && gg[slot] != null && ggInfo) {
    out.push({ price: gg[slot], src: ggInfo, origin: 'gogolf' });
    if (ggInfo.url) seenUrls.add(ggInfo.url);
  }

  // Crawled candidates from source_details — one row per source URL
  const sd = (c.fees_2026_05 || {}).source_details || [];
  for (const d of sd) {
    if (!d || d.slot !== slot) continue;
    const url = d.source_url;
    if (!url || seenUrls.has(url)) continue;
    seenUrls.add(url);
    const info = labelSource(url, c.website);
    const cat = SRC_TAB_OF_KIND[info.kind] || 'news';
    out.push({
      price: d.value_idr,
      src: {
        kind: cat,
        label: d.publisher || info.label,
        host: info.host,
        url,
        date: (d.fetched_at || '').slice(0, 10) || null,
      },
      origin: 'crawled',
      n_collapsed: d.n_collapsed_at_url || null,
      from_pdf: !!d.from_pdf,
      tier: d.tier,
    });
  }

  return out;
}

// Build a fee cell HTML for a single slot, given the active source-tab category.
function renderFeeCell(c, slot, cat) {
  const cands = getSlotCandidates(c, slot);
  if (cands.length === 0) return `<td class="num fee fee-cell"><span class="muted">—</span></td>`;

  // Filter by category when a specific tab is active. "all" shows everything.
  let visible = cands;
  let dimmed = false;
  if (cat !== 'all') {
    visible = cands.filter(x => x.src.kind === cat);
    if (visible.length === 0) {
      dimmed = true;
      visible = cands; // show grayed-out fallback so user knows price exists in another source
    }
  }

  // Pick "primary" candidate to display (prefer trust order: official > platform > aggregator > sns > news).
  const TRUST = { official: 0, platform: 1, aggregator: 2, sns: 3, news: 4 };
  const sorted = [...visible].sort((a, b) => (TRUST[a.src.kind] ?? 9) - (TRUST[b.src.kind] ?? 9));
  const primary = sorted[0];

  const prices = visible.map(x => x.price);
  const lo = Math.min(...prices);
  const hi = Math.max(...prices);
  const diffPct = lo > 0 ? ((hi - lo) / lo) * 100 : 0;
  const showRange = (cat === 'all') && visible.length > 1 && diffPct >= 1;
  const showWarn  = visible.length > 1 && diffPct >= 30;

  let priceHtml;
  if (showRange) {
    priceHtml = `<span class="fee-range"><span class="fee-range-pri">${fmtIDR(lo)} ~ ${fmtIDR(hi)}</span></span>`;
  } else {
    priceHtml = fmtIDR(primary.price);
  }
  const dimClass = dimmed ? ' dim' : '';
  const premiumClass = (slot === 'satAm' || slot === 'sunAm') ? ' fee-premium' : '';
  const ariaLabel = `${SLOT_LABEL[slot]} ${fmtIDR(primary.price)} — ${t('fee.sources')} ${primary.src.label}${visible.length > 1 ? `, +${visible.length - 1}` : ''}`;
  return `<td class="num fee fee-cell${dimClass}${premiumClass}" data-fee-cell="${slot}" data-course-id="${escapeHtml(c.id)}" tabindex="0" role="button" aria-label="${escapeHtml(ariaLabel)}">${priceHtml}</td>`;
}

// === Detail-panel: operating-status evidence ===
function renderOperatingEvidence(c) {
  const op = c.operating_status || {};
  const ev = (op.evidence || []).filter(Boolean);
  if (!ev.length && !op.last_verified) return '';
  const verified = op.last_verified
    ? `<span class="verified-date">${t('detail.verifiedDate', { date: escapeHtml(op.last_verified) })}</span>`
    : '';
  const confLabel = { high: t('conf.high'), medium: t('conf.medium'), low: t('conf.low') };
  const confBadge = op.confidence
    ? `<span class="conf-badge ${escapeHtml(op.confidence)}">${confLabel[op.confidence] || op.confidence}</span>`
    : '';
  const items = ev.map(e => {
    const isUrl = typeof e === 'string' && /^https?:/.test(e);
    if (isUrl) {
      let host = '';
      try { host = new URL(e).hostname.replace(/^www\./, ''); } catch (_) {}
      return `<li><a href="${escapeHtml(e)}" target="_blank" rel="noopener">${escapeHtml(host || e)} ↗</a></li>`;
    }
    // Mixed text — extract any URL inside it
    const m = String(e).match(/(https?:\/\/\S+)/);
    if (m) {
      const txt = String(e).replace(m[1], '').trim();
      return `<li>${escapeHtml(txt)} <a href="${escapeHtml(m[1])}" target="_blank" rel="noopener">↗</a></li>`;
    }
    return `<li>${escapeHtml(String(e))}</li>`;
  }).join('');
  return `<section class="evidence-section">
    <h3>${t('evidence.title')} ${confBadge} ${verified}</h3>
    <ul class="evidence-list">${items || `<li class="muted">${t('evidence.none')}</li>`}</ul>
  </section>`;
}

// === Detail-panel: price matrix (요일 × AM/PM) ===
function renderPriceMatrix(c) {
  const cells = {};
  let anyValue = false;
  for (const slot of SLOT_KEYS) {
    const cands = getSlotCandidates(c, slot);
    if (cands.length === 0) {
      cells[slot] = { html: '<span class="muted">—</span>', count: 0 };
      continue;
    }
    anyValue = true;
    const TRUST = { official: 0, platform: 1, aggregator: 2, sns: 3, news: 4 };
    const sorted = [...cands].sort((a, b) => (TRUST[a.src.kind] ?? 9) - (TRUST[b.src.kind] ?? 9));
    const primary = sorted[0];
    const prices = cands.map(x => x.price);
    const lo = Math.min(...prices);
    const hi = Math.max(...prices);
    const diffPct = lo > 0 ? ((hi - lo) / lo) * 100 : 0;
    const showRange = cands.length > 1 && diffPct >= 1;
    const warn = diffPct >= 30 ? ' <span class="price-warn" title="출처별 ±' + diffPct.toFixed(0) + '%">⚠️</span>' : '';
    const valHtml = showRange
      ? `${fmtIDR(lo)} ~ ${fmtIDR(hi)}`
      : fmtIDR(primary.price);
    cells[slot] = {
      html: `<button class="matrix-cell-btn" type="button" data-fee-cell="${slot}" data-course-id="${escapeHtml(c.id)}">${valHtml}${warn}</button>`,
      count: cands.length,
    };
  }
  if (!anyValue) return '';
  const r = (label, am, pm) => `<tr><th>${label}</th><td>${cells[am].html}</td><td>${cells[pm].html}</td></tr>`;
  return `<section class="price-matrix-section">
    <h3>${t('matrix.title')} <span class="matrix-hint">${t('matrix.hint')}</span></h3>
    <table class="price-matrix">
      <thead><tr><th></th><th>AM</th><th>PM</th></tr></thead>
      <tbody>
        ${r(t('matrix.weekday'), 'wdAm', 'wdPm')}
        ${r(t('matrix.sat'), 'satAm', 'satPm')}
        ${r(t('matrix.sun'), 'sunAm', 'sunPm')}
      </tbody>
    </table>
  </section>`;
}

// === Detail-panel: source-by-source price history ===
function renderSourceHistory(c) {
  // Group by source category. For each source, show what slots & prices it provides.
  const groups = { official: [], platform: [], aggregator: [], sns: [], news: [] };

  // Primary source (fees_2026_05) — represented as a single entry covering all slots present.
  const f = c.fees_2026_05 || {};
  const priInfo = primarySourceCategory(c);
  const priRates = getPrimaryRates(c);
  const priSlotPrices = SLOT_KEYS
    .filter(s => priRates[s] != null)
    .map(s => ({ slot: s, price: priRates[s] }));
  // Fingerprint slot prices so URLs in the same category that produce the
  // same rate set collapse into a single row (extras shown as compact links).
  const priSig = priSlotPrices.map(s => `${s.slot}:${s.price}`).join('|');
  const placedUrls = new Set();
  const fpKeyOf = (cat, sig) => `${cat}|${sig}`;
  const fingerprintIndex = new Map();
  if (priSlotPrices.length > 0) {
    const priUrl = priInfo.url || (f.sources || [])[0] || '';
    groups[priInfo.kind] ??= [];
    const priEntry = {
      label: priInfo.label || t('src.official'),
      url: priUrl,
      date: f.last_verified || null,
      slots: priSlotPrices,
      extraUrls: [],
    };
    groups[priInfo.kind].push(priEntry);
    if (priUrl) placedUrls.add(priUrl);
    fingerprintIndex.set(fpKeyOf(priInfo.kind, priSig), priEntry);

    // Other URLs in f.sources — fold into existing category-row when prices
    // match; otherwise create a new row for that category.
    const extra = (f.sources || []).slice(1).filter(u => typeof u === 'string' && /^https?:/.test(u));
    for (const u of extra) {
      if (placedUrls.has(u)) continue;
      placedUrls.add(u);
      const info = labelSource(u, c.website);
      const cat = SRC_TAB_OF_KIND[info.kind] || 'news';
      const fp = fpKeyOf(cat, priSig);
      const existing = fingerprintIndex.get(fp);
      if (existing) {
        existing.extraUrls.push({ label: info.label, url: u });
      } else {
        const entry = {
          label: info.label, url: u,
          date: f.last_verified || null,
          slots: priSlotPrices,
          extraUrls: [],
        };
        groups[cat] ??= [];
        groups[cat].push(entry);
        fingerprintIndex.set(fp, entry);
      }
    }
  }

  // GoGolf reference
  const gg = c.fees_gogolf_reference;
  if (gg && gg.schedule) {
    const ggInfo = gogolfSourceInfo(c);
    const ggRates = getGoGolfRates(c) || {};
    const ggSlotPrices = SLOT_KEYS
      .filter(s => ggRates[s] != null)
      .map(s => ({ slot: s, price: ggRates[s] }));
    if (ggSlotPrices.length > 0 && ggInfo) {
      groups.platform.push({
        label: ggInfo.label, url: ggInfo.url,
        date: ggInfo.date,
        slots: ggSlotPrices,
        confidence: gg.confidence,
        disclaimer: gg.disclaimer,
      });
    }
  }

  // Crawled candidates from source_details — group entries per source URL,
  // not per slot, so each URL becomes one history row spanning all slots
  // it provided values for.
  const sd = (f.source_details || []);
  if (sd.length) {
    const byUrl = new Map();
    const seenSrcUrls = new Set([
      priInfo.url || (f.sources || [])[0] || '',
      ...(f.sources || []),
      gg?.source_url || '',
    ].filter(Boolean));
    for (const d of sd) {
      if (!d || !d.source_url || !d.slot) continue;
      // Skip URLs already represented by primary or gogolf paths
      if (seenSrcUrls.has(d.source_url) && byUrl.has(d.source_url) === false) {
        // Still want to add slot-prices to existing group if any —
        // but those rows already get covered by primary loop. Skip.
        continue;
      }
      const key = d.source_url;
      if (!byUrl.has(key)) {
        const info = labelSource(d.source_url, c.website);
        byUrl.set(key, {
          label: d.publisher || info.label,
          url: d.source_url,
          host: info.host,
          kind: SRC_TAB_OF_KIND[info.kind] || 'news',
          date: (d.fetched_at || '').slice(0, 10) || null,
          tier: d.tier,
          from_pdf: !!d.from_pdf,
          n_collapsed: d.n_collapsed_at_url || null,
          slots: [],
          slotsSeen: new Set(),
          isCrawled: true,
        });
      }
      const g = byUrl.get(key);
      if (g.slotsSeen.has(d.slot)) continue;
      g.slotsSeen.add(d.slot);
      g.slots.push({ slot: d.slot, price: d.value_idr });
    }
    for (const g of byUrl.values()) {
      groups[g.kind] ??= [];
      groups[g.kind].push(g);
    }
  }

  const ORDER = ['official', 'platform', 'sns', 'aggregator', 'news'];
  const TITLE = ORDER.reduce((acc, k) => { acc[k] = t('srcCat.' + k); return acc; }, {});
  const allEmpty = ORDER.every(k => (groups[k] || []).length === 0);
  if (allEmpty) return '';

  const rowFor = (entry) => {
    const slotsHtml = entry.slots.map(s =>
      `<span class="hist-slot"><span class="hist-slot-key">${SLOT_LABEL[s.slot]}</span> <span class="hist-slot-val">${fmtIDR(s.price)}</span></span>`
    ).join('');
    const dateHtml = entry.date ? `<span class="hist-date">${escapeHtml(entry.date)}</span>` : '';
    const linkHtml = entry.url
      ? `<a class="hist-link" href="${escapeHtml(entry.url)}" target="_blank" rel="noopener">${t('history.original')}</a>`
      : '';
    const conf = entry.confidence === 'low' ? `<span class="hist-conf low">${t('history.refOnly')}</span>` : '';
    const crawledTag = entry.isCrawled
      ? `<span class="hist-crawled-tag" title="${escapeHtml(t('history.crawledTitle'))}">${t('history.crawled', { tier: entry.tier ?? '?', pdf: entry.from_pdf ? ' · PDF' : '' })}</span>`
      : '';
    const collapseTag = (entry.n_collapsed && entry.n_collapsed > 1)
      ? `<span class="hist-collapse-tag" title="${escapeHtml(t('history.collapseTitle', { n: entry.n_collapsed }))}">${t('history.collapseTag', { n: entry.n_collapsed })}</span>`
      : '';
    const extraUrlsHtml = (entry.extraUrls && entry.extraUrls.length)
      ? `<div class="hist-extra-sources" title="${escapeHtml(t('history.extraSrcTitle'))}">${t('history.extraSrc')}: ${entry.extraUrls.map(e => `<a href="${escapeHtml(e.url)}" target="_blank" rel="noopener" class="hist-extra-link">${escapeHtml(e.label)} ↗</a>`).join(' · ')}</div>`
      : '';
    return `<div class="hist-row${entry.isCrawled ? ' is-crawled' : ''}">
      <div class="hist-row-head"><span class="hist-label">${escapeHtml(entry.label)}</span>${conf}${crawledTag}${collapseTag}${dateHtml}${linkHtml}</div>
      <div class="hist-slots">${slotsHtml || '<span class="muted">—</span>'}</div>
      ${extraUrlsHtml}
    </div>`;
  };

  const groupHtml = ORDER.map(k => {
    const arr = groups[k] || [];
    if (arr.length === 0) return '';
    return `<div class="hist-group">
      <div class="hist-group-title"><span class="src-cat-pill k-${k}">${TITLE[k] || k}</span></div>
      <div class="hist-rows">${arr.map(rowFor).join('')}</div>
    </div>`;
  }).join('');

  return `<section class="source-history-section">
    <h3>${t('history.title')}</h3>
    <div class="hist-groups">${groupHtml}</div>
  </section>`;
}

// === Per-category rate provider ===
// Returns { wdAm, wdPm, satAm, satPm, sunAm, sunPm, note } where each is
// either a number (IDR) or null. The unified table rate columns swap
// based on the selected source category sub-tab.
function getCategoryRates(c, cat) {
  const f = c.fees_2026_05 || {};
  const sd = f.schedule_detailed || {};

  // Platform tab: prefer GoGolf reference rates if available (often differ from official)
  if (cat === 'platform' && c.fees_gogolf_reference?.schedule) {
    const sch = c.fees_gogolf_reference.schedule;
    return {
      wdAm: sch.weekday?.am ?? null,
      wdPm: sch.weekday?.pm ?? null,
      satAm: sch.saturday?.am ?? null,
      satPm: sch.saturday?.pm ?? null,
      sunAm: sch.sunday?.am ?? null,
      sunPm: sch.sunday?.pm ?? null,
      note: t('table.gogolfNote'),
      isPlatform: true,
    };
  }

  // Default: derive from main schedule (used by 전체·공시·SNS·애그리게이터·뉴스)
  const wd = extractAmPm(sd.weekday);
  const sat = extractAmPm(sd.weekend_saturday);
  const sun = extractAmPm(sd.weekend_sunday);
  return {
    wdAm: wd.am, wdPm: wd.pm,
    satAm: sat.am, satPm: sat.pm,
    sunAm: sun.am, sunPm: sun.pm,
    note: null,
    isPlatform: false,
  };
}

// === Unified row renderer (single row template, rates swap by category) ===
function renderAllTabRow(c, cat = 'all') {
  const status = c.operating_status?.status || 'operating';
  const statusLabel = statusLabelOf(status);

  // Multi-source price cells: each cell shows dominant price + dot + ⚠ if 30%+ diff.
  // In "all" tab, ranges are shown when sources differ.
  const wdAmCell = renderFeeCell(c, 'wdAm', cat);
  const wdPmCell = renderFeeCell(c, 'wdPm', cat);
  const satAmCell = renderFeeCell(c, 'satAm', cat);
  const satPmCell = renderFeeCell(c, 'satPm', cat);
  const sunAmCell = renderFeeCell(c, 'sunAm', cat);
  const sunPmCell = renderFeeCell(c, 'sunPm', cat);

  const matoaTag = c.id === 'matoa-nasional' ? '<span class="matoa-tag">★ Matoa</span>' : '';
  const noteTag = '';
  const mapLink = `<a href="${escapeHtml(googleMapsPlaceUrl(c))}" target="_blank" rel="noopener">${t('map.mapLink')}</a>`;

  const fin = c.financials || {};
  const parentLabel = fin.parent_group || fin.parent_company_full_name || '';
  const parentCell = parentLabel
    ? `<span class="parent-cell" title="${escapeHtml(parentLabel)}">${escapeHtml(parentLabel.slice(0, 40))}${parentLabel.length > 40 ? '…' : ''}</span>`
    : '<span class="muted">—</span>';
  const ticker = fin.idx_ticker || fin.foreign_ticker;
  const yhUrl = ticker ? yahooFinanceUrl(ticker, !!fin.idx_ticker) : null;
  const tickerCell = ticker
    ? (yhUrl
        ? `<a class="ticker-pill ${fin.idx_ticker ? 'idx' : 'foreign'} ticker-link" href="${escapeHtml(yhUrl)}" target="_blank" rel="noopener" title="${escapeHtml(t('finance.tickerOpen', { ticker }))}">${escapeHtml(ticker)} <span class="ticker-ext">↗</span></a>`
        : `<span class="ticker-pill ${fin.idx_ticker ? 'idx' : 'foreign'}">${escapeHtml(ticker)}</span>`)
    : '<span class="muted">—</span>';
  const revIdr = fin.revenue_idr ?? fin.revenue_idr_h1;
  const revYearLabel = fin.revenue_idr_h1 != null && fin.revenue_idr == null ? ' (H1)' : '';
  const xbrlBadge = fin.figure_origin === 'IDX_XBRL'
    ? ` <span class="xbrl-badge" title="IDX XBRL 공시에서 자동 추출 — ${escapeHtml(fin.last_verified || '')}">XBRL</span>`
    : '';
  const revCell = revIdr != null
    ? `<span class="rev-cell">${fmtBigIDR(revIdr)}${revYearLabel}${xbrlBadge}</span>`
    : '<span class="muted">—</span>';

  return `
    <tr class="primary-rate-row">
      <td class="name">${escapeHtml(c.name_en)}${matoaTag}${noteTag}</td>
      <td>${escapeHtml(c.region)}</td>
      <td>${escapeHtml(c.province)}</td>
      <td><span class="status-pill ${status}">${statusLabel}</span></td>
      <td class="num">${c.holes ?? '—'}</td>
      <td class="num">${c.year_opened ?? '—'}</td>
      ${wdAmCell}
      ${wdPmCell}
      ${satAmCell}
      ${satPmCell}
      ${sunAmCell}
      ${sunPmCell}
      <td class="member-type">${membershipTypeCell(c.membership)}</td>
      <td class="num member-amount">${membershipAmountCell(c.membership)}</td>
      <td class="parent-group finance-col">${parentCell}</td>
      <td class="ticker finance-col">${tickerCell}</td>
      <td class="num parent-revenue finance-col">${revCell}</td>
      <td class="address">${escapeHtml(c.address || '')}<br>${mapLink}</td>
    </tr>
  `;
}

// === Current selected source category sub-tab (drives rate column swap) ===
let currentSourceCat = 'all';

const SRC_TAB_DESC = new Proxy({}, {
  get(_, k) { return t('srcDesc.' + k); },
});

const SRC_COL_HEADER = new Proxy({}, {
  get(_, k) { return t('srcCol.' + k); },
});

function renderTable() {
  const rows = getTableRows();
  const CAT_TABS = ['official', 'sns', 'platform', 'aggregator', 'news'];

  // Per-category counts for the tab badges (count = courses that have ≥1 source in that category)
  const counts = { official: 0, sns: 0, platform: 0, aggregator: 0, news: 0 };
  for (const c of rows) {
    const cat = collectCategorizedSources(c);
    for (const t of CAT_TABS) if (cat[t].length) counts[t]++;
  }

  // Always show every filtered course — sub-tab only swaps prices/source column,
  // never hides rows. (Previously we filtered by category, which removed rows
  // when switching tabs; user wants the row set to stay stable.)
  const tbody = document.querySelector('[data-src-tbody="all"]');
  if (tbody) {
    if (rows.length === 0) {
      tbody.innerHTML = `<tr><td colspan="18"><div class="empty-state">
        <div class="empty-emoji">📭</div>
        <div class="empty-title">${t('empty.title')}</div>
        <div class="empty-hint">${t('empty.hint2')}</div>
      </div></td></tr>`;
    } else {
      tbody.innerHTML = rows.map(c => renderAllTabRow(c, currentSourceCat)).join('');
    }
  }

  // Tab counts (still reflect how many courses have a source in each category)
  document.getElementById('srcCount-all').textContent = rows.length;
  for (const t of CAT_TABS) {
    const el = document.getElementById(`srcCount-${t}`);
    if (el) el.textContent = counts[t];
  }

  // Toolbar visible count + panel description
  document.getElementById('tableVisibleCount').textContent = rows.length;
  const descEl = document.getElementById('srcPanelDesc');
  if (descEl) descEl.innerHTML = SRC_TAB_DESC[currentSourceCat] || SRC_TAB_DESC.all;
}

// Removed-legacy guard — no longer used.
function _unused_renderTableLegacy() {
  const rows = getTableRows();
  // legacy single-table renderer (unused, kept disabled below for safety)
  // eslint-disable-next-line no-unreachable
  const _legacyTbody = document.getElementById('courseTableBody');
  if (!_legacyTbody) return;
  _legacyTbody.innerHTML = rows.map(c => {
    const status = c.operating_status?.status || 'operating';
    const statusLabel = {
      operating: '운영중',
      closed_temporary: '임시 휴장',
      closed_permanent: '영구 폐장',
      uncertain: '불확실',
    }[status] || status;
    const f = c.fees_2026_05 || {};
    const sd = f.schedule_detailed || {};
    const wdSlots = extractAmPm(sd.weekday);
    const satSlots = extractAmPm(sd.weekend_saturday);
    const sunSlots = extractAmPm(sd.weekend_sunday);
    const wdFallback = f.weekday?.green_fee_idr ?? f.weekday?.guest_fee_idr;
    const weFallback = f.weekend?.green_fee_idr ?? f.weekend?.guest_fee_idr;
    const wdUsd = f.weekday?.green_fee_usd;
    const weUsd = f.weekend?.green_fee_usd;
    const cellHtml = (idr, fallbackIdr, fallbackUsd) => {
      if (idr != null) return fmtIDR(idr);
      if (fallbackIdr != null) return `<span class="fee-fallback">${fmtIDR(fallbackIdr)}</span>`;
      if (fallbackUsd != null) return `<span class="fee-fallback">${fmtUSD(fallbackUsd)}</span>`;
      return '<span class="muted">—</span>';
    };
    const wdAmCell = cellHtml(wdSlots.am, wdFallback, wdUsd);
    const wdPmCell = cellHtml(wdSlots.pm, wdFallback, wdUsd);
    const satAmCell = cellHtml(satSlots.am, weFallback, weUsd);
    const satPmCell = cellHtml(satSlots.pm, weFallback, weUsd);
    const sunAmCell = cellHtml(sunSlots.am, weFallback, weUsd);
    const sunPmCell = cellHtml(sunSlots.pm, weFallback, weUsd);

    const SNS_HOSTS = ['instagram.com', 'facebook.com', 'fb.com', 'tiktok.com', 'youtube.com', 'youtu.be', 'twitter.com', 'x.com', 'linkedin.com'];
    const isSnsUrl = u => SNS_HOSTS.some(h => u.includes(h));
    const allSources = (f.sources || []).concat((c.membership?.sources || []), (c.operating_status?.evidence || []).filter(s => typeof s === 'string' && s.startsWith('http'))).filter(Boolean);
    const uniqueSources = [...new Set(allSources)];

    const getHost = u => { try { return new URL(u).hostname.replace(/^www\./, '').toLowerCase(); } catch (e) { return null; } };
    const officialHost = c.website ? getHost(c.website) : null;
    const matchesOfficial = u => {
      if (!officialHost) return false;
      const h = getHost(u);
      return h && (h === officialHost || h.endsWith('.' + officialHost));
    };
    // Dedupe by hostname (so the same site doesn't appear twice from different paths)
    const officialLinks = [];
    const seenOfficialHosts = new Set();
    const tryAddOfficial = (u) => {
      const h = getHost(u);
      if (!h || seenOfficialHosts.has(h)) return;
      seenOfficialHosts.add(h);
      officialLinks.push(u);
    };
    if (c.website) tryAddOfficial(c.website);
    for (const u of uniqueSources) {
      if (matchesOfficial(u) && officialLinks.length < 3) tryAddOfficial(u);
    }
    // SNS: dedupe by hostname+account-path so multiple posts from same account don't repeat
    const snsKey = (u) => {
      try {
        const url = new URL(u);
        const host = url.hostname.replace(/^www\./, '').toLowerCase();
        const path = url.pathname.split('/').filter(Boolean).slice(0, 1).join('/');
        return path ? `${host}/${path}` : host;
      } catch (e) { return u; }
    };
    const snsLinks = [];
    const seenSnsKeys = new Set();
    for (const u of uniqueSources) {
      if (!isSnsUrl(u)) continue;
      const key = snsKey(u);
      if (seenSnsKeys.has(key)) continue;
      seenSnsKeys.add(key);
      snsLinks.push(u);
      if (snsLinks.length >= 4) break;
    }

    const officialHtml = officialLinks.length
      ? officialLinks.map((u, i) => {
          let label = '공식';
          try { label = new URL(u).hostname.replace(/^www\./, ''); } catch (e) {}
          return `<a href="${escapeHtml(u)}" target="_blank" rel="noopener" title="${escapeHtml(u)}">${escapeHtml(label)}</a>`;
        }).join('<br>')
      : '<span class="muted">—</span>';

    const snsLabel = u => {
      const lu = u.toLowerCase();
      if (lu.includes('instagram.com')) return 'IG';
      if (lu.includes('facebook.com') || lu.includes('fb.com')) return 'FB';
      if (lu.includes('tiktok.com')) return 'TT';
      if (lu.includes('youtube.com') || lu.includes('youtu.be')) return 'YT';
      if (lu.includes('twitter.com') || lu.includes('x.com')) return 'X';
      if (lu.includes('linkedin.com')) return 'LI';
      return 'SNS';
    };
    const snsHtml = snsLinks.length
      ? snsLinks.map(u => `<a class="sns-pill" href="${escapeHtml(u)}" target="_blank" rel="noopener" title="${escapeHtml(u)}">${snsLabel(u)}</a>`).join(' ')
      : '<span class="muted">—</span>';

    const matoaTag = c.id === 'matoa-nasional' ? '<span class="matoa-tag">★ Matoa</span>' : '';

    const mapLink = `<a href="https://www.google.com/maps/search/?api=1&query=${c.lat},${c.lng}" target="_blank" rel="noopener">지도</a>`;

    // Financials cells
    const fin = c.financials || {};
    const parentLabel = fin.parent_group || fin.parent_company_full_name || '';
    const parentCell = parentLabel
      ? `<span class="parent-cell" title="${escapeHtml(parentLabel)}">${escapeHtml(parentLabel.slice(0, 40))}${parentLabel.length > 40 ? '…' : ''}</span>`
      : '<span class="muted">—</span>';
    const ticker = fin.idx_ticker || fin.foreign_ticker;
    const yhUrl = ticker ? yahooFinanceUrl(ticker, !!fin.idx_ticker) : null;
    const tickerCell = ticker
      ? (yhUrl
          ? `<a class="ticker-pill ${fin.idx_ticker ? 'idx' : 'foreign'} ticker-link" href="${escapeHtml(yhUrl)}" target="_blank" rel="noopener" title="Yahoo Finance에서 ${escapeHtml(ticker)} 열기">${escapeHtml(ticker)} <span class="ticker-ext">↗</span></a>`
          : `<span class="ticker-pill ${fin.idx_ticker ? 'idx' : 'foreign'}">${escapeHtml(ticker)}</span>`)
      : '<span class="muted">—</span>';
    const revIdr = fin.revenue_idr ?? fin.revenue_idr_h1;
    const revYearLabel = fin.revenue_idr_h1 != null && fin.revenue_idr == null ? ' (H1)' : '';
    const revCell = revIdr != null
      ? `<span class="rev-cell">${fmtBigIDR(revIdr)}${revYearLabel}</span>`
      : '<span class="muted">—</span>';

    // === Build per-source attribution rows ===
    // 1) Categorize all primary fee sources (deduped by hostname)
    const primarySources = (f.sources || []).filter(s => typeof s === 'string' && /^https?:/.test(s));
    const labeledPrimary = [];
    const seenSrcHosts = new Set();
    for (const u of primarySources) {
      const info = labelSource(u, c.website);
      if (seenSrcHosts.has(info.host)) continue;
      seenSrcHosts.add(info.host);
      labeledPrimary.push(info);
    }
    // 2) Identify the lead source for the primary row (prefer 공식 → 공시 → Q-Access → 그 외)
    const kindRank = { official: 0, qaccess: 1, playgolf: 2, gogolf: 3, aggregator: 4, news: 5, sns: 6, gov: 7, archive: 8, booking: 9, other: 10 };
    labeledPrimary.sort((a, b) => (kindRank[a.kind] ?? 99) - (kindRank[b.kind] ?? 99));
    const leadSource = labeledPrimary[0] || null;
    const otherSources = labeledPrimary.slice(1);

    const leadPill = leadSource
      ? `<a class="src-pill src-${leadSource.kind}" href="${escapeHtml(leadSource.url)}" target="_blank" rel="noopener" title="${escapeHtml(leadSource.url)}">${escapeHtml(leadSource.label)}</a>`
      : '';

    // 3) Sub-row for each additional primary source (same rates, attribution differs)
    const sameRateBadge = '<span class="src-rate-badge">동일</span>';
    const fmtAncillary = () => {
      const parts = [];
      if (f.caddy_idr != null) parts.push(`캐디 ${typeof f.caddy_idr === 'number' ? fmtIDR(f.caddy_idr) : escapeHtml(String(f.caddy_idr))}`);
      if (f.cart_idr != null)  parts.push(`카트 ${typeof f.cart_idr === 'number' ? fmtIDR(f.cart_idr) : escapeHtml(String(f.cart_idr))}`);
      return parts.length ? `<span class="src-ancillary">${parts.join(' · ')}</span>` : '';
    };
    const ancillaryHtml = fmtAncillary();

    let sourceRowsHtml = '';
    for (const src of otherSources) {
      sourceRowsHtml += `
        <tr class="src-row src-row-${src.kind}">
          <td class="src-label" colspan="6">↳ <span class="src-pill src-${src.kind}">${escapeHtml(src.label)}</span> <a class="src-link" href="${escapeHtml(src.url)}" target="_blank" rel="noopener" title="${escapeHtml(src.url)}">${escapeHtml(src.host)}</a> ${sameRateBadge}</td>
          <td class="num fee src-fee">${wdAmCell}</td>
          <td class="num fee src-fee">${wdPmCell}</td>
          <td class="num fee fee-premium src-fee">${satAmCell}</td>
          <td class="num fee src-fee">${satPmCell}</td>
          <td class="num fee fee-premium src-fee">${sunAmCell}</td>
          <td class="num fee src-fee">${sunPmCell}</td>
          <td colspan="8" class="src-extras muted">${ancillaryHtml || '<span class="muted">cross-verified</span>'}</td>
        </tr>
      `;
    }

    // 4) GoGolf reference sub-row (when present, with potentially different rates)
    let gogolfRowHtml = '';
    const gg = c.fees_gogolf_reference;
    if (gg && gg.schedule) {
      const sch = gg.schedule;
      const hasAnyGgRate = ['weekday','saturday','sunday'].some(k => {
        const s = sch[k] || {};
        return (typeof s.am === 'number') || (typeof s.pm === 'number');
      });
      if (hasAnyGgRate || gg.member_rate_idr != null || gg.ancillary?.caddy_idr != null || gg.ancillary?.cart_idr != null) {
        const ggCell = (v) => v != null ? fmtIDR(v) : '<span class="muted">—</span>';
        const ggHost = gg.source_url ? (getHostname(gg.source_url) || 'GoGolf') : 'GoGolf';
        const ggKind = ggHost.includes('playgolf') ? 'playgolf' : (ggHost.includes('gogolf') ? 'gogolf' : 'aggregator');
        const ggLabel = ggHost.includes('playgolf') ? 'playgolf.id' : (ggHost.includes('gogolf') ? 'GoGolf' : ggHost);
        const ggSrc = gg.source_url
          ? `<a class="src-pill src-${ggKind}" href="${escapeHtml(gg.source_url)}" target="_blank" rel="noopener" title="${escapeHtml(gg.source_url)}">${escapeHtml(ggLabel)} 참고</a>`
          : `<span class="src-pill src-${ggKind}">${escapeHtml(ggLabel)} 참고</span>`;
        const ggMember = gg.member_rate_idr != null ? `<span class="member-amt">멤버 ${fmtIDR(gg.member_rate_idr)}</span>` : '<span class="muted">—</span>';
        const ggCaddy = gg.ancillary?.caddy_idr != null ? `캐디 ${fmtIDR(gg.ancillary.caddy_idr)}` : '';
        const ggCart = gg.ancillary?.cart_idr != null ? `카트 ${fmtIDR(gg.ancillary.cart_idr)}` : '';
        const ggExtras = [ggCaddy, ggCart].filter(Boolean).join(' · ');
        gogolfRowHtml = `
          <tr class="src-row gogolf-ref-row src-row-${ggKind}">
            <td class="src-label" colspan="6">↳ ${ggSrc} ${ggExtras ? `<span class="src-ancillary">${ggExtras}</span>` : ''}</td>
            <td class="num fee gogolf-fee">${ggCell(sch.weekday?.am)}</td>
            <td class="num fee gogolf-fee">${ggCell(sch.weekday?.pm)}</td>
            <td class="num fee gogolf-fee">${ggCell(sch.saturday?.am)}</td>
            <td class="num fee gogolf-fee">${ggCell(sch.saturday?.pm)}</td>
            <td class="num fee gogolf-fee">${ggCell(sch.sunday?.am)}</td>
            <td class="num fee gogolf-fee">${ggCell(sch.sunday?.pm)}</td>
            <td class="member-type"><span class="muted">—</span></td>
            <td class="num member-amount">${ggMember}</td>
            <td colspan="6" class="address gogolf-disclaimer"><span class="gogolf-note">${escapeHtml(gg.disclaimer || '참고용 비공식 가격')}</span></td>
          </tr>
        `;
      }
    }

    return `
      <tr class="primary-rate-row">
        <td class="name">${escapeHtml(c.name_en)}${matoaTag}${leadPill ? ` <span class="lead-source-wrap">${leadPill}</span>` : ''}</td>
        <td>${escapeHtml(c.region)}</td>
        <td>${escapeHtml(c.province)}</td>
        <td><span class="status-pill ${status}">${statusLabel}</span></td>
        <td class="num">${c.holes ?? '—'}</td>
        <td class="num">${c.year_opened ?? '—'}</td>
        <td class="num fee">${wdAmCell}</td>
        <td class="num fee">${wdPmCell}</td>
        <td class="num fee fee-premium">${satAmCell}</td>
        <td class="num fee">${satPmCell}</td>
        <td class="num fee fee-premium">${sunAmCell}</td>
        <td class="num fee">${sunPmCell}</td>
        <td class="member-type">${membershipTypeCell(c.membership)}</td>
        <td class="num member-amount">${membershipAmountCell(c.membership)}</td>
        <td class="parent-group">${parentCell}</td>
        <td class="ticker">${tickerCell}</td>
        <td class="num parent-revenue">${revCell}</td>
        <td class="address">${escapeHtml(c.address || '')}<br>${mapLink}</td>
        <td class="sources official-links">${officialHtml}</td>
        <td class="sources sns-links">${snsHtml}</td>
      </tr>${sourceRowsHtml}${gogolfRowHtml}
    `;
  }).join('');
}

// === CSV Export ===
document.getElementById('exportCsv').addEventListener('click', () => {
  const rows = getTableRows();
  const headers = [
    t('csv.name'), t('csv.region'), t('csv.province'), t('csv.status'), t('csv.holes'), t('csv.par'), t('csv.year'),
    t('csv.designer'), t('csv.address'), t('csv.weekdayFee'), t('csv.weekendFee'),
    t('csv.weekdayUsd'), t('csv.weekendUsd'), t('csv.caddyFee'), t('csv.cartFee'), t('csv.insuranceFee'),
    t('csv.website'), t('csv.lat'), t('csv.lng'), t('csv.note'), t('csv.feeNote'),
    t('csv.memberAvail'), t('csv.memberCat'), t('csv.memberLowest'),
    t('csv.memberNote'), t('csv.sources')
  ];
  const csvRows = rows.map(c => {
    const f = c.fees_2026_05 || {};
    const wd = f.weekday || {};
    const we = f.weekend || {};
    const m = c.membership || {};
    const cats = (m.categories || []).map(cat => {
      const init = cat.initiation_fee || {};
      const ann = cat.annual_fee || {};
      const parts = [cat.name];
      if (init.amount) parts.push(`${t('member.cellInit', { amt: `${init.amount} ${init.currency || 'IDR'}` })}`);
      if (ann.amount) parts.push(`${t('member.cellAnnual', { amt: `${ann.amount} ${ann.currency || 'IDR'}` })}`);
      return parts.join(' / ');
    }).join(' || ');
    const lowest = lowestMembershipFee(m);
    const memberSources = (m.sources || []).join(' | ');
    const allSources = [...(f.sources || []), ...(m.sources || [])];
    return [
      c.name_en,
      c.region,
      c.province,
      c.operating_status?.status || 'operating',
      c.holes,
      c.par,
      c.year_opened,
      c.designer,
      c.address,
      wd.green_fee_idr ?? wd.guest_fee_idr ?? '',
      we.green_fee_idr ?? we.guest_fee_idr ?? '',
      wd.green_fee_usd ?? '',
      we.green_fee_usd ?? '',
      f.caddy_idr ?? '',
      f.cart_idr ?? '',
      f.insurance_idr ?? '',
      c.website ?? '',
      c.lat,
      c.lng,
      c.notes ?? '',
      f.notes ?? '',
      m.available ?? '',
      cats,
      lowest ?? '',
      m.notes ?? '',
      [...new Set(allSources)].join(' | ')
    ].map(csvEscape).join(',');
  });
  const csv = '﻿' + [headers.join(','), ...csvRows].join('\r\n');
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `indonesia-golf-clubs-${new Date().toISOString().slice(0, 10)}.csv`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
});

function csvEscape(v) {
  if (v == null) return '';
  const s = String(v);
  if (/[",\r\n]/.test(s)) return '"' + s.replaceAll('"', '""') + '"';
  return s;
}

// === Ticker Financials Modal ===
let financialsByTicker = null;
let activeCharts = [];

async function loadFinancialsIfNeeded() {
  if (financialsByTicker) return financialsByTicker;
  try {
    const res = await fetch('data/company_financials_5y.json');
    if (!res.ok) throw new Error('not found');
    const doc = await res.json();
    const arr = Array.isArray(doc) ? doc : (doc.companies || doc.tickers || []);
    financialsByTicker = {};
    arr.forEach(c => { if (c.ticker) financialsByTicker[c.ticker.toUpperCase()] = c; });
    return financialsByTicker;
  } catch (e) {
    console.warn('5-year financials not available:', e);
    financialsByTicker = {};
    return financialsByTicker;
  }
}

function destroyActiveCharts() {
  activeCharts.forEach(ch => { try { ch.destroy(); } catch (e) {} });
  activeCharts = [];
}

function fmtCompactIDR(n) {
  if (n == null || !isFinite(n)) return null;
  const abs = Math.abs(n);
  const sign = n < 0 ? '-' : '';
  if (abs >= 1e12) return `${sign}Rp ${(abs/1e12).toFixed(2).replace(/\.?0+$/, '')}T`;
  if (abs >= 1e9)  return `${sign}Rp ${(abs/1e9).toFixed(2).replace(/\.?0+$/, '')}B`;
  if (abs >= 1e6)  return `${sign}Rp ${(abs/1e6).toFixed(0)}M`;
  return `${sign}Rp ${abs.toLocaleString('en-US')}`;
}
function fmtCompact(n, prefix) {
  if (n == null || !isFinite(n)) return null;
  const abs = Math.abs(n);
  const sign = n < 0 ? '-' : '';
  if (abs >= 1e12) return `${sign}${prefix}${(abs/1e12).toFixed(2).replace(/\.?0+$/, '')}T`;
  if (abs >= 1e9)  return `${sign}${prefix}${(abs/1e9).toFixed(2).replace(/\.?0+$/, '')}B`;
  if (abs >= 1e6)  return `${sign}${prefix}${(abs/1e6).toFixed(0)}M`;
  return `${sign}${prefix}${abs.toLocaleString('en-US')}`;
}

function renderTickerModal(ticker) {
  const overlay = document.getElementById('tickerModal');
  const titleEl = document.getElementById('tickerModalTitle');
  const subtitleEl = document.getElementById('tickerModalSubtitle');
  const bodyEl = document.getElementById('tickerModalBody');

  destroyActiveCharts();

  const data = financialsByTicker?.[ticker.toUpperCase()];

  titleEl.innerHTML = `<span class="ticker-badge">${escapeHtml(ticker)}</span> <span>${escapeHtml(data?.company_name || '')}</span>`;
  subtitleEl.textContent = data?.exchange ? `${data.exchange}${data.currency ? ` · ${data.currency}` : ''}` : '';

  if (!data) {
    bodyEl.innerHTML = `
      <p style="color:#64748b">${t('ticker.notReady', { ticker: escapeHtml(ticker) })}</p>
      <p style="color:#94a3b8; font-size:12px">${t('ticker.notReadyHint')}</p>
    `;
    overlay.hidden = false;
    return;
  }

  const yearly = data.yearly || {};
  const years = Object.keys(yearly).sort();
  const currency = (data.currency || 'IDR').toUpperCase();
  const isIDR = currency === 'IDR';
  const fmtMain = isIDR ? fmtCompactIDR : (n) => fmtCompact(n, currency === 'USD' ? '$' : currency === 'SGD' ? 'S$' : currency + ' ');
  const idrEquiv = !isIDR;
  const fmtForCell = (v, idrEqV) => {
    if (v == null) return '<span class="na">—</span>';
    const main = fmtMain(v) || '—';
    const sub = (idrEqV != null) ? `<br><span style="color:#94a3b8;font-size:10px">${fmtCompactIDR(idrEqV)}</span>` : '';
    return (v < 0 ? '<span class="neg">' + main + '</span>' : main) + sub;
  };

  // Metric rows
  const metrics = [
    { key: 'revenue', label: t('ticker.metric.revenue') },
    { key: 'operating_profit', label: t('ticker.metric.operating_profit') },
    { key: 'net_profit', label: t('ticker.metric.net_profit') },
    { key: 'ebitda', label: t('ticker.metric.ebitda') },
    { key: 'total_assets', label: t('ticker.metric.total_assets') },
    { key: 'total_liabilities', label: t('ticker.metric.total_liabilities') },
    { key: 'total_equity', label: t('ticker.metric.total_equity') },
    { key: 'eps', label: t('ticker.metric.eps') },
    { key: 'dividend_per_share', label: t('ticker.metric.dividend_per_share') },
    { key: 'employees', label: t('ticker.metric.employees') },
  ];

  const getMetricValue = (yr, key) => {
    const y = yearly[yr] || {};
    // Try various key conventions
    return y[key] ?? y[key + '_idr'] ?? null;
  };
  const getIdrEquiv = (yr, key) => {
    const y = yearly[yr] || {};
    return y[key + '_idr_equiv'] ?? null;
  };

  let tableRows = '';
  metrics.forEach(m => {
    const cells = years.map(yr => {
      const v = getMetricValue(yr, m.key);
      const idrEqV = idrEquiv ? getIdrEquiv(yr, m.key) : null;
      let html;
      if (v == null) html = '<td class="na">—</td>';
      else if (m.key === 'employees') html = `<td>${Number(v).toLocaleString('en-US')}</td>`;
      else if (m.key === 'eps' || m.key === 'dividend_per_share') {
        const main = isIDR ? `Rp ${Number(v).toLocaleString('en-US')}` : `${fmtMain(v)}`;
        html = `<td>${v < 0 ? '<span class="neg">'+main+'</span>' : main}</td>`;
      }
      else html = `<td>${fmtForCell(v, idrEqV)}</td>`;
      return html;
    }).join('');
    tableRows += `<tr><td class="metric-col">${m.label}</td>${cells}</tr>`;
  });

  const qualityClass = data.data_quality || 'medium';
  const summaryNote = data.summary_note ? `<div class="fin5y-summary">📊 ${escapeHtml(data.summary_note)}</div>` : '';

  // Collect all sources from all years
  const allSources = [];
  const seenUrls = new Set();
  years.forEach(yr => {
    (yearly[yr]?.sources || []).forEach(s => {
      const url = (typeof s === 'string') ? s : s?.url;
      if (!url || seenUrls.has(url)) return;
      seenUrls.add(url);
      allSources.push(typeof s === 'object' ? s : { url, title: null, publisher: null });
    });
  });
  const sourceLinks = allSources.length
    ? allSources.slice(0, 30).map(s => {
        const label = s.publisher || (() => { try { return new URL(s.url).hostname.replace(/^www\./,''); } catch { return s.url; } })();
        return `<a class="fin-src" href="${escapeHtml(s.url)}" target="_blank" rel="noopener" title="${escapeHtml(s.title || s.url)}">${escapeHtml(label)}${s.date_published ? ` <span class="src-date">${escapeHtml(s.date_published)}</span>` : ''}</a>`;
      }).join(' ')
    : `<span class="muted">${t('ticker.noSources')}</span>`;

  bodyEl.innerHTML = `
    <h3>${t('ticker.summary')} <span class="fin5y-quality ${qualityClass}">${escapeHtml(qualityClass.toUpperCase())}</span></h3>
    ${summaryNote}
    <div class="fin5y-charts">
      <div class="chart-card">
        <h4>${t('ticker.chart.revenue')}</h4>
        <canvas id="chart-revenue"></canvas>
      </div>
      <div class="chart-card">
        <h4>${t('ticker.chart.netprofit')}</h4>
        <canvas id="chart-netprofit"></canvas>
      </div>
      <div class="chart-card">
        <h4>${t('ticker.chart.assets')}</h4>
        <canvas id="chart-assets"></canvas>
      </div>
      <div class="chart-card">
        <h4>${t('ticker.chart.balance')}</h4>
        <canvas id="chart-balance"></canvas>
      </div>
    </div>
    <h3>${t('ticker.tableTitle', { currency: escapeHtml(currency) })}</h3>
    <table class="fin5y-table">
      <thead>
        <tr><th class="metric-col">${t('ticker.metricItem')}</th>${years.map(y => `<th>${y}</th>`).join('')}</tr>
      </thead>
      <tbody>${tableRows}</tbody>
    </table>
    <h3>${t('ticker.sourcesTitle')}</h3>
    <div class="fin-sources">${sourceLinks}</div>
    <p style="font-size:11px;color:#94a3b8;margin-top:14px">${t('ticker.unitFooter', { date: escapeHtml(data.last_verified || '2026-05-01'), unit: isIDR ? t('ticker.unitIDR') : escapeHtml(currency) })}${idrEquiv ? t('ticker.unitIDREquiv') : ''}</p>
  `;

  overlay.hidden = false;

  // Render charts after DOM insertion
  if (window.Chart) {
    const isDark = document.documentElement.dataset.theme === 'dark';
    const gridColor = isDark ? 'rgba(255,255,255,0.08)' : 'rgba(10,31,23,0.08)';
    const tickColor = isDark ? '#a8b3ac' : '#5b6d63';
    Chart.defaults.color = tickColor;
    Chart.defaults.borderColor = gridColor;
    const colors = {
      revenue: isDark ? '#60a5fa' : '#0d6e4d',
      netprofit: isDark ? '#34d399' : '#16a34a',
      assets: isDark ? '#a78bfa' : '#7c3aed',
    };
    const mkLineChart = (id, key, color, label) => {
      const canvas = document.getElementById(id);
      if (!canvas) return;
      const dataPts = years.map(yr => {
        const v = getMetricValue(yr, key);
        const eq = idrEquiv ? getIdrEquiv(yr, key) : null;
        return idrEquiv && eq != null ? eq : v;
      });
      const ch = new Chart(canvas, {
        type: 'bar',
        data: {
          labels: years,
          datasets: [{
            label,
            data: dataPts,
            backgroundColor: color + '88',
            borderColor: color,
            borderWidth: 2,
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { display: false },
            tooltip: {
              callbacks: {
                label: (ctx) => {
                  const v = ctx.parsed.y;
                  return idrEquiv ? `${label}: ${fmtCompactIDR(v)}` : `${label}: ${fmtMain(v)}`;
                }
              }
            }
          },
          scales: {
            y: {
              ticks: {
                callback: (v) => idrEquiv ? fmtCompactIDR(v) : fmtMain(v),
                font: { size: 10 },
                color: tickColor,
              },
              grid: { color: gridColor },
            },
            x: { ticks: { font: { size: 11 }, color: tickColor }, grid: { color: gridColor } }
          }
        }
      });
      activeCharts.push(ch);
    };
    mkLineChart('chart-revenue', 'revenue', colors.revenue, t('ticker.line.revenue'));
    mkLineChart('chart-netprofit', 'net_profit', colors.netprofit, t('ticker.line.netprofit'));
    mkLineChart('chart-assets', 'total_assets', colors.assets, t('ticker.line.assets'));

    // Stacked balance chart
    const balCanvas = document.getElementById('chart-balance');
    if (balCanvas) {
      const liabPts = years.map(yr => {
        const v = getMetricValue(yr, 'total_liabilities');
        const eq = idrEquiv ? getIdrEquiv(yr, 'total_liabilities') : null;
        return idrEquiv && eq != null ? eq : v;
      });
      const eqPts = years.map(yr => {
        const v = getMetricValue(yr, 'total_equity');
        const eq = idrEquiv ? getIdrEquiv(yr, 'total_equity') : null;
        return idrEquiv && eq != null ? eq : v;
      });
      const balCh = new Chart(balCanvas, {
        type: 'bar',
        data: {
          labels: years,
          datasets: [
            { label: t('ticker.line.liab'), data: liabPts, backgroundColor: isDark ? '#fbbf2488' : '#b8924a88', borderColor: isDark ? '#fbbf24' : '#b8924a', borderWidth: 2, stack: 'b' },
            { label: t('ticker.line.equity'), data: eqPts, backgroundColor: isDark ? '#34d39988' : '#0d6e4d88', borderColor: isDark ? '#34d399' : '#0d6e4d', borderWidth: 2, stack: 'b' },
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { position: 'bottom', labels: { font: { size: 10 }, color: tickColor } },
            tooltip: {
              callbacks: {
                label: (ctx) => `${ctx.dataset.label}: ${idrEquiv ? fmtCompactIDR(ctx.parsed.y) : fmtMain(ctx.parsed.y)}`
              }
            }
          },
          scales: {
            y: {
              stacked: true,
              ticks: { callback: v => idrEquiv ? fmtCompactIDR(v) : fmtMain(v), font: { size: 10 }, color: tickColor },
              grid: { color: gridColor },
            },
            x: { stacked: true, ticks: { font: { size: 11 }, color: tickColor }, grid: { color: gridColor } }
          }
        }
      });
      activeCharts.push(balCh);
    }
  }
}

document.getElementById('closeTickerModal').addEventListener('click', () => {
  document.getElementById('tickerModal').hidden = true;
  destroyActiveCharts();
});
document.getElementById('tickerModal').addEventListener('click', (e) => {
  if (e.target.id === 'tickerModal') {
    e.currentTarget.hidden = true;
    destroyActiveCharts();
  }
});

// Ticker pills are now plain anchors that open Yahoo Finance in a new tab.
// (Previously they opened an internal 5-year financials modal — removed.)

// === Theme toggle ===
const SUN_ICON = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4"></circle><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"></path></svg>';
const MOON_ICON = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path></svg>';

function applyTheme(mode) {
  document.documentElement.dataset.theme = mode;
  const tg = document.getElementById('themeToggle');
  if (tg) tg.innerHTML = mode === 'dark' ? SUN_ICON : MOON_ICON;
  try { localStorage.setItem('theme', mode); } catch (e) {}
  // Re-render any open ticker chart so axis colors stay readable
  if (financialsByTicker && document.getElementById('tickerModal') && !document.getElementById('tickerModal').hidden) {
    const t = document.getElementById('tickerModalTitle')?.querySelector('.ticker-badge')?.textContent;
    if (t) renderTickerModal(t);
  }
}

(function initTheme(){
  let saved = null;
  try { saved = localStorage.getItem('theme'); } catch (e) {}
  const prefers = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
  applyTheme(saved || (prefers ? 'dark' : 'light'));
})();

document.getElementById('themeToggle')?.addEventListener('click', () => {
  const cur = document.documentElement.dataset.theme || 'light';
  applyTheme(cur === 'dark' ? 'light' : 'dark');
});

// === Price comparison modal ===
const SRC_CAT_LABEL = new Proxy({}, {
  get(_, k) { return t('srcCat.' + k); },
});
const SRC_TRUST_ORDER = ['official', 'platform', 'sns', 'aggregator', 'news'];

function openPriceModal(courseId, slot) {
  const c = allCourses.find(x => x.id === courseId);
  if (!c) return;
  const modal = document.getElementById('priceModal');
  const title = document.getElementById('priceModalTitle');
  const sub = document.getElementById('priceModalSubtitle');
  const body = document.getElementById('priceModalBody');
  if (!modal || !body) return;

  const cands = getSlotCandidates(c, slot);
  title.textContent = c.name_en;
  sub.innerHTML = `<strong>${SLOT_LABEL[slot]}</strong> · ${escapeHtml(c.region)}` +
    (cands.length === 0 ? ` · <span class="muted">${t('priceModal.noData')}</span>` : '');

  if (cands.length === 0) {
    body.innerHTML = `<p style="color:var(--text-muted);text-align:center;padding:24px;">${t('priceModal.noDataMsg')}</p>`;
    modal.hidden = false;
    return;
  }

  // Sort by trust order; mark best as "trusted"
  const sorted = [...cands].sort((a, b) =>
    SRC_TRUST_ORDER.indexOf(a.src.kind) - SRC_TRUST_ORDER.indexOf(b.src.kind));
  const prices = cands.map(x => x.price);
  const lo = Math.min(...prices);
  const hi = Math.max(...prices);
  const diffPct = lo > 0 ? ((hi - lo) / lo) * 100 : 0;

  const rows = sorted.map((x, i) => {
    const cat = x.src.kind;
    const link = x.src.url
      ? `<a class="src-link" href="${escapeHtml(x.src.url)}" target="_blank" rel="noopener">${t('history.original')}</a>`
      : '';
    const originLabel = x.origin === 'gogolf' ? t('priceModal.gogolfExtract')
      : x.origin === 'crawled' ? t('priceModal.crawled', { tier: x.tier ?? '?', pdf: x.from_pdf ? ' · PDF' : '' })
      : '';
    const collapseNote = (x.n_collapsed && x.n_collapsed > 1)
      ? t('priceModal.collapsed', { n: x.n_collapsed })
      : '';
    const meta = [
      x.src.host || '',
      x.src.date ? t('priceModal.verified', { date: x.src.date }) : '',
      originLabel,
      collapseNote,
    ].filter(Boolean).join(' · ');
    return `<div class="price-source-row${i === 0 ? ' is-trusted' : ''}">
      <span class="src-cat-pill k-${cat}">${SRC_CAT_LABEL[cat] || cat}</span>
      <div class="src-info">
        <div class="src-info-label">${escapeHtml(x.src.label)}${i === 0 ? ` <small style="color:var(--accent);font-weight:600;">${t('priceModal.trusted')}</small>` : ''}</div>
        <div class="src-info-meta">${escapeHtml(meta || '—')}</div>
      </div>
      <span class="src-price">${fmtIDR(x.price)}</span>
      ${link}
    </div>`;
  }).join('');

  const summary = (sorted.length > 1)
    ? `<div class="price-modal-trust-note">${t('priceModal.diffNote', { pct: diffPct.toFixed(0), lo: fmtIDR(lo), hi: fmtIDR(hi), warn: diffPct >= 30 ? t('priceModal.diffWarn') : '' })}</div>`
    : `<div class="price-modal-trust-note">${t('priceModal.singleSrc')}</div>`;

  body.innerHTML = `<div class="price-modal-source-list">${rows}</div>${summary}`;
  modal.hidden = false;
}

function closePriceModal() {
  const m = document.getElementById('priceModal');
  if (m) m.hidden = true;
}

document.addEventListener('click', e => {
  const cell = e.target.closest('.fee-cell[data-fee-cell], .matrix-cell-btn[data-fee-cell]');
  if (cell && !e.target.closest('a')) {
    openPriceModal(cell.dataset.courseId, cell.dataset.feeCell);
    return;
  }
  if (e.target.id === 'closePriceModal' || e.target.closest('#closePriceModal')) {
    closePriceModal();
    return;
  }
  if (e.target.id === 'priceModal') {
    closePriceModal();
  }
});
document.addEventListener('keydown', e => {
  if (e.key === 'Enter' || e.key === ' ') {
    const cell = e.target.closest?.('.fee-cell[data-fee-cell]');
    if (cell) {
      e.preventDefault();
      openPriceModal(cell.dataset.courseId, cell.dataset.feeCell);
    }
  }
  if (e.key === 'Escape') closePriceModal();
});

// === Finance column toggle ===
document.getElementById('showFinanceCols')?.addEventListener('change', (e) => {
  document.querySelectorAll('.course-table').forEach(t => {
    t.classList.toggle('show-finance', e.target.checked);
  });
});

// === Finance table rendering ===

// Strict policy: a row is shown only when it has at least one actual
// financial-statement number (revenue/profit/assets/segment/...).
// Membership-only rows (회원권 가격만 있고 진짜 재무 데이터 없음) are
// excluded — they belong in the membership view, not 재무 분석.
function _hasMeaningfulFinancials(fin) {
  if (!fin || typeof fin !== 'object') return false;
  const NUM_KEYS = ['revenue_idr','revenue_idr_h1','net_profit_idr','net_profit_idr_h1',
                    'total_assets_idr','course_segment_revenue_idr',
                    'employees','investment_idr','investment_usd'];
  for (const k of NUM_KEYS) {
    if (typeof fin[k] === 'number' && fin[k] !== 0) return true;
  }
  return false;
}

// Extract a bare ticker code suitable for matching against
// company_financials_5y.json (which keys by code only — "BSDE", "PWON", etc).
// Strips parenthetical comments, exchange prefix (e.g. "SGX:5IG" -> "5IG"),
// and trailing whitespace.
function _bareTicker(raw) {
  if (!raw) return null;
  const head = String(raw).split('(')[0].trim();
  if (!head) return null;
  const tail = head.includes(':') ? head.split(':').pop() : head;
  const code = tail.trim().split(/\s+/)[0];
  return code || null;
}

// Robust source-URL extraction: handles strings, {url:...} objects,
// and discards empty / non-http values.
function _firstUrl(arr) {
  for (const s of (arr || [])) {
    if (typeof s === 'string' && /^https?:\/\//i.test(s.trim())) return s.trim();
    if (s && typeof s === 'object' && typeof s.url === 'string'
        && /^https?:\/\//i.test(s.url.trim())) return s.url.trim();
  }
  return null;
}

// Yahoo Finance URL with a guaranteed fallback: if the regular function
// can't resolve a confident exchange suffix (e.g. "Tbk(IDX 미거래)" or
// "BUMN holding"), fall back to a yahoo finance search query so the click
// always lands on something useful.
function _tickerYahooHref(ticker, isIDX) {
  const direct = yahooFinanceUrl(ticker, isIDX);
  if (direct) return direct;
  const q = String(ticker || '').split('(')[0].trim().split(/\s+/)[0];
  if (!q) return null;
  return `https://finance.yahoo.com/lookup?s=${encodeURIComponent(q)}`;
}

function renderFinanceTable() {
  const tbody = document.getElementById('financeTableBody');
  const search = (document.getElementById('financeSearch')?.value || '').trim().toLowerCase();
  const statusF = document.getElementById('financeStatusFilter')?.value || 'all';
  if (!tbody) return;

  // Universe: only courses with meaningful financials AND a ticker
  // (parent listed on an exchange). Rows without a ticker are excluded
  // from the finance view per product decision — they belong elsewhere.
  const universe = allCourses.filter(c => {
    if (!_hasMeaningfulFinancials(c.financials)) return false;
    const fin = c.financials || {};
    return !!(fin.idx_ticker || fin.foreign_ticker);
  });

  let rows = universe.filter(c => {
    const fin = c.financials;
    const ls = fin.listed_status || '';
    if (statusF === 'listed') {
      if (!(ls === 'listed' || ls === 'subsidiary-of-listed')) return false;
    } else if (statusF !== 'all' && ls !== statusF) return false;
    if (search) {
      const hay = [c.name_en, c.region, fin.parent_group, fin.parent_company_full_name,
        fin.idx_ticker, fin.foreign_ticker].filter(Boolean).join(' ').toLowerCase();
      if (!hay.includes(search)) return false;
    }
    return true;
  });

  rows.sort((a, b) => a.name_en.localeCompare(b.name_en));

  // Counter shows "<visible> / <universe>" (real meaningful total, not 137)
  const counter = document.getElementById('financeVisibleCount');
  if (counter) {
    counter.textContent = rows.length;
    const parent = counter.parentElement;
    if (parent) {
      parent.innerHTML = `<strong id="financeVisibleCount">${rows.length}</strong>` +
        ` / <span class="muted">${t('fin.totalKept')} ${universe.length}</span>`;
    }
  }

  if (rows.length === 0) {
    tbody.innerHTML = `<tr><td colspan="16"><div class="empty-state">
      <div class="empty-emoji">📊</div>
      <div class="empty-title">${t('empty.financeTitle')}</div>
      <div class="empty-hint">${t('empty.financeHint')}</div>
    </div></td></tr>`;
    return;
  }

  // Pre-load 5y financials so the trend cell knows which tickers have data.
  // If this is the first call, schedule a re-render once the fetch resolves
  // so the 📈 buttons appear without a manual reload.
  if (!financialsByTicker) {
    loadFinancialsIfNeeded().then(() => renderFinanceTable());
  }

  // 1차 출처(primary audited sources): IDX_XBRL (listed) 또는 AUDITED_AR (private/Tbk).
  const PRIMARY_SOURCE_TYPES = new Set(['IDX_XBRL', 'AUDITED_AR']);
  // 가장 최신 회계연도 자동 선택 — 모든 회사 중 primary source가 있는 max year.
  let xbrlYearKey = null;
  if (financialsByTicker) {
    for (const co of Object.values(financialsByTicker)) {
      const yrs = co?.yearly ? Object.keys(co.yearly) : [];
      for (const y of yrs) {
        const yb = co.yearly[y];
        const src = (yb?.sources || [])[0];
        if (src && PRIMARY_SOURCE_TYPES.has(src.source_type)) {
          if (!xbrlYearKey || y > xbrlYearKey) xbrlYearKey = y;
        }
      }
    }
  }
  xbrlYearKey = xbrlYearKey || '2024';
  // Update column header year label
  document.querySelectorAll('.finance-table .th-year').forEach(el => {
    el.textContent = `FY${xbrlYearKey}`;
  });

  const fmtNumOrDash = (v) => {
    if (v == null || Number.isNaN(v)) return '<span class="muted">—</span>';
    if (v < 0) return `<span class="neg">−${escapeHtml(fmtBigIDR(Math.abs(v)) || '')}</span>`;
    return escapeHtml(fmtBigIDR(v) || '—');
  };
  const fmtEps = (v) => {
    if (v == null || Number.isNaN(v)) return '<span class="muted">—</span>';
    if (v < 0) return `<span class="neg">${v.toFixed(2)}</span>`;
    return v.toFixed(2);
  };

  tbody.innerHTML = rows.map(c => {
    const fin = c.financials || {};
    const ticker = fin.idx_ticker || fin.foreign_ticker;
    const yhUrl = ticker ? _tickerYahooHref(ticker, !!fin.idx_ticker) : null;
    const tickerLinkHtml = ticker
      ? `<a class="ticker-pill ${fin.idx_ticker ? 'idx' : 'foreign'} ticker-link"`
          + ` href="${escapeHtml(yhUrl || 'https://finance.yahoo.com/')}"`
          + ` target="_blank" rel="noopener"`
          + ` title="${escapeHtml(t('finance.tickerOpen', { ticker }))}">`
          + `${escapeHtml(ticker)} <span class="ticker-ext">↗</span></a>`
      : '<span class="muted">—</span>';

    // === Unified primary-source data ===
    // 1차 출처(IDX_XBRL or AUDITED_AR)에서만 읽음. 회사별 latest primary year를 선택
    // (FY25가 없으면 FY24로 fallback — SGX/NYSE 회사들은 보통 FY25 미수집).
    const bare = _bareTicker(ticker);
    const company = (bare && financialsByTicker) ? financialsByTicker[bare.toUpperCase()] : null;
    let companyYear = null;
    if (company?.yearly) {
      const candidateYears = Object.keys(company.yearly).sort().reverse();
      for (const y of candidateYears) {
        const src = (company.yearly[y]?.sources || [])[0];
        if (src && PRIMARY_SOURCE_TYPES.has(src.source_type)) {
          companyYear = y;
          break;
        }
      }
    }
    const yblock = companyYear ? company.yearly[companyYear] : null;
    const primarySrc = (yblock?.sources || [])[0];
    const sourceType = primarySrc?.source_type;
    const isPrimary = PRIMARY_SOURCE_TYPES.has(sourceType);
    const xb = isPrimary ? yblock : null;
    // 회사 연도가 global 최신과 다르면 표 셀에 FY 접미사 표시
    const yearSuffix = (companyYear && companyYear !== xbrlYearKey)
      ? ` <span class="fy-suffix" title="이 회사 최신 감사필 연도">FY${companyYear.slice(-2)}</span>`
      : '';

    // 회사 통화 (SGX 회사는 SGD로 표기)
    const ccy = company?.currency || 'IDR';
    const ccyTag = (ccy !== 'IDR') ? ` <span class="ccy-tag" title="${escapeHtml(ccy)} (회사 보고 통화)">${escapeHtml(ccy)}</span>` : '';
    const revHtml = fmtNumOrDash(xb?.revenue) + yearSuffix + ccyTag;
    const gpHtml = fmtNumOrDash(xb?.gross_profit);
    const opHtml = fmtNumOrDash(xb?.operating_profit);
    const npHtml = fmtNumOrDash(xb?.net_profit);
    const taHtml = fmtNumOrDash(xb?.total_assets);
    const tlHtml = fmtNumOrDash(xb?.total_liabilities);
    const teHtml = fmtNumOrDash(xb?.total_equity);
    const epsHtml = fmtEps(xb?.eps);

    const memHtml = fin.membership_price_idr != null ? escapeHtml(fmtBigIDR(fin.membership_price_idr) || '')
      : (fin.membership_price_usd != null ? `$${fin.membership_price_usd.toLocaleString('en-US')}` : '<span class="muted">—</span>');

    const tickerHtml = tickerLinkHtml;

    // Trend column: opens 5y modal if we have data for the parent ticker.
    const has5y = bare && financialsByTicker && financialsByTicker[bare.toUpperCase()];
    const trendHtml = has5y
      ? `<button class="trend-btn" type="button" data-ticker="${escapeHtml(bare)}"`
        + ` title="${escapeHtml(t('finance.trendTitle', { ticker: bare }))}">📈 5Y</button>`
      : `<span class="muted" title="${escapeHtml(t('finance.trendNoData'))}">—</span>`;

    return `<tr>
      <td><strong>${escapeHtml(c.name_en)}</strong></td>
      <td>${escapeHtml(c.region || '—')}</td>
      <td>${escapeHtml(fin.parent_group || fin.parent_company_full_name || '—')}</td>
      <td>${escapeHtml(fin.operating_company || '—')}</td>
      <td>${escapeHtml(LISTED_STATUS_LABEL[fin.listed_status] || fin.listed_status || '—')}</td>
      <td>${tickerHtml}</td>
      <td class="num">${revHtml}</td>
      <td class="num">${gpHtml}</td>
      <td class="num">${opHtml}</td>
      <td class="num">${npHtml}</td>
      <td class="num">${taHtml}</td>
      <td class="num">${tlHtml}</td>
      <td class="num">${teHtml}</td>
      <td class="num">${epsHtml}</td>
      <td class="num">${memHtml}</td>
      <td class="trend-cell">${trendHtml}</td>
    </tr>`;
  }).join('');
}

// Click handler for the new "재무 추이" column — opens the existing
// 5-year ticker modal (renderTickerModal) which already has Chart.js
// visualizations for revenue, net profit, total assets, and balance.
document.addEventListener('click', async (e) => {
  const btn = e.target.closest('.trend-btn[data-ticker]');
  if (!btn) return;
  e.preventDefault();
  const ticker = btn.dataset.ticker;
  await loadFinancialsIfNeeded();
  renderTickerModal(ticker);
});

document.getElementById('financeSearch')?.addEventListener('input', renderFinanceTable);
document.getElementById('financeStatusFilter')?.addEventListener('change', renderFinanceTable);

// === Analytics tab ===
const _charts = {};

function destroyChart(key) {
  if (_charts[key]) {
    try { _charts[key].destroy(); } catch (e) { /* ignore */ }
    _charts[key] = null;
  }
}

function chartTheme() {
  const dark = document.documentElement.dataset.theme === 'dark';
  const cs = getComputedStyle(document.documentElement);
  return {
    grid:  dark ? 'rgba(255,255,255,0.06)' : 'rgba(10,31,23,0.06)',
    axis:  cs.getPropertyValue('--text-muted').trim() || (dark ? '#94a3b8' : '#8a9892'),
    text:  cs.getPropertyValue('--text-primary').trim() || (dark ? '#e8ebe7' : '#0a1f17'),
    accent: cs.getPropertyValue('--accent').trim() || (dark ? '#2eb478' : '#0d6e4d'),
    gold:  cs.getPropertyValue('--gold').trim() || '#b8924a',
  };
}

function fmtBigIDRShort(n) {
  if (n == null) return '—';
  const num = Number(n);
  if (!isFinite(num)) return '—';
  const abs = Math.abs(num);
  if (abs >= 1e12) return `${(num / 1e12).toFixed(2)}T`;
  if (abs >= 1e9)  return `${(num / 1e9).toFixed(1)}B`;
  if (abs >= 1e6)  return `${Math.round(num / 1e6)}M`;
  return num.toLocaleString('en-US');
}

function renderAnalytics() {
  if (typeof Chart === 'undefined' || !allCourses.length) return;
  // NOTE: keep this name `theme` (not `t`) — `t` is the i18n helper and
  // shadowing it here breaks every t('...') call further down the function.
  const theme = chartTheme();
  Chart.defaults.color = theme.axis;
  Chart.defaults.borderColor = theme.grid;
  Chart.defaults.font.family = "'Pretendard', 'Inter', sans-serif";

  // KPIs
  const counts = computeStatusCounts(allCourses);
  const prices = allCourses
    .map(c => ({ c, p: getSatAmIDR(c), op: (c.operating_status?.status || 'operating') === 'operating' }))
    .filter(x => x.p != null && x.op);
  const sorted = prices.map(x => x.p).sort((a, b) => a - b);
  const median = sorted[Math.floor(sorted.length / 2)] || 0;
  const avg = sorted.length ? sorted.reduce((a, b) => a + b, 0) / sorted.length : 0;
  const maxRow = prices.reduce((m, x) => x.p > m.p ? x : m, prices[0] || { p: 0 });

  const setText = (id, v) => { const el = document.getElementById(id); if (el) el.textContent = v; };

  // Count-up animation for numeric KPI values (skips when reduce-motion is set)
  const reduceMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
  const countUp = (id, target, format = (n) => String(n), duration = 700) => {
    const el = document.getElementById(id);
    if (!el) return;
    if (reduceMotion || target === 0) { el.textContent = format(target); return; }
    const start = performance.now();
    const tick = (now) => {
      const t = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - t, 3); // easeOutCubic
      el.textContent = format(Math.round(target * eased));
      if (t < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  };
  countUp('kpiTotal', counts.total);
  setText('kpiOperating', counts.operating);
  if (avg) countUp('kpiAvgPrice', Math.round(avg), n => fmtIDR(n) || '—');
  else setText('kpiAvgPrice', '—');
  setText('kpiMedianPrice', median ? fmtIDR(median) : '—');
  if (maxRow.p) countUp('kpiMaxPrice', maxRow.p, n => fmtIDR(n) || '—');
  else setText('kpiMaxPrice', '—');
  setText('kpiMaxName', maxRow.c?.name_en || '—');
  const listedCount = allCourses.filter(c => {
    const ls = c.financials?.listed_status;
    return ls === 'listed' || ls === 'subsidiary-of-listed';
  }).length;
  countUp('kpiListedCount', listedCount);

  // 1) Price distribution histogram
  const buckets = [
    { lo: 0,         hi: 250000,    label: '<250K' },
    { lo: 250000,    hi: 500000,    label: '250-500K' },
    { lo: 500000,    hi: 750000,    label: '500-750K' },
    { lo: 750000,    hi: 1000000,   label: '750K-1M' },
    { lo: 1000000,   hi: 1500000,   label: '1-1.5M' },
    { lo: 1500000,   hi: 2000000,   label: '1.5-2M' },
    { lo: 2000000,   hi: 3000000,   label: '2-3M' },
    { lo: 3000000,   hi: Infinity,  label: '3M+' },
  ];
  const distCounts = buckets.map(b => prices.filter(x => x.p >= b.lo && x.p < b.hi).length);

  destroyChart('priceDist');
  _charts.priceDist = new Chart(document.getElementById('chartPriceDist'), {
    type: 'bar',
    data: {
      labels: buckets.map(b => b.label),
      datasets: [{
        label: t('an.coursesCount'),
        data: distCounts,
        backgroundColor: theme.accent,
        borderRadius: 4,
      }],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        y: { beginAtZero: true, grid: { color: theme.grid }, ticks: { precision: 0 } },
        x: { grid: { display: false } },
      },
    },
  });

  // 2) Region average bar
  const regionAgg = {};
  for (const x of prices) {
    const r = x.c.region;
    if (!r) continue;
    (regionAgg[r] ??= []).push(x.p);
  }
  const regionRows = Object.entries(regionAgg)
    .filter(([, arr]) => arr.length >= 3)
    .map(([r, arr]) => ({ r, avg: arr.reduce((a, b) => a + b, 0) / arr.length, n: arr.length }))
    .sort((a, b) => b.avg - a.avg);

  destroyChart('regionAvg');
  _charts.regionAvg = new Chart(document.getElementById('chartRegionAvg'), {
    type: 'bar',
    data: {
      labels: regionRows.map(x => `${x.r} (${x.n})`),
      datasets: [{
        label: t('an.avgSatAm'),
        data: regionRows.map(x => Math.round(x.avg)),
        backgroundColor: theme.gold,
        borderRadius: 4,
      }],
    },
    options: {
      indexAxis: 'y',
      responsive: true, maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: { callbacks: { label: ctx => `Rp ${(ctx.raw / 1e6).toFixed(2)}M` } },
      },
      scales: {
        x: { beginAtZero: true, grid: { color: theme.grid },
             ticks: { callback: v => 'Rp ' + (v / 1e6).toFixed(1) + 'M' } },
        y: { grid: { display: false } },
      },
    },
  });

  // 3) Status donut
  destroyChart('status');
  _charts.status = new Chart(document.getElementById('chartStatus'), {
    type: 'doughnut',
    data: {
      labels: [t('status.operating'), t('status.closed'), t('status.uncertain')],
      datasets: [{
        data: [counts.operating, counts.closed, counts.uncertain],
        backgroundColor: ['#16a34a', '#94a3b8', '#f59e0b'],
        borderWidth: 0,
      }],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      cutout: '62%',
      plugins: {
        legend: { position: 'bottom', labels: { boxWidth: 12, padding: 10 } },
      },
    },
  });

  // 4) Parent revenue Top 10
  const parentAgg = {};
  for (const c of allCourses) {
    const fin = c.financials;
    if (!fin) continue;
    if (!(fin.listed_status === 'listed' || fin.listed_status === 'subsidiary-of-listed')) continue;
    const rev = fin.revenue_idr ?? fin.revenue_idr_h1;
    if (rev == null) continue;
    const key = fin.parent_group || fin.parent_company_full_name || c.name_en;
    // Keep one record per parent (highest rev to dedupe sibling courses)
    if (!parentAgg[key] || parentAgg[key].rev < rev) parentAgg[key] = { rev, name: key };
  }
  const top10 = Object.values(parentAgg).sort((a, b) => b.rev - a.rev).slice(0, 10);

  destroyChart('parentRevenue');
  _charts.parentRevenue = new Chart(document.getElementById('chartParentRevenue'), {
    type: 'bar',
    data: {
      labels: top10.map(x => x.name.length > 28 ? x.name.slice(0, 28) + '…' : x.name),
      datasets: [{
        label: t('an.parentRev'),
        data: top10.map(x => x.rev / 1e12),
        backgroundColor: theme.accent,
        borderRadius: 4,
      }],
    },
    options: {
      indexAxis: 'y',
      responsive: true, maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: { callbacks: { label: ctx => `Rp ${ctx.raw.toFixed(2)}T` } },
      },
      scales: {
        x: { beginAtZero: true, grid: { color: theme.grid },
             ticks: { callback: v => v + 'T' } },
        y: { grid: { display: false } },
      },
    },
  });

  // 5) Designer top 12
  const designerCounts = {};
  for (const c of allCourses) {
    if (!c.designer) continue;
    const first = c.designer.split(',')[0].split('(')[0].trim();
    if (!first) continue;
    designerCounts[first] = (designerCounts[first] || 0) + 1;
  }
  const designerTop = Object.entries(designerCounts)
    .map(([name, n]) => ({ name, n }))
    .sort((a, b) => b.n - a.n)
    .slice(0, 12);
  destroyChart('designer');
  _charts.designer = new Chart(document.getElementById('chartDesigner'), {
    type: 'bar',
    data: {
      labels: designerTop.map(x => x.name.length > 24 ? x.name.slice(0, 24) + '…' : x.name),
      datasets: [{
        label: t('an.coursesCount'),
        data: designerTop.map(x => x.n),
        backgroundColor: theme.gold,
        borderRadius: 4,
      }],
    },
    options: {
      indexAxis: 'y',
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { beginAtZero: true, grid: { color: theme.grid }, ticks: { precision: 0 } },
        y: { grid: { display: false } },
      },
    },
  });

  // 6) Opening-year timeline (10-year buckets)
  const yearBins = {};
  for (const c of allCourses) {
    if (!c.year_opened) continue;
    const decade = Math.floor(c.year_opened / 10) * 10;
    yearBins[decade] = (yearBins[decade] || 0) + 1;
  }
  const decades = Object.keys(yearBins).map(Number).sort((a, b) => a - b);
  // Fill missing decades with 0 for a continuous timeline
  if (decades.length) {
    const lo = decades[0], hi = decades[decades.length - 1];
    for (let d = lo; d <= hi; d += 10) yearBins[d] = yearBins[d] || 0;
  }
  const decadesFilled = Object.keys(yearBins).map(Number).sort((a, b) => a - b);

  destroyChart('timeline');
  _charts.timeline = new Chart(document.getElementById('chartTimeline'), {
    type: 'bar',
    data: {
      labels: decadesFilled.map(d => `${d}s`),
      datasets: [{
        label: t('an.openedCount'),
        data: decadesFilled.map(d => yearBins[d]),
        backgroundColor: theme.accent,
        borderRadius: 3,
        barPercentage: 0.85,
      }],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        y: { beginAtZero: true, grid: { color: theme.grid }, ticks: { precision: 0 } },
        x: { grid: { display: false } },
      },
    },
  });

  // 7) Scatter holes × price
  const STATUS_COLOR = {
    operating: '#16a34a',
    closed_temporary: '#94a3b8',
    closed_permanent: '#64748b',
    uncertain: '#f59e0b',
  };
  const points = [];
  for (const c of allCourses) {
    const p = getSatAmIDR(c);
    if (p == null || c.holes == null) continue;
    const op = c.operating_status?.status || 'operating';
    const rev = c.financials?.revenue_idr ?? c.financials?.revenue_idr_h1 ?? 0;
    points.push({
      x: c.holes,
      y: p / 1e6,
      r: Math.max(4, Math.min(18, 4 + Math.log10((rev || 1e9) / 1e9) * 4)),
      backgroundColor: STATUS_COLOR[op] || '#16a34a',
      label: c.name_en,
    });
  }
  destroyChart('scatter');
  _charts.scatter = new Chart(document.getElementById('chartScatter'), {
    type: 'bubble',
    data: { datasets: [{ label: t('an.course'), data: points,
      backgroundColor: points.map(p => p.backgroundColor + 'cc'),
      borderColor: points.map(p => p.backgroundColor),
      borderWidth: 1,
    }] },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: { callbacks: {
          label: ctx => {
            const d = ctx.raw;
            return `${d.label}: ${d.x}${t('an.holesUnit')} / Rp ${d.y.toFixed(2)}M`;
          }
        } },
      },
      scales: {
        x: { title: { display: true, text: t('an.holes') },
             grid: { color: theme.grid }, ticks: { stepSize: 9 } },
        y: { title: { display: true, text: t('an.satAmFee') },
             grid: { color: theme.grid }, beginAtZero: true },
      },
    },
  });
}

// Re-render charts on theme change
const _themeObserver = new MutationObserver(() => {
  if (document.getElementById('analyticsView') &&
      !document.getElementById('analyticsView').hidden) {
    renderAnalytics();
  }
});
_themeObserver.observe(document.documentElement,
  { attributes: true, attributeFilter: ['data-theme'] });

// === i18n ===
const I18N = {
  ko: {
    'tab.map': '지도',
    'tab.table': '가격 데이터',
    'tab.finance': '재무 분석',
    'tab.analytics': '대시보드',
    'tab.operations': '운영 벤치마크 ↗',

    'finance.hint': '💡 모든 수치는 1차 감사필 출처(IDX XBRL 또는 audited AR PDF)에서 직접 추출 — IDX 상장사는 매주 일요일 자동 갱신. <strong>티커</strong> 클릭 → Yahoo Finance · <strong>재무 추이</strong> 클릭 → 5Y 그래프.',

    'filter.active': '활성 필터',
    'filter.reset': '초기화',
    'filter.region': '지역',
    'filter.holes': '홀 수',
    'filter.status': '운영 상태',
    'filter.price': '가격대 (토 AM 그린피, IDR)',
    'filter.all': '전체',
    'filter.holes9': '9홀',
    'filter.holes18': '18홀',
    'filter.holes27': '27홀+',
    'filter.statusOpOnly': '운영중만',
    'filter.statusClosed': '휴장',
    'filter.statusUncertain': '불확실',
    'filter.includeUnknown': '가격 미상도 포함',

    'search.placeholder': '🔍 골프장 이름·지역·설계자 검색',

    'analytics.title': '인도네시아 골프장 대시보드',
    'analytics.subtitle': '137개 코스의 가격·지역·운영상태·재무 데이터를 한눈에',
    'kpi.total': '전체 골프장',
    'kpi.operating': '운영중',
    'kpi.avg': '평균 토 AM 그린피',
    'kpi.median': '중앙값',
    'kpi.max': '최고가',
    'kpi.listed': '상장 그룹 산하',
    'kpi.listedFoot': '개별 코스 (모회사 IDX)',

    'chart.priceDist': '토 AM 그린피 분포',
    'chart.priceDistDesc': '운영중 코스 기준, IDR 가격대별 코스 수',
    'chart.regionAvg': '지역별 평균 토 AM 그린피',
    'chart.regionAvgDesc': '코스 3개 이상 지역만 (가격 데이터 보유 코스만 포함)',
    'chart.status': '운영 상태 분포',
    'chart.statusDesc': '137개 전체 기준',
    'chart.parentRev': '모회사 매출 Top 10 (FY2024-25)',
    'chart.parentRevDesc': '상장사·자회사 기준, IDR Trillion · BKDP·BSDE·BKSL·SMRA·GOLF는 FY2025 / 그 외 FY2024',
    'chart.scatter': '홀 수 × 가격 산점도',
    'chart.scatterDesc': '9/18/27홀 코스의 토 AM 가격 분포 — 마커 크기는 모회사 매출, 색상은 운영 상태',
    'chart.designer': '설계자별 코스 수 (Top 12)',
    'chart.designerDesc': '유명 코스 설계자가 인도네시아에 남긴 코스 수',
    'chart.timeline': '개장년도 타임라인',
    'chart.timelineDesc': '1872년 식민지 시대부터 2025년까지의 개장 분포',

    // Common
    'common.close': '닫기',
    'common.loading': '로딩 중...',
    'common.dataLoadFailed': '데이터 로딩 실패',
    'common.noResults': '검색 결과 없음',
    'common.private': '비공개',
    'common.unknown': '정보 없음',
    'common.none': '없음',
    'common.all': '전체',
    'common.year': '년',
    'common.holesUnit': '홀',
    'common.peopleUnit': '명',
    'common.itemsUnit': '개',

    // Header / footer
    'header.loading': '데이터 로딩 중…',
    'header.totalLine': '총 <strong>{total}</strong> · <span class="status-dot operating" aria-hidden="true"></span>운영중 {operating} · <span class="status-dot closed" aria-hidden="true"></span>휴장 {closed} · <span class="status-dot uncertain" aria-hidden="true"></span>불확실 {uncertain}',
    'header.totalText': '총 {total} 골프장 (운영중 {operating} · 휴장 {closed} · 불확실 {uncertain})',
    'header.counterPill': '{total} (운영 {operating})',
    'theme.toggle': '다크모드 전환',
    'sidebar.toggle': '사이드바 토글',
    'price.min': '최소 가격',
    'price.max': '최대 가격',

    'footer.dataSrc': '데이터 출처',
    'footer.officialSite': '공식 골프장 사이트',
    'footer.map': '지도',
    'footer.geocode': '지오코딩',

    // Region multi
    'region.all': '전체 지역',
    'region.allRegions': '모든 지역',
    'region.search': '지역 검색…',
    'region.selectAll': '전체 선택',
    'region.clear': '선택 해제',
    'region.selectedSummary': '{first} 외 {extra}개',

    // Empty states
    'empty.title': '조건에 맞는 골프장이 없습니다',
    'empty.hint': '검색어·지역·가격대 필터를 완화하거나, 운영 상태를 "전체"로 바꿔 보세요.',
    'empty.hint2': '검색어를 비우거나, 운영 상태를 "전체"로 바꿔 보세요.',
    'empty.cta': '필터 초기화',
    'empty.financeTitle': '조건에 맞는 재무 정보가 없습니다',
    'empty.financeHint': '상장 구분 필터를 "전체"로 바꾸거나 검색어를 비워 보세요.',

    // Status labels
    'status.operating': '운영중',
    'status.operatingOnly': '운영중만',
    'status.closed': '휴장',
    'status.closedTemp': '임시 휴장',
    'status.closedPerm': '영구 폐장',
    'status.uncertain': '불확실',
    'status.banner.closed': '⚠️ {label} — {reason}{reopened}',
    'status.banner.uncertain': '❓ 운영 상태 불확실 — 사전 연락 권장',
    'status.reasonPerm': '영구 폐장',
    'status.reasonReno': '리노베이션 / 임시 휴장',

    // Marker popup / detail panel
    'popup.region': '지역',
    'popup.operating': '운영',
    'popup.holesPar': '홀/파',
    'popup.opened': '개장',
    'popup.designer': '설계자',
    'popup.weekdayWeekend': '평일/주말',
    'popup.membership': '멤버십',
    'popup.officialWeb': '공식 웹사이트',
    'popup.googleMap': '구글 지도',
    'popup.detailBtn': '상세 정보 →',

    'detail.holes': '홀',
    'detail.par': '파',
    'detail.opened': '개장',
    'detail.address': '주소',
    'detail.coordNotes': '좌표 신뢰도 메모',
    'detail.designer': '설계자',
    'detail.layout': '코스 구성',
    'detail.facilities': '부대시설',
    'detail.officialWebLink': '공식 웹사이트 →',
    'detail.googleMapOpen': 'Google 지도 열기 →',
    'detail.coordApprox': '좌표 근사',
    'detail.verifiedDate': '확인일 {date}',

    // Operating evidence
    'evidence.title': '운영 상태 근거',
    'evidence.none': '근거 없음',
    'conf.high': '신뢰도 높음',
    'conf.medium': '신뢰도 보통',
    'conf.low': '신뢰도 낮음',

    // Price matrix
    'matrix.title': '가격 매트릭스',
    'matrix.hint': '셀 클릭 → 출처별 비교',
    'matrix.weekday': '평일',
    'matrix.sat': '토',
    'matrix.sun': '일',

    // Source history
    'history.title': '출처별 가격 이력',
    'history.original': '원문 ↗',
    'history.refOnly': '참고용',
    'history.crawled': '자동 · Tier {tier}{pdf}',
    'history.crawledTitle': '자동 크롤로 추출된 출처',
    'history.collapseTag': '{n}개 추출/median',
    'history.collapseTitle': '이 페이지에서 {n}개 가격 추출 → median 사용',
    'history.extraSrc': '추가 출처',
    'history.extraSrcTitle': '동일 가격을 게시한 추가 출처',

    // Slot labels
    'slot.wdAm': '평일 AM',
    'slot.wdPm': '평일 PM',
    'slot.satAm': '토 AM',
    'slot.satPm': '토 PM',
    'slot.sunAm': '일 AM',
    'slot.sunPm': '일 PM',
    'slot.weekday': '평일',
    'slot.weekendSat': '토요일',
    'slot.weekendSun': '일요일',
    'slot.holiday': '공휴일',

    // Membership
    'member.section': '회원권 (멤버십)',
    'member.grade': '등급',
    'member.cost': '비용',
    'member.initFee': '가입비',
    'member.annualFee': '연회비',
    'member.monthlyFee': '월회비',
    'member.deposit': '예치금',
    'member.noDataNote': '공개된 가입비·연회비 정보가 없습니다. 회원권 문의는 클럽으로 직접 연락이 필요합니다.',
    'member.recruiting': '회원 모집 중',
    'member.employees': '직원 전용',
    'member.military': '군 전용',
    'member.militaryPersonnel': '군인 전용',
    'member.invitation': '초대제',
    'member.invitationOnly': '초대제 (비공개)',
    'member.membersOnly': '멤버 전용 (양도시장)',
    'member.membersOnlyShort': '회원 전용',
    'member.cellInit': '가입 {amt}',
    'member.cellAnnual': '연 {amt}',
    'member.cellMonthly': '월 {amt}',

    // Listed status
    'listed.listed': '상장',
    'listed.subsidiary-of-listed': '상장사 자회사',
    'listed.private': '비상장',
    'listed.state-owned': '국영기업',
    'listed.government': '정부 운영',
    'listed.local-government': '지방정부',
    'listed.military': '군 운영',
    'listed.foundation': '재단',
    'listed.joint-venture': '합작법인',
    'listed.plantation-soe': '국영농장',
    'listed.tbk-reporting-not-yet-traded': 'Tbk(IDX 미거래)',
    'listed.bumn-subsidiary': 'BUMN 자회사(미상장)',
    'listed.unknown': '미확인',

    // Financials
    'fin.section': '기업·재무 정보',
    'fin.opCompany': '운영법인',
    'fin.parent': '모회사·기업집단',
    'fin.ticker': '상장 티커',
    'fin.listedStatus': '상장 구분',
    'fin.revenue': '매출',
    'fin.revenueWith': '매출 ({year})',
    'fin.revenueH1': '매출 (H1-{year})',
    'fin.netProfit': '순이익',
    'fin.netProfitH1': '순이익 (H1)',
    'fin.totalAssets': '총자산',
    'fin.employees': '직원수',
    'fin.investment': '투자/개발비',
    'fin.investmentUsd': '투자 (USD)',
    'fin.golfSegment': '골프 세그먼트 매출',
    'fin.golfSegmentLabel': '골프 세그먼트',
    'fin.segDisclosed': '별도공시',
    'fin.segDisclosedNote': '(별도공시)',
    'fin.membership': '회원권',
    'fin.dataReliability': '데이터 신뢰도',
    'fin.recentNews': '최근 이슈',
    'fin.memberNote': '회원권 메모:',
    'fin.ownerNote': '소유 메모:',
    'fin.sources': '출처({n})',
    'fin.kindParent': '모회사',
    'fin.kindMember': '회원권',
    'fin.totalKept': '전체 재무 보유',

    // Fees / pricing
    'fee.title': '이용금액 ({date})',
    'fee.dateMay': '2026년 5월',
    'fee.weekday': '평일 그린피',
    'fee.weekend': '주말 그린피',
    'fee.twilight': '트와일라잇',
    'fee.caddy': '캐디피',
    'fee.cart': '카트',
    'fee.insurance': '보험',
    'fee.tax': '세금(PPN)',
    'fee.taxIncluded': '(포함)',
    'fee.rateIncludes': '요금 구성',
    'fee.detailed': '상세 시간/세그먼트별 요율',
    'fee.sources': '출처',
    'fee.caddyShort': '캐디',
    'fee.cartShort': '카트',
    'fee.member': '멤버',

    // Source labels (URL categorization)
    'src.official': '공식',
    'src.disclosure': '공시',
    'src.reservation': '예약',
    'src.sns': 'SNS',
    'src.news': '뉴스/매거진',
    'src.gov': '관공서',

    // Source category labels
    'srcCat.official': '공시·공식',
    'srcCat.platform': '플랫폼',
    'srcCat.aggregator': '애그리게이터',
    'srcCat.sns': 'SNS',
    'srcCat.news': '뉴스·기타',

    // Source tab labels (HTML attrs)
    'srcTabs.label': '요금 출처 카테고리',
    'srcTabs.prefix': '요금 출처:',
    'srcTabs.official': '공시',
    'srcTabs.sns': 'SNS',
    'srcTabs.platform': '전문 골프 플랫폼',
    'srcTabs.aggregator': '글로벌 애그리게이터',
    'srcTabs.news': '뉴스·미디어·예약',

    // Source tab descriptions
    'srcDesc.all': '필터에 해당하는 모든 골프장의 통합 정보 — 요금·멤버십·모회사 재무·전체 출처를 한 표에서 확인',
    'srcDesc.official': '공식 골프장 사이트 · 거래소(IDX) 공시 · OJK · 관공서(.go.id, .mil.id) — 1차 출처 기준 요금',
    'srcDesc.sns': 'Instagram · Facebook · X(Twitter) · TikTok · Threads — 공식 채널 게시물 (요금은 1차 출처와 동일)',
    'srcDesc.platform': 'Q-Access · GoGolf · playgolf.id — 인도네시아 현지 전문 골프 플랫폼. <strong>GoGolf 참고가</strong>가 있을 경우 해당 가격으로 표시 (참고용 비공식 가격)',
    'srcDesc.aggregator': 'GolfSavers · GolfAsian · GolfPass · GolfLux · Hole19 · GreenFee365 · Golfshake — 해외 애그리게이터 (요금은 1차 출처와 동일)',
    'srcDesc.news': '현지 뉴스/매거진 · 예약 채널(Klook, Traveloka, Agoda 등) · Wayback 아카이브 (요금은 1차 출처와 동일)',

    // Source column header
    'srcCol.all': '전체 출처',
    'srcCol.official': '공식·공시 출처',
    'srcCol.sns': 'SNS 채널',
    'srcCol.platform': '전문 골프 플랫폼 출처',
    'srcCol.aggregator': '애그리게이터 출처',
    'srcCol.news': '뉴스·예약·기타 출처',

    // Map controls
    'map.legendStatus': '운영 상태',
    'map.legendHoles': '홀 수',
    'map.legend9': '9홀 이하',
    'map.legend18': '18홀',
    'map.legend27': '27홀 이상',
    'map.zoomAll': '전체',
    'map.mapLink': '지도',

    // Map list
    'list.weekdayPrefix': '평일',

    // Table view
    'table.searchPh': '🔍 검색 (이름·지역·설계자·주소)',
    'table.showing': '개 표시',
    'table.showFinance': '재무 컬럼 표시',
    'table.csvDownload': '📥 CSV 다운로드',
    'table.sameRate': '동일',
    'table.gogolfNote': 'GoGolf 참고가',
    'table.gogolfDisclaimer': '참고용 비공식 가격',

    'th.name': '골프장명',
    'th.region': '지역',
    'th.province': '주(Province)',
    'th.status': '운영상태',
    'th.holes': '홀',
    'th.opened': '개장',
    'th.weekday': '평일',
    'th.saturday': '토',
    'th.sunday': '일',
    'th.memberType': '멤버십 종류',
    'th.memberFee': '멤버십 금액',
    'th.parent': '모회사·기업집단',
    'th.ticker': '티커',
    'th.parentRev': '모회사 매출',
    'th.address': '주소',
    'th.opCompany': '운영법인',
    'th.listedStatus': '상장 구분',
    'th.revenueFY': '매출 (FY)',
    'th.netProfit': '순이익',
    'th.totalAssets': '총자산',
    'th.membership': '회원권',
    'th.trend': '재무 추이',
    'th.sources': '출처',

    // Finance view
    'finance.searchPh': '🔍 검색 (이름·모회사·티커)',
    'finance.statusAll': '전체 (재무 정보 보유)',
    'finance.statusListed': '상장사만',
    'finance.statusSubsidiary': '상장사 자회사',
    'finance.statusTbk': 'Tbk 등록 (IDX 미거래)',
    'finance.counterSep': '개 / 85',
    'finance.viewSrc': '{n}개 출처 ↗',
    'finance.invalidSrc': '{n}개 (URL 없음)',
    'finance.invalidSrcTitle': '등록된 출처 {n}개 모두 유효한 URL이 아님',
    'finance.tickerOpen': 'Yahoo Finance에서 {ticker} 열기',
    'finance.trendTitle': '{ticker} 5년 매출·순이익·자산 추이 보기',
    'finance.trendNoData': '해당 모회사의 다년치 재무 데이터가 아직 준비되지 않음',

    // Ticker modal
    'ticker.notReady': '티커 <strong>{ticker}</strong>의 5년치 상세 재무 데이터가 아직 준비되지 않았습니다. (조사 진행 중)',
    'ticker.notReadyHint': '데이터가 추가되면 매출/순이익/총자산 5년 추이 그래프와 표를 이 위치에서 확인할 수 있습니다.',
    'ticker.summary': '📈 5년 재무 요약',
    'ticker.tableTitle': '📋 연도별 상세 ({currency})',
    'ticker.sourcesTitle': '🔗 출처 (전 연도 통합)',
    'ticker.metricItem': '항목',
    'ticker.metric.revenue': '매출',
    'ticker.metric.operating_profit': '영업이익',
    'ticker.metric.net_profit': '순이익',
    'ticker.metric.ebitda': 'EBITDA',
    'ticker.metric.total_assets': '총자산',
    'ticker.metric.total_liabilities': '총부채',
    'ticker.metric.total_equity': '자기자본',
    'ticker.metric.eps': 'EPS',
    'ticker.metric.dividend_per_share': 'DPS',
    'ticker.metric.employees': '직원수',
    'ticker.chart.revenue': '매출 (Revenue)',
    'ticker.chart.netprofit': '순이익 (Net Profit)',
    'ticker.chart.assets': '총자산 (Total Assets)',
    'ticker.chart.balance': '자산 vs 부채 vs 자본',
    'ticker.line.liab': '부채',
    'ticker.line.equity': '자본',
    'ticker.line.revenue': '매출',
    'ticker.line.netprofit': '순이익',
    'ticker.line.assets': '총자산',
    'ticker.unitFooter': '확인일 {date} · 단위 {unit}',
    'ticker.unitIDR': 'IDR (T=조, B=십억, M=백만)',
    'ticker.unitIDREquiv': ' · 작은 숫자는 IDR 환산값',
    'ticker.noSources': '출처 정보 없음',

    // Price modal
    'priceModal.noData': '출처 데이터 없음',
    'priceModal.noDataMsg': '이 시간대에 등록된 가격 정보가 없습니다.',
    'priceModal.gogolfExtract': 'gogolf.co.id 추출',
    'priceModal.crawled': '자동 크롤 (Tier {tier}{pdf})',
    'priceModal.collapsed': '페이지 내 {n}개 가격 추출 → median 사용',
    'priceModal.verified': '확인 {date}',
    'priceModal.trusted': '· 신뢰 우선',
    'priceModal.diffNote': '출처별 차이 <strong>{pct}%</strong> ({lo} ~ {hi}){warn}.<br>신뢰도 순서: 공시·공식 → 플랫폼 → SNS → 애그리게이터 → 뉴스',
    'priceModal.diffWarn': ' — 30% 이상 격차로 추가 검증 권장',
    'priceModal.singleSrc': '현재 등록된 출처는 1개. 다른 출처에서 가격이 확인되면 비교 가능.',

    // Analytics labels
    'an.coursesCount': '코스 수',
    'an.avgSatAm': '평균 토 AM (Rp)',
    'an.parentRev': '매출 FY2024-25 (Rp T)',
    'an.openedCount': '개장 코스 수',
    'an.course': '코스',
    'an.holes': '홀 수',
    'an.satAmFee': '토 AM 그린피 (Rp M)',
    'an.holesUnit': '홀',

    // CSV
    'csv.name': '골프장명',
    'csv.region': '지역',
    'csv.province': '주',
    'csv.status': '운영상태',
    'csv.holes': '홀',
    'csv.par': '파',
    'csv.year': '개장연도',
    'csv.designer': '설계자',
    'csv.address': '주소',
    'csv.weekdayFee': '평일그린피(IDR)',
    'csv.weekendFee': '주말그린피(IDR)',
    'csv.weekdayUsd': '평일USD',
    'csv.weekendUsd': '주말USD',
    'csv.caddyFee': '캐디(IDR)',
    'csv.cartFee': '카트(IDR)',
    'csv.insuranceFee': '보험(IDR)',
    'csv.website': '웹사이트',
    'csv.lat': '위도',
    'csv.lng': '경도',
    'csv.note': '특이사항',
    'csv.feeNote': '요금메모',
    'csv.memberAvail': '멤버십가입가능',
    'csv.memberCat': '멤버십카테고리',
    'csv.memberLowest': '멤버십최저비용(IDR환산)',
    'csv.memberNote': '멤버십메모',
    'csv.sources': '출처URL목록',
  },
  en: {
    'tab.map': 'Map',
    'tab.table': 'Price Data',
    'tab.finance': 'Financials',
    'tab.analytics': 'Dashboard',
    'tab.operations': 'Operations Benchmark ↗',

    'finance.hint': '💡 All figures sourced directly from primary audited filings (IDX XBRL or audited AR PDF) — IDX-listed parents refresh weekly. <strong>Ticker</strong> → Yahoo Finance; <strong>Trend</strong> → 5-year charts.',

    'filter.active': 'Active filters',
    'filter.reset': 'Reset',
    'filter.region': 'Region',
    'filter.holes': 'Holes',
    'filter.status': 'Status',
    'filter.price': 'Price range (Sat AM green fee, IDR)',
    'filter.all': 'All',
    'filter.holes9': '9 holes',
    'filter.holes18': '18 holes',
    'filter.holes27': '27+ holes',
    'filter.statusOpOnly': 'Operating only',
    'filter.statusClosed': 'Closed',
    'filter.statusUncertain': 'Uncertain',
    'filter.includeUnknown': 'Include unknown prices',

    'search.placeholder': '🔍 Search by name, region, or designer',

    'analytics.title': 'Indonesia Golf Course Dashboard',
    'analytics.subtitle': 'Pricing, regions, status, and financials across 137 courses at a glance',
    'kpi.total': 'Total courses',
    'kpi.operating': 'operating',
    'kpi.avg': 'Avg. Sat AM green fee',
    'kpi.median': 'median',
    'kpi.max': 'Highest',
    'kpi.listed': 'Listed-group affiliated',
    'kpi.listedFoot': 'individual courses (parent on IDX)',

    'chart.priceDist': 'Sat AM green-fee distribution',
    'chart.priceDistDesc': 'Operating courses, by IDR price band',
    'chart.regionAvg': 'Average Sat AM green fee by region',
    'chart.regionAvgDesc': 'Regions with ≥3 priced courses only',
    'chart.status': 'Operating-status mix',
    'chart.statusDesc': 'All 137 courses',
    'chart.parentRev': 'Parent revenue — Top 10 (FY2024-25)',
    'chart.parentRevDesc': 'Listed companies + subsidiaries, IDR trillion · BKDP/BSDE/BKSL/SMRA/GOLF use FY2025, others FY2024',
    'chart.scatter': 'Holes × price scatter',
    'chart.scatterDesc': 'Sat AM price by hole count — bubble size = parent revenue, color = operating status',
    'chart.designer': 'Top course designers (Top 12)',
    'chart.designerDesc': 'Famous course architects active in Indonesia',
    'chart.timeline': 'Opening-year timeline',
    'chart.timelineDesc': 'From the 1872 colonial era through 2025',

    // Common
    'common.close': 'Close',
    'common.loading': 'Loading...',
    'common.dataLoadFailed': 'Failed to load data',
    'common.noResults': 'No results',
    'common.private': 'Not disclosed',
    'common.unknown': 'Unknown',
    'common.none': 'None',
    'common.all': 'All',
    'common.year': '',
    'common.holesUnit': 'H',
    'common.peopleUnit': '',
    'common.itemsUnit': '',

    // Header / footer
    'header.loading': 'Loading data…',
    'header.totalLine': 'Total <strong>{total}</strong> · <span class="status-dot operating" aria-hidden="true"></span>Operating {operating} · <span class="status-dot closed" aria-hidden="true"></span>Closed {closed} · <span class="status-dot uncertain" aria-hidden="true"></span>Uncertain {uncertain}',
    'header.totalText': 'Total {total} courses (Operating {operating} · Closed {closed} · Uncertain {uncertain})',
    'header.counterPill': '{total} (Operating {operating})',
    'theme.toggle': 'Toggle dark mode',
    'sidebar.toggle': 'Toggle sidebar',
    'price.min': 'Min price',
    'price.max': 'Max price',

    'footer.dataSrc': 'Data sources',
    'footer.officialSite': 'Official course websites',
    'footer.map': 'Map',
    'footer.geocode': 'Geocoding',

    // Region multi
    'region.all': 'All regions',
    'region.allRegions': 'All regions',
    'region.search': 'Search regions…',
    'region.selectAll': 'Select all',
    'region.clear': 'Clear',
    'region.selectedSummary': '{first} +{extra} more',

    // Empty states
    'empty.title': 'No courses match your filters',
    'empty.hint': 'Try relaxing the search/region/price filters, or set status to "All".',
    'empty.hint2': 'Clear the search box, or set status to "All".',
    'empty.cta': 'Reset filters',
    'empty.financeTitle': 'No financial records match',
    'empty.financeHint': 'Set the listed-status filter to "All" or clear the search box.',

    // Status labels
    'status.operating': 'Operating',
    'status.operatingOnly': 'Operating only',
    'status.closed': 'Closed',
    'status.closedTemp': 'Temporarily closed',
    'status.closedPerm': 'Permanently closed',
    'status.uncertain': 'Uncertain',
    'status.banner.closed': '⚠️ {label} — {reason}{reopened}',
    'status.banner.uncertain': '❓ Operating status uncertain — call ahead recommended',
    'status.reasonPerm': 'Permanently closed',
    'status.reasonReno': 'Renovation / temporary closure',

    // Marker popup / detail panel
    'popup.region': 'Region',
    'popup.operating': 'Status',
    'popup.holesPar': 'Holes/Par',
    'popup.opened': 'Opened',
    'popup.designer': 'Designer',
    'popup.weekdayWeekend': 'Weekday/Weekend',
    'popup.membership': 'Membership',
    'popup.officialWeb': 'Official site',
    'popup.googleMap': 'Google Maps',
    'popup.detailBtn': 'Details →',

    'detail.holes': 'Holes',
    'detail.par': 'Par',
    'detail.opened': 'Opened',
    'detail.address': 'Address',
    'detail.coordNotes': 'Coordinate confidence notes',
    'detail.designer': 'Designer',
    'detail.layout': 'Course layout',
    'detail.facilities': 'Facilities',
    'detail.officialWebLink': 'Official website →',
    'detail.googleMapOpen': 'Open in Google Maps →',
    'detail.coordApprox': 'Approx. location',
    'detail.verifiedDate': 'Verified {date}',

    // Operating evidence
    'evidence.title': 'Operating-status evidence',
    'evidence.none': 'No evidence',
    'conf.high': 'High confidence',
    'conf.medium': 'Medium confidence',
    'conf.low': 'Low confidence',

    // Price matrix
    'matrix.title': 'Price matrix',
    'matrix.hint': 'Click a cell to compare sources',
    'matrix.weekday': 'Weekday',
    'matrix.sat': 'Sat',
    'matrix.sun': 'Sun',

    // Source history
    'history.title': 'Price history by source',
    'history.original': 'Original ↗',
    'history.refOnly': 'reference',
    'history.crawled': 'Auto · Tier {tier}{pdf}',
    'history.crawledTitle': 'Auto-crawled source',
    'history.collapseTag': '{n} extracted/median',
    'history.collapseTitle': '{n} prices extracted from this page → median used',
    'history.extraSrc': 'Other sources',
    'history.extraSrcTitle': 'Additional sources publishing the same price',

    // Slot labels
    'slot.wdAm': 'Weekday AM',
    'slot.wdPm': 'Weekday PM',
    'slot.satAm': 'Sat AM',
    'slot.satPm': 'Sat PM',
    'slot.sunAm': 'Sun AM',
    'slot.sunPm': 'Sun PM',
    'slot.weekday': 'Weekday',
    'slot.weekendSat': 'Saturday',
    'slot.weekendSun': 'Sunday',
    'slot.holiday': 'Public holiday',

    // Membership
    'member.section': 'Membership',
    'member.grade': 'Tier',
    'member.cost': 'Cost',
    'member.initFee': 'Initiation',
    'member.annualFee': 'Annual',
    'member.monthlyFee': 'Monthly',
    'member.deposit': 'Deposit',
    'member.noDataNote': 'No public initiation/annual fee information. Contact the club directly for membership inquiries.',
    'member.recruiting': 'Open enrollment',
    'member.employees': 'Employees only',
    'member.military': 'Military only',
    'member.militaryPersonnel': 'Military personnel only',
    'member.invitation': 'By invitation',
    'member.invitationOnly': 'By invitation only (private)',
    'member.membersOnly': 'Members only (transfer market)',
    'member.membersOnlyShort': 'Members only',
    'member.cellInit': 'Init {amt}',
    'member.cellAnnual': 'Annual {amt}',
    'member.cellMonthly': 'Monthly {amt}',

    // Listed status
    'listed.listed': 'Listed',
    'listed.subsidiary-of-listed': 'Subsidiary of listed co.',
    'listed.private': 'Private',
    'listed.state-owned': 'State-owned',
    'listed.government': 'Government-run',
    'listed.local-government': 'Local government',
    'listed.military': 'Military-run',
    'listed.foundation': 'Foundation',
    'listed.joint-venture': 'Joint venture',
    'listed.plantation-soe': 'State plantation (SOE)',
    'listed.tbk-reporting-not-yet-traded': 'Tbk (not yet traded)',
    'listed.bumn-subsidiary': 'BUMN subsidiary (unlisted)',
    'listed.unknown': 'Unknown',

    // Financials
    'fin.section': 'Company & financials',
    'fin.opCompany': 'Operating company',
    'fin.parent': 'Parent / group',
    'fin.ticker': 'Ticker',
    'fin.listedStatus': 'Listing status',
    'fin.revenue': 'Revenue',
    'fin.revenueWith': 'Revenue ({year})',
    'fin.revenueH1': 'Revenue (H1-{year})',
    'fin.netProfit': 'Net profit',
    'fin.netProfitH1': 'Net profit (H1)',
    'fin.totalAssets': 'Total assets',
    'fin.employees': 'Employees',
    'fin.investment': 'Investment / capex',
    'fin.investmentUsd': 'Investment (USD)',
    'fin.golfSegment': 'Golf segment revenue',
    'fin.golfSegmentLabel': 'Golf segment',
    'fin.segDisclosed': 'Disclosed separately',
    'fin.segDisclosedNote': '(disclosed separately)',
    'fin.membership': 'Membership',
    'fin.dataReliability': 'Data reliability',
    'fin.recentNews': 'Recent news',
    'fin.memberNote': 'Membership note:',
    'fin.ownerNote': 'Ownership note:',
    'fin.sources': 'Sources ({n})',
    'fin.kindParent': 'Parent',
    'fin.kindMember': 'Membership',
    'fin.totalKept': 'with financial data',

    // Fees / pricing
    'fee.title': 'Green fees ({date})',
    'fee.dateMay': 'May 2026',
    'fee.weekday': 'Weekday green fee',
    'fee.weekend': 'Weekend green fee',
    'fee.twilight': 'Twilight',
    'fee.caddy': 'Caddy fee',
    'fee.cart': 'Cart',
    'fee.insurance': 'Insurance',
    'fee.tax': 'Tax (PPN)',
    'fee.taxIncluded': '(included)',
    'fee.rateIncludes': 'Rate includes',
    'fee.detailed': 'Detailed schedule by time/segment',
    'fee.sources': 'Sources',
    'fee.caddyShort': 'Caddy',
    'fee.cartShort': 'Cart',
    'fee.member': 'Member',

    // Source labels (URL categorization)
    'src.official': 'Official',
    'src.disclosure': 'Disclosure',
    'src.reservation': 'Booking',
    'src.sns': 'SNS',
    'src.news': 'News/Magazine',
    'src.gov': 'Government',

    // Source category labels
    'srcCat.official': 'Official / Disclosure',
    'srcCat.platform': 'Platform',
    'srcCat.aggregator': 'Aggregator',
    'srcCat.sns': 'SNS',
    'srcCat.news': 'News / Other',

    // Source tab labels (HTML attrs)
    'srcTabs.label': 'Price source category',
    'srcTabs.prefix': 'Source:',
    'srcTabs.official': 'Official',
    'srcTabs.sns': 'SNS',
    'srcTabs.platform': 'Local golf platforms',
    'srcTabs.aggregator': 'Global aggregators',
    'srcTabs.news': 'News / Booking',

    // Source tab descriptions
    'srcDesc.all': 'All courses matching the filters — fees, membership, parent financials, all sources in one table',
    'srcDesc.official': 'Official course sites · IDX disclosures · OJK · Government (.go.id, .mil.id) — primary-source rates',
    'srcDesc.sns': 'Instagram · Facebook · X (Twitter) · TikTok · Threads — official-channel posts (rates same as primary)',
    'srcDesc.platform': 'Q-Access · GoGolf · playgolf.id — Indonesian local golf platforms. Shows <strong>GoGolf reference rate</strong> when present (informal reference price)',
    'srcDesc.aggregator': 'GolfSavers · GolfAsian · GolfPass · GolfLux · Hole19 · GreenFee365 · Golfshake — international aggregators (rates same as primary)',
    'srcDesc.news': 'Local news/magazines · Booking channels (Klook, Traveloka, Agoda, etc.) · Wayback archives (rates same as primary)',

    // Source column header
    'srcCol.all': 'All sources',
    'srcCol.official': 'Official / disclosure sources',
    'srcCol.sns': 'SNS channels',
    'srcCol.platform': 'Platform sources',
    'srcCol.aggregator': 'Aggregator sources',
    'srcCol.news': 'News / booking / other sources',

    // Map controls
    'map.legendStatus': 'Status',
    'map.legendHoles': 'Holes',
    'map.legend9': '≤9 holes',
    'map.legend18': '18 holes',
    'map.legend27': '≥27 holes',
    'map.zoomAll': 'All',
    'map.mapLink': 'Map',

    // Map list
    'list.weekdayPrefix': 'Weekday',

    // Table view
    'table.searchPh': '🔍 Search (name, region, designer, address)',
    'table.showing': ' shown',
    'table.showFinance': 'Show financial columns',
    'table.csvDownload': '📥 Download CSV',
    'table.sameRate': 'same',
    'table.gogolfNote': 'GoGolf reference',
    'table.gogolfDisclaimer': 'Informal reference price',

    'th.name': 'Course',
    'th.region': 'Region',
    'th.province': 'Province',
    'th.status': 'Status',
    'th.holes': 'Holes',
    'th.opened': 'Opened',
    'th.weekday': 'Weekday',
    'th.saturday': 'Sat',
    'th.sunday': 'Sun',
    'th.memberType': 'Membership type',
    'th.memberFee': 'Membership fee',
    'th.parent': 'Parent / group',
    'th.ticker': 'Ticker',
    'th.parentRev': 'Parent revenue',
    'th.address': 'Address',
    'th.opCompany': 'Operating co.',
    'th.listedStatus': 'Listing status',
    'th.revenueFY': 'Revenue (FY)',
    'th.netProfit': 'Net profit',
    'th.totalAssets': 'Total assets',
    'th.membership': 'Membership',
    'th.trend': 'Trend',
    'th.sources': 'Sources',

    // Finance view
    'finance.searchPh': '🔍 Search (name, parent, ticker)',
    'finance.statusAll': 'All (with financial data)',
    'finance.statusListed': 'Listed only',
    'finance.statusSubsidiary': 'Subsidiary of listed',
    'finance.statusTbk': 'Tbk registered (not yet on IDX)',
    'finance.counterSep': ' / 85',
    'finance.viewSrc': '{n} sources ↗',
    'finance.invalidSrc': '{n} (no URL)',
    'finance.invalidSrcTitle': 'None of the {n} registered sources are valid URLs',
    'finance.tickerOpen': 'Open {ticker} on Yahoo Finance',
    'finance.trendTitle': 'View {ticker} 5-year revenue / net profit / assets',
    'finance.trendNoData': 'Multi-year financial data not yet available for this parent',

    // Ticker modal
    'ticker.notReady': '5-year financials for ticker <strong>{ticker}</strong> are not yet available. (Research in progress.)',
    'ticker.notReadyHint': 'Once data is added, you will see 5-year revenue / net profit / total assets charts and tables here.',
    'ticker.summary': '📈 5-year financial summary',
    'ticker.tableTitle': '📋 Yearly detail ({currency})',
    'ticker.sourcesTitle': '🔗 Sources (all years combined)',
    'ticker.metricItem': 'Metric',
    'ticker.metric.revenue': 'Revenue',
    'ticker.metric.operating_profit': 'Operating profit',
    'ticker.metric.net_profit': 'Net profit',
    'ticker.metric.ebitda': 'EBITDA',
    'ticker.metric.total_assets': 'Total assets',
    'ticker.metric.total_liabilities': 'Total liabilities',
    'ticker.metric.total_equity': 'Total equity',
    'ticker.metric.eps': 'EPS',
    'ticker.metric.dividend_per_share': 'DPS',
    'ticker.metric.employees': 'Employees',
    'ticker.chart.revenue': 'Revenue',
    'ticker.chart.netprofit': 'Net Profit',
    'ticker.chart.assets': 'Total Assets',
    'ticker.chart.balance': 'Assets vs Liabilities vs Equity',
    'ticker.line.liab': 'Liabilities',
    'ticker.line.equity': 'Equity',
    'ticker.line.revenue': 'Revenue',
    'ticker.line.netprofit': 'Net profit',
    'ticker.line.assets': 'Total assets',
    'ticker.unitFooter': 'Verified {date} · Unit: {unit}',
    'ticker.unitIDR': 'IDR (T = trillion, B = billion, M = million)',
    'ticker.unitIDREquiv': ' · small numbers are IDR equivalents',
    'ticker.noSources': 'No source information',

    // Price modal
    'priceModal.noData': 'No source data',
    'priceModal.noDataMsg': 'No registered price for this time slot.',
    'priceModal.gogolfExtract': 'Extracted from gogolf.co.id',
    'priceModal.crawled': 'Auto-crawled (Tier {tier}{pdf})',
    'priceModal.collapsed': '{n} prices extracted from page → median used',
    'priceModal.verified': 'Verified {date}',
    'priceModal.trusted': '· primary',
    'priceModal.diffNote': 'Source spread <strong>{pct}%</strong> ({lo} ~ {hi}){warn}.<br>Trust order: Official/Disclosure → Platform → SNS → Aggregator → News',
    'priceModal.diffWarn': ' — over 30% spread, additional verification recommended',
    'priceModal.singleSrc': 'Only one source registered. Comparison enabled when more sources are added.',

    // Analytics labels
    'an.coursesCount': 'Courses',
    'an.avgSatAm': 'Avg Sat AM (Rp)',
    'an.parentRev': 'Revenue FY2024-25 (Rp T)',
    'an.openedCount': 'Courses opened',
    'an.course': 'Course',
    'an.holes': 'Holes',
    'an.satAmFee': 'Sat AM green fee (Rp M)',
    'an.holesUnit': 'H',

    // CSV
    'csv.name': 'Course',
    'csv.region': 'Region',
    'csv.province': 'Province',
    'csv.status': 'Status',
    'csv.holes': 'Holes',
    'csv.par': 'Par',
    'csv.year': 'Year opened',
    'csv.designer': 'Designer',
    'csv.address': 'Address',
    'csv.weekdayFee': 'Weekday GF (IDR)',
    'csv.weekendFee': 'Weekend GF (IDR)',
    'csv.weekdayUsd': 'Weekday USD',
    'csv.weekendUsd': 'Weekend USD',
    'csv.caddyFee': 'Caddy (IDR)',
    'csv.cartFee': 'Cart (IDR)',
    'csv.insuranceFee': 'Insurance (IDR)',
    'csv.website': 'Website',
    'csv.lat': 'Latitude',
    'csv.lng': 'Longitude',
    'csv.note': 'Notes',
    'csv.feeNote': 'Fee notes',
    'csv.memberAvail': 'Membership available',
    'csv.memberCat': 'Membership categories',
    'csv.memberLowest': 'Lowest membership cost (IDR)',
    'csv.memberNote': 'Membership notes',
    'csv.sources': 'Source URLs',
  },
};

// Bumping LANG_RESET_TOKEN forces a one-time reset of stored language
// preference on the next visit (used after a deploy that changes default
// behavior). Default is always Korean for new visitors.
const LANG_RESET_TOKEN = '2026-05-08-ko-default';
let _currentLang = (() => {
  try {
    if (localStorage.getItem('lang.reset') !== LANG_RESET_TOKEN) {
      localStorage.setItem('lang.reset', LANG_RESET_TOKEN);
      localStorage.removeItem('lang');
      return 'ko';
    }
    return localStorage.getItem('lang') || 'ko';
  } catch { return 'ko'; }
})();

function t(key, params) {
  const dict = I18N[_currentLang] || I18N.ko;
  let s = dict[key];
  if (s == null) s = (I18N.ko[key] != null ? I18N.ko[key] : key);
  if (params && typeof s === 'string') {
    s = s.replace(/\{(\w+)\}/g, (_, k) => (params[k] != null ? params[k] : ''));
  }
  return s;
}

function applyI18n(lang) {
  _currentLang = lang;
  const dict = I18N[lang] || I18N.ko;
  document.querySelectorAll('[data-i18n]').forEach(el => {
    const key = el.getAttribute('data-i18n');
    if (dict[key] == null) return;
    if (/[<>]/.test(dict[key])) el.innerHTML = dict[key];
    else el.textContent = dict[key];
  });
  document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
    const key = el.getAttribute('data-i18n-placeholder');
    if (dict[key] != null) el.placeholder = dict[key];
  });
  document.querySelectorAll('[data-i18n-title]').forEach(el => {
    const key = el.getAttribute('data-i18n-title');
    if (dict[key] != null) el.title = dict[key];
  });
  document.querySelectorAll('[data-i18n-aria-label]').forEach(el => {
    const key = el.getAttribute('data-i18n-aria-label');
    if (dict[key] != null) el.setAttribute('aria-label', dict[key]);
  });
  document.documentElement.lang = lang;
  try { localStorage.setItem('lang', lang); } catch {}

  document.querySelectorAll('.lang-btn').forEach(b => {
    b.classList.toggle('active', b.dataset.lang === lang);
  });

  // Re-render dynamic content that contains hardcoded labels
  if (allCourses.length) {
    try {
      const counts = computeStatusCounts(allCourses);
      renderHeaderSubtitle(counts);
      const totalEl = document.getElementById('totalCount');
      if (totalEl) totalEl.textContent = t('header.counterPill', { total: counts.total, operating: counts.operating });
      updateRegionTriggerLabel?.();
      renderCourseList?.();
      renderTable?.();
      renderFinanceTable?.();
      // Refresh source-tab description / column header
      const descEl = document.getElementById('srcPanelDesc');
      if (descEl) descEl.innerHTML = t('srcDesc.' + (currentSourceCat || 'all'));
      // Re-render markers (popups embed Korean strings)
      if (typeof markerCluster !== 'undefined' && markerCluster) renderMarkers?.();
      // Re-render legend / zoom presets
      _refreshMapControls?.();
    } catch (e) { /* ignore */ }
  }

  const analyticsView = document.getElementById('analyticsView');
  if (analyticsView && !analyticsView.hidden && allCourses.length) {
    renderAnalytics();
  }
}

document.addEventListener('click', e => {
  const btn = e.target.closest('.lang-btn');
  if (!btn) return;
  applyI18n(btn.dataset.lang);
});

// === Boot ===
// Default landing tab is the dashboard (analytics) — map / price / finance
// are hidden until the user clicks them.
document.getElementById('mapView').style.display = 'none';
document.getElementById('tableView').style.display = 'none';
const _financeView = document.getElementById('financeView');
if (_financeView) _financeView.style.display = 'none';
applyI18n(_currentLang);
renderCourseListSkeleton();
initMap();
addLegendControl();
addZoomPresetsControl();
loadData().then(() => {
  // Once courses are in memory, populate the dashboard charts so the
  // landing view isn't blank. Map/table/finance still render lazily on
  // their first tab activation.
  renderAnalytics();
});
