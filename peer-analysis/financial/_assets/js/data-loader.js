/* Data loader for Pure-play Comparison Site.
   Single-call entry: window.PurePlayData.load() -> Promise<{ pipg, dmig, peers, meta, pipgLong }>
*/
(function (global) {
  'use strict';

  /* Relative paths from peer-analysis/financial/index.html to /site root */
  const ROOT = '../../';
  const SOURCES = {
    companies:  ROOT + 'data/company_financials_5y.json',
    courses:    ROOT + 'data/golf_courses.json',
    pipgNotes:  ROOT + 'peer-analysis/operations/data/pipg_notes.json',
    dmigNotes:  ROOT + 'peer-analysis/operations/data/dmig_notes.json',
    pipgLong:   ROOT + 'data/pipg_pptx_data.json',
    peersMeta:  ROOT + 'peer-analysis/operations/data/_clubs_meta.json',
    peerOps:    ROOT + 'peer-analysis/operations/data/peer_operations.json',
    peersSum:   ROOT + 'peer-analysis/operations/data/peers_summary.json',
  };

  function fetchJSON(url) {
    return fetch(url, { cache: 'no-cache' }).then(r => {
      if (!r.ok) throw new Error('Failed to fetch ' + url + ' (' + r.status + ')');
      return r.json();
    });
  }

  /* Pick the company record for one ticker out of companies[] list. */
  function pickCompany(financials, ticker) {
    const list = financials && financials.companies;
    if (!Array.isArray(list)) return null;
    return list.find(c => c.ticker === ticker) || null;
  }

  /* Build a normalised peer object combining the 5-year company-level data
     with the AR-Note breakdown (FY22-25). Both shapes preserved. */
  function buildPeer(ticker, companies, notes, meta) {
    const c = pickCompany(companies, ticker) || { ticker };
    return {
      ticker,
      profile: meta && meta[ticker] ? meta[ticker] : {},
      yearly:  c.yearly || {},
      currency: c.currency || 'IDR',
      company_name: c.company_name,
      exchange: c.exchange,
      summary_note: c.summary_note,
      notes: notes || {},
    };
  }

  /* Build peer-context list (13 peers, raw company yearly + meta). */
  function buildPeerContext(companies, meta) {
    const tickers = ['DMIG','PIPG','GOLF','MDLN','KIJA','SMDM','KPIG','SMRA','BSDE','CTRA','ELTY','LPKR','PWON'];
    return tickers.map(t => ({
      ticker: t,
      meta:   meta && meta[t]    ? meta[t]    : null,
      yearly: (pickCompany(companies, t) || {}).yearly || {},
    }));
  }

  function load() {
    const tasks = [
      fetchJSON(SOURCES.companies),
      fetchJSON(SOURCES.pipgNotes).catch(() => ({})),
      fetchJSON(SOURCES.dmigNotes).catch(() => ({})),
      fetchJSON(SOURCES.pipgLong).catch(() => ({})),
      fetchJSON(SOURCES.peersMeta).catch(() => ({})),
      fetchJSON(SOURCES.peerOps).catch(() => ({})),
    ];

    return Promise.all(tasks).then(([companies, pipgNotes, dmigNotes, pipgLong, peersMeta, peerOps]) => {
      return {
        meta: {
          companies_metadata: companies.metadata || {},
          loaded_at: new Date().toISOString(),
          sources: SOURCES,
        },
        pipg: buildPeer('PIPG', companies, pipgNotes, peersMeta),
        dmig: buildPeer('DMIG', companies, dmigNotes, peersMeta),
        pipgLong: pipgLong,
        peers: buildPeerContext(companies, peersMeta),
        peerOps: peerOps,
      };
    });
  }

  global.PurePlayData = { load, SOURCES };
})(window);
