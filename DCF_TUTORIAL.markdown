# DCF Processing Tutorial (Wisesheets Pipeline)

This document describes how the DCF model is processed in this codebase, which input fields are used, where those fields come from, and how the output fields are produced. It focuses only on DCF-related modules and paths.

## Scope

Relevant modules:
- `valuation/models/dcf.py` defines the DCF logic and outputs.
- `data_sources/base.py` defines the canonical `StockData` inputs and CAPM helper.
- `data_sources/wisesheet_provider.py` maps Wisesheets inputs into `StockData`.
- `valuation/valuation_runner.py` maps DCF outputs into the summary row.
- `batch_process_wisesheets.py` emits a per-year DCF forecast CSV.

## Inputs Used by DCF (StockData Fields)

All DCF inputs live on the canonical `StockData` dataclass in `data_sources/base.py`. Units and meaning:

- `fcf_history` (dict year -> FCF, millions USD). Required for DCF.
- `fcf_growth_rate` (decimal). Optional override for DCF growth rate; if 0, DCF derives a historical average.
- `terminal_growth_rate` (decimal). Perpetuity growth after the explicit forecast period.
- `risk_free_rate` (decimal). Used in CAPM discount rate.
- `beta` (decimal). Used in CAPM discount rate.
- `equity_risk_premium` (decimal). Used in CAPM discount rate.
- `cash_and_equivalents` (millions USD). Added to enterprise value.
- `total_debt` (millions USD). Subtracted from enterprise value.
- `shares_outstanding` (millions). Used to compute per-share intrinsic value.
- `current_price` (USD). Used to compute upside percentage.
- `ticker` (string). Included in output for identification.

CAPM discount rate is computed by `StockData.capm_discount_rate()` in `data_sources/base.py`:

```
discount_rate = risk_free_rate + beta * equity_risk_premium
```

## Where the Inputs Come From (Wisesheets)

`data_sources/wisesheet_provider.py` loads Wisesheets data and maps columns to `StockData`. DCF-relevant columns are:

- `fcf_YYYY` (millions USD). One column per year, used to build `fcf_history`.
- `fcf_growth_rate` (decimal). Stored as `StockData.fcf_growth_rate`.
- `terminal_growth_rate` (decimal). Stored as `StockData.terminal_growth_rate`.
- `risk_free_rate` (decimal). Stored as `StockData.risk_free_rate`.
- `beta` (decimal). Stored as `StockData.beta`.
- `equity_risk_premium` (decimal). Stored as `StockData.equity_risk_premium`.
- `cash_and_equivalents` (millions USD). Stored as `StockData.cash_and_equivalents`.
- `total_debt` (millions USD). Stored as `StockData.total_debt`.
- `shares_outstanding` (millions). Stored as `StockData.shares_outstanding`.
- `current_price` (USD). Stored as `StockData.current_price`.
- `ticker` (string). Stored as `StockData.ticker`.
- `company_name` (string). Used in output summary but not the DCF math.

The provider supports CSV or Excel input. It normalizes headers case-insensitively and extracts `fcf_YYYY` fields via regex, then sorts them by year before storing in `fcf_history`.

## DCF Processing Flow (Core Logic)

All DCF math lives in `valuation/models/dcf.py`. The primary entry point is `run_dcf(data, forecast_years=10)`.

### Guard Conditions

DCF is skipped (returns `DCFResult.error`) when:
- `fcf_history` is empty.
- `shares_outstanding <= 0`.
- The most recent FCF is `<= 0` (loss-making FCF).

### Step 1: Determine Base FCF

- Sort `fcf_history` by year.
- Use the most recent FCF as `fcf_base`.

### Step 2: Determine Growth Rate

Growth rate is chosen as:

- If `data.fcf_growth_rate != 0.0`, use it as the explicit override.
- Otherwise compute a historical average with `_historical_avg_growth()`:
  - Average year-over-year growth rates where both years have positive FCF.
  - Cap each yearly growth rate at 100%.
  - If no usable rates, default to 10%.
  - Cap the final average at 50%.

This helper exists in both `valuation/models/dcf.py` and `batch_process_wisesheets.py` and follows the same logic.

### Step 3: Determine Discount Rate (CAPM)

The discount rate is computed using CAPM via `data.capm_discount_rate()`:

```
r = risk_free_rate + beta * equity_risk_premium
```

