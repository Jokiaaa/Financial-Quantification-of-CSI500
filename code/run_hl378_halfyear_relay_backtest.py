from __future__ import annotations

import argparse
import hashlib
import math
import json
from pathlib import Path
from typing import Any

import pandas as pd
import qlib
import yaml
from qlib.backtest import backtest, executor
from qlib.contrib.strategy import TopkDropoutStrategy


WORKDIR = Path(r"C:\Users\30855\qlib\examples\benchmarks\LightGBM\semiannual_rolling_yamls_for_router")
DEFAULT_OUT_DIR = WORKDIR / "analysis" / "hl378_halfyear_relay_backtest"


CASE_MAP = {
    "2018H2": {
        "prev_pred": WORKDIR / "mlruns" / "376065131763570804" / "2518352ddead4ddeb48bbdd4c16fe6c7" / "artifacts" / "pred.pkl",
        "curr_pred": WORKDIR / "mlruns" / "376065131763570804" / "f0402dbbdcdb42b4b09e3ba1c077f871" / "artifacts" / "pred.pkl",
        "yaml": WORKDIR / "hl378_mw2e4_2018H2_T40_D2.yaml",
    },
    "2019H1": {
        "prev_pred": WORKDIR / "mlruns" / "376065131763570804" / "f0402dbbdcdb42b4b09e3ba1c077f871" / "artifacts" / "pred.pkl",
        "curr_pred": WORKDIR / "mlruns" / "376065131763570804" / "848b2d9b8cb841a993f66c9a21d1787a" / "artifacts" / "pred.pkl",
        "yaml": WORKDIR / "hl378_mw2e4_2019H1_T40_D2.yaml",
    },
    "2022H1": {
        "prev_pred": WORKDIR / "mlruns" / "376065131763570804" / "fb7324915f634cf886ba39fcd6bde715" / "artifacts" / "pred.pkl",
        "curr_pred": WORKDIR / "mlruns_recent_weighted_valid4_batch" / "601906743829434398" / "e5233e6e5b4f49ab9dc5d0b900e471a7" / "artifacts" / "pred.pkl",
        "yaml": WORKDIR / "hl378_mw2e4_2022H1_T40_D2.yaml",
    },
    "2022H2": {
        "prev_pred": WORKDIR / "mlruns_recent_weighted_valid4_batch" / "601906743829434398" / "e5233e6e5b4f49ab9dc5d0b900e471a7" / "artifacts" / "pred.pkl",
        "curr_pred": WORKDIR / "mlruns_recent_weighted_valid4_batch" / "120649575812436836" / "1f275e0c897f4d03b038ef33e7327756" / "artifacts" / "pred.pkl",
        "yaml": WORKDIR / "hl378_mw2e4_2022H2_T40_D2.yaml",
    },
    "2023H1": {
        "prev_pred": WORKDIR / "mlruns_recent_weighted_valid4_batch" / "120649575812436836" / "1f275e0c897f4d03b038ef33e7327756" / "artifacts" / "pred.pkl",
        "curr_pred": WORKDIR / "mlruns_recent_weighted_valid4_batch" / "217597562639876647" / "ff58f23cf87b45128b440b14698ac064" / "artifacts" / "pred.pkl",
        "yaml": WORKDIR / "hl378_mw2e4_2023H1_T40_D2.yaml",
    },
    "2019H2": {
        "prev_pred": WORKDIR / "mlruns" / "376065131763570804" / "848b2d9b8cb841a993f66c9a21d1787a" / "artifacts" / "pred.pkl",
        "curr_pred": WORKDIR / "mlruns" / "376065131763570804" / "ee388ba5740c4e4e86745f2950e2f8da" / "artifacts" / "pred.pkl",
        "yaml": WORKDIR / "hl378_mw2e4_2019H2_T40_D2.yaml",
        "relay_start": "2019-01-02",
        "relay_end": "2019-12-31",
        "switch_date": "2019-07-01",
        "eval_start": "2019-07-01",
        "eval_end": "2019-12-31",
        "prev_last_day": "2019-06-28",
    },
    "2020H1": {
        "prev_pred": WORKDIR / "mlruns" / "376065131763570804" / "ee388ba5740c4e4e86745f2950e2f8da" / "artifacts" / "pred.pkl",
        "curr_pred": WORKDIR / "mlruns" / "376065131763570804" / "c5e43b129baf471b95fc42a65532363a" / "artifacts" / "pred.pkl",
        "yaml": WORKDIR / "hl378_mw2e4_2020H1_T40_D2.yaml",
    },
    "2020H2": {
        "prev_pred": WORKDIR / "mlruns" / "376065131763570804" / "c5e43b129baf471b95fc42a65532363a" / "artifacts" / "pred.pkl",
        "curr_pred": WORKDIR / "mlruns" / "376065131763570804" / "1c5efc26465c4c09846709db021427b6" / "artifacts" / "pred.pkl",
        "yaml": WORKDIR / "hl378_mw2e4_2020H2_T40_D2.yaml",
    },
    "2021H1": {
        "prev_pred": WORKDIR / "mlruns" / "376065131763570804" / "1c5efc26465c4c09846709db021427b6" / "artifacts" / "pred.pkl",
        "curr_pred": WORKDIR / "mlruns" / "376065131763570804" / "2ff56eececa44039afe4abbcb9675de3" / "artifacts" / "pred.pkl",
        "yaml": WORKDIR / "hl378_mw2e4_2021H1_T40_D2.yaml",
    },
    "2021H2": {
        "prev_pred": WORKDIR / "mlruns" / "376065131763570804" / "2ff56eececa44039afe4abbcb9675de3" / "artifacts" / "pred.pkl",
        "curr_pred": WORKDIR / "mlruns" / "376065131763570804" / "fb7324915f634cf886ba39fcd6bde715" / "artifacts" / "pred.pkl",
        "yaml": WORKDIR / "hl378_mw2e4_2021H2_T40_D2.yaml",
    },
    "2023H2": {
        "prev_pred": WORKDIR / "mlruns_recent_weighted_valid4_batch" / "217597562639876647" / "ff58f23cf87b45128b440b14698ac064" / "artifacts" / "pred.pkl",
        "curr_pred": WORKDIR / "mlruns_recent_weighted_valid4_batch" / "635672370655998665" / "efa57c74bb004691b35f3ae2ed4b7d8d" / "artifacts" / "pred.pkl",
        "yaml": WORKDIR / "hl378_mw2e4_2023H2_T40_D2.yaml",
        "relay_start": "2023-01-03",
        "relay_end": "2023-12-29",
        "switch_date": "2023-07-03",
        "eval_start": "2023-07-03",
        "eval_end": "2023-12-29",
        "prev_last_day": "2023-06-30",
    },
    "2024H1": {
        "prev_pred": WORKDIR / "mlruns_recent_weighted_valid4_batch" / "635672370655998665" / "efa57c74bb004691b35f3ae2ed4b7d8d" / "artifacts" / "pred.pkl",
        "curr_pred": WORKDIR / "mlruns_recent_weighted_valid4_batch" / "305762276293780650" / "5c146845ed644d4b811c34840857418d" / "artifacts" / "pred.pkl",
        "yaml": WORKDIR / "hl378_mw2e4_2024H1_T40_D2.yaml",
    },
    "2024H2": {
        "prev_pred": WORKDIR / "mlruns_recent_weighted_valid4_batch" / "305762276293780650" / "5c146845ed644d4b811c34840857418d" / "artifacts" / "pred.pkl",
        "curr_pred": WORKDIR / "mlruns_recent_weighted_valid4_batch" / "255285612611426148" / "a4b0ce5b8786488582b8ed5e365398f1" / "artifacts" / "pred.pkl",
        "yaml": WORKDIR / "hl378_mw2e4_2024H2_T40_D2.yaml",
    },
    "2025H1": {
        "prev_pred": WORKDIR / "mlruns_recent_weighted_valid4_batch" / "255285612611426148" / "a4b0ce5b8786488582b8ed5e365398f1" / "artifacts" / "pred.pkl",
        "curr_pred": WORKDIR / "mlruns_recent_weighted_valid4_batch" / "697129011575934405" / "b6bb7da21af14c7db0e1e64372a0b258" / "artifacts" / "pred.pkl",
        "yaml": WORKDIR / "hl378_mw2e4_2025H1_T40_D2.yaml",
    },
    "2025H2": {
        "prev_pred": WORKDIR / "mlruns_recent_weighted_valid4_batch" / "697129011575934405" / "b6bb7da21af14c7db0e1e64372a0b258" / "artifacts" / "pred.pkl",
        "curr_pred": WORKDIR / "mlruns_recent_weighted_valid4_batch" / "360518579130108206" / "f177ef9272a345da89b12c5f79450c3a" / "artifacts" / "pred.pkl",
        "yaml": WORKDIR / "hl378_mw2e4_2025H2_T40_D2.yaml",
    },
    "2026YTD": {
        "prev_pred": WORKDIR / "mlruns_recent_weighted_valid4_batch" / "360518579130108206" / "f177ef9272a345da89b12c5f79450c3a" / "artifacts" / "pred.pkl",
        "curr_pred": WORKDIR / "mlruns_recent_weighted_valid4_batch" / "701867599063671665" / "016f5311e4d145eda40cffeb8a526dde" / "artifacts" / "pred.pkl",
        "yaml": WORKDIR / "hl378_mw2e4_2026YTD_T40_D2.yaml",
    },
}

