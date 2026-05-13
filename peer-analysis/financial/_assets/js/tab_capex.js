/* Tab 5: 자산·CAPEX */
(function () {
  'use strict';
  const YEARS = ['2020','2021','2022','2023','2024','2025'];

  PurePlayTabs.register('capex', function (data) {
    const C = PurePlayCompare;
    const X = PurePlayCharts;
    const pipg = data.pipg, dmig = data.dmig;

    /* ----- 5.1 총자산 vs 매출 (PPE 단독 5y 미공시 → 총자산 proxy) ----- */
    const c = X.colours();
    Plotly.react(document.getElementById('capex-assets-revenue'), [
      { x: YEARS, y: YEARS.map(y => (pipg.yearly[y] || {}).total_assets), type: 'scatter', mode: 'lines+markers',
        name: 'PIPG 총자산', line: { color: c.pipg, width: 2.5 }, marker: { color: c.pipg } },
      { x: YEARS, y: YEARS.map(y => (pipg.yearly[y] || {}).revenue), type: 'scatter', mode: 'lines+markers',
        name: 'PIPG 매출', line: { color: c.pipg, width: 1.5, dash: 'dot' }, marker: { color: c.pipg, size: 5 } },
      { x: YEARS, y: YEARS.map(y => (dmig.yearly[y] || {}).total_assets), type: 'scatter', mode: 'lines+markers',
        name: 'DMIG 총자산', line: { color: c.dmig, width: 2.5 }, marker: { color: c.dmig } },
      { x: YEARS, y: YEARS.map(y => (dmig.yearly[y] || {}).revenue), type: 'scatter', mode: 'lines+markers',
        name: 'DMIG 매출', line: { color: c.dmig, width: 1.5, dash: 'dot' }, marker: { color: c.dmig, size: 5 } },
    ], {
      paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)',
      font: { color: c.text },
      yaxis: { tickformat: '.2s', gridcolor: c.border, title: { text: 'IDR (Rp)', font: { size: 11 } } },
      xaxis: { gridcolor: c.border },
      legend: { orientation: 'h', y: -0.18 },
      margin: { l: 70, r: 20, t: 20, b: 50 },
    }, { displayModeBar: false, responsive: true });

    /* ----- 5.2 매출/총자산 회전율 ----- */
    function turnover(yearly) {
      return YEARS.map(y => {
        const yy = yearly[y] || {};
        if (!yy.revenue || !yy.total_assets) return null;
        return yy.revenue / yy.total_assets;
      });
    }
    X.dualLine(document.getElementById('capex-asset-turnover'), {
      years: YEARS,
      pipg: turnover(pipg.yearly),
      dmig: turnover(dmig.yearly),
      tickFormat: '.2f',
      yLabel: '매출 / 총자산 (회전율)',
    });

    /* ----- 5.3 PIPG 14y PPE category long-history ----- */
    const ppe = data.pipgLong && data.pipgLong.capex_ppe_14y;
    if (ppe && ppe.categories) {
      /* Stacked area of book_value for each PPE category, FY11-FY24 */
      const allYears = ppe.years.filter(y => /^\d{4}$/.test(y));   // exclude avg_11_25
      /* Skip 'Total' and the unit row */
      const catNames = Object.keys(ppe.categories).filter(k =>
        k && k !== 'Total' && k.indexOf('단위') === -1);
      const traces = catNames.map((cat, i) => ({
        x: allYears,
        y: allYears.map(y => {
          const v = ppe.categories[cat][y];
          return v && typeof v === 'object' ? v.book_value : null;
        }),
        type: 'scatter', mode: 'lines', stackgroup: 'one',
        name: cat,
        line: { width: 0.5 },
        fillcolor: X.segmentColor(i),
        hovertemplate: cat + ' FY%{x}: %{y:,} Mil<extra></extra>',
      }));
      Plotly.react(document.getElementById('capex-pipg-ppe'), traces, {
        paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)',
        font: { color: c.text },
        yaxis: { gridcolor: c.border, title: { text: '장부가 (IDR Million)', font: { size: 11 } }, tickformat: ',' },
        xaxis: { gridcolor: c.border, tickangle: -30 },
        legend: { orientation: 'v', x: 1.02, y: 1, font: { size: 10 } },
        margin: { l: 70, r: 130, t: 20, b: 50 },
        hovermode: 'x unified',
      }, { displayModeBar: false, responsive: true });
    }

    /* ----- Footer ----- */
    document.getElementById('capex-footer').innerHTML = `
      <div>· PPE 단독 시계열은 양사 모두 5년 미공시 → 총자산 proxy 사용</div>
      <div>· PIPG 14y PPE 11+ 카테고리: <code>pipg_pptx_data.json#capex_ppe_14y</code> (PPT §7)</div>
      <div>· DMIG는 PPE 카테고리·신규투자·감가상각 분해 미공시 — 본 탭의 long-history는 PIPG single-peer reference</div>
    `;
  });
})();
