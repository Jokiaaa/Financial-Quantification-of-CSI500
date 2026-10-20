from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import importlib.metadata
import json
import math
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def fingerprint(path: Path) -> dict:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return {"name": path.name, "bytes": path.stat().st_size, "sha256": digest.hexdigest()}


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def environment() -> dict:
    packages = ("pyqlib", "lightgbm", "numpy", "pandas", "PyYAML", "pyarrow", "scipy", "scikit-learn")
    return {"python": platform.python_version(), "platform": platform.system(), "packages": {name: importlib.metadata.version(name) for name in packages}}


def reference_functions() -> dict:
    import numpy as np
    import pandas as pd

    path = ROOT / "code" / "formal_full_hl378_mw2e4_relay_pcf_risk_qlib_backtest.py"
    names = {"load_pred", "combine_preds", "stabilize_signal", "attach_valuation", "pct_by_day", "apply_pcf_filter", "apply_pcf_q90"}
    source = ast.parse(path.read_text(encoding="utf-8-sig"))
    nodes = [node for node in source.body if isinstance(node, ast.FunctionDef) and node.name in names]
    if {node.name for node in nodes} != names:
        raise ValueError("Historical signal function definitions have changed")
    namespace = {"pd": pd, "np": np, "Path": Path}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), "exec"), namespace)
    return namespace


def read_prediction(path: Path, functions: dict) -> Any:
    import numpy as np
    import pandas as pd

    if path.suffix.lower() == ".csv":
        frame = pd.read_csv(path, parse_dates=["datetime"])
        prediction = frame.set_index(["datetime", "instrument"])[["score"]].sort_index()
    else:
        prediction = functions["load_pred"](path)
    if prediction.index.duplicated().any() or not np.isfinite(prediction["score"]).all():
        raise ValueError("Duplicate prediction keys or non-finite scores")
    return prediction


def resolve_path(manifest_path: Path, value: str) -> Path:
    path = Path(value).expanduser()
    return path.resolve() if path.is_absolute() else (manifest_path.parent / path).resolve()


def plan_dates(calendar: list[str], start: str, end: str, validation_end: str, wait: int = 20) -> dict:
    if wait < 20:
        raise ValueError("The 20-day label requires at least 20 trading sessions of waiting")
    sessions = [date for date in calendar if start <= date <= end]
    if len(sessions) <= wait:
        raise ValueError("Evaluation range has no post-waiting trading day")
    if sessions[-1] >= calendar[-1]:
        raise ValueError("Qlib execution requires a calendar session after evaluation_end")
    label_sessions = [date for date in calendar if date > validation_end]
    if len(label_sessions) < 20:
        raise ValueError("Calendar cannot establish validation label maturity")
    maturity = label_sessions[19]
    signal_date, first_trade = sessions[wait - 1], sessions[wait]
    if maturity > signal_date:
        raise ValueError("Validation labels are not mature before the first execution signal")
    return {
        "validation_last_feature_date": validation_end,
        "validation_label_maturity_close": maturity,
        "reconstruction_end": signal_date,
        "first_execution_signal_date": signal_date,
        "first_actual_trade_date": first_trade,
        "evaluation_end": sessions[-1],
        "waiting_sessions": wait,
    }


def init_qlib(provider: Path) -> None:
    import qlib

    qlib.init(provider_uri=str(provider), region="cn", kernels=1, expression_cache=None, dataset_cache=None, joblib_backend="sequential")


def execution_exchange(config: dict) -> dict:
    exchange = copy.deepcopy(config["exchange"])
    threshold = exchange["limit_threshold"]
    if not isinstance(threshold, (int, float)) or not 0 < threshold < 1:
        raise ValueError("Provide a numeric limit threshold strictly between zero and one")
    exchange["limit_threshold"] = (
        f"$open >= Ref($close, 1) * {1 + threshold:g}",
        f"$open <= Ref($close, 1) * {1 - threshold:g}",
    )
    return exchange


