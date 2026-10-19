# HL378 Failure-Aware Regime Router v4 交接总报告

日期：2026-05-08  
用途：新对话交接文件。下一轮直接从本报告继续，不需要重新解释上下文。

## 1. 项目目标

本轮目标不是继续堆 mode，而是把 HL378 半年度接力的差收益问题拆成：

```text
模型层问题
旧仓接续问题
策略执行放大问题
成本/换手问题
```

并实现 v4：

```text
Failure-Aware Regime Router
```

原则：

```text
先无泄露诊断 failure type；
再 shadow；
再 dry-run；
再 policy；
最后才真实 replay。
```

## 2. 核心代码文件

工作目录：

```text
C:\Users\30855\qlib\examples\benchmarks\LightGBM\semiannual_rolling_yamls_for_router
```

核心文件：

```text
failure_aware_router_v4.py
router_v4_strategy.py
generate_valid_artifacts_from_run.py
run_hl378_halfyear_relay_backtest_with_curr_only_regime_split.py
```

说明：

- `failure_aware_router_v4.py`：无泄露检查、bucket bridge、recent valid、三层诊断、action decision、router audit、planned policy。
- `router_v4_strategy.py`：真正执行层 `RouterV4TopkDropoutStrategy`。
- `generate_valid_artifacts_from_run.py`：从已有 mlruns artifact 生成 `valid_pred.pkl / valid_label.pkl`。
- `run_hl378_halfyear_relay_backtest_with_curr_only_regime_split.py`：主入口，已支持 `--router-v4-shadow`、`--router-v4-replay-dry-run`、`--router-v4-replay`、`--router-v4-replay-smoke-days`。

## 3. 阶段产物路径

研究报告同步目录：

```text
C:\Users\30855\Desktop\A\研究6
```

重要报告：

```text
C:\Users\30855\Desktop\A\研究6\failure_aware_router_v4_shadow_refined_audit_20260507.md
C:\Users\30855\Desktop\A\研究6\router_v4_thresholds_refined_shadow_20260507.yaml
C:\Users\30855\Desktop\A\研究6\failure_aware_router_v4_replay_dry_run_20260507.md
C:\Users\30855\Desktop\A\研究6\failure_aware_router_v4_policy_dry_run_20260507.md
C:\Users\30855\Desktop\A\研究6\failure_aware_router_v4_pairwise_cost_gate_20260507.md
C:\Users\30855\Desktop\A\研究6\failure_aware_router_v4_replay_full_eligible6_20260507.md
C:\Users\30855\Desktop\A\研究6\failure_aware_router_v4_strategy_smoke10_eligible6_20260507.md
C:\Users\30855\Desktop\A\研究6\failure_aware_router_v4_soft_bridge_day0_update_20260507.md
C:\Users\30855\Desktop\A\研究6\failure_aware_router_v4_strategy_full_core4_20260507.md
```

工作区完整结果目录：

```text
analysis\hl378_failure_aware_router_v4_shadow_2018H2_2026YTD_refined_full
analysis\hl378_failure_aware_router_v4_replay_dry_run_2018H2_2026YTD
analysis\hl378_failure_aware_router_v4_policy_dry_run_2018H2_2026YTD
analysis\hl378_failure_aware_router_v4_policy_dry_run_pairwise_cost_gate_2018H2_2026YTD
analysis\hl378_failure_aware_router_v4_replay_full_eligible6
analysis\hl378_failure_aware_router_v4_strategy_smoke10_eligible6
analysis\hl378_failure_aware_router_v4_strategy_full_core4
```

## 4. Shadow Refined 结论

全 16 段 refined shadow：

| failure label | action | count | periods |
| --- | --- | ---: | --- |
| `healthy_relay_keep` | `relay_keep` | 5 | 2019H1, 2021H2, 2023H1, 2025H2, 2026YTD |
| `soft_dual_weak_top_bucket` | `soft_risk_off_day0_bridge` | 4 | 2019H2, 2021H1, 2022H2, 2024H2 |
| `unknown` | `relay_keep_audit_only` | 3 | 2020H1, 2022H1, 2024H1 |
| `thin_alpha_cost_friction` | `cost_aware_takeover` | 2 | 2018H2, 2020H2 |
| `hard_curr_bucket_failure` | `hard_risk_off` | 1 | 2023H2 |
| `regime_reset_path_mismatch` | `fast_path_reset` | 1 | 2025H1 |

重要改动：

```text
2021H2 从 hard_risk_off 修正为 healthy_relay_keep；
2020H1 / 2022H1 / 2024H1 改为 unknown；
防止证据不足时硬交易。
```

## 5. Dry-Run 与 Policy 结论

`--router-v4-replay-dry-run` 已实现。

输出：

```text
action_decision_v4.json
router_audit_v4.csv
planned_position_policy_v4.csv
```

eligible replay 分布：

| effective action | eligible | count | periods |
| --- | --- | ---: | --- |
| `relay_keep_audit_only` | False | 10 | 2019H1, 2020H1, 2021H1, 2021H2, 2022H1, 2022H2, 2023H1, 2024H1, 2025H2, 2026YTD |
| `cost_aware_takeover` | True | 2 | 2018H2, 2020H2 |
| `soft_risk_off_day0_bridge` | True | 2 | 2019H2, 2024H2 |
| `fast_path_reset` | True | 1 | 2025H1 |
| `hard_risk_off` | True | 1 | 2023H2 |

