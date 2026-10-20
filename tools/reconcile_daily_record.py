from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Reconcile compound return difference and summed daily excess from a historical daily record.")
    parser.add_argument("--daily", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() and any(args.output.iterdir()):
        raise ValueError("Output must be empty")
    content = args.daily.read_bytes()
    rows = list(csv.DictReader(content.decode("utf-8-sig").splitlines()))
    if not rows or len({row["datetime"] for row in rows}) != len(rows):
        raise ValueError("Empty or duplicate daily records")
    rows.sort(key=lambda row: row["datetime"])
    net = [float(row["return"]) - float(row["cost"]) for row in rows]
    benchmark = [float(row["bench"]) for row in rows]
    if not all(math.isfinite(value) for value in net + benchmark):
        raise ValueError("Non-finite returns")
    portfolio_return = math.prod(1 + value for value in net) - 1
    benchmark_return = math.prod(1 + value for value in benchmark) - 1
    compound_difference = portfolio_return - benchmark_return
    daily_sum = sum(value - base for value, base in zip(net, benchmark))
    output = args.output
    output.mkdir(parents=True, exist_ok=True)
    (output / "daily.csv").write_bytes(content)
    metrics = {
        "source_name": args.daily.name, "source_sha256": hashlib.sha256(content).hexdigest(),
        "days": len(rows), "start": rows[0]["datetime"], "end": rows[-1]["datetime"],
        "portfolio_return": portfolio_return, "benchmark_return": benchmark_return,
        "compound_return_difference": compound_difference, "daily_excess_sum": daily_sum,
        "conclusion": "The source table's -12.58% is rounded summed daily excess, not compound portfolio return minus benchmark. The latter rounds to -12.76 percentage points.",
    }
    (output / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    report = f"""# 2026H1 supplementary metric reconciliation

The original supplementary row mixes two definitions. Recalculation from the bundled daily record establishes the distinction:

| Metric | Recalculated value |
|---|---:|
| Window | {metrics['start']} to {metrics['end']} |
| Trading days | {len(rows)} |
| Net portfolio return | {portfolio_return:.8%} |
| Benchmark return | {benchmark_return:.8%} |
| Compound portfolio return minus benchmark | {compound_difference * 100:.8f} pp |
| Sum of net daily return minus daily benchmark | {daily_sum * 100:.8f} pp |

The historical **−12.58** value is the daily excess sum; **−12.76 pp** is the compound return difference consistent with the presentation's main metric. The original historical report remains unchanged. This overlapping 2026H1 observation is supplementary and is not counted in the 23-window paired comparison.

This daily record was sliced from an existing relay simulation. It substantiates the arithmetic definition, not a fresh cash-funded day-21 construction or historical model-availability timestamps.

Evidence: [daily records](daily.csv), [full precision metrics and source SHA256](metrics.json).

Reproduce with Python's standard library, writing to a new empty directory:

```bash
python tools/reconcile_daily_record.py --daily results/reconciliation_2026H1/daily.csv --output .local/reconciliation_check
```
"""
    (output / "RECONCILIATION.md").write_text(report, encoding="utf-8")
    print(json.dumps(metrics))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
