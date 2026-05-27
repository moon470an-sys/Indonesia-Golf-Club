"""IDX XBRL 인스턴스 파서.

IDX e-laporan zip은 instance.xbrl + Taxonomy.xsd 두 파일로 구성된다.
이 모듈은 zip(or instance.xbrl 경로)을 받아 표준 재무 필드를 dict로 추출한다.

추출 필드는 idx-cor / idx-dei 네임스페이스 기반이며, contextRef로
회계연도(Current / Prior)를 구분한다.

사용 예:
    from parse_xbrl import parse_xbrl_zip
    rec = parse_xbrl_zip('tmp_xbrl/BSDE_2024.zip')
    # → {'ticker': 'BSDE', 'years': {'2024': {...}, '2023': {...}}}
"""
from __future__ import annotations

import io
import os
import zipfile
from typing import Optional

from lxml import etree

NS_XBRLI = "http://www.xbrl.org/2003/instance"
NS_COR = "http://www.idx.co.id/xbrl/taxonomy/2020-01-01/cor"
NS_DEI = "http://www.idx.co.id/xbrl/taxonomy/2020-01-01/dei"

# 추출할 idx-cor 필드 (P&L / BS / CF / EPS)
COR_FIELDS = [
    "SalesAndRevenue",
    "CostOfSalesAndRevenue",
    "GrossProfit",
    "GeneralAndAdministrativeExpenses",
    "SellingExpenses",
    "OtherIncome",
    "OtherExpenses",
    "FinanceIncome",
    "ProfitLossBeforeIncomeTax",
    "ProfitLoss",
    "ProfitLossAttributableToParentEntity",
    "ProfitLossAttributableToNonControllingInterests",
    "ComprehensiveIncome",
    "Assets",
    "CurrentAssets",
    "NonCurrentAssets",
    "Liabilities",
    "CurrentLiabilities",
    "NonCurrentLiabilities",
    "Equity",
    "EquityAttributableToEquityOwnersOfParentEntity",
    "BasicEarningsLossPerShareFromContinuingOperations",
    "DilutedEarningsLossPerShareFromContinuingOperations",
    "CashAndCashEquivalents",
    "NetCashFlowsReceivedFromUsedInOperatingActivities",
    "NetCashFlowsReceivedFromUsedInInvestingActivities",
    "NetCashFlowsReceivedFromUsedInFinancingActivities",
]

# 추출할 idx-dei 메타 필드
DEI_FIELDS = [
    "EntityName",
    "EntityCode",
    "EntityIdentificationNumber",
    "DescriptionOfPresentationCurrency",
    "DescriptionOfFunctionalCurrency",
    "CurrentPeriodEndDate",
    "EndDateOfCurrentReportingPeriod",
    "EndDateOfPriorReportingPeriod",
]

# context id → (period_type, year_key)
# year_key는 회계연도 (예: '2024')로 매핑된다.
_CONTEXT_PERIOD_TYPES = {
    "CurrentYearInstant": ("instant", "current"),
    "PriorEndYearInstant": ("instant", "prior"),
    "PriorYearInstant": ("instant", "prior"),
    "CurrentYearDuration": ("duration", "current"),
    "PriorYearDuration": ("duration", "prior"),
}


def _to_number(text: Optional[str]) -> Optional[float]:
    if text is None:
        return None
    text = text.strip()
    if not text:
        return None
    try:
        if "." in text:
            return float(text)
        return int(text)
    except ValueError:
        return None


def _read_instance_bytes(path: str) -> bytes:
    """zip이면 안의 instance.xbrl을, .xbrl이면 그대로 읽음."""
    if path.lower().endswith(".zip"):
        with zipfile.ZipFile(path) as z:
            # 가장 큰 .xbrl 파일이 instance.xbrl
            candidates = [n for n in z.namelist() if n.lower().endswith(".xbrl")]
            if not candidates:
                raise ValueError(f"no .xbrl inside {path}")
            target = max(candidates, key=lambda n: z.getinfo(n).file_size)
            return z.read(target)
    with open(path, "rb") as f:
        return f.read()


