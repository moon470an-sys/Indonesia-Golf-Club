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

// === Region Dropdown ===
function renderRegionChips() {
  const regions = [...new Set(allCourses.map(c => c.region))].sort();
  const container = document.getElementById('regionChips');
  container.innerHTML = '';

  const select = document.createElement('select');
  select.id = 'regionSelect';
  select.className = 'region-select';

  const allOpt = document.createElement('option');
  allOpt.value = 'all';
  allOpt.textContent = '전체 지역';
  select.appendChild(allOpt);

  regions.forEach(r => {
    const opt = document.createElement('option');
    opt.value = r;
    opt.textContent = r;
    select.appendChild(opt);
  });

  select.value = currentFilter.region || 'all';
  select.addEventListener('change', () => {
    currentFilter.region = select.value;
    applyFilter();
  });

  container.appendChild(select);
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
function buildMarkerPopupHtml(c) {
  const status = c.operating_status?.status || 'operating';
  const statusLabel = { operating: '운영중', closed_temporary: '임시 휴장', closed_permanent: '영구 폐장', uncertain: '불확실' }[status] || status;
  const f = c.fees_2026_05 || {};
  const wd = f.weekday?.green_fee_idr ?? f.weekday?.guest_fee_idr ?? f.weekday?.member_fee_idr;
  const we = f.weekend?.green_fee_idr ?? f.weekend?.guest_fee_idr ?? f.weekend?.member_fee_idr;
  const wdUSD = f.weekday?.green_fee_usd;
  const weUSD = f.weekend?.green_fee_usd;
  const fmtFee = (idr, usd) => idr ? fmtIDR(idr) : (usd ? fmtUSD(usd) : '—');

  const designer = c.designer ? escapeHtml(c.designer.split(',')[0].trim().split('(')[0].trim()) : null;
  const m = c.membership || {};
  let membershipLine = '';
  if (m.available === true || m.available === 'true') membershipLine = '회원 모집 중';
  else if (m.available === 'employees_only') membershipLine = '직원 전용';
  else if (m.available === 'military_personnel') membershipLine = '군 전용';
  else if (m.available === 'by_invitation_only') membershipLine = '초대제';
  else if (m.available === 'members_only') membershipLine = '멤버 전용 (양도시장)';
  else if (m.available === false) membershipLine = '없음';

  const matoaTag = c.id === 'matoa-nasional' ? ' <span class="matoa-tag">★</span>' : '';
  const mapsUrl = `https://www.google.com/maps/search/?api=1&query=${c.lat},${c.lng}`;
  const websiteLink = c.website ? `<a href="${escapeHtml(c.website)}" target="_blank" rel="noopener">공식 웹사이트</a>` : '';
  const mapsLink = `<a href="${mapsUrl}" target="_blank" rel="noopener">구글 지도</a>`;

  const rows = [
    ['지역', `${escapeHtml(c.region || '—')}, ${escapeHtml(c.province || '—')}`],
    ['운영', `<span class="popup-status ${status}">${statusLabel}</span>`],
    ['홀/파', `${c.holes ?? '—'}홀${c.par ? ` · Par ${c.par}` : ''}`],
    ['개장', c.year_opened ? `${c.year_opened}년` : '—'],
    ['설계자', designer || '—'],
    ['평일/주말', `${fmtFee(wd, wdUSD)} / ${fmtFee(we, weUSD)}`],
    membershipLine ? ['멤버십', membershipLine] : null,
  ].filter(Boolean);

  return `
    <div class="marker-popup">
      <div class="popup-name">${escapeHtml(c.name_en)}${matoaTag}</div>
      ${c.address ? `<div class="popup-addr">${escapeHtml(c.address)}</div>` : ''}
      <table class="popup-table">${rows.map(([k, v]) => `<tr><th>${k}</th><td>${v}</td></tr>`).join('')}</table>
      <div class="popup-links">${[websiteLink, mapsLink].filter(Boolean).join(' · ')}</div>
      <button class="popup-detail-btn" data-detail-id="${escapeHtml(c.id)}">상세 정보 →</button>
    </div>
  `;
}

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
      .bindPopup(buildMarkerPopupHtml(c), { minWidth: 280, maxWidth: 320, className: 'course-popup' });

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
  const membershipHtml = renderMembership(c.membership);

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

    ${membershipHtml}

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

const MEMBERSHIP_AVAIL_LABEL = {
  'true': '회원 모집 중',
  true: '회원 모집 중',
  'false': '없음',
  false: '없음',
  'by_invitation_only': '초대제 (비공개)',
  'employees_only': '직원 전용',
  'military_personnel': '군인 전용',
  'members_only': '회원 전용',
  'unknown': '정보 없음',
};

function renderMembership(m) {
  if (!m || typeof m !== 'object') return '';
  const avail = m.available;
  const cats = Array.isArray(m.categories) ? m.categories : [];

  const availLabel = MEMBERSHIP_AVAIL_LABEL[avail] ?? '정보 없음';

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
    const term = cat.term_years ? `${cat.term_years}년` : '';
    const detail = [
      initT ? `가입비 ${initT}` : null,
      annT ? `연회비 ${annT}` : null,
      monT ? `월회비 ${monT}` : null,
      depT ? `예치금 ${depT}` : null,
      term,
    ].filter(Boolean).join(' · ');
    if (!cat.name && !detail) return '';
    return `<tr>
      <td>${escapeHtml(cat.name || '—')}</td>
      <td>${detail || '<span class="muted">비공개</span>'}</td>
    </tr>`;
  }).filter(Boolean).join('');

  const sources = (m.sources || []).filter(Boolean);
  const sourcesHtml = sources.length
    ? `<div class="fee-sources">출처: ${sources.slice(0, 4).map((u, i) =>
        `<a href="${escapeHtml(u)}" target="_blank" rel="noopener" title="${escapeHtml(u)}">[${i + 1}]</a>`
      ).join(' ')}</div>`
    : '';

  const notes = m.notes ? `<div class="fee-notes">${escapeHtml(m.notes)}</div>` : '';
  const verifiedDate = m.last_verified ? `<span class="verified-date">확인일 ${escapeHtml(m.last_verified)}</span>` : '';

  if (catRows) {
    return `
      <section class="membership-section">
        <h3>회원권 (멤버십) <span class="member-status-pill ${avail}">${availLabel}</span> ${verifiedDate}</h3>
        <table class="member-table">
          <thead><tr><th>등급</th><th>비용</th></tr></thead>
          <tbody>${catRows}</tbody>
        </table>
        ${notes}
        ${sourcesHtml}
      </section>`;
  }

  // No priced categories — show status only
  return `
    <section class="membership-section minimal">
      <h3>회원권 (멤버십) <span class="member-status-pill ${avail}">${availLabel}</span></h3>
      ${notes || '<p class="muted">공개된 가입비·연회비 정보가 없습니다. 회원권 문의는 클럽으로 직접 연락이 필요합니다.</p>'}
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
    rows.push(`<tr><td>평일 그린피</td><td class="amt">${[idr, usd].filter(Boolean).join(' / ') || '—'}</td></tr>`);
  }
  if (weGreen != null || weUSD != null) {
    const idr = fmtIDR(weGreen);
    const usd = fmtUSD(weUSD);
    rows.push(`<tr><td>주말 그린피</td><td class="amt">${[idr, usd].filter(Boolean).join(' / ') || '—'}</td></tr>`);
  }
  if (f.twilight_idr != null) rows.push(`<tr><td>트와일라잇</td><td class="amt">${fmtIDR(f.twilight_idr)}</td></tr>`);
  if (caddy != null) rows.push(`<tr><td>캐디피</td><td class="amt">${fmtFee(caddy)}</td></tr>`);
  if (cart != null) rows.push(`<tr><td>카트</td><td class="amt">${fmtFee(cart)}</td></tr>`);
  if (insurance != null) rows.push(`<tr><td>보험</td><td class="amt">${fmtFee(insurance)}</td></tr>`);
  if (taxPct != null) rows.push(`<tr><td>세금(PPN)</td><td class="amt">${taxPct}%${taxIncluded ? ' (포함)' : ''}</td></tr>`);
  if (rateIncludes) rows.push(`<tr><td>요금 구성</td><td class="amt note-cell">${escapeHtml(rateIncludes)}</td></tr>`);

  const detailed = f.schedule_detailed;
  let detailedHtml = '';
  if (isObject(detailed)) {
    const slotLabels = { weekday: '평일', weekend_saturday: '토요일', weekend_sunday: '일요일', public_holiday: '공휴일' };
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
    if (blocks.length) detailedHtml = `<details class="schedule-detailed"><summary>상세 시간/세그먼트별 요율</summary>${blocks.join('')}</details>`;
  }

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
        ${detailedHtml}
        ${notes}
        ${sourcesHtml}
      </section>`;
  }

  return `
    <section class="fees-section">
      <h3>이용금액 (2026년 5월) ${verifiedDate}</h3>
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
let tableSort = { key: 'region', dir: 'asc' };

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
    const showMap = target === 'map';
    mapView.hidden = !showMap;
    tableView.hidden = showMap;
    mapView.style.display = showMap ? '' : 'none';
    tableView.style.display = showMap ? 'none' : '';
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
      return `<span class="member-amt">가입 ${fmtMoney(init.amount, init.currency)}</span>`;
    }
    if (ann.amount != null) {
      return `<span class="member-amt">연 ${fmtMoney(ann.amount, ann.currency)}</span>`;
    }
  }
  const avail = m.available;
  const label = MEMBERSHIP_AVAIL_LABEL[avail];
  if (label && avail !== 'unknown' && avail !== false) {
    return `<span class="member-status-pill ${avail}">${label}</span>`;
  }
  return '<span class="muted">비공개</span>';
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
  const label = MEMBERSHIP_AVAIL_LABEL[avail];
  if (label && avail !== 'unknown' && avail !== false) {
    return `<span class="member-status-pill ${avail}">${label}</span>`;
  }
  return '<span class="muted">비공개</span>';
}

function membershipAmountCell(m) {
  if (!m) return '<span class="muted">—</span>';
  const cats = Array.isArray(m.categories) ? m.categories.filter(c => c && typeof c === 'object') : [];
  const parts = [];
  for (const cat of cats) {
    const init = cat.initiation_fee || {};
    const ann = cat.annual_fee || {};
    const mo = cat.monthly_fee || {};
    if (init.amount != null) parts.push(`<span class="member-amt">가입 ${fmtMoney(init.amount, init.currency)}</span>`);
    if (ann.amount != null) parts.push(`<span class="member-amt">연 ${fmtMoney(ann.amount, ann.currency)}</span>`);
    if (mo.amount != null) parts.push(`<span class="member-amt">월 ${fmtMoney(mo.amount, mo.currency)}</span>`);
    if (parts.length >= 3) break;
  }
  if (parts.length) return parts.slice(0, 3).join('<br>');
  return '<span class="muted">비공개</span>';
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

    // GoGolf reference sub-row (when present)
    let gogolfRowHtml = '';
    const gg = c.fees_gogolf_reference;
    if (gg && gg.schedule) {
      const sch = gg.schedule;
      const ggCell = (v) => v != null ? fmtIDR(v) : '<span class="muted">—</span>';
      const ggSrc = gg.source_url ? `<a href="${escapeHtml(gg.source_url)}" target="_blank" rel="noopener" title="${escapeHtml(gg.source_url)}">gogolf.co.id</a>` : '';
      const ggMember = gg.member_rate_idr != null ? `<span class="member-amt">멤버 ${fmtIDR(gg.member_rate_idr)}</span>` : '<span class="muted">—</span>';
      const ggCaddy = gg.ancillary?.caddy_idr != null ? `캐디 ${fmtIDR(gg.ancillary.caddy_idr)}` : '';
      const ggCart = gg.ancillary?.cart_idr != null ? `카트 ${fmtIDR(gg.ancillary.cart_idr)}` : '';
      const ggExtras = [ggCaddy, ggCart].filter(Boolean).join(' · ');
      gogolfRowHtml = `
        <tr class="gogolf-ref-row">
          <td class="gogolf-label" colspan="6">↳ <span class="gogolf-tag">GoGolf 참고</span> ${ggExtras ? `<span class="gogolf-extras">${ggExtras}</span>` : ''}</td>
          <td class="num fee gogolf-fee">${ggCell(sch.weekday?.am)}</td>
          <td class="num fee gogolf-fee">${ggCell(sch.weekday?.pm)}</td>
          <td class="num fee gogolf-fee">${ggCell(sch.saturday?.am)}</td>
          <td class="num fee gogolf-fee">${ggCell(sch.saturday?.pm)}</td>
          <td class="num fee gogolf-fee">${ggCell(sch.sunday?.am)}</td>
          <td class="num fee gogolf-fee">${ggCell(sch.sunday?.pm)}</td>
          <td class="member-type"><span class="muted">—</span></td>
          <td class="num member-amount">${ggMember}</td>
          <td class="address gogolf-disclaimer" colspan="3">${ggSrc} <span class="gogolf-note">${escapeHtml(gg.disclaimer || '참고용 비공식 가격')}</span></td>
        </tr>
      `;
    }

    return `
      <tr>
        <td class="name">${escapeHtml(c.name_en)}${matoaTag}</td>
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
        <td class="address">${escapeHtml(c.address || '')}<br>${mapLink}</td>
        <td class="sources official-links">${officialHtml}</td>
        <td class="sources sns-links">${snsHtml}</td>
      </tr>${gogolfRowHtml}
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
    '멤버십가입가능', '멤버십카테고리', '멤버십최저비용(IDR환산)',
    '멤버십메모', '출처URL목록'
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
      if (init.amount) parts.push(`가입 ${init.amount} ${init.currency || 'IDR'}`);
      if (ann.amount) parts.push(`연 ${ann.amount} ${ann.currency || 'IDR'}`);
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

// === Boot ===
document.getElementById('tableView').style.display = 'none';
initMap();
loadData();
