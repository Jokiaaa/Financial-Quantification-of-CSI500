from __future__ import annotations

import argparse
import hashlib
import json
import logging
import math
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml


ROOT = Path(r"C:\Users\30855\Desktop\RSRS")
PROJECT = Path(r"C:\Users\30855\qlib\examples\benchmarks\LightGBM\semiannual_rolling_yamls_for_router")
QLIB_PROVIDER = Path(r"C:\Users\30855\.qlib\qlib_data\cn_data")
VAL_PATH = Path(r"C:\Users\30855\Desktop\模拟盘2\data\baidu_valuation_latest.csv")
INDUSTRY_MAP_PATH = Path(r"C:\Users\30855\Desktop\industry\analysis\rough_industry_required_full\industry_map_sw1_cninfo.csv")
PURGED_FREEZE_DIR = Path(r"C:\Users\30855\Desktop\frozen_hl378_mw2e4_T40_D2_20260528(2)")
PURGED_YAML_DIR = PURGED_FREEZE_DIR / "yamls_valid_end_minus20td"
PURGED_RUN_KEY_PATH = PURGED_FREEZE_DIR / "runs_valid_end_minus20td_20260618_serial" / "run_key_paths_corrected.csv"
OUT_DIR = ROOT / "output" / "formal_full_hl378_mw2e4_relay_pcf_risk_qlib_purged_20260618"

BASE_RISK_DEGREE = 0.95
LOW_RISK_DEGREE = BASE_RISK_DEGREE * 0.70
FED_RISK_MULTIPLIERS = [0.50, 0.60, 0.70, 0.80, 0.90, 1.00]
PCF_VARIANT = "drop_expensive_edge36_40_pcf_only_q90"
MODEL_GATE_ENABLED = True
MODEL_GATE_MANIFEST_PATH = Path(r"C:\Users\30855\Desktop\模拟盘2\data\model_gate_2026H1\model_gate_manifest.csv")


ORIGINAL_PRED_BY_PERIOD: dict[str, Path] = {
    "2014H2": PROJECT / "mlruns" / "376065131763570804" / "4c788abf027749b688a9fc3c303cbf85" / "artifacts" / "pred.pkl",
    "2015H1": PROJECT / "mlruns" / "376065131763570804" / "d17b77a120334ea8ab9d0da0951daf4c" / "artifacts" / "pred.pkl",
    "2015H2": PROJECT / "mlruns" / "376065131763570804" / "d71d36c929b64f0989e60987f90e3294" / "artifacts" / "pred.pkl",
    "2016H1": PROJECT / "mlruns" / "376065131763570804" / "fc4d7d581fc74bdabfe9623fbf1f3ee4" / "artifacts" / "pred.pkl",
    "2016H2": PROJECT / "mlruns" / "376065131763570804" / "a6fe8e4cc93b48a8ba7a18bad65874dd" / "artifacts" / "pred.pkl",
    "2017H1": PROJECT / "mlruns" / "376065131763570804" / "5ae095d3efed465dbce0aacfa87819fe" / "artifacts" / "pred.pkl",
    "2017H2": PROJECT / "mlruns" / "376065131763570804" / "28d4f7b3f5564844aee29a2636f1a457" / "artifacts" / "pred.pkl",
    "2018H1": PROJECT / "mlruns" / "376065131763570804" / "2518352ddead4ddeb48bbdd4c16fe6c7" / "artifacts" / "pred.pkl",
    "2018H2": PROJECT / "mlruns" / "376065131763570804" / "f0402dbbdcdb42b4b09e3ba1c077f871" / "artifacts" / "pred.pkl",
    "2019H1": PROJECT / "mlruns" / "376065131763570804" / "848b2d9b8cb841a993f66c9a21d1787a" / "artifacts" / "pred.pkl",
    "2019H2": PROJECT / "mlruns" / "376065131763570804" / "ee388ba5740c4e4e86745f2950e2f8da" / "artifacts" / "pred.pkl",
    "2020H1": PROJECT / "mlruns" / "376065131763570804" / "c5e43b129baf471b95fc42a65532363a" / "artifacts" / "pred.pkl",
    "2020H2": PROJECT / "mlruns" / "376065131763570804" / "1c5efc26465c4c09846709db021427b6" / "artifacts" / "pred.pkl",
    "2021H1": PROJECT / "mlruns" / "376065131763570804" / "2ff56eececa44039afe4abbcb9675de3" / "artifacts" / "pred.pkl",
    "2021H2": PROJECT / "mlruns" / "376065131763570804" / "fb7324915f634cf886ba39fcd6bde715" / "artifacts" / "pred.pkl",
    "2022H1": PROJECT / "mlruns_recent_weighted_valid4_batch" / "601906743829434398" / "e5233e6e5b4f49ab9dc5d0b900e471a7" / "artifacts" / "pred.pkl",
    "2022H2": PROJECT / "mlruns_recent_weighted_valid4_batch" / "120649575812436836" / "1f275e0c897f4d03b038ef33e7327756" / "artifacts" / "pred.pkl",
    "2023H1": PROJECT / "mlruns_recent_weighted_valid4_batch" / "217597562639876647" / "ff58f23cf87b45128b440b14698ac064" / "artifacts" / "pred.pkl",
    "2023H2": PROJECT / "mlruns_recent_weighted_valid4_batch" / "635672370655998665" / "efa57c74bb004691b35f3ae2ed4b7d8d" / "artifacts" / "pred.pkl",
    "2024H1": PROJECT / "mlruns_recent_weighted_valid4_batch" / "305762276293780650" / "5c146845ed644d4b811c34840857418d" / "artifacts" / "pred.pkl",
    "2024H2": PROJECT / "mlruns_recent_weighted_valid4_batch" / "255285612611426148" / "a4b0ce5b8786488582b8ed5e365398f1" / "artifacts" / "pred.pkl",
    "2025H1": PROJECT / "mlruns_recent_weighted_valid4_batch" / "697129011575934405" / "b6bb7da21af14c7db0e1e64372a0b258" / "artifacts" / "pred.pkl",
    "2025H2": PROJECT / "mlruns_recent_weighted_valid4_batch" / "360518579130108206" / "f177ef9272a345da89b12c5f79450c3a" / "artifacts" / "pred.pkl",
    "2026YTD": Path(r"C:\Users\30855\Desktop\模拟盘2\data\pred\pred_2026-01-01_2026-06-16.pkl"),
}

ORDERED_PERIODS = list(ORIGINAL_PRED_BY_PERIOD)
DEFAULT_CASES = ORDERED_PERIODS[1:]


FED_ACTIONS = [
    ("2018-03-22", "hike", 25, 1.75),
    ("2018-06-14", "hike", 25, 2.00),
    ("2018-09-27", "hike", 25, 2.25),
    ("2018-12-20", "hike", 25, 2.50),
    ("2019-08-01", "cut", -25, 2.25),
    ("2019-09-19", "cut", -25, 2.00),
    ("2019-10-31", "cut", -25, 1.75),
    ("2020-03-04", "cut", -50, 1.25),
    ("2020-03-16", "cut", -100, 0.25),
    ("2022-03-17", "hike", 25, 0.50),
    ("2022-05-05", "hike", 50, 1.00),
    ("2022-06-16", "hike", 75, 1.75),
    ("2022-07-28", "hike", 75, 2.50),
    ("2022-09-22", "hike", 75, 3.25),
    ("2022-11-03", "hike", 75, 4.00),
    ("2022-12-15", "hike", 50, 4.50),
    ("2023-02-02", "hike", 25, 4.75),
    ("2023-03-23", "hike", 25, 5.00),
    ("2023-05-04", "hike", 25, 5.25),
    ("2023-07-27", "hike", 25, 5.50),
    ("2024-09-19", "cut", -50, 5.00),
    ("2024-11-08", "cut", -25, 4.75),
    ("2024-12-19", "cut", -25, 4.50),
    ("2025-09-18", "cut", -25, 4.25),
    ("2025-10-30", "cut", -25, 4.00),
    ("2025-12-11", "cut", -25, 3.75),
]

_VALUATION: pd.DataFrame | None = None
_STRATEGY_CLASS: Any | None = None
_RISK_GATES: dict[str, pd.Series] | None = None
_RISK_DEGREES: dict[str, pd.Series] | None = None
_TOPK_ADJUST: dict[str, pd.Series] | None = None
_NDROP_ADJUST: dict[str, pd.Series] | None = None
_PCF_ENABLED: dict[str, pd.Series] | None = None
_PCF_STRONG: dict[str, pd.Series] | None = None
_MARKET_REGIME: pd.DataFrame | None = None
_INDUSTRY_MAP: dict[str, str] | None = None


def yaml_path(period: str, pred_source: str = "purged") -> Path:
    if pred_source == "purged":
        purged = PURGED_YAML_DIR / f"hl378_mw2e4_{period}_T40_D2.yaml"
        if purged.exists():
            return purged
    early = ROOT / "generated_yamls" / f"hl378_mw2e4_{period}_T40_D2.yaml"
    return early if early.exists() else PROJECT / f"hl378_mw2e4_{period}_T40_D2.yaml"


def load_purged_pred_by_period(path: Path) -> dict[str, Path]:
    if not path.exists():
        raise FileNotFoundError(f"Purged pred path manifest not found: {path}")
    manifest = pd.read_csv(path)
    out: dict[str, Path] = {}
    for _, row in manifest.iterrows():
        case = str(row["Case"])
        prefix = "hl378_mw2e4_"
        suffix = "_T40_D2"
        if not (case.startswith(prefix) and case.endswith(suffix)):
            continue
        period = case[len(prefix) : -len(suffix)]
        pred = Path(str(row["Pred"]))
        if not pred.exists():
            migrated = Path(str(pred).replace(
                r"C:\Users\30855\Desktop\frozen_hl378_mw2e4_T40_D2_20260528",
                str(PURGED_FREEZE_DIR),
            ))
            if migrated.exists():
                pred = migrated
        if not pred.exists():
            raise FileNotFoundError(f"Purged pred missing for {period}: {pred}")
        out[period] = pred
    missing = [p for p in ORDERED_PERIODS if p not in out]
    if missing:
        raise ValueError(f"Purged pred manifest is missing periods: {missing}")
    return {p: out[p] for p in ORDERED_PERIODS}


