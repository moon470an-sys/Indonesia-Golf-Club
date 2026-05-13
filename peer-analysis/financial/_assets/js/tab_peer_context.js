/* Tab 8: Peer Context — 11개사 보조 컨텍스트 */
(function () {
  'use strict';
  const FY = '2024';

  /* Categorisation for "Pure-play 제외 사유" annotation per tier */
  const TIER_LABEL = {
    'PIPG':'Tier 1 (Pure-play)',  'DMIG':'Tier 1 (Pure-play)',
    'GOLF':'Tier 1 (Pure-play)',
    'MDLN':'Tier 2 (Group + golf segment)',
    'KIJA':'Tier 2 (Group + golf segment)',
    'SMDM':'Tier 2 (Group + golf segment)',
    'KPIG':'Tier 3 (Hotel/Resort adjacent)',
    'SMRA':'Tier 3 (Hotel/Resort adjacent)',
    'BSDE':'Tier 4 (Property group + 1+ golf)',
    'CTRA':'Tier 4 (Property group + 1+ golf)',
    'ELTY':'Tier 4 (Property group + 1+ golf)',
    'LPKR':'Tier 4 (Property group + 1+ golf)',
    'PWON':'Tier 4 (Property group + 1+ golf)',
  };
  const EXCLUDE_REASON = {
    'GOLF':'Tier 1이지만 매출 규모가 매우 작아 1:1 비교에서 보조 참조로 분리',
    'MDLN':'Township amenity — 골프 segment만 분리 공시 (그룹 매출 대비 ~1-2%)',
    'KIJA':'Industrial estate developer — 골프는 부속 amenity',
    'SMDM':'Township amenity — segment restatement caveat 존재',
    'KPIG':'Hotel/Resort/Golf 통합 segment, 골프 단독 분리 불가',
    'SMRA':'Hotel/Resort 통합, 골프 단독 비공시',
    'BSDE':'BSD City township — 골프 매출 그룹 매출의 ~1%',
    'CTRA':'다 township에 2 코스 amenity — 그룹 BS 통합',
    'ELTY':'Bakrieland 다 township — 골프 segment 비공시',
    'LPKR':'Imperial Klub amenity — Lippo 그룹 BS 통합',
    'PWON':'Surabaya township amenity — segment 비공시',
  };

  PurePlayTabs.register('peer-context', function (data) {
    const C = PurePlayCompare;
    const X = PurePlayCharts;

    const peers = data.peers || [];
    /* ----- 8.1 FY24 revenue ranking ----- */
    const ranked = peers.slice().filter(p => (p.yearly[FY] || {}).revenue != null)
      .sort((a, b) => (b.yearly[FY].revenue) - (a.yearly[FY].revenue));
    X.peerRankingBar(document.getElementById('pc-revenue-rank'), {
      tickers: ranked.map(p => p.ticker),
      values:  ranked.map(p => p.yearly[FY].revenue),
      tickFormat: '.2s',
      format: 'IDR_B',
      yLabel: 'FY24 그룹 매출 (IDR)',
    });

    /* ----- 8.2 FY24 total assets ranking ----- */
    const assRank = peers.slice().filter(p => (p.yearly[FY] || {}).total_assets != null)
      .sort((a, b) => (b.yearly[FY].total_assets) - (a.yearly[FY].total_assets));
    X.peerRankingBar(document.getElementById('pc-assets-rank'), {
      tickers: assRank.map(p => p.ticker),
      values:  assRank.map(p => p.yearly[FY].total_assets),
      tickFormat: '.2s',
      format: 'IDR_B',
      yLabel: 'FY24 그룹 총자산 (IDR)',
    });

    /* ----- 8.3 OP margin / ROA distribution ----- */
    function opMargin(p) {
      const y = p.yearly[FY] || {};
      if (!y.revenue || y.operating_profit == null) return null;
      return y.operating_profit / y.revenue;
    }
    function roa(p) {
      const y = p.yearly[FY] || {};
      if (!y.total_assets || y.net_profit == null) return null;
      return y.net_profit / y.total_assets;
    }
    function distChart(elId, fn, label, fmt) {
      const c = X.colours();
      const pure = peers.filter(p => ['PIPG','DMIG'].includes(p.ticker));
      const others = peers.filter(p => !['PIPG','DMIG'].includes(p.ticker));
      Plotly.react(document.getElementById(elId), [
        { y: others.map(fn).filter(v => v != null), type: 'box', name: 'Tier 2-4 (11개)',
          marker: { color: c.peerOther },
          boxpoints: 'all', jitter: 0.5, pointpos: 0,
          text: others.map(p => p.ticker), hoverinfo: 'text+y' },
        { y: [fn(pure.find(p => p.ticker==='PIPG'))], x: ['Tier 2-4 (11개)'],
          type: 'scatter', mode: 'markers+text', name: 'PIPG',
          marker: { color: c.pipg, size: 16, symbol: 'diamond' },
          text: ['PIPG'], textposition: 'middle right', textfont: { size: 12 } },
        { y: [fn(pure.find(p => p.ticker==='DMIG'))], x: ['Tier 2-4 (11개)'],
          type: 'scatter', mode: 'markers+text', name: 'DMIG',
          marker: { color: c.dmig, size: 16, symbol: 'diamond' },
          text: ['DMIG'], textposition: 'middle right', textfont: { size: 12 } },
      ], {
        paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)',
        font: { color: c.text },
        yaxis: { tickformat: fmt === 'pct' ? '.1%' : ',', gridcolor: c.border, title: { text: label, font: { size: 11 } } },
        xaxis: { gridcolor: c.border },
        showlegend: false,
        margin: { l: 70, r: 20, t: 20, b: 50 },
      }, { displayModeBar: false, responsive: true });
    }
    distChart('pc-opm-box', opMargin, 'OP 마진', 'pct');
    distChart('pc-roa-box', roa, 'ROA (end-of-period)', 'pct');

    /* ----- 8.4 13 peer cards grid ----- */
    const gridHtml = peers.map(p => {
      const isPure = ['PIPG','DMIG'].includes(p.ticker);
      const meta = p.meta || {};
      const rev = (p.yearly[FY] || {}).revenue;
      const yLink = '../operations/clubs/' + p.ticker.toLowerCase() + '.html';
      return `
        <a href="${yLink}" class="peer-context-card ${isPure ? 'pure' : ''}">
          <div class="ticker">${p.ticker}</div>
          <div class="name">${(meta.name || '').slice(0, 40)}</div>
          <div class="tier">${TIER_LABEL[p.ticker] || '—'}</div>
          <div class="rev">${C.fmtIDR(rev)}</div>
          ${isPure ? '<div class="badge">Pure-play 비교 대상</div>'
                   : '<div class="reason">' + (EXCLUDE_REASON[p.ticker] || '') + '</div>'}
        </a>`;
    }).join('');
    document.getElementById('pc-peer-grid').innerHTML = `
      <style>
        .peer-context-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 12px; }
        .peer-context-card { display: block; padding: 14px; border-radius: 8px;
                            border: 1px solid var(--color-border); background: var(--color-surface);
                            color: var(--color-text); text-decoration: none; transition: 0.15s; }
        .peer-context-card:hover { border-color: var(--color-divider); text-decoration: none;
                                   transform: translateY(-1px); box-shadow: var(--shadow); }
        .peer-context-card.pure { border-left: 4px solid var(--color-pipg); }
        .peer-context-card .ticker { font-weight: 700; font-size: 16px; }
        .peer-context-card .name { font-size: 12px; color: var(--color-text-muted); margin: 2px 0; }
        .peer-context-card .tier { font-size: 11px; color: var(--color-text-muted); margin-top: 4px;
                                  text-transform: uppercase; letter-spacing: 0.4px; font-weight: 600; }
        .peer-context-card .rev  { font-size: 14px; font-weight: 600; margin-top: 6px;
                                  font-variant-numeric: tabular-nums; }
        .peer-context-card .badge { margin-top: 8px; font-size: 11px; color: var(--color-pipg); font-weight: 600; }
        .peer-context-card .reason { margin-top: 8px; font-size: 11px; color: var(--color-text-muted); line-height: 1.4; }
      </style>
      <div class="peer-context-grid">${gridHtml}</div>`;

    document.getElementById('pc-footer').innerHTML = `
      <div>· 13 peer 5y financials: <code>company_financials_5y.json</code></div>
      <div>· Tier 분류 (v2 cycle 168): <code>company_financials_5y.json#metadata.peer_group_v2</code></div>
      <div>· 그룹 매출 기준이므로 Tier 4 peer는 골프 부문 매출이 노출되지 않음 (그룹 ~1-2%)</div>
    `;
  });
})();
