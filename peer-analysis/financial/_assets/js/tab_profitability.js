/* Tab 3: 수익성 (Profitability) */
(function () {
  'use strict';
  const YEARS = ['2020','2021','2022','2023','2024','2025'];

  PurePlayTabs.register('profitability', function (data) {
    const C = PurePlayCompare;
    const X = PurePlayCharts;
    const pipg = data.pipg, dmig = data.dmig;
    const pDer = C.derive(pipg.yearly);
    const dDer = C.derive(dmig.yearly);
    const fy = '2024';
    const pmFY = pDer.per_year[fy] || {};
    const dmFY = dDer.per_year[fy] || {};

    /* ----- 3.1 FY24 마진 1:1 (4 metrics × 2 series grouped) ----- */
    X.dualMetricGroup(document.getElementById('prof-fy24-margins'), {
      metrics: ['GP 마진 (notes-only)', 'OP 마진', 'EBITDA 마진', 'NI 마진'],
      pipg: [null, pmFY.op_margin, pmFY.ebitda_margin, pmFY.ni_margin],
      dmig: [null, dmFY.op_margin, dmFY.ebitda_margin, dmFY.ni_margin],
      tickFormat: '.0%',
      format: 'pct',
    });

    /* ----- 3.2 5-year margin trend × 4 panels ----- */
    function lineFor(field) {
      return {
        years: YEARS,
        pipg: YEARS.map(y => (pDer.per_year[y] || {})[field]),
        dmig: YEARS.map(y => (dDer.per_year[y] || {})[field]),
        tickFormat: '.1%',
      };
    }
    X.dualLine(document.getElementById('prof-op-line'),     Object.assign(lineFor('op_margin'),     { yLabel: 'OP 마진' }));
    X.dualLine(document.getElementById('prof-ebitda-line'), Object.assign(lineFor('ebitda_margin'), { yLabel: 'EBITDA 마진' }));
    X.dualLine(document.getElementById('prof-ni-line'),     Object.assign(lineFor('ni_margin'),     { yLabel: 'NI 마진' }));
    /* GP 마진은 5y 가용 X — placeholder note */
    const gpEl = document.getElementById('prof-gp-line');
    gpEl.innerHTML = '<div style="padding:24px;background:var(--color-surface-alt);border-radius:8px;font-size:13px;color:var(--color-text-muted);text-align:center">GP 마진 (매출총이익률)은 company-level 5년 COGS 미공시 →<br>AR Note 기반 FY22-25 4년만 가용. 비용 구조 탭 참조.</div>';

    /* ----- 3.3 ROA / ROE 5y ----- */
    X.dualLine(document.getElementById('prof-roa-line'), Object.assign(lineFor('roa_avg'), { yLabel: 'ROA (평균 자산 기준)' }));
    X.dualLine(document.getElementById('prof-roe-line'), Object.assign(lineFor('roe_avg'), { yLabel: 'ROE (평균 자본 기준)' }));

    /* ----- 3.4 비영업 손익 의존도: (NI - OP) / Revenue ----- */
    function nonop(yearly) {
      return YEARS.map(y => {
        const yy = yearly[y] || {};
        if (yy.revenue == null || yy.net_profit == null || yy.operating_profit == null) return null;
        return (yy.net_profit - yy.operating_profit) / yy.revenue;
      });
    }
    X.dualLine(document.getElementById('prof-nonop'), {
      years: YEARS,
      pipg: nonop(pipg.yearly),
      dmig: nonop(dmig.yearly),
      tickFormat: '.1%',
      yLabel: '(순이익 − 영업이익) / 매출',
    });

    /* ----- 3.5 PIPG 14y margin trajectory ----- */
    const pl = data.pipgLong && data.pipgLong.pnl;
    if (pl) {
      const years = pl.years;
      const revenue = pl.lines['매출액'] || pl.lines['Revenue'] || {};
      const opIncome = pl.lines['영업이익'] || pl.lines['Operating profit'] || {};
      const niIncome = pl.lines['당기순이익'] || pl.lines['Net profit'] || {};
      const opMargin = years.map(y => (opIncome[y] != null && revenue[y]) ? opIncome[y] / revenue[y] : null);
      const niMargin = years.map(y => (niIncome[y] != null && revenue[y]) ? niIncome[y] / revenue[y] : null);
      const el = document.getElementById('prof-pipg-long-chart');
      const c = X.colours();
      Plotly.react(el, [
        { x: years, y: opMargin, type: 'scatter', mode: 'lines+markers', name: 'OP 마진',
          line: { color: c.pipg, width: 2.5 }, marker: { color: c.pipg, size: 6 } },
        { x: years, y: niMargin, type: 'scatter', mode: 'lines+markers', name: 'NI 마진',
          line: { color: c.pipgSoft, width: 2.5, dash: 'dash' }, marker: { color: c.pipgSoft, size: 6 } },
      ], {
        paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)',
        font: { color: c.text },
        margin: { l: 60, r: 20, t: 20, b: 50 },
        yaxis: { tickformat: '.0%', gridcolor: c.border },
        xaxis: { gridcolor: c.border, tickangle: -30 },
        legend: { orientation: 'h', y: -0.18 },
      }, { displayModeBar: false, responsive: true });
    }

    /* ----- Footer ----- */
    document.getElementById('prof-footer').innerHTML = `
      <div>· 5년 P&L: <code>company_financials_5y.json</code> (영업이익, EBITDA, 순이익, 매출)</div>
      <div>· ROA·ROE는 (평균 자산/자본) 기준 — FY20은 prior year 미가용으로 end-of-period 사용</div>
      <div>· GP 마진 (매출총이익률): notes-only — FY22-FY25만 AR Note에서 가용 (비용 구조 탭 참조)</div>
      <div>· PIPG 14y 마진: <code>pipg_pptx_data.json#pnl</code></div>
    `;
  });
})();