def calculate_metrics(report: Any) -> dict:
    import numpy as np

    net = report["return"].astype(float) - report["cost"].astype(float)
    benchmark = report["bench"].astype(float)
    if not np.isfinite(net).all() or not np.isfinite(benchmark).all():
        raise ValueError("Non-finite daily returns")
    nav = (1 + net).cumprod()
    benchmark_nav = (1 + benchmark).cumprod()
    peak = nav.cummax().clip(lower=1.0)
    excess = net - benchmark
    deviation = float(net.std(ddof=1))
    excess_deviation = float(excess.std(ddof=1))
    return {
        "days": len(report),
        "total_return": float(nav.iloc[-1] - 1),
        "benchmark_return": float(benchmark_nav.iloc[-1] - 1),
        "compound_return_difference": float(nav.iloc[-1] - benchmark_nav.iloc[-1]),
        "daily_excess_sum": float(excess.sum()),
        "annualized_return": float(nav.iloc[-1] ** (252 / len(nav)) - 1),
        "max_drawdown_including_initial_cash": float((nav / peak - 1).min()),
        "sharpe_zero_cash_rate": float(net.mean() / deviation * math.sqrt(252)) if deviation > 0 else None,
        "information_ratio": float(excess.mean() / excess_deviation * math.sqrt(252)) if excess_deviation > 0 else None,
        "sum_daily_cost_rate": float(report["cost"].sum()),
        "mean_daily_turnover": float(report["turnover"].mean()),
    }


def simulate(signal: Any, config: dict, start: str, end: str, cost_multiple: float = 1.0, initial_targets: list[str] | None = None) -> tuple:
    import pandas as pd
    from qlib.backtest import backtest, executor
    from qlib.backtest.decision import TradeDecisionWO
    from qlib.contrib.strategy import TopkDropoutStrategy

    class AuditedStrategy(TopkDropoutStrategy):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.orders = []
            self.executions = []
            self.started = False

        def generate_trade_decision(self, execute_result=None):
            decision = super().generate_trade_decision(execute_result)
            step = self.trade_calendar.get_trade_step()
            signal_start, _ = self.trade_calendar.get_step_time(step, shift=1)
            if initial_targets is not None and not self.started:
                permitted = set(initial_targets)
                decision = TradeDecisionWO([order for order in decision.get_decision() if order.stock_id in permitted], self)
            self.started = True
            for order in decision.get_decision():
                if signal_start >= order.start_time:
                    raise ValueError("Order signal is not from an earlier session")
                self.orders.append({"date": str(order.start_time.date()), "signal_date": str(signal_start.date()), "instrument": order.stock_id, "direction": int(order.direction), "requested_amount": float(order.amount)})
            return decision

        def post_exe_step(self, execute_result):
            for order, value, cost, price in execute_result or []:
                self.executions.append({
                    "date": str(order.start_time.date()), "instrument": order.stock_id,
                    "direction": int(order.direction), "requested_amount": float(order.amount),
                    "filled_amount": float(order.deal_amount), "trade_value": float(value),
                    "trade_cost": float(cost), "trade_price": float(price),
                })

    strategy_kwargs = config["strategy"]
    exchange = execution_exchange(config)
    for field in ("open_cost", "close_cost", "min_cost"):
        exchange[field] *= cost_multiple
    strategy = AuditedStrategy(signal=signal["score"], **strategy_kwargs)
    reports, _ = backtest(
        start_time=start, end_time=end,
        strategy=strategy,
        executor=executor.SimulatorExecutor(time_per_step="day", generate_portfolio_metrics=True),
        account=float(config["initial_cash"]), benchmark=config["benchmark"],
        exchange_kwargs={"freq": "day", "codes": sorted(set(signal.index.get_level_values("instrument"))), **exchange},
    )
    report, positions = reports["1day"]
    report.index = pd.to_datetime(report.index)
    return report, positions, strategy.orders, strategy.executions


def position_rows(positions: dict) -> list[dict]:
    rows = []
    for date, position in sorted(positions.items()):
        for stock in sorted(position.get_stock_list()):
            rows.append({"date": str(date.date()), "instrument": stock, "amount": float(position.get_stock_amount(stock)), "price": float(position.get_stock_price(stock))})
    return rows