CASE_MAP_MW3E4 = {
    "2022H1": {
        "prev_pred": WORKDIR / "mlruns" / "376065131763570804" / "fb7324915f634cf886ba39fcd6bde715" / "artifacts" / "pred.pkl",
        "curr_pred": WORKDIR / "mlruns_recent_weighted_valid4_batch" / "213208356838145024" / "422daa677e61430b9b8ab287a6a2d11c" / "artifacts" / "pred.pkl",
        "yaml": WORKDIR / "hl378_mw3e4_2022H1_T40_D2.yaml",
    },
    "2022H2": {
        "prev_pred": WORKDIR / "mlruns_recent_weighted_valid4_batch" / "213208356838145024" / "422daa677e61430b9b8ab287a6a2d11c" / "artifacts" / "pred.pkl",
        "curr_pred": WORKDIR / "mlruns_recent_weighted_valid4_batch" / "823093709173100816" / "efb673884a554ce0a3b100ac3f9851ad" / "artifacts" / "pred.pkl",
        "yaml": WORKDIR / "hl378_mw3e4_2022H2_T40_D2.yaml",
    },
    "2023H1": {
        "prev_pred": WORKDIR / "mlruns_recent_weighted_valid4_batch" / "823093709173100816" / "efb673884a554ce0a3b100ac3f9851ad" / "artifacts" / "pred.pkl",
        "curr_pred": WORKDIR / "mlruns_recent_weighted_valid4_batch" / "141427414138180709" / "f0648ad4572947fab2a5755470b82e91" / "artifacts" / "pred.pkl",
        "yaml": WORKDIR / "hl378_mw3e4_2023H1_T40_D2.yaml",
    },
    "2023H2": {
        "prev_pred": WORKDIR / "mlruns_recent_weighted_valid4_batch" / "141427414138180709" / "f0648ad4572947fab2a5755470b82e91" / "artifacts" / "pred.pkl",
        "curr_pred": WORKDIR / "mlruns_recent_weighted_valid4_batch" / "906303048993257448" / "aebd23ffe40e4f00b3d624e0dc729fd2" / "artifacts" / "pred.pkl",
        "yaml": WORKDIR / "hl378_mw3e4_2023H2_T40_D2.yaml",
    },
    "2024H1": {
        "prev_pred": WORKDIR / "mlruns_recent_weighted_valid4_batch" / "906303048993257448" / "aebd23ffe40e4f00b3d624e0dc729fd2" / "artifacts" / "pred.pkl",
        "curr_pred": WORKDIR / "mlruns_recent_weighted_valid4_batch" / "260186956192716253" / "964b832169ee47a099e1c9c3738f7344" / "artifacts" / "pred.pkl",
        "yaml": WORKDIR / "hl378_mw3e4_2024H1_T40_D2.yaml",
    },
    "2024H2": {
        "prev_pred": WORKDIR / "mlruns_recent_weighted_valid4_batch" / "260186956192716253" / "964b832169ee47a099e1c9c3738f7344" / "artifacts" / "pred.pkl",
        "curr_pred": WORKDIR / "mlruns_recent_weighted_valid4_batch" / "381335331619802872" / "7a2a9e60ba164de0a2ccc2c0559592c6" / "artifacts" / "pred.pkl",
        "yaml": WORKDIR / "hl378_mw3e4_2024H2_T40_D2.yaml",
    },
    "2025H1": {
        "prev_pred": WORKDIR / "mlruns_recent_weighted_valid4_batch" / "381335331619802872" / "7a2a9e60ba164de0a2ccc2c0559592c6" / "artifacts" / "pred.pkl",
        "curr_pred": WORKDIR / "mlruns_recent_weighted_valid4_batch" / "875978046095791620" / "d839f28a165b457d9dd406581d27ce8d" / "artifacts" / "pred.pkl",
        "yaml": WORKDIR / "hl378_mw3e4_2025H1_T40_D2.yaml",
    },
    "2025H2": {
        "prev_pred": WORKDIR / "mlruns_recent_weighted_valid4_batch" / "875978046095791620" / "d839f28a165b457d9dd406581d27ce8d" / "artifacts" / "pred.pkl",
        "curr_pred": WORKDIR / "mlruns_recent_weighted_valid4_batch" / "646900817876998546" / "fc1c45bff3b843d395bc0a08d9b9efdf" / "artifacts" / "pred.pkl",
        "yaml": WORKDIR / "hl378_mw3e4_2025H2_T40_D2.yaml",
    },
    "2026YTD": {
        "prev_pred": WORKDIR / "mlruns_recent_weighted_valid4_batch" / "646900817876998546" / "fc1c45bff3b843d395bc0a08d9b9efdf" / "artifacts" / "pred.pkl",
        "curr_pred": WORKDIR / "mlruns_recent_weighted_valid4_batch" / "728303557807447435" / "113ba0b723904263ac26496e28e4a584" / "artifacts" / "pred.pkl",
        "yaml": WORKDIR / "hl378_mw3e4_2026YTD_T40_D2.yaml",
    },
}