## 6. Pairwise Cost Gate 结论

旧 cost gate 太宽：

```text
2018H2: 26 / 26 通过
2020H2: 23 / 23 通过
```

已改成逐笔配对：

```text
高分 curr_only -> 低分 prev_only
net_replace_score = new_score - old_score - expected_cost - boundary_noise_penalty
并设置 topk * 25% cap
```

新结果：

```text
2018H2: 10 / 26 通过
2020H2: 10 / 23 通过
```

## 7. Signal-Only Full Eligible6 结论

目录：

```text
analysis\hl378_failure_aware_router_v4_replay_full_eligible6
```

结果：

| period | action | v4 - relay |
| --- | --- | ---: |
| 2018H2 | `cost_aware_takeover` | +3.93% |
| 2019H2 | `soft_risk_off_day0_bridge` | -0.16% |
| 2020H2 | `cost_aware_takeover` | +1.83% |
| 2023H2 | `hard_risk_off` | -1.67% |
| 2024H2 | `soft_risk_off_day0_bridge` | -1.54% |
| 2025H1 | `fast_path_reset` | +1.13% |

判断：

```text
signal-only 只能验证链路，不足以表达 hard/soft 的真实低换手执行。
```

## 8. RouterV4TopkDropoutStrategy Smoke10 结论

新增真正执行层：

```text
router_v4_strategy.py
RouterV4TopkDropoutStrategy
```

目录：

```text
analysis\hl378_failure_aware_router_v4_strategy_smoke10_eligible6
```

10 日结果：

| period | action | v4 - relay | cost delta | turnover delta |
| --- | --- | ---: | ---: | ---: |
| 2018H2 | `cost_aware_takeover` | +37.96% | -2.68% | -6.54% |
| 2019H2 | `soft_risk_off_day0_bridge` | -37.51% | -1.21% | -3.36% |
| 2020H2 | `cost_aware_takeover` | +13.46% | -1.48% | -4.07% |
| 2023H2 | `hard_risk_off` | +14.06% | -1.63% | -4.47% |
| 2024H2 | `soft_risk_off_day0_bridge` | -8.01% | -1.10% | -3.06% |
| 2025H1 | `fast_path_reset` | +44.84% | -0.08% | -0.37% |

判断：

```text
cost_aware / hard_risk_off / fast_reset 有效；
soft_risk_off 明显有问题。
```

## 9. Soft Bridge 修正

`soft_risk_off_day0_bridge` 已从 5 日桥接改成 day0-only：

| day | prev_fraction | curr_fraction | n_drop | max_replace |
| --- | ---: | ---: | ---: | --- |
| day0 | 1.00 | 0.00 | 1 | low |
| day1+ | 0.00 | 1.00 | base | base |

但 qlib smoke 回测未稳定完成：

```text
2019H2 day0-only 回测超时；
2024H2 遇到数据缺失：
C:\Users\30855\.qlib\qlib_data\cn_data\features\sz300242\change.day.bin
```

因此当前结论：

```text
soft action 暂不纳入正式 core replay。
```

## 10. Strategy Full Core4 结论

目录：

```text
analysis\hl378_failure_aware_router_v4_strategy_full_core4
```

完整区间结果：

| period | action | relay ann | router v4 ann | v4 - relay | cost delta | turnover delta |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 2018H2 | `cost_aware_takeover` | 19.78% | -0.88% | -20.66% | -2.67% | -7.08% |
| 2020H2 | `cost_aware_takeover` | -5.94% | -3.31% | +2.63% | +0.63% | +1.67% |
| 2023H2 | `hard_risk_off` | -6.18% | -1.27% | +4.92% | +0.08% | +0.21% |
| 2025H1 | `fast_path_reset` | 3.42% | 9.00% | +5.58% | +0.38% | +1.01% |

核心判断：

```text
2020H2、2023H2、2025H1 三段成立；
2018H2 被强 cost-aware cap 误伤。
```

## 11. 当前最终结论

目前最稳的 v4 core set：

```text
2020H2: thin_alpha_cost_friction -> cost_aware_takeover
2023H2: hard_curr_bucket_failure -> hard_risk_off
2025H1: regime_reset_path_mismatch -> fast_path_reset
```

暂不纳入：

```text
2018H2: cost_aware 误伤，需 light/strict 分档
2019H2: soft bridge 未验证通过
2024H2: soft bridge 未验证通过且 qlib 数据缺失
```

## 12. 下一步建议

下一轮新对话建议直接从这里开始：

```text
任务 1：实现 cost_aware strict/light 分档
任务 2：2018H2 使用 light cap 或 base n_drop，重新 replay
任务 3：core3 只保留 2020H2 / 2023H2 / 2025H1，做完整复合收益汇总
任务 4：修复或绕开 2024H2 的 qlib 缺失数据 sz300242/change.day.bin
任务 5：soft_risk_off 暂停，不进入正式版本
```