PURGED_PRED_BY_PERIOD = load_purged_pred_by_period(PURGED_RUN_KEY_PATH)
PRED_BY_PERIOD = PURGED_PRED_BY_PERIOD


def pred_by_source(pred_source: str) -> dict[str, Path]:
    if pred_source == "original":
        return ORIGINAL_PRED_BY_PERIOD
    if pred_source == "purged":
        return PURGED_PRED_BY_PERIOD
    raise ValueError(f"Unknown pred source: {pred_source}")


def load_model_gate_manifest(path: Path = MODEL_GATE_MANIFEST_PATH) -> dict[str, dict[str, Any]]:
    if not MODEL_GATE_ENABLED or not path.exists():
        return {}
    manifest = pd.read_csv(path)
    out: dict[str, dict[str, Any]] = {}
    for _, row in manifest.iterrows():
        case = str(row.get("case", "")).strip()
        if not case:
            continue
        enabled = str(row.get("enabled", "1")).strip().lower() not in {"0", "false", "no", "nan"}
        if not enabled:
            continue
        selected = Path(str(row.get("selected_pred", "")).strip())
        if not selected.exists():
            raise FileNotFoundError(f"Model gate selected pred missing for {case}: {selected}")
        out[case] = {k: row.get(k) for k in manifest.columns}
        out[case]["selected_pred"] = selected
    return out


MODEL_GATE_BY_CASE = load_model_gate_manifest()


def gated_curr_pred_path(case_name: str, pred_paths: dict[str, Path]) -> tuple[Path, dict[str, Any]]:
    original_path = pred_paths[case_name]
    gate = MODEL_GATE_BY_CASE.get(case_name)
    if not gate:
        return original_path, {"model_gate_enabled": False, "model_gate_decision": "use_configured_pred"}
    selected = Path(gate["selected_pred"])
    return selected, {
        "model_gate_enabled": True,
        "model_gate_decision": str(gate.get("decision", "selected_pred")),
        "model_gate_manifest": str(MODEL_GATE_MANIFEST_PATH),
        "model_gate_original_pred": str(original_path),
        "model_gate_selected_pred": str(selected),
        "model_gate_shadow_window": str(gate.get("shadow_window", "")),
        "model_gate_reason": str(gate.get("reason", "")),
    }


def previous_period(period: str) -> str:
    idx = ORDERED_PERIODS.index(period)
    if idx <= 0:
        raise ValueError(f"{period} has no previous pred period")
    return ORDERED_PERIODS[idx - 1]


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
    pred.index = pd.MultiIndex.from_arrays(
        [pd.to_datetime(pred.index.get_level_values("datetime")), pred.index.get_level_values("instrument")],
        names=["datetime", "instrument"],
    )
    pred["score"] = pd.to_numeric(pred["score"], errors="coerce")
    return pred.dropna(subset=["score"]).sort_index()[["score"]]


def infer_dates(prev_pred: pd.DataFrame, curr_pred: pd.DataFrame) -> dict[str, str]:
    prev_dates = pd.DatetimeIndex(prev_pred.index.get_level_values("datetime")).sort_values().unique()
    curr_dates = pd.DatetimeIndex(curr_pred.index.get_level_values("datetime")).sort_values().unique()
    return {
        "relay_start": pd.Timestamp(prev_dates.min()).strftime("%Y-%m-%d"),
        "switch_date": pd.Timestamp(curr_dates.min()).strftime("%Y-%m-%d"),
        "eval_start": pd.Timestamp(curr_dates.min()).strftime("%Y-%m-%d"),
        "eval_end": pd.Timestamp(curr_dates.max()).strftime("%Y-%m-%d"),
        "relay_end": pd.Timestamp(curr_dates.max()).strftime("%Y-%m-%d"),
        "prev_last_day": pd.Timestamp(prev_dates.max()).strftime("%Y-%m-%d"),
    }


def combine_preds(prev_pred: pd.DataFrame, curr_pred: pd.DataFrame, switch_date: str) -> pd.DataFrame:
    switch_ts = pd.Timestamp(switch_date)
    prev_dt = pd.DatetimeIndex(prev_pred.index.get_level_values("datetime"))
    curr_dt = pd.DatetimeIndex(curr_pred.index.get_level_values("datetime"))
    combined = pd.concat([prev_pred.loc[prev_dt < switch_ts], curr_pred.loc[curr_dt >= switch_ts]], axis=0)
    return combined[~combined.index.duplicated(keep="last")].sort_index()


def stabilize_signal(signal: pd.DataFrame) -> pd.DataFrame:
    parts: list[pd.DataFrame] = []
    for dt, sub in signal.reset_index().groupby("datetime", sort=True):
        day = sub[["instrument", "score"]].copy()
        day = day.sort_values(["score", "instrument"], ascending=[False, True], kind="mergesort").reset_index(drop=True)
        day["score_stable"] = day["score"].astype(float)

        unique_scores = sorted(day["score"].dropna().unique(), reverse=True)
        min_gap_by_score: dict[float, float] = {}
        for i, score in enumerate(unique_scores):
            gaps = []
            if i > 0:
                gaps.append(float(unique_scores[i - 1] - score))
            if i + 1 < len(unique_scores):
                gaps.append(float(score - unique_scores[i + 1]))
            gaps = [g for g in gaps if g > 0]
            min_gap_by_score[float(score)] = min(gaps) if gaps else max(abs(float(score)), 1.0) * 1e-12

        for score, grp in day.groupby("score", sort=False):
            if len(grp) <= 1:
                continue
            step = min_gap_by_score[float(score)] / (len(grp) + 1) / 4.0
            for rank_idx, row_idx in enumerate(grp.index):
                day.at[row_idx, "score_stable"] = float(score) + (len(grp) - 1 - rank_idx) * step

        parts.append(
            pd.DataFrame(
                {
                    "datetime": pd.Timestamp(dt),
                    "instrument": day["instrument"].values,
                    "score": day["score_stable"].values,
                }
            )
        )
    return pd.concat(parts, ignore_index=True).set_index(["datetime", "instrument"]).sort_index()[["score"]]


def attach_valuation(signal: pd.DataFrame, val: pd.DataFrame, lag_trading_days: int = 1) -> pd.DataFrame:
    dates = pd.DatetimeIndex(sorted(signal.index.get_level_values("datetime").unique()))
    instruments = sorted(signal.index.get_level_values("instrument").unique())
    val = val[val["instrument"].isin(instruments)].copy()
    frames = []
    for inst, sub in val.groupby("instrument"):
        sub = sub.set_index("datetime").sort_index()
        idx = dates.union(sub.index).sort_values()
        aligned = sub[["market_cap", "pe_ttm", "pb", "pcf"]].reindex(idx).ffill().reindex(dates)
        aligned = aligned.shift(lag_trading_days)
        aligned["instrument"] = inst
        aligned["datetime"] = dates
        frames.append(aligned.reset_index(drop=True))
    if not frames:
        return signal.copy()
    panel = pd.concat(frames, ignore_index=True).set_index(["datetime", "instrument"]).sort_index()
    return signal.join(panel)


def pct_by_day(s: pd.Series, ascending: bool = True) -> pd.Series:
    return s.groupby(level="datetime").rank(pct=True, ascending=ascending)


def classify_board(instrument: str) -> str:
    code = str(instrument).upper()
    if code.startswith("SZ300") or code.startswith("SZ301"):
        return "CHINEXT"
    if code.startswith("SH688"):
        return "STAR"
    if code.startswith("BJ"):
        return "BSE"
    if code.startswith("SZ"):
        return "SZ_MAIN"
    if code.startswith("SH"):
        return "SH_MAIN"
    return "UNKNOWN"


def load_industry_map(path: Path = INDUSTRY_MAP_PATH) -> dict[str, str]:
    if not path.exists():
        return {}
    df = pd.read_csv(path)
    if "instrument" not in df.columns or "industry" not in df.columns:
        return {}
    df["instrument"] = df["instrument"].astype(str).str.upper()
    df["industry"] = df["industry"].astype(str).str.strip()
    df = df[df["industry"].ne("") & df["industry"].ne("nan")]
    return dict(zip(df["instrument"], df["industry"]))


def apply_pcf_filter(
    signal_with_val: pd.DataFrame,
    *,
    edge_start: int = 36,
    edge_end: int = 40,
    expensive_quantile: float = 0.90,
) -> pd.DataFrame:
    out = signal_with_val[["score"]].copy()
    original_rank = signal_with_val["score"].groupby(level="datetime").rank(method="first", ascending=False)
    top100 = original_rank <= 100
    edge = (original_rank >= edge_start) & (original_rank <= edge_end)
    pcf_pct_top100 = pct_by_day(signal_with_val["pcf"].where((signal_with_val["pcf"] > 0) & top100), ascending=True)
    expensive = edge & (pcf_pct_top100 >= expensive_quantile)
    out.loc[expensive, "score"] = -1e9
    return out


def apply_pcf_q90(signal_with_val: pd.DataFrame) -> pd.DataFrame:
    return apply_pcf_filter(signal_with_val, edge_start=36, edge_end=40, expensive_quantile=0.90)


