# HL378 半年度接力保守版实验记录（2022H1-2026YTD）

记录时间：2026-05-05

## 1. 实验目标

本次实验的目标是评估 `HL378` 半年度接力回测中的保守 guard 机制是否真正提升了 2022H1 到 2026YTD 各段的综合表现，重点比较三类方案：

- `orig`：直接使用当期模型原始预测
- `relay_full`：使用上一段与当前段的接力拼接预测
- `relay_conservative`：在 `relay_full` 基础上加入保守 guard、冷却期和低 overlap 回退逻辑

后续又进一步做了一个低成本规则筛选，判断当前 guard 是否过于保守，以及是否存在更窄的 guard 触发方式。

## 2. 关键脚本与输出路径

主脚本：

- `C:\Users\30855\qlib\examples\benchmarks\LightGBM\semiannual_rolling_yamls_for_router\run_hl378_halfyear_relay_backtest_conservative.py`
- `C:\Users\30855\qlib\examples\benchmarks\LightGBM\semiannual_rolling_yamls_for_router\run_hl378_halfyear_relay_backtest.py`

工作目录：

- `C:\Users\30855\qlib\examples\benchmarks\LightGBM\semiannual_rolling_yamls_for_router`

本次正式结果输出目录：

- `C:\Users\30855\qlib\examples\benchmarks\LightGBM\semiannual_rolling_yamls_for_router\analysis\hl378_halfyear_relay_backtest_conservative`

总汇总文件：

- `C:\Users\30855\qlib\examples\benchmarks\LightGBM\semiannual_rolling_yamls_for_router\analysis\hl378_halfyear_relay_backtest_conservative\summary.csv`

各半年度分段的明细目录：

- `...\analysis\hl378_halfyear_relay_backtest_conservative\2022H1`
- `...\analysis\hl378_halfyear_relay_backtest_conservative\2022H2`
- `...\analysis\hl378_halfyear_relay_backtest_conservative\2023H1`
- `...\analysis\hl378_halfyear_relay_backtest_conservative\2023H2`
- `...\analysis\hl378_halfyear_relay_backtest_conservative\2024H1`
- `...\analysis\hl378_halfyear_relay_backtest_conservative\2024H2`
- `...\analysis\hl378_halfyear_relay_backtest_conservative\2025H1`
- `...\analysis\hl378_halfyear_relay_backtest_conservative\2025H2`
- `...\analysis\hl378_halfyear_relay_backtest_conservative\2026YTD`

每个分段目录内包含：

- `meta.json`：该段使用的 yaml、pred 路径、切换日期、guard 判定和 overlap 统计
- `compare_metrics.csv`：`orig / relay_full / relay_conservative` 指标对比
- `orig_report_eval.csv`
- `relay_full_report_eval.csv`
- `relay_conservative_report_eval.csv`
- `cooldown_schedule.csv`
- 部分 case 还会有 `cooldown_history.csv`

## 3. 使用的数据与模型来源

本次运行使用的是 `mw2e4` 这条链路，不是 `mw3e4`。

YAML 配置路径示例：

- `...\hl378_mw2e4_2022H1_T40_D2.yaml`
- `...\hl378_mw2e4_2022H2_T40_D2.yaml`
- `...\hl378_mw2e4_2023H1_T40_D2.yaml`
- `...\hl378_mw2e4_2023H2_T40_D2.yaml`
- `...\hl378_mw2e4_2024H1_T40_D2.yaml`
- `...\hl378_mw2e4_2024H2_T40_D2.yaml`
- `...\hl378_mw2e4_2025H1_T40_D2.yaml`
- `...\hl378_mw2e4_2025H2_T40_D2.yaml`
- `...\hl378_mw2e4_2026YTD_T40_D2.yaml`

预测文件来源有两类：

- 较早一段来自 `...\mlruns\376065131763570804\...\artifacts\pred.pkl`
- 2022H1 之后主要来自 `...\mlruns_recent_weighted_valid4_batch\...\artifacts\pred.pkl`

切换逻辑所依赖的数据在每个 case 的 `meta.json` 中都写明了 `prev_pred` 和 `curr_pred` 的完整路径，可以直接回溯。

示例：

