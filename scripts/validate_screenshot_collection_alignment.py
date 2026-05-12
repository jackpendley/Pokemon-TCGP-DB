#!/usr/bin/env python3
"""
Validate data/current/screenshot_collection_alignment.json against:
  - data/current/collection_normalized.json (source entries, quantities)
  - data/current/screenshot_inventory.json  (expected slot count)

Delegates to the --validate mode of build_screenshot_collection_alignment.py.

Usage:
    python3 scripts/validate_screenshot_collection_alignment.py
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUILD_SCRIPT = ROOT / "scripts" / "build_screenshot_collection_alignment.py"


def main():
    result = subprocess.run(
        [sys.executable, str(BUILD_SCRIPT), "--validate"],
        check=False,
    )
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
