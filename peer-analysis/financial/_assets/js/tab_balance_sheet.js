/* Tab 2: 재무 건전성 (Balance Sheet) */
(function () {
  'use strict';
  const YEARS = ['2020','2021','2022','2023','2024','2025'];

  PurePlayTabs.register('balance-sheet', function (data) {
    const C = PurePlayCompare;
    const X = PurePlayCharts;
    const pipg = data.pipg, dmig = data.dmig;
    const pDer = C.derive(pipg.yearly);
    const dDer = C.derive(dmig.yearly);

    /* ----- 2.1 자산 구성 (FY25 단년) — 그룹 BS 3 카테고리만 가용 ----- */
    const fy25P = pipg.yearly['2025'] || {};
    const fy25D = dmig.yearly['2025'] || {};
    /* asset_mix container has chart-grid-2; show 2 100%-stacked panels */
    document.getElementById('bs-asset-mix').innerHTML = `
      <div>
        <h4 style="margin:0 0 8px;font-size:13px">자산-부채-자본 구성 (FY25)</h4>
        <div id="bs-asset-mix-stack" class="chart"></div>
      </div>
      <div>
        <h4 style="margin:0 0 8px;font-size:13px">유동/비유동 분리</h4>
        <div style="padding:12px;background:var(--color-surface-alt);border-radius:8px;font-size:13px;line-height:1.7">
          AR Note에 유동자산·유동부채·현금 단년 가용. <span class="na-label">5년 시계열 N/A</span><br>
          PIPG FY25 유동자산 / 부채 / 자본 — Note에서 추출(다음 cycle), 현재는 총자산만 시각화.<br>
          DMIG: 동일. 5년 유동성 비율 (current/cash ratio) 미공시.
        </div>
      </div>`;
    X.stacked100(document.getElementById('bs-asset-mix-stack'), {
      series: [
        { label: '부채 (Liabilities)',         pipg: fy25P.total_liabilities, dmig: fy25D.total_liabilities, color: '#EF4444' },
        { label: '자본 (Equity)',              pipg: fy25P.total_equity,      dmig: fy25D.total_equity,      color: '#10B981' },
      ],
    });

    /* ----- 2.2 부채/자본 비율 5년 ----- */
    X.dualLine(document.getElementById('bs-debt-ratio'), {
      years: YEARS,
      pipg: YEARS.map(y => (pDer.per_year[y] || {}).debt_ratio),
      dmig: YEARS.map(y => (dDer.per_year[y] || {}).debt_ratio),
      tickFormat: '.1%',
      yLabel: '부채비율 (부채/자산)',
    });
    X.dualLine(document.getElementById('bs-equity-ratio'), {
      years: YEARS,
      pipg: YEARS.map(y => (pDer.per_year[y] || {}).equity_ratio),
      dmig: YEARS.map(y => (dDer.per_year[y] || {}).equity_ratio),
      tickFormat: '.1%',
      yLabel: '자기자본비율 (자본/자산)',
    });

    /* ----- 2.3 안정성 매트릭스 ----- */
    const rows = [
      ['부채비율',     YEARS.map(y => (pDer.per_year[y] || {}).debt_ratio),     YEARS.map(y => (dDer.per_year[y] || {}).debt_ratio),     'pct'],
      ['자기자본비율', YEARS.map(y => (pDer.per_year[y] || {}).equity_ratio),   YEARS.map(y => (dDer.per_year[y] || {}).equity_ratio),   'pct'],
      ['유동비율',     YEARS.map(() => null), YEARS.map(() => null), 'na'],
      ['현금비율',     YEARS.map(() => null), YEARS.map(() => null), 'na'],
    ];
    function cellFmt(v, fmt) {
      if (v === null || v === undefined || !isFinite(v)) return '<span class="na-cell">N/A</span>';
      return fmt === 'pct' ? C.fmtPct(v) : C.fmtNum(v);
    }
    let html = '<table class="cmp-table"><thead><tr><th>지표</th><th>피어</th>';
    YEARS.forEach(y => html += `<th>FY${y.slice(-2)}</th>`);
    html += '</tr></thead><tbody>';
    rows.forEach(r => {
      html += `<tr><td rowspan="2">${r[0]}</td><td class="col-pipg">PIPG</td>`;
      r[1].forEach((v, i) => html += `<td>${cellFmt(v, r[3])}</td>`);
      html += `</tr><tr><td class="col-dmig">DMIG</td>`;
      r[2].forEach((v, i) => html += `<td>${cellFmt(v, r[3])}</td>`);
      html += '</tr>';
    });
    html += '</tbody></table>';
    html += '<p class="section-sub" style="margin-top:12px">유동비율/현금비율은 양사 모두 5년 시계열 BS 분해 미공시. AR Note에서 단년 가용 시 향후 추가 예정.</p>';
    document.getElementById('bs-stability-matrix').innerHTML = html;

    /* ----- 2.4 토지권 비교 ----- */
    const land = (data.pipgLong && data.pipgLong.land_rights) || {};
    const items = land.items || [];
    const parcelRows = items.map(it => `
      <tr><td>${it.parcel}</td><td>${it.validity}</td><td class="numeric">${C.fmtNum(it.area_m2)}</td></tr>`).join('');
    document.getElementById('bs-land-rights').innerHTML = `
      <div class="head-to-head">
        <div>
          <h4 style="margin:0 0 8px;font-size:13px;color:var(--color-pipg)">PIPG — 12 parcels (총 ${C.fmtNum(land.total_m2)} m²)</h4>
          <table class="cmp-table">
            <thead><tr><th>Parcel</th><th>Validity</th><th>면적 (m²)</th></tr></thead>
            <tbody>${parcelRows}</tbody>
          </table>
        </div>
        <div>
          <h4 style="margin:0 0 8px;font-size:13px;color:var(--color-dmig)">DMIG</h4>
          <div style="padding:12px;background:var(--color-surface-alt);border-radius:8px;font-size:13px">
            DMIG AR은 BSD+PIK 양 코스 토지권 parcel 단위 미공시. 총 면적 ~156 ha (개별 HGB/HP detail은 그룹 BS 통합).
            <br><br><span class="na-label">parcel-level 비교 N/A</span>
          </div>
        </div>
      </div>`;

    /* ----- 2.5 PIPG 14y BS reference ----- */
    const bs = data.pipgLong && data.pipgLong.balance_sheet;
    if (bs) {
      const yrs = bs.years;
      const totalAssets = (bs.lines['자산총계'] || bs.lines['Total assets'] || {});
      const totalLiab   = (bs.lines['부채총계'] || bs.lines['Total liabilities'] || {});
      const totalEq     = (bs.lines['자본총계'] || bs.lines['Total equity'] || {});
      X.pipgLongLine(document.getElementById('bs-pipg-long-chart'), {
        years: yrs,
        values: yrs.map(y => totalAssets[y]),
        yLabel: 'PIPG 총자산 (IDR Million, 14년)',
        tickFormat: ',',
      });
    }

    /* ----- Footer ----- */
    document.getElementById('bs-footer').innerHTML = `
      <div>· 5년 BS (총자산/총부채/총자본): <code>data/company_financials_5y.json</code></div>
      <div>· PIPG 12 parcel land rights: <code>data/pipg_pptx_data.json#land_rights</code> (PPT §2)</div>
      <div>· PIPG 14년 BS 시계열: <code>data/pipg_pptx_data.json#balance_sheet</code> (37 lines × 14y)</div>
      <div>· DMIG parcel-level land rights는 AR 미공시 (그룹 BS 통합)</div>
    `;
  });
})();
