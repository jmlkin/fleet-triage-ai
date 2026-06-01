"""Regenerate the committed synthetic fleet (data/fleet.json).

    python scripts/generate_fleet.py [--count 200] [--seed 1337]

Deterministic: the same seed always produces byte-identical data, so the
committed fleet is reproducible. This is a thin wrapper over
`fleet_triage.generator` (the same code the `fleet-triage generate-data`
command uses) so there is one generator, not two.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fleet_triage.generator import write  # noqa: E402

DEFAULT_OUT = Path(__file__).resolve().parents[1] / "data" / "fleet.json"


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate the synthetic fleet.")
    ap.add_argument("--count", type=int, default=200)
    ap.add_argument("--seed", type=int, default=1337)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    n = write(args.out, count=args.count, seed=args.seed)
    print(f"Wrote {n} synthetic endpoints to {args.out}")


if __name__ == "__main__":
    main()
