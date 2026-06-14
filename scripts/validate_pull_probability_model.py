#!/usr/bin/env python3
"""
Validate pull_probability_model.json against its schema, then delegate
to build_pull_probability_model.py --validate for semantic checks.
"""
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _collection_io import (ROOT, REFERENCE_DIR,
                            PULL_MODEL_JSON as MODEL_JSON)

SCHEMA_JSON = REFERENCE_DIR / "pull_probability_model.schema.json"

try:
    import jsonschema
    _JSONSCHEMA_AVAILABLE = True
except ImportError:
    _JSONSCHEMA_AVAILABLE = False

if MODEL_JSON.exists() and SCHEMA_JSON.exists() and _JSONSCHEMA_AVAILABLE:
    try:
        model  = json.loads(MODEL_JSON.read_text(encoding="utf-8"))
        schema = json.loads(SCHEMA_JSON.read_text(encoding="utf-8"))
        jsonschema.validate(instance=model, schema=schema)
        print("PASS  JSON schema validation")
    except jsonschema.ValidationError as e:
        print(f"FAIL  JSON schema validation: {e.message} (path: {list(e.path)})")
        sys.exit(1)
    except Exception as e:
        print(f"WARN  Schema check failed unexpectedly: {e}", file=sys.stderr)
elif not _JSONSCHEMA_AVAILABLE:
    print("WARN  jsonschema not installed — skipping structural schema check")

result = subprocess.run(
    [sys.executable, "scripts/build_pull_probability_model.py", "--validate"],
    capture_output=False,
)
sys.exit(result.returncode)
