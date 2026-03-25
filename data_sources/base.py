"""
data_sources/base.py
====================
Canonical schema and abstract interface that every data provider must implement.

All providers (Yahoo Finance, Wisesheets, custom) must return a ``StockData``
instance so the valuation layer never needs to know where the data came from.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


# ---------------------------------------------------------------------------
# Supporting structures
# ---------------------------------------------------------------------------

@dataclass
class ComparableCompany:
    """A peer company used in the Multiples Valuation model."""
    ticker: str
    company_name: str
    stock_price: float
    eps: float

    @property
    def pe_ratio(self) -> Optional[float]:
        if self.eps and self.eps != 0:
            return self.stock_price / self.eps
        return None


# ---------------------------------------------------------------------------
# Canonical data schema
# ---------------------------------------------------------------------------

@dataclass
class StockData:
    """
    Single source of truth for all data consumed by the valuation engine.

    Units convention
    ----------------
    - Monetary figures (FCF, cash, debt, market_cap): millions of USD
    - Rates / ratios: decimals  (e.g. 0.165 for 16.5 %)
    - Prices and EPS: plain USD
    - Shares outstanding: millions

    Fields marked "engine-computed if 0" are optional overrides: leave them at
    0.0 to let the valuation runner derive sensible defaults from history.
    """

    # ── Identity ──────────────────────────────────────────────────────────
    ticker: str
    company_name: str
    sector: str = ""
    industry: str = ""

    # ── Market price & capitalisation ────────────────────────────────────
    current_price: float = 0.0
    market_cap: float = 0.0        # millions
    shares_outstanding: float = 0.0  # millions

    # ── Earnings per share ────────────────────────────────────────────────
    eps_ttm: float = 0.0
    # Projected 5-year EPS growth rate used by Graham model.
    # Engine-computed if 0 (falls back to historical EPS CAGR if available,
    # otherwise raises a warning and uses a conservative 0.08).
    eps_growth_rate: float = 0.0

    # ── Free Cash Flow history ────────────────────────────────────────────
    # {year (int): FCF in millions}  — provide at least 3 years for DCF
    fcf_history: dict = field(default_factory=dict)
    # Override DCF growth rate; engine-computed from history if 0.
    fcf_growth_rate: float = 0.0

    # ── DCF / CAPM assumptions ────────────────────────────────────────────
    beta: float = 1.0
    risk_free_rate: float = 0.043       # 10-yr Treasury yield
    equity_risk_premium: float = 0.05
    terminal_growth_rate: float = 0.03  # perpetuity growth after year 10

    # ── Balance sheet ─────────────────────────────────────────────────────
    cash_and_equivalents: float = 0.0   # millions
    total_debt: float = 0.0             # millions

    # ── Dividends ─────────────────────────────────────────────────────────
    # Annual dividends per share, oldest first, up to 5 years.
    dividend_history: list = field(default_factory=list)
    # Override DDM growth rate; engine-computed from history if 0.
    dividend_growth_rate: float = 0.0
    # DDM discount rate.  Engine-computed via CAPM if 0.
    wacc: float = 0.0

    # ── Multiples ─────────────────────────────────────────────────────────
    comparables: list = field(default_factory=list)  # list[ComparableCompany]

    # ── Graham constants ──────────────────────────────────────────────────
    # Current yield on AAA corporate bonds (the "Y" in the revised formula).
    aaa_bond_yield: float = 0.044

    # ── Metadata ──────────────────────────────────────────────────────────
    data_source: str = ""
    last_updated: datetime = field(default_factory=datetime.utcnow)

    # ------------------------------------------------------------------
    def validate(self) -> list[str]:
        """
        Lightweight sanity check.  Returns a list of human-readable warning
        strings; an empty list means the record looks clean.
        """
        warnings: list[str] = []
        pfx = f"[{self.ticker}]"

        if self.current_price <= 0:
            warnings.append(f"{pfx} current_price = {self.current_price} (≤ 0)")
        if self.eps_ttm == 0:
            warnings.append(f"{pfx} eps_ttm = 0  → Graham & Multiples may be unreliable")
        if not self.fcf_history:
            warnings.append(f"{pfx} fcf_history is empty  → DCF cannot run")
        if not self.dividend_history:
            warnings.append(f"{pfx} dividend_history is empty  → DDM cannot run")
        if self.shares_outstanding <= 0:
            warnings.append(f"{pfx} shares_outstanding = {self.shares_outstanding} (≤ 0)  → DCF per-share will fail")

        return warnings

    # ------------------------------------------------------------------
    def capm_discount_rate(self) -> float:
        """Convenience: compute CAPM discount rate from stored assumptions."""
        return self.risk_free_rate + self.beta * self.equity_risk_premium


# ---------------------------------------------------------------------------
# Abstract provider interface
# ---------------------------------------------------------------------------

class AbstractDataProvider(ABC):
    """
    Every data source must implement ``fetch(ticker) -> StockData``.

    The optional ``fetch_many`` method defaults to a sequential loop but can be
    overridden to use batching / async requests where the source supports it.
    """

    source_name: str = "abstract"

    @abstractmethod
    def fetch(self, ticker: str) -> StockData:
        """Return a fully-populated ``StockData`` for *ticker*."""
        ...

    def fetch_many(self, tickers: list[str]) -> list[StockData]:
        """
        Fetch multiple tickers.  Errors are caught per-ticker so a single
        bad symbol does not abort the whole batch.
        """
        results: list[StockData] = []
        for ticker in tickers:
            try:
                data = self.fetch(ticker)
                warnings = data.validate()
                for w in warnings:
                    print(f"  ⚠  {w}")
                results.append(data)
            except Exception as exc:  # noqa: BLE001
                print(f"  ✗  [{self.source_name}] Could not fetch {ticker}: {exc}")
        return results