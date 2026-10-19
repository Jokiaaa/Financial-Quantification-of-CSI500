import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd

import update_pcf as u


class UpdateTests(unittest.TestCase):
    def frame(self, rows):
        return pd.DataFrame(rows, columns=["instrument", "datetime", "pcf", "pb"])

    def test_merge_preserves_history_other_fields_and_failed_values(self):
        old = self.frame([("SH600004", "2020-01-01", 8.0, 1.5),
                          ("SH600004", "2020-01-02", 9.0, 1.6),
                          ("SZ000001", "2020-01-01", 7.0, 2.0)])
        new = self.frame([("SH600004", "2020-01-01", np.nan, 99),
                          ("SH600004", "2020-01-02", -2.0, 99),
                          ("SH600004", "2020-01-03", 10.0, 99)])
        got = u.merge_panel(old, new).set_index(u.KEY)
        self.assertEqual(len(got), 4)
        self.assertEqual(got.loc[("SH600004", pd.Timestamp("2020-01-01")), "pcf"], 8)
        self.assertEqual(got.loc[("SH600004", pd.Timestamp("2020-01-02")), "pcf"], -2)
        self.assertEqual(got.loc[("SH600004", pd.Timestamp("2020-01-02")), "pb"], 1.6)
        self.assertEqual(got.loc[("SZ000001", pd.Timestamp("2020-01-01")), "pcf"], 7)

    def test_invalid_and_duplicate_rejected(self):
        for rows in [[("SH600004", "bad", 8, 1)], [("BAD", "2020-01-01", 8, 1)],
                     [("SH600004", "2020-01-01", float("inf"), 1)],
                     [("SH600004", "2020-01-01", "oops", 1)],
                     [("SH600004", "2020-01-01", 8, 1)] * 2]:
            with self.assertRaises(ValueError):
                u.clean(self.frame(rows))

    def test_empty_fetch_preserves_old(self):
        old = self.frame([("SH600004", "2020-01-01", 8, 1)])
        pd.testing.assert_frame_equal(u.merge_panel(old, pd.DataFrame()), u.clean(old), check_dtype=False)

    def test_network_failure_has_no_data_and_records_failure(self):
        with patch.object(u.requests, "get", side_effect=u.requests.Timeout("fixture")):
            frame, log = u.fetch_one("SH600004", retry=1, timeout=1, period="全部")
        self.assertTrue(frame.empty)
        self.assertEqual(log["status"], "failed")
        self.assertIn("Timeout", log["error"])

    def test_fetch_parses_response_and_sets_timeout(self):
        body = {"Result": [{"DisplayData": {"resultData": {"tplData": {"result": {
            "chartInfo": [{"body": [["2020-01-01", "-2.5"], ["2020-01-02", "8.5"]]}]}}}}}]}
        with patch.object(u.requests, "get") as get:
            get.return_value.json.return_value = body
            frame, log = u.fetch_one("SH600004", retry=1, timeout=3, period="全部")
            self.assertEqual(get.call_args.kwargs["timeout"], (3, 3))
        self.assertEqual(log["status"], "ok")
        self.assertEqual(frame.pcf.tolist(), [-2.5, 8.5])

    def test_publish_backup_and_change_detection(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as folder:
            target, candidate = Path(folder) / "target.csv", Path(folder) / "candidate.csv"
            target.write_text("old", encoding="utf-8")
            candidate.write_text("new", encoding="utf-8")
            original_hash, candidate_hash = u.digest(target), u.digest(candidate)
            with self.assertRaises(ValueError):
                u.publish(candidate, target, "wrong", candidate_hash)
            self.assertEqual(target.read_text(), "old")
            backup = u.publish(candidate, target, original_hash, candidate_hash)
            self.assertEqual(Path(backup).read_text(), "old")
            self.assertEqual(target.read_text(), "new")
            candidate.write_text("changed")
            with self.assertRaises(ValueError):
                u.publish(candidate, target, u.digest(target), candidate_hash)

    def test_real_backtest_lag_and_filter(self):
        ns = u.context(u.DEFAULT_SCRIPT)
        days = pd.to_datetime(["2026-06-01", "2026-06-02"])
        insts = [f"SH{600000+i:06d}" for i in range(100)]
        index = pd.MultiIndex.from_product([days, insts], names=["datetime", "instrument"])
        signal = pd.DataFrame({"score": list(range(100, 0, -1)) * 2}, index=index)
        # Rank 36 has high PCF on prior day and low PCF on current day.
        panel = pd.DataFrame([{"instrument": inst, "datetime": day,
                               "pcf": (1000 if i == 35 and day == days[0] else i+1)}
                              for day in days for i, inst in enumerate(insts)])
        audit = u.audit_signal(ns, signal, panel, "fixture", "2026-06-02")
        self.assertEqual(len(audit), 100)
        self.assertTrue(audit.covered.all())
        self.assertTrue(audit.loc[audit.instrument.eq(insts[35]), "filtered"].item())


if __name__ == "__main__":
    unittest.main(verbosity=2)