CASE_MAP_BY_MODEL = {
    "mw2e4": CASE_MAP,
    "mw3e4": CASE_MAP_MW3E4,
}

DEFAULT_CASES_BY_MODEL = {
    "mw2e4": ["2022H1", "2022H2", "2023H1", "2023H2", "2024H1", "2024H2", "2025H1", "2025H2", "2026YTD"],
    "mw3e4": ["2022H1", "2022H2", "2023H1", "2023H2", "2024H1", "2024H2", "2025H1", "2025H2", "2026YTD"],
}


def load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8-sig"))


def load_pred(path: Path) -> pd.DataFrame:
    pred = pd.read_pickle(path)
    if isinstance(pred, pd.Series):
        pred = pred.to_frame("score")
    elif isinstance(pred, pd.DataFrame) and "score" not in pred.columns:
        pred = pred.iloc[:, [0]].copy()
        pred.columns = ["score"]
    pred = pred.copy()
    pred.index = pred.index.set_names(["datetime", "instrument"])
    return pred.sort_index()[["score"]]


def tail_prev_pred(prev_pred: pd.DataFrame, prev_fraction: float) -> pd.DataFrame:
    if prev_fraction >= 0.999999:
        return prev_pred
    prev_dates = pd.DatetimeIndex(prev_pred.index.get_level_values("datetime")).sort_values().unique()
    keep_n = max(1, int(math.ceil(len(prev_dates) * prev_fraction)))
    keep_dates = set(prev_dates[-keep_n:])
    dt = pd.DatetimeIndex(prev_pred.index.get_level_values("datetime"))
    return prev_pred.loc[dt.isin(keep_dates)].copy()


