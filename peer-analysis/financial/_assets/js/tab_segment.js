/* Tab 7: 수익 다각화 (Segment / Revenue mix) */
(function () {
  'use strict';
  const FY = 'FY2024';

  PurePlayTabs.register('segment', function (data) {
    const C = PurePlayCompare;
    const X = PurePlayCharts;
    const pipg = data.pipg, dmig = data.dmig;
    const pNotes = pipg.notes || {};
    const dNotes = dmig.notes || {};

    const pipgLines = (pNotes.revenue_note_27 && pNotes.revenue_note_27.lines) || [];
    const dmigLines = (dNotes.revenue_note    && dNotes.revenue_note.lines)    || [];
    const pNorm = C.normaliseSegments(pipgLines, 'pipg');
    const dNorm = C.normaliseSegments(dmigLines, 'dmig');

    /* ----- 7.1 매출 구성 1:1 stacked (FY24) ----- */
    const series = C.SEGMENT_MAP.map((m, i) => ({
      label: m.norm,
      pipg: (pNorm[i].values && pNorm[i].values[FY]) || 0,
      dmig: (dNorm[i].values && dNorm[i].values[FY]) || 0,
      color: X.segmentColor(i),
    }));
    X.stacked100(document.getElementById('segment-mix-stack'), { series });

    /* ----- 7.2 골프 vs 부수 수익원 pie grid ----- */
    document.getElementById('segment-pie-grid').innerHTML = `
      <div id="segment-pie-pipg" class="chart"></div>
      <div id="segment-pie-dmig" class="chart"></div>`;
    function pieFor(elId, label, color, lines) {
      const items = lines.filter(l => l.values && l.values[FY]).map(l => ({
        label: l.norm, value: l.values[FY] || 0,
      }));
      const c = X.colours();
      Plotly.react(document.getElementById(elId), [{
        labels: items.map(i => i.label),
        values: items.map(i => i.value),
        type: 'pie',
        textinfo: 'label+percent',
        textposition: 'outside',
        marker: { colors: items.map((_, i) => X.segmentColor(i)) },
        hovertemplate: '%{label}: %{value:,} (%{percent})<extra></extra>',
      }], {
        title: { text: label, font: { color: color, size: 14 } },
        paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)',
        font: { color: c.text, size: 11 },
        margin: { l: 20, r: 20, t: 40, b: 20 },
        showlegend: false,
      }, { displayModeBar: false, responsive: true });
    }
    pieFor('segment-pie-pipg', 'PIPG (11 segments, AR Note 27)', X.colours().pipg, pNorm);
    pieFor('segment-pie-dmig', 'DMIG (7 segments, AR Note 23)',  X.colours().dmig, dNorm);

    /* ----- 7.3 Segment 절대값 1:1 bar (sorted desc) ----- */
    const sorted = C.SEGMENT_MAP.map((m, i) => ({
      norm: m.norm,
      pipg: (pNorm[i].values && pNorm[i].values[FY]) || 0,
      dmig: (dNorm[i].values && dNorm[i].values[FY]) || 0,
    })).filter(r => r.pipg || r.dmig)
      .sort((a, b) => (b.pipg + b.dmig) - (a.pipg + a.dmig));
    X.dualMetricGroup(document.getElementById('segment-abs-bars'), {
      metrics: sorted.map(s => s.norm),
      pipg: sorted.map(s => s.pipg || null),
      dmig: sorted.map(s => s.dmig || null),
      tickFormat: '.2s',
    });

    /* ----- 7.4 PIPG 14y segment evolution ----- */
    const longSeg = data.pipgLong && data.pipgLong.segment_revenue;
    if (longSeg && longSeg.segments) {
      const yrs = longSeg.years;
      const segs = Object.keys(longSeg.segments).filter(s =>
        s && s !== 'Total' && s.indexOf('단위') === -1);
      const traces = segs.map((seg, i) => ({
        x: yrs,
        y: yrs.map(y => {
          const yr = longSeg.segments[seg].yearly || longSeg.segments[seg];
          return (yr && yr[y] != null) ? yr[y] : null;
        }),
        type: 'scatter', mode: 'lines', stackgroup: 'one',
        name: seg, line: { width: 0.5 },
        fillcolor: X.segmentColor(i),
      }));
      const c = X.colours();
      Plotly.react(document.getElementById('segment-pipg-long'), traces, {
        paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)',
        font: { color: c.text },
        yaxis: { gridcolor: c.border, tickformat: ',', title: { text: '매출 (IDR Million)', font: { size: 11 } } },
        xaxis: { gridcolor: c.border, tickangle: -30 },
        legend: { orientation: 'v', x: 1.02, y: 1, font: { size: 10 } },
        margin: { l: 70, r: 130, t: 20, b: 50 },
        hovermode: 'x unified',
      }, { displayModeBar: false, responsive: true });
    }

    /* ----- Footer ----- */
    document.getElementById('segment-footer').innerHTML = `
      <div>· PIPG (FY23-FY24): <code>pipg_notes.json#revenue_note_27</code> (11 segments)</div>
      <div>· DMIG (FY22-FY24): <code>dmig_notes.json#revenue_note</code> (7 segments)</div>
      <div>· 정규화: 13 공통 카테고리 (Golf course / Restaurant / Membership / Driving range / Rent / Cart / Branding-sponsor / Sharing / Academy / Gym / Tournament / Recreation / Others)</div>
      <div>· PIPG 14y 13-segment 시계열: <code>pipg_pptx_data.json#segment_revenue</code> (PPT §6)</div>
    `;
  });
})();
