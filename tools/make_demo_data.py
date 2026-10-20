from __future__ import annotations

import argparse
import csv
import json
import math
import struct
from datetime import date, timedelta
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate deterministic synthetic Qlib data for an offline execution demonstration, not investment evidence.")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists() and any(output.iterdir()):
        raise ValueError("Demo output must be empty")
    provider = output / "provider"
    (provider / "calendars").mkdir(parents=True)
    (provider / "instruments").mkdir()
    calendar = []
    session = date(2024, 11, 1)
    while session <= date(2025, 7, 2):
        if session.weekday() < 5:
            calendar.append(session.isoformat())
        session += timedelta(days=1)
    (provider / "calendars" / "day.txt").write_text("\n".join(calendar) + "\n", encoding="utf-8")
    stocks = [f"SH{600000 + number:06d}" for number in range(60)]
    instruments = "".join(f"{stock}\t{calendar[0]}\t{calendar[-1]}\n" for stock in stocks)
    (provider / "instruments" / "csi500.txt").write_text(instruments, encoding="utf-8")
    (provider / "instruments" / "all.txt").write_text(instruments + f"SH000905\t{calendar[0]}\t{calendar[-1]}\n", encoding="utf-8")
    for number, stock in enumerate(stocks + ["SH000905"]):
        directory = provider / "features" / stock.lower()
        directory.mkdir(parents=True)
        closes = [(30 + number) * math.exp(0.0002 * index + 0.02 * math.sin(index / 11 + number)) for index in range(len(calendar))]
        fields = {
            "close": closes,
            "open": [close * (1 + 0.001 * math.sin(index + number)) for index, close in enumerate(closes)],
            "high": [close * 1.01 for close in closes],
            "low": [close * 0.99 for close in closes],
            "vwap": closes,
            "volume": [10000000.0] * len(calendar),
            "factor": [1.0] * len(calendar),
            "change": [0.0] + [closes[index] / closes[index - 1] - 1 for index in range(1, len(closes))],
        }
        for name, values in fields.items():
            (directory / f"{name}.day.bin").write_bytes(struct.pack(f"<{len(values) + 1}f", 0.0, *values))
    for name, predicate in (("previous", lambda day: day < "2025-01-01"), ("current", lambda day: day >= "2025-01-01")):
        with (output / f"{name}.csv").open("w", newline="", encoding="utf-8") as stream:
            writer = csv.writer(stream)
            writer.writerow(["datetime", "instrument", "score"])
            for index, day in enumerate(calendar):
                if predicate(day):
                    writer.writerows((day, stock, math.sin(number * 0.27 + index / 13)) for number, stock in enumerate(stocks))
    with (output / "valuation.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["datetime", "instrument", "pcf"])
        writer.writerows((day, stock, 5 + number % 23) for day in calendar for number, stock in enumerate(stocks))
    manifest = {
        "kind": "synthetic_offline_demo_not_financial_evidence",
        "provider_uri": "provider", "previous_prediction": "previous.csv", "current_prediction": "current.csv", "valuation": "valuation.csv",
        "period_start": "2025-01-01", "period_end": "2025-06-30", "validation_end": "2024-12-31", "wait_sessions": 20,
        "initial_cash": 1000000, "benchmark": "SH000905",
        "strategy": {"topk": 40, "n_drop": 2, "risk_degree": 0.95},
        "exchange": {"limit_threshold": 0.095, "deal_price": "open", "open_cost": 0.001, "close_cost": 0.002, "min_cost": 5},
        "cost_multiples": [1.0], "allow_missing_pcf": False,
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print("Created synthetic fixture:", output / "manifest.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
