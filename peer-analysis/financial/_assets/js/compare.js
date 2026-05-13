/* Comparison derivers — pure functions, no DOM, no Plotly.
   All input is the normalised peer.yearly schema:
     { '2020': { revenue, operating_profit, net_profit, ebitda,
                 total_assets, total_liabilities, total_equity,
                 eps, dividend_per_share, employees, sources } , ... }
*/
(function (global) {
  'use strict';

  const FY_RANGE = ['2020','2021','2022','2023','2024','2025'];

  function num(v) { return (typeof v === 'number' && isFinite(v)) ? v : null; }
  function safeDiv(a, b) {
    a = num(a); b = num(b);
    if (a === null || b === null || b === 0) return null;
    return a / b;
  }

  /* Margin family — operating, gross, ebitda, net */
  function margins(y) {
    const r = num(y && y.revenue);
    return {
      op_margin:     safeDiv(y && y.operating_profit, r),
      ebitda_margin: safeDiv(y && y.ebitda,           r),
      ni_margin:     safeDiv(y && y.net_profit,       r),
      /* gross margin requires COGS which is not in 5y. left null (use notes) */
      gross_margin:  null,
    };
  }

  /* Return on assets/equity. Uses end-of-period balance for simplicity;
     averaged variant added when prior year present. */
  function returns(y, yPrev) {
    const a   = num(y && y.total_assets);
    const e   = num(y && y.total_equity);
    const aPrev = num(yPrev && yPrev.total_assets);
    const ePrev = num(yPrev && yPrev.total_equity);
    const avgA  = (a !== null && aPrev !== null) ? (a + aPrev) / 2 : a;
    const avgE  = (e !== null && ePrev !== null) ? (e + ePrev) / 2 : e;
    return {
      roa_avg: safeDiv(y && y.net_profit, avgA),
      roe_avg: safeDiv(y && y.net_profit, avgE),
      roa_end: safeDiv(y && y.net_profit, a),
      roe_end: safeDiv(y && y.net_profit, e),
    };
  }

  /* Capital structure */
  function structure(y) {
    const a = num(y && y.total_assets);
    return {
      debt_ratio:    safeDiv(y && y.total_liabilities, a),
      equity_ratio:  safeDiv(y && y.total_equity,      a),
    };
  }

  /* CAGR between two years; years must both be present */
  function cagr(yStart, yEnd, nPeriods) {
    yStart = num(yStart); yEnd = num(yEnd);
    if (yStart === null || yEnd === null || yStart <= 0 || nPeriods <= 0) return null;
    return Math.pow(yEnd / yStart, 1 / nPeriods) - 1;
  }

  /* YoY growth array. Returns map year -> yoy */
  function yoyMap(yearly, field) {
    const years = Object.keys(yearly).sort();
    const out = {};
    for (let i = 1; i < years.length; i++) {
      const prev = num(yearly[years[i-1]] && yearly[years[i-1]][field]);
      const curr = num(yearly[years[i]]    && yearly[years[i]][field]);
      if (prev !== null && curr !== null && prev !== 0) {
        out[years[i]] = (curr - prev) / prev;
      } else {
        out[years[i]] = null;
      }
    }
    return out;
  }

  /* Compute full derived bundle for one peer's yearly */
  function derive(yearly) {
    const years = Object.keys(yearly).sort();
    const result = {
      years,
      per_year: {},
    };
    years.forEach((y, i) => {
      const cur = yearly[y];
      const prev = i > 0 ? yearly[years[i-1]] : null;
      result.per_year[y] = Object.assign({},
        margins(cur),
        returns(cur, prev),
        structure(cur)
      );
    });
    /* 5-year (or 6-year) averages, computed only when full window present */
    const fullYears = years.filter(y => yearly[y] && yearly[y].revenue != null);
    if (fullYears.length >= 2) {
      const start = fullYears[0], end = fullYears[fullYears.length - 1];
      const n = fullYears.length - 1;
      result.cagr = {
        revenue:        cagr(yearly[start].revenue,      yearly[end].revenue,      n),
        total_assets:   cagr(yearly[start].total_assets, yearly[end].total_assets, n),
        net_profit:     cagr(yearly[start].net_profit,   yearly[end].net_profit,   n),
        operating_profit: cagr(yearly[start].operating_profit, yearly[end].operating_profit, n),
        period: start + '–' + end + ' (' + n + 'y)',
      };
    }
    /* Margin averages */
    const marginAvg = (field) => {
      const vals = years.map(y => result.per_year[y][field]).filter(v => v != null);
      if (!vals.length) return null;
      return vals.reduce((a,b) => a+b, 0) / vals.length;
    };
    result.avg = {
      op_margin:     marginAvg('op_margin'),
      ebitda_margin: marginAvg('ebitda_margin'),
      ni_margin:     marginAvg('ni_margin'),
      roa_avg:       marginAvg('roa_avg'),
      roe_avg:       marginAvg('roe_avg'),
      debt_ratio:    marginAvg('debt_ratio'),
      equity_ratio:  marginAvg('equity_ratio'),
    };
    return result;
  }

  /* OPEX label mapping table — maps PIPG (Indonesian/English mixed) labels to
     a normalised English category, with DMIG's English label as cross-reference.
     Source: pipg_notes.opex_note_29 vs dmig_notes.opex_note (FY22-FY24).
     Where a category exists in one but not the other, the other side is null. */
  const OPEX_MAP = [
    { norm: 'Salaries & wages',        pipg: 'Salary and allowances',        dmig: 'Salaries and wages' },
    { norm: 'Depreciation',            pipg: 'Depreciation (Notes 9, 13)',   dmig: 'Depreciation' },
    { norm: 'Land & building tax',     pipg: 'Tax and legal',                dmig: 'Land and building tax' },
    { norm: 'Repair & maintenance',    pipg: 'Repair and maintenance',       dmig: 'Repair and maintenance' },
    { norm: 'Electricity & water',     pipg: 'Electricity and water',        dmig: 'Electricity and water' },
    { norm: 'Amortization',            pipg: 'Amortization of deferred charge (Note 12)', dmig: 'Amortization' },
    { norm: 'Employee benefits',       pipg: 'Provision for employee benefit (Note 22)',  dmig: 'Employee benefits' },
    { norm: 'Supplies / office equip', pipg: 'Supplies and office equipment',dmig: null },
    { norm: 'Donations',               pipg: 'Donation and contribution',    dmig: null },
    { norm: 'Insurance',               pipg: 'Insurance',                    dmig: 'Insurance' },
    { norm: 'Training',                pipg: 'Training expenses',            dmig: null },
    { norm: 'Audit & consulting',      pipg: 'Audit and consultant',         dmig: 'Professional fee' },
    { norm: 'Travel & transport',      pipg: 'Transportation and travels',   dmig: 'Transportation' },
    { norm: 'Receivables impairment',  pipg: 'Allowance for impairment of receivable (Note 6)', dmig: null },
    { norm: 'Telecom & postage',       pipg: 'Post, telephone and fax',      dmig: 'Telephone and telex' },
    { norm: 'Inventory write-off',     pipg: 'Write-off inventory',          dmig: null },
    { norm: 'Stationery & printing',   pipg: null,                           dmig: 'Stationery and printing' },
    { norm: 'Cleaning service',        pipg: null,                           dmig: 'Cleaning service' },
    { norm: 'Bank administration',     pipg: null,                           dmig: 'Bank administration' },
    { norm: 'Tax & licensing',         pipg: null,                           dmig: 'Tax and licensing' },
    { norm: 'Employee welfare',        pipg: null,                           dmig: 'Employee welfare' },
    { norm: 'Inventory allowance',     pipg: 'Allowance of inventories',     dmig: null },
    { norm: 'Other (<100m each)',      pipg: null,                           dmig: 'Others (each below Rp100m)' },
  ];

  /* Segment label mapping — PIPG revenue_note_27 vs DMIG revenue_note */
  const SEGMENT_MAP = [
    { norm: 'Golf course',         pipg: 'Golf course',         dmig: 'Golf course' },
    { norm: 'Restaurant',          pipg: 'Restaurant',          dmig: 'Restaurant' },
    { norm: 'Membership',          pipg: 'Membership and registration fees', dmig: 'Membership dues' },
    { norm: 'Driving range',       pipg: 'Driving range',       dmig: null },
    { norm: 'Rent',                pipg: 'Rent (Note 10)',      dmig: 'Room rental' },
    { norm: 'Golf cart',           pipg: 'Golf cart',           dmig: null },
    { norm: 'Branding / sponsor',  pipg: 'Branding',            dmig: 'Sponsorship' },
    { norm: 'Sharing revenue',     pipg: 'Sharing revenue',     dmig: null },
    { norm: 'Academy',             pipg: 'Academy golf',        dmig: null },
    { norm: 'Gym',                 pipg: 'Gym',                 dmig: null },
    { norm: 'Tournament',          pipg: "Indonesia's open sponsor", dmig: null },
    { norm: 'Recreation',          pipg: null,                  dmig: 'Recreation' },
    { norm: 'Others',              pipg: null,                  dmig: 'Others' },
  ];

  /* Build a normalised segment-revenue table for one peer's revenue_note.
     `lines` is the list of {id_label, en_label, FY2022, ...} objects.
     Returns: { years: ['FY2022', ...], rows: [ { norm, values:{year:val} } ] }. */
  function normaliseSegments(lines, sideKey /* 'pipg' or 'dmig' */) {
    const map = SEGMENT_MAP;
    const out = [];
    map.forEach(m => {
      const lab = m[sideKey];
      if (!lab) { out.push({ norm: m.norm, values: {} }); return; }
      const row = (lines || []).find(l => (l.en_label === lab) || (l.id_label === lab));
      if (!row) { out.push({ norm: m.norm, values: {} }); return; }
      const vals = {};
      Object.keys(row).forEach(k => {
        if (/^FY20\d{2}$/.test(k)) vals[k] = row[k];
      });
      out.push({ norm: m.norm, values: vals });
    });
    return out;
  }

  function normaliseOpex(lines, sideKey) {
    const map = OPEX_MAP;
    const out = [];
    map.forEach(m => {
      const lab = m[sideKey];
      if (!lab) { out.push({ norm: m.norm, values: {} }); return; }
      const row = (lines || []).find(l => (l.en_label === lab) || (l.id_label === lab));
      if (!row) { out.push({ norm: m.norm, values: {} }); return; }
      const vals = {};
      Object.keys(row).forEach(k => {
        if (/^FY20\d{2}$/.test(k)) vals[k] = row[k];
      });
      out.push({ norm: m.norm, values: vals });
    });
    return out;
  }

  /* Number formatting helpers used by both panels and charts. */
  function fmtIDR(v, opts) {
    if (v === null || v === undefined || !isFinite(v)) return 'N/A';
    opts = opts || {};
    const abs = Math.abs(v);
    const sign = v < 0 ? '-' : '';
    if (abs >= 1e12) return sign + 'Rp ' + (abs / 1e12).toFixed(opts.precision || 1) + 'T';
    if (abs >= 1e9)  return sign + 'Rp ' + (abs / 1e9).toFixed(opts.precision || 1) + 'B';
    if (abs >= 1e6)  return sign + 'Rp ' + (abs / 1e6).toFixed(opts.precision || 1) + 'M';
    return sign + 'Rp ' + abs.toLocaleString();
  }
  function fmtPct(v, digits) {
    if (v === null || v === undefined || !isFinite(v)) return 'N/A';
    return (v * 100).toFixed(digits == null ? 1 : digits) + '%';
  }
  function fmtNum(v, digits) {
    if (v === null || v === undefined || !isFinite(v)) return 'N/A';
    return v.toLocaleString(undefined, { maximumFractionDigits: digits == null ? 0 : digits });
  }

  global.PurePlayCompare = {
    derive, margins, returns, structure, cagr, yoyMap,
    normaliseSegments, normaliseOpex,
    fmtIDR, fmtPct, fmtNum,
    FY_RANGE, OPEX_MAP, SEGMENT_MAP,
  };
})(window);