推荐下一条指令：

```text
继续 v4：先实现 cost_aware strict/light 分档，并跑 2018H2 light vs strict vs relay 对比。
```

## 13. 命令参考

shadow：

```powershell
C:\Users\30855\miniconda3\envs\qlib\python.exe run_hl378_halfyear_relay_backtest_with_curr_only_regime_split.py --router-v4-shadow --cases 2018H2 2019H1 2019H2 2020H1 2020H2 2021H1 2021H2 2022H1 2022H2 2023H1 2023H2 2024H1 2024H2 2025H1 2025H2 2026YTD --out-dir analysis\hl378_failure_aware_router_v4_shadow_2018H2_2026YTD_refined_full
```

dry-run：

```powershell
C:\Users\30855\miniconda3\envs\qlib\python.exe run_hl378_halfyear_relay_backtest_with_curr_only_regime_split.py --router-v4-replay-dry-run --cases 2018H2 2019H1 2019H2 2020H1 2020H2 2021H1 2021H2 2022H1 2022H2 2023H1 2023H2 2024H1 2024H2 2025H1 2025H2 2026YTD --out-dir analysis\hl378_failure_aware_router_v4_policy_dry_run_pairwise_cost_gate_2018H2_2026YTD
```

core4 full replay：

```powershell
C:\Users\30855\miniconda3\envs\qlib\python.exe run_hl378_halfyear_relay_backtest_with_curr_only_regime_split.py --router-v4-replay --cases 2018H2 2020H2 2023H2 2025H1 --out-dir analysis\hl378_failure_aware_router_v4_strategy_full_core4
```

## 14. 2026-05-08 对话续跑进展补充

本轮已完成以下三件事：

```text
1. 将 cost_aware strict/light 分档做成正式参数开关
2. 完成 2018H2 strict vs light vs relay 对比 replay
3. 完成 core3（2020H2 / 2023H2 / 2025H1）完整策略版 replay 与复合收益汇总
```

### 14.1 cost_aware strict/light 已实现

代码已更新：

```text
failure_aware_router_v4.py
run_hl378_halfyear_relay_backtest_with_curr_only_regime_split.py
```

新增参数：

```text
--router-v4-cost-aware-cap-mode {auto,strict,light}
```

说明：

```text
auto: 保持旧行为，2018H2 -> light，其余 cost_aware 段 -> strict
strict: replacement_cap_ratio = 0.25
light: replacement_cap_ratio = 0.50
```

### 14.2 2018H2 strict vs light replay 结论

结果目录：

```text
analysis\hl378_failure_aware_router_v4_strategy_2018H2_strict
analysis\hl378_failure_aware_router_v4_strategy_2018H2_light
```

对比结果：

| mode | relay ann | router ann | v4 - relay | passed cost gate |
| --- | ---: | ---: | ---: | ---: |
| `strict` | 19.78% | -0.88% | -20.66% | 10 / 26 |
| `light` | 19.78% | +1.91% | -17.87% | 20 / 26 |

判断：

```text
light 比 strict 明显改善，但 2018H2 仍显著落后于 relay；
因此 2018H2 的问题不只是 10 笔 cap 太紧，而是当前 cost_aware_takeover 本身不适合该段。
```

进一步结论：

```text
2018H2 更像健康高换手段被自动执行约束误伤；
它不是“是否进入 replay”被误伤，
而是“进入 replay 后套用了过强的 cost_aware 自动执行规则”被误伤。
```

因此：

```text
2018H2 暂不纳入正式版本；
cost_aware strict/light 保留为研究开关。
```

### 14.3 core3 full replay 已完成

正式 core set 已收敛为：

```text
2020H2: thin_alpha_cost_friction -> cost_aware_takeover
2023H2: hard_curr_bucket_failure -> hard_risk_off
2025H1: regime_reset_path_mismatch -> fast_path_reset
```

结果目录：

```text
analysis\hl378_failure_aware_router_v4_strategy_full_core3
```

逐段结果：

| period | action | relay ann | router v4 ann | v4 - relay |
| --- | --- | ---: | ---: | ---: |
| 2020H2 | `cost_aware_takeover` | -5.94% | -3.31% | +2.63% |
| 2023H2 | `hard_risk_off` | -6.18% | -1.27% | +4.92% |
| 2025H1 | `fast_path_reset` | +3.42% | +9.00% | +5.58% |

汇总：

```text
3 / 3 段全部为正；
平均 v4 - relay 年化 = +4.38%
```

### 14.4 core3 复合收益结论

复合口径：

```text
直接拼接 2020H2 / 2023H2 / 2025H1 三段 eval 区间日收益，按日复利计算
```

复合结果：

| variant | days | net ann excess | max drawdown | compounded net excess |
| --- | ---: | ---: | ---: | ---: |
| `relay_full` | 367 | -3.04% | -11.05% | -4.75% |
| `router_v4_replay` | 367 | +1.30% | -7.08% | +1.55% |

核心差值：

```text
composite v4 - relay 年化 = +4.34%
alpha_nav_ratio - 1 = +6.61%
最大回撤改善：-11.05% -> -7.08%
```

与 core4 对比：

