from qlib.contrib.data.handler import Alpha158


class Alpha158Label20PlusConfirm(Alpha158):
    def get_feature_config(self):
        fields, names = super().get_feature_config()

        extra_fields = [
            "Std($close / Ref($close, 1) - 1, 20) / (Std($close / Ref($close, 1) - 1, 60) + 1e-12)",
            "Std($close / Ref($close, 1) - 1, 10) / (Std($close / Ref($close, 1) - 1, 40) + 1e-12)",

            "(Max($high, 20) - Min($low, 20)) / (Mean($close, 20) + 1e-12)",
            "(Max($high, 40) - Min($low, 40)) / (Mean($close, 40) + 1e-12)",
            "(Max($high, 80) - Min($low, 80)) / (Mean($close, 80) + 1e-12)",

            "((Max($high, 20) - Min($low, 20)) / (Mean($close, 20) + 1e-12)) / (((Max($high, 60) - Min($low, 60)) / (Mean($close, 60) + 1e-12)) + 1e-12)",

            "Mean($volume, 20) / (Mean($volume, 60) + 1e-12) - 1",
            "Mean($volume, 40) / (Mean($volume, 80) + 1e-12) - 1",

            "Mean($vwap, 20) / Mean($close, 20) - 1",
            "Mean($vwap, 40) / Mean($close, 40) - 1",
        ]

        extra_names = [
            "VOLRATIO20_60",
            "VOLRATIO10_40",
            "RANGE20_NORM",
            "RANGE40_NORM",
            "RANGE80_NORM",
            "RANGE20_60_RATIO",
            "VOLMEAN20_60",
            "VOLMEAN40_80",
            "VWAP_CLOSE20",
            "VWAP_CLOSE40",
        ]

        fields.extend(extra_fields)
        names.extend(extra_names)
        return fields, names