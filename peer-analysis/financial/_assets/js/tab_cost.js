/* Tab 6: 비용 구조 */
(function () {
  'use strict';
  const YEARS = ['2020','2021','2022','2023','2024','2025'];

  PurePlayTabs.register('cost', function (data) {
    const C = PurePlayCompare;
    const X = PurePlayCharts;
    const pipg = data.pipg, dmig = data.dmig;

    /* ----- 6.1 매출 100% stacked (COGS / OPEX / OP profit), FY24 -----
       PIPG financial_highlights uses thousand-Rp, DMIG notes raw.
       Use yearly revenue + opex_note totals as the most consistent FY24 source.
    */
    const pNotes = pipg.notes || {};
    const dNotes = dmig.notes || {};
    /* PIPG COGS FY24 (raw IDR) from financial_highlights (thousand IDR) */
    let pCogsFY24 = null, pOpexFY24 = null;
    if (pNotes.financial_highlights && pNotes.financial_highlights.rows_in_idr_thousand) {
      const rows = pNotes.financial_highlights.rows_in_idr_thousand;
      const b = rows.find(r => r.label === 'Beban Pokok');
      if (b && b.FY2024 != null) pCogsFY24 = b.FY2024 * 1000;  // convert to raw IDR (was thousand)
      const o = rows.find(r => r.label === 'Beban Usaha');
      if (o && o.FY2024 != null) pOpexFY24 = o.FY2024 * 1000;
    }
    /* DMIG COGS / OPEX FY24 from cogs_note.total / opex_note.total */
    let dCogsFY24 = null, dOpexFY24 = null;
    if (dNotes.cogs_note && dNotes.cogs_note.total) dCogsFY24 = dNotes.cogs_note.total.FY2024;
    if (dNotes.opex_note && dNotes.opex_note.total) dOpexFY24 = dNotes.opex_note.total.FY2024;

    const pRev = (pipg.yearly['2024'] || {}).revenue;
    const dRev = (dmig.yearly['2024'] || {}).revenue;
    const pOp = (pipg.yearly['2024'] || {}).operating_profit;
    const dOp = (dmig.yearly['2024'] || {}).operating_profit;
    /* Note: PIPG COGS is negative in financial_highlights; take absolute */
    const absVal = v => v != null ? Math.abs(v) : null;

    X.stacked100(document.getElementById('cost-cogs-opex-stack'), {
      series: [
        { label: '매출원가 (COGS)', pipg: absVal(pCogsFY24), dmig: absVal(dCogsFY24), color: '#F59E0B' },
        { label: '영업비용 (OPEX)', pipg: absVal(pOpexFY24), dmig: absVal(dOpexFY24), color: '#EF4444' },
        { label: '영업이익',         pipg: pOp,                dmig: dOp,                color: '#10B981' },
      ],
    });

    /* ----- 6.2 COGS ratio 5y (notes-only, FY22-FY24 + FY25 follow-up) ----- */
    const cogsYears = ['2022','2023','2024','2025'];
    function cogsRatio(notes, yearly) {
      return cogsYears.map(y => {
        const fy = 'FY' + y;
        let cogs = null, rev = null;
        /* Use opex_note totals for the comparable years, or financial_highlights */
        if (y === '2025') {
          /* FY25 from fy2025_follow_up.pnl_FY2025 */
          const f25 = notes.fy2025_follow_up && notes.fy2025_follow_up.pnl_FY2025;
          if (f25) { cogs = Math.abs(f25.cogs); rev = f25.revenue; }
        } else {
          /* PIPG: financial_highlights rows in thousand IDR */
          if (notes.financial_highlights) {
            const rows = notes.financial_highlights.rows_in_idr_thousand || [];
            const b = rows.find(r => r.label === 'Beban Pokok');
            const r = rows.find(r => r.label === 'Pendapatan Usaha');
            if (b && b[fy] != null) cogs = Math.abs(b[fy] * 1000);
            if (r && r[fy] != null) rev = r[fy] * 1000;
          }
          /* DMIG: cogs_note.total + revenue_note.total */
          if (cogs == null && notes.cogs_note && notes.cogs_note.total) cogs = notes.cogs_note.total[fy];
          if (rev == null && notes.revenue_note && notes.revenue_note.total) rev = notes.revenue_note.total[fy];
        }
        return (cogs != null && rev) ? cogs / rev : null;
      });
    }
    X.dualLine(document.getElementById('cost-cogs-ratio'), {
      years: cogsYears,
      pipg: cogsRatio(pNotes, pipg.yearly),
      dmig: cogsRatio(dNotes, dmig.yearly),
      tickFormat: '.1%',
      yLabel: '매출원가율 (COGS / Revenue)',
    });

    /* ----- 6.3 OPEX 17 항목 normalised 1:1 (FY24) ----- */
    const pipgOpexLines = (pNotes.opex_note_29 && pNotes.opex_note_29.lines) || [];
    const dmigOpexLines = (dNotes.opex_note    && dNotes.opex_note.lines)    || [];
    const pNorm = C.normaliseOpex(pipgOpexLines, 'pipg');
    const dNorm = C.normaliseOpex(dmigOpexLines, 'dmig');
    /* Build merged rows: norm category -> {pipg FY24, dmig FY24} */
    const merged = C.OPEX_MAP.map((m, i) => ({
      norm: m.norm,
      pipg: (pNorm[i] && pNorm[i].values && pNorm[i].values.FY2024) || null,
      dmig: (dNorm[i] && dNorm[i].values && dNorm[i].values.FY2024) || null,
    }));
    /* Sort by max(pipg+dmig) desc for legibility */
    merged.sort((a, b) => ((b.pipg || 0) + (b.dmig || 0)) - ((a.pipg || 0) + (a.dmig || 0)));

    X.dualMetricGroup(document.getElementById('cost-opex-bars'), {
      metrics: merged.map(m => m.norm),
      pipg: merged.map(m => m.pipg),
      dmig: merged.map(m => m.dmig),
      tickFormat: '.2s',
    });

    /* Mapping table */
    const mapHtml = `
      <details>
        <summary style="cursor:pointer;font-size:13px;color:var(--color-text-muted);font-weight:600">OPEX 라벨 매핑표 (PIPG ↔ DMIG, 23 normalised)</summary>
        <table class="cmp-table" style="margin-top:8px">
          <thead><tr><th>Normalised</th><th>PIPG label</th><th>DMIG label</th></tr></thead>
          <tbody>${C.OPEX_MAP.map(m => `
            <tr>
              <td>${m.norm}</td>
              <td>${m.pipg || '<span class="na-cell">—</span>'}</td>
              <td>${m.dmig || '<span class="na-cell">—</span>'}</td>
            </tr>`).join('')}</tbody>
        </table>
      </details>`;
    document.getElementById('cost-opex-mapping-table').innerHTML = mapHtml;

    /* ----- 6.4 PIPG 14y OPEX long ----- */
    const longOpex = data.pipgLong && data.pipgLong.opex_14y;
    if (longOpex && longOpex.lines) {
      const yrs = longOpex.years;
      const top5 = longOpex.lines.slice()
        .sort((a, b) => (b.yearly[yrs[yrs.length-1]] || 0) - (a.yearly[yrs[yrs.length-1]] || 0))
        .slice(0, 5);
      const traces = top5.map((line, i) => ({
        x: yrs,
        y: yrs.map(y => line.yearly[y]),
        type: 'scatter', mode: 'lines+markers',
        name: line.label_ko,
        line: { color: X.segmentColor(i), width: 2 },
        marker: { size: 5 },
      }));
      const c = X.colours();
      Plotly.react(document.getElementById('cost-pipg-opex-long'), traces, {
        paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)',
        font: { color: c.text },
        yaxis: { tickformat: ',', gridcolor: c.border, title: { text: 'IDR Million', font: { size: 11 } } },
        xaxis: { gridcolor: c.border, tickangle: -30 },
        legend: { orientation: 'h', y: -0.22, font: { size: 11 } },
        margin: { l: 70, r: 20, t: 20, b: 70 },
      }, { displayModeBar: false, responsive: true });
    }

    /* ----- Footer ----- */
    document.getElementById('cost-footer').innerHTML = `
      <div>· PIPG OPEX (FY22-FY24): <code>pipg_notes.json#opex_note_29</code> (17 lines)</div>
      <div>· DMIG OPEX (FY22-FY24): <code>dmig_notes.json#opex_note</code> (17 lines)</div>
      <div>· FY25 P&L 단년: <code>{pipg,dmig}_notes.json#fy2025_follow_up</code></div>
      <div>· PIPG 14y OPEX 18 lines: <code>pipg_pptx_data.json#opex_14y</code></div>
      <div>· 매핑은 PIPG·DMIG 17 라인을 23 normalised category로 통합. 한쪽 미공시 항목은 빈 막대.</div>
    `;
  });
})();