```text
core4 因 2018H2 被拖累，复合相对表现仍为负；
core3 去掉 2018H2 后，复合 alpha 转正。
```

### 14.5 当前机制说明：手动纳入 replay，纳入后自动执行

这一点在本轮对话中已明确：

```text
1. 诊断层是自动的：每段自动给出 failure label / action family
2. 是否纳入正式 replay：当前仍是研究结论驱动的手动收口，不是全自动正式放行
3. 一旦某段被纳入 replay：后续执行是自动的，由
   action_decision_v4 / router_audit_v4 / planned_position_policy_v4
   自动决定具体执行
```

因此当前正式版本的真实含义是：

```text
2020H2 / 2023H2 / 2025H1 -> 使用 v4 action 自动执行
其它年份 -> 维持原版 relay
```

### 14.6 更新后的当前最终结论

```text
正式 core set 先冻结为 core3：2020H2 + 2023H2 + 2025H1
2018H2 暂不纳入正式版本
soft_risk_off 相关段继续暂停，不进入正式版本
其余 healthy_relay_keep / unknown 段维持原版 relay
```

### 14.7 新的建议下一步

```text
任务 1：若要正式化，增加“自动 fallback 到 relay”的正式 gating 机制
任务 2：将正式版白名单/放行集合显式写入配置，避免 core3 只存在于研究口径
任务 3：2018H2 后续若继续研究，方向应改为 healthy-high-turnover 识别，而不是继续强化当前 cost_aware
任务 4：soft_risk_off 继续暂停，待 2019H2 / 2024H2 数据与稳定性问题解决后再重开
```
核心不是一个单独叫“core3 自动选策略”的脚本，而是这三处一起完成的。

最关键的是 failure_aware_router_v4.py：


build_action_decision_v4 (line 461)

这里把诊断结果映射成 effective_action_family

映射到的动作包括：

cost_aware_takeover 514 (line 514)

hard_risk_off 506 (line 506)

fast_path_reset 523 (line 523)





调度这套逻辑的是 run_hl378_halfyear_relay_backtest_with_curr_only_regime_split.py：


run_case (line 917)

在这里依次调用：

build_action_decision_v4 (line 1008)

build_router_audit_v4 (line 1019)

build_planned_position_policy_v4 (line 1032)





真正执行策略的是 router_v4_strategy.py：


RouterV4TopkDropoutStrategy (line 19)

generate_target_weight_position (line 93)


一句话总结：


“问题 -> 选哪个策略” 看 failure_aware_router_v4.py

“整段回测怎么串起来” 看 run_hl378_halfyear_relay_backtest_with_curr_only_regime_split.py

“选完策略后怎么执行持仓” 看 router_v4_strategy.py
## 15. 2026-05-08 auto_core3 自动选择与 replay 结果补充

本轮在补完 `used_features` 的 no-leakage assert 后，已完成：

```text
1. auto_core3 自动 gate 全 16 段判定
2. auto_core3 全样本 replay（2018H2~2026YTD）
3. 验证 auto_core3 是否自动复现人工 core3
```

### 15.1 auto_core3 规则

当前自动放行框架：

```text
hard_curr_bucket_failure -> 自动放行 -> hard_risk_off
regime_reset_path_mismatch -> 自动放行 -> fast_path_reset
thin_alpha_cost_friction -> 必须先过 cost_aware_auto_gate_v1
soft_dual_weak_top_bucket / unknown / healthy_relay_keep -> fallback relay
```

其中 `cost_aware_auto_gate_v1` 为二段式：

基础资格：

```text
primary_failure == thin_alpha_cost_friction
confidence >= medium
expected_turnover >= 0.55
expected_cost_proxy >= 0.0016
0.30 <= overlap_top40 <= 0.55
```

健康强势 veto：

```text
curr_top40_top80_gap > 0.12
OR curr_top10_top40_gap > 0.12
OR curr_score_std > 0.10
OR curr_vs_universe_score_gap > 0.25
```

### 15.2 自动 gate 分布结果

结果目录：

```text
analysis\hl378_failure_aware_router_v4_auto_core3_gate_2018H2_2026YTD
analysis\hl378_failure_aware_router_v4_auto_core3_replay_2018H2_2026YTD
```

自动 gate 分布：

| auto_replay_allowed | auto_replay_action | fallback_reason | case_count | cases |
| --- | --- | --- | ---: | --- |
| `False` | `cost_aware_takeover` | `healthy_strength_veto` | 1 | `2018H2` |
| `False` | `relay_keep` | `non_core_action_family` | 9 | `2019H1, 2019H2, 2021H1, 2021H2, 2022H2, 2023H1, 2024H2, 2025H2, 2026YTD` |
| `False` | `relay_keep_audit_only` | `non_core_action_family` | 3 | `2020H1, 2022H1, 2024H1` |
| `True` | `cost_aware_takeover` |  | 1 | `2020H2` |
| `True` | `hard_risk_off` |  | 1 | `2023H2` |
| `True` | `fast_path_reset` |  | 1 | `2025H1` |

判断：

```text
auto_core3 已自动复现人工 core3：
2020H2 / 2023H2 / 2025H1 放行；
2018H2 被 healthy_strength_veto 挡回 relay；
其它年份全部 fallback relay。
```

