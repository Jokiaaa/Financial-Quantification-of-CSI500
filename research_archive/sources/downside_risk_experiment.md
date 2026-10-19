# 研究7：LightGBM 下行风险模型与二阶段筛选实验总记录

## 1. 实验目标
- 使用 LightGBM 构建“未来 20 个交易日 open-to-open 下行风险”预测模型。
- 将原版收益模型 pred.pkl 与下行风险模型 pred.pkl 结合，做二阶段选股。
- 重点测试 rerank_pool80_keep10：先按收益模型取前 80，固定保留前 10，再用风险模型重排剩余 30，最终持有 40。

## 2. 关键代码与配置文件路径
- 工作目录：C:\Users\30855\qlib\examples\benchmarks\LightGBM\semiannual_rolling_yamls_for_router
- 风险模型核心配置示例：C:\Users\30855\qlib\examples\benchmarks\LightGBM\semiannual_rolling_yamls_for_router\hl378_mw2e4_2026YTD_T40_D2_label_open_open_downside_risk.yaml
- 2018-2020 风险 YAML 生成脚本：C:\Users\30855\qlib\examples\benchmarks\LightGBM\semiannual_rolling_yamls_for_router\generate_downside_risk_yamls_2018_2020.py
- 2021-2022 风险 YAML 生成脚本：C:\Users\30855\qlib\examples\benchmarks\LightGBM\semiannual_rolling_yamls_for_router\generate_downside_risk_yamls_2021_2022.py
- 2023 风险 YAML 生成脚本：C:\Users\30855\qlib\examples\benchmarks\LightGBM\semiannual_rolling_yamls_for_router\generate_downside_risk_yamls_2023.py
- 2024-2025 风险 YAML 生成脚本：C:\Users\30855\qlib\examples\benchmarks\LightGBM\semiannual_rolling_yamls_for_router\generate_downside_risk_yamls_2024_2025.py
- 二阶段回测脚本：C:\Users\30855\qlib\examples\benchmarks\LightGBM\semiannual_rolling_yamls_for_router\run_baseline_downside_rerank_backtest.py
- 自定义特征处理器：C:\Users\30855\qlib\examples\benchmarks\LightGBM\semiannual_rolling_yamls_for_router\alpha158_label20_plus_confirm_handler.py
- 泄露审计脚本：C:\Users\30855\qlib\examples\benchmarks\LightGBM\semiannual_rolling_yamls_for_router\audit_open_capacity_risk.py

## 3. 风险模型标签定义
- 下行风险标签使用未来 20 日 open-to-open 收益的 downside 部分：
- ((Ref($open, -21) / Ref($open, -1) - 1) - Abs(Ref($open, -21) / Ref($open, -1) - 1)) / 2
- 含义：只惩罚未来下跌，不惩罚未来上涨。

## 4. 数据配对表路径
- 2018H1-2021H2：C:\Users\30855\qlib\examples\benchmarks\LightGBM\semiannual_rolling_yamls_for_router\analysis\baseline_downside_pred_pairs_2018H1_2021H2.csv
- 2021H1-2022H2：C:\Users\30855\qlib\examples\benchmarks\LightGBM\semiannual_rolling_yamls_for_router\analysis\baseline_downside_pred_pairs_2021H1_2022H2.csv
- 2023H1-2023H2：C:\Users\30855\qlib\examples\benchmarks\LightGBM\semiannual_rolling_yamls_for_router\analysis\baseline_downside_pred_pairs_2023H1_2023H2.csv
- 2024H1-2026YTD：C:\Users\30855\qlib\examples\benchmarks\LightGBM\semiannual_rolling_yamls_for_router\analysis\baseline_downside_pred_pairs_2024H1_2026YTD.csv

## 5. 二阶段回测结果文件路径
- 2018H1-2020H2 汇总：C:\Users\30855\qlib\examples\benchmarks\LightGBM\semiannual_rolling_yamls_for_router\analysis\baseline_downside_rerank_backtest\summary.csv
- 2018H1-2020H2 变体聚合：C:\Users\30855\qlib\examples\benchmarks\LightGBM\semiannual_rolling_yamls_for_router\analysis\baseline_downside_rerank_backtest\aggregate_by_variant.csv
- 2021H1-2022H2 汇总：C:\Users\30855\qlib\examples\benchmarks\LightGBM\semiannual_rolling_yamls_for_router\analysis\baseline_downside_rerank_backtest_2021_2022_keep10\summary.csv
- 2024H1-2026YTD 汇总：C:\Users\30855\qlib\examples\benchmarks\LightGBM\semiannual_rolling_yamls_for_router\analysis\baseline_downside_rerank_backtest_2024_2026_keep10\summary.csv
- 2024H1-2026YTD 逐期明细目录：C:\Users\30855\qlib\examples\benchmarks\LightGBM\semiannual_rolling_yamls_for_router\analysis\baseline_downside_rerank_backtest_2024_2026_keep10

