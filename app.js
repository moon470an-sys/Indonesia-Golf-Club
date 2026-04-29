// === State ===
let allCourses = [];
let filteredCourses = [];
let markers = {};
let markerCluster;
let map;
let currentFilter = {
  search: '',
  region: 'all',
  holes: 'all',
  status: 'operating-only',
};

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
}

// === Load Data ===
async function loadData() {
  try {
    const res = await fetch('data/golf_courses.json');
    const doc = await res.json();
    allCourses = doc.courses.filter(c => c.lat != null && c.lng != null);
    const operatingCount = allCourses.filter(c => (c.operating_status?.status || 'operating') === 'operating').length;
    document.getElementById('totalCount').textContent = `${allCourses.length} (운영 ${operatingCount})`;
    renderRegionChips();
    applyFilter();
  } catch (e) {
    console.error('Failed to load data:', e);
    alert('데이터 로딩 실패');
  }
}

// === Region Chips ===
function renderRegionChips() {
  const regions = [...new Set(allCourses.map(c => c.region))].sort();
  const container = document.getElementById('regionChips');
  container.innerHTML = '';

  const allBtn = document.createElement('button');
  allBtn.className = 'chip active';
  allBtn.dataset.region = 'all';
  allBtn.textContent = '전체';
  container.appendChild(allBtn);

  regions.forEach(r => {
    const btn = document.createElement('button');
    btn.className = 'chip';
    btn.dataset.region = r;
    btn.textContent = r;
    container.appendChild(btn);
  });

  container.addEventListener('click', e => {
    if (!e.target.classList.contains('chip')) return;
    container.querySelectorAll('.chip').forEach(b => b.classList.remove('active'));
    e.target.classList.add('active');
    currentFilter.region = e.target.dataset.region;
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
    if (currentFilter.status !== 'all' && currentFilter.status !== 'operating-only' && status !== currentFilter.status) return false;

    if (currentFilter.region !== 'all' && c.region !== currentFilter.region) return false;
    if (currentFilter.holes !== 'all') {
      const h = c.holes;
      if (currentFilter.holes === '9' && h !== 9) return false;
      if (currentFilter.holes === '18' && h !== 18) return false;
      if (currentFilter.holes === '27+' && (h == null || h < 27)) return false;
    }
    if (currentFilter.search) {
      const q = currentFilter.search;
      const haystack = [
        c.name_en,
        c.region,
        c.province,
        c.designer,
        c.address,
      ].filter(Boolean).join(' ').toLowerCase();
      if (!haystack.includes(q)) return false;
    }
    return true;
  });

  document.getElementById('visibleCount').textContent = filteredCourses.length;
  renderMarkers();
  renderCourseList();
}

// === Render Markers ===
function renderMarkers() {
  markerCluster.clearLayers();
  markers = {};

  filteredCourses.forEach(c => {
    const isMatoa = c.id === 'matoa-nasional';
    const status = c.operating_status?.status || 'operating';
    const statusClass = status === 'closed_temporary' ? ' closed' : (status === 'uncertain' ? ' uncertain' : '');
    const icon = L.divIcon({
      className: '',
      html: `<div class="golf-marker${isMatoa ? ' matoa' : ''}${statusClass}"></div>`,
      iconSize: [28, 28],
      iconAnchor: [14, 28],
      popupAnchor: [0, -28],
    });

    const marker = L.marker([c.lat, c.lng], { icon })
      .bindTooltip(c.name_en, { direction: 'top', offset: [0, -24] })
      .on('click', () => showDetail(c));

    markers[c.id] = marker;
    markerCluster.addLayer(marker);
  });
}

