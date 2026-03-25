"""
main.py
=======
Convenience entry point.  Equivalent to running:
 
    python pipelines/build_dataset.py [args]
 
Usage examples
--------------
  # Run with defaults from settings.py
  python main.py
 
  # Override tickers and source at runtime
  python main.py --tickers MSFT AAPL NVDA --source yahoo
 
  # Use Wisesheets workbook, write Parquet
  python main.py --source wisesheets --format parquet
 
  # Append results to a history log
  python main.py --append
 
  # Full override
  python main.py --tickers MSFT GOOG --source yahoo --format csv --mos 0.15 --output ./output
"""
 
import sys
from pathlib import Path
 
# Make sure the project root is on sys.path
sys.path.insert(0, str(Path(__file__).parent))
 
from pipelines.build_dataset import run_pipeline
 
if __name__ == "__main__":
    import argparse
 
    parser = argparse.ArgumentParser(
        description="Value Engine v2 — Fetch · Value · Output",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--tickers",  nargs="+", metavar="TICKER",
                        help="Space-separated list of tickers (overrides settings.py)")
    parser.add_argument("--source",   metavar="SOURCE",
                        help="Data source: yahoo | wisesheets | <custom>")
    parser.add_argument("--format",   dest="fmt", choices=["csv", "parquet"],
                        help="Output file format (default: settings.py)")
    parser.add_argument("--output",   dest="output_dir", metavar="DIR",
                        help="Output directory (default: settings.py)")
    parser.add_argument("--append",   action="store_true",
                        help="Append to existing output file instead of overwriting")
    parser.add_argument("--mos",      type=float, dest="margin_of_safety",
                        metavar="FLOAT",
                        help="Margin of safety as a decimal, e.g. 0.15 for 15%%")
    args = parser.parse_args()
 
    out = run_pipeline(
        tickers          = args.tickers,
        source           = args.source,
        output_dir       = args.output_dir,
        output_fmt       = args.fmt,
        append           = args.append or None,
        margin_of_safety = args.margin_of_safety,
    )
    print(f"\n  Output file: {out}\n")
