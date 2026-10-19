# 模型1接力基本盘健康度风控实验记录（2026-05-27）

## 1. 实验目的

本轮目标是做“基本盘弱的时候退出”的风控，而不是用指数均线判断市场强弱。风控信号来自模型1接力基本盘自身的历史表现，并严格使用 T-1 已知数据决定 T 的仓位，避免未来信息泄露。

## 2. 指定基底

- yaml 基底：C:\Users\30855\qlib\examples\benchmarks\LightGBM\semiannual_rolling_yamls_for_router\hl378_mw2e4_*_T40_D2.yaml
- pred 来源清单：C:\Users\30855\qlib\examples\benchmarks\LightGBM\semiannual_rolling_yamls_for_router\pkl+回测\近期加权valid4.txt
- 接力基底脚本：C:\Users\30855\qlib\examples\benchmarks\LightGBM\semiannual_rolling_yamls_for_router\run_hl378_halfyear_relay_backtest.py
- 接力逻辑：复用基底脚本中的 CASE_MAP_BY_MODEL / combine_preds / stabilize_signal / infer_case_dates / load_yaml / load_pred
- 同分规则：复用 exact-tie instrument 稳定同分处理 stabilize_signal
- 本轮新增实验脚本：C:\Users\30855\Documents\risk\run_base_health_exit_grid.py

## 3. 未来信息检查

B3 风控规则本身没有未来信息泄露。脚本中用于触发的基底健康度指标均为滚动后 .shift(1)：

```python
feat["roll10_net_excess"] = net.rolling(10, min_periods=10).sum().shift(1)
```

含义是：T 日是否空仓，只使用 T-1 及以前的基底表现。需要注意，它依赖一条“无风控原基底”的影子净值曲线；实盘中需要每天同步计算该影子基底表现。

## 4. 实验文件路径汇总

### 4.1 脚本

- 健康度风控脚本：C:\Users\30855\Documents\risk\run_base_health_exit_grid.py
- 基底接力脚本：C:\Users\30855\qlib\examples\benchmarks\LightGBM\semiannual_rolling_yamls_for_router\run_hl378_halfyear_relay_backtest.py
- 风控策略类：C:\Users\30855\qlib\examples\benchmarks\LightGBM\semiannual_rolling_yamls_for_router\risk_regime_strategy.py

### 4.2 本轮输出目录和关键文件

- A/B/C 初筛目录：C:\Users\30855\qlib\examples\benchmarks\LightGBM\semiannual_rolling_yamls_for_router\analysis\base_health_exit_grid_20260527
- A/B/C 初筛汇总：C:\Users\30855\qlib\examples\benchmarks\LightGBM\semiannual_rolling_yamls_for_router\analysis\base_health_exit_grid_20260527\summary.csv
- B 系列前半段目录：C:\Users\30855\qlib\examples\benchmarks\LightGBM\semiannual_rolling_yamls_for_router\analysis\base_health_exit_B_grid_20260527
- B 系列后半段目录：C:\Users\30855\qlib\examples\benchmarks\LightGBM\semiannual_rolling_yamls_for_router\analysis\base_health_exit_B_grid_20260527_tail
- B 系列合并目录：C:\Users\30855\qlib\examples\benchmarks\LightGBM\semiannual_rolling_yamls_for_router\analysis\base_health_exit_B_grid_20260527_merged
- B 系列合并汇总：C:\Users\30855\qlib\examples\benchmarks\LightGBM\semiannual_rolling_yamls_for_router\analysis\base_health_exit_B_grid_20260527_merged\summary.csv
- B 系列策略排名：C:\Users\30855\qlib\examples\benchmarks\LightGBM\semiannual_rolling_yamls_for_router\analysis\base_health_exit_B_grid_20260527_merged\policy_rank.csv
- B3 单独补跑 2023H1：C:\Users\30855\qlib\examples\benchmarks\LightGBM\semiannual_rolling_yamls_for_router\analysis\base_health_exit_B3_2023H1_20260527\summary.csv
- B3 vs B3R1 全阶段：C:\Users\30855\qlib\examples\benchmarks\LightGBM\semiannual_rolling_yamls_for_router\analysis\base_health_exit_B3_B3R1_full_20260527\summary.csv
- B3 vs B3C1 全阶段：C:\Users\30855\qlib\examples\benchmarks\LightGBM\semiannual_rolling_yamls_for_router\analysis\base_health_exit_B3_B3C1_full_20260527\summary.csv
- MA 三态 TopK 无泄露复核：C:\Users\30855\qlib\examples\benchmarks\LightGBM\semiannual_rolling_yamls_for_router\analysis\base_relay_shift1_topk_regime_diag_20260527\diag_summary_3combos.csv

