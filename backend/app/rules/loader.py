from __future__ import annotations

from pathlib import Path

import yaml

from ..paths import repo_root
from .schema import CountryRules


def load_country_rules(country: str) -> CountryRules:
    # NOTE: do not cache rule packs in-process.
    # During POC/dev you will edit YAML frequently; caching causes “Required documents: []”
    # even after updating rule files, unless the server is restarted.
    root = repo_root()
    p = root / "rules" / "countries" / country.upper() / "rules.yml"
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    return CountryRules.model_validate(data)

