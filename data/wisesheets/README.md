# Wisesheets Data Integration

This directory (`data/wisesheets/`) stores Excel workbooks for individual stocks in Wisesheets format.

NOTE: You will either need to purchase a license from Wisesheets doc come to pull data from the market or you will need to pull the data from other sources and put it into the same format as Wisesheets.

This process does not include any Wisesheets. You will need to provide them yourself. 

We are working on a SEC connector which is currently publicly available and free. 

## Case Study
This code is part of a case study that is trying to discover if averaging the results of different valuation methods (DCF, Multiples, Grahap) will lead to better investing results. 

Documentation on the case study can be find in the Documentation directory here on GitHub.

## Technical Architecture
To streamline the documentation, I've created a separate [architecture document](Architecture.md) that describes the technologies.

## Setup

1. **Place one Excel file per stock** in this directory:
   ```
   data/wisesheets/
     ├── MSFT.xlsx
     ├── AAPL.xlsx
     ├── NVDA.xlsx
     └── ...
   ```

2. **Each file should contain** Wisesheets format sheets:
   - Income Statement
   - Balance Sheet  
   - Cash Flow
   - Key Metrics
   - Financial Growth

## Usage

### Load a single ticker:
```python
from data_sources.provider_factory import get_wisesheets_provider

provider = get_wisesheets_provider("MSFT")
stock_data = provider.fetch("MSFT")
```

### Batch load multiple tickers:
```python
from data_sources.provider_factory import batch_load_wisesheets

providers = batch_load_wisesheets(["MSFT", "AAPL", "NVDA"])
for ticker, provider in providers.items():
    stock_data = provider.fetch(ticker)
```

### Run valuations:
```python
from valuation.valuation_runner import run_all

summary = run_all(stock_data, margin_of_safety=0.15)
print(f"{ticker}: {summary.signal} - ${summary.intrinsic_value_avg:.2f}")
```

## Example

See `example_wisesheets.py` for a complete working example.

```bash
python example_wisesheets.py
```

## File Format

Each Excel workbook must follow the Wisesheets template structure. You can generate a template with:

```python
from data_sources.wisesheet_provider import WisesheetsProvider

WisesheetsProvider.write_template("MSFT_template.xlsx")
```

Then populate it with your data and place it in this directory as `MSFT.xlsx`.
