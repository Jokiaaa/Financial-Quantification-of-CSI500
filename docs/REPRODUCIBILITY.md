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

## 2. Train a configured model

The root `requirements.txt` is a historical Windows/Python 3.12 environment snapshot. It is not a minimal cross-platform installation specification, and a fresh installation was not verified during preparation of this presentation.

To reproduce training, first obtain and document the required Qlib CSI 500 provider data and its instrument/calendar coverage. Install a compatible Qlib/LightGBM environment. Replace the machine-specific `sys.rel_path` in the selected YAML with the absolute path to this checkout's `code` directory, and set `provider_uri` to the restored provider.

With those prerequisites satisfied, an example training entry point is:

```bash
qrun yamls/hl378_mw2e4_2025H1_T40_D2.yaml
```

This invokes the selected YAML workflow. It does not by itself establish the author's delayed-construction portfolio protocol, nor does it generate all preceding handover artifacts. Save the resolved configuration, random seeds, library versions, model completion time, and prediction-file hashes.

## 3. Reproduce the historical portfolio simulation

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

## 4. Source archive provenance

The curated notes were imported from the author-supplied archive. Only the explicitly listed research files are included. To deliberately re-import those same sources from an available external archive:

```bash
python tools/import_research_archive.py --archive "PATH_TO_RESEARCH_ARCHIVE"
```

The importer refuses to overwrite a differing existing snapshot. The snapshot manifest records original relative paths and byte hashes; the original external files are not modified.

## 5. Data maintenance

The [PCF updater guide](../日常数据更新/pcf_updater/README.md) documents planning, candidate generation, coverage validation, and controlled publication. Presentation generation does not execute that updater or publish any data. Its coverage checks and execution backtests answer different questions and should be recorded separately.