def combine_preds(prev_pred: pd.DataFrame, curr_pred: pd.DataFrame, switch_date: str, prev_fraction: float) -> pd.DataFrame:
    switch_ts = pd.Timestamp(switch_date)
    prev_trim = tail_prev_pred(prev_pred, prev_fraction=prev_fraction)
    prev_dt = pd.DatetimeIndex(prev_trim.index.get_level_values("datetime"))
    curr_dt = pd.DatetimeIndex(curr_pred.index.get_level_values("datetime"))
    left = prev_trim.loc[prev_dt < switch_ts].copy()
    right = curr_pred.loc[curr_dt >= switch_ts].copy()
    combined = pd.concat([left, right], axis=0)
    combined = combined[~combined.index.duplicated(keep="last")].sort_index()
    return combined


def stabilize_signal(signal: pd.DataFrame) -> pd.DataFrame:
    """
    Pure exact-tie stabilizer.

    Rules within each trading day:
    1. Higher score first.
    2. If score is exactly equal, sort by instrument ascending.
    3. Only exact-tie groups get a tiny bounded perturbation so the ordering
       becomes reproducible for downstream sort-based logic.

    """
    stable_parts: list[pd.DataFrame] = []

    for dt, sub in signal.reset_index().groupby("datetime", sort=True):
        day = sub[["instrument", "score"]].copy()
        day["score"] = day["score"].astype(float)

        day = day.sort_values(
            ["score", "instrument"],
            ascending=[False, True],
            kind="mergesort",
        ).reset_index(drop=True)
        day["adjusted_score"] = day["score"]

        unique_scores_desc = sorted(day["score"].unique(), reverse=True)
        min_gap_by_score: dict[float, float] = {}
        for idx, score in enumerate(unique_scores_desc):
            gaps: list[float] = []
            if idx > 0:
                gaps.append(float(unique_scores_desc[idx - 1] - score))
            if idx + 1 < len(unique_scores_desc):
                gaps.append(float(score - unique_scores_desc[idx + 1]))
            positive_gaps = [gap for gap in gaps if gap > 0]
            fallback = max(abs(float(score)), 1.0) * 1e-12
            min_gap_by_score[float(score)] = min(positive_gaps) if positive_gaps else fallback

        for _, grp in day.groupby("score", sort=False):
            if len(grp) <= 1:
                continue
            score_value = float(grp["score"].iloc[0])
            min_gap = min_gap_by_score[score_value]
            step = min_gap / (len(grp) + 1) / 4.0
            for rank_idx, row_idx in enumerate(grp.index):
                offset = (len(grp) - 1 - rank_idx) * step
                day.at[row_idx, "adjusted_score"] = score_value + offset

        stable_parts.append(
            pd.DataFrame(
                {
                    "datetime": pd.Timestamp(dt),
                    "instrument": day["instrument"].values,
                    "score": day["adjusted_score"].values,
                }
            )
        )

    stable = pd.concat(stable_parts, ignore_index=True)
    return stable.set_index(["datetime", "instrument"]).sort_index()[["score"]]


