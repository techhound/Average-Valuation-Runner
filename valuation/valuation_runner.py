"""
valuation/valuation_runner.py
==============================
Orchestrates all four valuation models for a single StockData record and
aggregates the results into a flat ``ValuationSummary``.

Typical usage::

    from data_sources import get_provider
    from valuation.valuation_runner import run_all

    provider = get_provider()
    data     = provider.fetch("MSFT")
    summary  = run_all(data, margin_of_safety=0.10)
    print(summary)
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from data_sources.base import StockData

from .models.dcf       import run_dcf,       DCFResult
from .models.graham    import run_graham,    GrahamResult
from .models.multiples import run_multiples, MultiplesResult
from .models.ddm       import run_ddm,       DDMResult


# ---------------------------------------------------------------------------
# Aggregated result
# ---------------------------------------------------------------------------

@dataclass
class ValuationSummary:
    """
    Flat record written to CSV/Parquet and consumed by Power BI.
    """
    # â”€â”€ Identity â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    ticker: str
    company_name: str
    sector: str
    industry: str
    data_source: str
    run_timestamp: datetime = field(default_factory=datetime.utcnow)

    # â”€â”€ Market â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    current_price: float = 0.0
    market_cap_m: float = 0.0
    shares_outstanding_m: float = 0.0

    # â”€â”€ Individual model outputs â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    dcf_value: Optional[float] = None
    graham_value: Optional[float] = None
    multiples_value: Optional[float] = None
    ddm_value: Optional[float] = None

    dcf_error: str = ""
    graham_error: str = ""
    multiples_error: str = ""
    ddm_error: str = ""

    # â”€â”€ Aggregate â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    intrinsic_value_avg: Optional[float] = None
    intrinsic_value_median: Optional[float] = None
    models_used: int = 0          # how many models produced a valid result

    # â”€â”€ Decision outputs â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    margin_of_safety: float = 0.10
    acceptable_buy_price: Optional[float] = None
    upside_to_intrinsic_pct: Optional[float] = None   # (iv_avg âˆ’ price) / price
    signal: str = ""              # "Buy", "Hold", or "Sell"

    # â”€â”€ Model assumptions (for auditability) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    dcf_growth_rate: Optional[float] = None
    dcf_discount_rate: Optional[float] = None
    dcf_terminal_rate: Optional[float] = None
    dcf_fcf_base_m: Optional[float] = None

    graham_eps: Optional[float] = None
    graham_growth_pct: Optional[float] = None
    graham_aaa_yield_pct: Optional[float] = None

    multiples_avg_pe: Optional[float] = None
    multiples_median_pe: Optional[float] = None
    multiples_n_comps: Optional[int] = None

    ddm_d0: Optional[float] = None
    ddm_growth_rate: Optional[float] = None
    ddm_discount_rate: Optional[float] = None

    def to_dict(self) -> dict:
        """Flat dict suitable for a DataFrame row."""
        return {
            "ticker":                self.ticker,
            "company_name":          self.company_name,
            "sector":                self.sector,
            "industry":              self.industry,
            "data_source":           self.data_source,
            "run_timestamp":         self.run_timestamp.isoformat(),
            "current_price":         self.current_price,
            "market_cap_m":          self.market_cap_m,
            "shares_outstanding_m":  self.shares_outstanding_m,
            "dcf_value":             self.dcf_value,
            "graham_value":          self.graham_value,
            "multiples_value":       self.multiples_value,
            "ddm_value":             self.ddm_value,
            "dcf_error":             self.dcf_error,
            "graham_error":          self.graham_error,
            "multiples_error":       self.multiples_error,
            "ddm_error":             self.ddm_error,
            "intrinsic_value_avg":   self.intrinsic_value_avg,
            "intrinsic_value_median":self.intrinsic_value_median,
            "models_used":           self.models_used,
            "margin_of_safety":      self.margin_of_safety,
            "acceptable_buy_price":  self.acceptable_buy_price,
            "upside_to_intrinsic_pct": self.upside_to_intrinsic_pct,
            "signal":                self.signal,
            # Assumptions
            "dcf_growth_rate":       self.dcf_growth_rate,
            "dcf_discount_rate":     self.dcf_discount_rate,
            "dcf_terminal_rate":     self.dcf_terminal_rate,
            "dcf_fcf_base_m":        self.dcf_fcf_base_m,
            "graham_eps":            self.graham_eps,
            "graham_growth_pct":     self.graham_growth_pct,
            "graham_aaa_yield_pct":  self.graham_aaa_yield_pct,
            "multiples_avg_pe":      self.multiples_avg_pe,
            "multiples_median_pe":   self.multiples_median_pe,
            "multiples_n_comps":     self.multiples_n_comps,
            "ddm_d0":                self.ddm_d0,
            "ddm_growth_rate":       self.ddm_growth_rate,
            "ddm_discount_rate":     self.ddm_discount_rate,
        }


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------
def run_all(
    data: StockData,
    margin_of_safety: float = 0.10,
    run_dcf_model: bool = True,
    run_graham_model: bool = True,
    run_multiples_model: bool = True,
    run_ddm_model: bool = True,
) -> ValuationSummary:
    """
    Run all enabled valuation models and return an aggregated summary.

    Parameters
    ----------
    data : StockData
        Canonical stock data.
    margin_of_safety : float
        Fraction below intrinsic value used to compute ``acceptable_buy_price``
        (default 0.10 = 10 %).
    run_* : bool
        Toggle individual models on/off.
    """
    summary = ValuationSummary(
        ticker=data.ticker,
        company_name=data.company_name,
        sector=data.sector,
        industry=data.industry,
        data_source=data.data_source,
        current_price=data.current_price,
        market_cap_m=data.market_cap,
        shares_outstanding_m=data.shares_outstanding,
        margin_of_safety=margin_of_safety,
    )

    valid_values: list[float] = []

    # â”€â”€ DCF â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    if run_dcf_model:
        dcf: DCFResult = run_dcf(data)
        if dcf.error:
            summary.dcf_error = dcf.error
        else:
            summary.dcf_value    = dcf.intrinsic_value
            summary.dcf_growth_rate   = dcf.growth_rate
            summary.dcf_discount_rate = dcf.discount_rate
            summary.dcf_terminal_rate = dcf.terminal_growth_rate
            summary.dcf_fcf_base_m    = dcf.fcf_base
            valid_values.append(dcf.intrinsic_value)

    # â”€â”€ Graham â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    if run_graham_model:
        graham: GrahamResult = run_graham(data)
        if graham.error:
            summary.graham_error = graham.error
        else:
            summary.graham_value      = graham.intrinsic_value
            summary.graham_eps        = graham.eps
            summary.graham_growth_pct = graham.growth_rate_pct
            summary.graham_aaa_yield_pct = graham.aaa_bond_yield_pct
            valid_values.append(graham.intrinsic_value)

    # â”€â”€ Multiples â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    if run_multiples_model:
        mult: MultiplesResult = run_multiples(data)
        if mult.error:
            summary.multiples_error = mult.error
        else:
            summary.multiples_value    = mult.intrinsic_value
            summary.multiples_avg_pe   = mult.avg_pe
            summary.multiples_median_pe = mult.median_pe
            summary.multiples_n_comps  = len(mult.comps)
            valid_values.append(mult.intrinsic_value)

    # â”€â”€ DDM â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    if run_ddm_model:
        ddm: DDMResult = run_ddm(data)
        if ddm.error:
            summary.ddm_error = ddm.error
        else:
            summary.ddm_value         = ddm.intrinsic_value
            summary.ddm_d0            = ddm.d0
            summary.ddm_growth_rate   = ddm.growth_rate
            summary.ddm_discount_rate = ddm.discount_rate
            valid_values.append(ddm.intrinsic_value)

    # â”€â”€ Aggregate â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    summary.models_used = len(valid_values)

    if valid_values:
        avg_iv    = statistics.mean(valid_values)
        median_iv = statistics.median(valid_values)

        summary.intrinsic_value_avg    = avg_iv
        summary.intrinsic_value_median = median_iv
        summary.acceptable_buy_price   = avg_iv * (1 - margin_of_safety)

        if data.current_price > 0:
            upside = (avg_iv - data.current_price) / data.current_price
            summary.upside_to_intrinsic_pct = upside
            if data.current_price <= summary.acceptable_buy_price:
                summary.signal = "Buy"
            elif data.current_price < avg_iv:
                summary.signal = "Hold"
            else:
                summary.signal = "Sell"

    return summary


# ---------------------------------------------------------------------------
# Batch helper
# ---------------------------------------------------------------------------

def run_batch(
    stock_data_list: list[StockData],
    margin_of_safety: float = 0.10,
    **kwargs,
) -> list[ValuationSummary]:
    """Run ``run_all`` over a list of StockData records."""
    results: list[ValuationSummary] = []
    for data in stock_data_list:
        print(f"  â†’ Valuing {data.ticker} â€¦")
        summary = run_all(data, margin_of_safety=margin_of_safety, **kwargs)
        results.append(summary)
    return results
