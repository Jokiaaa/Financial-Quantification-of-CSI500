"""Non-destructive PCF downloader for the existing relay backtest."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import shutil
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import requests

DEFAULT_SCRIPT = Path(r"C:\Users\30855\Desktop\frozen_hl378_mw2e4_T40_D2_20260528(2)\code\formal\formal_full_hl378_mw2e4_relay_pcf_risk_qlib_backtest.py")
KEY = ["instrument", "datetime"]


def digest(path: Path) -> str | None:
    if not path.exists():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def json_write(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def context(script: Path) -> dict:
    """Load only selected constants and pure functions; never import/run backtest."""
    tree = ast.parse(script.read_text(encoding="utf-8-sig"))
    names = {"ROOT", "PROJECT", "VAL_PATH", "PURGED_FREEZE_DIR", "PURGED_YAML_DIR",
             "PURGED_RUN_KEY_PATH", "ORIGINAL_PRED_BY_PERIOD", "ORDERED_PERIODS",
             "DEFAULT_CASES", "MODEL_GATE_ENABLED", "MODEL_GATE_MANIFEST_PATH"}
    functions = {"load_purged_pred_by_period", "load_model_gate_manifest", "load_pred",
                 "combine_preds", "stabilize_signal", "infer_dates", "attach_valuation",
                 "pct_by_day", "apply_pcf_filter", "apply_pcf_q90"}
    nodes = [ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0)]
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if any(isinstance(t, ast.Name) and t.id in names for t in targets):
                nodes.append(node)
        elif isinstance(node, ast.FunctionDef) and node.name in functions:
            nodes.append(node)
    ns = {"Path": Path, "pd": pd, "np": np, "Any": Any}
    exec(compile(ast.fix_missing_locations(ast.Module(body=nodes, type_ignores=[])), str(script), "exec"), ns)
    return ns


def clean(df: pd.DataFrame, *, allow_empty: bool = False) -> pd.DataFrame:
    if df.empty and allow_empty:
        return pd.DataFrame(columns=KEY + ["pcf"])
    missing = set(KEY + ["pcf"]) - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")
    out = df.copy()
    out["instrument"] = out["instrument"].astype(str).str.strip().str.upper()
    out["datetime"] = pd.to_datetime(out["datetime"], errors="coerce")
    if out["datetime"].isna().any():
        raise ValueError("Invalid/empty datetime")
    if not out["instrument"].str.fullmatch(r"(?:SH|SZ|BJ)\d{6}").all():
        raise ValueError("Invalid instrument; expected SH/SZ/BJ + six digits")
    numeric = pd.to_numeric(out["pcf"], errors="coerce")
    if (out["pcf"].notna() & (numeric.isna() | ~np.isfinite(numeric))).any():
        raise ValueError("Invalid/non-finite PCF")
    out["pcf"] = numeric
    if out.duplicated(KEY).any():
        raise ValueError("Duplicate instrument/datetime keys")
    return out.sort_values(KEY).reset_index(drop=True)


def merge_panel(old: pd.DataFrame, fetched: pd.DataFrame) -> pd.DataFrame:
    old = clean(old, allow_empty=True).set_index(KEY)
    new = clean(fetched, allow_empty=True).set_index(KEY)
    merged = old.reindex(old.index.union(new.index)).copy()
    # Change only valid PCF cells. Preserve every original row and other column.
    valid = new["pcf"].dropna()
    merged.loc[valid.index, "pcf"] = valid
    return clean(merged.reset_index())


def fetch_one(inst: str, *, retry: int, timeout: float, period: str) -> tuple[pd.DataFrame, dict]:
    params = {"openapi": "1", "dspName": "iphone", "tn": "tangram", "client": "app",
              "query": "市现率", "code": inst[-6:], "word": "", "resource_id": "51171",
              "market": "ab", "tag": "市现率", "chart_select": period,
              "industry_select": "", "skip_industry": "1", "finClientType": "pc"}
    error = ""
    for attempt in range(1, retry + 1):
        try:
            response = requests.get("https://gushitong.baidu.com/opendata", params=params,
                                    timeout=(min(timeout, 10), timeout))
            response.raise_for_status()
            body = response.json()["Result"][0]["DisplayData"]["resultData"]["tplData"]["result"]["chartInfo"][0]["body"]
            frame = pd.DataFrame(body)
            if frame.empty or len(frame.columns) != 2:
                raise ValueError("Empty/unexpected Baidu response")
            frame.columns = ["datetime", "pcf"]
            frame["instrument"] = inst
            frame = clean(frame)
            if not frame["pcf"].notna().any():
                raise ValueError("Response contains no valid PCF")
            return frame, {"instrument": inst, "status": "ok", "attempts": attempt,
                           "rows": len(frame), "latest_valid_date": str(frame.loc[frame.pcf.notna(), "datetime"].max().date()),
                           "earliest_valid_date": str(frame.loc[frame.pcf.notna(), "datetime"].min().date()), "error": ""}
        except (requests.RequestException, ValueError, KeyError, IndexError, TypeError) as exc:
            error = f"{type(exc).__name__}: {exc}"
            if attempt < retry:
                time.sleep(min(attempt * 1.0, 5))
    return pd.DataFrame(columns=KEY + ["pcf"]), {"instrument": inst, "status": "failed", "attempts": retry, "rows": 0, "error": error}


def signals(ns: dict, source: str, cases: list[str], out: Path):
    paths = ns["load_purged_pred_by_period"](ns["PURGED_RUN_KEY_PATH"]) if source == "purged" else ns["ORIGINAL_PRED_BY_PERIOD"]
    gates = ns["load_model_gate_manifest"]()
    records, targets, requirements = [], set(), []
    for case in cases:
        index = ns["ORDERED_PERIODS"].index(case)
        if index == 0:
            raise ValueError(f"{case} has no previous period")
        prev_case = ns["ORDERED_PERIODS"][index - 1]
        curr_path = Path(gates.get(case, {}).get("selected_pred", paths[case]))
        prev_path = paths[prev_case]
        print(f"Reading {case}: {curr_path}", flush=True)
        prev, curr = ns["load_pred"](prev_path), ns["load_pred"](curr_path)
        bounds = ns["infer_dates"](prev, curr)
        relay = ns["stabilize_signal"](ns["combine_preds"](prev, curr, bounds["switch_date"]))
        targets.update(relay.index.get_level_values("instrument"))
        ranks = relay["score"].groupby(level="datetime").rank(method="first", ascending=False)
        required = relay.loc[ranks.le(100)].reset_index()[["datetime", "instrument"]]
        all_dates = pd.DatetimeIndex(sorted(relay.index.get_level_values("datetime").unique()))
        prior = pd.Series(all_dates, index=all_dates).shift(1)
        required["required_date"] = required["datetime"].map(prior)
        required["case"] = case
        required = required.loc[required["datetime"].ge(pd.Timestamp(bounds["eval_start"]))]
        requirements.append(required)
        records.append({"case": case, "previous_pred": str(prev_path), "previous_sha256": digest(prev_path),
                        "current_pred": str(curr_path), "current_sha256": digest(curr_path), **bounds})
        yield case, relay, bounds["eval_start"]
    pd.DataFrame({"instrument": sorted(targets)}).to_csv(out / "instruments.csv", index=False)
    pd.concat(requirements, ignore_index=True).to_csv(out / "requirements_top100.csv", index=False)
    json_write(out / "prediction_sources.json", records)


def audit_signal(ns: dict, signal: pd.DataFrame, panel: pd.DataFrame, case: str, eval_start: str) -> pd.DataFrame:
    # These are the backtest's exact alignment and lag functions.
    val = panel.copy()
    for col in ["market_cap", "pe_ttm", "pb"]:
        if col not in val:
            val[col] = np.nan
    enriched = ns["attach_valuation"](signal, val, lag_trading_days=1)
    ranks = signal["score"].groupby(level="datetime").rank(method="first", ascending=False)
    pcf = enriched["pcf"] if "pcf" in enriched else pd.Series(np.nan, index=signal.index)
    top = ranks.le(100) & (signal.index.get_level_values("datetime") >= pd.Timestamp(eval_start))
    filtered = ns["apply_pcf_q90"](enriched) if "pcf" in enriched else signal.copy()
    return pd.DataFrame({"case": case, "covered": pcf.loc[top].notna(), "positive": pcf.loc[top].gt(0),
                         "filtered": filtered.loc[top, "score"].eq(-1e9)}).reset_index()


def publish(candidate: Path, target: Path, expected_hash: str | None, expected_candidate_hash: str) -> str | None:
    if digest(candidate) != expected_candidate_hash:
        raise ValueError("Candidate changed after verification; refusing publish")
    if digest(target) != expected_hash:
        raise ValueError("Original CSV changed since snapshot; run update again")
    target.parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    backup = target.with_name(f"{target.stem}.backup_{stamp}{target.suffix}") if target.exists() else None
    if backup:
        shutil.copy2(target, backup)
        if digest(backup) != expected_hash:
            raise ValueError("Backup mismatch; refusing publish")
    temp = target.with_name(f".{target.name}.{stamp}.tmp")
    try:
        shutil.copy2(candidate, temp)
        if digest(temp) != expected_candidate_hash or digest(target) != expected_hash:
            raise ValueError("File changed during publish")
        os.replace(temp, target)
    finally:
        temp.unlink(missing_ok=True)
    return str(backup) if backup else None


def run(args) -> int:
    ns = context(args.backtest)
    target = args.target or ns["VAL_PATH"]
    if target.suffix.lower() != ".csv":
        raise ValueError("Target must be CSV")
    if args.publish_run:
        report_path = args.publish_run / "report.json"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        if not report.get("accepted"):
            raise ValueError("Run did not pass acceptance checks; cannot publish")
        if digest(Path(report["backtest"])) != report["backtest_sha256"]:
            raise ValueError("Backtest script changed since validation; run again")
        sources = json.loads((args.publish_run / "prediction_sources.json").read_text(encoding="utf-8"))
        for source in sources:
            for prefix in ("previous", "current"):
                if digest(Path(source[f"{prefix}_pred"])) != source[f"{prefix}_sha256"]:
                    raise ValueError(f"Prediction changed since validation: {source[f'{prefix}_pred']}")
        target = Path(report["target"])
        backup = publish(args.publish_run / "candidate.csv", target, report["original_sha256"], report["candidate_sha256"])
        json_write(args.publish_run / "published.json", {"target": target, "backup": backup, "time": datetime.now().isoformat()})
        print(f"Published: {target}\nBackup: {backup}")
        return 0
    args.output.mkdir(parents=True, exist_ok=True)
    out = args.output / datetime.now().strftime("run_%Y%m%d_%H%M%S_%f")
    out.mkdir()
    print(f"Run folder: {out}", flush=True)
    backtest_hash = digest(args.backtest)
    original_hash = digest(target)
    if target.exists():
        shutil.copy2(target, out / "original.csv")
        if digest(out / "original.csv") != original_hash:
            raise ValueError("Original changed while taking snapshot")
        old = clean(pd.read_csv(out / "original.csv", float_precision="round_trip"))
    else:
        old = clean(pd.DataFrame(), allow_empty=True)
    cases = args.cases or ns["DEFAULT_CASES"]
    # Stream cases and keep only compact coverage rows instead of all predictions.
    before_parts = []
    for case, relay, eval_start in signals(ns, args.pred_source, cases, out):
        before_parts.append(audit_signal(ns, relay, old, case, eval_start))
    initial_sources = json.loads((out / "prediction_sources.json").read_text(encoding="utf-8"))
    before = pd.concat(before_parts, ignore_index=True)
    before.to_csv(out / "coverage_before.csv", index=False)
    instruments = pd.read_csv(out / "instruments.csv")["instrument"].tolist()
    if args.symbols:
        requested = {v.strip().upper() for v in args.symbols.split(",") if v.strip()}
        instruments = sorted(requested)
    if args.limit:
        instruments = instruments[:args.limit]
    limited = bool(args.symbols or args.limit)
    if args.plan:
        json_write(out / "plan.json", {"target": target, "original_sha256": original_hash,
                   "stocks_to_fetch": len(instruments), "cases": cases, "period": args.period,
                   "limited": limited, "mode": "plan_only"})
        print(f"Plan ready: {len(instruments)} stocks; no downloads or target writes. {out}")
        return 0
    frames, logs = [], []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(fetch_one, inst, retry=args.retry, timeout=args.timeout, period=args.period): inst for inst in instruments}
        for count, future in enumerate(as_completed(futures), 1):
            frame, log = future.result()
            logs.append(log)
            if not frame.empty:
                frames.append(frame)
            print(f"[{count}/{len(instruments)}] {log['instrument']} {log['status']} rows={log['rows']}", flush=True)
    download_log = pd.DataFrame(logs)
    download_log.to_csv(out / "download_log.csv", index=False, encoding="utf-8-sig")
    fetched = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=KEY + ["pcf"])
    fetched.to_csv(out / "downloaded.csv", index=False, encoding="utf-8-sig")
    candidate = merge_panel(old, fetched)
    candidate_path = out / "candidate.csv"
    candidate.to_csv(candidate_path, index=False, encoding="utf-8-sig", date_format="%Y-%m-%d")
    # Audit the serialized artifact, not only the in-memory frame.
    candidate = clean(pd.read_csv(candidate_path, float_precision="round_trip"))
    after_parts = []
    for case, relay, eval_start in signals(ns, args.pred_source, cases, out):
        after_parts.append(audit_signal(ns, relay, candidate, case, eval_start))
    final_sources = json.loads((out / "prediction_sources.json").read_text(encoding="utf-8"))
    after = pd.concat(after_parts, ignore_index=True)
    detail = before.merge(after, on=["case", "datetime", "instrument"], suffixes=("_before", "_after"), validate="one_to_one")
    detail["coverage_regressed"] = detail.covered_before & ~detail.covered_after
    detail["filter_changed"] = detail.filtered_before != detail.filtered_after
    detail.to_csv(out / "coverage_comparison.csv", index=False)
    daily = detail.groupby(["case", "datetime"]).agg(top100_count=("instrument", "size"),
        covered_before=("covered_before", "sum"), covered_after=("covered_after", "sum"),
        positive_after=("positive_after", "sum"), filtered_after=("filtered_after", "sum"),
        filter_changed=("filter_changed", "sum")).reset_index()
    daily.to_csv(out / "coverage_daily.csv", index=False)
    detail.loc[~detail.covered_after].to_csv(out / "missing_top100.csv", index=False)
    latest = candidate.loc[candidate.pcf.notna()].groupby("instrument").datetime.agg(["min", "max", "count"])
    latest.to_csv(out / "stock_date_ranges.csv")
    # Freshness relative to each stock's own latest required prior signal date.
    req = pd.read_csv(out / "requirements_top100.csv", parse_dates=["required_date"])
    freshness = req.groupby("instrument").required_date.max().to_frame().join(latest[["max"]])
    freshness["stale"] = freshness["required_date"].notna() & (freshness["max"].isna() | freshness["max"].lt(freshness.required_date))
    freshness.to_csv(out / "freshness.csv")
    oi, ci = old.set_index(KEY), candidate.set_index(KEY)
    changes = oi[["pcf"]].rename(columns={"pcf": "pcf_before"}).join(
        ci[["pcf"]].rename(columns={"pcf": "pcf_after"}), how="outer")
    same = changes.pcf_before.eq(changes.pcf_after) | (changes.pcf_before.isna() & changes.pcf_after.isna())
    changes.loc[~same].to_csv(out / "pcf_changes.csv")
    preserved = oi.index.isin(ci.index).all()
    valid_old = oi.pcf.dropna()
    valid_preserved = ci.reindex(valid_old.index).pcf.notna().all()
    other_cols = [c for c in oi if c != "pcf"]
    try:
        pd.testing.assert_frame_equal(oi[other_cols], ci.reindex(oi.index)[other_cols], check_dtype=False, check_exact=True)
        other_preserved = True
    except AssertionError:
        other_preserved = False
    failed = int(download_log.status.ne("ok").sum()) if len(logs) else len(instruments)
    checks = {"unlimited_run": not limited, "download_has_valid_rows": not fetched.empty,
              "all_downloads_successful": failed == 0 and bool(instruments),
              "all_original_keys_preserved": bool(preserved), "old_valid_pcf_not_erased": bool(valid_preserved),
              "other_columns_preserved": bool(other_preserved),
              "coverage_not_regressed": not bool(detail.coverage_regressed.any()),
              "required_top100_has_pcf": bool(detail.covered_after.all()),
              "required_top100_fresh": not bool(freshness.stale.any()),
              "source_unchanged": digest(target) == original_hash,
              "prediction_sources_unchanged": initial_sources == final_sources,
              "backtest_unchanged": digest(args.backtest) == backtest_hash}
    report = {"accepted": all(checks.values()), "checks": checks, "target": str(target),
              "backtest": str(args.backtest), "backtest_sha256": backtest_hash, "pred_source": args.pred_source, "cases": cases,
              "original_sha256": original_hash, "candidate_sha256": digest(candidate_path),
              "original_rows": len(old), "candidate_rows": len(candidate), "requested_stocks": len(instruments),
              "failed_downloads": failed, "coverage_before": float(detail.covered_before.mean()),
              "coverage_after": float(detail.covered_after.mean()), "missing_top100": int((~detail.covered_after).sum()),
              "stale_required_stocks": int(freshness.stale.sum()), "filter_changed_rows": int(detail.filter_changed.sum()),
              "changed_pcf_cells": int((~same).sum()),
              "note": "Checks use original backtest functions and eval dates, including relay history for lag alignment. Full Qlib backtest is not executed. Coverage/freshness gaps block publishing."}
    json_write(out / "report.json", report)
    lines = ["# PCF 更新验证报告", "", f"验收结果：{'通过，可执行发布' if report['accepted'] else '未通过，正式文件未替换'}",
             f"原始行数：{len(old)}；候选行数：{len(candidate)}；下载失败：{failed}",
             f"前100名覆盖率：{report['coverage_before']:.6%} → {report['coverage_after']:.6%}",
             f"缺失记录：{report['missing_top100']}；日期滞后股票：{report['stale_required_stocks']}",
             f"PCF 单元格变化：{report['changed_pcf_cells']}；基础 q90 筛选变化：{report['filter_changed_rows']}", "",
             "| 检查项 | 结果 |", "|---|---|"]
    lines.extend(f"| {key} | {'通过' if value else '未通过'} |" for key, value in checks.items())
    if limited:
        lines.extend(["", "本次为限定股票的联网测试，unlimited_run 未通过是预期结果，不能用该运行替换正式文件。"])
    lines.extend(["", "详细缺口见 missing_top100.csv / freshness.csv；下载错误见 download_log.csv。",
                  "仅验证原回测的基础 q90 筛选及数据对齐，不代替所有策略变体的完整 Qlib 回测。"])
    (out / "验证报告.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)
    print(f"Artifacts: {out}")
    return 0 if report["accepted"] else 2


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backtest", type=Path, default=DEFAULT_SCRIPT)
    parser.add_argument("--target", type=Path, help="Defaults to backtest VAL_PATH")
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parent / "runs")
    parser.add_argument("--pred-source", choices=["purged", "original"], default="purged")
    parser.add_argument("--cases", nargs="+")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--retry", type=int, default=3)
    parser.add_argument("--timeout", type=float, default=25)
    parser.add_argument("--period", choices=["全部", "近十年", "近五年", "近三年", "近一年"], default="全部")
    parser.add_argument("--symbols", help="Comma-separated instruments for smoke test; never publishable")
    parser.add_argument("--limit", type=int, default=0, help="Limit download count; never publishable")
    parser.add_argument("--plan", action="store_true", help="Inspect predictions and existing coverage only")
    parser.add_argument("--publish-run", type=Path, help="Publish a previously accepted run with backup")
    args = parser.parse_args()
    if args.workers < 1 or args.retry < 1 or args.timeout <= 0 or args.limit < 0:
        parser.error("workers/retry/timeout must be positive; limit must be >= 0")
    try:
        return run(args)
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
