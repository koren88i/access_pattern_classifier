from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
SPECS_DIR = REPO_ROOT / "specs"


def load_spec(name: str) -> dict[str, Any]:
    """Load a YAML spec by file name from the repository specs directory."""
    with (SPECS_DIR / name).open("r", encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle)
    return loaded or {}