def apply_pcf_layered(signal_with_val: pd.DataFrame) -> pd.DataFrame:
    out = signal_with_val[["score"]].copy()
    original_rank = signal_with_val["score"].groupby(level="datetime").rank(method="first", ascending=False)
    top100 = original_rank <= 100
    pcf_pct_top100 = pct_by_day(signal_with_val["pcf"].where((signal_with_val["pcf"] > 0) & top100), ascending=True)

    edge36_40 = original_rank.between(36, 40)
    edge31_40 = original_rank.between(31, 40)
    strong = (edge36_40 & pcf_pct_top100.ge(0.90)) | (edge31_40 & pcf_pct_top100.ge(0.95))
    light = edge36_40 & pcf_pct_top100.ge(0.80) & pcf_pct_top100.lt(0.90) & ~strong

    out.loc[strong.fillna(False), "score"] = -1e9
    for dt, light_day in light.groupby(level="datetime", sort=True):
        light_idx = light_day[light_day.fillna(False)].index
        if len(light_idx) == 0:
            continue
        scores = signal_with_val.loc[(dt, slice(None)), "score"].droplevel("datetime").dropna()
        if scores.empty:
            continue
        ranked = scores.sort_values(ascending=False, kind="mergesort")
        if len(ranked) >= 40:
            anchor = float(ranked.iloc[39])
        else:
            anchor = float(ranked.iloc[-1])
        if len(ranked) >= 41:
            gap = max(float(ranked.iloc[39] - ranked.iloc[40]), 1e-12)
        elif len(ranked) >= 2:
            diffs = ranked.diff(-1).dropna()
            gap = max(float(diffs[diffs > 0].min()) if (diffs > 0).any() else abs(anchor) * 1e-12, 1e-12)
        else:
            gap = max(abs(anchor) * 1e-12, 1e-12)
        for offset, idx in enumerate(light_idx):
            out.loc[idx, "score"] = anchor + gap * (0.05 + offset * 1e-6)
    return out


def top40_changed(base_signal: pd.DataFrame, new_signal: pd.DataFrame) -> float:
    changes = []
    for dt, base_scores in base_signal["score"].groupby(level="datetime"):
        try:
            new_scores = new_signal.loc[(dt, slice(None)), "score"]
        except KeyError:
            continue
        b = set(base_scores.droplevel("datetime").sort_values(ascending=False).head(40).index)
        n = set(new_scores.droplevel("datetime").sort_values(ascending=False).head(40).index)
        changes.append(1.0 - len(b & n) / 40.0)
    return float(pd.Series(changes).mean()) if changes else float("nan")


def setup_runtime() -> None:
    logging.getLogger("qlib").setLevel(logging.ERROR)
    os.chdir(PROJECT)
    os.environ.setdefault("MLFLOW_ALLOW_FILE_STORE", "true")
    for env_name in ["OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"]:
        os.environ.setdefault(env_name, "1")
    for dll_dir in [ROOT / ".venv-qlib" / "Scripts", ROOT / ".venv-qlib"]:
        if dll_dir.exists() and hasattr(os, "add_dll_directory"):
            os.add_dll_directory(str(dll_dir))


def load_qlib_feature(instrument: str, field: str) -> pd.Series:
    cal = pd.to_datetime(pd.read_csv(QLIB_PROVIDER / "calendars" / "day.txt", header=None)[0])
    path = QLIB_PROVIDER / "features" / instrument / f"{field}.day.bin"
    if not path.exists():
        raise FileNotFoundError(f"Missing qlib feature: {path}")
    raw = np.fromfile(path, dtype="<f4")
    start = int(raw[0])
    values = raw[1:]
    idx = cal[start : start + len(values)]
    return pd.Series(values[: len(idx)], index=idx, name=f"{instrument}_{field}").replace([np.inf, -np.inf], np.nan).ffill()


def load_index_close(instrument: str = "sh000905") -> pd.Series:
    return load_qlib_feature(instrument, "close")


def load_index_amount(instrument: str = "sh000905") -> pd.Series:
    return load_qlib_feature(instrument, "amount")


def load_stock_close_frame(instruments: list[str], dates: pd.DatetimeIndex) -> pd.DataFrame:
    frames: dict[str, pd.Series] = {}
    for inst in instruments:
        try:
            s = load_qlib_feature(str(inst).lower(), "close")
        except FileNotFoundError:
            try:
                s = load_qlib_feature(str(inst).upper(), "close")
            except FileNotFoundError:
                continue
        frames[inst] = s.reindex(dates).ffill()
    return pd.DataFrame(frames, index=dates)


def rolling_beta(stock_ret: pd.DataFrame, bench_ret: pd.Series) -> pd.DataFrame:
    bench = bench_ret.reindex(stock_ret.index)
    bench_var = bench.rolling(120, min_periods=60).var()
    out = {}
    for inst in stock_ret.columns:
        out[inst] = stock_ret[inst].rolling(120, min_periods=60).cov(bench) / bench_var
    return pd.DataFrame(out, index=stock_ret.index).shift(1)


def build_constraint_features(signal: pd.DataFrame, valuation: pd.DataFrame) -> pd.DataFrame:
    signal_dates = pd.DatetimeIndex(sorted(signal.index.get_level_values("datetime").unique()))
    instruments = sorted(signal.index.get_level_values("instrument").unique())
    start = signal_dates.min() - pd.Timedelta(days=260)
    end = signal_dates.max()
    cal = pd.to_datetime(pd.read_csv(QLIB_PROVIDER / "calendars" / "day.txt", header=None)[0])
    feature_dates = pd.DatetimeIndex(cal[(cal >= start) & (cal <= end)])
    close = load_stock_close_frame(instruments, feature_dates)
    stock_ret = close.pct_change(fill_method=None)
    bench = load_index_close("sh000905").reindex(feature_dates).ffill().pct_change(fill_method=None)

    beta120 = rolling_beta(stock_ret, bench).reindex(signal_dates)
    vol60 = stock_ret.rolling(60, min_periods=30).std().shift(1).reindex(signal_dates) * math.sqrt(252)

    feat = pd.concat(
        [
            beta120.stack(dropna=False).rename("beta120"),
            vol60.stack(dropna=False).rename("vol60_ann"),
        ],
        axis=1,
    )
    feat.index = feat.index.set_names(["datetime", "instrument"])
    enriched = attach_valuation(signal[["score"]], valuation, lag_trading_days=1)
    out = enriched.join(feat)
    return out


def apply_portfolio_caps_signal(
    signal: pd.DataFrame,
    valuation: pd.DataFrame,
    *,
    variant: str,
    industry_map: dict[str, str],
    topk: int = 40,
    active_dates: pd.DatetimeIndex | None = None,
) -> pd.DataFrame:
    if variant not in {"relay_tie_pcf_cap_soft", "relay_tie_pcf_cap_tight"}:
        return signal
    caps = {
        "relay_tie_pcf_cap_soft": {
            "industry": 10,
            "chinext": 14,
            "small": 20,
            "high_beta": 16,
            "high_vol": 16,
        },
        "relay_tie_pcf_cap_tight": {
            "industry": 8,
            "chinext": 12,
            "small": 16,
            "high_beta": 12,
            "high_vol": 12,
        },
    }[variant]
    active_set = None if active_dates is None else set(pd.DatetimeIndex(active_dates))
    feat = build_constraint_features(signal, valuation)
    out_parts = []
    for dt, scores in signal["score"].groupby(level="datetime", sort=True):
        day = scores.droplevel("datetime").dropna().sort_values(ascending=False, kind="mergesort")
        if active_set is not None and pd.Timestamp(dt) not in active_set:
            out_parts.append(pd.DataFrame({"datetime": dt, "instrument": day.index, "score": day.values}))
            continue
        try:
            fday = feat.loc[(dt, slice(None)), :].droplevel("datetime")
        except KeyError:
            out_parts.append(pd.DataFrame({"datetime": dt, "instrument": day.index, "score": day.values}))
            continue
        selected: list[str] = []
        counts = {"chinext": 0, "small": 0, "high_beta": 0, "high_vol": 0}
        industry_counts: dict[str, int] = {}
        deferred: list[str] = []
        for inst in day.index:
            row = fday.loc[inst] if inst in fday.index else None
            industry = industry_map.get(str(inst).upper(), "UNKNOWN")
            is_chinext = classify_board(inst) == "CHINEXT"
            mcap = pd.to_numeric(row.get("market_cap") if row is not None else np.nan, errors="coerce")
            beta = pd.to_numeric(row.get("beta120") if row is not None else np.nan, errors="coerce")
            vol = pd.to_numeric(row.get("vol60_ann") if row is not None else np.nan, errors="coerce")
            is_small = bool(pd.notna(mcap) and float(mcap) < 100.0)
            is_high_beta = bool(pd.notna(beta) and float(beta) > 1.20)
            is_high_vol = bool(pd.notna(vol) and float(vol) > 0.45)
            blocked = (
                (is_chinext and counts["chinext"] >= caps["chinext"])
                or (is_small and counts["small"] >= caps["small"])
                or (is_high_beta and counts["high_beta"] >= caps["high_beta"])
                or (is_high_vol and counts["high_vol"] >= caps["high_vol"])
                or (industry != "UNKNOWN" and industry_counts.get(industry, 0) >= caps["industry"])
            )
            if blocked:
                deferred.append(inst)
                continue
            selected.append(inst)
            counts["chinext"] += int(is_chinext)
            counts["small"] += int(is_small)
            counts["high_beta"] += int(is_high_beta)
            counts["high_vol"] += int(is_high_vol)
            if industry != "UNKNOWN":
                industry_counts[industry] = industry_counts.get(industry, 0) + 1
            if len(selected) >= topk:
                break
        if len(selected) < topk:
            for inst in day.index:
                if inst not in selected:
                    selected.append(inst)
                if len(selected) >= topk:
                    break
        order = selected + [inst for inst in day.index if inst not in set(selected)]
        n = len(order)
        new_scores = pd.Series(index=day.index, dtype=float)
        for rank, inst in enumerate(order):
            new_scores.loc[inst] = float(n - rank)
        out_parts.append(pd.DataFrame({"datetime": dt, "instrument": new_scores.index, "score": new_scores.values}))
    return pd.concat(out_parts, ignore_index=True).set_index(["datetime", "instrument"]).sort_index()[["score"]]


def consecutive(flag: pd.Series, n: int) -> pd.Series:
    return flag.fillna(False).astype(bool).rolling(n, min_periods=n).sum().ge(n)


