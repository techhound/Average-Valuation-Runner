"""
valuation/models/ddm.py
========================
Dividend Discount Model (DDM) — Gordon Growth Model variant.

Formula
-------
    P = D₁ / (r − g)

where:
    D₁ = D₀ × (1 + g)          next-period expected dividend
    D₀ = most-recent annual dividend
    g  = dividend growth rate   (engine-computed from history, or explicit override)
    r  = discount rate          (WACC from StockData, or CAPM if 0)

This model requires the stock to pay a dividend.  Stocks with no dividend
history produce an error result and are excluded from the Output average.
"""

from __future__ import annotations

from dataclasses import dataclass

from data_sources.base import StockData


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class DDMResult:
    ticker: str
    model: str = "DDM"

    d0: float = 0.0                 # most-recent annual dividend
    d1: float = 0.0                 # next-period expected dividend
    growth_rate: float = 0.0        # g
    avg_historical_growth: float = 0.0
    discount_rate: float = 0.0      # r

    intrinsic_value: float = 0.0
    current_price: float = 0.0
    upside_pct: float = 0.0

    error: str = ""


# ---------------------------------------------------------------------------
# Model function
# ---------------------------------------------------------------------------

def run_ddm(data: StockData) -> DDMResult:
    """
    Run the Gordon-Growth DDM on *data*.
    """
    res = DDMResult(ticker=data.ticker, current_price=data.current_price)

    if not data.dividend_history:
        res.error = "No dividend history — DDM requires dividend-paying stock"
        return res

    d0 = data.dividend_history[-1]
    if d0 <= 0:
        res.error = f"Most-recent dividend = {d0} (≤ 0) — DDM cannot run"
        return res

    # ── Growth rate ────────────────────────────────────────────────────
    avg_growth = _historical_avg_growth(data.dividend_history)
    if data.dividend_growth_rate != 0.0:
        growth_rate = data.dividend_growth_rate
    else:
        growth_rate = avg_growth

    # ── Discount rate ──────────────────────────────────────────────────
    if data.wacc != 0.0:
        discount_rate = data.wacc
    else:
        discount_rate = data.capm_discount_rate()

    # Gordon Growth requires r > g
    if discount_rate <= growth_rate:
        res.error = (
            f"Discount rate ({discount_rate:.3%}) ≤ growth rate ({growth_rate:.3%}) — "
            "Gordon Growth model is undefined"
        )
        return res

    d1 = d0 * (1 + growth_rate)
    intrinsic_value = d1 / (discount_rate - growth_rate)

    upside = (
        (intrinsic_value - data.current_price) / data.current_price
        if data.current_price > 0
        else 0.0
    )

    res.d0 = d0
    res.d1 = d1
    res.growth_rate = growth_rate
    res.avg_historical_growth = avg_growth
    res.discount_rate = discount_rate
    res.intrinsic_value = intrinsic_value
    res.upside_pct = upside
    return res


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _historical_avg_growth(div_history: list[float]) -> float:
    """
    Compute the simple average of year-over-year dividend growth rates.
    Skips any transition from zero (first dividend).
    """
    if len(div_history) < 2:
        return 0.05   # conservative fallback

    rates = []
    for i in range(1, len(div_history)):
        prev = div_history[i - 1]
        curr = div_history[i]
        if prev > 0:
            rates.append((curr - prev) / prev)

    return sum(rates) / len(rates) if rates else 0.05