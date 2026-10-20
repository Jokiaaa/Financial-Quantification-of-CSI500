# 2026H1 supplementary metric reconciliation

The original supplementary row mixes two definitions. Recalculation from the bundled daily record establishes the distinction:

| Metric | Recalculated value |
|---|---:|
| Window | 2026-02-02 to 2026-06-30 |
| Trading days | 96 |
| Net portfolio return | -4.86439438% |
| Benchmark return | 7.89512021% |
| Compound portfolio return minus benchmark | -12.75951459 pp |
| Sum of net daily return minus daily benchmark | -12.57916114 pp |

The historical **−12.58** value is the daily excess sum; **−12.76 pp** is the compound return difference consistent with the presentation's main metric. The original historical report remains unchanged. This overlapping 2026H1 observation is supplementary and is not counted in the 23-window paired comparison.

This daily record was sliced from an existing relay simulation. It substantiates the arithmetic definition, not a fresh cash-funded day-21 construction or historical model-availability timestamps.

Evidence: [daily records](daily.csv), [full precision metrics and source SHA256](metrics.json).

Reproduce with Python's standard library, writing to a new empty directory:

```bash
python tools/reconcile_daily_record.py --daily results/reconciliation_2026H1/daily.csv --output .local/reconciliation_check
```
