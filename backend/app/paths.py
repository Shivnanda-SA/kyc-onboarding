from __future__ import annotations

from pathlib import Path


def repo_root() -> Path:
    # backend/app/paths.py -> backend/app -> backend -> repo root
    return Path(__file__).resolve().parents[2]


def backend_root() -> Path:
    return Path(__file__).resolve().parents[2]

