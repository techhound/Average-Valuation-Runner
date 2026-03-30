# Architecture

This document describes how the valuation engine is structured, how data flows
through it, and which inputs/outputs and variables drive the results. It only
references the files needed to understand the system.

## Overview

The project is a three‑stage pipeline:
1. Fetch canonical stock data from a provider (Yahoo Finance, Wisesheets, or a custom provider).
2. Run valuation models (DCF, Graham, Multiples, DDM) on that canonical data.
3. Write a flat output dataset (CSV or Parquet) for Power BI or downstream use.

The primary entry points are:
- `main.py` (CLI convenience wrapper).
- `pipelines/build_dataset.py` (the main pipeline module).
- `batch_process_wisesheets.py` (batch Wisesheets processing with extra outputs for Power BI).

## Primary Entry Points

**`main.py`**
- CLI entry with flags for tickers, data source, output format, output directory, append mode, and margin of safety.
- Delegates to `pipelines/build_dataset.py` via `run_pipeline`.

**`pipelines/build_dataset.py`**
- Orchestrates the end‑to‑end pipeline:
  - `get_provider(...)` → fetch data (`StockData`).
  - `run_batch(...)` → compute valuations (`ValuationSummary`).
  - `write_results(...)` → persist output.

**`batch_process_wisesheets.py`**
- Specialized bulk workflow for Wisesheets Excel files in `data/wisesheets/`.
- Produces per‑ticker valuation CSVs and additional normalized outputs (cashflows, dividends, forecasts, and assumptions) to support Power BI folder ingestion.

## Configuration and Runtime Inputs

**`config/settings.py`**
- Global defaults used by the pipeline when CLI overrides are not provided.
- Key settings:
  - `TICKERS`: default symbols to run.
  - `DATA_SOURCE`: `"yahoo"` or `"wisesheets"` (or custom provider key).
  - `OUTPUT_DIR`, `OUTPUT_FORMAT`, `APPEND_TO_OUTPUT`.
  - `MARGIN_OF_SAFETY`.
  - `MODELS`: toggle individual valuation models.

**Runtime inputs**
- CLI flags in `main.py` and `pipelines/build_dataset.py` override defaults.
- Wisesheets mode requires `.xlsx` files in `data/wisesheets/`.
- Yahoo mode uses live data via `yfinance` (network required).

## Canonical Data Model

**`data_sources/base.py`**
- Defines the system’s canonical record: `StockData`.
- All providers must return `StockData` so valuation code is provider‑agnostic.

Key fields in `StockData` (inputs to models):
- Identity: `ticker`, `company_name`, `sector`, `industry`.
- Market: `current_price`, `market_cap`, `shares_outstanding`.
- Earnings: `eps_ttm`, `eps_growth_rate`.
- Cashflow: `fcf_history`, `fcf_growth_rate`.
- DCF/CAPM: `beta`, `risk_free_rate`, `equity_risk_premium`, `terminal_growth_rate`.
- Balance sheet: `cash_and_equivalents`, `total_debt`.
- Dividends: `dividend_history`, `dividend_growth_rate`, `wacc`.
- Multiples: `comparables` (list of `ComparableCompany`).
- Graham: `aaa_bond_yield`.
- Metadata: `data_source`, `last_updated`.

Two important computed helpers:
- `validate()` emits warnings for missing/invalid inputs.
- `capm_discount_rate()` returns `risk_free_rate + beta * equity_risk_premium`.

## Data Providers (Fetch Stage)

**`data_sources/provider_factory.py`**
- Maps a source name to a provider instance.
- Built‑ins: `"yahoo"` and `"wisesheets"`.
- Custom providers can be registered in `_custom_registry()`.

**`data_sources/yahoo_provider.py`**
- Uses `yfinance` to pull:
  - Price, market cap, shares, EPS, sector/industry.
  - FCF history from cashflow statements.
  - Balance sheet cash/debt.
  - Dividend history.
  - Beta.
- Returns a fully populated `StockData`.

**`data_sources/wisesheet_provider.py`**
- Reads a Wisesheets workbook, or prefers the normalized CSV outputs if present.
- Extracts:
  - Core valuation inputs from `ValuationData`.
  - Historical FCF, dividends, and comparables from normalized CSVs.
- Returns `StockData` with the canonical fields populated.