- `2022H1` 上一段 pred：
  `C:\Users\30855\qlib\examples\benchmarks\LightGBM\semiannual_rolling_yamls_for_router\mlruns\376065131763570804\fb7324915f634cf886ba39fcd6bde715\artifacts\pred.pkl`
- `2022H1` 当前段 pred：
  `C:\Users\30855\qlib\examples\benchmarks\LightGBM\semiannual_rolling_yamls_for_router\mlruns_recent_weighted_valid4_batch\601906743829434398\e5233e6e5b4f49ab9dc5d0b900e471a7\artifacts\pred.pkl`
- `2026YTD` 上一段 pred：
  `C:\Users\30855\qlib\examples\benchmarks\LightGBM\semiannual_rolling_yamls_for_router\mlruns_recent_weighted_valid4_batch\360518579130108206\f177ef9272a345da89b12c5f79450c3a\artifacts\pred.pkl`
- `2026YTD` 当前段 pred：
  `C:\Users\30855\qlib\examples\benchmarks\LightGBM\semiannual_rolling_yamls_for_router\mlruns_recent_weighted_valid4_batch\701867599063671665\016f5311e4d145eda40cffeb8a526dde\artifacts\pred.pkl`

## 4. 保守版实验流程

### 4.1 正式运行

在目录 `semiannual_rolling_yamls_for_router` 下运行：

```powershell
C:\Users\30855\miniconda3\envs\qlib\python.exe run_hl378_halfyear_relay_backtest_conservative.py --cases 2022H1 2022H2 2023H1 2023H2 2024H1 2024H2 2025H1 2025H2 2026YTD
```

### 4.2 当前 conservative 逻辑

脚本中主要使用了以下规则：

- `prev_fraction = 0.5`
- `overlap_guard = 0.50`
- `extreme_low_overlap_guard = 0.15`
- `cooldown_days = 20`
- `cooldown_n_drop = 1`

它的思路是：

1. 先算上一段 topk 与当前段 topk 在切换点的 overlap。
2. 如果 overlap 很低，或者 overlap 偏低且 opening 弱，则触发 guard。
3. guard 触发后，会从 `half_relay` 切回 `orig_guarded` 或 `orig_guarded_extreme`。
4. 同时配合 cooldown 降低换手。

### 4.3 低成本二次筛选

在正式结果落盘后，没有立刻重跑新回测，而是先基于 9 段已有结果做了便宜验证：

- 汇总 `orig / relay_full / relay_conservative`
- 统计各段 `overlap_ratio`
- 读取 `meta.json` 中的 `weak_opening`、`extreme_dislocation`、`guard_triggered`
- 尝试若干简化策略，判断是否存在“更窄 guard”

这里的低成本筛选只用于方向判断，不算正式样本外验证。

## 5. 2022H1-2026YTD 对比结果

| Period | Overlap | Guard | Mode | Orig Return | Relay Full Return | Conservative Return | Orig Net Ann Excess | Relay Full Net Ann Excess | Conservative Net Ann Excess |
|---|---:|---|---|---:|---:|---:|---:|---:|---:|
| 2022H1 | 25.0% | No | `half_relay` | -3.09% | -1.29% | -1.86% | 22.06% | 28.68% | 26.16% |
| 2022H2 | 32.5% | Yes | `orig_guarded` | -8.25% | -6.23% | -5.72% | 2.14% | 6.72% | 7.42% |
| 2023H1 | 15.0% | No | `half_relay` | 2.73% | 3.66% | 5.44% | 0.69% | 5.52% | 8.70% |
| 2023H2 | 32.5% | Yes | `orig_guarded` | -13.32% | -12.89% | -12.29% | -8.61% | -6.18% | -6.35% |
| 2024H1 | 7.5% | Yes | `orig_guarded_extreme` | -6.05% | -7.07% | -5.57% | 6.30% | 4.65% | 7.46% |
| 2024H2 | 47.5% | Yes | `orig_guarded` | 26.62% | 24.81% | 24.33% | 19.22% | 20.62% | 15.30% |
| 2025H1 | 5.0% | Yes | `orig_guarded_extreme` | 7.67% | 8.23% | 7.33% | 8.82% | 3.42% | 7.83% |
| 2025H2 | 7.5% | Yes | `orig_guarded_extreme` | 31.18% | 34.80% | 27.51% | 7.91% | 15.35% | 2.06% |
| 2026YTD | 12.5% | Yes | `orig_guarded_extreme` | 9.81% | 12.54% | 10.11% | -12.48% | 27.43% | -10.82% |

