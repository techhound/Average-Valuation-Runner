# Wisesheets Data Integration

This directory (`data/wisesheets/`) stores Excel workbooks for individual stocks in Wisesheets format.

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
