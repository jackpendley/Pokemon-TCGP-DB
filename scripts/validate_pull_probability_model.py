#!/usr/bin/env python3
"""Standalone validator for pull_probability_model.json. Delegates to the builder --validate mode."""
import subprocess
import sys

result = subprocess.run(
    [sys.executable, "scripts/build_pull_probability_model.py", "--validate"],
    capture_output=False,
)
sys.exit(result.returncode)
