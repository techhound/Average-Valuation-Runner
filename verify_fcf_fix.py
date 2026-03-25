#!/usr/bin/env python
"""Quick check of FCF history after fixes."""

from data_sources.provider_factory import get_provider
import json

provider = get_provider(source="yahoo")

for ticker in ["MSFT", "NVDA"]:
    data = provider.fetch(ticker)
    print(f"\n{ticker} FCF History (should NOT include 2026):")
    for year, fcf in sorted(data.fcf_history.items()):
        print(f"  {year}: ${fcf:,.0f}M")