def build_bear_gate() -> pd.Series:
    close = load_index_close()
    state = pd.DataFrame(index=close.index)
    state["nav"] = close / close.dropna().iloc[0]
    state["ma60"] = state["nav"].rolling(60, min_periods=60).mean()
    state["ma120"] = state["nav"].rolling(120, min_periods=120).mean()
    state["dd120"] = state["nav"] / state["nav"].rolling(120, min_periods=120).max() - 1.0
    state["ret20"] = state["nav"] / state["nav"].shift(20) - 1.0
    state["ret60"] = state["nav"] / state["nav"].shift(60) - 1.0
    entry = consecutive(state["nav"].lt(state["ma120"]) & state["dd120"].lt(-0.10) & state["ret60"].lt(0.0), 2)
    exit_signal = consecutive(state["nav"].gt(state["ma60"]) | state["ret20"].gt(0.0), 5)

    active = []
    in_bear = False
    for dt in state.index:
        if bool(entry.loc[dt]):
            in_bear = True
        if in_bear and bool(exit_signal.loc[dt]):
            in_bear = False
        active.append(in_bear)
    return pd.Series(active, index=state.index).shift(1).fillna(False).astype(bool)


def build_fastdd_gate() -> pd.Series:
    close = load_index_close()
    state = pd.DataFrame(index=close.index)
    state["nav"] = close / close.dropna().iloc[0]
    state["ma20"] = state["nav"].rolling(20, min_periods=20).mean()
    state["dd20"] = state["nav"] / state["nav"].rolling(20, min_periods=20).max() - 1.0
    state["dd60"] = state["nav"] / state["nav"].rolling(60, min_periods=60).max() - 1.0
    state["ret10"] = state["nav"] / state["nav"].shift(10) - 1.0
    state["ret20"] = state["nav"] / state["nav"].shift(20) - 1.0
    fast_raw = (
        state["dd20"].lt(-0.08)
        | state["ret10"].lt(-0.08)
        | (state["nav"].lt(state["ma20"]) & state["ret20"].lt(-0.06))
        | state["dd60"].lt(-0.12)
    )
    return consecutive(fast_raw, 2).shift(1).fillna(False).astype(bool)


def build_strong_gate() -> pd.Series:
    close = load_index_close()
    state = pd.DataFrame(index=close.index)
    state["nav"] = close / close.dropna().iloc[0]
    state["ma20"] = state["nav"].rolling(20, min_periods=20).mean()
    state["ma60"] = state["nav"].rolling(60, min_periods=60).mean()
    state["ret10"] = state["nav"] / state["nav"].shift(10) - 1.0
    state["ret20"] = state["nav"] / state["nav"].shift(20) - 1.0
    state["ret60"] = state["nav"] / state["nav"].shift(60) - 1.0
    strong_raw = (
        (state["nav"].gt(state["ma20"]) & state["ret10"].gt(0.035))
        | (state["nav"].gt(state["ma20"]) & state["ret20"].gt(0.050))
        | (state["nav"].gt(state["ma60"]) & state["ret60"].gt(0.100))
    )
    return consecutive(strong_raw, 2).shift(1).fillna(False).astype(bool)


def build_strong_cap60_gate(ret60_cap: float = 0.40) -> pd.Series:
    close = load_index_close()
    state = pd.DataFrame(index=close.index)
    state["nav"] = close / close.dropna().iloc[0]
    state["ma20"] = state["nav"].rolling(20, min_periods=20).mean()
    state["ma60"] = state["nav"].rolling(60, min_periods=60).mean()
    state["ret10"] = state["nav"] / state["nav"].shift(10) - 1.0
    state["ret20"] = state["nav"] / state["nav"].shift(20) - 1.0
    state["ret60"] = state["nav"] / state["nav"].shift(60) - 1.0
    strong_raw = (
        (state["nav"].gt(state["ma20"]) & state["ret10"].gt(0.035))
        | (state["nav"].gt(state["ma20"]) & state["ret20"].gt(0.050))
        | (state["nav"].gt(state["ma60"]) & state["ret60"].gt(0.100))
    )
    strong_raw = strong_raw & state["ret60"].lt(ret60_cap)
    return consecutive(strong_raw, 2).shift(1).fillna(False).astype(bool)


def build_fed_ub5_gate(index: pd.DatetimeIndex) -> pd.Series:
    actions = pd.DataFrame(FED_ACTIONS, columns=["action_date", "action", "bps", "upper_bound"])
    actions["action_date"] = pd.to_datetime(actions["action_date"])
    raw = []
    for dt in index:
        prior = actions[actions["action_date"] < pd.Timestamp(dt).normalize()]
        if prior.empty:
            raw.append(False)
        else:
            last = prior.iloc[-1]
            raw.append(bool(last["action"] == "hike" and float(last["upper_bound"]) >= 5.0))
    return pd.Series(raw, index=index).shift(1).fillna(False).astype(bool)


def build_market_regime_profiles(
    *,
    bear_gate: pd.Series,
    fastdd_gate: pd.Series,
    strong_gate: pd.Series,
    fed_gate: pd.Series,
) -> tuple[pd.DataFrame, dict[str, pd.Series]]:
    close_500 = load_index_close("sh000905")
    close_300 = load_index_close("sh000300").reindex(close_500.index).ffill()
    close_1000 = load_index_close("sh000852").reindex(close_500.index).ffill()
    amount_500 = load_index_amount("sh000905").reindex(close_500.index).ffill()
    amount_300 = load_index_amount("sh000300").reindex(close_500.index).ffill()
    amount_1000 = load_index_amount("sh000852").reindex(close_500.index).ffill()

    state = pd.DataFrame(index=close_500.index)
    state["nav_500"] = close_500 / close_500.dropna().iloc[0]
    state["ret20_500"] = state["nav_500"] / state["nav_500"].shift(20) - 1.0
    state["ret60_500"] = state["nav_500"] / state["nav_500"].shift(60) - 1.0
    state["ma60_500"] = state["nav_500"].rolling(60, min_periods=60).mean()
    state["ma120_500"] = state["nav_500"].rolling(120, min_periods=120).mean()
    state["vol20_500"] = state["nav_500"].pct_change().rolling(20, min_periods=20).std() * math.sqrt(252)

    rel_1000_300 = (close_1000 / close_1000.dropna().iloc[0]) / (close_300 / close_300.dropna().iloc[0])
    rel_500_300 = state["nav_500"] / (close_300 / close_300.dropna().iloc[0])
    state["small_mid_rel20"] = rel_1000_300 / rel_1000_300.shift(20) - 1.0
    state["mid_rel20"] = rel_500_300 / rel_500_300.shift(20) - 1.0

    amount_sum = amount_500 + amount_300 + amount_1000
    amount_ratio60 = amount_sum / amount_sum.rolling(60, min_periods=60).mean()
    vol_q75 = state["vol20_500"].rolling(252, min_periods=120).quantile(0.75)
    state["amount_crowded"] = amount_ratio60.gt(1.35)
    state["amount_cold"] = amount_ratio60.lt(0.80)
    state["high_vol"] = state["vol20_500"].gt(vol_q75)
    state["small_mid_strong"] = state["small_mid_rel20"].gt(0.02) | state["mid_rel20"].gt(0.01)
    state["small_mid_weak"] = state["small_mid_rel20"].lt(-0.02) | state["mid_rel20"].lt(-0.01)
    state["index_downtrend"] = state["nav_500"].lt(state["ma120_500"]) & state["ret20_500"].lt(0.0)

    aligned_bear = bear_gate.reindex(state.index).fillna(False).astype(bool)
    aligned_fastdd = fastdd_gate.reindex(state.index).fillna(False).astype(bool)
    aligned_strong = strong_gate.reindex(state.index).fillna(False).astype(bool)
    aligned_fed = fed_gate.reindex(state.index).fillna(False).astype(bool)

    state["risk_off"] = aligned_bear | aligned_fed | aligned_fastdd | (state["index_downtrend"] & state["high_vol"])
    state["risk_on"] = aligned_strong & state["small_mid_strong"] & ~state["high_vol"] & ~aligned_fed
    state["regime"] = "neutral"
    state.loc[state["risk_on"], "regime"] = "risk_on_small_mid"
    state.loc[state["risk_off"], "regime"] = "risk_off"
    state.loc[aligned_fastdd, "regime"] = "fast_drawdown"

    base = pd.Series(BASE_RISK_DEGREE, index=state.index)
    risk_degree = pd.concat(
        [
            base,
            base.where(~state["risk_on"], 1.00),
            base.where(~state["risk_off"], BASE_RISK_DEGREE * 0.70),
            base.where(~aligned_fastdd, BASE_RISK_DEGREE * 0.50),
        ],
        axis=1,
    ).min(axis=1)
    risk_degree = risk_degree.where(~state["risk_on"], 1.00)

    topk_adjust = pd.Series(0, index=state.index, dtype="int64")
    topk_adjust = topk_adjust.mask(state["risk_on"], 10)
    topk_adjust = topk_adjust.mask(state["risk_off"], -5)
    topk_adjust = topk_adjust.mask(aligned_fastdd, -10)

    ndrop_adjust = pd.Series(0, index=state.index, dtype="int64")
    ndrop_adjust = ndrop_adjust.mask(state["risk_on"], 1)
    ndrop_adjust = ndrop_adjust.mask(state["risk_off"], -1)
    ndrop_adjust = ndrop_adjust.mask(aligned_fastdd, -2)

    pcf_enabled = pd.Series(True, index=state.index)
    pcf_enabled = pcf_enabled.mask(state["risk_on"] & ~state["amount_crowded"], False)
    pcf_enabled = pcf_enabled.mask(state["risk_off"] | state["amount_crowded"], True)
    pcf_strong = (
        aligned_fastdd
        | state["amount_crowded"]
        | state["amount_cold"]
        | state["small_mid_weak"]
        | (state["index_downtrend"] & state["high_vol"])
    )
    bad_state_cap = (
        aligned_fastdd
        | state["amount_crowded"]
        | (state["high_vol"] & state["small_mid_weak"])
        | (state["high_vol"] & state["index_downtrend"])
    )

    profiles = {
        "risk_gate": state["risk_off"].astype(bool),
        "risk_degree": risk_degree.astype(float),
        "topk_adjust": topk_adjust.astype("int64"),
        "ndrop_adjust": ndrop_adjust.astype("int64"),
        "pcf_enabled": pcf_enabled.astype(bool),
        "pcf_strong": pcf_strong.astype(bool),
        "bad_state_cap": bad_state_cap.astype(bool),
        "layered_small_mid": state["small_mid_strong"].shift(1).fillna(False).astype(bool),
    }
    return state, profiles


