from __future__ import annotations

"""Safely append daily CSI500 data to a local Qlib binary data set.

The updater uses a prepare/apply transaction:
1. download and cache raw/qfq quotes;
2. build a complete staged copy of every file that will change;
3. validate the staged data and source file hashes;
4. back up the originals and atomically replace them.

Run without arguments (or with ``status``) for a read-only status check.
"""

import argparse
import concurrent.futures as cf
import hashlib
import json
import os
import shutil
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import requests


DEFAULT_QLIB_DIR = Path(r"C:\Users\30855\.qlib\qlib_data\cn_data")
ROOT = Path(__file__).resolve().parent
RUNS_ROOT = ROOT / "daily_update_runs"
INDEX_SYMBOL = "sh000905"
FIELDS = ["open", "high", "low", "close", "volume", "amount", "vwap", "factor", "change", "adjclose"]
PRICE_FIELDS = ["open", "high", "low", "close"]


@dataclass
class SymbolResult:
    symbol: str
    anchor: str = ""
    rows: int = 0
    suspended: str = ""
    status: str = "ok"
    error: str = ""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="CSI500 Qlib 日常安全增量更新")
    parser.add_argument("command", nargs="?", default="status", choices=["status", "prepare", "apply", "update", "verify"])
    parser.add_argument("--qlib-dir", type=Path, default=DEFAULT_QLIB_DIR)
    parser.add_argument("--target-date", help="更新截止日 YYYY-MM-DD；省略时自动选择最近已收盘交易日")
    parser.add_argument("--run-dir", type=Path, help="apply/verify 指定已有批次目录；默认使用 latest_run.txt")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--allow-long-gap", action="store_true", help="允许一次补超过 20 个交易日")
    parser.add_argument("--keep-going", action="store_true", help="下载个别失败时继续，以便下次断点续传")
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_read_lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines()


def read_calendar(qlib_dir: Path) -> list[str]:
    days = safe_read_lines(qlib_dir / "calendars" / "day.txt")
    if not days or days != sorted(set(days)):
        raise RuntimeError("正式交易日历为空、乱序或包含重复日期")
    return days


def read_bin(path: Path, calendar: list[str]) -> tuple[pd.Series, int]:
    data = np.fromfile(path, dtype="<f4")
    if len(data) < 2:
        raise RuntimeError(f"无效的 Qlib 文件: {path}")
    start = int(data[0])
    dates = calendar[start : start + len(data) - 1]
    if len(dates) != len(data) - 1:
        raise RuntimeError(f"文件长度超过交易日历: {path}")
    return pd.Series(data[1:].astype(float), index=dates), start


