#!/usr/bin/env python
"""
Transform raw Wisesheets files into ValuationData format.

Usage:
  python transform_wisesheets.py MSFT.xlsx
  python transform_wisesheets.py data/wisesheets/MSFT.xlsx
"""

import sys
from pathlib import Path

from data_sources.wisesheets_transformer import transform_raw_wisesheets


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python transform_wisesheets.py <input_file> [output_file]")
        print("Example: python transform_wisesheets.py data/wisesheets/MSFT.xlsx")
        sys.exit(1)
    
    input_file = Path(sys.argv[1])
    output_file = Path(sys.argv[2]) if len(sys.argv) > 2 else input_file
    
    try:
        result = transform_raw_wisesheets(
            input_file,
            output_file,
        )
        print(f"\n✓ Transformation complete: {result}")
        print(f"  You can now load this with: get_wisesheets_provider()")
        
    except Exception as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
