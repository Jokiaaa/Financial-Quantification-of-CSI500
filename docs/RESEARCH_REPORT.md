# CSI 500 quantitative equity research

## Abstract

This project investigates the adaptation of a machine-learning stock-selection strategy to changing market conditions. It extends Qlib's Alpha158/LightGBM workflow with exponentially decaying sample weights, additional price/volume features, semiannual prediction handover, and a targeted valuation overlay. The supplied research archive records baseline failures, feature ablations, half-life comparisons, model-routing audits, and risk-control experiments. The principal displayed result compares the relay portfolio with and without PCF filtering across 23 matching delayed evaluation windows from 2015H1 through 2026YTD ending June 16. The mean reported window return increases from 9.34% to 10.21%; PCF has higher return in 16 windows, equal return in two, and lower return in five. These are historical descriptive observations extracted from the existing report, rather than newly rerun or independently audited results.

## Research motivation

A stock-selection model can retain apparent predictive information while its portfolio deteriorates after transaction costs or under a new market regime. The early baseline evaluation records this problem explicitly. The project therefore examines three connected questions:

1. Can emphasizing recent training observations improve adaptation without making the model excessively sensitive to the latest regime?
2. How should predictions and portfolio state be handled at semiannual model changes?
3. Can a limited valuation intervention improve selection without suppressing the strongest return signals?

The archive also explores alternative labels, feature subsets, downside-risk reranking, and dynamic risk controls. These branches are recorded in [the experiment history](EXPERIMENT_HISTORY.md), including rejected approaches.

## Data and experimental setting

The target market is the CSI 500 universe, with `SH000905` as the benchmark. The selected configuration uses Alpha158 plus ten additional expressions and predicts 20-trading-day close-to-close returns. Semiannual YAMLs identify training, validation, and test segments; an inspected 2025H1 configuration uses training through 2020, validation during 2021–2024, and a 2025H1 test segment.

Full market data, original provider snapshots, and prediction artifacts are external to the GitHub-sized project snapshot. The supplied archive also contains a frozen package whose README describes preservation of configurations, code, MLflow/prediction artifacts, and a hash manifest. This presentation includes the freeze description, not the complete frozen model package.

## Method

### Recency-weighted learning

The model extends Qlib's `LGBModel` and calculates exponentially decaying sample weights from observation age in calendar days. The selected setting uses a half-life of 378 days and an unnormalized minimum of 0.0002; weights are then normalized to unit mean. The implementation weights validation observations as well as training observations and uses LightGBM early stopping.

The archived half-life experiment compared 252, 378, and 504 days. A candidate that looked strongest in one period deteriorated on other inspected periods, motivating cross-period comparisons. That development history is not presented as an untouched prospective test.

### Feature engineering

The handler adds volatility ratios, normalized high/low ranges, relative volume means, and VWAP/close relationships. A separate archived study removes groups of features to examine their contribution. Its numerical conclusions remain scoped to that historical branch; the currently released handler retains all ten additions.

### Model handover and delayed construction

Prediction files from successive models are spliced into a relay signal. Exactly tied scores are stabilized using instrument ordering. According to the author's clarified procedure, the strategy waits 20 trading days for validation labels to mature, reconstructs the target using the prediction files, and begins actual construction on day 21. Signal availability and the opening execution timestamp must be consistent. [The timing protocol](METHODOLOGY.md) distinguishes this design from the historical report's delayed-window summarization and the available runner's separate purged-validation branch.

### Portfolio and valuation overlay

The reference portfolio targets 40 stocks using TopkDropout with `n_drop=2`. The overlay demotes candidates at raw ranks 36–40 when their PCF is in the most expensive decile of that day's raw top-100 pool. Inputs are aligned with a one-trading-day lag. The inspected backtest configurations use open prices, buy cost 0.1%, sell cost 0.2%, and minimum transaction cost 5. Risk-budget variants are separate exploratory experiments.

## Results

The main presentation uses section 15's 23 paired delayed windows. A PCF-only 2026H1 row overlaps the paired 2026YTD observation and is kept supplementary.

| Metric across 23 paired windows | Relay | Relay + PCF |
|---|---:|---:|
| Mean window return | 9.34% | 10.21% |
| Mean reported window excess | 4.90 pp | 5.77 pp |
| Mean within-window maximum drawdown | −14.20% | −13.89% |
| Positive reported excess windows | 18 / 23 | 20 / 23 |

The paired mean return change is +0.87 percentage points. The latest paired 2026YTD window is negative relative to the benchmark for both strategies. Excluding 2015 is shown as a sensitivity view, alongside the full sample, rather than replacing it.

![Reported window excess returns](../assets/delay20_excess.svg)

The [generated results page](../results/RESULTS.md) provides every observation and the source hash. Calculations start from rounded table values, so they can differ slightly from historical summary cells calculated from unrounded data. The supplementary 2026H1 row also has a reported excess that does not reconcile with its displayed return and benchmark; that original discrepancy is documented rather than corrected by assumption.

## Discussion

The available paired comparison suggests that a narrow PCF overlay improved the average observed window result within this strategy. It does not isolate the effect of recency weighting or the extra features. The archive supplies development comparisons for these components, but they use different configurations and periods and should not be pooled into a single common ablation table.

Negative findings are part of the research outcome. Broad relay guards and strong downside reranking sometimes reduced performance; some market-state rules were rejected after information-lag checks. These records support a research process that revisits assumptions and limits intervention when the supporting evidence is weak.

## Contribution map

| Component | Foundation | Project-level implementation / investigation |
|---|---|---|
| Learning | LightGBM; Qlib `LGBModel` | Recency-weight calculation, weighted fitting/validation, half-life experiments |
| Features | Qlib Alpha158 | Ten additional expressions and archived feature-group comparisons |
| Portfolio simulation | Qlib executor, exchange, TopkDropout | Prediction handover, exact-tie handling, PCF overlay, risk-budget variants |
| Experiment design | Time-ordered financial prediction | Semiannual configurations, failures, branch comparisons, timing investigations |
| Data operations | External market and valuation sources | Update scripts, coverage validation, hash records, controlled publication |
| Presentation | Existing code and research notes | English/Chinese documentation, curated evidence, reproducible result extraction |

This table identifies implemented project extensions. When describing personal authorship, the applicant should accurately state their own decisions, coding, supervision, collaboration, and any AI assistance; the repository cannot independently certify individual authorship.

## Scope and further validation

The remaining work for a fully reproducible execution release is an explicit day-21 construction manifest linked to daily trades, positions, and cost records; portable paths; access instructions for the exact provider snapshot; and a pinned environment verified by a fresh backtest. Matched model ablations, transaction-cost sensitivity, and a frozen prospective evaluation would strengthen the empirical claim. Historical periods used repeatedly for model selection remain development evidence.

## References and supporting material

- [Microsoft Qlib](https://github.com/microsoft/qlib): research workflow, Alpha158, portfolio simulation.
- [LightGBM](https://github.com/microsoft/LightGBM): boosted-tree framework.
- [Original historical report](../回测结果.md).
- [Curated experiment history](EXPERIMENT_HISTORY.md) and [source manifest](../research_archive/manifest.json).
