# Planned Changes: Wisesheets Normalized Outputs

Goal: Split dividends, cashflows, future cashflows, and comps out of `output/wisesheets_valinput` into four normalized tables:
- `output/wisesheets_dividends`
- `output/wisesheets_cashflows`
- `output/wisesheets_futurecash`
- `output/wisesheets_comps`

## Proposed Approach
1. **Define normalized schemas** for each new output table and document column definitions in this file.
   - Dividends: `ticker, year, dividend_per_share`
   - Cashflows (historical FCF): `ticker, year, fcf`
   - Future cashflows (projection inputs if present): `ticker, year, fcf` (or `period` if more appropriate)
   - Comparables: `ticker, comp_ticker, comp_name, comp_price, comp_eps`
   - Confirm units (USD vs millions) and whether `year` is calendar or fiscal.

2. **Update `data_sources/wisesheets_transformer.py` export logic**
   - Keep a slimmed `wisesheets_valinput/{TICKER}.csv` containing only non-normalized core fields.
   - Write the four normalized CSVs to their new output directories.
   - Add clear log lines describing each export.

3. **Update `data_sources/wisesheet_provider.py` loading logic**
   - When `prefer_csv` is enabled, load core fields from `wisesheets_valinput/{TICKER}.csv`.
   - Load matching rows from each normalized table and populate `StockData`:
     - `dividend_history` from dividends table
     - `fcf_history` from cashflows table
     - `comparables` from comps table
   - Add a fallback path that preserves current behavior if normalized files are missing.

4. **Update Wisesheets factory helpers**
   - `data_sources/provider_factory.py` and any helper code that assumes all data lives in `wisesheets_valinput` will be adjusted to accept the split layout.

5. **Update docs / examples**
   - Refresh any README or scripts that mention `wisesheets_valinput` as the only output (e.g., `example_wisesheets.py`, `WISESHEETS_BATCH_PROCESSING.md`).

6. **Migration notes**
   - Provide a short note on how existing `wisesheets_valinput/*.csv` files map to the normalized outputs.
   - Decide whether to keep backward compatibility indefinitely or mark it deprecated.

## Files Likely to Change
- `data_sources/wisesheets_transformer.py`
- `data_sources/wisesheet_provider.py`
- `data_sources/provider_factory.py`
- `example_wisesheets.py`
- `WISESHEETS_BATCH_PROCESSING.md`
- `README.md` (if it documents the old layout)

## Open Questions for Approval
- Confirm the exact schema for `wisesheets_futurecash`.
- Confirm whether historical cashflows should include only FCF or other cashflow metrics.
- Confirm how to order `dividend_history` (oldest-first vs newest-first) when reconstructing `StockData`.

---
If this plan looks good, I will proceed with implementation.