def make_strategy_class():
    import copy

    import numpy as np
    import pandas as pd
    from qlib.backtest.decision import Order, OrderDir, TradeDecisionWO
    from qlib.backtest.position import Position
    from qlib.contrib.strategy.signal_strategy import TopkDropoutStrategy

    class RiskGateTopkDropoutStrategy(TopkDropoutStrategy):
        def __init__(
            self,
            *,
            risk_degree_series: pd.Series,
            topk_series: pd.Series | None = None,
            n_drop_series: pd.Series | None = None,
            force_deleverage: bool = False,
            use_custom_trade_path: bool = False,
            **kwargs,
        ):
            super().__init__(**kwargs)
            self.risk_degree_series = risk_degree_series
            self.topk_series = topk_series
            self.n_drop_series = n_drop_series
            self.force_deleverage = bool(force_deleverage)
            self.use_custom_trade_path = bool(use_custom_trade_path)

        def _dt_for_step(self) -> pd.Timestamp:
            trade_step = self.trade_calendar.get_trade_step()
            trade_start_time, _ = self.trade_calendar.get_step_time(trade_step)
            return pd.Timestamp(trade_start_time).normalize()

        def _risk_degree_for_step(self) -> float:
            dt = self._dt_for_step()
            return float(self.risk_degree_series.get(dt, self.risk_degree))

        def _topk_for_step(self) -> int:
            if self.topk_series is None:
                return int(self.topk)
            dt = self._dt_for_step()
            return max(1, int(self.topk_series.get(dt, self.topk)))

        def _n_drop_for_step(self) -> int:
            if self.n_drop_series is None:
                return int(self.n_drop)
            dt = self._dt_for_step()
            return max(0, int(self.n_drop_series.get(dt, self.n_drop)))

        def generate_trade_decision(self, execute_result=None):
            old_risk_degree = self.risk_degree
            old_topk = self.topk
            old_n_drop = self.n_drop
            self.risk_degree = self._risk_degree_for_step()
            self.topk = self._topk_for_step()
            self.n_drop = self._n_drop_for_step()
            try:
                if self.force_deleverage or self.use_custom_trade_path:
                    return self._generate_trade_decision_with_forced_exposure(execute_result=execute_result)
                return super().generate_trade_decision(execute_result=execute_result)
            finally:
                self.risk_degree = old_risk_degree
                self.topk = old_topk
                self.n_drop = old_n_drop

        def _generate_trade_decision_with_forced_exposure(self, execute_result=None):
            trade_step = self.trade_calendar.get_trade_step()
            trade_start_time, trade_end_time = self.trade_calendar.get_step_time(trade_step)
            pred_start_time, pred_end_time = self.trade_calendar.get_step_time(trade_step, shift=1)
            pred_score = self.signal.get_signal(start_time=pred_start_time, end_time=pred_end_time)
            if isinstance(pred_score, pd.DataFrame):
                pred_score = pred_score.iloc[:, 0]
            if pred_score is None:
                return TradeDecisionWO([], self)

            if self.only_tradable:
                def get_first_n(li, n, reverse=False):
                    cur_n = 0
                    res = []
                    for si in reversed(li) if reverse else li:
                        if self.trade_exchange.is_stock_tradable(
                            stock_id=si, start_time=trade_start_time, end_time=trade_end_time
                        ):
                            res.append(si)
                            cur_n += 1
                            if cur_n >= n:
                                break
                    return res[::-1] if reverse else res

                def get_last_n(li, n):
                    return get_first_n(li, n, reverse=True)
            else:
                def get_first_n(li, n):
                    return list(li)[:n]

                def get_last_n(li, n):
                    return list(li)[-n:]

            current_temp: Position = copy.deepcopy(self.trade_position)
            sell_order_list = []
            buy_order_list = []
            cash = current_temp.get_cash()
            current_stock_list = current_temp.get_stock_list()
            last = pred_score.reindex(current_stock_list).sort_values(ascending=False).index

            if self.method_buy == "top":
                today = get_first_n(
                    pred_score[~pred_score.index.isin(last)].sort_values(ascending=False).index,
                    self.n_drop + self.topk - len(last),
                )
            elif self.method_buy == "random":
                topk_candi = get_first_n(pred_score.sort_values(ascending=False).index, self.topk)
                candi = list(filter(lambda x: x not in last, topk_candi))
                n = self.n_drop + self.topk - len(last)
                try:
                    today = np.random.choice(candi, n, replace=False)
                except ValueError:
                    today = candi
            else:
                raise NotImplementedError(f"This type of input is not supported")

            comb = pred_score.reindex(last.union(pd.Index(today))).sort_values(ascending=False).index
            if self.method_sell == "bottom":
                sell = last[last.isin(get_last_n(comb, self.n_drop))]
            elif self.method_sell == "random":
                candi = last
                try:
                    sell = pd.Index(np.random.choice(candi, self.n_drop, replace=False) if len(last) else [])
                except ValueError:
                    sell = candi
            else:
                raise NotImplementedError(f"This type of input is not supported")

            buy = today[: len(sell) + self.topk - len(last)]
            time_per_step = self.trade_calendar.get_freq()

            for code in current_stock_list:
                if not self.trade_exchange.is_stock_tradable(
                    stock_id=code,
                    start_time=trade_start_time,
                    end_time=trade_end_time,
                    direction=None if self.forbid_all_trade_at_limit else OrderDir.SELL,
                ):
                    continue
                if code in sell:
                    if current_temp.get_stock_count(code, bar=time_per_step) < self.hold_thresh:
                        continue
                    sell_amount = current_temp.get_stock_amount(code=code)
                    sell_order = Order(
                        stock_id=code,
                        amount=sell_amount,
                        start_time=trade_start_time,
                        end_time=trade_end_time,
                        direction=Order.SELL,
                    )
                    if self.trade_exchange.check_order(sell_order):
                        sell_order_list.append(sell_order)
                        trade_val, trade_cost, _ = self.trade_exchange.deal_order(sell_order, position=current_temp)
                        cash += trade_val - trade_cost

            target_stock_value = self.risk_degree * current_temp.calculate_value()
            current_stock_value = current_temp.calculate_stock_value()
            excess_stock_value = current_stock_value - target_stock_value
            if excess_stock_value > 0 and current_stock_value > 0:
                trim_fraction = min(1.0, excess_stock_value / current_stock_value)
                for code in list(current_temp.get_stock_list()):
                    if not self.trade_exchange.is_stock_tradable(
                        stock_id=code,
                        start_time=trade_start_time,
                        end_time=trade_end_time,
                        direction=None if self.forbid_all_trade_at_limit else OrderDir.SELL,
                    ):
                        continue
                    if current_temp.get_stock_count(code, bar=time_per_step) < self.hold_thresh:
                        continue
                    sell_amount = current_temp.get_stock_amount(code=code) * trim_fraction
                    if sell_amount <= 0:
                        continue
                    sell_order = Order(
                        stock_id=code,
                        amount=sell_amount,
                        start_time=trade_start_time,
                        end_time=trade_end_time,
                        direction=Order.SELL,
                    )
                    if self.trade_exchange.check_order(sell_order):
                        sell_order_list.append(sell_order)
                        trade_val, trade_cost, _ = self.trade_exchange.deal_order(sell_order, position=current_temp)
                        cash += trade_val - trade_cost

            value = cash * self.risk_degree / len(buy) if len(buy) > 0 else 0
            for code in buy:
                if not self.trade_exchange.is_stock_tradable(
                    stock_id=code,
                    start_time=trade_start_time,
                    end_time=trade_end_time,
                    direction=None if self.forbid_all_trade_at_limit else OrderDir.BUY,
                ):
                    continue
                buy_price = self.trade_exchange.get_deal_price(
                    stock_id=code,
                    start_time=trade_start_time,
                    end_time=trade_end_time,
                    direction=OrderDir.BUY,
                )
                buy_amount = value / buy_price
                factor = self.trade_exchange.get_factor(
                    stock_id=code,
                    start_time=trade_start_time,
                    end_time=trade_end_time,
                )
                buy_amount = self.trade_exchange.round_amount_by_trade_unit(buy_amount, factor)
                buy_order = Order(
                    stock_id=code,
                    amount=buy_amount,
                    start_time=trade_start_time,
                    end_time=trade_end_time,
                    direction=Order.BUY,
                )
                buy_order_list.append(buy_order)
            return TradeDecisionWO(sell_order_list + buy_order_list, self)

    return RiskGateTopkDropoutStrategy


