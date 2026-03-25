#!/usr/bin/env python
"""Debug script to inspect Yahoo Finance data fetching."""

from data_sources.provider_factory import get_provider

provider = get_provider(source="yahoo")

# Fetch MSFT and NVDA
for ticker in ["MSFT", "NVDA"]:
    print(f"\n{'='*80}")
    print(f"Ticker: {ticker}")
    print(f"{'='*80}")
    
    stock_data = provider.fetch(ticker)
    
    if stock_data:
        print(f"Current Price:          ${stock_data.current_price:.2f}")
        print(f"Market Cap:             ${stock_data.market_cap:,.0f}M = ${stock_data.market_cap/1000:,.1f}B")
        print(f"Shares Outstanding:     {stock_data.shares_outstanding:,.0f}M")
        print(f"EPS TTM:                ${stock_data.eps_ttm:.2f}")
        print(f"EPS Growth Rate:        {stock_data.eps_growth_rate*100:.2f}%")
        
        print(f"\nFCF History (millions):")
        for year, fcf in sorted(stock_data.fcf_history.items()):
            print(f"  {year}: ${fcf:,.0f}M")
        
        print(f"\nCash & Debt:")
        print(f"  Cash:                 ${stock_data.cash_and_equivalents:,.0f}M")
        print(f"  Total Debt:           ${stock_data.total_debt:,.0f}M")
        
        print(f"\nDividends:")
        if stock_data.dividend_history:
            for i, div in enumerate(reversed(stock_data.dividend_history)):
                print(f"  Year {i}: ${div:.4f}/share")
        else:
            print("  No dividend history")
        
        print(f"\nAssumptions:")
        print(f"  Beta:                 {stock_data.beta:.2f}")
        print(f"  Risk-Free Rate:       {stock_data.risk_free_rate*100:.2f}%")
        print(f"  ERP:                  {stock_data.equity_risk_premium*100:.2f}%")
        print(f"  Terminal Growth Rate: {stock_data.terminal_growth_rate*100:.2f}%")
        print(f"  CAPM Discount Rate:   {stock_data.capm_discount_rate()*100:.2f}%")
    else:
        print(f"Failed to fetch {ticker}")
