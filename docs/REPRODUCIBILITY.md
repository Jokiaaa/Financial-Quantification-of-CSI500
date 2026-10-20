# Reproduction guide

## 1. Rebuild the presentation

Python 3.10+ is sufficient; no third-party dependencies or market-data downloads are needed. Run from the repository root:

```bash
python tools/build_showcase.py
python tools/build_showcase.py --check
python tools/import_research_archive.py --check
```

The first command generates five artifacts: two CSV tables, a provenance JSON, an SVG chart, and a Markdown results page. Check mode writes nothing. Extraction verifies expected case ordering, duplicate/missing observations, paired evaluation dates, benchmark agreement, and excess-return arithmetic within rounding tolerance. An unmatched supplementary row is preserved separately, including its arithmetic discrepancy.

The archive check validates the 11 bundled note snapshots against their SHA256 hashes and the source list. It does not require the author's external archive directory.

## 2. Run a self-contained offline execution demonstration

Use Python 3.12. The eight principal package versions in `requirements-research.txt` were exercised in the recorded Windows environment; `requirements.txt` retains the larger historical environment snapshot.

```bash
python -m pip install -r requirements-research.txt
python tools/make_demo_data.py --output .local/demo_inputs
python tools/research_pipeline.py backtest --manifest .local/demo_inputs/manifest.json --output .local/demo_run
python tools/verify_execution_artifacts.py --run .local/demo_run
```

The generator uses Python's standard library and creates a deterministic synthetic Qlib provider, 60 synthetic stocks, prediction CSVs, valuation CSV, calendar, and a relative-path manifest. The runner exercises real Qlib order simulation, day-21 construction, fees, and exports. It requires no network after dependencies are installed. These synthetic returns are software validation and are never counted as financial research evidence.

Each output directory must be new or empty. Completed evidence is not overwritten. `--help` and the standard-library artifact verifier do not import Qlib or access external market data.

## 3. Rerun a real-data portfolio

The portable runner reads explicit paths from a JSON manifest; relative paths are resolved against the manifest's directory. There are no embedded usernames or external path loads at import time. Start with [the example manifest](../configs/replay.example.json), or generate one from a historical YAML:

```bash
python tools/prepare_manifest.py --config yamls/hl378_mw2e4_2025H1_T40_D2.yaml --provider PATH_TO_PROVIDER --previous PATH_TO_PREVIOUS_PRED --current PATH_TO_CURRENT_PRED --valuation PATH_TO_VALUATION --output .local/inputs.json
python tools/research_pipeline.py check-inputs --manifest .local/inputs.json --output .local/input_check
python tools/research_pipeline.py backtest --manifest .local/inputs.json --output .local/replay
python tools/verify_execution_artifacts.py --run .local/replay
```

Inputs:

| Input | Required structure |
|---|---|
| Qlib provider | `calendars/day.txt`, instrument files, and daily feature binaries including open, close, factor, change, volume; benchmark close series |
| Predictions | Trusted local Qlib pickle, or CSV columns `datetime,instrument,score`; unique stock/date keys |
| Valuation | CSV/parquet columns `datetime,instrument,pcf`; unique stock/date keys; history sufficient for lagged alignment |
| Calendar | Must cover label maturity, 20 waiting sessions, evaluation, and at least one later session required by Qlib |

Real provider data and original full prediction artifacts remain external. Obtain them from your authorized data source or restore the author's frozen research package. That package's [freeze description](../research_archive/sources/freeze_description.txt) identifies the required artifact classes; the preserved small program ZIP is not represented as containing the complete provider. Current provider-file hashes, prediction hashes, valuation hashes, configurations, and versions are included in each new run manifest. Real-market reruns with a different snapshot are new experiments.

The historical valuation panel used in the published replay has one missing required PCF observation. The default checker rejects missing coverage. To reproduce that explicitly disclosed experiment, `prepare_manifest.py --allow-missing-pcf` records permission for gaps; missing keys and counts remain visible in the output manifest. No value is imputed.

Outputs include `daily.csv`, `orders.csv`, `trades.csv`, `positions.csv`, `initial_target.csv`, `execution_audit.json`, `metrics.csv`, and a source/data/output hash manifest. [The executed validation](../results/VALIDATION.md) provides the observed results. Reconstruction and actual trading are separate accounts; initial construction costs are charged.

