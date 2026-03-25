"""
data_sources/yahoo_provider.py
==============================
DataProvider implementation that pulls live data from Yahoo Finance via
the ``yfinance`` library.
 
Usage::
 
    from data_sources.yahoo_provider import YahooFinanceProvider
    provider = YahooFinanceProvider()
    data = provider.fetch("MSFT")
"""
 
from __future__ import annotations
 
import math
from datetime import datetime
from typing import Optional
 
import numpy as np
 
from .base import AbstractDataProvider, ComparableCompany, StockData
 
# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
 
def _find_row(df, candidates: list[str]) -> Optional[str]:
    """Return the first candidate label that exists in *df.index*, or None."""
    for c in candidates:
        if c in df.index:
            return c
    return None
 
 
def _safe(value, default=0.0):
    """Return *value* unless it is None or NaN, in which case return *default*."""
    if value is None:
        return default
    try:
        if math.isnan(float(value)):
            return default
    except (TypeError, ValueError):
        return default
    return value
 
 
def _to_millions(value) -> float:
    return _safe(value, 0.0) / 1_000_000
 
 
# ---------------------------------------------------------------------------
# Provider
# ---------------------------------------------------------------------------
 
class YahooFinanceProvider(AbstractDataProvider):
    """
    Pulls fundamentals from Yahoo Finance.
 
    Parameters
    ----------
    risk_free_rate : float
        Override for the 10-yr Treasury yield used in CAPM & DCF.
    equity_risk_premium : float
        Market equity-risk premium (Damodaran default ≈ 0.05).
    aaa_bond_yield : float
        Current yield on AAA corporate bonds used in Graham's formula.
    terminal_growth_rate : float
        Perpetuity growth rate for DCF terminal value (≈ long-run GDP).
    n_fcf_years : int
        How many historical annual FCF data-points to request (default 10).
    n_div_years : int
        How many annual dividend observations to keep (default 5).
    """
 
    source_name = "yahoo_finance"
 
    def __init__(
        self,
        risk_free_rate: float = 0.043,
        equity_risk_premium: float = 0.05,
        aaa_bond_yield: float = 0.044,
        terminal_growth_rate: float = 0.03,
        n_fcf_years: int = 10,
        n_div_years: int = 5,
    ):
        self.risk_free_rate = risk_free_rate
        self.equity_risk_premium = equity_risk_premium
        self.aaa_bond_yield = aaa_bond_yield
        self.terminal_growth_rate = terminal_growth_rate
        self.n_fcf_years = n_fcf_years
        self.n_div_years = n_div_years
 
    # ------------------------------------------------------------------
    def fetch(self, ticker: str) -> StockData:
        try:
            import yfinance as yf
        except ImportError as exc:
            raise ImportError(
                "yfinance is required for YahooFinanceProvider.  "
                "Install it with: pip install yfinance"
            ) from exc
 
        t = yf.Ticker(ticker)
        info = t.info or {}
 
        # ── Identity ──────────────────────────────────────────────────
        company_name = info.get("longName") or info.get("shortName") or ticker
        sector = info.get("sector", "")
        industry = info.get("industryKey") or info.get("industry", "")
 
        # ── Market ────────────────────────────────────────────────────
        current_price = _safe(
            info.get("currentPrice") or info.get("regularMarketPrice")
        )
        market_cap = _to_millions(info.get("marketCap"))
        shares_out = _to_millions(info.get("sharesOutstanding"))
 
        # ── EPS ───────────────────────────────────────────────────────
        eps_ttm = _safe(info.get("trailingEps"), 0.0)
        # yfinance earningsGrowth is the YoY Q growth; earningsQuarterlyGrowth
        # is sometimes better.  We fall back to a 5yr historical if available.
        eps_growth_rate = _safe(
            info.get("earningsGrowth")
            or info.get("earningsQuarterlyGrowth")
            or info.get("revenueGrowth"),
            0.0,
        )
 
        # ── FCF history ───────────────────────────────────────────────
        fcf_history = self._build_fcf_history(t)
 
        # ── Balance sheet ─────────────────────────────────────────────
        cash, debt = self._build_balance_sheet(t)
 
        # ── Dividends ─────────────────────────────────────────────────
        dividend_history = self._build_dividend_history(t)
 
        # ── Beta ──────────────────────────────────────────────────────
        beta = _safe(info.get("beta"), 1.0)
 
        return StockData(
            ticker=ticker.upper(),
            company_name=company_name,
            sector=sector,
            industry=industry,
            current_price=current_price,
            market_cap=market_cap,
            shares_outstanding=shares_out,
            eps_ttm=eps_ttm,
            eps_growth_rate=eps_growth_rate,
            fcf_history=fcf_history,
            beta=beta,
            risk_free_rate=self.risk_free_rate,
            equity_risk_premium=self.equity_risk_premium,
            terminal_growth_rate=self.terminal_growth_rate,
            cash_and_equivalents=cash,
            total_debt=debt,
            dividend_history=dividend_history,
            aaa_bond_yield=self.aaa_bond_yield,
            comparables=[],   # Comparables must be supplied via settings
            data_source=self.source_name,
            last_updated=datetime.utcnow(),
        )
 
    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------
 
    def _build_fcf_history(self, ticker_obj) -> dict:
        """Build {year: FCF_millions} from yfinance cash-flow statement.
        
        Only includes completed fiscal years (year < current year) to avoid
        forward-looking projections or incomplete year data that can cause 
        unrealistic growth rates.
        """
        try:
            from datetime import datetime
            
            cf = ticker_obj.cashflow
            if cf is None or cf.empty:
                return {}
 
            op_row = _find_row(cf, [
                "Operating Cash Flow",
                "Total Cash From Operating Activities",
                "Cash Flow From Continuing Operating Activities",
            ])
            cx_row = _find_row(cf, [
                "Capital Expenditure",
                "Capital Expenditures",
                "Purchase Of Property Plant And Equipment",
            ])
            if op_row is None or cx_row is None:
                return {}
 
            current_year = datetime.now().year
            result = {}
            for col in list(cf.columns)[: self.n_fcf_years]:
                year = col.year if hasattr(col, "year") else int(str(col)[:4])
                
                # Skip current and future years (they may be projections or incomplete)
                if year >= current_year:
                    continue
                
                ocf = _safe(cf.loc[op_row, col], 0.0)
                capex = abs(_safe(cf.loc[cx_row, col], 0.0))
                fcf_m = (ocf - capex) / 1_000_000
                result[year] = fcf_m
 
            # Return sorted oldest→newest
            return dict(sorted(result.items()))
 
        except Exception:  # noqa: BLE001
            return {}
 
    def _build_balance_sheet(self, ticker_obj) -> tuple[float, float]:
        """Return (cash_millions, debt_millions) from the most-recent balance sheet."""
        try:
            bs = ticker_obj.balance_sheet
            if bs is None or bs.empty:
                return 0.0, 0.0
 
            latest = bs.columns[0]
 
            cash_row = _find_row(bs, [
                "Cash And Cash Equivalents",
                "Cash Cash Equivalents And Short Term Investments",
                "Cash And Short Term Investments",
            ])
            debt_row = _find_row(bs, [
                "Total Debt",
                "Long Term Debt",
                "Long Term Debt And Capital Lease Obligation",
            ])
 
            cash = _to_millions(bs.loc[cash_row, latest]) if cash_row else 0.0
            debt = _to_millions(bs.loc[debt_row, latest]) if debt_row else 0.0
            return cash, debt
 
        except Exception:  # noqa: BLE001
            return 0.0, 0.0
 
    def _build_dividend_history(self, ticker_obj) -> list[float]:
        """Return list of annual dividend totals (oldest→newest, up to n_div_years)."""
        try:
            divs = ticker_obj.dividends
            if divs is None or divs.empty:
                return []
            annual = divs.resample("YE").sum()
            return [float(v) for v in annual.values[-self.n_div_years :]]
        except Exception:  # noqa: BLE001
            return []