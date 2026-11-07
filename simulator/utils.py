"""Strict, portable JSON export."""
import json
from pathlib import Path


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, allow_nan=False, separators=(',', ':')), encoding='utf-8')
