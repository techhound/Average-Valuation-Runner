#!/usr/bin/env python
"""
Example: Loading Wisesheets data using the new helper functions.

Place your Excel files in: data/wisesheets/{TICKER}.xlsx

Then use:
  - get_wisesheets_provider(ticker) for a single ticker
  - batch_load_wisesheets(tickers) for multiple tickers
"""

from data_sources.provider_factory import (
    get_wisesheets_provider,
    batch_load_wisesheets,
)
from valuation.valuation_runner import run_all


# ── Example 1: Load a single ticker ───────────────────────────────────
def example_single_ticker():
    """Load and value MSFT from data/wisesheets/MSFT.xlsx"""
    print("\n" + "="*70)
    print("EXAMPLE 1: Single ticker from Wisesheets")
    print("="*70)
    
    try:
        provider = get_wisesheets_provider("MSFT")
        stock_data = provider.fetch("MSFT")
        
        print(f"\n{stock_data.company_name} ({stock_data.ticker})")
        print(f"  Current Price:      ${stock_data.current_price:.2f}")
        print(f"  EPS TTM:            ${stock_data.eps_ttm:.2f}")
        print(f"  FCF History:        {list(stock_data.fcf_history.keys())}")
        
        # Run valuations
        summary = run_all(stock_data, margin_of_safety=0.15)
        dcf_str = f"${summary.dcf_value:.2f}" if summary.dcf_value else "N/A"
        iv_str = f"${summary.intrinsic_value_avg:.2f}" if summary.intrinsic_value_avg else "N/A"
        print(f"\n  DCF Value:          {dcf_str}")
        print(f"  Intrinsic Value:    {iv_str}")
        print(f"  Signal:             {summary.signal or 'Unable to compute'}")
        
    except FileNotFoundError as e:
        print(f"  ⚠️  {e}")
        print(f"      Place your file at: data/wisesheets/MSFT.xlsx")


# ── Example 2: Batch load multiple tickers ────────────────────────────
def example_batch_load():
    """Load and value multiple tickers from Wisesheets files"""
    print("\n" + "="*70)
    print("EXAMPLE 2: Batch load multiple tickers")
    print("="*70)
    
    tickers = ["MSFT", "AAPL", "NVDA"]
    providers = batch_load_wisesheets(tickers)
    
    print(f"\n  Successfully loaded: {list(providers.keys())}")
    
    for ticker, provider in providers.items():
        try:
            stock_data = provider.fetch(ticker)
            summary = run_all(stock_data, margin_of_safety=0.15)
            
            print(f"\n  {ticker}: ${stock_data.current_price:.2f} → "
                  f"${summary.intrinsic_value_avg:.2f} ({summary.signal})")
        except Exception as e:
            print(f"\n  {ticker}: Error — {e}")


if __name__ == "__main__":
    # Run examples (will warn if files don't exist yet)
    example_single_ticker()
    example_batch_load()
    
    print("\n" + "="*70)
    print("💡 Next steps:")
    print("   1. Place Wisesheets Excel files in: data/wisesheets/{TICKER}.xlsx")
    print("   2. Import and use: get_wisesheets_provider(ticker)")
    print("   3. Or batch load with: batch_load_wisesheets([tickers...])")
    print("="*70 + "\n")