def parse_xbrl(path: str) -> dict:
    """IDX XBRL 인스턴스를 파싱하여 구조화된 dict를 반환.

    반환 dict:
      {
        'ticker': 'BSDE',
        'entity_name': 'PT ...',
        'currency': 'Rupiah / IDR',
        'period_end': '2024-12-31',
        'prior_period_end': '2023-12-31',
        'years': {
          '2024': { 'revenue': 13796572148837, ..., 'period_end': '2024-12-31' },
          '2023': { ... }
        },
        'source_file': '<basename>',
      }
    """
    data = _read_instance_bytes(path)
    root = etree.fromstring(data)

    # contexts: cid → (kind, start, end_or_instant)
    contexts: dict[str, tuple] = {}
    for ctx in root.iter(f"{{{NS_XBRLI}}}context"):
        cid = ctx.get("id")
        period = ctx.find(f"{{{NS_XBRLI}}}period")
        if period is None:
            continue
        # context with scenario/dimension은 segment 분해라 제외
        scenario = ctx.find(f"{{{NS_XBRLI}}}scenario")
        if scenario is not None and len(scenario) > 0:
            continue
        instant = period.find(f"{{{NS_XBRLI}}}instant")
        if instant is not None:
            contexts[cid] = ("instant", None, instant.text)
        else:
            s = period.find(f"{{{NS_XBRLI}}}startDate")
            e = period.find(f"{{{NS_XBRLI}}}endDate")
            if s is not None and e is not None:
                contexts[cid] = ("duration", s.text, e.text)

    # DEI 메타
    dei: dict[str, Optional[str]] = {}
    cor_facts: dict[str, dict[str, Optional[float]]] = {}
    # key: field name, value: {context_ref: numeric_value}

    for elem in root:
        if not isinstance(elem.tag, str) or "}" not in elem.tag:
            continue
        ns, local = elem.tag[1:].split("}", 1)
        if ns == NS_DEI and local in DEI_FIELDS:
            dei[local] = (elem.text or "").strip() if elem.text else None
        elif ns == NS_COR and local in COR_FIELDS:
            ctx_ref = elem.get("contextRef")
            if ctx_ref not in _CONTEXT_PERIOD_TYPES:
                continue
            cor_facts.setdefault(local, {})[ctx_ref] = _to_number(elem.text)

    # period_end → year string
    cur_end = (
        dei.get("CurrentPeriodEndDate")
        or dei.get("EndDateOfCurrentReportingPeriod")
    )
    prior_end = dei.get("EndDateOfPriorReportingPeriod")
    if not cur_end:
        # fallback to context
        c = contexts.get("CurrentYearInstant") or contexts.get("CurrentYearDuration")
        cur_end = c[2] if c else None
    if not prior_end:
        c = contexts.get("PriorEndYearInstant") or contexts.get("PriorYearInstant") or contexts.get("PriorYearDuration")
        prior_end = c[2] if c else None

    cur_year = cur_end[:4] if cur_end else None
    prior_year = prior_end[:4] if prior_end else None

    years: dict[str, dict] = {}
    if cur_year:
        years[cur_year] = {"period_end": cur_end}
    if prior_year:
        years[prior_year] = {"period_end": prior_end}

    # 각 필드를 current/prior 연도에 분배
    for field, by_ctx in cor_facts.items():
        for ctx_ref, value in by_ctx.items():
            kind, year_key = _CONTEXT_PERIOD_TYPES[ctx_ref]
            year = cur_year if year_key == "current" else prior_year
            if not year:
                continue
            years[year][_field_to_key(field)] = value

    ticker = dei.get("EntityCode")
    return {
        "ticker": ticker,
        "entity_name": dei.get("EntityName"),
        "currency": dei.get("DescriptionOfPresentationCurrency")
        or dei.get("DescriptionOfFunctionalCurrency"),
        "period_end": cur_end,
        "prior_period_end": prior_end,
        "years": years,
        "source_file": os.path.basename(path),
    }


# camelCase → snake_case 간단 키 매핑 (JSON 친화)
_KEY_MAP = {
    "SalesAndRevenue": "revenue",
    "CostOfSalesAndRevenue": "cost_of_revenue",
    "GrossProfit": "gross_profit",
    "GeneralAndAdministrativeExpenses": "ga_expenses",
    "SellingExpenses": "selling_expenses",
    "OtherIncome": "other_income",
    "OtherExpenses": "other_expenses",
    "FinanceIncome": "finance_income",
    "ProfitLossBeforeIncomeTax": "profit_before_tax",
    "ProfitLoss": "net_profit_total",
    "ProfitLossAttributableToParentEntity": "net_profit",
    "ProfitLossAttributableToNonControllingInterests": "net_profit_nci",
    "ComprehensiveIncome": "comprehensive_income",
    "Assets": "total_assets",
    "CurrentAssets": "current_assets",
    "NonCurrentAssets": "noncurrent_assets",
    "Liabilities": "total_liabilities",
    "CurrentLiabilities": "current_liabilities",
    "NonCurrentLiabilities": "noncurrent_liabilities",
    "Equity": "total_equity",
    "EquityAttributableToEquityOwnersOfParentEntity": "total_equity_parent",
    "BasicEarningsLossPerShareFromContinuingOperations": "eps_basic",
    "DilutedEarningsLossPerShareFromContinuingOperations": "eps_diluted",
    "CashAndCashEquivalents": "cash_and_equivalents",
    "NetCashFlowsReceivedFromUsedInOperatingActivities": "cfo",
    "NetCashFlowsReceivedFromUsedInInvestingActivities": "cfi",
    "NetCashFlowsReceivedFromUsedInFinancingActivities": "cff",
}


def _field_to_key(field: str) -> str:
    return _KEY_MAP.get(field, field)


def parse_xbrl_zip(path: str) -> dict:
    """parse_xbrl의 별칭 (zip/xbrl 둘 다 받음)."""
    return parse_xbrl(path)


if __name__ == "__main__":
    import json
    import sys

    target = sys.argv[1] if len(sys.argv) > 1 else "../../tmp_xbrl/BSDE_2024.zip"
    rec = parse_xbrl(target)
    print(json.dumps(rec, ensure_ascii=False, indent=2))