## 6. 2023 风险模型结果
- 2023H1 downside run id：06a4f2aa5b8e4b9782979e5b590f2d99
- 2023H2 downside run id：684f87ea41d84da6ae81e85b6b51ae25
- 2023H1 pred.pkl：C:\Users\30855\qlib\examples\benchmarks\LightGBM\semiannual_rolling_yamls_for_router\mlruns\376065131763570804\06a4f2aa5b8e4b9782979e5b590f2d99\artifacts\pred.pkl
- 2023H2 pred.pkl：C:\Users\30855\qlib\examples\benchmarks\LightGBM\semiannual_rolling_yamls_for_router\mlruns\376065131763570804\684f87ea41d84da6ae81e85b6b51ae25\artifacts\pred.pkl
- 2023H1 风险模型单独回测：年化超额约 12.35%，IR 约 1.4115，最大回撤约 -5.37%
- 2023H2 风险模型单独回测：年化超额约 9.59%，IR 约 0.9630，最大回撤约 -5.07%
- 备注：2023 只重新训练并记录了风险模型与 pred 配对，未继续跑 rerank_pool80_keep10 组合回测。

## 7. 2018H1-2020H2 二阶段回测结论
- 最优平均变体是 rerank_pool80_keep10。
- baseline 平均年化超额：0.086899
- rerank_pool80_keep10 平均年化超额：0.099087
- baseline 平均 IR：1.053715
- rerank_pool80_keep10 平均 IR：1.318351
- 平均回撤基本持平，略差。

### 2018H2 特别说明
- 2018H2 baseline 已经很强，年化超额约 32.53%，IR 约 3.681。
- rerank_pool80_keep10 年化超额约 26.74%，没有超过 baseline。
- 结论：2018H2 属于收益模型本身已足够强，风险重排是过度干预。

### 2020H2 特别说明
- 2020H2 baseline 年化超额约 -0.42%，rerank_pool80_keep10 约 -0.94%。
- 结论：风险重排未能改善该阶段。

## 8. 2021H1-2022H2 rerank_pool80_keep10 结果
- 2021H1：baseline 8.88%，rerank 8.66%，IR 从 0.7588 降到 0.6416
- 2021H2：baseline 16.81%，rerank 23.995%，IR 从 1.3677 升到 1.9795
- 2022H1：baseline 15.76%，rerank 20.834%，IR 从 1.9578 升到 2.8252
- 2022H2：baseline 8.60%，rerank 8.40%，基本持平略差
- 结论：2021H2、2022H1 明显受益；2021H1、2022H2 没有明显改善。

## 9. 2024H1-2026YTD rerank_pool80_keep10 结果
- 2024H1：baseline 5.40%，rerank 16.06%，改善明显
- 2024H2：baseline 29.50%，rerank 1.46%，大幅变差
- 2025H1：baseline 14.21%，rerank 2.98%，明显变差
- 2025H2：baseline 9.52%，rerank 3.90%，变差
- 2026YTD：baseline -12.48%，rerank -19.23%，进一步变差

### 对 2024H2-2026YTD 收益变差的解释
- 不是回测跑错，而是风险重排确实把原版收益信号压坏了。
- 2024H2-2025H2 中，baseline 本身已经很强，尤其 2024H2 baseline IR 达到 2.585。
- rerank_pool80_keep10 只保留前 10 名，剩下 30 个名额大量交给风险模型重排，导致很多高收益候选被换掉。
- 汇总表显示 kept_head_share 约 0.40-0.43，reranked_tail_share 约 0.57-0.60，说明组合里超过一半仓位都被风险模型改票。
- avg_selected_base_rank 在 34-37 左右，说明最终入选股票平均已落到 baseline top80 的中后段。
- 2026YTD 是双重问题：baseline 本身已经失效，风险模型也没有救回来。

## 10. 未来信息泄露判断
- 未发现明显的训练集/测试集穿越问题。
- 主要风险在于时点泄露：回测使用 deal_price: open，但特征里可能包含同日 high/low/close/volume/vwap 等日内已知后验信息。
- 如果 pred.pkl 是用 T-1 收盘后冻结数据生成，再在 T 开盘交易，则可认为没有未来信息泄露。
- 如果 pred.pkl 是用 T 当天完整日频特征生成，再在 T 开盘成交，则存在未来信息泄露。
- 稳妥修法：
- 方案 A：将成交价改为 close。
- 方案 B：保留 open 成交，但所有特征整体滞后 1 天。

## 11. 总体研究结论
- downside risk 模型单独作为“低风险排序”是可训练、可落地的。
- 在 2018H1-2022H2 的多数阶段，二阶段收益+风险模型有一定增益，尤其在弱势或困难阶段更有价值。
- 在 2024H2-2025H2，这套 rerank_pool80_keep10 发生了明显的过度干预，压坏了本来已经很强的收益信号。
- 2026YTD 说明不只是风险模型问题，baseline 自身也已经失效或面临风格切换。
- 更适合后续继续测试的方案不是“强重排”，而是：
- 只做风险过滤，不做大幅重排。
- 或提高固定保留比例，例如 keep20 / keep25。
- 或仅在 baseline 较弱阶段启用风险模型。

## 12. 建议下一步
- 先做“过滤式策略”：收益前 80 中剔除风险最差的 10-20 只，再按收益取前 40。
- 同时做一版无时点泄露的严格回测，用于确认 open 成交框架下结果是否稳健。
