/* Renders a club deep-dive page (PIPG or DMIG) using shared layout. */
(function (global) {
  'use strict';
  const YEARS = ['2020','2021','2022','2023','2024','2025'];

  function render(which, data) {
    const C = PurePlayCompare;
    const X = PurePlayCharts;
    const isPipg = which === 'pipg';
    const peer  = isPipg ? data.pipg : data.dmig;
    const other = isPipg ? data.dmig : data.pipg;
    const notes = peer.notes || {};

    /* ----- Hero specs ----- */
    const profileNotes = notes.profile || {};
    const fy24 = peer.yearly['2024'] || {};
    let specs = [
      ['상장',         peer.exchange || '—'],
      ['모회사',       peer.company_name || '—'],
      ['Tier',         'Tier 1 — Pure-play golf'],
      ['홀수',         profileNotes.holes ? (profileNotes.holes + 'H') : (isPipg ? '18H' : '36H (BSD + PIK)')],
      ['면적',         profileNotes.land_area_ha_total ? (profileNotes.land_area_ha_total + ' ha') : (isPipg ? '53 ha' : '156 ha (추정)')],
      ['FY24 매출',    C.fmtIDR(fy24.revenue)],
      ['FY24 순이익',  C.fmtIDR(fy24.net_profit)],
      ['FY24 종업원',  C.fmtNum(fy24.employees)],
    ];
    document.getElementById('hero-specs').innerHTML = specs.map(s =>
      '<dt>' + s[0] + '</dt><dd>' + s[1] + '</dd>').join('');

    /* ----- Risk flags ----- */
    const flags = riskFlags(peer, notes, isPipg);
    document.getElementById('hero-risk-flags').innerHTML = flags.map(f =>
      `<span class="risk-flag ${f.level}">${f.level.toUpperCase()} · ${f.label}</span>`).join('');
    document.getElementById('hero-risk-detail').innerHTML = flags.map(f => '• ' + f.detail).join('<br>');

    /* ----- 5y P&L chart ----- */
    const c = X.colours();
    const accent = isPipg ? c.pipg : c.dmig;
    Plotly.react(document.getElementById('pnl-chart'), [
      { x: YEARS, y: YEARS.map(y => (peer.yearly[y]||{}).revenue),          name: '매출',
        type: 'bar', marker: { color: accent } },
      { x: YEARS, y: YEARS.map(y => (peer.yearly[y]||{}).operating_profit), name: '영업이익',
        type: 'scatter', mode: 'lines+markers', yaxis: 'y2', line: { color: c.pos, width: 2 } },
      { x: YEARS, y: YEARS.map(y => (peer.yearly[y]||{}).net_profit),       name: '순이익',
        type: 'scatter', mode: 'lines+markers', yaxis: 'y2', line: { color: c.pos, width: 2, dash: 'dash' } },
      { x: YEARS, y: YEARS.map(y => (peer.yearly[y]||{}).ebitda),           name: 'EBITDA',
        type: 'scatter', mode: 'lines+markers', yaxis: 'y2', line: { color: c.dmig, width: 1.5, dash: 'dot' } },
    ], {
      paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)',
      font: { color: c.text },
      yaxis:  { tickformat: '.2s', gridcolor: c.border, title: { text: '매출 (IDR)', font: { size: 11 } } },
      yaxis2: { tickformat: '.2s', overlaying: 'y', side: 'right', title: { text: '이익 (IDR)', font: { size: 11 } } },
      xaxis:  { gridcolor: c.border },
      legend: { orientation: 'h', y: -0.2 },
      margin: { l: 70, r: 70, t: 20, b: 50 },
    }, { displayModeBar: false, responsive: true });

    /* PnL table */
    const rows = [
      ['매출',     YEARS.map(y => (peer.yearly[y]||{}).revenue)],
      ['영업이익', YEARS.map(y => (peer.yearly[y]||{}).operating_profit)],
      ['EBITDA',   YEARS.map(y => (peer.yearly[y]||{}).ebitda)],
      ['순이익',   YEARS.map(y => (peer.yearly[y]||{}).net_profit)],
      ['총자산',   YEARS.map(y => (peer.yearly[y]||{}).total_assets)],
      ['총부채',   YEARS.map(y => (peer.yearly[y]||{}).total_liabilities)],
      ['자기자본', YEARS.map(y => (peer.yearly[y]||{}).total_equity)],
    ];
    let table = '<table class="cmp-table"><thead><tr><th>항목</th>';
    YEARS.forEach(y => table += '<th>FY' + y.slice(-2) + '</th>');
    table += '</tr></thead><tbody>';
    rows.forEach(r => {
      table += '<tr><td>' + r[0] + '</td>';
      r[1].forEach(v => table += '<td>' + (v != null ? C.fmtIDR(v) : '<span class="na-cell">N/A</span>') + '</td>');
      table += '</tr>';
    });
    table += '</tbody></table>';
    document.getElementById('pnl-table').innerHTML = table;

    /* ----- Segment chart ----- */
    const segEl = document.getElementById('segment-chart');
    if (segEl) {
      const lines = isPipg
        ? (notes.revenue_note_27 && notes.revenue_note_27.lines)
        : (notes.revenue_note && notes.revenue_note.lines);
      if (lines && lines.length) {
        const segYears = isPipg ? ['FY2023','FY2024'] : ['FY2022','FY2023','FY2024'];
        const traces = lines.filter(l => segYears.some(y => l[y] != null)).map((l, i) => ({
          x: segYears,
          y: segYears.map(y => l[y]),
          type: 'bar',
          name: l.en_label || l.id_label,
          marker: { color: X.segmentColor(i) },
        }));
        Plotly.react(segEl, traces, {
          paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)',
          font: { color: c.text },
          barmode: 'stack',
          yaxis: { tickformat: '.2s', gridcolor: c.border, title: { text: 'IDR', font: { size: 11 } } },
          xaxis: { gridcolor: c.border },
          legend: { orientation: 'v', x: 1.02, y: 1, font: { size: 11 } },
          margin: { l: 70, r: 140, t: 20, b: 50 },
        }, { displayModeBar: false, responsive: true });
      } else {
        segEl.innerHTML = '<div style="padding:24px;color:var(--color-text-muted)">segment 데이터 없음</div>';
      }
    }

    /* ----- Land (PIPG only) ----- */
    if (isPipg) {
      const land = (data.pipgLong && data.pipgLong.land_rights) || {};
      const items = land.items || [];
      /* timeline scatter: x = expiry year, y = area */
      const parsed = items.map(it => {
        const m = (it.validity || '').match(/(\d{4})/);
        return {
          parcel: it.parcel,
          year: m ? parseInt(m[1], 10) : null,
          area_m2: it.area_m2,
          validity: it.validity,
        };
      }).filter(p => p.year);
      Plotly.react(document.getElementById('land-timeline'), [{
        x: parsed.map(p => p.year),
        y: parsed.map(p => p.area_m2),
        text: parsed.map(p => p.parcel),
        type: 'scatter', mode: 'markers+text',
        marker: { size: parsed.map(p => Math.max(10, Math.log10(p.area_m2 || 1) * 8)), color: accent },
        textposition: 'top center',
        textfont: { size: 10 },
        hovertemplate: '%{text}<br>만료: %{x}<br>면적: %{y:,} m²<extra></extra>',
      }], {
        paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)',
        font: { color: c.text },
        xaxis: { title: { text: '만료 연도' }, gridcolor: c.border, dtick: 5 },
        yaxis: { title: { text: '면적 (m²)' }, gridcolor: c.border, tickformat: ',' },
        margin: { l: 70, r: 20, t: 20, b: 60 },
        showlegend: false,
      }, { displayModeBar: false, responsive: true });
      /* Table */
      const sortedItems = items.slice().sort((a, b) => (a.validity || '').localeCompare(b.validity || ''));
      let t = '<table class="cmp-table"><thead><tr><th>Parcel</th><th>Validity</th><th>면적 (m²)</th></tr></thead><tbody>';
      sortedItems.forEach(it => { t += '<tr><td>' + it.parcel + '</td><td>' + (it.validity || '—') + '</td><td>' + C.fmtNum(it.area_m2) + '</td></tr>'; });
      t += '</tbody></table>';
      document.getElementById('land-table').innerHTML = t;

      /* Contracts table */
      const contracts = (data.pipgLong && data.pipgLong.contracts && data.pipgLong.contracts.agreements) || [];
      let ct = '<table class="cmp-table"><thead><tr><th>상대</th><th>계약 내용</th><th>수익 분류</th></tr></thead><tbody>';
      contracts.forEach(a => { ct += '<tr><td>' + a.counterparty + '</td><td>' + a.contract + '</td><td>' + a.revenue_classification + '</td></tr>'; });
      ct += '</tbody></table>';
      document.getElementById('contracts-table').innerHTML = ct;

      /* Long P&L */
      const pl = data.pipgLong && data.pipgLong.pnl;
      if (pl) {
        const years = pl.years;
        const rev = pl.lines['매출액'] || {};
        const op  = pl.lines['영업이익'] || {};
        const ni  = pl.lines['당기순이익'] || {};
        Plotly.react(document.getElementById('long-pnl'), [
          { x: years, y: years.map(y => rev[y]), name: '매출', type: 'scatter', mode: 'lines+markers', line: { color: c.pipg, width: 2.5 } },
          { x: years, y: years.map(y => op[y]),  name: '영업이익', type: 'scatter', mode: 'lines+markers', line: { color: c.pos, width: 2 } },
          { x: years, y: years.map(y => ni[y]),  name: '순이익',   type: 'scatter', mode: 'lines+markers', line: { color: c.dmig, width: 2 } },
        ], {
          paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)',
          font: { color: c.text },
          yaxis: { tickformat: ',', gridcolor: c.border, title: { text: 'IDR Million', font: { size: 11 } } },
          xaxis: { gridcolor: c.border, tickangle: -30 },
          legend: { orientation: 'h', y: -0.18 },
          margin: { l: 70, r: 20, t: 20, b: 50 },
        }, { displayModeBar: false, responsive: true });
      }
      /* Long traffic */
      const trafGolf = data.pipgLong && data.pipgLong.traffic_golf;
      if (trafGolf && trafGolf.length) {
        const valid = trafGolf.filter(r => r.total != null);
        Plotly.react(document.getElementById('long-traffic'), [
          { x: valid.map(r => r.year), y: valid.map(r => r.members),     name: '회원', type: 'bar', marker: { color: c.pipg } },
          { x: valid.map(r => r.year), y: valid.map(r => r.non_members), name: '비회원', type: 'bar', marker: { color: c.dmig } },
        ], {
          paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)',
          font: { color: c.text },
          barmode: 'stack',
          yaxis: { tickformat: ',', gridcolor: c.border, title: { text: '방문자 수', font: { size: 11 } } },
          xaxis: { gridcolor: c.border, dtick: 1 },
          legend: { orientation: 'h', y: -0.18 },
          margin: { l: 70, r: 20, t: 20, b: 50 },
        }, { displayModeBar: false, responsive: true });
      }
    } else {
      /* DMIG land/related party fallbacks */
      document.getElementById('land-info').innerHTML = `
        <table class="cmp-table">
          <tr><td>코스 위치</td><td>Tangerang (BSD City) + North Jakarta (PIK)</td></tr>
          <tr><td>총 홀수</td><td>36H (BSD 18 + PIK 18)</td></tr>
          <tr><td>면적</td><td>156 ha (추정)</td></tr>
          <tr><td>모회사</td><td>Sinarmas Land (BSDE group)</td></tr>
          <tr><td>parcel-level land rights</td><td><span class="na-label">AR 미공시</span> — 그룹 BS 통합</td></tr>
        </table>`;
      const rp = notes.related_party_note && notes.related_party_note.lines;
      if (rp && rp.length) {
        let t = '<table class="cmp-table"><thead><tr><th>항목</th><th>FY22</th><th>FY23</th><th>FY24</th></tr></thead><tbody>';
        rp.forEach(l => {
          t += '<tr><td>' + (l.en_label || l.id_label) + '</td>';
          ['FY2022','FY2023','FY2024'].forEach(y => {
            t += '<td>' + (l[y] != null ? C.fmtIDR(l[y]) : '<span class="na-cell">N/A</span>') + '</td>';
          });
          t += '</tr>';
        });
        t += '</tbody></table>';
        document.getElementById('related-party').innerHTML = t;
      } else {
        document.getElementById('related-party').innerHTML = '<div style="color:var(--color-text-muted)">related party 데이터 없음</div>';
      }
    }

    /* ----- Counterpart mini-bars (6 metrics) ----- */
    const myDer    = C.derive(peer.yearly);
    const otherDer = C.derive(other.yearly);
    const myFY24    = myDer.per_year['2024']    || {};
    const otherFY24 = otherDer.per_year['2024'] || {};
    const myCagr    = myDer.cagr || {};
    const otherCagr = otherDer.cagr || {};
    const myYear    = peer.yearly['2024']  || {};
    const otherYear = other.yearly['2024'] || {};
    const mini = [
      { id: 'mini-rev',     label: 'FY24 매출',    me: myYear.revenue,      other: otherYear.revenue,      fmt: 'IDR' },
      { id: 'mini-opm',     label: 'OP 마진',      me: myFY24.op_margin,    other: otherFY24.op_margin,    fmt: 'pct' },
      { id: 'mini-ebitdam', label: 'EBITDA 마진',  me: myFY24.ebitda_margin, other: otherFY24.ebitda_margin, fmt: 'pct' },
      { id: 'mini-roa',     label: 'ROA (avg)',    me: myFY24.roa_avg,      other: otherFY24.roa_avg,      fmt: 'pct' },
      { id: 'mini-roe',     label: 'ROE (avg)',    me: myFY24.roe_avg,      other: otherFY24.roe_avg,      fmt: 'pct' },
      { id: 'mini-rev-cagr',label: '매출 CAGR',    me: myCagr.revenue,      other: otherCagr.revenue,      fmt: 'pct' },
    ];
    const wrap = document.getElementById('counterpart-mini-bars');
    wrap.innerHTML = '';
    mini.forEach(m => {
      const div = document.createElement('div');
      div.id = m.id;
      div.className = 'chart';
      div.style.minHeight = '180px';
      wrap.appendChild(div);
      X.dualBar(div, {
        title: m.label,
        pipgValue: isPipg ? m.me  : m.other,
        dmigValue: isPipg ? m.other : m.me,
        pipgText:  C[m.fmt === 'pct' ? 'fmtPct' : 'fmtIDR'](isPipg ? m.me : m.other),
        dmigText:  C[m.fmt === 'pct' ? 'fmtPct' : 'fmtIDR'](isPipg ? m.other : m.me),
        tickFormat: m.fmt === 'pct' ? '.1%' : '.2s',
        format: m.fmt,
      });
    });

    /* ----- Footer ----- */
    document.getElementById('club-footer').innerHTML = `
      <div>· 5년 P&L: <code>data/company_financials_5y.json</code> (FY20-FY25)</div>
      <div>· AR Note (FY22-FY25): <code>peer-analysis/operations/data/${which}_notes.json</code></div>
      ${isPipg ? '<div>· 14년 long-history: <code>data/pipg_pptx_data.json</code> (PPT §1-§12)</div>' : ''}
    `;
  }

  function riskFlags(peer, notes, isPipg) {
    const flags = [];
    if (isPipg) {
      flags.push({ level: 'med', label: 'IDX 미상장', detail: 'OJK Tbk이지만 IDX 거래 X (POJK 3/2021) — 유동성·공시 빈도 제한' });
      flags.push({ level: 'med', label: 'HP No.119 만료 임박', detail: 'HP No. 119 (207,014 m² = 약 39%) 2027-03-05 만료 — 갱신 비용·승인 리스크' });
      flags.push({ level: 'low', label: '재무 우수', detail: 'FY24 ROA 12.5%, 부채비율 ~20%, 이자수익·유형자산처분이익 등 비영업 수익 비중 높아 마진 buffer' });
      flags.push({ level: 'med', label: '소유주 의존', detail: 'PT Metropolitan Kentjana Tbk (MKPI) 토지 일부 임차 + 21건 주요 계약 중 상당수 그룹사' });
    } else {
      flags.push({ level: 'low', label: 'IDX 상장 + 그룹사 안정', detail: 'Sinarmas Land (BSDE) 자회사 — 공시 충실, 회원권 수익 안정' });
      flags.push({ level: 'med', label: 'COGS 분해 얕음', detail: 'AR Note 24 COGS는 3개 segment(Golf/Restaurant/Recreation)로만 분리 — segment 수익성 정밀 평가 제약' });
      flags.push({ level: 'med', label: 'parcel-level 토지권 비공시', detail: '156 ha 추정 그룹 BS 통합 — 만료 임박 토지권 식별 불가' });
      flags.push({ level: 'low', label: 'FY24 매출 +3.3%, 마진 안정', detail: 'OP 마진 ~31%, ROA ~11.9%, 부채비율 ~27% — 안정적 운영' });
    }
    return flags;
  }

  global.PurePlayClubPage = { render };
})(window);