def run_backtest(manifest_path: Path, output: Path, validate_only: bool = False) -> int:
    import pandas as pd

    manifest_path = manifest_path.resolve()
    config = json.loads(manifest_path.read_text(encoding="utf-8"))
    requested_variants = config.get("portfolio_variants", ["relay", "relay_pcf"])
    if not requested_variants or set(requested_variants) - {"relay", "relay_pcf"}:
        raise ValueError("portfolio_variants must select relay and/or relay_pcf")
    pcf_required = "relay_pcf" in requested_variants
    provider = resolve_path(manifest_path, config["provider_uri"])
    calendar_path = provider / "calendars" / "day.txt"
    calendar = calendar_path.read_text(encoding="utf-8-sig").splitlines()
    dates = plan_dates(calendar, config["period_start"], config["period_end"], config["validation_end"], config.get("wait_sessions", 20))
    if config["exchange"]["deal_price"] != "open":
        raise ValueError("This protocol requires next-session open execution")
    if output.exists() and any(output.iterdir()):
        raise ValueError("Output must be an empty directory; previous evidence is never overwritten")
    functions = reference_functions()
    current_path = resolve_path(manifest_path, config["current_prediction"])
    previous_path = resolve_path(manifest_path, config["previous_prediction"])
    current = read_prediction(current_path, functions)
    previous = read_prediction(previous_path, functions)
    signal = functions["stabilize_signal"](functions["combine_preds"](previous, current, config["period_start"]))
    needed = [date for date in calendar if config["period_start"] <= date <= config["period_end"]]
    signal_dates = set(signal.index.get_level_values("datetime").strftime("%Y-%m-%d"))
    if set(needed) - signal_dates:
        raise ValueError("Prediction files do not cover the evaluation calendar")
    valuation_path = resolve_path(manifest_path, config["valuation"])
    valuation = pd.read_parquet(valuation_path) if valuation_path.suffix in {".parquet", ".pq"} else pd.read_csv(valuation_path)
    for column in ("market_cap", "pe_ttm", "pb"):
        if column not in valuation:
            valuation[column] = float("nan")
    valuation["datetime"] = pd.to_datetime(valuation["datetime"], errors="raise")
    if valuation.duplicated(["datetime", "instrument"]).any():
        raise ValueError("Duplicate valuation keys")
    enriched = functions["attach_valuation"](signal, valuation, lag_trading_days=1)
    ranks = signal["score"].groupby(level="datetime").rank(method="first", ascending=False)
    signal_days = signal.index.get_level_values("datetime")
    evaluation = (signal_days >= pd.Timestamp(dates["first_execution_signal_date"])) & (signal_days <= pd.Timestamp(config["period_end"]))
    required = (ranks <= 100) & evaluation
    missing = int(enriched.loc[required, "pcf"].isna().sum())
    if missing and pcf_required and not config.get("allow_missing_pcf", False):
        raise ValueError(f"Missing PCF in {missing} required top-100 observations; repair input or explicitly document allow_missing_pcf")
    filtered = functions["stabilize_signal"](functions["apply_pcf_q90"](enriched))
    meta = {
        "kind": config.get("kind", "retrospective_day21_cash_construction_replay"),
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "historical_training_timestamps_verified": False,
        "model_release_assumption": "Stored model could be trained after validation labels mature and before the first eligible open; historical completion timestamps are not certified.",
        "account_protocol": "Reconstructed holdings select the initial target; actual account starts in cash, buys at its first eligible open, pays fees, and carries no reconstructed quantities or entry prices.",
        "dates": dates, "environment": environment(),
        "effective_exchange": execution_exchange(config),
        "tradability_rule": "Open execution limits compare current open to previous close, not current closing return. The historical fixed 9.5% approximation is retained; this is not an exchange-specific board-rule reconstruction.",
        "configuration": {key: value for key, value in config.items() if key not in {"provider_uri", "valuation", "previous_prediction", "current_prediction"}},
        "inputs": {"current_prediction": fingerprint(current_path), "previous_prediction": fingerprint(previous_path), "valuation": fingerprint(valuation_path), "calendar": fingerprint(calendar_path), "manifest": fingerprint(manifest_path), "runner": fingerprint(Path(__file__)), "signal_source": fingerprint(ROOT / "code" / "formal_full_hl378_mw2e4_relay_pcf_risk_qlib_backtest.py")},
        "missing_top100_pcf_observations": missing,
        "pcf_used_by_requested_variants": pcf_required,
        "required_top100_observations": int(required.sum()),
    }
    meta["provider_files"] = {}
    stocks = sorted(set(signal.index.get_level_values("instrument")) | {config["benchmark"]})
    for stock in stocks:
        for field in ("open", "close", "factor", "change", "volume"):
            relative = f"features/{stock.lower()}/{field}.day.bin"
            path = provider / relative
            if path.exists():
                meta["provider_files"][relative] = fingerprint(path)["sha256"]
    meta["missing_pcf_keys"] = [{"datetime": str(date.date()), "instrument": stock} for date, stock in enriched.loc[required & enriched["pcf"].isna()].index]
    output.mkdir(parents=True, exist_ok=True)
    write_json(output / "run_manifest.json", meta)
    if validate_only:
        print(json.dumps({"input_check": "passed", "dates": dates, "missing_pcf": missing}))
        return 0
    init_qlib(provider)
    all_metrics = []
    for variant, scores in (("relay", signal), ("relay_pcf", filtered)):
        if variant not in requested_variants:
            continue
        print(f"Reconstructing {variant} target through {dates['reconstruction_end']}", flush=True)
        reconstruction_start = str(scores.index.get_level_values("datetime").min().date())
        _, reconstructed, _, _ = simulate(scores, config, reconstruction_start, dates["reconstruction_end"])
        last = reconstructed[max(reconstructed)]
        target = last.get_stock_list()
        if not target:
            raise ValueError("Reconstruction produced no target holdings")
        first_signal = scores.xs(pd.Timestamp(dates["first_execution_signal_date"]), level="datetime")["score"]
        if set(target) - set(first_signal.index):
            raise ValueError("Reconstructed target contains stocks missing from the day-20 signal")
        if len(target) > config["strategy"]["topk"]:
            raise ValueError("Reconstructed holdings exceed the target count")
        ordered = first_signal.reindex(target).sort_values(ascending=False, kind="mergesort").index.tolist()
        actual_signal = scores.copy()
        first_index = actual_signal.index.get_level_values("datetime") == pd.Timestamp(dates["first_execution_signal_date"])
        actual_signal.loc[first_index, "score"] = -1e12
        for index, stock in enumerate(ordered):
            actual_signal.loc[(pd.Timestamp(dates["first_execution_signal_date"]), stock), "score"] = float(len(ordered) - index)
        for multiple in config.get("cost_multiples", [1.0, 2.0]):
            if multiple < 0:
                raise ValueError("Cost multiple must be nonnegative")
            name = f"{variant}_cost{multiple:g}"
            destination = output / name
            destination.mkdir()
            report, positions, orders, trades = simulate(actual_signal, config, dates["first_actual_trade_date"], dates["evaluation_end"], multiple, ordered)
            report.to_csv(destination / "daily.csv", index_label="datetime")
            pd.DataFrame(orders, columns=["date", "signal_date", "instrument", "direction", "requested_amount"]).to_csv(destination / "orders.csv", index=False)
            pd.DataFrame(trades, columns=["date", "instrument", "direction", "requested_amount", "filled_amount", "trade_value", "trade_cost", "trade_price"]).to_csv(destination / "trades.csv", index=False)
            pd.DataFrame(position_rows(positions)).to_csv(destination / "positions.csv", index=False)
            pd.DataFrame({"instrument": ordered}).to_csv(destination / "initial_target.csv", index=False)
            first_trades = [trade for trade in trades if trade["date"] == dates["first_actual_trade_date"] and trade["filled_amount"] > 0]
            audit = {
                "first_trade_date": dates["first_actual_trade_date"], "signal_date": dates["first_execution_signal_date"],
                "initial_cash": config["initial_cash"], "initial_positions": [],
                "reconstructed_target_count": len(target), "first_day_filled_stocks": len(first_trades),
                "first_day_construction_cost": sum(trade["trade_cost"] for trade in first_trades),
                "pre_start_orders": sum(order["date"] < dates["first_actual_trade_date"] for order in orders),
                "cost_multiple": multiple,
            }
            if audit["pre_start_orders"] or (multiple > 0 and audit["first_day_construction_cost"] <= 0):
                raise ValueError("Construction audit failed")
            write_json(destination / "execution_audit.json", audit)
            metrics = {"variant": variant, "cost_multiple": multiple, **calculate_metrics(report)}
            all_metrics.append(metrics)
            print(json.dumps(metrics), flush=True)
    pd.DataFrame(all_metrics).to_csv(output / "metrics.csv", index=False)
    meta["output_hashes"] = {path.relative_to(output).as_posix(): fingerprint(path)["sha256"] for path in sorted(output.rglob("*")) if path.is_file() and path.name != "run_manifest.json"}
    write_json(output / "run_manifest.json", meta)
    return 0


