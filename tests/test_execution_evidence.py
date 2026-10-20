import hashlib
import json
import runpy
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERIFY = runpy.run_path(str(ROOT / "tools" / "verify_execution_artifacts.py"))["verify_run"]


class CommittedExecutionEvidenceTests(unittest.TestCase):
    def test_committed_runs_have_valid_orders_costs_and_output_hashes(self):
        manifests = list((ROOT / "results").rglob("run_manifest.json"))
        self.assertTrue(manifests, "No committed execution evidence")
        for manifest in manifests:
            with self.subTest(run=str(manifest.parent.relative_to(ROOT))):
                result = VERIFY(manifest.parent)
                self.assertTrue(result["verified"])
                self.assertGreater(len(result["variants"]), 0)

    def test_native_models_match_training_manifest_and_feature_counts(self):
        directory = ROOT / "results" / "matched_models_2025H1"
        manifest = json.loads((directory / "training_manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(len(manifest["predictions"]), 3)
        for name, record in manifest["predictions"].items():
            with self.subTest(model=name):
                content = (directory / name / "model.txt").read_bytes()
                self.assertEqual(hashlib.sha256(content).hexdigest(), record["model"]["sha256"])
                lines = content.decode("utf-8").splitlines()
                feature_line = next(line for line in lines if line.startswith("max_feature_idx="))
                self.assertEqual(int(feature_line.split("=")[1]) + 1, record["feature_count"])


if __name__ == "__main__":
    unittest.main()