def write_bin(path: Path, start: int, values: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    output = np.concatenate((np.array([float(start)], dtype="<f4"), values.astype("<f4")))
    output.tofile(path)


def active_csi500(qlib_dir: Path, date: str) -> list[str]:
    symbols: set[str] = set()
    for line in safe_read_lines(qlib_dir / "instruments" / "csi500.txt"):
        parts = line.split()
        if len(parts) == 3 and parts[1] <= date <= parts[2]:
            symbols.add(parts[0].lower())
    if len(symbols) != 500:
        raise RuntimeError(f"{date} 的 CSI500 成分数量应为 500，实际为 {len(symbols)}")
    return sorted(symbols)


def constituent_snapshot_problem(qlib_dir: Path, date: str) -> str | None:
    active_rows = []
    for line in safe_read_lines(qlib_dir / "instruments" / "csi500.txt"):
        parts = line.split()
        if len(parts) == 3 and parts[1] <= date <= parts[2]:
            active_rows.append(parts)
    if len(active_rows) != 500:
        return f"成分记录应为 500 条，实际为 {len(active_rows)} 条"
    days = safe_read_lines(qlib_dir / "calendars" / "day_future.txt")
    stamp = pd.Timestamp(date)
    if stamp.month >= 7:
        boundary = f"{stamp.year}-06-30"
    else:
        boundary = f"{stamp.year - 1}-12-31"
    expected = max((day for day in days if day <= boundary), default=None)
    starts = sorted({row[1] for row in active_rows})
    if expected and starts != [expected]:
        return f"当前成分区间起点为 {starts}，应先同步到最近半年度边界 {expected}"
    return None


def completed_cutoff() -> str:
    # A股日线通常在 18:00 后再更新；更早运行时只尝试到前一天。
    now = datetime.now()
    day = now.date() if now.hour >= 18 else (now.date() - timedelta(days=1))
    return day.isoformat()


def choose_dates(qlib_dir: Path, target_date: str | None, allow_long_gap: bool) -> tuple[str, list[str]]:
    calendar = read_calendar(qlib_dir)
    base = calendar[-1]
    future_path = qlib_dir / "calendars" / "day_future.txt"
    if not future_path.exists():
        raise RuntimeError(f"缺少未来交易日历: {future_path}")
    future = safe_read_lines(future_path)
    cutoff = target_date or completed_cutoff()
    if cutoff <= base:
        return base, []
    dates = [d for d in future if base < d <= cutoff]
    if not dates:
        raise RuntimeError(f"{base} 之后到 {cutoff} 之间没有可用交易日")
    if target_date and dates[-1] != target_date:
        raise RuntimeError(f"指定日期 {target_date} 不是交易日；最近交易日是 {dates[-1]}")
    if len(dates) > 20 and not allow_long_gap:
        raise RuntimeError(f"待补 {len(dates)} 个交易日，超过日常更新上限 20；确认长缺口后加 --allow-long-gap")
    return base, dates


def patch_request_timeout() -> None:
    original = requests.sessions.Session.request
    if getattr(original, "_qlib_daily_bounded", False):
        return

    def bounded(self, method, url, **kwargs):
        kwargs.setdefault("timeout", 25)
        return original(self, method, url, **kwargs)

    bounded._qlib_daily_bounded = True  # type: ignore[attr-defined]
    requests.sessions.Session.request = bounded


def load_csv(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    if "date" not in frame.columns:
        raise RuntimeError(f"行情缓存缺少 date: {path}")
    frame["date"] = frame["date"].astype(str).str[:10]
    frame = frame.drop_duplicates("date", keep="last").set_index("date").sort_index()
    for field in [*PRICE_FIELDS, "volume", "amount"]:
        if field in frame:
            frame[field] = pd.to_numeric(frame[field], errors="coerce")
    return frame


def save_frame(frame: pd.DataFrame, path: Path) -> pd.DataFrame:
    if frame is None or frame.empty:
        raise RuntimeError("数据源返回空行情")
    result = frame.copy()
    if "date" not in result.columns:
        result = result.reset_index()
    result["date"] = result["date"].astype(str).str[:10]
    missing = set([*PRICE_FIELDS, "volume", "amount", "date"]) - set(result.columns)
    if missing:
        raise RuntimeError(f"数据源缺少字段: {sorted(missing)}")
    path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(path, index=False)
    return load_csv(path)


def retry(callable_, label: str):
    last: Exception | None = None
    for attempt in range(4):
        try:
            return callable_()
        except Exception as exc:
            last = exc
            if attempt < 3:
                time.sleep(2 + attempt * 2)
    raise RuntimeError(f"{label} 下载失败: {last}")


def fetch_pair(symbol: str, begin: str, end: str, raw_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    raw_path = raw_dir / f"{symbol}_raw.csv"
    adj_path = raw_dir / f"{symbol}_qfq.csv"
    if raw_path.exists() and adj_path.exists():
        return load_csv(raw_path), load_csv(adj_path)

    import akshare as ak

    compact_begin = begin.replace("-", "")
    compact_end = end.replace("-", "")
    if symbol in (INDEX_SYMBOL, "sh689009"):
        if raw_path.exists():
            raw = load_csv(raw_path)
        else:
            raw = retry(
                lambda: save_frame(ak.stock_zh_a_cdr_daily(symbol, compact_begin, compact_end), raw_path),
                f"{symbol} 原始行情",
            )
        if symbol == INDEX_SYMBOL:
            if not adj_path.exists():
                raw.reset_index().to_csv(adj_path, index=False)
            adjusted = load_csv(adj_path)
        else:
            if adj_path.exists():
                adjusted = load_csv(adj_path)
            else:
                adjusted = retry(
                    lambda: save_frame(
                        ak.stock_zh_a_hist_tx(symbol, compact_begin, compact_end, adjust="qfq", timeout=25), adj_path
                    ),
                    f"{symbol} 前复权行情",
                )
        return raw, adjusted

    if raw_path.exists():
        raw = load_csv(raw_path)
    else:
        raw = retry(
            lambda: save_frame(
                ak.stock_zh_a_daily(symbol=symbol, start_date=compact_begin, end_date=compact_end, adjust=""), raw_path
            ),
            f"{symbol} 原始行情",
        )
    if adj_path.exists():
        adjusted = load_csv(adj_path)
    else:
        adjusted = retry(
            lambda: save_frame(
                ak.stock_zh_a_daily(symbol=symbol, start_date=compact_begin, end_date=compact_end, adjust="qfq"), adj_path
            ),
            f"{symbol} 前复权行情",
        )
    return raw, adjusted


def old_frame(qlib_dir: Path, symbol: str, calendar: list[str]) -> tuple[pd.DataFrame, dict[str, int]]:
    values: dict[str, pd.Series] = {}
    starts: dict[str, int] = {}
    for field in FIELDS:
        path = qlib_dir / "features" / symbol / f"{field}.day.bin"
        if not path.exists():
            raise RuntimeError(f"缺少字段文件: {path}")
        values[field], starts[field] = read_bin(path, calendar)
    return pd.DataFrame(values), starts


def make_rows(
    symbol: str,
    old: pd.DataFrame,
    raw: pd.DataFrame,
    adjusted: pd.DataFrame,
    dates: list[str],
) -> tuple[pd.DataFrame, SymbolResult]:
    overlap = sorted(set(old.index) & set(raw.index) & set(adjusted.index))
    overlap = [d for d in overlap if raw.loc[d, "volume"] > 0]
    if not overlap:
        raise RuntimeError("找不到本地数据与下载行情的重叠锚点")
    anchor = overlap[-1]
    if anchor != old.index[-1]:
        # Suspended shares may legitimately use an earlier anchor, but it must be recent.
        distance = (pd.Timestamp(old.index[-1]) - pd.Timestamp(anchor)).days
        if distance > 30:
            raise RuntimeError(f"最近有效锚点 {anchor} 距本地末日过远")

    price_scale = old.loc[anchor, "close"] / adjusted.loc[anchor, "close"]
    adjclose_scale = old.loc[anchor, "adjclose"] / adjusted.loc[anchor, "close"]
    previous = old.iloc[-1].copy()
    previous_raw_close = float(previous["close"] / previous["factor"])
    rows: list[dict[str, float]] = []
    suspended: list[str] = []

    for date in dates:
        traded = (
            date in raw.index
            and date in adjusted.index
            and np.isfinite(raw.loc[date, "volume"])
            and raw.loc[date, "volume"] > 0
        )
        if not traded:
            suspended.append(date)
            # Qlib represents a suspension as missing data on that market day.
            # Keep the previous traded row only as the anchor for the next trade.
            row = {field: np.nan for field in FIELDS}
        else:
            row = {field: float(adjusted.loc[date, field] * price_scale) for field in PRICE_FIELDS}
            factor = row["close"] / float(raw.loc[date, "close"])
            raw_volume = float(raw.loc[date, "volume"])
            raw_amount = float(raw.loc[date, "amount"])
            raw_close = float(raw.loc[date, "close"])
            row.update({
                "volume": raw_volume * 0.01 / factor,
                "amount": raw_amount * 0.001,
                "vwap": raw_amount / raw_volume * factor,
                "factor": factor,
                "change": raw_close / previous_raw_close - 1.0,
                "adjclose": float(adjusted.loc[date, "close"] * adjclose_scale),
            })
            previous_raw_close = raw_close
        if traded:
            previous = pd.Series(row)
        rows.append(row)

    frame = pd.DataFrame(rows, index=dates, columns=FIELDS)
    return frame, SymbolResult(symbol=symbol, anchor=anchor, rows=len(frame), suspended=",".join(suspended))


def stage_symbol(
    symbol: str,
    qlib_dir: Path,
    calendar: list[str],
    dates: list[str],
    raw_dir: Path,
    stage_dir: Path,
    begin: str,
    end: str,
) -> SymbolResult:
    try:
        old, starts = old_frame(qlib_dir, symbol, calendar)
        raw, adjusted = fetch_pair(symbol, begin, end, raw_dir)
        if symbol == INDEX_SYMBOL:
            missing = [date for date in dates if date not in raw.index or date not in adjusted.index]
            if missing:
                raise RuntimeError(f"指数行情尚未发布这些交易日: {','.join(missing)}")
        rows, result = make_rows(symbol, old, raw, adjusted, dates)
        for field in FIELDS:
            # Preserve calendar positions when a historical file ends early or
            # fields have different start dates. Missing historical days remain NaN.
            historical = old[field].reindex(calendar[starts[field] :])
            values = np.concatenate((historical.to_numpy(dtype=float), rows[field].to_numpy(dtype=float)))
            write_bin(stage_dir / "features" / symbol / f"{field}.day.bin", starts[field], values)
        return result
    except Exception as exc:
        return SymbolResult(symbol=symbol, status="failed", error=str(exc))


def extend_instrument(
    source: Path, destination: Path, base: str, target: str, allowed_symbols: set[str]
) -> int:
    output: list[str] = []
    changed = 0
    for line in safe_read_lines(source):
        parts = line.split()
        if len(parts) == 3 and parts[0].lower() in allowed_symbols and parts[2] == base:
            parts[2] = target
            line = "\t".join(parts)
            changed += 1
        output.append(line)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("\n".join(output) + "\n", encoding="utf-8")
    return changed


def prepare(qlib_dir: Path, target_date: str | None, workers: int, allow_long_gap: bool, keep_going: bool) -> Path | None:
    base, dates = choose_dates(qlib_dir, target_date, allow_long_gap)
    if not dates:
        print(f"已经是最新状态，本地最后交易日={base}")
        return None
    target = dates[-1]
    snapshot_problem = constituent_snapshot_problem(qlib_dir, base)
    if snapshot_problem:
        raise RuntimeError(f"沪深500成分表过期，停止更新：{snapshot_problem}")
    symbols = [INDEX_SYMBOL, *active_csi500(qlib_dir, base)]
    run_dir = RUNS_ROOT / f"{base.replace('-', '')}_to_{target.replace('-', '')}"
    raw_dir = run_dir / "raw"
    stage_dir = run_dir / "stage"
    raw_dir.mkdir(parents=True, exist_ok=True)
    if stage_dir.exists():
        shutil.rmtree(stage_dir)
    stage_dir.mkdir(parents=True)

    calendar = read_calendar(qlib_dir)
    new_calendar = calendar + dates
    (stage_dir / "calendars").mkdir(parents=True)
    (stage_dir / "calendars" / "day.txt").write_text("\n".join(new_calendar) + "\n", encoding="utf-8")
    begin = (pd.Timestamp(base) - pd.Timedelta(days=35)).strftime("%Y-%m-%d")
    end = target
    patch_request_timeout()
    print(f"准备批次: {base} -> {target}，新增 {len(dates)} 个交易日，标的 {len(symbols)} 个")

    # Check the benchmark first. If the provider has not published the latest
    # market day yet, stop before making hundreds of unnecessary requests.
    index_result = stage_symbol(
        INDEX_SYMBOL, qlib_dir, calendar, dates, raw_dir, stage_dir, begin, end
    )
    if index_result.status != "ok":
        for cached in raw_dir.glob(f"{INDEX_SYMBOL}_*.csv"):
            cached.unlink(missing_ok=True)
        raise RuntimeError(f"市场日线尚未准备好: {index_result.error}")

    results: list[SymbolResult] = [index_result]
    stock_symbols = symbols[1:]
    with cf.ThreadPoolExecutor(max_workers=max(1, min(workers, 8))) as pool:
        futures = {
            pool.submit(stage_symbol, symbol, qlib_dir, calendar, dates, raw_dir, stage_dir, begin, end): symbol
            for symbol in stock_symbols
        }
        for count, future in enumerate(cf.as_completed(futures), 1):
            results.append(future.result())
            if count % 25 == 0 or count == len(futures):
                failed = sum(r.status != "ok" for r in results)
                print(f"已处理 {count + 1}/{len(symbols)}，失败 {failed}", flush=True)

    failed = [r for r in results if r.status != "ok"]
    (run_dir / "results.json").write_text(
        json.dumps([asdict(r) for r in sorted(results, key=lambda x: x.symbol)], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    if failed:
        print("失败标的（最多显示 20 个）:")
        for item in failed[:20]:
            print(f"  {item.symbol}: {item.error}")
        if keep_going:
            print("缓存已经保留；重新执行 prepare 会从缓存继续。")
        raise RuntimeError(f"共有 {len(failed)} 个标的下载或生成失败，未形成可写入批次")

    instrument_counts = {}
    for name in ("all.txt", "csi500.txt"):
        source = qlib_dir / "instruments" / name
        destination = stage_dir / "instruments" / name
        instrument_counts[name] = extend_instrument(source, destination, base, target, set(symbols))

    manifest: dict = {
        "version": 1,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "qlib_dir": str(qlib_dir.resolve()),
        "base_date": base,
        "target_date": target,
        "new_dates": dates,
        "symbols": symbols,
        "instrument_counts": instrument_counts,
        "files": {},
    }
    relative_files = [Path("calendars/day.txt"), Path("instruments/all.txt"), Path("instruments/csi500.txt")]
    relative_files.extend(
        Path("features") / symbol / f"{field}.day.bin" for symbol in symbols for field in FIELDS
    )
    for relative in relative_files:
        source = qlib_dir / relative
        staged = stage_dir / relative
        manifest["files"][relative.as_posix()] = {
            "source_sha256": sha256(source),
            "staged_sha256": sha256(staged),
        }
    (run_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    verify(run_dir, qlib_dir, check_source=True)
    RUNS_ROOT.mkdir(parents=True, exist_ok=True)
    (RUNS_ROOT / "latest_run.txt").write_text(str(run_dir.resolve()), encoding="utf-8")
    print(f"准备完成，尚未修改正式数据: {run_dir}")
    return run_dir


def resolve_run_dir(run_dir: Path | None) -> Path:
    if run_dir:
        return run_dir.resolve()
    pointer = RUNS_ROOT / "latest_run.txt"
    if not pointer.exists():
        raise RuntimeError("找不到已准备批次，请先运行 prepare")
    return Path(pointer.read_text(encoding="utf-8").strip()).resolve()


def verify(run_dir: Path, qlib_dir: Path | None = None, check_source: bool = True) -> dict:
    manifest_path = run_dir / "manifest.json"
    if not manifest_path.exists():
        raise RuntimeError(f"缺少批次清单: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    source_root = (qlib_dir or Path(manifest["qlib_dir"])).resolve()
    stage_dir = run_dir / "stage"
    new_dates = manifest["new_dates"]
    calendar = safe_read_lines(stage_dir / "calendars" / "day.txt")
    if calendar[-len(new_dates) :] != new_dates or calendar != sorted(set(calendar)):
        raise RuntimeError("暂存交易日历校验失败")
    if len(manifest["symbols"]) != 501:
        raise RuntimeError(f"暂存标的数量应为 501，实际为 {len(manifest['symbols'])}")

    max_relation_error = 0.0
    traded_by_date = {date: 0 for date in new_dates}
    for relative_text, hashes in manifest["files"].items():
        relative = Path(relative_text)
        staged = stage_dir / relative
        if not staged.exists() or sha256(staged) != hashes["staged_sha256"]:
            raise RuntimeError(f"暂存文件缺失或已改变: {relative_text}")
        if check_source:
            source = source_root / relative
            if not source.exists() or sha256(source) != hashes["source_sha256"]:
                raise RuntimeError(f"正式文件在准备后发生变化: {relative_text}")

    for symbol in manifest["symbols"]:
        frames = {}
        for field in FIELDS:
            series, _ = read_bin(stage_dir / "features" / symbol / f"{field}.day.bin", calendar)
            frames[field] = series.loc[new_dates]
        frame = pd.DataFrame(frames)
        finite_rows = frame.notna().all(axis=1)
        missing_rows = frame.isna().all(axis=1)
        if not (finite_rows | missing_rows).all():
            raise RuntimeError(f"{symbol} 存在部分字段缺失的交易日")
        finite_frame = frame.loc[finite_rows]
        if (finite_frame[["volume", "amount"]] < 0).any().any():
            raise RuntimeError(f"{symbol} 成交量额为负数")
        if ((finite_frame["low"] > finite_frame[["open", "close", "high"]].min(axis=1) + 1e-5) |
                (finite_frame["high"] < finite_frame[["open", "close", "low"]].max(axis=1) - 1e-5)).any():
            raise RuntimeError(f"{symbol} OHLC 关系异常")
        traded = finite_rows & (frame["volume"] > 0)
        if symbol != INDEX_SYMBOL:
            for date in new_dates:
                traded_by_date[date] += int(traded.loc[date])
        if traded.any():
            relation = frame.loc[traded, "amount"] / (
                frame.loc[traded, "volume"] * frame.loc[traded, "vwap"]
            )
            max_relation_error = max(max_relation_error, float((relation / 0.1 - 1).abs().max()))
    if max_relation_error > 3e-5:
        raise RuntimeError(f"amount/volume/vwap 关系异常，最大误差={max_relation_error}")
    thin_dates = {date: count for date, count in traded_by_date.items() if count < 450}
    if thin_dates:
        raise RuntimeError(f"交易股票数量异常（应至少 450）: {thin_dates}")
    print(
        f"批次校验通过: {manifest['base_date']} -> {manifest['target_date']}，"
        f"交易日 {len(new_dates)}，标的 {len(manifest['symbols'])}"
    )
    return manifest


def apply(run_dir: Path, qlib_dir: Path) -> None:
    manifest = verify(run_dir, qlib_dir, check_source=True)
    backup = run_dir / "backup_before_apply"
    if backup.exists():
        raise RuntimeError(f"该批次已经存在备份，拒绝重复写入: {backup}")
    stage_dir = run_dir / "stage"
    backup.mkdir(parents=True)
    for relative_text in manifest["files"]:
        relative = Path(relative_text)
        destination = backup / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(qlib_dir / relative, destination)
    (backup / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    replaced: list[Path] = []
    try:
        # Features first; calendar and instruments are committed last.
        relatives = [Path(p) for p in manifest["files"]]
        relatives.sort(key=lambda p: (p.parts[0] != "features", p.as_posix()))
        for relative in relatives:
            destination = qlib_dir / relative
            temporary = destination.with_name(destination.name + ".daily_update_tmp")
            shutil.copy2(stage_dir / relative, temporary)
            os.replace(temporary, destination)
            replaced.append(relative)
    except Exception:
        for relative in replaced:
            shutil.copy2(backup / relative, qlib_dir / relative)
        raise
    (run_dir / "APPLIED.txt").write_text(datetime.now().isoformat(timespec="seconds"), encoding="utf-8")
    print(f"正式数据更新完成，最新交易日={manifest['target_date']}")
    print(f"原文件备份={backup}")


def status(qlib_dir: Path) -> None:
    calendar = read_calendar(qlib_dir)
    latest = calendar[-1]
    symbols = active_csi500(qlib_dir, latest)
    cutoff = completed_cutoff()
    future_path = qlib_dir / "calendars" / "day_future.txt"
    future = safe_read_lines(future_path) if future_path.exists() else []
    pending = [d for d in future if latest < d <= cutoff]
    print(f"Qlib目录: {qlib_dir.resolve()}")
    print(f"本地最后交易日: {latest}")
    print(f"CSI500成分数量: {len(symbols)}")
    snapshot_problem = constituent_snapshot_problem(qlib_dir, latest)
    if snapshot_problem:
        print(f"警告：沪深500成分表过期：{snapshot_problem}")
    if pending:
        print(f"按本机日期推算待更新: {len(pending)} 个交易日，至 {pending[-1]}")
    else:
        print("按本机日期推算暂无待更新交易日")


def main() -> int:
    args = parse_args()
    qlib_dir = args.qlib_dir.resolve()
    if not qlib_dir.exists():
        raise SystemExit(f"Qlib 数据目录不存在: {qlib_dir}")
    try:
        if args.command == "status":
            status(qlib_dir)
        elif args.command == "prepare":
            prepare(qlib_dir, args.target_date, args.workers, args.allow_long_gap, args.keep_going)
        elif args.command == "verify":
            verify(resolve_run_dir(args.run_dir), qlib_dir, check_source=True)
        elif args.command == "apply":
            apply(resolve_run_dir(args.run_dir), qlib_dir)
        elif args.command == "update":
            run_dir = prepare(qlib_dir, args.target_date, args.workers, args.allow_long_gap, args.keep_going)
            if run_dir is not None:
                apply(run_dir, qlib_dir)
    except Exception as exc:
        print(f"更新失败: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