### 15.3 关键案例核对

| case | primary_failure | effective_action_family | eligible_for_replay | auto_replay_allowed | fallback_reason |
| --- | --- | --- | ---: | ---: | --- |
| `2018H2` | `thin_alpha_cost_friction` | `relay_keep_audit_only` | False | False | `healthy_strength_veto` |
| `2020H2` | `thin_alpha_cost_friction` | `cost_aware_takeover` | True | True |  |
| `2023H2` | `hard_curr_bucket_failure` | `hard_risk_off` | True | True |  |
| `2025H1` | `regime_reset_path_mismatch` | `fast_path_reset` | True | True |  |

### 15.4 auto_core3 replay 关键结果

放行三段 replay 结果与人工 core3 一致：

| case | action | relay ann | router ann | v4 - relay |
| --- | --- | ---: | ---: | ---: |
| `2020H2` | `cost_aware_takeover` | -5.94% | -3.31% | +2.63% |
| `2023H2` | `hard_risk_off` | -6.18% | -1.27% | +4.92% |
| `2025H1` | `fast_path_reset` | +3.42% | +9.00% | +5.58% |

### 15.5 no-leakage 加固

本轮已增加硬断言：

```text
assert_diagnosis_used_features_no_leakage(...)
```

作用：

```text
1. 禁止 used_features 使用 POST_AUDIT_ONLY
2. 禁止 used_features 使用 EARLY_CONFIRM_ONLY
3. domain 必须为 PRE_SWITCH_ALLOWED
4. 若存在 available_time，则必须 <= decision_time
5. 回测后收益汇总字段不得进入 action decision
```

因此当前 auto_core3 是在更严格的防泄露约束下运行的。

### 15.6 更新后的最终结论

```text
auto_core3 已可以替代人工 core3 作为正式自动选择机制；
2018H2 被稳定挡回 relay；
2020H2 / 2023H2 / 2025H1 被稳定放行；
其余年份维持原版 relay。
```

### 15.7 新的下一步建议

```text
任务 1：整理 auto_core3 完整复合收益汇总（与人工 core3 / core4 并排比较）
任务 2：若需要正式交付，将 auto_core3 设为默认正式模式
任务 3：soft_risk_off 继续暂停，待数据与稳定性问题解决后再重新纳入自动放行讨论
```

### 15.8 auto_core3 / relay 自动选择相关脚本与产物完整路径

本轮“自动在 core3 与原版 relay 之间选择，以及进入 core3 后自动选择三种策略”的关键文件路径如下。

脚本文件：

```text
C:\Users\30855\qlib\examples\benchmarks\LightGBM\semiannual_rolling_yamls_for_router\failure_aware_router_v4.py
C:\Users\30855\qlib\examples\benchmarks\LightGBM\semiannual_rolling_yamls_for_router\run_hl378_halfyear_relay_backtest_with_curr_only_regime_split.py
C:\Users\30855\qlib\examples\benchmarks\LightGBM\semiannual_rolling_yamls_for_router\router_v4_strategy.py
```

各文件职责：

```text
failure_aware_router_v4.py
- build_action_decision_v4(...)
- evaluate_cost_aware_auto_gate_v1(...)
- assert_diagnosis_used_features_no_leakage(...)
- 问题 -> action family -> 是否放行 replay 的核心决策逻辑

run_hl378_halfyear_relay_backtest_with_curr_only_regime_split.py
- 主入口脚本
- --router-v4-replay-selection {all, core3, auto_core3}
- 串联 diagnosis / action_decision / router_audit / planned_policy / replay
- 输出 auto_core3_gate_decision.csv / auto_core3_gate_distribution.csv / summary_all.csv

router_v4_strategy.py
- RouterV4TopkDropoutStrategy
- 真正执行 cost_aware_takeover / hard_risk_off / fast_path_reset 的持仓层
```

自动 gate 判定目录：

```text
C:\Users\30855\qlib\examples\benchmarks\LightGBM\semiannual_rolling_yamls_for_router\analysis\hl378_failure_aware_router_v4_auto_core3_gate_2018H2_2026YTD
```

该目录下关键文件：

```text
C:\Users\30855\qlib\examples\benchmarks\LightGBM\semiannual_rolling_yamls_for_router\analysis\hl378_failure_aware_router_v4_auto_core3_gate_2018H2_2026YTD\auto_core3_gate_decision.csv
C:\Users\30855\qlib\examples\benchmarks\LightGBM\semiannual_rolling_yamls_for_router\analysis\hl378_failure_aware_router_v4_auto_core3_gate_2018H2_2026YTD\auto_core3_gate_distribution.csv
C:\Users\30855\qlib\examples\benchmarks\LightGBM\semiannual_rolling_yamls_for_router\analysis\hl378_failure_aware_router_v4_auto_core3_gate_2018H2_2026YTD\summary_all.csv
```

auto_core3 全样本 replay 目录：

```text
C:\Users\30855\qlib\examples\benchmarks\LightGBM\semiannual_rolling_yamls_for_router\analysis\hl378_failure_aware_router_v4_auto_core3_replay_2018H2_2026YTD
```

