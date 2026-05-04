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

    ${renderFinancials(c.financials)}

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

// === Financials Rendering ===
const LISTED_STATUS_LABEL = {
  'listed': '상장',
  'subsidiary-of-listed': '상장사 자회사',
  'private': '비상장',
  'state-owned': '국영기업',
  'government': '정부 운영',
  'local-government': '지방정부',
  'military': '군 운영',
  'foundation': '재단',
  'joint-venture': '합작법인',
  'plantation-soe': '국영농장',
  'tbk-reporting-not-yet-traded': 'Tbk(IDX 미거래)',
  'subsidiary-of-state-owned (BUMN holding, unlisted)': 'BUMN 자회사(미상장)',
  'unknown': '미확인'
};

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

function renderFinancials(fin) {
  if (!fin || typeof fin !== 'object') return '';

  const ticker = fin.idx_ticker || fin.foreign_ticker;
  const status = fin.listed_status || 'unknown';
  const statusLabel = LISTED_STATUS_LABEL[status] || status;
  const parent = fin.parent_company_full_name || fin.parent_group;
  const op = fin.operating_company;

  const rows = [];
  if (op) rows.push(['운영법인', escapeHtml(op)]);
  if (parent) rows.push(['모회사·기업집단', escapeHtml(parent)]);
  if (ticker) {
    const cls = fin.idx_ticker ? 'idx' : 'foreign';
    const tickerHtml = `<span class="ticker-pill ${cls} ticker-clickable" data-ticker="${escapeHtml(ticker)}" title="클릭하면 5년 재무 그래프 보기">${escapeHtml(ticker)}</span>`;
    rows.push(['상장 티커', tickerHtml]);
  }
  rows.push(['상장 구분', `<span class="listed-status ${escapeHtml(status)}">${escapeHtml(statusLabel)}</span>`]);

  // Revenue (full-year preferred, else H1)
  const rev = fin.revenue_idr;
  const revH1 = fin.revenue_idr_h1;
  const revYear = fin.revenue_year;
  if (rev != null) {
    rows.push([`매출${revYear ? ` (${escapeHtml(String(revYear))})` : ''}`, fmtBigIDR(rev)]);
  } else if (revH1 != null) {
    rows.push([`매출 (H1-${escapeHtml(String(revYear || '2024'))})`, fmtBigIDR(revH1)]);
  }
  if (fin.net_profit_idr != null) {
    const np = fin.net_profit_idr;
    const sign = np < 0 ? '<span class="neg">−</span>' : '';
    rows.push(['순이익', sign + fmtBigIDR(Math.abs(np))]);
  } else if (fin.net_profit_idr_h1 != null) {
    rows.push(['순이익 (H1)', fmtBigIDR(fin.net_profit_idr_h1)]);
  }
  if (fin.total_assets_idr != null) rows.push(['총자산', fmtBigIDR(fin.total_assets_idr)]);
  if (fin.employees != null) rows.push(['직원수', `${fin.employees.toLocaleString('en-US')}명`]);
  if (fin.investment_idr != null) rows.push(['투자/개발비', fmtBigIDR(fin.investment_idr)]);
  if (fin.investment_usd != null) rows.push(['투자 (USD)', `$${fin.investment_usd.toLocaleString('en-US')}`]);

  if (fin.course_segment_disclosed === true && fin.course_segment_revenue_idr != null) {
    rows.push(['골프 세그먼트 매출', `<span class="seg-disclosed">${fmtBigIDR(fin.course_segment_revenue_idr)}</span> <span class="muted">(별도공시)</span>`]);
  } else if (fin.course_segment_disclosed === true) {
    rows.push(['골프 세그먼트', '<span class="seg-disclosed">별도공시</span>']);
  }

  // Membership pricing
  if (fin.membership_price_idr != null) {
    rows.push(['회원권', `${fmtBigIDR(fin.membership_price_idr)}`]);
  } else if (fin.membership_price_usd != null) {
    rows.push(['회원권', `$${fin.membership_price_usd.toLocaleString('en-US')}`]);
  }

  if (fin.figure_origin) {
    rows.push(['데이터 신뢰도', `<span class="origin-pill">${escapeHtml(fin.figure_origin)}</span>`]);
  }

  if (fin.recent_news) {
    rows.push(['최근 이슈', `<span class="news-line">${escapeHtml(fin.recent_news)}</span>`]);
  }

  // Notes
  let notesHtml = '';
  if (fin.membership_price_notes) notesHtml += `<div class="fin-note"><span class="note-label">회원권 메모:</span> ${escapeHtml(fin.membership_price_notes)}</div>`;
  if (fin.ownership_notes) notesHtml += `<div class="fin-note"><span class="note-label">소유 메모:</span> ${escapeHtml(fin.ownership_notes)}</div>`;

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
      const kindBadge = s.kind === 'parent' ? '<span class="kind-pill parent">모회사</span>'
        : s.kind === 'membership' ? '<span class="kind-pill membership">회원권</span>'
        : '';
      const label = s.publisher || (() => {
        try { return new URL(s.url).hostname.replace(/^www\./, ''); }
        catch { return `[${i+1}]`; }
      })();
      const dateInfo = s.date_published ? ` <span class="src-date">${escapeHtml(s.date_published)}</span>` : '';
      const titleAttr = s.title ? `${s.title} — ${s.url}` : s.url;
      return `<a class="fin-src" href="${escapeHtml(s.url)}" target="_blank" rel="noopener" title="${escapeHtml(titleAttr)}">${kindBadge}${escapeHtml(label)}${dateInfo}</a>`;
    }).join(' ');
    sourcesHtml = `<div class="fin-sources">출처(${allSources.length}): ${items}</div>`;
  }

  const verifiedDate = fin.last_verified ? `<span class="verified-date">확인일 ${escapeHtml(fin.last_verified)}</span>` : '';

  return `
    <section class="financials-section">
      <h3>기업·재무 정보 ${verifiedDate}</h3>
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

// Source-category tab switching
document.querySelectorAll('.src-tab').forEach(btn => {
  btn.addEventListener('click', () => {
    const tab = btn.dataset.srcTab;
    document.querySelectorAll('.src-tab').forEach(b => {
      const on = b === btn;
      b.classList.toggle('active', on);
      b.setAttribute('aria-selected', on ? 'true' : 'false');
    });
    document.querySelectorAll('.src-panel').forEach(p => {
      p.classList.toggle('active', p.dataset.srcPanel === tab);
    });
    const cntEl = document.getElementById(`srcCount-${tab}`);
    if (cntEl) document.getElementById('tableVisibleCount').textContent = cntEl.textContent;
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
      return { label: '공식', kind: 'official', host, url };
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
  if (host.includes('klook') || host.includes('traveloka') || host.includes('agoda') || host.includes('tiket.com') || host.includes('trip.com')) return { label: '예약', kind: 'booking', host, url };
  if (host.includes('facebook') || host === 'fb.com' || host.includes('instagram') || host.includes('twitter') || host === 'x.com' || host.includes('tiktok') || host.includes('threads')) return { label: 'SNS', kind: 'sns', host, url };
  if (host.includes('idnfinancials') || host.includes('kontan') || host.includes('bisnis') || host.includes('kompas') || host.includes('detik') || host.includes('tempo.co') || host.includes('tribun') || host.includes('liputan6') || host.includes('voi.id') || host.includes('cnbcindonesia') || host.includes('jawapos') || host.includes('suaramerdeka') || host.includes('antaranews') || host.includes('golftimes') || host.includes('obgolf') || host.includes('xplorewisata') || host.includes('antorij')) return { label: '뉴스/매거진', kind: 'news', host, url };
  if (host.includes('idx.co.id') || host.includes('ojk.go.id') || host.includes('sec.gov') || host.includes('sgx.com')) return { label: '공시', kind: 'official', host, url };
  if (host.includes('archive.org') || host.includes('wayback')) return { label: 'Wayback', kind: 'archive', host, url };
  if (host.includes('tni-au.mil') || host.includes('tniad') || host.includes('tnial') || host.endsWith('.mil.id') || host.endsWith('.go.id')) return { label: '관공서', kind: 'gov', host, url };
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

function renderSourceTabRow(c, info, sources) {
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
  const satAmCell = cellHtml(satSlots.am, weFallback, weUsd);
  const sunAmCell = cellHtml(sunSlots.am, weFallback, weUsd);

  const matoaTag = c.id === 'matoa-nasional' ? '<span class="matoa-tag">★ Matoa</span>' : '';

  const srcPills = sources.map(s =>
    `<a class="src-pill src-${s.kind}" href="${escapeHtml(s.url)}" target="_blank" rel="noopener" title="${escapeHtml(s.url)}"><span class="src-pill-label">${escapeHtml(s.label)}</span><span class="src-pill-host">${escapeHtml(s.host)}</span></a>`
  ).join('');

  return `
    <tr class="primary-rate-row">
      <td class="name">${escapeHtml(c.name_en)}${matoaTag}</td>
      <td>${escapeHtml(c.region)}</td>
      <td><span class="status-pill ${status}">${statusLabel}</span></td>
      <td class="num">${c.holes ?? '—'}</td>
      <td class="num fee">${wdAmCell}</td>
      <td class="num fee fee-premium">${satAmCell}</td>
      <td class="num fee fee-premium">${sunAmCell}</td>
      <td class="src-cell">${srcPills || '<span class="muted">—</span>'}</td>
    </tr>
  `;
}

function renderTable() {
  const rows = getTableRows();
  const TABS = ['official', 'sns', 'platform', 'aggregator', 'news'];
  const buckets = { official: [], sns: [], platform: [], aggregator: [], news: [] };

  for (const c of rows) {
    const cat = collectCategorizedSources(c);
    for (const tab of TABS) {
      if (cat[tab].length) buckets[tab].push({ course: c, sources: cat[tab] });
    }
  }

  // Active panel count → main toolbar counter
  const activeTabBtn = document.querySelector('.src-tab.active');
  const activeTab = activeTabBtn ? activeTabBtn.dataset.srcTab : 'official';
  document.getElementById('tableVisibleCount').textContent = buckets[activeTab].length;

  for (const tab of TABS) {
    const tbody = document.querySelector(`[data-src-tbody="${tab}"]`);
    if (!tbody) continue;
    tbody.innerHTML = buckets[tab].map(({ course, sources }) =>
      renderSourceTabRow(course, tab, sources)
    ).join('') || `<tr><td colspan="8" class="src-empty">표시할 데이터가 없습니다</td></tr>`;
    const cnt = document.getElementById(`srcCount-${tab}`);
    if (cnt) cnt.textContent = buckets[tab].length;
  }

  return;
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
    const tickerCell = ticker
      ? `<span class="ticker-pill ${fin.idx_ticker ? 'idx' : 'foreign'} ticker-clickable" data-ticker="${escapeHtml(ticker)}" title="클릭하면 5년 재무 그래프 보기">${escapeHtml(ticker)}</span>`
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
      <p style="color:#64748b">티커 <strong>${escapeHtml(ticker)}</strong>의 5년치 상세 재무 데이터가 아직 준비되지 않았습니다. (조사 진행 중)</p>
      <p style="color:#94a3b8; font-size:12px">데이터가 추가되면 매출/순이익/총자산 5년 추이 그래프와 표를 이 위치에서 확인할 수 있습니다.</p>
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
    { key: 'revenue', label: '매출' },
    { key: 'operating_profit', label: '영업이익' },
    { key: 'net_profit', label: '순이익' },
    { key: 'ebitda', label: 'EBITDA' },
    { key: 'total_assets', label: '총자산' },
    { key: 'total_liabilities', label: '총부채' },
    { key: 'total_equity', label: '자기자본' },
    { key: 'eps', label: 'EPS' },
    { key: 'dividend_per_share', label: 'DPS' },
    { key: 'employees', label: '직원수' },
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
    : '<span class="muted">출처 정보 없음</span>';

  bodyEl.innerHTML = `
    <h3>📈 5년 재무 요약 <span class="fin5y-quality ${qualityClass}">${escapeHtml(qualityClass.toUpperCase())}</span></h3>
    ${summaryNote}
    <div class="fin5y-charts">
      <div class="chart-card">
        <h4>매출 (Revenue)</h4>
        <canvas id="chart-revenue"></canvas>
      </div>
      <div class="chart-card">
        <h4>순이익 (Net Profit)</h4>
        <canvas id="chart-netprofit"></canvas>
      </div>
      <div class="chart-card">
        <h4>총자산 (Total Assets)</h4>
        <canvas id="chart-assets"></canvas>
      </div>
      <div class="chart-card">
        <h4>자산 vs 부채 vs 자본</h4>
        <canvas id="chart-balance"></canvas>
      </div>
    </div>
    <h3>📋 연도별 상세 (${escapeHtml(currency)})</h3>
    <table class="fin5y-table">
      <thead>
        <tr><th class="metric-col">항목</th>${years.map(y => `<th>${y}</th>`).join('')}</tr>
      </thead>
      <tbody>${tableRows}</tbody>
    </table>
    <h3>🔗 출처 (전 연도 통합)</h3>
    <div class="fin-sources">${sourceLinks}</div>
    <p style="font-size:11px;color:#94a3b8;margin-top:14px">확인일 ${escapeHtml(data.last_verified || '2026-05-01')} · 단위 ${isIDR ? 'IDR (T=조, B=십억, M=백만)' : escapeHtml(currency)}${idrEquiv ? ' · 작은 숫자는 IDR 환산값' : ''}</p>
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
    mkLineChart('chart-revenue', 'revenue', colors.revenue, '매출');
    mkLineChart('chart-netprofit', 'net_profit', colors.netprofit, '순이익');
    mkLineChart('chart-assets', 'total_assets', colors.assets, '총자산');

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
            { label: '부채', data: liabPts, backgroundColor: isDark ? '#fbbf2488' : '#b8924a88', borderColor: isDark ? '#fbbf24' : '#b8924a', borderWidth: 2, stack: 'b' },
            { label: '자본', data: eqPts, backgroundColor: isDark ? '#34d39988' : '#0d6e4d88', borderColor: isDark ? '#34d399' : '#0d6e4d', borderWidth: 2, stack: 'b' },
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

// Click delegation for ticker pills
document.addEventListener('click', async (e) => {
  const t = e.target.closest('.ticker-clickable');
  if (!t) return;
  e.preventDefault();
  e.stopPropagation();
  const ticker = t.dataset.ticker;
  if (!ticker) return;
  await loadFinancialsIfNeeded();
  renderTickerModal(ticker);
});

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

// === Boot ===
document.getElementById('tableView').style.display = 'none';
initMap();
loadData();