def init_worker() -> None:
    global _VALUATION, _STRATEGY_CLASS, _RISK_GATES, _RISK_DEGREES, _TOPK_ADJUST, _NDROP_ADJUST, _PCF_ENABLED, _PCF_STRONG, _MARKET_REGIME, _INDUSTRY_MAP
    setup_runtime()
    import qlib

    qlib.init(
        provider_uri=str(QLIB_PROVIDER),
        region="cn",
        kernels=1,
        expression_cache=None,
        dataset_cache=None,
        maxtasksperchild=1,
        joblib_backend="loky",
    )
    val = pd.read_parquet(VAL_PATH) if VAL_PATH.suffix.lower() in {".parquet", ".pq"} else pd.read_csv(VAL_PATH)
    for col in ["market_cap", "pe_ttm", "pb"]:
        if col not in val.columns:
            val[col] = np.nan
    val["datetime"] = pd.to_datetime(val["datetime"], errors="coerce")
    _VALUATION = val.dropna(subset=["datetime"])
    _INDUSTRY_MAP = load_industry_map()
    _STRATEGY_CLASS = make_strategy_class()
    bear_gate = build_bear_gate()
    fastdd_gate = build_fastdd_gate().reindex(bear_gate.index).fillna(False).astype(bool)
    strong_gate = build_strong_gate().reindex(bear_gate.index).fillna(False).astype(bool)
    strong_cap60_gate = build_strong_cap60_gate(0.40).reindex(bear_gate.index).fillna(False).astype(bool)
    fed_gate = build_fed_ub5_gate(pd.DatetimeIndex(bear_gate.index))
    danger_gate = bear_gate | fed_gate
    regime_state, regime_profiles = build_market_regime_profiles(
        bear_gate=bear_gate,
        fastdd_gate=fastdd_gate,
        strong_gate=strong_gate,
        fed_gate=fed_gate,
    )
    _MARKET_REGIME = regime_state
    base = pd.Series(BASE_RISK_DEGREE, index=bear_gate.index)
    fed_variants = {f"relay_tie_pcf_fed{int(mult * 100):02d}": fed_gate for mult in FED_RISK_MULTIPLIERS}
    fed_risk_degrees = {
        f"relay_tie_pcf_fed{int(mult * 100):02d}": base.where(~fed_gate, BASE_RISK_DEGREE * mult)
        for mult in FED_RISK_MULTIPLIERS
    }
    _RISK_GATES = {
        "relay_tie": pd.Series(False, index=bear_gate.index),
        "relay_tie_strong100": strong_gate,
        "relay_tie_strong110": strong_gate,
        "relay_tie_strong100_cap60_40": strong_cap60_gate,
        "relay_tie_pcf": pd.Series(False, index=bear_gate.index),
        "relay_tie_pcf_layered": pd.Series(False, index=bear_gate.index),
        "relay_tie_pcf_layered_smallmid": regime_profiles["layered_small_mid"],
        "relay_tie_pcf_strong100": strong_gate,
        "relay_tie_pcf_strong110": strong_gate,
        "relay_tie_pcf_strong100_cap60_40": strong_cap60_gate,
        **fed_variants,
        "relay_tie_pcf_bear70_only": bear_gate,
        "relay_tie_pcf_danger70": danger_gate,
        "relay_tie_pcf_fastdd50": fastdd_gate,
        "relay_tie_pcf_danger50_fastdd30": danger_gate | fastdd_gate,
        "relay_tie_pcf_fastdd50_force": fastdd_gate,
        "relay_tie_pcf_danger50_fastdd30_force": danger_gate | fastdd_gate,
        "relay_tie_pcf_regime": regime_profiles["risk_gate"],
        "relay_tie_pcf_state85": regime_profiles["pcf_strong"],
        "relay_tie_pcf_state70": regime_profiles["pcf_strong"],
        "relay_tie_pcf_strongpcf": pd.Series(False, index=bear_gate.index),
        "relay_tie_pcf_strongpcf_state85": regime_profiles["pcf_strong"],
        "relay_tie_pcf_cap_soft": pd.Series(False, index=bear_gate.index),
        "relay_tie_pcf_cap_tight": pd.Series(False, index=bear_gate.index),
        "relay_tie_pcf_bad_state_cap": regime_profiles["bad_state_cap"],
        "relay_tie_pcf_bad_state_relay": regime_profiles["bad_state_cap"],
    }
    _RISK_DEGREES = {
        "relay_tie": base.copy(),
        "relay_tie_strong100": base.where(~strong_gate, 1.00),
        "relay_tie_strong110": base.where(~strong_gate, 1.10),
        "relay_tie_strong100_cap60_40": base.where(~strong_cap60_gate, 1.00),
        "relay_tie_pcf": base.copy(),
        "relay_tie_pcf_layered": base.copy(),
        "relay_tie_pcf_layered_smallmid": base.copy(),
        "relay_tie_pcf_strong100": base.where(~strong_gate, 1.00),
        "relay_tie_pcf_strong110": base.where(~strong_gate, 1.10),
        "relay_tie_pcf_strong100_cap60_40": base.where(~strong_cap60_gate, 1.00),
        **fed_risk_degrees,
        "relay_tie_pcf_bear70_only": base.where(~bear_gate, BASE_RISK_DEGREE * 0.70),
        "relay_tie_pcf_danger70": base.where(~danger_gate, BASE_RISK_DEGREE * 0.70),
        "relay_tie_pcf_fastdd50": base.where(~fastdd_gate, BASE_RISK_DEGREE * 0.50),
        "relay_tie_pcf_danger50_fastdd30": pd.concat(
            [
                base.where(~danger_gate, BASE_RISK_DEGREE * 0.50),
                base.where(~fastdd_gate, BASE_RISK_DEGREE * 0.30),
            ],
            axis=1,
        ).min(axis=1),
        "relay_tie_pcf_fastdd50_force": base.where(~fastdd_gate, BASE_RISK_DEGREE * 0.50),
        "relay_tie_pcf_danger50_fastdd30_force": pd.concat(
            [
                base.where(~danger_gate, BASE_RISK_DEGREE * 0.50),
                base.where(~fastdd_gate, BASE_RISK_DEGREE * 0.30),
            ],
            axis=1,
        ).min(axis=1),
        "relay_tie_pcf_regime": regime_profiles["risk_degree"],
        "relay_tie_pcf_state85": base.where(~regime_profiles["pcf_strong"], BASE_RISK_DEGREE * 0.85),
        "relay_tie_pcf_state70": base.where(~regime_profiles["pcf_strong"], BASE_RISK_DEGREE * 0.70),
        "relay_tie_pcf_strongpcf": base.copy(),
        "relay_tie_pcf_strongpcf_state85": base.where(~regime_profiles["pcf_strong"], BASE_RISK_DEGREE * 0.85),
        "relay_tie_pcf_cap_soft": base.copy(),
        "relay_tie_pcf_cap_tight": base.copy(),
        "relay_tie_pcf_bad_state_cap": base.copy(),
        "relay_tie_pcf_bad_state_relay": base.copy(),
    }
    zero_adjust = pd.Series(0, index=bear_gate.index, dtype="int64")
    pcf_on = pd.Series(True, index=bear_gate.index)
    variant_names = set(_RISK_DEGREES)
    _TOPK_ADJUST = {variant: zero_adjust.copy() for variant in variant_names}
    _NDROP_ADJUST = {variant: zero_adjust.copy() for variant in variant_names}
    _PCF_ENABLED = {variant: pcf_on.copy() for variant in variant_names}
    _PCF_STRONG = {variant: pd.Series(False, index=bear_gate.index) for variant in variant_names}
    _TOPK_ADJUST["relay_tie_pcf_regime"] = regime_profiles["topk_adjust"]
    _NDROP_ADJUST["relay_tie_pcf_regime"] = regime_profiles["ndrop_adjust"]
    _PCF_ENABLED["relay_tie_pcf_regime"] = regime_profiles["pcf_enabled"]
    _PCF_ENABLED["relay_tie_pcf_bad_state_relay"] = ~regime_profiles["bad_state_cap"]
    for variant in ["relay_tie_pcf_strongpcf", "relay_tie_pcf_strongpcf_state85"]:
        _PCF_STRONG[variant] = regime_profiles["pcf_strong"]


def combine_pcf_by_gate(relay_signal: pd.DataFrame, pcf_signal: pd.DataFrame, enabled: pd.Series) -> pd.DataFrame:
    out = relay_signal[["score"]].copy()
    enabled = enabled.reindex(pd.DatetimeIndex(sorted(out.index.get_level_values("datetime").unique()))).fillna(True).astype(bool)
    enabled_dates = set(enabled[enabled].index)
    dt_index = out.index.get_level_values("datetime")
    out.loc[dt_index.isin(enabled_dates), "score"] = pcf_signal.loc[dt_index.isin(enabled_dates), "score"].values
    return stabilize_signal(out)


def run_backtest(signal: pd.DataFrame, cfg: dict[str, Any], dates: dict[str, str], variant: str) -> tuple[pd.DataFrame, Any]:
    from qlib.backtest import backtest, executor

    if _STRATEGY_CLASS is None or _RISK_GATES is None or _RISK_DEGREES is None or _TOPK_ADJUST is None or _NDROP_ADJUST is None:
        raise RuntimeError("worker not initialized")

    scfg = cfg["port_analysis_config"]["strategy"]["kwargs"]
    bcfg = cfg["port_analysis_config"]["backtest"]
    risk_gate = _RISK_GATES[variant]
    risk_degree_series = _RISK_DEGREES[variant]
    base_topk = int(scfg["topk"])
    base_n_drop = int(scfg["n_drop"])
    topk_series = (pd.Series(base_topk, index=risk_degree_series.index) + _TOPK_ADJUST[variant]).clip(lower=1).astype(int)
    n_drop_series = (pd.Series(base_n_drop, index=risk_degree_series.index) + _NDROP_ADJUST[variant]).clip(lower=0).astype(int)
    strategy = _STRATEGY_CLASS(
        signal=signal["score"],
        topk=base_topk,
        n_drop=base_n_drop,
        risk_degree_series=risk_degree_series,
        topk_series=topk_series,
        n_drop_series=n_drop_series,
        force_deleverage=variant.endswith("_force"),
        use_custom_trade_path=variant
        in {"relay_tie_pcf_cap_soft", "relay_tie_pcf_cap_tight", "relay_tie_pcf_bad_state_cap"},
    )
    report_dict, _ = backtest(
        executor=executor.SimulatorExecutor(time_per_step="day", generate_portfolio_metrics=True),
        strategy=strategy,
        start_time=dates["relay_start"],
        end_time=dates["relay_end"],
        account=bcfg["account"],
        benchmark=bcfg["benchmark"],
        exchange_kwargs={
            "freq": "day",
            "limit_threshold": bcfg["exchange_kwargs"]["limit_threshold"],
            "deal_price": bcfg["exchange_kwargs"]["deal_price"],
            "open_cost": bcfg["exchange_kwargs"]["open_cost"],
            "close_cost": bcfg["exchange_kwargs"]["close_cost"],
            "min_cost": bcfg["exchange_kwargs"]["min_cost"],
        },
    )
    report, positions = report_dict["1day"]
    report.index = pd.to_datetime(report.index)
    report = report.sort_index()
    eval_report = report.loc[
        (report.index >= pd.Timestamp(dates["eval_start"])) & (report.index <= pd.Timestamp(dates["eval_end"]))
    ].copy()
    eval_report["risk_degree"] = risk_degree_series.reindex(eval_report.index).fillna(BASE_RISK_DEGREE).astype(float)
    eval_report["risk_gate"] = risk_gate.reindex(eval_report.index).fillna(False).astype(bool)
    eval_report["topk"] = topk_series.reindex(eval_report.index).fillna(base_topk).astype(int)
    eval_report["n_drop"] = n_drop_series.reindex(eval_report.index).fillna(base_n_drop).astype(int)
    if _PCF_ENABLED is not None and variant in _PCF_ENABLED:
        eval_report["pcf_enabled"] = _PCF_ENABLED[variant].reindex(eval_report.index).fillna(True).astype(bool)
    if _PCF_STRONG is not None and variant in _PCF_STRONG:
        eval_report["pcf_strong"] = _PCF_STRONG[variant].reindex(eval_report.index).fillna(False).astype(bool)
    if _MARKET_REGIME is not None:
        eval_report["market_regime"] = _MARKET_REGIME["regime"].reindex(eval_report.index).fillna("neutral").astype(str)
    return eval_report, positions