## 5. 已淘汰路线：MA 三态 TopK 风控

该路线使用无泄露 T-1 -> T 后整体不如原基底，结论是不适合作为主线。

| 组合 | 阶段数 | 改善段数 | 原基底复利 | 风控后复利 | 提升 |
| --- | --- | --- | --- | --- | --- |
| buf_0p03_n24_d12 | 8 | 3 | 53.56% | 24.05% | -29.51% |
| buf_0p04_n32_d16 | 8 | 3 | 53.56% | 22.21% | -31.35% |
| buf_0p03_n24_d0 | 8 | 2 | 53.56% | 18.45% | -35.11% |

## 6. 基本盘健康度风控初筛（A/B/C）

A/B/C 初筛中，B 规则最有价值：10d基底净超额 < -5% -> 空仓10天。C 规则因为长期困在防守状态，表现很差。

| 规则 | 阶段数 | 改善段数 | 回撤改善段数 | 空仓天数 | 原基底复利 | 风控后复利 | 提升 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| B_10d_net_m5pct_cash10 | 8 | 4 | 6 | 0 | 53.56% | 54.03% | 0.47% |
| A_5d_net_m3pct_cash5 | 8 | 3 | 6 | 10 | 53.56% | 46.92% | -6.64% |
| C_5d_net_m3pct_or_dd_m6pct_top12_recover5d | 8 | 1 | 5 | 457 | 53.56% | 1.65% | -51.91% |

## 7. B 系列小网格

围绕 10d基底净超额 的阈值和空仓天数做小网格。最优为 B3：10d基底净超额 < -4% -> 空仓15天。

| 规则 | 阶段数 | 改善段数 | 回撤改善段数 | 空仓天数 | 原基底复利 | 风控后复利 | 提升 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| B3_10d_net_m4pct_cash15 | 8 | 4 | 6 | 30 | 53.56% | 60.46% | 6.90% |
| B2_10d_net_m4pct_cash10 | 8 | 4 | 6 | 20 | 53.56% | 58.22% | 4.66% |
| B6_10d_net_m6pct_cash5 | 8 | 4 | 6 | 0 | 53.56% | 55.68% | 2.12% |
| B5_10d_net_m5pct_cash15 | 8 | 4 | 6 | 0 | 53.56% | 55.41% | 1.85% |
| B7_10d_net_m6pct_cash10 | 8 | 4 | 6 | 0 | 53.56% | 55.19% | 1.63% |
| B8_10d_net_m6pct_cash15 | 8 | 4 | 6 | 0 | 53.56% | 55.18% | 1.63% |
| B4_10d_net_m5pct_cash5 | 8 | 4 | 6 | 0 | 53.56% | 54.16% | 0.60% |
| B_10d_net_m5pct_cash10 | 8 | 4 | 6 | 0 | 53.56% | 54.03% | 0.47% |
| B1_10d_net_m4pct_cash5 | 8 | 3 | 6 | 10 | 53.56% | 43.21% | -10.35% |

## 8. 全阶段主线对照：B3 / B3R1 / B3C1

- B3：10d基底净超额 < -4% -> 空仓15天
- B3R1：10d基底净超额 < -4% -> 最少空仓5天，若5d净超额转正提前恢复，最多15天
- B3C1：10d基底净超额 < -4% 且 10d绝对收益 < 0 -> 空仓15天

全阶段 2018H2 ~ 2026YTD 结果如下：

| 规则 | 阶段数 | 改善段数 | 回撤改善段数 | 空仓天数 | 原基底复利 | 风控后复利 | 提升 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| B3_10d_net_m4pct_cash15 | 16 | 10 | 11 | 60 | 177.90% | 193.95% | 16.04% |
| B3R1_10d_net_m4pct_cash_min5_recover5d_max15 | 16 | 9 | 11 | 23 | 177.90% | 172.33% | -5.57% |
| B3C1_10d_net_m4pct_abs10d_neg_cash15 | 16 | 10 | 11 | 45 | 177.90% | 187.98% | 10.07% |

