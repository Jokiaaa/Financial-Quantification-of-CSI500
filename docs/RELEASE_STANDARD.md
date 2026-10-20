# Project presentation and release standard

This is a practical acceptance standard for this project, not an institution's admissions requirement. The current package supports review of the implementation, recorded research process, and reported observations. A reproducible trading-execution release requires additional artifacts listed below.

| Area | Acceptance criterion | Current delivery |
|---|---|---|
| Research identity | A clear question, model definition, and scope | English README and research report; Chinese introduction |
| Prior work and contribution | Frameworks distinguished from project extensions | Contribution map with source-module references |
| Experiment history | Decisions include rejected directions and supporting records | Eleven selected original notes, experiment map, hashes |
| Result traceability | Every displayed observation has an identified source | CSV extraction includes report section and line number; source SHA256 |
| Statistical meaning | Window returns, annualization, and drawdown are distinguished | Results page and metric definitions |
| Overlapping observations | Duplicate time coverage is not counted twice | 2026H1 PCF row separated from paired 2026YTD |
| Presentation reproducibility | A fresh reader can regenerate committed tables and chart | Standard-library builder with check mode |
| Timing documentation | Label maturity, reconstruction, and actual construction are distinguished | Author-stated protocol and evidence mapping |
| Execution reproducibility | Trades match declared signal dates, construction costs, and starting account | New real-data day-21 cash-funded replay; order/fill/position/daily exports and an independent artifact verifier; original historical training timestamps remain unverified |
| Environment portability | Explicit paths and an exercised execution environment | Portable JSON manifest runner, principal version pins, working offline synthetic provider demonstration; real data restored separately |
| Empirical robustness | Matched ablations, cost sensitivity, frozen prospective evaluation | Three models actually trained and replayed on a common development window; ordinary/doubled-fee reference replay; broader periods and prospective evaluation remain |

## Review sequence

1. Read the README and research report to understand the question and implementation.
2. Inspect the experiment map and original notes to assess the development process.
3. Rebuild the displayed evidence and inspect the latest underperforming periods.
4. For execution claims, inspect the timing manifest, daily orders, positions, and costs.
5. Use a frozen evaluation for any claim of prospective performance.

## Publication package

Keep `code`, `yamls`, existing update utilities, the original report, and the new `docs`, `results`, `assets`, `tools`, and `research_archive` directories together. Exclude local virtual environments, downloaded market data, credentials, and unreviewed personal material. The curated archive in this package is limited to research notes.

Suggested GitHub description:

> CSI 500 equity research with Qlib and LightGBM: recency-weighted learning, semiannual prediction handover, valuation filtering, and documented experimental decisions.

Suggested topics: `quantitative-finance`, `qlib`, `lightgbm`, `equity-research`, `machine-learning`, `backtesting`.

The original program ZIP is preserved at its existing repository path. Historical YAML backups are organized under `research_archive/config_backups/`; the root historical report remains at its existing path so result extraction and earlier links retain their meaning. Application-writing notes are kept outside the public upload. A software license should be selected by the rights holder; none is inferred here.
