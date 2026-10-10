import numpy as np
import pandas as pd
import lightgbm as lgb

from qlib.contrib.model.gbdt import LGBModel
from qlib.data.dataset.handler import DataHandlerLP


class RecencyWeightedLGBModel(LGBModel):
    """
    V24-C:
    在原有 LGBModel 基础上，训练时对近样本加更高权重。
    """

    def __init__(
        self,
        recency_half_life_days=504,
        recency_min_weight=0.05,
        recency_ref_date=None,
        **kwargs,
    ):
        """
        recency_half_life_days:
            半衰期，默认 504 个自然日，约 2 年。
        recency_min_weight:
            最小样本权重下限，避免太老样本权重变成 0。
        recency_ref_date:
            参考日期。一般填 fit_end，如 2025-06-30。
        """
        self.recency_half_life_days = recency_half_life_days
        self.recency_min_weight = recency_min_weight
        self.recency_ref_date = recency_ref_date
        super().__init__(**kwargs)

    def _split_xy(self, seg):
        """
        兼容 qlib Dataset.prepare 返回格式。
        """
        if isinstance(seg, tuple) and len(seg) == 2:
            x, y = seg
        else:
            x = seg["feature"]
            y = seg["label"]

        if isinstance(y, pd.DataFrame):
            y = y.iloc[:, 0]
        elif isinstance(y, pd.Series):
            pass
        else:
            y = pd.Series(np.asarray(y).reshape(-1))

        return x, y

    def _make_recency_weight(self, index):
        """
        基于 datetime 生成时间衰减权重。
        返回 numpy 1-D array，供 LightGBM 直接使用。
        """
        if isinstance(index, pd.MultiIndex):
            dt = pd.to_datetime(index.get_level_values("datetime"))
        else:
            dt = pd.to_datetime(index)

        dt = pd.Series(dt)

        if self.recency_ref_date is None:
            ref_date = pd.Timestamp(dt.max())
        else:
            ref_date = pd.Timestamp(self.recency_ref_date)

        age_days = (ref_date - dt).dt.days.astype(float).to_numpy()
        age_days = np.maximum(age_days, 0.0)

        w = np.power(0.5, age_days / float(self.recency_half_life_days))
        w = np.maximum(w, float(self.recency_min_weight))
        w = w / np.mean(w)

        return np.asarray(w, dtype=np.float32)

    def fit(
        self,
        dataset,
        num_boost_round=1000,
        early_stopping_rounds=50,
        verbose_eval=20,
        evals_result=None,
    ):
        if evals_result is None:
            evals_result = {}

        train_seg, valid_seg = dataset.prepare(
            ["train", "valid"],
            col_set=["feature", "label"],
            data_key=DataHandlerLP.DK_L,
        )

        x_train, y_train = self._split_xy(train_seg)
        x_valid, y_valid = self._split_xy(valid_seg)

        w_train = np.asarray(self._make_recency_weight(x_train.index), dtype=np.float32)
        w_valid = np.asarray(self._make_recency_weight(x_valid.index), dtype=np.float32)
        print("[DEBUG] recency_half_life_days =", self.recency_half_life_days)
        print("[DEBUG] recency_ref_date =", self.recency_ref_date)
        print("[DEBUG] train weight stats:",
            float(np.min(w_train)), float(np.mean(w_train)), float(np.max(w_train)))
        print("[DEBUG] valid weight stats:",
            float(np.min(w_valid)), float(np.mean(w_valid)), float(np.max(w_valid)))

        if isinstance(x_train, pd.DataFrame):
            x_train_values = x_train.values
            feature_name = list(x_train.columns)
        else:
            x_train_values = np.asarray(x_train)
            feature_name = None

        if isinstance(x_valid, pd.DataFrame):
            x_valid_values = x_valid.values
        else:
            x_valid_values = np.asarray(x_valid)

        y_train_values = np.asarray(y_train).reshape(-1)
        y_valid_values = np.asarray(y_valid).reshape(-1)

        dtrain = lgb.Dataset(
            x_train_values,
            label=y_train_values,
            weight=w_train,
            feature_name=feature_name,
        )
        dvalid = lgb.Dataset(
            x_valid_values,
            label=y_valid_values,
            weight=w_valid,
            feature_name=feature_name,
            reference=dtrain,
        )

        params = dict(getattr(self, "params", {}))
        params.setdefault("objective", "regression")
        params.setdefault("verbosity", -1)

        self.model = lgb.train(
            params=params,
            train_set=dtrain,
            num_boost_round=num_boost_round,
            valid_sets=[dtrain, dvalid],
            valid_names=["train", "valid"],
            callbacks=[
                lgb.early_stopping(early_stopping_rounds),
                lgb.log_evaluation(verbose_eval),
                lgb.record_evaluation(evals_result),
            ],
        )

        return self