结论：B3R1 和 B3C1 都不如 B3。B3R1 牺牲了 2022H1 的关键保护；B3C1 没有修复 2018H2 / 2025H2 的异常误伤，还削弱了 2020H2 / 2026YTD。

## 9. 当前最成功策略：B3

规则：

`	ext
如果 T-1 已知的过去10日基底净超额收益 < -4%，则 T 起空仓15个交易日。
`

全阶段总收益：

- 原基底接力：177.90%
- B3 风控后：193.95%
- 提升：+16.05pct
- 改善阶段：10 / 16
- 回撤改善阶段：11 / 16

### 9.1 B3 分段收益对比

| 阶段 | 原基底收益 | B3收益 | 收益差 | 原基底回撤 | B3回撤 | 空仓天数 |
| --- | --- | --- | --- | --- | --- | --- |
| 2018H2 | -10.39% | -18.43% | -8.04% | -16.21% | -23.78% | 0 |
| 2019H1 | 26.70% | 33.59% | 6.89% | -19.81% | -19.32% | 0 |
| 2019H2 | -2.97% | -2.42% | 0.56% | -13.81% | -14.06% | 0 |
| 2020H1 | 13.00% | 14.45% | 1.46% | -16.29% | -14.90% | 0 |
| 2020H2 | 5.16% | 7.28% | 2.12% | -12.46% | -8.92% | 15 |
| 2021H1 | 13.34% | 11.68% | -1.66% | -5.31% | -5.71% | 0 |
| 2021H2 | 17.68% | 20.58% | 2.89% | -7.57% | -5.45% | 15 |
| 2022H1 | -1.29% | 7.09% | 8.37% | -25.72% | -11.51% | 15 |
| 2022H2 | -6.23% | -4.87% | 1.36% | -11.54% | -10.52% | 0 |
| 2023H1 | 3.66% | 4.20% | 0.54% | -6.22% | -6.11% | 0 |
| 2023H2 | -12.89% | -10.12% | 2.77% | -14.11% | -11.13% | 0 |
| 2024H1 | -7.07% | -7.44% | -0.37% | -19.09% | -19.80% | 0 |
| 2024H2 | 24.81% | 23.49% | -1.32% | -14.11% | -12.71% | 0 |
| 2025H1 | 8.23% | 11.12% | 2.89% | -14.04% | -12.93% | 0 |
| 2025H2 | 34.80% | 23.94% | -10.86% | -7.45% | -7.60% | 15 |
| 2026YTD | 12.54% | 11.33% | -1.21% | -8.10% | -6.90% | 0 |

## 10. 结论

1. 本轮所有有效风控应继续以“基底自身健康度”为核心，而不是指数 MA 三态。
2. 当前最成功策略是 B3：10d基底净超额 < -4% -> 空仓15天。
3. B3 在全阶段将复利收益从 177.90% 提升到 193.95%，同时 11/16 阶段回撤改善。
4. B3 的主要问题是：
   - 2018H2 明显变差：原基底 -10.39%，B3 -18.43%。
   - 2025H2 强势段误伤：原基底 34.80%，B3 23.94%。
5. B3R1 提前恢复版和 B3C1 绝对收益确认版都未能优于 B3，因此暂不作为主线。

## 11. 下一步建议

下一步不要继续盲目加确认条件。应针对 2018H2 和 2025H2 做触发日诊断：

- 查看对应阶段的 ase_health_schedule.csv，确认具体哪一天触发。
- 对比触发后 15 天内原基底实际收益，判断空仓是避险还是错过反弹。
- 若误伤集中在“接力预热段改变初始持仓”，需要把触发限制在 eval 窗口内或加入切换期专门规则。
- 若误伤来自强势段短暂跑输，则考虑加入“只在基底10日绝对收益显著为负”或“触发后分批恢复”，但 B3C1 已说明简单 10d_abs < 0 不够。

当前可写入阶段性结论：B3 是目前全阶段最成功的基本盘弱退出策略，但仍需对 2018H2 / 2025H2 做触发日级别归因。



