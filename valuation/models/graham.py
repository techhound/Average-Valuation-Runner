"""
valuation/models/graham.py
============================
Benjamin Graham's valuation formulas.

Original formula (1962)
-----------------------
    V* = EPS × (8.5 + 2g)

where g is the expected 5-year EPS growth rate in percentage points.

Revised formula (1974)  ← model default
----------------------------------------
    V* = EPS × (8.5 + 2g) × 4.4 / Y

where:
    4.4  = average AAA bond yield when Graham devised the formula
    Y    = current AAA bond yield (decimal × 100 = %)
    g    = 5-year projected EPS growth rate (percent, NOT decimal)

The revised formula adjusts the valuation for changes in the interest-rate
environment.  Higher rates → lower intrinsic value, and vice versa.
"""

from __future__ import annotations

from dataclasses import dataclass

from data_sources.base import StockData


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class GrahamResult:
    ticker: str
    model: str = "Graham"

    eps: float = 0.0
    growth_rate_pct: float = 0.0        # g as a percentage (e.g. 16.5)
    aaa_bond_yield_pct: float = 0.0     # Y as a percentage (e.g. 5.36)

    # Original formula: V = EPS × (8.5 + 2g)
    original_intrinsic_value: float = 0.0
    # Revised formula:  V = EPS × (8.5 + 2g) × 4.4/Y
    revised_intrinsic_value: float = 0.0

    # The number reported in the Output sheet (revised, default)
    intrinsic_value: float = 0.0
    current_price: float = 0.0
    upside_pct: float = 0.0

    error: str = ""


# ---------------------------------------------------------------------------
# Model function
# ---------------------------------------------------------------------------

AAA_CONSTANT = 4.4   # Graham's historical AAA yield anchor

def run_graham(data: StockData) -> GrahamResult:
    """
    Run both Graham formulas on *data*.

    The ``intrinsic_value`` field of the result uses the **revised** formula
    (consistent with the Excel model) to account for the current rate
    environment.
    """
    res = GrahamResult(ticker=data.ticker, current_price=data.current_price)

    if data.eps_ttm == 0:
        res.error = "eps_ttm = 0 — Graham requires positive EPS"
        return res

    # Graham growth rate is expressed as a percentage (e.g. 16.5 for 16.5%)
    # eps_growth_rate in StockData is a decimal — convert
    if data.eps_growth_rate != 0.0:
        g_pct = data.eps_growth_rate * 100
    else:
        # Conservative fallback
        g_pct = 8.0

    # AAA bond yield: stored as decimal in StockData, Graham formula needs %
    y_pct = data.aaa_bond_yield * 100
    if y_pct <= 0:
        y_pct = AAA_CONSTANT  # avoid division by zero

    eps = data.eps_ttm

    # ── Original formula ───────────────────────────────────────────────
    # V = EPS × (8.5 + 2g)
    original_iv = eps * (8.5 + 2 * g_pct)

    # ── Revised formula ────────────────────────────────────────────────
    # V = EPS × (8.5 + 2g) × 4.4/Y
    revised_iv = original_iv * (AAA_CONSTANT / y_pct)

    upside = (
        (revised_iv - data.current_price) / data.current_price
        if data.current_price > 0
        else 0.0
    )

    res.eps = eps
    res.growth_rate_pct = g_pct
    res.aaa_bond_yield_pct = y_pct
    res.original_intrinsic_value = original_iv
    res.revised_intrinsic_value = revised_iv
    res.intrinsic_value = revised_iv   # revised is the standard used in Output
    res.upside_pct = upside
    return res