def calc_metrics(report: pd.DataFrame) -> dict[str, float | int]:
    port = pd.to_numeric(report["return"], errors="coerce").fillna(0.0) - pd.to_numeric(report["cost"], errors="coerce").fillna(0.0)
    bench = pd.to_numeric(report["bench"], errors="coerce").fillna(0.0)
    excess = port - bench
    gross_excess = pd.to_numeric(report["return"], errors="coerce").fillna(0.0) - bench
    nav = (1.0 + port).cumprod()
    bnav = (1.0 + bench).cumprod()
    ex_nav = (1.0 + excess).cumprod()
    std = port.std(ddof=1)
    ex_std = excess.std(ddof=1)
    turnover = pd.to_numeric(report.get("turnover", pd.Series(0.0, index=report.index)), errors="coerce").fillna(0.0)
    cost = pd.to_numeric(report["cost"], errors="coerce").fillna(0.0)
    return {
        "days": int(len(report)),
        "total_return": float(nav.iloc[-1] - 1.0),
        "benchmark_total_return": float(bnav.iloc[-1] - 1.0),
        "excess_sum": float(excess.sum()),
        "gross_excess_sum": float(gross_excess.sum()),
        "net_ann_excess": float(excess.mean() * 252),
        "gross_ann_excess": float(gross_excess.mean() * 252),
        "ann_return": float(nav.iloc[-1] ** (252 / len(report)) - 1.0),
        "sharpe": float(port.mean() / std * math.sqrt(252)) if std and not pd.isna(std) else float("nan"),
        "excess_ir": float(excess.mean() / ex_std * math.sqrt(252)) if ex_std and not pd.isna(ex_std) else float("nan"),
        "mdd": float((nav / nav.cummax() - 1.0).min()),
        "excess_mdd": float((ex_nav / ex_nav.cummax() - 1.0).min()),
        "cost_sum": float(cost.sum()),
        "turnover_sum": float(turnover.sum()),
        "avg_turnover": float(turnover.mean()),
        "avg_risk_degree": float(pd.to_numeric(report["risk_degree"], errors="coerce").mean()),
        "risk_days": int((pd.to_numeric(report["risk_degree"], errors="coerce") < BASE_RISK_DEGREE).sum()),
        "risk_gate_days": int(pd.Series(report.get("risk_gate", pd.Series(False, index=report.index))).fillna(False).astype(bool).sum()),
        "avg_topk": float(pd.to_numeric(report.get("topk", pd.Series(np.nan, index=report.index)), errors="coerce").mean()),
        "avg_n_drop": float(pd.to_numeric(report.get("n_drop", pd.Series(np.nan, index=report.index)), errors="coerce").mean()),
        "pcf_enabled_days": int(pd.Series(report.get("pcf_enabled", pd.Series(False, index=report.index))).fillna(False).astype(bool).sum()),
        "pcf_strong_days": int(pd.Series(report.get("pcf_strong", pd.Series(False, index=report.index))).fillna(False).astype(bool).sum()),
    }


def file_fingerprint(path: Path) -> dict[str, Any]:
    stat = path.stat()
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return {"path": str(path), "size": stat.st_size, "mtime_ns": stat.st_mtime_ns, "sha256": h.hexdigest()}


def run_case_variant(task: tuple[str, str, str] | tuple[str, str, str, str]) -> tuple[dict[str, Any], pd.DataFrame]:
    if len(task) == 3:
        case_name, variant, out_dir_str = task
        pred_source = "purged"
    else:
        case_name, variant, out_dir_str, pred_source = task
    if _VALUATION is None or _PCF_ENABLED is None or _PCF_STRONG is None or _INDUSTRY_MAP is None:
        raise RuntimeError("worker not initialized")
    pred_paths = pred_by_source(pred_source)
    prev_name = previous_period(case_name)
    prev_pred = load_pred(pred_paths[prev_name])
    curr_pred_path, gate_meta = gated_curr_pred_path(case_name, pred_paths)
    curr_pred = load_pred(curr_pred_path)
    dates = infer_dates(prev_pred, curr_pred)
    cfg = load_yaml(yaml_path(case_name, pred_source=pred_source))

    relay_signal = stabilize_signal(combine_preds(prev_pred, curr_pred, switch_date=dates["switch_date"]))
    if "pcf" not in variant:
        final_signal = relay_signal
        changed = 0.0
        pcf_cov = float("nan")
        pcf_enabled_frac = float("nan")
        pcf_strong_frac = float("nan")
    else:
        enriched = attach_valuation(relay_signal, _VALUATION, lag_trading_days=1)
        if variant == "relay_tie_pcf_layered":
            pcf_signal = stabilize_signal(apply_pcf_layered(enriched))
        elif variant == "relay_tie_pcf_layered_smallmid":
            hard_signal = stabilize_signal(apply_pcf_q90(enriched))
            layered_signal = stabilize_signal(apply_pcf_layered(enriched))
            pcf_signal = combine_pcf_by_gate(hard_signal, layered_signal, _RISK_GATES[variant])
        else:
            pcf_signal = stabilize_signal(apply_pcf_q90(enriched))
        pcf_enabled = _PCF_ENABLED[variant]
        pcf_strong = _PCF_STRONG[variant]
        if variant in {"relay_tie_pcf_regime", "relay_tie_pcf_bad_state_relay"}:
            final_signal = combine_pcf_by_gate(relay_signal, pcf_signal, pcf_enabled)
        elif bool(pcf_strong.any()):
            strong_signal = stabilize_signal(apply_pcf_filter(enriched, edge_start=31, edge_end=40, expensive_quantile=0.80))
            final_signal = combine_pcf_by_gate(pcf_signal, strong_signal, pcf_strong)
        else:
            final_signal = pcf_signal
        if variant in {"relay_tie_pcf_cap_soft", "relay_tie_pcf_cap_tight", "relay_tie_pcf_bad_state_cap"}:
            topk = int(cfg["port_analysis_config"]["strategy"]["kwargs"]["topk"])
            cap_variant = "relay_tie_pcf_cap_tight" if variant == "relay_tie_pcf_bad_state_cap" else variant
            active_dates = None
            if variant == "relay_tie_pcf_bad_state_cap":
                cap_gate = _RISK_GATES[variant]
                signal_dates = pd.DatetimeIndex(sorted(final_signal.index.get_level_values("datetime").unique()))
                active_dates = pd.DatetimeIndex(cap_gate.reindex(signal_dates).fillna(False).astype(bool).loc[lambda s: s].index)
            final_signal = stabilize_signal(
                apply_portfolio_caps_signal(
                    final_signal,
                    _VALUATION,
                    variant=cap_variant,
                    industry_map=_INDUSTRY_MAP,
                    topk=topk,
                    active_dates=active_dates,
                )
            )
        changed = top40_changed(relay_signal.loc[final_signal.index], final_signal)
        pcf_cov = float(enriched["pcf"].notna().mean())
        signal_dates = pd.DatetimeIndex(sorted(final_signal.index.get_level_values("datetime").unique()))
        pcf_enabled_frac = float(pcf_enabled.reindex(signal_dates).fillna(True).astype(bool).mean())
        pcf_strong_frac = float(pcf_strong.reindex(signal_dates).fillna(False).astype(bool).mean())

    report, _positions = run_backtest(final_signal, cfg, dates, variant)
    if report.empty:
        raise ValueError(f"{case_name} {variant}: empty eval report {dates['eval_start']} to {dates['eval_end']}")

    out_case = Path(out_dir_str) / variant / case_name
    out_case.mkdir(parents=True, exist_ok=True)
    report.reset_index().rename(columns={"index": "datetime"}).to_csv(out_case / "report_eval.csv", index=False, encoding="utf-8-sig")
    if variant in {
        "relay_tie",
        "relay_tie_pcf",
        "relay_tie_pcf_layered",
        "relay_tie_pcf_layered_smallmid",
        "relay_tie_pcf_regime",
        "relay_tie_pcf_cap_soft",
        "relay_tie_pcf_cap_tight",
        "relay_tie_pcf_bad_state_cap",
        "relay_tie_pcf_bad_state_relay",
    }:
        final_signal.reset_index().to_parquet(out_case / "signal.parquet", index=False)

    row = {
        "case": case_name,
        "variant": variant,
        "prev_case": prev_name,
        **dates,
        **calc_metrics(report),
        "top40_changed_frac": changed,
        "pcf_valuation_coverage": pcf_cov,
        "pcf_enabled_frac": pcf_enabled_frac,
        "pcf_strong_frac": pcf_strong_frac,
        "pred_source": pred_source,
        "prev_pred": str(pred_paths[prev_name]),
        "curr_pred": str(curr_pred_path),
        **gate_meta,
        "yaml": str(yaml_path(case_name, pred_source=pred_source)),
    }
    return row, report.assign(case=case_name, variant=variant).reset_index().rename(columns={"index": "datetime"})


