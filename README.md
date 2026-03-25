# Value Engine v2 — Python dependencies
# Install with:  pip install -r requirements.txt

# ── Data fetching ──────────────────────────────────────────────────────────
yfinance>=0.2.40           # Yahoo Finance provider

# ── Excel I/O ─────────────────────────────────────────────────────────────
openpyxl>=3.1.0            # Wisesheets provider + template generator

# ── Parquet output (optional — only needed if output.format = "parquet") ──
pandas>=2.0.0
pyarrow>=14.0.0

# ── Standard library only — no extra installs needed for:
# csv, statistics, math, dataclasses, pathlib, datetime, abc, typing