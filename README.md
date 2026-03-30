# Average Valuation Runner

This Python project creates valuations using market data. Today it supports:
- Wisesheets Excel inputs (primary workflow)
- Yahoo Finance (via `yfinance`) when `DATA_SOURCE = "yahoo"` in `config/settings.py`

Raw Excel sheets in Wisesheets format are read and transformed into CSV outputs. The input Excel files are not modified.

Outputs are written under `output/`:
- `wisesheets_results` (valuation results per ticker)
- `wisesheets_valinput` (core valuation inputs extracted from Wisesheets)
- `wisesheets_cashflows` (normalized historical cashflows)
- `wisesheets_dividends` (normalized dividends)
- `wisesheets_comps` (normalized comparables)
- `wisesheets_forecasted` (DCF forecast rows per ticker)
- `computed_assumptions` (model assumptions used per run)

**You will need to create a spreadsheet that contains the needed data in wisesheets.com format. See Wisesheets.com for more information as to that format.

We are currently working on a connector to the SEC data for use in this model. 

## Case Study
This code is part of a case study that is trying to discover if averaging the results of different valuation methods (DCF, Multiples, Grahap) will lead to better investing results. 

Documentation on the case study can be find in the Documentation directory here on GitHub.

## Technical Architecture
To streamline the documentation, I've created a separate [architecture document](Architecture.md) that describes the technologies.

## Power BI Case Study
The completed power BI case study can be found here -> https://DataScienceReview.com/Valuation.

# Batch Processing Excel workbooks in Wisesheets format for Power BI

This guide shows how to batch process all your XLSX files and export results to Power BI.
If you see "Permission denied" errors when writing to `output/`, close any open
Excel/Power BI files using those CSVs. On some machines you may need to run the
batch script with elevated permissions.

In the Power BI subfolder, I included the starting (work in progress) PBIX for you to take a look. If you decide to use it as is and want to work in the Power Query to make changes, you'll need to change the paths of the source accordingly.

## Quick Start

### Copy your files
Place all your raw Wisesheets Excel files in `data/wisesheets/`:
```
data/wisesheets/
  |-- MSFT.xlsx          (raw Wisesheets format)
  |-- AAPL.xlsx          (auto-transforms on load)
  |-- NVDA.xlsx
  |-- GOOGL.xlsx
```

### Process all files (per-ticker output)
```bash
uv run python batch_process_wisesheets.py
```

**Output:** one CSV per ticker in `output/wisesheets_results/`.

### Or output per-ticker for Power BI folder import
```bash
uv run python batch_process_wisesheets.py --separate
```

**Output:** `output/wisesheets_results/`
```
|-- MSFT_valuation.csv
|-- AAPL_valuation.csv
|-- NVDA_valuation.csv
|-- GOOGL_valuation.csv
```

You can then:
- Create a Power BI folder connector pointing to `output/wisesheets_results/`
- Or manually import each CSV file
- Or combine them in Power BI itself

## Features

### Auto-transformation
Files in raw Wisesheets format (with Income Statement, Cash Flow, etc. sheets) are automatically transformed to the proper ValuationData CSV format on first load. No manual transformation needed.

### Customization

```bash
# Custom output directory
uv run python batch_process_wisesheets.py --output my_results/

# Custom margin of safety (default: 0.15)
uv run python batch_process_wisesheets.py --mos 0.20

# Separate output with custom MOS
uv run python batch_process_wisesheets.py --separate --mos 0.20
```

## Python Usage

If you want to use the batch processing in code:

```python
from pathlib import Path
from batch_process_wisesheets import batch_process_wisesheets

# Per-ticker output (default)
batch_process_wisesheets()

# Separate output (same behavior, explicit)
batch_process_wisesheets(
    output_format="separate",
    output_dir=Path("my_results/"),
    margin_of_safety=0.15,
)
```

## Power BI Integration

### Option 1: Folder connector (recommended for ongoing updates)
1. Run: `uv run python batch_process_wisesheets.py --separate`
2. In Power BI Desktop: Get Data -> Folder
3. Point to: `output/wisesheets_results/`
4. Power BI automatically combines all CSVs
5. When you add new stocks, just re-run the script and refresh Power BI

### Option 2: Manual per-file import
1. Run: `uv run python batch_process_wisesheets.py --separate`
2. Import each CSV file individually to Power BI
3. Combine them in the Power BI data model

## Workflow Example

```bash
# 1. Add new Wisesheets files to data/wisesheets/
cp ~/Downloads/AAPL.xlsx data/wisesheets/
cp ~/Downloads/NVDA.xlsx data/wisesheets/

# 2. Process all files
uv run python batch_process_wisesheets.py --separate

# 3. In Power BI, refresh your data source pointing to output/wisesheets_results/
```

## Output Columns

Both combined and separate outputs include:

```
ticker                    Stock symbol
company_name              Full company name
sector, industry          Sector and industry classifications
current_price             Current stock price
market_cap_m              Market cap in millions
shares_outstanding_m      Shares outstanding in millions

dcf_value                 DCF valuation per share
graham_value              Graham valuation per share
multiples_value           Multiples-based valuation
ddm_value                 Dividend discount model valuation

intrinsic_value_avg       Average of all models
intrinsic_value_median    Median of all models
margin_of_safety          Applied margin of safety
acceptable_buy_price      Price to buy at MOS

signal                    "Buy", "Hold", or "Sell"
upside_to_intrinsic_pct   Upside/downside % to intrinsic value

dcf_*, graham_*, multiples_*, ddm_*
                          Model assumptions and intermediate values
```

## Troubleshooting

### "No .xlsx files found"
- Check that files are in `data/wisesheets/`
- Ensure files end with `.xlsx` (not .xls)

### "Sheet 'ValuationData' not found"
- File is in raw Wisesheets format but auto-transform failed
- Run manually: `uv run python transform_wisesheets.py data/wisesheets/{TICKER}.xlsx`

### Power BI won't update
- Make sure you refresh the data source in Power BI
- Check file permissions on `output/wisesheets_results/`

## Next Steps

1. Add your Wisesheets files to `data/wisesheets/`
2. Run batch processing to generate CSVs
3. Import to Power BI and create dashboards
4. Refresh periodically when you add new stocks
