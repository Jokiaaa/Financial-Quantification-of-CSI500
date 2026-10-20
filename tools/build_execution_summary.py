from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    directory = ROOT / "results" / "execution_2025H1"
    manifest = json.loads((directory / "run_manifest.json").read_text(encoding="utf-8"))
    with (directory / "metrics.csv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    lines = [
        "# Executed validation: day-21 cash-funded reconstruction", "",
        "This is a new retrospective Qlib execution experiment, run with restored prediction files and the current local provider snapshot. It does not overwrite the original 23-window statistics or certify historical model-training timestamps.", "",
        "## Protocol exercised", "",
        f"- Last validation observation: **{manifest['dates']['validation_last_feature_date']}**.",
        f"- Full validation-label maturity: **{manifest['dates']['validation_label_maturity_close']} close**.",
        f"- Reconstruction and first execution signal: **{manifest['dates']['first_execution_signal_date']}**.",
        f"- Actual simulated cash-funded execution starts **{manifest['dates']['first_actual_trade_date']}**, ends **{manifest['dates']['evaluation_end']}**.",
        "- Reconstruction is run separately. Only its target stock list is transferred; no historical shares, entry prices, cash, or profits are transferred.",
        "- Actual order signals precede their trade session. Initial purchases pay the configured commission and are included in the first daily return.", "",
        "- Opening trade limits use the current open versus previous close. They do not use the same day's closing return. The original fixed 9.5% approximation is retained, rather than asserting a complete exchange/board-specific limit model.", "",
        "## Portfolio and cost comparison", "",
        "These are full compounded returns over this experiment's 97-session window, not averages across the historical sample.", "",
        "| Portfolio | Fee multiplier | Net return | Benchmark | Compound difference | MDD including initial cash | First-day filled stocks | First-day construction cost |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        name = f"{row['variant']}_cost{float(row['cost_multiple']):g}"
        audit = json.loads((directory / name / "execution_audit.json").read_text())
        lines.append(f"| {row['variant']} | {float(row['cost_multiple']):g}× | {float(row['total_return']):.4%} | {float(row['benchmark_return']):.4%} | {float(row['compound_return_difference']) * 100:.4f} pp | {float(row['max_drawdown_including_initial_cash']):.4%} | {audit['first_day_filled_stocks']} | {audit['first_day_construction_cost']:,.2f} |")
    lines += [
        "", "The nominal target is 40 stocks. Filled counts are observed simulation outputs, not forced target counts. Cost, return, and drawdown effects are shown together; one development window cannot establish general superiority or statistical significance.", "",
        "## Input completeness", "",
        f"The original valuation panel has **{manifest['missing_top100_pcf_observations']} missing PCF observation out of {manifest['required_top100_observations']} required top-100 observations**. This run explicitly permits and records the gap; it does not replace the value. The default input checker rejects gaps. Missing keys and provider-file hashes are recorded in [the run manifest](execution_2025H1/run_manifest.json). Provider updates and vendor revisions can change a new replay.", "",
        "## Independent checks on the exported evidence", "",
        "```bash",
        "python tools/verify_execution_artifacts.py --run results/execution_2025H1",
        "```", "",
        "The standard-library verifier checks output SHA256 hashes, an initially empty account, order/signal date ordering, first-day purchases, construction commissions in the daily P&L, and compounded returns. It does not require Qlib or the external provider.", "",
        "## Matched model ablation", "",
    ]
    ablation_root = ROOT / "results" / "matched_ablation_2025H1"
    ablation_files = sorted(ablation_root.glob("*/metrics.csv"))
    if ablation_files:
        lines += [
            "The following are additional development experiments, not untouched out-of-sample evidence. Models share the same 2021-start training sample, 2024 validation period, purged training/validation boundary, 2025H1 prediction interval, 300-round cap, 30-round early stopping, and seed 1729. All use the same previous-model prediction file as the inherited reconstruction anchor. This isolates new-model differences within a common handover experiment; it is not a comparison of fully independent historical portfolio chains.", "",
            "| New model | Portfolio | Fee multiplier | Net return | Benchmark difference | MDD |",
            "|---|---|---:|---:|---:|---:|",
        ]
        for path in ablation_files:
            with path.open(encoding="utf-8", newline="") as stream:
                for row in csv.DictReader(stream):
                    lines.append(f"| {path.parent.name} | {row['variant']} | {float(row['cost_multiple']):g}× | {float(row['total_return']):.4%} | {float(row['compound_return_difference']) * 100:.4f} pp | {float(row['max_drawdown_including_initial_cash']):.4%} |")
        lines.append("\nTraining artifacts and settings: [training manifest](matched_models_2025H1/training_manifest.json), [model inventory](matched_models_2025H1/models.csv), [provider snapshot fingerprints](matched_models_2025H1/provider_manifest.json). Native LightGBM model files and the exact training runner source are preserved alongside the manifest.\n")
        lines.append("The feature and weighting changes improve this particular matched window's observed net return. The weighted model also changes validation weighting and its selected stopping iteration. These observations require further periods before claiming a stable effect.\n")
    else:
        lines.append("The portable training command supports the common Alpha158/unweighted, extended/unweighted, and extended/weighted comparison. Completed result files are required before any model-effect claim is made.\n")
    lines += [
        "## Historical metric correction", "",
        "The overlapping 2026H1 supplementary record is now reconciled from 96 daily observations: −12.58 is the summed daily excess; −12.76 pp is the compound strategy-return minus benchmark-return difference. [Recalculation and source evidence](reconciliation_2026H1/RECONCILIATION.md).", "",
        "## Practical limits", "",
        "These checks establish what the new implementation did. They cannot recover the old model's historical training completion time or remove historical strategy-selection bias. Broader multi-period testing and a separately frozen future evaluation remain necessary for a general performance claim.", "",
    ]
    (ROOT / "results" / "VALIDATION.md").write_text("\n".join(lines), encoding="utf-8")
    print("Built results/VALIDATION.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
