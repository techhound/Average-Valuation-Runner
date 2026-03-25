#!/usr/bin/env python
"""Debug DCF valuation to see where it fails."""

from data_sources.provider_factory import get_provider
from valuation.valuation_runner import run_all

provider = get_provider(source="yahoo")

# Fetch and value MSFT and NVDA
for ticker in ["MSFT", "NVDA"]:
    print(f"\n{'='*80}")
    print(f"Valuing {ticker}")
    print(f"{'='*80}")
    
    stock_data = provider.fetch(ticker)
    
    if stock_data:
        from valuation.models.dcf import run_dcf
        
        dcf = run_dcf(stock_data)
        
        print(f"\nDCF Inputs:")
        print(f"  FCF Base (latest year): ${dcf.fcf_base:,.0f}M")
        print(f"  Historical Growth Avg:  {dcf.avg_historical_growth*100:.2f}%")
        print(f"  Applied Growth Rate:    {dcf.growth_rate*100:.2f}%")
        print(f"  Discount Rate (CAPM):   {dcf.discount_rate*100:.2f}%")
        print(f"  Terminal Growth Rate:   {dcf.terminal_growth_rate*100:.2f}%")
        
        print(f"\nDCF Calculations:")
        print(f"  Sum PV(FCF 10yr):       ${dcf.sum_pv_fcf:,.0f}M")
        print(f"  PV(Terminal Value):     ${dcf.pv_terminal_value:,.0f}M")
        print(f"  Enterprise Value:       ${dcf.enterprise_value:,.0f}M")
        print(f"  + Cash:                 ${dcf.cash:,.0f}M")
        print(f"  - Debt:                 ${dcf.debt:,.0f}M")
        print(f"  = Equity Value:         ${dcf.equity_value:,.0f}M")
        print(f"  / Shares:               {dcf.shares_outstanding:,.0f}M")
        
        print(f"\nDCF Result:")
        print(f"  Intrinsic Value:        ${dcf.intrinsic_value:.2f}/share")
        print(f"  Current Price:          ${dcf.current_price:.2f}/share")
        print(f"  Upside:                 {dcf.upside_pct*100:.1f}%")
        
        if dcf.error:
            print(f"  ERROR: {dcf.error}")
    else:
        print(f"Failed to fetch {ticker}")