def train_ablation(arguments: argparse.Namespace) -> int:
    import pandas as pd
    import yaml
    from qlib.utils import init_instance_by_config

    output = arguments.output.resolve()
    if output.exists() and any(output.iterdir()):
        raise ValueError("Training output must be empty")
    output.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(ROOT / "code"))
    from lgb_recency_weighted_model import RecencyWeightedLGBModel

    cfg = yaml.safe_load(arguments.config.read_text(encoding="utf-8-sig"))
    calendar = (arguments.provider / "calendars" / "day.txt").read_text(encoding="utf-8-sig").splitlines()
    dataset_cfg = copy.deepcopy(cfg["task"]["dataset"])
    segments = dataset_cfg["kwargs"]["segments"]
    valid_start = segments["valid"][0]
    training_sessions = [date for date in calendar if date < valid_start]
    segments["train"][1] = min(segments["train"][1], training_sessions[-21])
    if arguments.train_start:
        segments["train"][0] = arguments.train_start
    if arguments.valid_start:
        segments["valid"][0] = arguments.valid_start
        training_sessions = [date for date in calendar if date < arguments.valid_start]
        segments["train"][1] = training_sessions[-21]
    if segments["train"][0] > segments["train"][1] or segments["valid"][0] > segments["valid"][1]:
        raise ValueError("Invalid training or validation window")
    init_qlib(arguments.provider)
    model_kwargs = dict(cfg["task"]["model"]["kwargs"])
    weighting = {key: model_kwargs.pop(key) for key in list(model_kwargs) if key.startswith("recency_")}
    model_kwargs.update(seed=1729, feature_fraction_seed=1729, bagging_seed=1729, deterministic=True, force_col_wise=True, num_threads=arguments.threads)
    handler = dataset_cfg["kwargs"]["handler"]
    handler["kwargs"]["start_time"] = min(segments["train"][0], segments["valid"][0])
    training_meta = {"environment": environment(), "segments": segments, "seed": 1729, "config_source": fingerprint(arguments.config), "runner": fingerprint(Path(__file__)), "model_parameters": model_kwargs, "weighting_parameters": weighting, "dataset_configuration": dataset_cfg, "num_boost_round_cap": arguments.rounds, "early_stopping_rounds": arguments.early_stopping, "label_horizon_sessions": 20, "training_validation_boundary_purged": True, "kind": "matched_retrospective_model_ablation", "fitting_engine": "The same RecencyWeightedLGBModel wrapper is used for all variants. Unweighted variants set minimum unnormalized weight to 1, producing exactly uniform training and validation weights.", "predictions": {}}
    write_json(output / "training_manifest.json", training_meta)
    print("Loading the common extended feature panel once for all three variants", flush=True)
    dataset = init_instance_by_config(dataset_cfg)
    from qlib.contrib.data.handler import Alpha158

    _, base_names = Alpha158(init_data=False).get_feature_config()
    base_names = set(base_names)
    for variant in ("alpha158_unweighted", "extended_unweighted", "extended_weighted"):
        selected_dataset = dataset
        if variant == "alpha158_unweighted":
            selected_dataset = copy.copy(dataset)
            selected_dataset.handler = copy.copy(dataset.handler)
            for attribute in ("_data", "_learn", "_infer"):
                frame = getattr(dataset.handler, attribute, None)
                if frame is not None:
                    columns = [column for column in frame.columns if column[0] != "feature" or column[1] in base_names]
                    setattr(selected_dataset.handler, attribute, frame.loc[:, columns])
        print(f"Training {variant}", flush=True)
        variant_weights = weighting if variant == "extended_weighted" else {**weighting, "recency_min_weight": 1.0}
        model = RecencyWeightedLGBModel(**model_kwargs, **variant_weights)
        model.fit(selected_dataset, num_boost_round=arguments.rounds, early_stopping_rounds=arguments.early_stopping, verbose_eval=100)
        prediction = model.predict(selected_dataset)
        destination = output / variant
        destination.mkdir()
        prediction.to_frame("score").to_pickle(destination / "pred.pkl")
        model.model.save_model(str(destination / "model.txt"))
        training_meta["predictions"][variant] = {"prediction": fingerprint(destination / "pred.pkl"), "model": fingerprint(destination / "model.txt"), "feature_count": model.model.num_feature(), "best_iteration": model.model.best_iteration, "training_completed_at_utc": datetime.now(timezone.utc).isoformat()}
        write_json(output / "training_manifest.json", training_meta)
    pd.DataFrame([{ "variant": name, "feature_count": record["feature_count"], "best_iteration": record["best_iteration"]} for name, record in training_meta["predictions"].items()]).to_csv(output / "models.csv", index=False)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Portable CSI 500 research: explicit inputs, day-21 cash construction, audit exports, matched training.")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("check-inputs", "backtest"):
        command = commands.add_parser(name)
        command.add_argument("--manifest", type=Path, required=True)
        command.add_argument("--output", type=Path, required=True)
    train = commands.add_parser("train-ablation")
    train.add_argument("--config", type=Path, required=True)
    train.add_argument("--provider", type=Path, required=True)
    train.add_argument("--output", type=Path, required=True)
    train.add_argument("--train-start")
    train.add_argument("--valid-start")
    train.add_argument("--threads", type=int, default=4)
    train.add_argument("--rounds", type=int, default=1000)
    train.add_argument("--early-stopping", type=int, default=50)
    arguments = parser.parse_args()
    if arguments.command == "train-ablation":
        return train_ablation(arguments)
    return run_backtest(arguments.manifest, arguments.output.resolve(), arguments.command == "check-inputs")


if __name__ == "__main__":
    raise SystemExit(main())
