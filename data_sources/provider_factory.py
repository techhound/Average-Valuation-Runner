"""
data_sources/provider_factory.py
==================================
Single entry-point for instantiating the correct DataProvider.

Usage::

    from data_sources.provider_factory import get_provider
    provider = get_provider()          # reads source from settings.py
    data     = provider.fetch("MSFT")

Or override the source at runtime::

    provider = get_provider(source="wisesheets")
"""

from __future__ import annotations

from .base import AbstractDataProvider


def get_provider(source: str | None = None, **kwargs) -> AbstractDataProvider:
    """
    Return an initialised DataProvider.

    Parameters
    ----------
    source : str, optional
        One of ``"yahoo"``, ``"wisesheets"``, or any string that matches a
        registered custom provider.  If *None*, the value from
        ``config.settings.DATA_SOURCE`` is used.
    **kwargs
        Passed through to the provider constructor.  Useful for one-off
        overrides without editing settings (e.g. ``workbook_path="..."``)
        when using the Wisesheets provider.

    Raises
    ------
    ValueError
        If *source* is not recognised.
    """
    from config.settings import SETTINGS  # local import avoids circular deps

    resolved = (source or SETTINGS.get("data_source", "yahoo")).lower().strip()

    # ── Yahoo Finance ─────────────────────────────────────────────────
    if resolved == "yahoo":
        from .yahoo_provider import YahooFinanceProvider
        yahoo_cfg = SETTINGS.get("yahoo", {})
        merged = {**yahoo_cfg, **kwargs}
        return YahooFinanceProvider(**merged)

    # ── Wisesheets (Excel) ────────────────────────────────────────────
    if resolved == "wisesheets":
        from .wisesheet_provider import WisesheetsProvider
        ws_cfg = SETTINGS.get("wisesheets", {})
        merged = {**ws_cfg, **kwargs}
        workbook_path = merged.pop("workbook_path", None)
        if workbook_path is None:
            raise ValueError(
                "Wisesheets provider requires 'workbook_path' in settings or as a kwarg."
            )
        return WisesheetsProvider(workbook_path=workbook_path, **merged)

    # ── Custom / user-registered providers ───────────────────────────
    registry = _custom_registry()
    if resolved in registry:
        cls = registry[resolved]
        custom_cfg = SETTINGS.get(resolved, {})
        merged = {**custom_cfg, **kwargs}
        return cls(**merged)

    raise ValueError(
        f"Unknown data source '{resolved}'.  "
        f"Valid built-in options: 'yahoo', 'wisesheets'.  "
        f"Registered custom sources: {list(registry.keys()) or 'none'}."
    )


# ---------------------------------------------------------------------------
# Custom provider registry
# ---------------------------------------------------------------------------

def _custom_registry() -> dict[str, type]:
    """
    Return a dict of {source_name: ProviderClass} for user-defined providers.

    To register a new source, import your class here and add it to the dict:

        from .my_source_provider import MySourceProvider
        return {
            "my_source": MySourceProvider,
            ...
        }
    """
    # Import custom providers here as you create them, for example:
    # from .bloomberg_provider import BloombergProvider
    # from .polygon_provider import PolygonProvider

    return {
        # "bloomberg": BloombergProvider,
        # "polygon":   PolygonProvider,
    }


# ---------------------------------------------------------------------------
# Wisesheets helpers
# ---------------------------------------------------------------------------

def get_wisesheets_provider(ticker: str) -> "AbstractDataProvider":
    """
    Quick helper to load a Wisesheets provider for a specific ticker.
    
    Looks for a file named '{ticker}.xlsx' in the data/wisesheets/ directory.
    
    If the file is in raw Wisesheets format (Income Statement, Cash Flow, etc.),
    it will be automatically transformed to ValuationData format on first load.
    
    Parameters
    ----------
    ticker : str
        Stock ticker (e.g. "MSFT", "AAPL").  Will search for `{ticker}.xlsx`.
    
    Returns
    -------
    WisesheetsProvider
        Initialised provider ready to fetch data.
    
    Raises
    ------
    FileNotFoundError
        If no Wisesheets file exists for the ticker.
    
    Example
    -------
    >>> provider = get_wisesheets_provider("MSFT")
    >>> data = provider.fetch("MSFT")
    """
    from pathlib import Path
    from .wisesheet_provider import WisesheetsProvider
    from .wisesheets_transformer import transform_raw_wisesheets
    
    # Default to data/wisesheets/{TICKER}.xlsx
    wisesheets_dir = Path(__file__).parent.parent / "data" / "wisesheets"
    workbook_path = wisesheets_dir / f"{ticker.upper()}.xlsx"
    
    if not workbook_path.exists():
        raise FileNotFoundError(
            f"No Wisesheets file found for {ticker}. "
            f"Expected: {workbook_path}"
        )
    
    # Check if file needs transformation (raw Wisesheets format)
    _auto_transform_if_needed(workbook_path)
    
    return WisesheetsProvider(workbook_path=str(workbook_path))


def _auto_transform_if_needed(workbook_path: Path) -> None:
    """
    Check if file needs transformation and auto-transform if required.
    
    A file needs transformation if:
    1. It's in raw Wisesheets format (has Income Statement, Cash Flow, etc.)
    2. AND the canonical CSV output doesn't exist or is older than the input Excel
    """
    import os
    import openpyxl
    
    try:
        # Check if input is raw Wisesheets format
        wb = openpyxl.load_workbook(workbook_path, data_only=False)
        sheets = wb.sheetnames
        wb.close()
        
        # Check for raw Wisesheets sheets
        has_income = any("Income Statement" in s for s in sheets)
        has_cashflow = any("Cash Flow" in s for s in sheets)
        
        if not (has_income and has_cashflow):
            # Not raw Wisesheets format, skip transformation
            return
        
        # Extract ticker from Excel filename
        ticker = workbook_path.stem.upper()
        csv_path = workbook_path.parent.parent / "output" / "wisesheets_valinput" / f"{ticker}.csv"
        
        # Determine if transformation is needed
        needs_transform = False
        
        if not csv_path.exists():
            # CSV doesn't exist, need to transform
            needs_transform = True
        else:
            # CSV exists, check timestamp: if Excel is newer, re-transform
            excel_mtime = os.path.getmtime(workbook_path)
            csv_mtime = os.path.getmtime(csv_path)
            if excel_mtime > csv_mtime:
                needs_transform = True
        
        if needs_transform:
            from .wisesheets_transformer import transform_raw_wisesheets
            transform_raw_wisesheets(workbook_path)
    
    except Exception:
        # If anything goes wrong, just skip auto-transform
        # File will fail to load properly anyway with clearer error
        pass


def batch_load_wisesheets(tickers: list[str]) -> dict[str, "AbstractDataProvider"]:
    """
    Load Wisesheets providers for multiple tickers.
    
    Parameters
    ----------
    tickers : list[str]
        List of ticker symbols (e.g. ["MSFT", "AAPL", "NVDA"]).
    
    Returns
    -------
    dict[str, WisesheetsProvider]
        Dict mapping {ticker: provider} for each successfully loaded file.
        Skips tickers with missing files (logs a warning).
    
    Example
    -------
    >>> providers = batch_load_wisesheets(["MSFT", "AAPL", "NVDA"])
    >>> for ticker, provider in providers.items():
    ...     data = provider.fetch(ticker)
    """
    import warnings
    
    providers = {}
    for ticker in tickers:
        try:
            providers[ticker.upper()] = get_wisesheets_provider(ticker)
        except FileNotFoundError as e:
            warnings.warn(str(e), stacklevel=2)
    
    return providers