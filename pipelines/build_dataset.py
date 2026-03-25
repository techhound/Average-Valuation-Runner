"""
pipelines/build_dataset.py
============================
Main pipeline.  Pulls data â†’ runs valuations â†’ writes output.

Run directly::

    python pipelines/build_dataset.py

Or call from your own script::

    from pipelines.build_dataset import run_pipeline
    run_pipeline(tickers=["MSFT", "AAPL"])
"""

from __future__ import annotations

import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

# Ensure the project root is importable regardless of cwd
_ROOT = Path(__file__).parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from config.settings import SETTINGS
from data_sources.provider_factory import get_provider
from valuation.valuation_runner import run_batch
from storage.writer import write_results


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

def run_pipeline(
    tickers: Optional[list[str]] = None,
    source: Optional[str] = None,
    output_dir: Optional[str] = None,
    output_fmt: Optional[str] = None,
    append: Optional[bool] = None,
    margin_of_safety: Optional[float] = None,
    verbose: bool = True,
) -> Path:
    """
    Full end-to-end pipeline:  fetch â†’ value â†’ write.

    Parameters override ``SETTINGS`` if provided; otherwise ``SETTINGS``
    values are used.

    Returns
    -------
    Path
        Path of the written output file.
    """
    t_start = time.perf_counter()

    # Resolve config (kwargs > settings)
    _tickers   = tickers          or SETTINGS["tickers"]
    _source    = source           or SETTINGS["data_source"]
    _out_dir   = output_dir       or SETTINGS["output"]["directory"]
    _fmt       = output_fmt       or SETTINGS["output"]["format"]
    _append    = append           if append is not None else SETTINGS["output"]["append"]
    _mos       = margin_of_safety if margin_of_safety is not None else SETTINGS["margin_of_safety"]

    model_flags = SETTINGS.get("models", {})

    if verbose:
        print("=" * 60)
        print(f"  Value Engine  |  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  Source        :  {_source}")
        print(f"  Tickers       :  {', '.join(_tickers)}")
        print(f"  Output dir    :  {_out_dir}")
        print(f"  Format        :  {_fmt}")
        print("=" * 60)

    # â”€â”€ 1. Fetch data â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    if verbose:
        print("\n[1/3]  Fetching data â€¦")

    provider = get_provider(source=_source)
    stock_data_list = provider.fetch_many(_tickers)

    if not stock_data_list:
        raise RuntimeError("No data was fetched â€” check your tickers and data source config.")

    if verbose:
        print(f"       Fetched {len(stock_data_list)} / {len(_tickers)} tickers successfully.")

    # â”€â”€ 2. Run valuations â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    if verbose:
        print("\n[2/3]  Running valuations â€¦")

    summaries = run_batch(
        stock_data_list,
        margin_of_safety=_mos,
        run_dcf_model       = model_flags.get("dcf",       True),
        run_graham_model    = model_flags.get("graham",    True),
        run_multiples_model = model_flags.get("multiples", True),
        run_ddm_model       = model_flags.get("ddm",       True),
    )

    # â”€â”€ 3. Write output â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    if verbose:
        print(f"\n[3/3]  Writing {_fmt.upper()} output â€¦")

    out_path = write_results(
        summaries,
        output_dir=_out_dir,
        fmt=_fmt,
        append=_append,
    )

    elapsed = time.perf_counter() - t_start
    if verbose:
        print(f"\n  Done in {elapsed:.1f}s\n")
        _print_summary_table(summaries)

    return out_path


# ---------------------------------------------------------------------------
# Pretty-print helper
# ---------------------------------------------------------------------------

def _print_summary_table(summaries) -> None:
    """Print a compact results table to stdout."""
    hdr = f"{'Ticker':<8} {'Price':>8} {'DCF':>8} {'Graham':>8} {'Mult.':>8} {'DDM':>8} {'IV Avg':>9} {'Signal':>6}"
    sep = "-" * len(hdr)
    print(sep)
    print(hdr)
    print(sep)
    for s in summaries:
        def _f(v):
            return f"{v:8.2f}" if v is not None else "     N/A"
        row = (
            f"{s.ticker:<8} {s.current_price:>8.2f}"
            f" {_f(s.dcf_value)}"
            f" {_f(s.graham_value)}"
            f" {_f(s.multiples_value)}"
            f" {_f(s.ddm_value)}"
            f" {_f(s.intrinsic_value_avg)}"
            f" {s.signal or '':>6}"
        )
        print(row)
    print(sep)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Value Engine â€” build valuation dataset")
    parser.add_argument("--tickers",  nargs="+", help="Override tickers list")
    parser.add_argument("--source",   help="Data source: yahoo | wisesheets | <custom>")
    parser.add_argument("--format",   dest="fmt", choices=["csv", "parquet"], help="Output format")
    parser.add_argument("--output",   dest="output_dir", help="Output directory")
    parser.add_argument("--append",   action="store_true", help="Append to existing file")
    parser.add_argument("--mos",      type=float, dest="margin_of_safety", help="Margin of safety (0â€“1)")
    args = parser.parse_args()

    run_pipeline(
        tickers          = args.tickers,
        source           = args.source,
        output_dir       = args.output_dir,
        output_fmt       = args.fmt,
        append           = args.append or None,
        margin_of_safety = args.margin_of_safety,
    )