def run_backtest(signal: pd.DataFrame, cfg: dict[str, Any], start_time: str, end_time: str) -> tuple[pd.DataFrame, Any]:
    bt_cfg = cfg["port_analysis_config"]["backtest"]
    strategy_cfg = cfg["port_analysis_config"]["strategy"]["kwargs"]
    strategy = TopkDropoutStrategy(signal=signal["score"], topk=int(strategy_cfg["topk"]), n_drop=int(strategy_cfg["n_drop"]))
    report_dict, _ = backtest(
        executor=executor.SimulatorExecutor(time_per_step="day", generate_portfolio_metrics=True),
        strategy=strategy,
        start_time=start_time,
        end_time=end_time,
        account=bt_cfg["account"],
        benchmark=bt_cfg["benchmark"],
        exchange_kwargs={
            "freq": "day",
            "limit_threshold": bt_cfg["exchange_kwargs"]["limit_threshold"],
            "deal_price": bt_cfg["exchange_kwargs"]["deal_price"],
            "open_cost": bt_cfg["exchange_kwargs"]["open_cost"],
            "close_cost": bt_cfg["exchange_kwargs"]["close_cost"],
            "min_cost": bt_cfg["exchange_kwargs"]["min_cost"],
        },
    )
    report, positions = report_dict["1day"]
    report.index = pd.to_datetime(report.index)
    return report.sort_index(), positions


