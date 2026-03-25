"""
valuation/models/multiples.py
==============================
Multiples (comparable-company) valuation.

Method
------
1.  Collect a list of comparable companies (from ``StockData.comparables``).
2.  Compute each comp's trailing P/E ratio  =  price / EPS.
3.  Calculate the **average** and **median** P/E across the comp set.
4.  Apply both to the target company's EPS to arrive at two implied prices.
5.  Report the average-based price as the primary ``intrinsic_value``.

If no comparables are provided the model cannot produce a result.  In that
case set a meaningful error message and leave ``intrinsic_value`` at 0.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field

from data_sources.base import ComparableCompany, StockData


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class CompResult:
    """Intermediate per-comparable result."""
    ticker: str
    company_name: str
    stock_price: float
    eps: float
    pe_ratio: float


@dataclass
class MultiplesResult:
    ticker: str
    model: str = "Multiples"

    target_eps: float = 0.0

    comps: list = field(default_factory=list)  # list[CompResult]
    avg_pe: float = 0.0
    median_pe: float = 0.0

    # avg-P/E based implied price  →  primary output
    implied_price_avg: float = 0.0
    # median-P/E based implied price
    implied_price_median: float = 0.0

    intrinsic_value: float = 0.0   # = implied_price_avg
    current_price: float = 0.0
    upside_pct: float = 0.0

    error: str = ""


# ---------------------------------------------------------------------------
# Model function
# ---------------------------------------------------------------------------

def run_multiples(data: StockData) -> MultiplesResult:
    """
    Run the P/E multiples valuation on *data*.
    """
    res = MultiplesResult(ticker=data.ticker, current_price=data.current_price)

    if data.eps_ttm == 0:
        res.error = "eps_ttm = 0 — Multiples valuation requires non-zero EPS"
        return res

    if not data.comparables:
        res.error = (
            "No comparable companies supplied — Multiples valuation skipped.  "
            "Populate StockData.comparables (e.g. via the Wisesheets template "
            "or settings.py) to enable this model."
        )
        return res

    # ── Build comp P/E list ────────────────────────────────────────────
    comp_results: list[CompResult] = []
    pe_list: list[float] = []

    for comp in data.comparables:
        if not isinstance(comp, ComparableCompany):
            continue
        if comp.eps is None or comp.eps == 0 or comp.stock_price <= 0:
            continue
        pe = comp.stock_price / comp.eps
        if pe <= 0:
            continue
        comp_results.append(CompResult(
            ticker=comp.ticker,
            company_name=comp.company_name,
            stock_price=comp.stock_price,
            eps=comp.eps,
            pe_ratio=pe,
        ))
        pe_list.append(pe)

    if not pe_list:
        res.error = "All comparables have invalid (≤ 0) EPS or price — cannot compute P/E"
        return res

    avg_pe    = statistics.mean(pe_list)
    median_pe = statistics.median(pe_list)

    implied_avg    = avg_pe    * data.eps_ttm
    implied_median = median_pe * data.eps_ttm

    upside = (
        (implied_avg - data.current_price) / data.current_price
        if data.current_price > 0
        else 0.0
    )

    res.target_eps         = data.eps_ttm
    res.comps              = comp_results
    res.avg_pe             = avg_pe
    res.median_pe          = median_pe
    res.implied_price_avg  = implied_avg
    res.implied_price_median = implied_median
    res.intrinsic_value    = implied_avg   # primary metric
    res.upside_pct         = upside
    return res