## 6. 聚合结论

按 9 段复合收益看：

- `orig`：`46.08%`
- `relay_full`：`59.18%`
- `relay_conservative`：`51.38%`

按平均年化超额看：

- `orig`：`5.12%`
- `relay_full`：`11.80%`
- `relay_conservative`：`6.42%`

逐段胜负关系：

- `relay_full` 有 7 段优于 `orig`
- `relay_conservative` 有 6 段优于 `orig`
- `relay_conservative` 只有 4 段优于 `relay_full`

## 7. 对当前 conservative 版本的判断

核心判断：

- 这版 conservative 不是完全没用
- 但它更像“止损器”，不是“收益增强器”
- 它能修复部分弱段，但明显拖累了多个强段的接力收益

主要帮助的区间：

- `2022H2`：`-6.23% -> -5.72%`
- `2023H2`：`-12.89% -> -12.29%`
- `2024H1`：`-7.07% -> -5.57%`

主要拖累的区间：

- `2025H2`：`34.80% -> 27.51%`
- `2026YTD`：`12.54% -> 10.11%`
- `2025H1`：`8.23% -> 7.33%`
- `2024H2`：`24.81% -> 24.33%`

因此，当前 conservative 版本的主要问题不是完全没有方向，而是 guard 触发太宽，误杀了本该保留的 `relay_full` 强段。

## 8. 低成本规则筛选的结果

基于已有 9 段结果做了一个“只在极端且弱开局时才 fallback 到 orig”的便宜筛选。

候选规则：

- 默认使用 `relay_full`
- 仅当 `extreme_dislocation && weak_opening` 时，才回退到 `orig`

这条规则在本轮 9 段上的样本内表现为：

- `current_conservative`：复合收益 `51.38%`
- `relay_full_all`：复合收益 `59.18%`
- `orig_if_extreme_and_weak`：复合收益 `60.92%`

这条窄 guard 在本轮实际上只拦了 `2024H1` 一段：

- `2024H1` 选择 `orig`
- 其余 8 段全部保留 `relay_full`

这说明：

- 现在的宽 guard 明显过度保守
- 更窄的 guard 在样本内看起来更优
- 但这个结论带有明显样本内优化色彩

## 9. 过拟合风险判断

这个“窄 guard”方向存在明显过拟合风险，原因如下：

- 规则是在看完 `2022H1-2026YTD` 结果后反推出来的
- 样本只有 9 段，数量偏少，容易被少数区间主导
- `2025H2`、`2026YTD` 等强段对整体结果影响较大

因此目前不能把窄 guard 直接当成最终正式方案，更适合作为待验证假设。

## 10. 对下一步方向的结论

本轮讨论后的方向判断是：

- 主线上建议开新方向
- 当前这条 conservative guard 线降级为低投入验证线

理由：

- `relay_full` 已经明显强于 `orig`
- 当前 `conservative` 已证明触发太宽，会误杀收益
- 继续深调这条 guard 线的边际效益可能不大
- 更值得研究的是：为什么在低 overlap 段里，`relay_full` 有时仍然有效

更合适的后续安排：

1. 主线研究新的切换依据，不再只围绕 overlap 打补丁。
2. 支线保留这条 guard 线，只做便宜验证。
3. 如果要正式保留窄 guard，必须补样本外验证。

## 11. 建议的后续验证流程

如果继续验证这条线，建议用样本外方法，而不是继续在这 9 段上来回调：

- 留一段法：每次用 8 段定规则，剩 1 段检验
- 时间前推法：只用更早年份定规则，再看后面年份是否成立

如果样本外验证不过，这条 conservative 修补线可以直接关掉；如果验证能过，再决定是否保留成兜底模块。

## 12. 本轮最终结论

一句话总结：

`relay_full` 是当前更强的主方向；现有 conservative guard 版本过度保守，虽然能修补少数弱段，但总体拖累了接力收益；窄 guard 有一定希望，但目前仅能视为样本内候选规则，下一步不应再把 guard 微调当主战场，而应转向新的切换信号方向。 