def compare_to_baseline(periods: pd.DataFrame) -> pd.DataFrame:
    base = periods[periods["variant"].eq("relay_tie")].set_index("case")
    rows = []
    for _, r in periods[~periods["variant"].eq("relay_tie")].iterrows():
        b = base.loc[r["case"]]
        rows.append(
            {
                "case": r["case"],
                "variant": r["variant"],
                "baseline_total": b["total_return"],
                "variant_total": r["total_return"],
                "bench_total": r["benchmark_total_return"],
                "total_diff": r["total_return"] - b["total_return"],
                "excess_sum_diff": r["excess_sum"] - b["excess_sum"],
                "ann_excess_diff": r["net_ann_excess"] - b["net_ann_excess"],
                "mdd_diff": r["mdd"] - b["mdd"],
                "excess_ir_diff": r["excess_ir"] - b["excess_ir"],
                "turnover_diff": r["turnover_sum"] - b["turnover_sum"],
                "avg_risk_degree": r["avg_risk_degree"],
                "risk_days": r["risk_days"],
                "risk_gate_days": r.get("risk_gate_days", 0),
                "top40_changed_frac": r["top40_changed_frac"],
                "year": int(str(r["case"])[:4]),
            }
        )
    return pd.DataFrame(rows).sort_values(["variant", "case"])


def aggregate(comp: pd.DataFrame) -> pd.DataFrame:
    windows = {
        "all": pd.Series(True, index=comp.index),
        "ex_2026ytd": comp["case"].ne("2026YTD"),
        "early_2015_2017": comp["year"].between(2015, 2017),
        "train_2018_2022": comp["year"].between(2018, 2022),
        "forward_2023_2026": comp["year"].between(2023, 2026),
    }
    rows = []
    for variant, g in comp.groupby("variant"):
        for window, mask in windows.items():
            sub = g[mask.loc[g.index]]
            rows.append(
                {
                    "variant": variant,
                    "window": window,
                    "cases": int(len(sub)),
                    "avg_total_diff": sub["total_diff"].mean(),
                    "win_total": int((sub["total_diff"] > 0).sum()),
                    "avg_excess_sum_diff": sub["excess_sum_diff"].mean(),
                    "win_excess_sum": int((sub["excess_sum_diff"] > 0).sum()),
                    "avg_ann_excess_diff": sub["ann_excess_diff"].mean(),
                    "avg_mdd_diff": sub["mdd_diff"].mean(),
                    "better_mdd": int((sub["mdd_diff"] > 0).sum()),
                    "avg_ir_diff": sub["excess_ir_diff"].mean(),
                    "avg_risk_degree": sub["avg_risk_degree"].mean(),
                    "avg_risk_days": sub["risk_days"].mean(),
                    "avg_risk_gate_days": sub["risk_gate_days"].mean(),
                    "avg_top40_changed": sub["top40_changed_frac"].mean(),
                }
            )
    return pd.DataFrame(rows).sort_values(["variant", "window"])


def pct(x: float) -> str:
    return "NA" if pd.isna(x) else f"{x:.2%}"


def num(x: float) -> str:
    return "NA" if pd.isna(x) else f"{x:.4f}"


def make_report(periods: pd.DataFrame, comp: pd.DataFrame, agg: pd.DataFrame, meta: dict[str, Any]) -> str:
    lines = [
        "# Formal Full HL378 mw2e4 Relay PCF Risk Qlib Backtest",
        "",
        "Fresh qlib run from pred files. No prior report files are used as inputs.",
        "",
        "Causality: relay switches at current pred first day; exact ties are stabilized by instrument; PCF valuation is lagged one trading day; Fed and bear gates are shifted so day t state controls day t+1 risk_degree.",
        "",
        f"Low risk_degree: `{LOW_RISK_DEGREE:.3f}`; normal risk_degree: `{BASE_RISK_DEGREE:.3f}`.",
        "",
        "## Aggregate vs relay_tie",
        "",
        "| Variant | Window | Cases | Avg Total Diff | Win | Avg Excess Sum Diff | Avg Ann Excess Diff | Avg MDD Diff | Better MDD | Avg Risk Deg | Avg Risk Days | Avg Gate Days | Top40 Changed |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for _, r in agg.iterrows():
        lines.append(
            f"| `{r['variant']}` | {r['window']} | {int(r['cases'])} | {pct(r['avg_total_diff'])} | "
            f"{int(r['win_total'])}/{int(r['cases'])} | {pct(r['avg_excess_sum_diff'])} | "
            f"{pct(r['avg_ann_excess_diff'])} | {pct(r['avg_mdd_diff'])} | "
            f"{int(r['better_mdd'])}/{int(r['cases'])} | {pct(r['avg_risk_degree'])} | "
            f"{num(r['avg_risk_days'])} | {num(r['avg_risk_gate_days'])} | {pct(r['avg_top40_changed'])} |"
        )

    lines += [
        "",
        "## Case Comparison vs relay_tie",
        "",
        "| Case | Variant | Base Total | Variant Total | Bench | Total Diff | Excess Sum Diff | MDD Diff | Risk Deg | Risk Days | Gate Days | Top40 Changed |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for _, r in comp.iterrows():
        lines.append(
            f"| {r['case']} | `{r['variant']}` | {pct(r['baseline_total'])} | {pct(r['variant_total'])} | "
            f"{pct(r['bench_total'])} | {pct(r['total_diff'])} | {pct(r['excess_sum_diff'])} | "
            f"{pct(r['mdd_diff'])} | {pct(r['avg_risk_degree'])} | {int(r['risk_days'])} | "
            f"{int(r['risk_gate_days'])} | "
            f"{pct(r['top40_changed_frac'])} |"
        )

    lines += [
        "",
        "## Run Meta",
        "",
        "```json",
        json.dumps(meta, ensure_ascii=False, indent=2),
        "```",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", nargs="*", default=DEFAULT_CASES)
    parser.add_argument(
        "--variants",
        nargs="*",
        default=[
            "relay_tie",
            "relay_tie_pcf",
            "relay_tie_pcf_layered",
            "relay_tie_pcf_layered_smallmid",
            "relay_tie_pcf_fed50",
            "relay_tie_pcf_fed60",
            "relay_tie_pcf_fed70",
            "relay_tie_pcf_fed80",
            "relay_tie_pcf_fed90",
            "relay_tie_pcf_fed100",
            "relay_tie_pcf_bad_state_cap",
            "relay_tie_pcf_bad_state_relay",
        ],
    )
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--out-dir", default=str(OUT_DIR))
    parser.add_argument("--pred-source", choices=["original", "purged"], default="purged")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    pred_paths = pred_by_source(args.pred_source)
    meta = {
        "created_by": Path(__file__).name,
        "pred_source": args.pred_source,
        "provider_uri": str(QLIB_PROVIDER),
        "valuation_path": file_fingerprint(VAL_PATH),
        "pcf_variant": PCF_VARIANT,
        "risk_degree_normal": BASE_RISK_DEGREE,
        "risk_degree_low": LOW_RISK_DEGREE,
        "fed_risk_multipliers": FED_RISK_MULTIPLIERS,
        "cases": args.cases,
        "variants": args.variants,
        "pred_files": {k: file_fingerprint(v) for k, v in pred_paths.items() if k in set(args.cases) | {previous_period(c) for c in args.cases}},
    }
    (out_dir / "run_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    tasks = [(case, variant, str(out_dir), args.pred_source) for case in args.cases for variant in args.variants]
    rows = []
    daily_parts = []
    with ProcessPoolExecutor(max_workers=args.jobs, initializer=init_worker) as pool:
        futs = [pool.submit(run_case_variant, task) for task in tasks]
        for fut in as_completed(futs):
            row, daily = fut.result()
            rows.append(row)
            daily_parts.append(daily)
            pd.DataFrame(rows).sort_values(["case", "variant"]).to_csv(out_dir / "periods_partial.csv", index=False, encoding="utf-8-sig")
            print(
                f"{row['case']} {row['variant']}: total={row['total_return']:.2%} "
                f"excess_sum={row['excess_sum']:.2%} mdd={row['mdd']:.2%} risk_days={row['risk_days']}",
                flush=True,
            )

    periods = pd.DataFrame(rows).sort_values(["case", "variant"])
    daily_all = pd.concat(daily_parts, ignore_index=True).sort_values(["case", "variant", "datetime"])

    periods.to_csv(out_dir / "periods.csv", index=False, encoding="utf-8-sig")
    daily_all.to_csv(out_dir / "daily_eval.csv", index=False, encoding="utf-8-sig")
    if "relay_tie" in set(periods["variant"]):
        comp = compare_to_baseline(periods)
        agg = aggregate(comp)
        comp.to_csv(out_dir / "comparison_vs_relay_tie.csv", index=False, encoding="utf-8-sig")
        agg.to_csv(out_dir / "aggregate_vs_relay_tie.csv", index=False, encoding="utf-8-sig")
        report = make_report(periods, comp, agg, meta)
        (out_dir / "formal_full_hl378_mw2e4_relay_pcf_risk_qlib_report.md").write_text(report, encoding="utf-8")
        print(out_dir / "formal_full_hl378_mw2e4_relay_pcf_risk_qlib_report.md")
        print(agg[agg["window"].eq("all")].to_string(index=False))
    else:
        print(f"Wrote candidate-only qlib results to {out_dir}")
        print(periods[["case", "variant", "total_return", "mdd", "avg_risk_degree", "risk_days"]].to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
