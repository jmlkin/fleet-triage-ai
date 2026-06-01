"""Loads and lightly validates the policy file (config/ruleset.yaml).

The engine reads thresholds and weights from a `Ruleset`, never from literals,
so the same code adapts to any org baseline by editing one YAML file.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

DEFAULT_RULESET_PATH = Path(__file__).resolve().parents[2] / "config" / "ruleset.yaml"


@dataclass
class Ruleset:
    compliance: dict
    risk_weights: dict
    role_multipliers: dict
    bands: dict

    @property
    def at_risk_threshold(self) -> int:
        return int(self.bands["at_risk_threshold"])


def load_ruleset(path: str | Path | None = None) -> Ruleset:
    p = Path(path) if path else DEFAULT_RULESET_PATH
    raw = yaml.safe_load(p.read_text(encoding="utf-8"))
    for key in ("compliance", "risk_weights", "role_multipliers", "bands"):
        if key not in raw:
            raise ValueError(f"ruleset {p} is missing required section: {key!r}")
    return Ruleset(
        compliance=raw["compliance"],
        risk_weights=raw["risk_weights"],
        role_multipliers=raw["role_multipliers"],
        bands=raw["bands"],
    )
