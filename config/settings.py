"""
config/settings.py
==================
Global configuration and default settings for the Value Engine.

These settings can be overridden at runtime via command-line arguments.
"""

from __future__ import annotations

from pathlib import Path

# Default tickers to analyze
TICKERS = ["AAPL", "MSFT", "GOOGL"]

# Default data source ("yahoo", "wisesheets", or custom provider name)
DATA_SOURCE = "yahoo"

# Output directory and format
OUTPUT_DIR = Path(__file__).parent.parent / "output"
OUTPUT_FORMAT = "csv"  # "csv" or "parquet"
APPEND_TO_OUTPUT = False  # Append to existing output files

# Default margin of safety for valuations
MARGIN_OF_SAFETY = 0.20  # 20%

# Which valuation models to run (set to False to skip)
MODELS = {
    "dcf": True,
    "graham": True,
    "multiples": True,
    "ddm": True,
}

# ────────────────────────────────────────────────────────────────────────────
# Settings dict (used by pipeline)
# ────────────────────────────────────────────────────────────────────────────

SETTINGS = {
    "tickers": TICKERS,
    "data_source": DATA_SOURCE,
    "output": {
        "directory": str(OUTPUT_DIR),
        "format": OUTPUT_FORMAT,
        "append": APPEND_TO_OUTPUT,
    },
    "margin_of_safety": MARGIN_OF_SAFETY,
    "models": MODELS,
}
