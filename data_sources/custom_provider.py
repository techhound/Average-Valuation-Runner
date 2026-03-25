"""
data_sources/custom_provider.py
================================
A fully documented template for building your own data provider.

Copy this file, rename it (e.g. ``bloomberg_provider.py``), replace every
``# TODO`` section with your source-specific logic, and register the new class
in ``provider_factory.py``.  The only hard contract is that ``fetch()`` must
return a populated ``StockData`` instance — everything else is up to you.

Quick-start
-----------
1.  Copy this file:
        cp data_sources/custom_provider.py data_sources/my_source_provider.py

2.  Replace the class name and ``source_name``:
        class MySourceProvider(CustomDataProvider):
            source_name = "my_source"

3.  Implement ``fetch()``.

4.  Add an entry in ``config/settings.py`` and ``provider_factory.py``.
"""

from __future__ import annotations

from datetime import datetime

from .base import AbstractDataProvider, ComparableCompany, StockData


class CustomDataProvider(AbstractDataProvider):
    """
    Template for a user-supplied data provider.

    Subclass this and implement ``fetch()``.  Override ``fetch_many()`` only
    if your source has a more efficient batch API (e.g. a single request that
    returns many tickers at once).
    """

    source_name = "custom"   # ← change this in your subclass

    def __init__(self, **kwargs):
        """
        Accept whatever credentials / config your source needs.

        Example:
            def __init__(self, api_key: str, base_url: str = "https://..."):
                self.api_key = api_key
                self.base_url = base_url
        """
        # TODO: store your connection/config parameters here
        pass

    # ------------------------------------------------------------------
    def fetch(self, ticker: str) -> StockData:
        """
        Retrieve data for *ticker* from your custom source and return a
        ``StockData``.  Every field is optional except ``ticker``; leave
        unknown fields at their default (0.0 / [] / {}) and the valuation
        engine will either skip the affected model or apply a conservative
        fallback.

        Skeleton implementation — replace the ``# TODO`` sections.
        """

        # ── 1. Call your data source ──────────────────────────────────
        # TODO: replace with your actual API / DB / file call
        raw = self._fetch_raw(ticker)

        # ── 2. Map raw data → canonical types ─────────────────────────

        # Identity
        company_name: str = raw.get("company_name", ticker)
        sector: str       = raw.get("sector", "")
        industry: str     = raw.get("industry", "")

        # Market
        current_price: float        = float(raw.get("price", 0.0))
        market_cap: float           = float(raw.get("market_cap_m", 0.0))   # millions
        shares_outstanding: float   = float(raw.get("shares_m", 0.0))       # millions

        # EPS
        eps_ttm: float         = float(raw.get("eps_ttm", 0.0))
        eps_growth_rate: float = float(raw.get("eps_growth_rate", 0.0))     # decimal

        # FCF history {year: millions}
        # TODO: build this from your source's income/cashflow data
        fcf_history: dict[int, float] = {}   # e.g. {2020: 45234.0, 2021: 56118.0}
        fcf_growth_rate: float = 0.0         # 0 → engine computes from history

        # DCF / CAPM assumptions
        beta: float                 = float(raw.get("beta", 1.0))
        risk_free_rate: float       = 0.043   # TODO: pull from your source or settings
        equity_risk_premium: float  = 0.05
        terminal_growth_rate: float = 0.03

        # Balance sheet (millions)
        cash_and_equivalents: float = float(raw.get("cash_m", 0.0))
        total_debt: float           = float(raw.get("debt_m", 0.0))

        # Dividends — list of annual totals, oldest first
        dividend_history: list[float] = []   # TODO: populate from your source
        dividend_growth_rate: float   = 0.0  # 0 → engine computes from history
        wacc: float                   = 0.0  # 0 → engine computes via CAPM

        # Comparable companies for Multiples model
        comparables: list[ComparableCompany] = []
        # TODO: populate from your source, e.g.:
        # comparables = [
        #     ComparableCompany("AAPL", "Apple Inc", 247.99, 7.92),
        #     ComparableCompany("GOOG", "Alphabet",  298.79, 10.81),
        # ]

        # Graham constant
        aaa_bond_yield: float = 0.044   # TODO: pull from your source

        # ── 3. Return canonical StockData ─────────────────────────────
        return StockData(
            ticker=ticker.upper(),
            company_name=company_name,
            sector=sector,
            industry=industry,
            current_price=current_price,
            market_cap=market_cap,
            shares_outstanding=shares_outstanding,
            eps_ttm=eps_ttm,
            eps_growth_rate=eps_growth_rate,
            fcf_history=fcf_history,
            fcf_growth_rate=fcf_growth_rate,
            beta=beta,
            risk_free_rate=risk_free_rate,
            equity_risk_premium=equity_risk_premium,
            terminal_growth_rate=terminal_growth_rate,
            cash_and_equivalents=cash_and_equivalents,
            total_debt=total_debt,
            dividend_history=dividend_history,
            dividend_growth_rate=dividend_growth_rate,
            wacc=wacc,
            comparables=comparables,
            aaa_bond_yield=aaa_bond_yield,
            data_source=self.source_name,
            last_updated=datetime.utcnow(),
        )

    # ------------------------------------------------------------------
    # Private helpers — implement or replace as needed
    # ------------------------------------------------------------------

    def _fetch_raw(self, ticker: str) -> dict:
        """
        Call your data source and return a raw dict.

        TODO: replace the stub below with your actual data-fetch logic.

        Example patterns:
            REST API  →  return requests.get(url, headers=...).json()
            SQL DB    →  return cursor.execute(query, (ticker,)).fetchone()
            CSV       →  return df.loc[df.ticker == ticker].iloc[0].to_dict()
        """
        # Stub — returns an empty dict so the provider instantiates without error
        return {}