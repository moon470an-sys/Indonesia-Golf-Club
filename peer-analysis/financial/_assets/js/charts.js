/* Plotly chart wrappers tailored for the PIPG-vs-DMIG comparison site.
   Every wrapper reads CSS custom properties so the chart colours follow the
   active light/dark theme. Pure presentational layer — no data derivation. */
(function (global) {
  'use strict';

  function token(name) {
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  }
  function colours() {
    return {
      pipg:      token('--color-pipg'),
      dmig:      token('--color-dmig'),
      pipgSoft:  token('--color-pipg-soft'),
      dmigSoft:  token('--color-dmig-soft'),
      muted:     token('--color-text-muted'),
      text:      token('--color-text'),
      border:    token('--color-border'),
      surface:   token('--color-surface'),
      peerOther: token('--color-peer-other'),
      pos:       token('--color-pos'),
      neg:       token('--color-neg'),
    };
  }

  function baseLayout(extra) {
    const c = colours();
    return Object.assign({
      paper_bgcolor: 'rgba(0,0,0,0)',
      plot_bgcolor:  'rgba(0,0,0,0)',
      font: { family: '-apple-system, "Inter", "Noto Sans KR", sans-serif',
              size: 12, color: c.text },
      margin: { l: 60, r: 20, t: 30, b: 50 },
      xaxis: { gridcolor: c.border, zerolinecolor: c.border, tickcolor: c.muted },
      yaxis: { gridcolor: c.border, zerolinecolor: c.border, tickcolor: c.muted },
      legend: { orientation: 'h', y: -0.18, x: 0, font: { size: 11 } },
      hovermode: 'closest',
    }, extra || {});
  }

  const CONFIG = { displayModeBar: false, responsive: true };

  /* Bar with PIPG and DMIG values for one metric. */
  function dualBar(el, opts) {
    const c = colours();
    const data = [
      { x: ['PIPG'], y: [opts.pipgValue], type: 'bar',
        marker: { color: c.pipg }, name: 'PIPG',
        text: [opts.pipgText || formatVal(opts.pipgValue, opts.format)],
        textposition: 'outside', cliponaxis: false },
      { x: ['DMIG'], y: [opts.dmigValue], type: 'bar',
        marker: { color: c.dmig }, name: 'DMIG',
        text: [opts.dmigText || formatVal(opts.dmigValue, opts.format)],
        textposition: 'outside', cliponaxis: false },
    ];
    const layout = baseLayout({
      title: { text: opts.title || '', font: { size: 13 } },
      showlegend: false,
      yaxis: { gridcolor: c.border, tickformat: opts.tickFormat },
      bargap: 0.45,
    });
    Plotly.react(el, data, layout, CONFIG);
  }

  /* Grouped bar across N metrics, two series (PIPG, DMIG). */
  function dualMetricGroup(el, opts) {
    const c = colours();
    const data = [
      { x: opts.metrics, y: opts.pipg, type: 'bar', name: 'PIPG',
        marker: { color: c.pipg },
        text: opts.pipg.map(v => formatVal(v, opts.format)),
        textposition: 'outside', cliponaxis: false },
      { x: opts.metrics, y: opts.dmig, type: 'bar', name: 'DMIG',
        marker: { color: c.dmig },
        text: opts.dmig.map(v => formatVal(v, opts.format)),
        textposition: 'outside', cliponaxis: false },
    ];
    const layout = baseLayout({
      barmode: 'group',
      bargap: 0.25, bargroupgap: 0.05,
      yaxis: { gridcolor: c.border, tickformat: opts.tickFormat },
      margin: { l: 60, r: 20, t: 30, b: 70 },
    });
    Plotly.react(el, data, layout, CONFIG);
  }

  /* Two lines across N years (PIPG, DMIG). */
  function dualLine(el, opts) {
    const c = colours();
    const data = [
      { x: opts.years, y: opts.pipg, type: 'scatter', mode: 'lines+markers',
        name: 'PIPG', line: { color: c.pipg, width: 2.5 },
        marker: { size: 7, color: c.pipg },
        hovertemplate: '%{x}: ' + (opts.hoverPrefix || '') + '%{y:' + (opts.tickFormat || '.2s') + '}<extra>PIPG</extra>' },
      { x: opts.years, y: opts.dmig, type: 'scatter', mode: 'lines+markers',
        name: 'DMIG', line: { color: c.dmig, width: 2.5 },
        marker: { size: 7, color: c.dmig },
        hovertemplate: '%{x}: ' + (opts.hoverPrefix || '') + '%{y:' + (opts.tickFormat || '.2s') + '}<extra>DMIG</extra>' },
    ];
    const layout = baseLayout({
      yaxis: { gridcolor: c.border, tickformat: opts.tickFormat, title: { text: opts.yLabel || '', font: { size: 11 } } },
      xaxis: { gridcolor: c.border, tickmode: 'array', tickvals: opts.years },
    });
    Plotly.react(el, data, layout, CONFIG);
  }

  /* Side-by-side 100% stacked composition (e.g. asset mix). One element each. */
  function stacked100(el, opts) {
    /* opts.series = [ {label, pipg, dmig, color}, ... ]
       Renders PIPG and DMIG as two grouped 100% stacked bars. */
    const c = colours();
    const total = (arr) => arr.reduce((a,b) => a + (b||0), 0);
    const pipgTot = total(opts.series.map(s => s.pipg));
    const dmigTot = total(opts.series.map(s => s.dmig));
    const data = opts.series.map((s, i) => ({
      x: ['PIPG', 'DMIG'],
      y: [pipgTot ? s.pipg / pipgTot : 0,
          dmigTot ? s.dmig / dmigTot : 0],
      type: 'bar',
      name: s.label,
      marker: { color: s.color || segmentColor(i) },
      text: [s.pipg ? (s.pipg/pipgTot*100).toFixed(0)+'%' : '',
             s.dmig ? (s.dmig/dmigTot*100).toFixed(0)+'%' : ''],
      textposition: 'inside',
      hovertemplate: '%{x}: ' + s.label + ' %{y:.1%}<extra></extra>',
    }));
    const layout = baseLayout({
      barmode: 'stack',
      yaxis: { tickformat: '.0%', gridcolor: c.border, range: [0, 1] },
      legend: { orientation: 'h', y: -0.18, x: 0, font: { size: 11 } },
      bargap: 0.45,
    });
    Plotly.react(el, data, layout, CONFIG);
  }

  /* PIPG long-history single line (FY11-FY24). Used inside <details>. */
  function pipgLongLine(el, opts) {
    const c = colours();
    const data = [{
      x: opts.years, y: opts.values, type: 'scatter', mode: 'lines+markers',
      name: 'PIPG (14y)',
      line:   { color: c.pipg, width: 2 },
      marker: { color: c.pipg, size: 5 },
      hovertemplate: 'FY%{x}: %{y:' + (opts.tickFormat || ',') + '}<extra></extra>',
    }];
    const layout = baseLayout({
      yaxis: { gridcolor: c.border, tickformat: opts.tickFormat, title: { text: opts.yLabel || '', font: { size: 11 } } },
      xaxis: { gridcolor: c.border, tickangle: -30 },
      margin: { l: 60, r: 20, t: 10, b: 50 },
    });
    Plotly.react(el, data, layout, CONFIG);
  }

  /* Peer Context tab — 13-peer ranking bar, PIPG and DMIG highlighted */
  function peerRankingBar(el, opts) {
    const c = colours();
    const colours_ = opts.tickers.map(t =>
      t === 'PIPG' ? c.pipg :
      t === 'DMIG' ? c.dmig :
      c.peerOther);
    const data = [{
      x: opts.tickers, y: opts.values, type: 'bar',
      marker: { color: colours_ },
      text: opts.values.map(v => formatVal(v, opts.format)),
      textposition: 'outside', cliponaxis: false,
    }];
    const layout = baseLayout({
      yaxis: { gridcolor: c.border, tickformat: opts.tickFormat,
               title: { text: opts.yLabel || '', font: { size: 11 } } },
      xaxis: { gridcolor: c.border, tickangle: -45, automargin: true },
      margin: { l: 60, r: 20, t: 20, b: 70 },
    });
    Plotly.react(el, data, layout, CONFIG);
  }

  function segmentColor(i) {
    const palette = ['#1B3A5F', '#0EA5E9', '#10B981', '#F59E0B', '#8B5CF6',
                     '#EC4899', '#14B8A6', '#F43F5E', '#84CC16', '#06B6D4',
                     '#A855F7', '#EAB308', '#94A3B8'];
    return palette[i % palette.length];
  }

  function formatVal(v, fmt) {
    if (v === null || v === undefined || !isFinite(v)) return 'N/A';
    if (!fmt) return v.toLocaleString();
    if (fmt === 'IDR_B') return 'Rp ' + (v / 1e9).toFixed(1) + 'B';
    if (fmt === 'IDR_M') return 'Rp ' + (v / 1e6).toFixed(0) + 'M';
    if (fmt === 'pct')   return (v * 100).toFixed(1) + '%';
    if (fmt === 'pct0')  return (v * 100).toFixed(0) + '%';
    if (fmt === 'int')   return Math.round(v).toLocaleString();
    return v.toLocaleString();
  }

  /* Redraw all currently-rendered Plotly charts to pick up new theme tokens. */
  function refreshAll() {
    document.querySelectorAll('.chart').forEach(el => {
      if (el._fullLayout) {
        Plotly.relayout(el, baseLayout({
          xaxis: el._fullLayout.xaxis ? { gridcolor: token('--color-border') } : undefined,
          yaxis: el._fullLayout.yaxis ? { gridcolor: token('--color-border') } : undefined,
          font: { color: token('--color-text') },
        }));
      }
    });
  }

  global.PurePlayCharts = {
    dualBar, dualMetricGroup, dualLine, stacked100,
    pipgLongLine, peerRankingBar, refreshAll,
    formatVal, segmentColor, colours,
  };
})(window);