Safety rule:
- If `r <= terminal_growth_rate`, set `r = terminal_growth_rate + 0.02`.

### Step 4: Forecast FCF and Discount It

For years `t = 1..forecast_years` (default 10):

- `fcf_t = fcf_{t-1} * (1 + growth_rate)`
- `pv_t = fcf_t / (1 + discount_rate)^t`
- Accumulate `sum_pv_fcf = sum(pv_t)`

### Step 5: Terminal Value

Using the Gordon Growth formula:

```
terminal_fcf = fcf_10 * (1 + terminal_growth_rate)
terminal_value = terminal_fcf / (discount_rate - terminal_growth_rate)
pv_terminal = terminal_value / (1 + discount_rate)^forecast_years
```

### Step 6: Enterprise Value -> Equity Value -> Per Share

```
enterprise_value = sum_pv_fcf + pv_terminal
equity_value = enterprise_value + cash_and_equivalents - total_debt
intrinsic_value = equity_value / shares_outstanding
```

### Step 7: Upside

```
upside_pct = (intrinsic_value - current_price) / current_price
```

If `current_price <= 0`, upside is set to 0.

## DCF Outputs and Where They Go

### DCFResult (from `valuation/models/dcf.py`)

`DCFResult` holds the model outputs and intermediate values:

- Inputs used: `fcf_base`, `growth_rate`, `avg_historical_growth`, `discount_rate`, `terminal_growth_rate`.
- Intermediate outputs: `sum_pv_fcf`, `pv_terminal_value`, `enterprise_value`, `cash`, `debt`, `equity_value`, `shares_outstanding`.
- Final output: `intrinsic_value` (per share), `upside_pct`, plus `current_price`.

### ValuationSummary Fields (from `valuation/valuation_runner.py`)

`run_all()` embeds the DCF outputs into the summary row:

- `dcf_value` = `DCFResult.intrinsic_value`.
- `dcf_growth_rate` = `DCFResult.growth_rate`.
- `dcf_discount_rate` = `DCFResult.discount_rate`.
- `dcf_terminal_rate` = `DCFResult.terminal_growth_rate`.
- `dcf_fcf_base_m` = `DCFResult.fcf_base`.
- `dcf_error` is set if DCF failed any guard condition.

These fields are emitted to CSV in `ValuationSummary.to_dict()`.

### Forecast CSV (from `batch_process_wisesheets.py`)

`batch_process_wisesheets.py` writes a per-ticker forecast file to `output/wisesheets_forecasted/{TICKER}_forecasted.csv` with one row per forecast year and these columns:

- `ticker`
- `base_year` (last year of `fcf_history`)
- `year_index` (1..10)
- `year` (base_year + year_index)
- `fcf_forecast_m`
- `pv_fcf_m`
- `discount_factor`
- `growth_rate`
- `discount_rate`
- `terminal_growth_rate`
- `fcf_base_m`
- `terminal_value_m` (same value on every row)

This output is built from the same logic as `run_dcf()` and is intended for audit and visualization.

## Quick Field Map (Inputs -> Outputs)

Inputs (Wisesheets columns):
- `fcf_YYYY` -> `fcf_history` -> `fcf_base`, `growth_rate`, `sum_pv_fcf`, `terminal_value`, `intrinsic_value`
- `fcf_growth_rate` -> `growth_rate` (override)
- `terminal_growth_rate` -> `terminal_value`, `discount_rate` safety check
- `risk_free_rate`, `beta`, `equity_risk_premium` -> `discount_rate`
- `cash_and_equivalents`, `total_debt` -> `equity_value`
- `shares_outstanding` -> `intrinsic_value` per share
- `current_price` -> `upside_pct`

Outputs:
- Summary CSV: `dcf_value`, `dcf_growth_rate`, `dcf_discount_rate`, `dcf_terminal_rate`, `dcf_fcf_base_m`, `dcf_error`
- Forecast CSV: per-year `fcf_forecast_m` and `pv_fcf_m`, plus `terminal_value_m`

## Notes and Assumptions

- All monetary amounts for FCF, cash, debt are in millions of USD.
- Rates are decimals (0.05 for 5%).
- DCF uses a fixed explicit forecast horizon of 10 years.
- DCF is skipped if FCF is missing, shares are non-positive, or the latest FCF is non-positive.
