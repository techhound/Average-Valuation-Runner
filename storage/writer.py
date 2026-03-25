"""
storage/writer.py
==================
Writes valuation results to flat files (CSV or Parquet) for consumption by
Power BI.

Power BI integration
--------------------
After each pipeline run, point Power BI's data source at the output file:

  CSV     â€” Home â†’ Get Data â†’ Text/CSV â†’ select valuation_results.csv
  Parquet â€” Home â†’ Get Data â†’ Parquet  â†’ select valuation_results.parquet

Enable "scheduled refresh" in Power BI Desktop / Service so the report
updates automatically whenever the Python pipeline re-runs.

File naming
-----------
  valuation_results.csv     (or .parquet)   â€” latest run (overwrite mode)
  valuation_results_history.csv             â€” append mode: full run log
"""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import Literal

from valuation.valuation_runner import ValuationSummary


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def write_results(
    summaries: list[ValuationSummary],
    output_dir: str | Path = "output",
    fmt: Literal["csv", "parquet"] = "csv",
    append: bool = False,
) -> Path:
    """
    Persist valuation summaries to disk.

    Parameters
    ----------
    summaries : list[ValuationSummary]
        Results from ``run_batch()``.
    output_dir : str | Path
        Directory to write into (created if absent).
    fmt : "csv" | "parquet"
        Output file format.
    append : bool
        If True, append rows to an existing file (builds a history log).
        If False (default), overwrite with the current run only.

    Returns
    -------
    Path
        Absolute path of the written file.
    """
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    suffix    = "history" if append else "results"
    filename  = f"valuation_{suffix}.{fmt}"
    out_path  = out_dir / filename

    rows = [s.to_dict() for s in summaries]

    if fmt == "csv":
        return _write_csv(rows, out_path, append)
    elif fmt == "parquet":
        return _write_parquet(rows, out_path, append)
    else:
        raise ValueError(f"Unsupported format '{fmt}'.  Choose 'csv' or 'parquet'.")


# ---------------------------------------------------------------------------
# CSV
# ---------------------------------------------------------------------------

def _write_csv(
    rows: list[dict],
    path: Path,
    append: bool,
) -> Path:
    if not rows:
        print("  âš   No rows to write.")
        return path

    fieldnames = list(rows[0].keys())
    mode       = "a" if (append and path.exists()) else "w"
    write_header = not (append and path.exists())

    with open(path, mode, newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        if write_header:
            writer.writeheader()
        writer.writerows(rows)

    print(f"  âœ“  CSV written â†’ {path}  ({len(rows)} rows)")
    return path.resolve()


# ---------------------------------------------------------------------------
# Parquet
# ---------------------------------------------------------------------------

def _write_parquet(
    rows: list[dict],
    path: Path,
    append: bool,
) -> Path:
    try:
        import pandas as pd
    except ImportError as exc:
        raise ImportError(
            "pandas is required for Parquet output.  "
            "Install it with: pip install pandas pyarrow"
        ) from exc

    df_new = pd.DataFrame(rows)

    if append and path.exists():
        df_existing = pd.read_parquet(path)
        df_combined = pd.concat([df_existing, df_new], ignore_index=True)
        df_combined.to_parquet(path, index=False)
    else:
        df_new.to_parquet(path, index=False)

    print(f"  âœ“  Parquet written â†’ {path}  ({len(rows)} rows)")
    return path.resolve()