// === Course List ===
function renderCourseList() {
  const list = document.getElementById('courseList');
  list.innerHTML = '';

  if (filteredCourses.length === 0) {
    list.innerHTML = '<p style="padding: 20px; text-align: center; color: #94a3b8;">검색 결과가 없습니다</p>';
    return;
  }

  // Sort: by region, then by name
  const sorted = [...filteredCourses].sort((a, b) => {
    if (a.region !== b.region) return a.region.localeCompare(b.region);
    return a.name_en.localeCompare(b.name_en);
  });

  sorted.forEach(c => {
    const item = document.createElement('div');
    item.className = 'course-item';
    item.dataset.id = c.id;

    const holesText = c.holes ? `${c.holes}홀` : '';
    const parText = c.par ? `Par ${c.par}` : '';
    const designerBadge = c.designer ? `<span class="badge">${escapeHtml(c.designer.split(',')[0].trim().split('(')[0].trim())}</span>` : '';

    // Fee preview (weekday green fee)
    const f = c.fees_2026_05;
    let feePreview = '';
    if (f && f.weekday) {
      const wd = f.weekday.green_fee_idr ?? f.weekday.guest_fee_idr ?? f.weekday.member_fee_idr;
      if (wd != null) {
        feePreview = `<span class="fee-badge">평일 ${fmtIDR(wd)}~</span>`;
      } else if (f.weekday.green_fee_usd) {
        feePreview = `<span class="fee-badge">평일 ${fmtUSD(f.weekday.green_fee_usd)}~</span>`;
      }
    }

    // Status badge
    const status = c.operating_status?.status || 'operating';
    let statusBadge = '';
    if (status === 'closed_temporary') statusBadge = '<span class="status-badge closed">휴장</span>';
    else if (status === 'uncertain') statusBadge = '<span class="status-badge uncertain">불확실</span>';

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

  const holesText = c.holes ? `${c.holes}홀` : '—';
  const parText = c.par != null ? c.par : '—';
  const yearText = c.year_opened || '—';

  const facilities = (c.facilities || []).map(f => `<li>${escapeHtml(f)}</li>`).join('');
  const approxTag = c.coord_approximate ? '<span class="approx-tag">좌표 근사</span>' : '';
  const feesHtml = renderFees(c.fees_2026_05);

  // Operating status banner
  const opStatus = c.operating_status?.status || 'operating';
  let statusBanner = '';
  if (opStatus === 'closed_temporary') {
    const reason = c.operating_status?.closure_reason || '리노베이션 / 임시 휴장';
    const reopened = c.operating_status?.reopened_as ? ` (${escapeHtml(c.operating_status.reopened_as)})` : '';
    statusBanner = `<div class="status-banner closed">⚠️ 임시 휴장 — ${escapeHtml(reason)}${reopened}</div>`;
  } else if (opStatus === 'uncertain') {
    statusBanner = `<div class="status-banner uncertain">❓ 운영 상태 불확실 — 사전 연락 권장</div>`;
  }

  content.innerHTML = `
    <h2 class="name">${escapeHtml(c.name_en)}${approxTag}</h2>
    <div class="region-line">${escapeHtml(c.region)} · ${escapeHtml(c.province)}</div>
    ${statusBanner}

    <div class="stats">
      <div class="stat">
        <div class="label">홀</div>
        <div class="value">${holesText}</div>
      </div>
      <div class="stat">
        <div class="label">파</div>
        <div class="value">${parText}</div>
      </div>
      <div class="stat">
        <div class="label">개장</div>
        <div class="value">${yearText}</div>
      </div>
    </div>

    ${c.address ? `
    <section>
      <h3>주소</h3>
      <p>${escapeHtml(c.address)}</p>
    </section>` : ''}

    ${c.designer ? `
    <section>
      <h3>설계자</h3>
      <p>${escapeHtml(c.designer)}</p>
    </section>` : ''}

    ${c.course_layout ? `
    <section>
      <h3>코스 구성</h3>
      <p>${escapeHtml(c.course_layout)}</p>
    </section>` : ''}

    ${feesHtml}

    ${facilities ? `
    <section>
      <h3>부대시설</h3>
      <ul class="facility-list">${facilities}</ul>
    </section>` : ''}

    ${c.notes ? `
    <section>
      <div class="notes">${escapeHtml(c.notes)}</div>
    </section>` : ''}

    ${c.website ? `
    <section>
      <a class="website-link" href="${escapeHtml(c.website)}" target="_blank" rel="noopener">공식 웹사이트 →</a>
    </section>` : ''}

    <section>
      <a class="website-link" style="background:#475569" href="https://www.google.com/maps/search/?api=1&query=${c.lat},${c.lng}" target="_blank" rel="noopener">Google 지도 열기 →</a>
    </section>
  `;

  panel.classList.add('open');
  panel.setAttribute('aria-hidden', 'false');
}

document.getElementById('closeDetail').addEventListener('click', () => {
  const panel = document.getElementById('detailPanel');
  panel.classList.remove('open');
  panel.setAttribute('aria-hidden', 'true');
  document.querySelectorAll('.course-item').forEach(el => el.classList.remove('active'));
});

// === Mobile sidebar toggle ===
document.getElementById('sidebarToggle').addEventListener('click', () => {
  document.getElementById('sidebar').classList.toggle('open');
});

// === Fee Rendering ===
function fmtIDR(n) {
  if (n == null) return null;
  const num = Number(n);
  if (!isFinite(num)) return null;
  if (num >= 1000000) return `Rp ${(num / 1000000).toFixed(num % 1000000 === 0 ? 0 : 2)}M`;
  if (num >= 1000) return `Rp ${(num / 1000).toFixed(0)}K`;
  return `Rp ${num.toLocaleString('ko-KR')}`;
}
function fmtUSD(n) {
  if (n == null) return null;
  return `$${Number(n).toLocaleString('en-US')}`;
}

function renderFees(f) {
  if (!f) return '';

  const isObject = v => v && typeof v === 'object' && !Array.isArray(v);
  const wd = isObject(f.weekday) ? f.weekday : null;
  const we = isObject(f.weekend) ? f.weekend : null;

  const wdGreen = wd ? (wd.green_fee_idr ?? wd.guest_fee_idr ?? wd.member_fee_idr) : null;
  const weGreen = we ? (we.green_fee_idr ?? we.guest_fee_idr ?? we.member_fee_idr) : null;
  const wdUSD = wd ? wd.green_fee_usd : null;
  const weUSD = we ? we.green_fee_usd : null;

  const hasAny = wdGreen != null || weGreen != null || wdUSD != null || weUSD != null
                 || f.caddy_idr != null || f.cart_idr != null || f.insurance_idr != null
                 || f.twilight_idr != null;

  if (!hasAny && !f.notes) return '';

  const rows = [];
  if (wdGreen != null || wdUSD != null) {
    const idr = fmtIDR(wdGreen);
    const usd = fmtUSD(wdUSD);
    rows.push(`<tr><td>평일 그린피</td><td class="amt">${[idr, usd].filter(Boolean).join(' / ') || '—'}</td></tr>`);
  }
  if (weGreen != null || weUSD != null) {
    const idr = fmtIDR(weGreen);
    const usd = fmtUSD(weUSD);
    rows.push(`<tr><td>주말 그린피</td><td class="amt">${[idr, usd].filter(Boolean).join(' / ') || '—'}</td></tr>`);
  }
  if (f.twilight_idr != null) rows.push(`<tr><td>트와일라잇</td><td class="amt">${fmtIDR(f.twilight_idr)}</td></tr>`);
  if (f.caddy_idr != null) rows.push(`<tr><td>캐디피</td><td class="amt">${fmtIDR(f.caddy_idr)}</td></tr>`);
  if (f.cart_idr != null) rows.push(`<tr><td>카트</td><td class="amt">${fmtIDR(f.cart_idr)}</td></tr>`);
  if (f.insurance_idr != null) rows.push(`<tr><td>보험</td><td class="amt">${fmtIDR(f.insurance_idr)}</td></tr>`);

  const sources = (f.sources || []).filter(Boolean);
  const idUrls = new Set((f.indonesian_sources || []).map(e => e?.url).filter(Boolean));
  const sourcesHtml = sources.length
    ? `<div class="fee-sources">출처: ${sources.slice(0, 8).map((u, i) => {
        const langTag = idUrls.has(u) ? '<span class="lang-tag">ID</span>' : '<span class="lang-tag en">EN</span>';
        return `<a href="${escapeHtml(u)}" target="_blank" rel="noopener" title="${escapeHtml(u)}">[${i + 1}]${langTag}</a>`;
      }).join(' ')}</div>`
    : '';

  const verifiedDate = f.last_verified ? `<span class="verified-date">확인일 ${escapeHtml(f.last_verified)}</span>` : '';
  const basedOn = f.based_on ? `<div class="fee-warning">⚠ ${escapeHtml(f.based_on)}</div>` : '';
  const notes = f.notes ? `<div class="fee-notes">${escapeHtml(f.notes)}</div>` : '';

  if (rows.length === 0) {
    // Notes-only fee section (for closed courses or member-only)
    return `
      <section class="fees-section">
        <h3>이용금액 (2026년 5월) ${verifiedDate}</h3>
        ${basedOn}
        ${notes}
        ${sourcesHtml}
      </section>`;
  }

  return `
    <section class="fees-section">
      <h3>이용금액 (2026년 5월) ${verifiedDate}</h3>
      ${basedOn}
      <table class="fee-table">${rows.join('')}</table>
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
let tableSort = { key: 'region', dir: 'asc' };

document.querySelectorAll('.tab').forEach(btn => {
  btn.addEventListener('click', () => {
    const target = btn.dataset.tab;
    document.querySelectorAll('.tab').forEach(b => {
      const active = b.dataset.tab === target;
      b.classList.toggle('active', active);
      b.setAttribute('aria-selected', active);
    });
    document.getElementById('mapView').hidden = target !== 'map';
    document.getElementById('tableView').hidden = target !== 'table';
    if (target === 'table') {
      renderTable();
      // Sync map filters into table when first opened
      if (target === 'table' && !document.getElementById('tableRegionFilter').dataset.populated) {
        populateTableRegions();
      }
    }
    if (target === 'map' && map) setTimeout(() => map.invalidateSize(), 100);
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
  rows.sort((a, b) => {
    let va, vb;
    if (k === 'weekday_fee') {
      va = a.fees_2026_05?.weekday?.green_fee_idr ?? a.fees_2026_05?.weekday?.guest_fee_idr ?? null;
      vb = b.fees_2026_05?.weekday?.green_fee_idr ?? b.fees_2026_05?.weekday?.guest_fee_idr ?? null;
    } else if (k === 'weekend_fee') {
      va = a.fees_2026_05?.weekend?.green_fee_idr ?? a.fees_2026_05?.weekend?.guest_fee_idr ?? null;
      vb = b.fees_2026_05?.weekend?.green_fee_idr ?? b.fees_2026_05?.weekend?.guest_fee_idr ?? null;
    } else if (k === 'status') {
      va = a.operating_status?.status || 'operating';
      vb = b.operating_status?.status || 'operating';
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

function renderTable() {
  const rows = getTableRows();
  document.getElementById('tableVisibleCount').textContent = rows.length;
  const tbody = document.getElementById('courseTableBody');
  tbody.innerHTML = rows.map(c => {
    const status = c.operating_status?.status || 'operating';
    const statusLabel = {
      operating: '운영중',
      closed_temporary: '임시 휴장',
      closed_permanent: '영구 폐장',
      uncertain: '불확실',
    }[status] || status;
    const f = c.fees_2026_05 || {};
    const wd = f.weekday?.green_fee_idr ?? f.weekday?.guest_fee_idr;
    const we = f.weekend?.green_fee_idr ?? f.weekend?.guest_fee_idr;
    const wdUSD = f.weekday?.green_fee_usd;
    const weUSD = f.weekend?.green_fee_usd;
    const wdText = wd ? fmtIDR(wd) : (wdUSD ? fmtUSD(wdUSD) : '—');
    const weText = we ? fmtIDR(we) : (weUSD ? fmtUSD(weUSD) : '—');

    const idUrls = new Set((f.indonesian_sources || []).map(e => e?.url).filter(Boolean));
    const sourcesHtml = (f.sources || []).slice(0, 4).map((u, i) => {
      const lang = idUrls.has(u) ? 'ID' : 'EN';
      return `<a href="${escapeHtml(u)}" target="_blank" rel="noopener" title="${escapeHtml(u)}">[${i + 1}]${lang}</a>`;
    }).join('');

    const designer = c.designer ? escapeHtml(c.designer.split(',')[0].trim().split('(')[0].trim()) : '—';
    const matoaTag = c.id === 'matoa-nasional' ? '<span class="matoa-tag">★ Matoa</span>' : '';

    const websiteLink = c.website ? `<a href="${escapeHtml(c.website)}" target="_blank" rel="noopener">웹</a>` : '';
    const mapLink = `<a href="https://www.google.com/maps/search/?api=1&query=${c.lat},${c.lng}" target="_blank" rel="noopener">지도</a>`;

    return `
      <tr>
        <td class="name">${escapeHtml(c.name_en)}${matoaTag}</td>
        <td>${escapeHtml(c.region)}</td>
        <td>${escapeHtml(c.province)}</td>
        <td><span class="status-pill ${status}">${statusLabel}</span></td>
        <td class="num">${c.holes ?? '—'}</td>
        <td class="num">${c.par ?? '—'}</td>
        <td class="num">${c.year_opened ?? '—'}</td>
        <td>${designer}</td>
        <td class="num fee">${wdText}</td>
        <td class="num fee">${weText}</td>
        <td class="notes">${escapeHtml(c.notes || '')}</td>
        <td class="address">${escapeHtml(c.address || '')}<br>${websiteLink} ${mapLink}</td>
        <td class="sources">${sourcesHtml || '—'}</td>
      </tr>
    `;
  }).join('');
}

// === CSV Export ===
document.getElementById('exportCsv').addEventListener('click', () => {
  const rows = getTableRows();
  const headers = [
    '골프장명', '지역', '주', '운영상태', '홀', '파', '개장연도',
    '설계자', '주소', '평일그린피(IDR)', '주말그린피(IDR)',
    '평일USD', '주말USD', '캐디(IDR)', '카트(IDR)', '보험(IDR)',
    '웹사이트', '위도', '경도', '특이사항', '요금메모',
    '출처URL목록'
  ];
  const csvRows = rows.map(c => {
    const f = c.fees_2026_05 || {};
    const wd = f.weekday || {};
    const we = f.weekend || {};
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
      (f.sources || []).join(' | ')
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

// === Boot ===
initMap();
loadData();