def calc_metrics(report: pd.DataFrame) -> dict[str, float]:
    gross = pd.to_numeric(report["return"] - report["bench"], errors="coerce").dropna()
    net = pd.to_numeric(report["return"] - report["bench"] - report["cost"], errors="coerce").dropna()
    cost = pd.to_numeric(report["cost"], errors="coerce").dropna()
    turnover = pd.to_numeric(report["turnover"], errors="coerce").dropna()
    if len(net) == 0:
        raise ValueError("Evaluation report is empty after trimming; cannot calculate metrics.")
    std = net.std(ddof=1)
    nav = (1.0 + net).cumprod()
    return {
        "days": int(len(net)),
        "net_excess_sum": float(net.sum()),
        "gross_excess_sum": float(gross.sum()),
        "cost_sum": float(cost.sum()),
        "net_ann_excess": float(net.mean() * 252),
        "gross_ann_excess": float(gross.mean() * 252),
        "cost_ann_drag": float(cost.mean() * 252),
        "avg_turnover": float(turnover.mean()),
        "net_ir": float(math.nan if std == 0 or math.isnan(std) else net.mean() / std * math.sqrt(252)),
        "max_drawdown": float((nav / nav.cummax() - 1.0).min()),
        "first_day_net_excess": float(net.iloc[0]),
    }


def count_non_cash_positions(positions_obj: Any, dt: str) -> int:
    ts = pd.Timestamp(dt)
    if ts not in positions_obj:
        available = sorted(pd.Timestamp(k) for k in positions_obj.keys())
        fallback = max((k for k in available if k <= ts), default=None)
        if fallback is None:
            raise KeyError(f"No position snapshot available on or before {ts.date()}.")
        ts = fallback
    payload = positions_obj[ts]
    pos = payload["position"] if isinstance(payload, dict) else payload.position
    return len([k for k in pos.keys() if k not in {"cash", "now_account_value"}])


def infer_case_dates(case: dict[str, Any]) -> dict[str, str]:
    prev_pred = load_pred(case["prev_pred"])
    curr_pred = load_pred(case["curr_pred"])
    prev_dates = pd.DatetimeIndex(prev_pred.index.get_level_values("datetime")).sort_values().unique()
    curr_dates = pd.DatetimeIndex(curr_pred.index.get_level_values("datetime")).sort_values().unique()
    relay_start = pd.Timestamp(prev_dates.min()).strftime("%Y-%m-%d")
    relay_end = pd.Timestamp(curr_dates.max()).strftime("%Y-%m-%d")
    switch_date = pd.Timestamp(curr_dates.min()).strftime("%Y-%m-%d")
    prev_last_day = pd.Timestamp(prev_dates.max()).strftime("%Y-%m-%d")
    return {
        "relay_start": relay_start,
        "relay_end": relay_end,
        "switch_date": switch_date,
        "eval_start": switch_date,
        "eval_end": relay_end,
        "prev_last_day": prev_last_day,
    }


