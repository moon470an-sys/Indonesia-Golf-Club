/* Tab 4: 성장성 (Growth) */
(function () {
  'use strict';
  const YEARS = ['2020','2021','2022','2023','2024','2025'];

  PurePlayTabs.register('growth', function (data) {
    const C = PurePlayCompare;
    const X = PurePlayCharts;
    const pipg = data.pipg, dmig = data.dmig;
    const pDer = C.derive(pipg.yearly);
    const dDer = C.derive(dmig.yearly);

    /* ----- 4.1 CAGR 3 metric bar ----- */
    const pC = pDer.cagr || {};
    const dC = dDer.cagr || {};
    X.dualMetricGroup(document.getElementById('growth-cagr'), {
      metrics: ['매출 CAGR', '총자산 CAGR', '순이익 CAGR'],
      pipg: [pC.revenue, pC.total_assets, pC.net_profit],
      dmig: [dC.revenue, dC.total_assets, dC.net_profit],
      tickFormat: '.1%',
      format: 'pct',
    });

    /* ----- 4.2 Normalised revenue FY20=100 ----- */
    function norm(yearly) {
      const base = (yearly['2020'] || {}).revenue;
      if (!base) return YEARS.map(() => null);
      return YEARS.map(y => {
        const r = (yearly[y] || {}).revenue;
        return r != null ? (r / base) * 100 : null;
      });
    }
    X.dualLine(document.getElementById('growth-normalised'), {
      years: YEARS,
      pipg: norm(pipg.yearly),
      dmig: norm(dmig.yearly),
      tickFormat: ',',
      yLabel: 'Revenue Index (FY20 = 100)',
    });

    /* ----- 4.3 YoY grouped bar ----- */
    const pYoY = C.yoyMap(pipg.yearly, 'revenue');
    const dYoY = C.yoyMap(dmig.yearly, 'revenue');
    const yoyYears = YEARS.slice(1);  // FY21-FY25
    X.dualMetricGroup(document.getElementById('growth-yoy'), {
      metrics: yoyYears.map(y => 'FY' + y.slice(-2)),
      pipg: yoyYears.map(y => pYoY[y]),
      dmig: yoyYears.map(y => dYoY[y]),
      tickFormat: '.1%',
      format: 'pct',
    });

    /* ----- 4.4 Revenue vs Asset CAGR scatter ----- */
    const el = document.getElementById('growth-scatter');
    const c = X.colours();
    const xs = [pC.revenue, dC.revenue];
    const ys = [pC.total_assets, dC.total_assets];
    Plotly.react(el, [
      { x: [pC.revenue], y: [pC.total_assets], type: 'scatter', mode: 'markers+text', name: 'PIPG',
        marker: { color: c.pipg, size: 24 }, text: ['PIPG'], textposition: 'top center', textfont: { color: c.pipg, size: 13 } },
      { x: [dC.revenue], y: [dC.total_assets], type: 'scatter', mode: 'markers+text', name: 'DMIG',
        marker: { color: c.dmig, size: 24 }, text: ['DMIG'], textposition: 'top center', textfont: { color: c.dmig, size: 13 } },
    ], {
      paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)',
      font: { color: c.text },
      xaxis: { title: { text: '매출 CAGR (FY20→FY25)' }, tickformat: '.1%', gridcolor: c.border, zeroline: true, zerolinecolor: c.muted },
      yaxis: { title: { text: '총자산 CAGR (FY20→FY25)' }, tickformat: '.1%', gridcolor: c.border, zeroline: true, zerolinecolor: c.muted },
      showlegend: false,
      margin: { l: 70, r: 30, t: 20, b: 60 },
    }, { displayModeBar: false, responsive: true });

    /* ----- Footer ----- */
    document.getElementById('growth-footer').innerHTML = `
      <div>· CAGR period: <code>${(pC.period || '—')}</code></div>
      <div>· YoY는 단순 연도간 % 변화. 정규화는 FY20 = 100 base.</div>
      <div>· Scatter는 FY20→FY25 단일 CAGR 점. 연도별 trajectory path는 향후 추가 예정.</div>
    `;
  });
})();
