# Executed validation: day-21 cash-funded reconstruction

This is a new retrospective Qlib execution experiment, run with restored prediction files and the current local provider snapshot. It does not overwrite the original 23-window statistics or certify historical model-training timestamps.

## Protocol exercised

- Last validation observation: **2024-12-31**.
- Full validation-label maturity: **2025-02-06 close**.
- Reconstruction and first execution signal: **2025-02-06**.
- Actual simulated cash-funded execution starts **2025-02-07**, ends **2025-06-30**.
- Reconstruction is run separately. Only its target stock list is transferred; no historical shares, entry prices, cash, or profits are transferred.
- Actual order signals precede their trade session. Initial purchases pay the configured commission and are included in the first daily return.

- Opening trade limits use the current open versus previous close. They do not use the same day's closing return. The original fixed 9.5% approximation is retained, rather than asserting a complete exchange/board-specific limit model.

## Portfolio and cost comparison

These are full compounded returns over this experiment's 97-session window, not averages across the historical sample.

| Portfolio | Fee multiplier | Net return | Benchmark | Compound difference | MDD including initial cash | First-day filled stocks | First-day construction cost |
|---|---:|---:|---:|---:|---:|---:|---:|
| relay | 1× | 0.3214% | 2.9140% | -2.5925 pp | -13.0370% | 39 | 92,556.71 |
| relay | 2× | -1.1886% | 2.9140% | -4.1026 pp | -13.3749% | 39 | 185,113.42 |
| relay_pcf | 1× | 3.0521% | 2.9140% | 0.1382 pp | -13.6162% | 39 | 92,558.47 |
| relay_pcf | 2× | 1.5200% | 2.9140% | -1.3940 pp | -13.7729% | 39 | 185,116.95 |

The nominal target is 40 stocks. Filled counts are observed simulation outputs, not forced target counts. Cost, return, and drawdown effects are shown together; one development window cannot establish general superiority or statistical significance.

## Input completeness

The original valuation panel has **1 missing PCF observation out of 9800 required top-100 observations**. This run explicitly permits and records the gap; it does not replace the value. The default input checker rejects gaps. Missing keys and provider-file hashes are recorded in [the run manifest](execution_2025H1/run_manifest.json). Provider updates and vendor revisions can change a new replay.

## Independent checks on the exported evidence

```bash
python tools/verify_execution_artifacts.py --run results/execution_2025H1
```

The standard-library verifier checks output SHA256 hashes, an initially empty account, order/signal date ordering, first-day purchases, construction commissions in the daily P&L, and compounded returns. It does not require Qlib or the external provider.

## Matched model ablation

The following are additional development experiments, not untouched out-of-sample evidence. Models share the same 2021-start training sample, 2024 validation period, purged training/validation boundary, 2025H1 prediction interval, 300-round cap, 30-round early stopping, and seed 1729. All use the same previous-model prediction file as the inherited reconstruction anchor. This isolates new-model differences within a common handover experiment; it is not a comparison of fully independent historical portfolio chains.

| New model | Portfolio | Fee multiplier | Net return | Benchmark difference | MDD |
|---|---|---:|---:|---:|---:|
| alpha158_unweighted | relay | 1× | 4.8717% | 1.9577 pp | -9.1091% |
| extended_unweighted | relay | 1× | 8.7078% | 5.7938 pp | -9.1429% |
| extended_weighted | relay | 1× | 10.0629% | 7.1490 pp | -8.3582% |

Training artifacts and settings: [training manifest](matched_models_2025H1/training_manifest.json), [model inventory](matched_models_2025H1/models.csv), [provider snapshot fingerprints](matched_models_2025H1/provider_manifest.json). Native LightGBM model files and the exact training runner source are preserved alongside the manifest.

The feature and weighting changes improve this particular matched window's observed net return. The weighted model also changes validation weighting and its selected stopping iteration. These observations require further periods before claiming a stable effect.

## Historical metric correction

The overlapping 2026H1 supplementary record is now reconciled from 96 daily observations: −12.58 is the summed daily excess; −12.76 pp is the compound strategy-return minus benchmark-return difference. [Recalculation and source evidence](reconciliation_2026H1/RECONCILIATION.md).

## Practical limits

These checks establish what the new implementation did. They cannot recover the old model's historical training completion time or remove historical strategy-selection bias. Broader multi-period testing and a separately frozen future evaluation remain necessary for a general performance claim.