def file_fingerprint(path: Path) -> dict[str, Any]:
    stat = path.stat()
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return {
        "path": str(path),
        "size": int(stat.st_size),
        "mtime_ns": int(stat.st_mtime_ns),
        "sha256": h.hexdigest(),
    }


def build_cache_meta(case_name: str, case: dict[str, Any], merged_case: dict[str, Any], prev_fraction: float) -> dict[str, Any]:
    return {
        "case": case_name,
        "prev_fraction": float(prev_fraction),
        "tie_break_policy": "exact_tie_instrument_only_v1",
        "prev_pred": file_fingerprint(Path(case["prev_pred"])),
        "curr_pred": file_fingerprint(Path(case["curr_pred"])),
        "yaml": file_fingerprint(Path(case["yaml"])),
        "relay_start": merged_case["relay_start"],
        "relay_end": merged_case["relay_end"],
        "switch_date": merged_case["switch_date"],
        "eval_start": merged_case["eval_start"],
        "eval_end": merged_case["eval_end"],
        "prev_last_day": merged_case["prev_last_day"],
    }


def should_reuse_existing(summary_path: Path, meta_path: Path, desired_meta: dict[str, Any], rerun_existing: bool) -> bool:
    if rerun_existing or not summary_path.exists() or not meta_path.exists():
        return False
    try:
        existing_meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except Exception:
        return False
    return existing_meta == desired_meta


def run_case(case_name: str, case_map: dict[str, dict[str, Any]], out_root: Path, prev_fraction: float) -> Path:
    case = case_map[case_name]
    out_dir = out_root / case_name
    out_dir.mkdir(parents=True, exist_ok=True)

    inferred = infer_case_dates(case)
    merged_case = {**inferred, **case}

    cfg = load_yaml(case["yaml"])
    prev_pred = load_pred(case["prev_pred"])
    curr_pred = load_pred(case["curr_pred"])
    relay_signal = stabilize_signal(
        combine_preds(prev_pred, curr_pred, switch_date=merged_case["switch_date"], prev_fraction=prev_fraction)
    )
    orig_signal = stabilize_signal(curr_pred.copy())

    report_full, positions = run_backtest(relay_signal, cfg, start_time=merged_case["relay_start"], end_time=merged_case["relay_end"])
    relay_eval = report_full.loc[(report_full.index >= pd.Timestamp(merged_case["eval_start"])) & (report_full.index <= pd.Timestamp(merged_case["eval_end"]))].copy()

    orig_report_full, _ = run_backtest(orig_signal, cfg, start_time=merged_case["eval_start"], end_time=merged_case["eval_end"])
    orig_eval = orig_report_full.loc[(orig_report_full.index >= pd.Timestamp(merged_case["eval_start"])) & (orig_report_full.index <= pd.Timestamp(merged_case["eval_end"]))].copy()

    if relay_eval.empty:
        raise ValueError(f"{case_name}: relay evaluation window {merged_case['eval_start']} ~ {merged_case['eval_end']} is empty.")
    if orig_eval.empty:
        raise ValueError(f"{case_name}: orig evaluation window {merged_case['eval_start']} ~ {merged_case['eval_end']} is empty.")

    relay_metrics = calc_metrics(relay_eval)
    orig_metrics = calc_metrics(orig_eval)

    summary = pd.DataFrame(
        [
            {
                "case": case_name,
                "eval_start": merged_case["eval_start"],
                "eval_end": merged_case["eval_end"],
                "orig_net_ann_excess": orig_metrics["net_ann_excess"],
                "relay_net_ann_excess": relay_metrics["net_ann_excess"],
                "net_ann_improvement": relay_metrics["net_ann_excess"] - orig_metrics["net_ann_excess"],
                "orig_net_excess_sum": orig_metrics["net_excess_sum"],
                "relay_net_excess_sum": relay_metrics["net_excess_sum"],
                "net_sum_improvement": relay_metrics["net_excess_sum"] - orig_metrics["net_excess_sum"],
                "orig_first_day_net_excess": orig_metrics["first_day_net_excess"],
                "relay_first_day_net_excess": relay_metrics["first_day_net_excess"],
                "relay_prev_position_count": count_non_cash_positions(positions, merged_case["prev_last_day"]),
                "prev_fraction": prev_fraction,
                "prev_pred": str(case["prev_pred"]),
                "curr_pred": str(case["curr_pred"]),
            }
        ]
    )
    summary.to_csv(out_dir / "summary.csv", index=False, encoding="utf-8-sig")
    cache_meta = build_cache_meta(case_name, case, merged_case, prev_fraction=prev_fraction)
    (out_dir / "cache_meta.json").write_text(json.dumps(cache_meta, ensure_ascii=True, indent=2), encoding="utf-8")
    relay_signal.reset_index().to_csv(out_dir / "relay_signal.csv", index=False, encoding="utf-8-sig")
    report_full.reset_index().to_csv(out_dir / "relay_report_full.csv", index=False, encoding="utf-8-sig")
    orig_report_full.reset_index().to_csv(out_dir / "orig_report_full.csv", index=False, encoding="utf-8-sig")
    relay_eval.reset_index().to_csv(out_dir / "relay_report_eval.csv", index=False, encoding="utf-8-sig")
    orig_eval.reset_index().to_csv(out_dir / "orig_report_eval.csv", index=False, encoding="utf-8-sig")
    return out_dir / "summary.csv"