Unlike the legacy floating Qlib price-limit threshold, opening trade eligibility is evaluated from the current open and previous close, not the current day's closing return. The effective expressions are exported. The fixed 9.5% approximation is retained; exchange-board-specific limits and live fill capacity require further modeling.

## 4. Train a matched model comparison

The portable training entry ignores the YAML's machine-specific `sys.rel_path` and loads this checkout's model and handler modules. It uses a common extended feature panel, selects the original 158 columns for the baseline, and keeps all 168 for the extended variants. All models use the same fitting implementation; unweighted variants set the observation weights to exactly one. Only the designated weighted variant uses the configured time decay, including validation weighting.

```bash
python tools/research_pipeline.py train-ablation --config yamls/hl378_mw2e4_2025H1_T40_D2.yaml --provider PATH_TO_PROVIDER --train-start 2021-01-01 --valid-start 2024-01-01 --rounds 300 --early-stopping 30 --threads 4 --output .local/models
```

This declared development experiment compares Alpha158/unweighted, extended/unweighted, and extended/weighted models. The training/validation boundary is purged by 20 trading sessions, validation labels mature before the simulated day-21 release, and seed 1729 is common. The final manifest records resolved segments, model and weight parameters, feature counts, best iterations, prediction/model hashes, and actual training completion timestamps of the new retrospective run. It does not certify the original historical training dates.

Use the generated `pred.pkl` as the current prediction in the same replay manifest to compare portfolios. Retaining the same previous prediction across models defines a common inherited reconstruction anchor; it does not compare three independent historical portfolio chains. The shorter common training window differs from the original 2008-start model and must not be labeled an exact retraining of that model.

## 5. Historical YAML workflow and legacy runner

The root `requirements.txt` is a historical Windows/Python 3.12 environment snapshot. It is not a minimal cross-platform installation specification, and a fresh installation was not verified during preparation of this presentation.

To reproduce training, first obtain and document the required Qlib CSI 500 provider data and its instrument/calendar coverage. Install a compatible Qlib/LightGBM environment. Replace the machine-specific `sys.rel_path` in the selected YAML with the absolute path to this checkout's `code` directory, and set `provider_uri` to the restored provider.

With those prerequisites satisfied, an example training entry point is:

```bash
qrun yamls/hl378_mw2e4_2025H1_T40_D2.yaml
```

This invokes the selected YAML workflow. It does not by itself establish the author's delayed-construction portfolio protocol, nor does it generate all preceding handover artifacts. Save the resolved configuration, random seeds, library versions, model completion time, and prediction-file hashes.

### Historical portfolio simulation

The historical runners preserve environment-specific dependencies. In particular, the formal runner loads a purged-prediction manifest **at module import time**, before command-line arguments are processed. A fresh checkout therefore cannot run that script, including its help path, without resolving that dependency.

| Required input | Current state |
|---|---|
| Qlib provider | External; path is machine-specific |
| Old and new `pred.pkl` files | Referenced in historical code; not bundled in this checkout |
| Purged YAMLs and run-path manifest | External frozen-directory references |
| Valuation history | External CSV/parquet; exact source snapshot needed |
| Industry map / enabled model-gate manifest | Additional dependencies for the formal runner and relevant variants |
| Day-21 construction trace | Described by author; not linked to the section-15 table by a bundled execution manifest |

Restore these artifacts, map paths, and record exact identities before rerunning. The runner supports `--cases`, `--variants`, `--jobs`, `--out-dir`, and `--pred-source`; setting `--pred-source original` does not bypass the import-time purged-manifest load.

Do not substitute newly downloaded or revised data and then label the output an exact reproduction of the earlier report. A run with new inputs is a new experiment and should have its own manifest and result directory.

## 6. Source archive provenance

The curated notes were imported from the author-supplied archive. Only the explicitly listed research files are included. To deliberately re-import those same sources from an available external archive:

```bash
python tools/import_research_archive.py --archive "PATH_TO_RESEARCH_ARCHIVE"
```

The importer refuses to overwrite a differing existing snapshot. The snapshot manifest records original relative paths and byte hashes; the original external files are not modified.

## 7. Data maintenance

The [PCF updater guide](../日常数据更新/pcf_updater/README.md) documents planning, candidate generation, coverage validation, and controlled publication. Presentation generation does not execute that updater or publish any data. Its coverage checks and execution backtests answer different questions and should be recorded separately.
