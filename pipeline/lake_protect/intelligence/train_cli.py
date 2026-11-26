"""CLI for offline, asset-group-held-out model training."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .training import train_model


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True, help="CSV of independently field-verified examples.")
    parser.add_argument("--artifact", required=True, help="Output path for the joblib model artifact.")
    parser.add_argument("--report", required=True, help="Output path for the JSON model card/evaluation.")
    parser.add_argument("--dataset-ref", default=None, help="Stable dataset version or provenance reference.")
    args = parser.parse_args()
    result = train_model(args.dataset, args.artifact, dataset_ref=args.dataset_ref)
    Path(args.report).parent.mkdir(parents=True, exist_ok=True)
    Path(args.report).write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