**`data_sources/wisesheets_transformer.py`**
- Preprocesses raw Wisesheets Excel files into:
  - `output/wisesheets_valinput/*_valinput.csv` (core inputs).
  - `output/wisesheets_cashflows/*_cashflows.csv`.
  - `output/wisesheets_dividends/*_dividends.csv`.
  - `output/wisesheets_comps/*_comps.csv`.
- This is invoked automatically by `get_wisesheets_provider(...)` when raw sheets are detected.

## Valuation Engine (Compute Stage)

**`valuation/valuation_runner.py`**
- `run_all(...)` executes each enabled model and aggregates results.
- `ValuationSummary` is the flat output record written to disk.
- Outputs include:
  - Per‑model values and errors (`dcf_value`, `graham_value`, etc).
  - Aggregations (`intrinsic_value_avg`, `intrinsic_value_median`).
  - Decision outputs (`acceptable_buy_price`, `signal`, `upside_to_intrinsic_pct`).
  - Model assumptions used (for auditability).

**Model inputs and derived values**
- `margin_of_safety` is applied to `intrinsic_value_avg` to compute `acceptable_buy_price`.
- `signal` is computed from `current_price` relative to intrinsic value and buy price.

**`valuation/models/dcf.py`**
- Uses `fcf_history`, `fcf_growth_rate`, CAPM discount rate, and `terminal_growth_rate`.
- Computes a 10‑year forecast plus terminal value, then equity value per share.

**`valuation/models/graham.py`**
- Uses `eps_ttm`, `eps_growth_rate`, and `aaa_bond_yield`.
- Runs revised Graham formula to produce intrinsic value.

**`valuation/models/multiples.py`**
- Uses `comparables` and `eps_ttm`.
- Computes comp P/E averages/medians and applies to target EPS.

**`valuation/models/ddm.py`**
- Uses `dividend_history`, `dividend_growth_rate`, and `wacc` (or CAPM if `wacc` is 0).
- Applies Gordon Growth Model.

## Output (Write Stage)

**`storage/writer.py`**
- Persists `ValuationSummary` rows to:
  - `output/valuation_results.csv` or `output/valuation_results.parquet`.
  - `output/valuation_history.csv` when append mode is enabled.

Key output variables include:
- Identity and market data fields.
- Per‑model valuation outputs.
- Aggregated intrinsic values.
- Decision fields (`margin_of_safety`, `acceptable_buy_price`, `signal`).
- Model assumptions for traceability.

## Batch Wisesheets Workflow

**`batch_process_wisesheets.py`**
- Iterates all `.xlsx` files in `data/wisesheets/`.
- For each ticker:
  - Loads via `get_wisesheets_provider(...)` (auto‑transform if needed).
  - Runs `run_all(...)`.
  - Writes per‑ticker results: `output/wisesheets_results/{TICKER}_valuation.csv`.
  - Writes supplemental Power BI datasets:
    - `output/wisesheets_forecasted/{TICKER}_forecasted.csv` (DCF forecast rows).
    - `output/wisesheets_cashflows/{TICKER}_cashflows.csv`.
    - `output/wisesheets_dividends/{TICKER}_dividends.csv`.
    - `output/computed_assumptions/{TICKER}_assumptions.csv`.

## End‑to‑End Data Flow (Default Pipeline)

1. **Entry**: `main.py` → `run_pipeline(...)` in `pipelines/build_dataset.py`.
2. **Fetch**: `get_provider(...)` in `data_sources/provider_factory.py`.
3. **Canonicalize**: Provider returns `StockData` (`data_sources/base.py`).
4. **Compute**: `run_batch(...)` → `run_all(...)` (`valuation/valuation_runner.py`).
5. **Model Outputs**: DCF, Graham, Multiples, DDM compute intrinsic values.
6. **Aggregate**: `ValuationSummary` includes metrics + assumptions.
7. **Persist**: `storage/writer.py` writes CSV or Parquet.

## Files Referenced

- `main.py`
- `pipelines/build_dataset.py`
- `config/settings.py`
- `data_sources/base.py`
- `data_sources/provider_factory.py`
- `data_sources/yahoo_provider.py`
- `data_sources/wisesheet_provider.py`
- `data_sources/wisesheets_transformer.py`
- `valuation/valuation_runner.py`
- `valuation/models/dcf.py`
- `valuation/models/graham.py`
- `valuation/models/multiples.py`
- `valuation/models/ddm.py`
- `storage/writer.py`
- `batch_process_wisesheets.py`
