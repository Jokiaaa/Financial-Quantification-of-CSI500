from pathlib import Path
import argparse
import importlib.util
import sys
import json
from datetime import datetime
import pandas as pd

PACKAGE = Path(r'C:\Users\30855\Desktop\frozen_hl378_mw2e4_T40_D2_20260528(2)')

def latest_pred(experiment):
    root = PACKAGE / 'mlruns' / experiment
    paths = list(root.glob('*/artifacts/pred.pkl'))
    if not paths:
        raise RuntimeError(f'预测文件尚未生成，请等待训练完成：{root}')
    return max(paths, key=lambda p: p.stat().st_mtime)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check-only', action='store_true')
    args = parser.parse_args()
    h1_path = Path(r'C:\Users\30855\Desktop\A\更新数据\mlruns\325189916040279901\a3c5984a6fd74e78919e6a21fc0de7ee\artifacts\pred.pkl')
    h2_path = PACKAGE / 'mlruns/282454532613173259/69fc82777b134165a103ad4e2c999811/artifacts/pred.pkl'
    source = PACKAGE / 'code/formal_full_hl378_mw2e4_relay_pcf_risk_qlib_backtest.py'
    spec = importlib.util.spec_from_file_location('formal_2026_relay', source)
    formal = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = formal
    spec.loader.exec_module(formal)
    h1, h2 = formal.load_pred(h1_path), formal.load_pred(h2_path)
    switch = pd.Timestamp('2026-07-01')
    h1 = h1.loc[(h1.index.get_level_values('datetime') >= '2026-01-01') & (h1.index.get_level_values('datetime') < switch)]
    h2 = h2.loc[(h2.index.get_level_values('datetime') >= switch) & (h2.index.get_level_values('datetime') < '2027-01-01')]
    if h1.empty or h2.empty:
        raise RuntimeError('H1或H2的预测日期范围不正确')
    signal = formal.stabilize_signal(pd.concat([h1, h2]).sort_index())
    if signal.index.has_duplicates:
        raise RuntimeError('预测存在重复日期和股票')
    first = signal.index.get_level_values('datetime').min().strftime('%Y-%m-%d')
    last = signal.index.get_level_values('datetime').max().strftime('%Y-%m-%d')
    days = signal.index.get_level_values('datetime').unique()
    calendar = pd.to_datetime((formal.QLIB_PROVIDER / 'calendars/day.txt').read_text().splitlines())
    missing = calendar[(calendar >= first) & (calendar <= last)].difference(days)
    if len(missing):
        raise RuntimeError(f'预测缺少整个交易日：{list(missing)}')
    eval_start = h2.index.get_level_values('datetime').min().strftime('%Y-%m-%d')
    print(f'H1: {h1_path}\nH2: {h2_path}\n含预热的连续回测区间: {first} -> {last}\n正式评价区间: {eval_start} -> {last}', flush=True)
    if args.check_only:
        return
    out = PACKAGE / 'output' / ('relay_tie_2026_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
    out.mkdir(parents=True)
    cfg = formal.load_yaml(PACKAGE / 'yamls/hl378_mw2e4_2026H2_T40_D2.yaml')
    dates = dict(relay_start=first, relay_end=last, eval_start=eval_start, eval_end=last)
    formal.init_worker()
    report, _ = formal.run_backtest(signal, cfg, dates, 'relay_tie')
    report.reset_index().to_csv(out / 'daily_report.csv', index=False, encoding='utf-8-sig')
    signal.to_pickle(out / 'combined_pred.pkl')
    metrics = formal.calc_metrics(report)
    pd.DataFrame([metrics]).to_csv(out / 'summary.csv', index=False, encoding='utf-8-sig')
    (out / 'run_meta.json').write_text(json.dumps(dict(h1=str(h1_path), h2=str(h2_path), switch_date='2026-07-01', dates=dates), ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"总收益={metrics['total_return']:.2%}，基准收益={metrics['benchmark_total_return']:.2%}，最大回撤={metrics['mdd']:.2%}")
    print(f'结果目录：{out}')

if __name__ == '__main__':
    main()
