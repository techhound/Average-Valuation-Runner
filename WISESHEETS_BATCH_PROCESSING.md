# Batch Processing Wisesheets for Power BI

This guide shows how to batch process all your Wisesheets files and export results to Power BI.

## Quick Start

### Copy your files
Place all your raw Wisesheets Excel files in `data/wisesheets/`:
```
data/wisesheets/
  ├── MSFT.xlsx          (raw Wisesheets format)
  ├── AAPL.xlsx          (auto-transforms on load)
  ├── NVDA.xlsx
  └── GOOGL.xlsx
```

### Process all files (combined output)
```bash
uv run python batch_process_wisesheets.py
```

**Output:** `output/wisesheets_results/valuation_results_combined.csv`  
One CSV with all stocks - import directly to Power BI.

### Or output per-ticker for Power BI folder import
```bash
uv run python batch_process_wisesheets.py --separate
```

**Output:** `output/wisesheets_results/`
```
├── MSFT_valuation.csv
├── AAPL_valuation.csv
├── NVDA_valuation.csv
└── GOOGL_valuation.csv
```

You can then:
- Create a Power BI **folder connector** pointing to `output/wisesheets_results/`
- Or manually import each CSV file
- Or combine them in Power BI itself

## Features

### Auto-transformation
Files in raw Wisesheets format (with Income Statement, Cash Flow, etc. sheets) are **automatically transformed** to the proper ValuationData format on first load. No manual transformation needed!

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

# Combined output (default)
batch_process_wisesheets()

# Separate output
batch_process_wisesheets(
    output_format="separate",
    output_dir=Path("my_results/"),
    margin_of_safety=0.15,
)
```

## Power BI Integration

### Option 1: Combined CSV (recommended for simple setup)
1. Run: `uv run python batch_process_wisesheets.py`
2. In Power BI Desktop:  **Get Data** → **CSV** → `output/wisesheets_results/valuation_results_combined.csv`
3. Done!

### Option 2: Folder connector (recommended for ongoing updates)
1. Run: `uv run python batch_process_wisesheets.py --separate`
2. In Power BI Desktop: **Get Data** → **Folder**
3. Point to: `output/wisesheets_results/`
4. Power BI automatically combines all CSVs
5. When you add new stocks, just re-run the script and refresh Power BI

### Option 3: Manual per-file import
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
# Or import the combined CSV:
# uv run python batch_process_wisesheets.py  (for combined output)
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

1. **Add your Wisesheets files** to `data/wisesheets/`
2. **Run batch processing** to generate CSVs
3. **Import to Power BI** and create dashboards
4. **Refresh periodically** when you add new stocks
