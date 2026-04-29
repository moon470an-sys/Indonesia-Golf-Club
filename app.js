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
    document.getElementById('totalCount').textContent = allCourses.length;
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

// === Search ===
document.getElementById('searchInput').addEventListener('input', e => {
  currentFilter.search = e.target.value.trim().toLowerCase();
  applyFilter();
});

// === Apply Filter ===
function applyFilter() {
  filteredCourses = allCourses.filter(c => {
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
    const icon = L.divIcon({
      className: '',
      html: `<div class="golf-marker${isMatoa ? ' matoa' : ''}"></div>`,
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

    item.innerHTML = `
      <h4>${escapeHtml(c.name_en)}</h4>
      <div class="meta">
        <span>📍 ${escapeHtml(c.region)}</span>
        ${holesText ? `<span>⛳ ${holesText}</span>` : ''}
        ${parText ? `<span>${parText}</span>` : ''}
        ${designerBadge}
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

  content.innerHTML = `
    <h2 class="name">${escapeHtml(c.name_en)}${approxTag}</h2>
    <div class="region-line">${escapeHtml(c.region)} · ${escapeHtml(c.province)}</div>

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

// === Boot ===
initMap();
loadData();
