/* Tab 1: 종합 대시보드 (Cockpit)
   Head-to-head card + 12 metric tiles + 6y revenue dual line + spec table. */
(function () {
  'use strict';
  const FY = '2024';            // primary year for hero metrics
  const YEARS = ['2020','2021','2022','2023','2024','2025'];

  PurePlayTabs.register('cockpit', function (data) {
    const C = PurePlayCompare;
    const X = PurePlayCharts;
    const pipg = data.pipg;
    const dmig = data.dmig;
    const pDer = C.derive(pipg.yearly);
    const dDer = C.derive(dmig.yearly);
    const pY = pipg.yearly[FY] || {};
    const dY = dmig.yearly[FY] || {};
    const pPrev = pipg.yearly['2023'] || {};
    const dPrev = dmig.yearly['2023'] || {};

    /* ----- 1.1 Head-to-head card ----- */
    const yoy = (cur, prev) => (cur && prev && prev !== 0) ? (cur - prev) / prev : null;
    function card(label, peer, cls) {
      const y = peer.yearly[FY] || {};
      const prev = peer.yearly['2023'] || {};
      const der = label === 'PIPG' ? pDer : dDer;
      const pm = der.per_year[FY] || {};
      return `
      <article class="peer-card ${cls}">
        <h4 class="peer-name">${label}</h4>
        <p class="peer-sub">${peer.company_name || ''} · ${peer.exchange || ''}</p>
        <dl>
          <dt>FY24 매출</dt>           <dd class="numeric">${C.fmtIDR(y.revenue)}</dd>
          <dt>YoY</dt>                 <dd class="numeric">${C.fmtPct(yoy(y.revenue, prev.revenue))}</dd>
          <dt>영업이익</dt>            <dd class="numeric">${C.fmtIDR(y.operating_profit)}</dd>
          <dt>OP 마진</dt>             <dd class="numeric">${C.fmtPct(pm.op_margin)}</dd>
          <dt>EBITDA 마진</dt>         <dd class="numeric">${C.fmtPct(pm.ebitda_margin)}</dd>
          <dt>순이익</dt>              <dd class="numeric">${C.fmtIDR(y.net_profit)}</dd>
          <dt>NI 마진</dt>             <dd class="numeric">${C.fmtPct(pm.ni_margin)}</dd>
          <dt>ROA (avg)</dt>           <dd class="numeric">${C.fmtPct(pm.roa_avg)}</dd>
          <dt>ROE (avg)</dt>           <dd class="numeric">${C.fmtPct(pm.roe_avg)}</dd>
          <dt>총자산</dt>              <dd class="numeric">${C.fmtIDR(y.total_assets)}</dd>
          <dt>부채비율</dt>            <dd class="numeric">${C.fmtPct(pm.debt_ratio)}</dd>
          <dt>종업원 수</dt>           <dd class="numeric">${C.fmtNum(y.employees)}</dd>
        </dl>
      </article>`;
    }
    document.getElementById('cockpit-h2h').innerHTML = card('PIPG', pipg, 'pipg') + card('DMIG', dmig, 'dmig');

    /* ----- 1.2 Metric grid (12 tiles) ----- */
    const pmFY = pDer.per_year[FY] || {};
    const dmFY = dDer.per_year[FY] || {};
    const tiles = [
      { label: '매출',         pipg: pY.revenue,         dmig: dY.revenue,         fmt: 'IDR' },
      { label: '영업이익',     pipg: pY.operating_profit, dmig: dY.operating_profit, fmt: 'IDR' },
      { label: 'EBITDA',       pipg: pY.ebitda,           dmig: dY.ebitda,           fmt: 'IDR' },
      { label: '순이익',       pipg: pY.net_profit,       dmig: dY.net_profit,       fmt: 'IDR' },
      { label: 'OP 마진',      pipg: pmFY.op_margin,      dmig: dmFY.op_margin,      fmt: 'pct' },
      { label: 'EBITDA 마진',  pipg: pmFY.ebitda_margin,  dmig: dmFY.ebitda_margin,  fmt: 'pct' },
      { label: 'NI 마진',      pipg: pmFY.ni_margin,      dmig: dmFY.ni_margin,      fmt: 'pct' },
      { label: 'ROA (avg)',    pipg: pmFY.roa_avg,        dmig: dmFY.roa_avg,        fmt: 'pct' },
      { label: 'ROE (avg)',    pipg: pmFY.roe_avg,        dmig: dmFY.roe_avg,        fmt: 'pct' },
      { label: '총자산',       pipg: pY.total_assets,     dmig: dY.total_assets,     fmt: 'IDR' },
      { label: '부채비율',     pipg: pmFY.debt_ratio,     dmig: dmFY.debt_ratio,     fmt: 'pct' },
      { label: '자기자본비율', pipg: pmFY.equity_ratio,   dmig: dmFY.equity_ratio,   fmt: 'pct' },
    ];
    function fmtTile(v, fmt) {
      if (v === null || v === undefined || !isFinite(v)) return '<span class="na-label">N/A</span>';
      if (fmt === 'IDR') return C.fmtIDR(v);
      if (fmt === 'pct') return C.fmtPct(v);
      return C.fmtNum(v);
    }
    document.getElementById('cockpit-metric-grid').innerHTML = tiles.map(t => `
      <div class="metric-tile">
        <div class="label">${t.label}</div>
        <div class="pair">
          <span class="v pipg">${fmtTile(t.pipg, t.fmt)}</span>
          <span class="v dmig">${fmtTile(t.dmig, t.fmt)}</span>
        </div>
      </div>`).join('');

    /* ----- 1.3 6y revenue dual line ----- */
    X.dualLine(document.getElementById('cockpit-revenue-line'), {
      years: YEARS,
      pipg: YEARS.map(y => (pipg.yearly[y] || {}).revenue),
      dmig: YEARS.map(y => (dmig.yearly[y] || {}).revenue),
      tickFormat: '.2s',
      hoverPrefix: 'Rp ',
      yLabel: '매출 (IDR)',
    });

    /* ----- 1.4 클럽 사양 비교 표 ----- */
    const profP = pipg.notes.profile || {};
    const metaP = pipg.profile || {};
    const metaD = dmig.profile || {};
    const specs = [
      ['위치',          metaP.loc || 'South Jakarta',                  metaD.loc || 'Tangerang (BSD) + North Jakarta (PIK)'],
      ['모회사',        metaP.parent || 'PT Pondok Indah Padang Golf Tbk', metaD.parent || 'Sinarmas Land (BSDE group)'],
      ['상장',          pipg.exchange || '—',                         dmig.exchange || '—'],
      ['홀수',          metaP.holes || (profP.holes || 18) + 'H',     metaD.holes || '36H (BSD 18 + PIK 18)'],
      ['면적',          metaP.area || (profP.land_area_ha_total ? profP.land_area_ha_total + ' ha' : '53 ha'), metaD.area || '156 ha (추정)'],
      ['토지권',        profP.land_certificates ? profP.land_certificates + '건 (HGB + HP)' : '12건', '<span class="na-label">미공시</span>'],
      ['Tier 분류',     'Tier 1 (Pure-play)',                          'Tier 1 (Pure-play)'],
      ['FY24 매출',     C.fmtIDR(pY.revenue),                          C.fmtIDR(dY.revenue)],
      ['FY24 종업원',   C.fmtNum(pY.employees),                        C.fmtNum(dY.employees)],
    ];
    document.getElementById('cockpit-spec-table').innerHTML = `
      <table class="cmp-table">
        <thead><tr><th>항목</th><th class="col-pipg">PIPG</th><th class="col-dmig">DMIG</th></tr></thead>
        <tbody>${specs.map(r => `<tr><td>${r[0]}</td><td class="col-pipg">${r[1]}</td><td class="col-dmig">${r[2]}</td></tr>`).join('')}</tbody>
      </table>`;

    /* ----- 1.5 Footer ----- */
    const pipgSrc = (pY.sources && pY.sources[0]) || {};
    const dmigSrc = (dY.sources && dY.sources[0]) || {};
    document.getElementById('cockpit-footer').innerHTML = `
      <div><strong>데이터 출처:</strong></div>
      <div>· PIPG FY24: <code>${pipgSrc.title || 'PIPG Annual Report'}</code> ${pipgSrc.page ? '(' + pipgSrc.page + ')' : ''}</div>
      <div>· DMIG FY24: <code>${dmigSrc.title || 'DMIG Annual Report'}</code> ${dmigSrc.page ? '(' + dmigSrc.page + ')' : ''}</div>
      <div>· 5년 회사단위 financials: <code>data/company_financials_5y.json</code> (FY20-FY25)</div>
      <div>· AR Note 단위 (segment/OPEX): <code>peer-analysis/operations/data/{pipg,dmig}_notes.json</code> (FY22-FY25)</div>
    `;
  });
})();
