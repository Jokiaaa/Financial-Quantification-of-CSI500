# Methodology and information timing

## Model and target

The released handler extends Alpha158 with ten expressions describing volatility ratios, normalized price ranges, volume means, and VWAP/close relationships. The YAML target is:

```text
Ref($close, -20) / $close - 1
```

For an observation on trading day t, its full label requires the close on t+20. Calendar dates and trading-day positions must therefore be distinguished.

The model calculates an observation age in **calendar days** from the reference date. Before normalization:

```text
weight = max(0.5 ** (age_calendar_days / 378), 0.0002)
normalized_weight = weight / mean(weight)
```

The current implementation weights both training and validation samples; validation participates in LightGBM early stopping. Label availability therefore matters for model selection as well as parameter fitting.

## Author-stated delayed construction protocol

The author describes the strategy as follows:

1. At each half-year boundary, wait 20 trading days for the preceding validation labels to become observable.
2. Produce the new model after the waiting period. Generate its prediction file, including scores for the first 20 dates needed for reconstruction.
3. Splice new-model scores and the preceding model's prediction file; use the relay and rolling-holdings calculation to determine the target portfolio.
4. Start actual construction of the target 40-stock portfolio on trading day 21. The reconstructed prior holdings are a target-selection calculation, not a claim of earlier executable trading profits.

```text
Previous validation period | day 1 ........ day 20 | day 21 onward
                          | label maturity wait   | first eligible construction
                          | historical reconstruction contributes no claimed live P&L
```

Generating predictions for historical feature dates after model training is not itself future trading. Eligibility depends on when the resulting signal and all required inputs were available to the actual decision. An actual day-21 portfolio must be funded and filled at that day's executable prices, with construction costs; reconstructed historical entry prices cannot be carried into a newly funded account.

## Decision timestamp

The YAMLs specify open-price execution. A day-21 opening order must use a target finalized before that open. If label maturity requires the close of day 20, model training and target computation must complete between that close and day 21's open. Same-day close/high/low/volume information cannot determine that day's opening order. If data arrival or computation finishes later, the first eligible execution moves later accordingly.

## What the available artifacts establish

| Evidence | What it describes |
|---|---|
| Author's clarification | Twenty-day waiting, reconstruction with spliced prediction files, actual construction from day 21 |
| Original report section 15 | Statistics beginning at record 21 of an existing daily evaluation series |
| Current formal runner | Loads a `valid_end_minus20td` manifest at import time and defaults to `pred_source=purged` |
| Archived router audit | Separate investigations of information timing in exploratory routing branches |

The delayed-window statistics and the historical runner's purged-validation branch are distinct experimental definitions. Neither is silently substituted for the author's delayed-construction procedure.

## New executable construction replay

`tools/research_pipeline.py` implements a separately identified retrospective replay. It reconstructs holdings through the waiting period's last session, transfers only that target stock list, and starts a new account containing cash and no shares on session 21. The first signal is dated session 20. Initial target purchases are made through Qlib's exchange with fees and trading constraints; later decisions return to the ordinary signal. Historical share quantities, entry prices, and prior profits are never transferred into the actual account.

This precisely defines the reconstruction boundary used in the new experiment: end-of-day-20 reconstructed holdings determine the initial target. It does not use an end-of-day-21 shadow position to construct a day-21 opening order.

The [executed validation](../results/VALIDATION.md) includes the order, fill, daily-return, and position exports. It exercises the specified timing and funding mechanics. The old models' historical training completion timestamps are not recovered by this rerun and are explicitly recorded as unverified.

The new replay also changes opening trade eligibility: the original Qlib floating threshold tests the same day's `$change`, a closing return. The portable runner instead supplies explicit upper/lower limit expressions using `$open / Ref($close, 1)`. This avoids using the day's closing return to authorize an opening trade. It retains the configured fixed threshold, so differences between exchange boards, ST stocks, listing rules, and historical regulatory changes are not fully modeled. Qlib's other daily-data suspension and fill assumptions remain simulation assumptions, not proof of live execution feasibility.

## Execution manifest for a complete release

Each evaluated half-year should link the following fields to the daily order and position records:

| Field | Meaning |
|---|---|
| `validation_last_feature_date` | Last validation observation |
| `validation_last_label_available_at` | Timestamp at which its full 20-day label is available |
| `model_training_completed_at` | Model ready for inference |
| `prediction_sha256` | Exact new and old prediction artifacts |
| `signal_available_at` | Target calculation completed |
| `first_actual_order_at` | Actual construction timestamp, after all required information |
| `initial_cash`, `initial_positions` | Actual funded account state, distinct from reconstructed target state |
| `construction_cost`, `execution_price` | Actual initial execution assumptions |
| `evaluation_start`, `evaluation_end` | Explicit statistics window |
| `variant`, `data_snapshot`, `config_sha256` | Reproducible experiment identity |

This manifest documents the author's design precisely; it does not require a different model or trading strategy.

## PCF and portfolio rules

The base portfolio targets 40 stocks with `n_drop=2`. This parameter is a strategy setting, not a guarantee that exactly two stocks trade on every date under all constraints. Ties are stabilized using instrument ordering within exactly equal scores.

The PCF overlay examines raw ranks 36–40 and demotes expensive candidates above the top-100 pool's 90th percentile. Valuation inputs are aligned with a one-trading-day lag. That computational lag is separate from verifying the provider's original publication timestamps and subsequent revisions. Risk-state branches also require their own lag and execution checks.

## Metric convention

For each reported delayed window:

```text
portfolio_return = product(1 + net_daily_return) - 1
benchmark_return = product(1 + daily_benchmark_return) - 1
window_excess_pp = 100 * (portfolio_return - benchmark_return)
```

The presentation averages reported window observations with equal weight. It does not compound the windows into a continuous account, annualize the averages, or infer a full-period drawdown from the average of separate drawdowns.
