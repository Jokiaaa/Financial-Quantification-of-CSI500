import runpy
import unittest
from datetime import date, timedelta
from pathlib import Path


MODULE = runpy.run_path(str(Path(__file__).resolve().parents[1] / "tools" / "research_pipeline.py"))


class TimingProtocolTests(unittest.TestCase):
    def setUp(self):
        start = date(2024, 12, 1)
        self.calendar = [(start + timedelta(days=offset)).isoformat() for offset in range(120) if (start + timedelta(days=offset)).weekday() < 5]

    def test_construction_is_on_session_21_not_calendar_day_21(self):
        plan = MODULE["plan_dates"](self.calendar, "2025-01-01", "2025-02-28", "2024-12-31")
        sessions = [session for session in self.calendar if session >= "2025-01-01"]
        self.assertEqual(plan["first_actual_trade_date"], sessions[20])
        self.assertEqual(plan["first_execution_signal_date"], sessions[19])
        self.assertLess(plan["validation_label_maturity_close"], plan["first_actual_trade_date"])

    def test_immature_validation_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "not mature"):
            MODULE["plan_dates"](self.calendar, "2025-01-01", "2025-02-28", "2025-01-10")

    def test_short_wait_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "at least 20"):
            MODULE["plan_dates"](self.calendar, "2025-01-01", "2025-02-28", "2024-12-31", 19)

    def test_no_investable_session_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "no post-waiting"):
            MODULE["plan_dates"](self.calendar, "2025-01-01", "2025-01-10", "2024-12-31")

    def test_manifest_relative_paths_follow_manifest_directory(self):
        manifest = Path(__file__).resolve().parent / "config" / "replay.json"
        self.assertEqual(MODULE["resolve_path"](manifest, "../data/pred.pkl"), manifest.parent.parent / "data" / "pred.pkl")

    def test_calendar_must_extend_beyond_evaluation(self):
        with self.assertRaisesRegex(ValueError, "calendar session after"):
            MODULE["plan_dates"](self.calendar, "2025-01-01", self.calendar[-1], "2024-12-31")

    def test_open_limit_uses_open_and_prior_close(self):
        config = {"exchange": {"deal_price": "open", "limit_threshold": 0.095}}
        actual = MODULE["execution_exchange"](config)
        self.assertEqual(actual["limit_threshold"], ("$open >= Ref($close, 1) * 1.095", "$open <= Ref($close, 1) * 0.905"))
        self.assertEqual(config["exchange"]["limit_threshold"], 0.095)


if __name__ == "__main__":
    unittest.main()
