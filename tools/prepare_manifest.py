from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Create an explicit input manifest from a research YAML and restored data paths.")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--provider", type=Path, required=True)
    parser.add_argument("--previous", type=Path, required=True)
    parser.add_argument("--current", type=Path, required=True)
    parser.add_argument("--valuation", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--allow-missing-pcf", action="store_true")
    args = parser.parse_args()
    import yaml

    cfg = yaml.safe_load(args.config.read_text(encoding="utf-8-sig"))
    portfolio = cfg["port_analysis_config"]
    strategy = portfolio["strategy"]["kwargs"]
    data = cfg["task"]["dataset"]["kwargs"]
    value = {
        "provider_uri": str(args.provider.resolve()),
        "previous_prediction": str(args.previous.resolve()),
        "current_prediction": str(args.current.resolve()),
        "valuation": str(args.valuation.resolve()),
        "period_start": str(portfolio["backtest"]["start_time"]),
        "period_end": str(portfolio["backtest"]["end_time"]),
        "validation_end": str(data["segments"]["valid"][1]),
        "wait_sessions": 20,
        "initial_cash": portfolio["backtest"]["account"],
        "benchmark": portfolio["backtest"]["benchmark"],
        "strategy": {"topk": strategy["topk"], "n_drop": strategy["n_drop"], "risk_degree": 0.95},
        "exchange": portfolio["backtest"]["exchange_kwargs"],
        "cost_multiples": [1.0, 2.0],
        "allow_missing_pcf": args.allow_missing_pcf,
    }
    if args.output.exists():
        raise ValueError("Manifest already exists; choose a new filename")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    print("Created input manifest:", args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