该目录下关键文件：

```text
C:\Users\30855\qlib\examples\benchmarks\LightGBM\semiannual_rolling_yamls_for_router\analysis\hl378_failure_aware_router_v4_auto_core3_replay_2018H2_2026YTD\auto_core3_gate_decision.csv
C:\Users\30855\qlib\examples\benchmarks\LightGBM\semiannual_rolling_yamls_for_router\analysis\hl378_failure_aware_router_v4_auto_core3_replay_2018H2_2026YTD\auto_core3_gate_distribution.csv
C:\Users\30855\qlib\examples\benchmarks\LightGBM\semiannual_rolling_yamls_for_router\analysis\hl378_failure_aware_router_v4_auto_core3_replay_2018H2_2026YTD\summary_all.csv
```

本轮新增汇总报告：

```text
C:\Users\30855\qlib\examples\benchmarks\LightGBM\semiannual_rolling_yamls_for_router\analysis\failure_aware_router_v4_auto_core3_replay_2018H2_2026YTD_20260508.md
```

说明：

```text
如果后续要继续检查“自动选 core3 / 原版 relay”的逻辑，优先看：
1. failure_aware_router_v4.py
2. run_hl378_halfyear_relay_backtest_with_curr_only_regime_split.py
3. auto_core3_gate_decision.csv
4. auto_core3_gate_distribution.csv
```

### 15.9 前面实验报告路径补齐与“三种模式脚本”说明

本轮复查后补充说明：

```text
“core3 自动切换的三种模式”不是三个独立脚本；
而是同一个主入口脚本 + 同一个决策脚本 + 同一个执行脚本内的三种 action 路径。
```

也就是说，后续如果要查：

```text
cost_aware_takeover
hard_risk_off
fast_path_reset
```

不要去找三个不同的 .py 文件；它们都属于同一套 router v4 代码链路：

```text
主入口：run_hl378_halfyear_relay_backtest_with_curr_only_regime_split.py
决策：failure_aware_router_v4.py
执行：router_v4_strategy.py
```

三种模式对应位置：

```text
C:\Users\30855\qlib\examples\benchmarks\LightGBM\semiannual_rolling_yamls_for_router\failure_aware_router_v4.py
- build_action_decision_v4(...)
- evaluate_cost_aware_auto_gate_v1(...)
- build_router_audit_v4(...)
- build_planned_position_policy_v4(...)

C:\Users\30855\qlib\examples\benchmarks\LightGBM\semiannual_rolling_yamls_for_router\router_v4_strategy.py
- RouterV4TopkDropoutStrategy
```

其中：

```text
cost_aware_takeover
-> 由 build_action_decision_v4(...) + evaluate_cost_aware_auto_gate_v1(...) 决定是否放行

hard_risk_off
-> 由 build_action_decision_v4(...) 自动放行为 hard_risk_off

fast_path_reset
-> 由 build_action_decision_v4(...) 自动放行为 fast_path_reset
```

前面实验新增报告路径补齐如下：

```text
C:\Users\30855\qlib\examples\benchmarks\LightGBM\semiannual_rolling_yamls_for_router\analysis\failure_aware_router_v4_cost_aware_cap_mode_compare_2018H2_20260508.md
C:\Users\30855\qlib\examples\benchmarks\LightGBM\semiannual_rolling_yamls_for_router\analysis\failure_aware_router_v4_strategy_full_core3_20260508.md
C:\Users\30855\qlib\examples\benchmarks\LightGBM\semiannual_rolling_yamls_for_router\analysis\failure_aware_router_v4_auto_core3_replay_2018H2_2026YTD_20260508.md
```

对应实验目录补齐如下：

```text
C:\Users\30855\qlib\examples\benchmarks\LightGBM\semiannual_rolling_yamls_for_router\analysis\hl378_failure_aware_router_v4_strategy_2018H2_strict
C:\Users\30855\qlib\examples\benchmarks\LightGBM\semiannual_rolling_yamls_for_router\analysis\hl378_failure_aware_router_v4_strategy_2018H2_light
C:\Users\30855\qlib\examples\benchmarks\LightGBM\semiannual_rolling_yamls_for_router\analysis\hl378_failure_aware_router_v4_strategy_full_core3
C:\Users\30855\qlib\examples\benchmarks\LightGBM\semiannual_rolling_yamls_for_router\analysis\hl378_failure_aware_router_v4_auto_core3_gate_2018H2_2026YTD
C:\Users\30855\qlib\examples\benchmarks\LightGBM\semiannual_rolling_yamls_for_router\analysis\hl378_failure_aware_router_v4_auto_core3_replay_2018H2_2026YTD
```

复查结论：

```text
前面实验路径现在已经补齐到：
1. 核心脚本
2. 关键函数/模式归属
3. 人工 core3 报告
4. 2018H2 strict/light 对比报告
5. auto_core3 gate / replay 报告与目录
```

## 16. 2026-05-08 新增故障：模型严重失效（full_exit_no_reentry）

本轮新增一个更高等级的故障诊断，用来处理 `2019H2` 这类问题：

```text
模型严重失效
= 不再做 soft bridge / 不再保留 relay 持仓
= 直接清仓
= 后续该段维持空仓
= 不再换仓
```