def main() -> None:
    parser = argparse.ArgumentParser(description="Relay previous-half HL378 signal into H2 and evaluate only the strict H2 window.")
    parser.add_argument("--model-name", choices=sorted(CASE_MAP_BY_MODEL.keys()), default="mw2e4")
    parser.add_argument("--cases", nargs="*")
    parser.add_argument("--out-dir")
    parser.add_argument("--prev-fraction", type=float, default=1.0, help="Fraction of the previous half-period to keep for preheat. 0.5 means only use the latter half of the previous half-year.")
    parser.add_argument("--rerun-existing", action="store_true")
    args = parser.parse_args()
    if not (0.0 < args.prev_fraction <= 1.0):
        raise ValueError(f"--prev-fraction must satisfy 0 < prev_fraction <= 1, got {args.prev_fraction}.")

    case_map = CASE_MAP_BY_MODEL[args.model_name]
    selected_cases = args.cases or DEFAULT_CASES_BY_MODEL[args.model_name]
    out_dir = args.out_dir or str(WORKDIR / "analysis" / f"hl378_halfyear_relay_backtest_{args.model_name}")

    out_root = Path(out_dir).resolve()
    out_root.mkdir(parents=True, exist_ok=True)

    qlib.init(provider_uri="~/.qlib/qlib_data/cn_data", region="cn", kernels=1, maxtasksperchild=1, joblib_backend="loky")

    rows = []
    for case_name in selected_cases:
        if case_name not in case_map:
            raise ValueError(f"Unsupported case: {case_name}")
        summary_path = out_root / case_name / "summary.csv"
        inferred = infer_case_dates(case_map[case_name])
        merged_case = {**inferred, **case_map[case_name]}
        desired_meta = build_cache_meta(case_name, case_map[case_name], merged_case, prev_fraction=args.prev_fraction)
        meta_path = out_root / case_name / "cache_meta.json"
        if should_reuse_existing(summary_path, meta_path, desired_meta, rerun_existing=args.rerun_existing):
            row = pd.read_csv(summary_path).iloc[0].to_dict()
            rows.append(row)
            print(f"[SKIP] {case_name} -> existing summary reused")
            continue
        summary_path = run_case(case_name, case_map, out_root, prev_fraction=args.prev_fraction)
        row = pd.read_csv(summary_path).iloc[0].to_dict()
        rows.append(row)
        print(pd.DataFrame([row]).to_string(index=False))

    all_summary = pd.DataFrame(rows)
    all_summary.to_csv(out_root / "summary_all.csv", index=False, encoding="utf-8-sig")
    print(out_root / "summary_all.csv")


if __name__ == "__main__":
    main()
