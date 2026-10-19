# CSI 500 Quantitative Equity Research

**Time-weighted learning, semiannual model handover, and valuation-aware portfolio selection with Qlib.**

[中文介绍](docs/README.zh-CN.md) · [Research report](docs/RESEARCH_REPORT.md) · [Experiment history](docs/EXPERIMENT_HISTORY.md) · [Results](results/RESULTS.md) · [Reproduction guide](docs/REPRODUCIBILITY.md) · [Timing protocol](docs/METHODOLOGY.md)

**Original program archive:** [CSI 500 Quantitative Program Based on Python and Qlib](Financial-Quantification-of-CSI500-main%20%281%29.zip). The original download is preserved separately from the research presentation.

## Research question

Can a model that gives greater weight to recent observations, combined with a targeted price-to-cash-flow (PCF) filter, improve the historical performance of a CSI 500 stock-selection portfolio?

This repository contains model extensions, semiannual experiment configurations, signal handover logic, portfolio backtesting code, and a historical results record. Eleven curated research-note snapshots document baseline evaluation, half-life selection, feature ablations, model-routing audits, and risk-control experiments. The principal displayed comparison is the relay portfolio versus the same portfolio with PCF filtering; earlier branch experiments remain separately identified.

## Project at a glance

| Component | Design |
|---|---|
| Universe / benchmark | CSI 500 / `SH000905` |
| Features | Qlib Alpha158 plus 10 volatility, range, volume, and VWAP-related features |
| Prediction target | Forward 20-trading-day close-to-close return |
| Model | LightGBM with exponentially decaying observation weights |
| Weighting configuration | 378-calendar-day half-life; minimum unnormalized weight `0.0002` |
| Portfolio | Target 40 stocks; TopkDropout parameter `n_drop=2` |
| Valuation overlay | Filter ranks 36–40 when PCF is in the most expensive decile of daily top-100 candidates |
| Execution configuration | Open-price simulation; buy cost 0.1%, sell cost 0.2%, minimum cost 5 |
| Timing convention | Wait 20 trading days; day 21 is the first eligible construction day under the author's stated protocol |
| Presented observations | 23 paired windows, 2015H1–2025H2 and 2026YTD ending June 16 |

## Historical evidence

![Excess return in paired delayed evaluation windows](assets/delay20_excess.svg)

Each bar is a window's reported portfolio return minus its benchmark return, in percentage points. These are delayed evaluation windows, not full half-years. Underperformance, including the latest paired 2026YTD observation, is retained.

The [results page](results/RESULTS.md) provides paired comparisons, averages, drawdowns, and provenance. Calculations use the rounded observations in section 15 of [the original report](回测结果.md), rather than an independently rerun backtest. An additional 2026H1 PCF row is retained separately because it overlaps 2026YTD and has no matching baseline.

## Research implementation

- **Learning:** extend Qlib's LightGBM model with normalized exponential time weights and weighted validation for early stopping.
- **Feature engineering:** extend Alpha158 with ten explicitly defined feature expressions.
- **Model handover:** combine successive prediction files into a relay signal and stabilize equal scores deterministically.
- **Portfolio design:** evaluate a targeted PCF overlay and exploratory risk-budget variants through Qlib's order simulation.
- **Data operations:** provide daily update scripts and a [PCF updater](日常数据更新/pcf_updater/README.md) with coverage checks, file hashes, and controlled publication.

Framework components and project extensions are distinguished in the [contribution map](docs/RESEARCH_REPORT.md#contribution-map). Repository ownership alone does not establish sole authorship of every component.

## Reproduce the displayed results

Requires Python 3.10+ and its standard library only. From the repository root:

```bash
python tools/build_showcase.py
python tools/build_showcase.py --check
python tools/import_research_archive.py --check
```

This rebuilds the CSV tables, chart, provenance JSON, and results summary from the committed report. It does not run Qlib or download market data. Full training and simulation additionally require external datasets, prediction artifacts, and path configuration; see the [reproduction guide](docs/REPRODUCIBILITY.md).

## Repository map

```text
code/                  Models, feature handler, historical backtest scripts
yamls/                 Active semiannual Qlib experiment configurations
日常数据更新/           Market-data and PCF update utilities
回测结果.md             Original historical record, preserved unchanged
docs/                  Research, timing, reproduction, application documents
results/               Extracted observations, summaries, provenance
assets/                Generated comparison chart
tools/                 Standard-library presentation rebuild tool
research_archive/      Eleven curated research notes and their hash manifest
```

Historical YAML backup files are kept under `research_archive/config_backups/`; they are not additional active experiments.

## Interpretation and next experiments

The paired observations support a descriptive comparison of PCF filtering within this strategy. They do not establish a causal effect, statistical significance, live profitability, or a fully untouched historical test. Continuous-account CAGR, Sharpe, and full-period maximum drawdown require daily returns and cannot be recovered from window averages.

The author's day-21 construction procedure is documented in the [timing protocol](docs/METHODOLOGY.md). The historical report describes a delayed statistics window, while the available runner also contains a separate purged-prediction configuration. The exact execution trace for the stated day-21 procedure is not bundled; the presentation does not claim an execution audit.

Priority extensions are a released execution manifest, matched model ablations, cost sensitivity, and a frozen prospective evaluation. See the [release standard](docs/RELEASE_STANDARD.md).

## Foundations

- [Microsoft Qlib](https://github.com/microsoft/qlib): Alpha158, data handling, recording, portfolio simulation.
- [LightGBM](https://github.com/microsoft/LightGBM): gradient-boosted tree learning.

External data and third-party software remain subject to their original access and licensing terms.
