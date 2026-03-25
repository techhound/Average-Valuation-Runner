"""
valuation/models/dcf.py
========================
Discounted Cash Flow (DCF) valuation.

Formula
-------
    FCF_n  = FCF_0 Ã— (1 + g)^n                        for n = 1..10
    PV_n   = FCF_n / (1 + r)^n
    TV     = FCF_10 Ã— (1 + g_t) / (r - g_t)          (Gordon Growth terminal value)
    PV_TV  = TV / (1 + r)^10
    EV     = Î£ PV_n + PV_TV
    Equity = EV + Cash âˆ’ Debt
    Price  = Equity / Shares

where:
    g   = FCF growth rate for the explicit forecast period
    g_t = terminal (perpetuity) growth rate
    r   = CAPM discount rate  =  Rf + Î² Ã— ERP
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from data_sources.base import StockData


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class DCFResult:
    ticker: str
    model: str = "DCF"

    # Assumptions actually used
    fcf_base: float = 0.0           # starting FCF (most-recent year, millions)
    growth_rate: float = 0.0        # FCF growth rate applied
    avg_historical_growth: float = 0.0
    discount_rate: float = 0.0      # CAPM discount rate
    terminal_growth_rate: float = 0.0

    # Intermediate outputs
    sum_pv_fcf: float = 0.0         # PV of 10-year FCF stream, millions
    pv_terminal_value: float = 0.0  # PV of terminal value, millions
    enterprise_value: float = 0.0   # millions
    cash: float = 0.0               # millions
    debt: float = 0.0               # millions
    equity_value: float = 0.0       # millions
    shares_outstanding: float = 0.0 # millions

    # Final output
    intrinsic_value: float = 0.0    # per share
    current_price: float = 0.0
    upside_pct: float = 0.0         # (intrinsic âˆ’ price) / price

    error: str = ""


# ---------------------------------------------------------------------------
# Model function
# ---------------------------------------------------------------------------

def run_dcf(data: StockData, forecast_years: int = 10) -> DCFResult:
    """
    Run a DCF valuation on *data* and return a ``DCFResult``.

    Parameters
    ----------
    data : StockData
        Populated stock data record.
    forecast_years : int
        Number of years in the explicit FCF forecast (default 10).
    """
    res = DCFResult(ticker=data.ticker, current_price=data.current_price)

    # â”€â”€ Guard: need FCF history â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    if not data.fcf_history:
        res.error = "No FCF history available â€” DCF skipped"
        return res

    if data.shares_outstanding <= 0:
        res.error = "shares_outstanding â‰¤ 0 â€” cannot compute per-share value"
        return res

    # â”€â”€ Base FCF: most-recent year â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    sorted_fcf = sorted(data.fcf_history.items())  # [(year, fcf), â€¦]
    fcf_base = sorted_fcf[-1][1]

    if fcf_base <= 0:
        res.error = (
            f"Most-recent FCF is {fcf_base:.0f}M (â‰¤ 0) â€” "
            "DCF is not meaningful for loss-making FCF"
        )
        return res

    # â”€â”€ Growth rate â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    avg_growth = _historical_avg_growth(sorted_fcf)
    if data.fcf_growth_rate != 0.0:
        growth_rate = data.fcf_growth_rate          # explicit override
    else:
        growth_rate = avg_growth                    # use historical average

    # â”€â”€ Discount rate (CAPM) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    discount_rate = data.capm_discount_rate()

    # Safety: discount rate must exceed terminal growth rate
    if discount_rate <= data.terminal_growth_rate:
        discount_rate = data.terminal_growth_rate + 0.02

    # â”€â”€ 10-year FCF projection â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    sum_pv_fcf = 0.0
    fcf_t = fcf_base
    for t in range(1, forecast_years + 1):
        fcf_t *= (1 + growth_rate)
        pv = fcf_t / math.pow(1 + discount_rate, t)
        sum_pv_fcf += pv

    # â”€â”€ Terminal value â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    terminal_fcf = fcf_t * (1 + data.terminal_growth_rate)
    terminal_value = terminal_fcf / (discount_rate - data.terminal_growth_rate)
    pv_terminal = terminal_value / math.pow(1 + discount_rate, forecast_years)

    # â”€â”€ Enterprise â†’ equity â†’ per-share â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    enterprise_value = sum_pv_fcf + pv_terminal
    equity_value = enterprise_value + data.cash_and_equivalents - data.total_debt
    intrinsic_value = equity_value / data.shares_outstanding

    upside = (
        (intrinsic_value - data.current_price) / data.current_price
        if data.current_price > 0
        else 0.0
    )

    res.fcf_base = fcf_base
    res.growth_rate = growth_rate
    res.avg_historical_growth = avg_growth
    res.discount_rate = discount_rate
    res.terminal_growth_rate = data.terminal_growth_rate
    res.sum_pv_fcf = sum_pv_fcf
    res.pv_terminal_value = pv_terminal
    res.enterprise_value = enterprise_value
    res.cash = data.cash_and_equivalents
    res.debt = data.total_debt
    res.equity_value = equity_value
    res.shares_outstanding = data.shares_outstanding
    res.intrinsic_value = intrinsic_value
    res.upside_pct = upside
    return res


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _historical_avg_growth(sorted_fcf: list[tuple[int, float]]) -> float:
    """
    Compute the simple average of year-over-year FCF growth rates,
    excluding any year where the prior year's FCF was â‰¤ 0.
    
    Caps individual growth rates at 100% per year to prevent unrealistic
    projections (e.g., from data quality issues like future-year projections).
    """
    if len(sorted_fcf) < 2:
        return 0.10   # fallback: 10%

    rates = []
    for i in range(1, len(sorted_fcf)):
        prev = sorted_fcf[i - 1][1]
        curr = sorted_fcf[i][1]
        if prev > 0 and curr > 0:
            growth = (curr - prev) / prev
            # Cap unrealistic growth rates at 100% per year
            # (growth > 100% suggests data quality issues)
            if growth > 1.0:
                growth = 1.0
            rates.append(growth)

    if not rates:
        return 0.10
    
    avg = sum(rates) / len(rates)
    # Cap the average growth at 50% (still aggressive but more reasonable)
    return min(avg, 0.50)
