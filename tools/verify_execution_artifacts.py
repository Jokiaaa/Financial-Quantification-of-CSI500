from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def verify_run(directory: Path) -> dict:
    manifest = json.loads((directory / "run_manifest.json").read_text(encoding="utf-8"))
    if not manifest.get("output_hashes"):
        raise ValueError("Incomplete run: output hashes missing")
    for name, expected in manifest["output_hashes"].items():
        path = (directory / name).resolve()
        if not path.is_relative_to(directory.resolve()):
            raise ValueError("Output hash path escapes run directory")
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError(f"Changed output: {name}")
    counts = []
    for metric in read_csv(directory / "metrics.csv"):
        variant = f"{metric['variant']}_cost{float(metric['cost_multiple']):g}"
        destination = directory / variant
        audit = json.loads((destination / "execution_audit.json").read_text(encoding="utf-8"))
        orders = read_csv(destination / "orders.csv")
        trades = read_csv(destination / "trades.csv")
        daily = read_csv(destination / "daily.csv")
        first_date = manifest["dates"]["first_actual_trade_date"]
        if audit["initial_positions"] or audit["pre_start_orders"]:
            raise ValueError(f"Invalid initial account: {variant}")
        if not orders or any(order["date"] < first_date or order["signal_date"] >= order["date"] for order in orders):
            raise ValueError(f"Invalid signal/order timing: {variant}")
        first_trades = [trade for trade in trades if trade["date"] == first_date and float(trade["filled_amount"]) > 0]
        if not first_trades or any(int(trade["direction"]) != 1 for trade in first_trades):
            raise ValueError(f"First cash-funded construction not observed: {variant}")
        first_cost = sum(float(trade["trade_cost"]) for trade in first_trades)
        if not math.isclose(first_cost, audit["first_day_construction_cost"], abs_tol=1e-7):
            raise ValueError(f"Construction fee mismatch: {variant}")
        if not math.isclose(float(daily[0]["cost"]) * audit["initial_cash"], first_cost, abs_tol=1e-5):
            raise ValueError(f"Construction cost absent from daily P&L: {variant}")
        total = math.prod(1 + float(row["return"]) - float(row["cost"]) for row in daily) - 1
        if not math.isclose(total, float(metric["total_return"]), abs_tol=1e-10):
            raise ValueError(f"Daily return aggregation mismatch: {variant}")
        counts.append({"variant": variant, "orders": len(orders), "trade_records": len(trades), "first_day_filled_stocks": len(first_trades), "construction_cost": first_cost})
    return {"verified": True, "kind": manifest["kind"], "variants": counts, "historical_training_timestamps_verified": manifest["historical_training_timestamps_verified"]}


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify exported execution evidence without Qlib or market-data access.")
    parser.add_argument("--run", type=Path, required=True)
    arguments = parser.parse_args()
    print(json.dumps(verify_run(arguments.run), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