### 16.1 新增标签与动作

新增故障标签：

```text
model_severe_failure
```

新增动作族：

```text
full_exit_no_reentry
```

含义：

```text
切换点后直接退出持仓；
全年/该段后续不再开新仓；
策略层返回空仓，不再换仓。
```

### 16.2 当前触发条件

本轮先用最直接的一版诊断条件：

```text
recent_valid_ic <= -0.005
AND overlap_ratio >= 0.45
```

满足后在故障诊断层直接判为：

```text
primary_failure = model_severe_failure
action_family = full_exit_no_reentry
```

说明：

```text
这类段不再视为 soft risk-off；
而是视为“模型严重失效，继续接力或桥接都没有意义”，
因此直接退出到现金。
```

### 16.3 代码落点

相关脚本路径：

```text
C:\Users\30855\qlib\examples\benchmarks\LightGBM\semiannual_rolling_yamls_for_router\failure_aware_router_v4.py
C:\Users\30855\qlib\examples\benchmarks\LightGBM\semiannual_rolling_yamls_for_router\router_v4_strategy.py
C:\Users\30855\qlib\examples\benchmarks\LightGBM\semiannual_rolling_yamls_for_router\run_hl378_halfyear_relay_backtest_with_curr_only_regime_split.py
```

职责：

```text
failure_aware_router_v4.py
- 诊断层新增 primary_failure = model_severe_failure
- 动作层新增 action_family = full_exit_no_reentry
- planned policy 新增 liquidate_all_hold_cash_no_reentry

router_v4_strategy.py
- 遇到 full_exit_no_reentry 时直接返回 {}
- 即空仓，不再持有，不再买入

run_hl378_halfyear_relay_backtest_with_curr_only_regime_split.py
- replay 信号链路兼容 full_exit_no_reentry
```

### 16.4 验证结果

验证目录：

```text
C:\Users\30855\qlib\examples\benchmarks\LightGBM\semiannual_rolling_yamls_for_router\analysis\hl378_failure_aware_router_v4_severe_failure_2019H2_dryrun
C:\Users\30855\qlib\examples\benchmarks\LightGBM\semiannual_rolling_yamls_for_router\analysis\hl378_failure_aware_router_v4_severe_failure_2019H2_smoke10
```

验证结论：

```text
2019H2 在 dry-run 中已被诊断为：
primary_failure = model_severe_failure
effective_action_family = full_exit_no_reentry

smoke10 replay 已验证：
执行层确实进入 full_exit_no_reentry 路径，
策略层返回空仓。
```

### 16.5 与 soft_risk_off 的关系

本轮调整后：

```text
高置信度、且满足 severe 条件的原 soft 问题段
-> 升级为 model_severe_failure
-> 不再走 soft_risk_off_day0_bridge

其余低置信度 soft 段
-> 仍保留在 soft_dual_weak_top_bucket / soft_risk_off_day0_bridge 体系内
-> 但正式版本当前仍不放行
```

### 16.6 防泄露说明

该诊断仍受当前 no-leakage 约束：

```text
1. recent_valid_ic 来自带 embargo 的 recent valid 诊断
2. overlap_ratio 为切换时点结构特征
3. build_action_decision_v4(...) 前已有 assert_diagnosis_used_features_no_leakage(...)
4. 不允许 POST_AUDIT_ONLY / EARLY_CONFIRM_ONLY / 回测后收益字段进入决策
```

因此本轮“模型严重失效 -> 清仓空过”的诊断，当前口径下未见直接未来收益泄露。

### 16.7 当前意义

```text
这条新诊断主要是为了解决 2019H2 这类：
不是 cost-aware、不是 hard_risk_off、也不适合 soft bridge，
而是应该直接退出市场、空过去的问题。
```

### 16.8 口径修正：soft_dual_weak_top_bucket 冻结 + severe gate 收窄
2026-05-08 本轮后续实验已将第 16 节前面那版“severe 扫描”进一步收敛，当前应以这版为准：

```text
1. soft_dual_weak_top_bucket 暂时冻结
2. 原本落到 soft_dual_weak_top_bucket / soft_risk_off_day0_bridge 的段
   先统一回退到 unknown / relay_keep_audit_only
3. model_severe_failure 保持窄口径，只保留真正极端段
4. severe gate 当前以 recent_valid_ic <= -0.005 且 overlap_ratio >= 0.50 为准
   不再采用更宽的 0.45 口径
```

这样做的直接原因：

```text
用户明确要求不要误伤 2024H2。
实测表明，如果 severe gate 放宽到 overlap_ratio >= 0.45，
2024H2 会和 2019H2 一起被升级为 model_severe_failure。
因此当前正式研究口径改为：
- severe 只保留 2019H2
- soft_dual_weak_top_bucket 先冻结，不进入正式 replay 集合
```

对应代码修正位置：
```text
C:\Users\30855\qlib\examples\benchmarks\LightGBM\semiannual_rolling_yamls_for_router\failure_aware_router_v4.py
- severe gate 注释已明确收窄口径，避免 2024H2 类边界段被升级
- curr_quality_level == weak 分支已改为 unknown / relay_keep_audit_only
```

