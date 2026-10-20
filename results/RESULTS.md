# Historical results: paired delayed evaluation windows

![Window excess returns](../assets/delay20_excess.svg)

## Scope and provenance

Calculated from rounded observations in sections 15.2 and 15.4 of [the original research record](../回测结果.md). This reproduces reported results, not model training or order execution.

The main comparison has 23 matching windows: 2015H1–2025H2 plus 2026YTD (through June 16). Each begins on its 21st trading-day record. The additional PCF-only 2026H1 observation is supplementary and is never counted alongside overlapping 2026YTD.

## Descriptive summary

Returns and drawdowns are percentages; excess and differences are percentage points. Each window has equal weight, including shorter YTD. None of these averages is an annualized or continuous-account metric.

| Sample | Strategy | Windows | Mean return | Mean reported excess | Median reported excess | Mean within-window MDD | Positive excess windows |
|---|---|---:|---:|---:|---:|---:|---:|
| All paired windows | `relay_tie` | 23 | 9.34% | 4.90 pp | 6.46 pp | -14.20% | 18/23 |
| All paired windows | `relay_tie_pcf` | 23 | 10.21% | 5.77 pp | 7.37 pp | -13.89% | 20/23 |
| Excluding 2015 | `relay_tie` | 21 | 6.87% | 4.75 pp | 6.46 pp | -12.52% | 16/21 |
| Excluding 2015 | `relay_tie_pcf` | 21 | 7.89% | 5.77 pp | 7.37 pp | -12.19% | 18/21 |

Across paired windows, PCF changes mean window return by **+0.87 pp**, with higher return in **16/23** windows and equal return in **2/23**. This is descriptive, not a significance test.

## Window observations

| Window | Evaluation dates | Days | Benchmark | Relay | Relay + PCF | Relay excess | PCF excess | PCF − relay return |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 2015H1 | 2015-02-02 至 2015-06-30 | 99 | 58.11% | 65.49% | 65.49% | 7.37 pp | 7.37 pp | +0.00 pp |
| 2015H2 | 2015-07-29 至 2015-12-31 | 105 | -0.42% | 5.10% | 3.69% | 5.52 pp | 4.11 pp | -1.41 pp |
| 2016H1 | 2016-02-01 至 2016-06-30 | 100 | 11.96% | 19.34% | 19.34% | 7.37 pp | 7.37 pp | +0.00 pp |
| 2016H2 | 2016-07-29 至 2016-12-30 | 104 | 0.33% | 8.70% | 9.21% | 8.38 pp | 8.88 pp | +0.51 pp |
| 2017H1 | 2017-02-07 至 2017-06-30 | 99 | -1.93% | 3.18% | 3.88% | 5.12 pp | 5.82 pp | +0.70 pp |
| 2017H2 | 2017-07-31 至 2017-12-29 | 105 | 0.57% | 11.10% | 8.75% | 10.53 pp | 8.18 pp | -2.35 pp |
| 2018H1 | 2018-01-30 至 2018-06-29 | 99 | -17.31% | -10.32% | -9.92% | 6.99 pp | 7.38 pp | +0.40 pp |
| 2018H2 | 2018-07-30 至 2018-12-28 | 104 | -20.60% | -11.23% | -9.14% | 9.37 pp | 11.46 pp | +2.09 pp |
| 2019H1 | 2019-01-30 至 2019-06-28 | 98 | 16.36% | 20.52% | 25.88% | 4.15 pp | 9.52 pp | +5.36 pp |
| 2019H2 | 2019-07-29 至 2019-12-31 | 106 | 7.54% | 3.44% | 3.11% | -4.11 pp | -4.44 pp | -0.33 pp |
| 2020H1 | 2020-02-07 至 2020-06-30 | 97 | 11.01% | 18.18% | 20.38% | 7.17 pp | 9.38 pp | +2.20 pp |
| 2020H2 | 2020-07-29 至 2020-12-31 | 106 | 0.12% | -0.22% | 4.02% | -0.34 pp | 3.90 pp | +4.24 pp |
| 2021H1 | 2021-02-01 至 2021-06-30 | 98 | 7.28% | 14.25% | 14.51% | 6.97 pp | 7.23 pp | +0.26 pp |
| 2021H2 | 2021-07-29 至 2021-12-31 | 105 | 11.14% | 20.13% | 24.60% | 8.99 pp | 13.47 pp | +4.47 pp |
| 2022H1 | 2022-02-08 至 2022-06-30 | 97 | -3.33% | 3.58% | 4.41% | 6.91 pp | 7.74 pp | +0.83 pp |
| 2022H2 | 2022-07-29 至 2022-12-30 | 105 | -7.62% | -6.10% | -5.86% | 1.52 pp | 1.76 pp | +0.24 pp |
| 2023H1 | 2023-02-07 至 2023-06-30 | 98 | -4.82% | 1.52% | 0.83% | 6.34 pp | 5.65 pp | -0.69 pp |
| 2023H2 | 2023-07-31 至 2023-12-29 | 104 | -10.16% | -12.14% | -11.48% | -1.98 pp | -1.32 pp | +0.66 pp |
| 2024H1 | 2024-01-30 至 2024-06-28 | 97 | 0.30% | 6.06% | 7.85% | 5.76 pp | 7.55 pp | +1.79 pp |
| 2024H2 | 2024-07-29 至 2024-12-31 | 105 | 20.89% | 32.62% | 30.97% | 11.73 pp | 10.08 pp | -1.65 pp |
| 2025H1 | 2025-02-07 至 2025-06-30 | 97 | 2.91% | 2.60% | 4.56% | -0.32 pp | 1.64 pp | +1.96 pp |
| 2025H2 | 2025-07-29 至 2025-12-31 | 106 | 18.06% | 24.53% | 25.00% | 6.46 pp | 6.93 pp | +0.47 pp |
| 2026YTD | 2026-02-02 至 2026-06-16 | 87 | 1.64% | -5.52% | -5.28% | -7.17 pp | -6.92 pp | +0.24 pp |

## Supplementary observation

- `relay_tie_pcf`, 2026H1, 2026-02-02 至 2026-06-30: return -4.86%, excess -12.58 pp, within-window MDD -13.30%. Excluded from paired summary.
- Resolved metric mismatch: displayed return minus benchmark is -12.76 pp, whereas the original reported field is -12.58. Daily records show the latter is summed daily excess, not compound return difference. See [the full-precision reconciliation](reconciliation_2026H1/RECONCILIATION.md). Original source values are preserved.

## Metric and execution boundaries

- Excess is the source's difference between compounded portfolio and benchmark returns. Small subtraction discrepancies arise from rounding.
- Averaged within-window drawdowns are not the maximum drawdown of an investable multi-year portfolio.
- The source describes Qlib costs and net portfolio returns. Fees and day-21 initial construction costs were not independently reconstructed here.
- The author's day-21 construction procedure and the report's delayed-window calculation are distinguished in [the timing protocol](../docs/METHODOLOGY.md). Tables alone do not establish execution timing.
- Source summary cells can differ from means of rounded rows. This page always computes from extracted observations; the original is unchanged.
- No full-period CAGR, Sharpe, significance, or live-performance claim is inferred.

## Machine-readable artifacts

- [Paired rows](delay20_windows.csv)
- [Supplementary rows](supplementary_windows.csv)
- [Source hash and metadata](provenance.json)

Rebuild: `python tools/build_showcase.py`. Verify: `python tools/build_showcase.py --check`.
