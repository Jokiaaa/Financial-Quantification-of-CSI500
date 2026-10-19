from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCES = [
    ("E01", "v1/考试.txt", "baseline_evaluation.txt"),
    ("E02", "v24/v24-c半衰期比较.txt", "recency_half_life_comparison.txt"),
    ("E03", "v25/说明.txt", "hl378_selection.txt"),
    ("E04", "v31/最终模型定版说明.txt", "rolling_model_decision.txt"),
    ("E05", "研究2/confirm有效成分.txt", "feature_ablation.txt"),
    ("E06", "研究4/防未来信息泄露.txt", "router_information_audit.txt"),
    ("E07", "研究5/HL378半年度接力保守版实验记录_20260505.md", "relay_guard_experiment.md"),
    ("E08", "研究6/HL378_Failure_Aware_Router_v4_交接总报告_20260508.md", "failure_router_report.md"),
    ("E09", "研究7/研究7_风险模型实验总报告.md", "downside_risk_experiment.md"),
    ("E10", "研究8/模型1接力基本盘健康度风控实验记录_20260527.md", "portfolio_health_experiment.md"),
    ("E11", "最终版本/frozen_hl378_mw2e4_T40_D2_20260528/README_FREEZE.txt", "freeze_description.txt"),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Import a curated set of research notes or verify the bundled snapshots.")
    parser.add_argument("--archive", type=Path, help="Source archive directory; reads only the explicitly listed research notes")
    parser.add_argument("--check", action="store_true", help="Verify bundled snapshots without accessing the external archive")
    arguments = parser.parse_args()
    destination = ROOT / "research_archive"
    manifest_path = destination / "manifest.json"
    if arguments.check:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if len(manifest["sources"]) != len(SOURCES):
            raise ValueError("Unexpected evidence count")
        for source, expected in zip(manifest["sources"], SOURCES):
            evidence_id, origin, filename = expected
            if (source["id"], source["original_relative_path"], source["snapshot"]) != (evidence_id, origin, filename):
                raise ValueError("Unexpected evidence identity")
            content = (destination / "sources" / filename).read_bytes()
            if hashlib.sha256(content).hexdigest() != source["sha256"] or len(content) != source["bytes"]:
                raise ValueError(f"Snapshot changed: {evidence_id}")
        print(f"Verified {len(SOURCES)} research snapshots.")
        return 0
    if arguments.archive is None:
        parser.error("Provide --archive for import, or --check to verify the bundled notes")
    contents = [(entry, (arguments.archive / entry[1]).read_bytes()) for entry in SOURCES]
    (destination / "sources").mkdir(parents=True, exist_ok=True)
    records = []
    for (evidence_id, relative_path, filename), content in contents:
        target = destination / "sources" / filename
        if target.exists() and target.read_bytes() != content:
            raise ValueError(f"Existing evidence differs; review before replacing: {target}")
        target.write_bytes(content)
        records.append({
            "id": evidence_id,
            "original_relative_path": relative_path,
            "snapshot": filename,
            "bytes": len(content),
            "sha256": hashlib.sha256(content).hexdigest(),
        })
    manifest_path.write_text(json.dumps({
        "scope": "Curated research-note snapshots; not the complete experiment archive or an independent verification of their claims",
        "sources": records,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Imported {len(records)} research snapshots; originals unchanged.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