### 16.9 冻结版 shadow 全量 16 段重扫
实验目录：
```text
C:\Users\30855\qlib\examples\benchmarks\LightGBM\semiannual_rolling_yamls_for_router\analysis\hl378_failure_aware_router_v4_soft_frozen_shadow_2018H2_2026YTD
```

关键汇总文件：
```text
C:\Users\30855\qlib\examples\benchmarks\LightGBM\semiannual_rolling_yamls_for_router\analysis\hl378_failure_aware_router_v4_soft_frozen_shadow_2018H2_2026YTD\summary_all.csv
```

16 段冻结版 shadow 分布：

| primary_failure | count | periods |
| --- | ---: | --- |
| `unknown` | 6 | 2020H1, 2021H1, 2022H1, 2022H2, 2024H1, 2024H2 |
| `healthy_relay_keep` | 5 | 2019H1, 2021H2, 2023H1, 2025H2, 2026YTD |
| `thin_alpha_cost_friction` | 2 | 2018H2, 2020H2 |
| `regime_reset_path_mismatch` | 1 | 2025H1 |
| `hard_curr_bucket_failure` | 1 | 2023H2 |
| `model_severe_failure` | 1 | 2019H2 |

对应动作分布：

| effective_action_family | count | periods |
| --- | ---: | --- |
| `relay_keep_audit_only` | 6 | 2020H1, 2021H1, 2022H1, 2022H2, 2024H1, 2024H2 |
| `relay_keep` | 5 | 2019H1, 2021H2, 2023H1, 2025H2, 2026YTD |
| `cost_aware_takeover` | 2 | 2018H2, 2020H2 |
| `fast_path_reset` | 1 | 2025H1 |
| `hard_risk_off` | 1 | 2023H2 |
| `full_exit_no_reentry` | 1 | 2019H2 |

关键结论：
```text
1. model_severe_failure 现在只剩 2019H2 一段
2. 2024H2 已经不再被 severe 误伤
3. 2021H1 / 2022H2 这两个原 soft 段也已退回 audit-only
4. soft_dual_weak_top_bucket 当前不再进入正式动作集合
```

可以明确点名的 4 段验证结果：
```text
2019H2 -> model_severe_failure / full_exit_no_reentry
2021H1 -> unknown / relay_keep_audit_only
2022H2 -> unknown / relay_keep_audit_only
2024H2 -> unknown / relay_keep_audit_only
```

### 16.10 冻结版 policy dry-run：downstream replay eligible 集合清洗
实验目录：
```text
C:\Users\30855\qlib\examples\benchmarks\LightGBM\semiannual_rolling_yamls_for_router\analysis\hl378_failure_aware_router_v4_policy_dry_run_soft_frozen_2018H2_2026YTD
```

关键汇总文件：
```text
C:\Users\30855\qlib\examples\benchmarks\LightGBM\semiannual_rolling_yamls_for_router\analysis\hl378_failure_aware_router_v4_policy_dry_run_soft_frozen_2018H2_2026YTD\summary_all.csv
```

冻结版 dry-run 后的 eligible replay 集合：

| period | primary_failure | effective_action_family |
| --- | --- | --- |
| 2018H2 | `thin_alpha_cost_friction` | `cost_aware_takeover` |
| 2019H2 | `model_severe_failure` | `full_exit_no_reentry` |
| 2020H2 | `thin_alpha_cost_friction` | `cost_aware_takeover` |
| 2023H2 | `hard_curr_bucket_failure` | `hard_risk_off` |
| 2025H1 | `regime_reset_path_mismatch` | `fast_path_reset` |

非 eligible 段的统一状态：
```text
其余 11 段全部为：eligible_for_replay = False
且 effective_action_family = relay_keep_audit_only
```

重点说明：
```text
2021H1 / 2022H2 / 2024H2 这些原 soft 段已经不再混入 downstream replay eligible 集合。
这说明“冻结 soft + 收窄 severe”不仅改变了 shadow 诊断，
也已经把 dry-run 下游的 replay 候选集同步清洗干净。
```

### 16.11 本轮阶段性最终结论（截至 2026-05-08）
当前冻结版口径下，正式值得继续推进 replay 的候选段为：

```text
2018H2 -> cost_aware_takeover
2019H2 -> full_exit_no_reentry
2020H2 -> cost_aware_takeover
2023H2 -> hard_risk_off
2025H1 -> fast_path_reset
```

当前不进入正式 replay 候选的段：
```text
2019H1, 2020H1, 2021H1, 2021H2, 2022H1, 2022H2, 2023H1, 2024H1, 2024H2, 2025H2, 2026YTD
```

其中本轮最重要的新结论是：
```text
1. 2019H2 severe full exit 现已被单独隔离出来
2. 2024H2 不再被 severe 误伤
3. soft_dual_weak_top_bucket 暂时冻结，不进入正式 replay 体系
4. downstream replay eligible 集合已从旧的 soft 命中集合收敛为 5 段
```

建议后续直接从这 5 段出发做真实 replay，尤其重点验证：
```text
2019H2 的 full_exit_no_reentry 是否应该进入正式 core
```
