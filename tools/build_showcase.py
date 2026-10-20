from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
from html import escape
from pathlib import Path
from statistics import mean, median


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "回测结果.md"
EXPECTED_CASES = [
    f"{year}H{half}" for year in range(2015, 2026) for half in (1, 2)
] + ["2026YTD"]
FIELDS = [
    "strategy", "case", "original_window", "evaluation_window", "trading_days",
    "return_pct", "mdd_pct", "reported_excess_pp", "benchmark_return_pct",
    "source_section", "source_line",
]


def extract_rows(source: str) -> tuple[list[dict], list[dict]]:
    section = None
    rows = []
    supplementary = []
    for line_number, line in enumerate(source.splitlines(), 1):
        if line.startswith("### "):
            section = None
            if line.startswith("### 15.2 "):
                section = ("relay_tie", "15.2")
            elif line.startswith("### 15.4 "):
                section = ("relay_tie_pcf", "15.4")
        if not section or not re.match(r"^\| 20\d\d(?:H[12]|YTD) \|", line):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != 8:
            raise ValueError(f"Unexpected result columns at line {line_number}")
        row = dict(zip(FIELDS, [
            section[0], cells[0], cells[1], cells[2], int(cells[3]),
            *[float(value.removesuffix("%")) for value in cells[4:]],
            section[1], line_number,
        ]))
        if row["trading_days"] <= 0 or row["mdd_pct"] > 0:
            raise ValueError(f"Invalid days or drawdown at line {line_number}")
        if row["case"] in EXPECTED_CASES and abs(row["return_pct"] - row["benchmark_return_pct"] - row["reported_excess_pp"]) > 0.021:
            raise ValueError(f"Excess-return mismatch at line {line_number}")
        (rows if row["case"] in EXPECTED_CASES else supplementary).append(row)
    for strategy in ("relay_tie", "relay_tie_pcf"):
        actual = [row["case"] for row in rows if row["strategy"] == strategy]
        if actual != EXPECTED_CASES:
            raise ValueError(f"Unexpected or duplicate case sequence for {strategy}: {actual}")
    baseline = {row["case"]: row for row in rows if row["strategy"] == "relay_tie"}
    for row in rows:
        other = baseline[row["case"]]
        for field in ("original_window", "evaluation_window", "trading_days", "benchmark_return_pct"):
            if row[field] != other[field]:
                raise ValueError(f"Unmatched paired field {field}: {row['case']}")
    return rows, supplementary


def csv_text(rows: list[dict]) -> str:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue()


def chart_text(rows: list[dict]) -> str:
    left, top, plot_width, plot_height = 72, 108, 1010, 282
    lower, upper = -10, 16

    def ordinate(value: float) -> float:
        return top + (upper - value) / (upper - lower) * plot_height

    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1120 510" role="img" aria-labelledby="title description">',
        '<title id="title">CSI 500: excess return by delayed evaluation window</title>',
        '<desc id="description">Paired baseline and PCF-filtered window excess returns from report section 15. Percentage points, not annualized. Negative observations are included.</desc>',
        '<rect width="1120" height="510" rx="16" fill="#f6f8fc"/>',
        '<g font-family="Arial, sans-serif" fill="#15253d">',
        '<text x="40" y="40" font-size="23" font-weight="700">CSI 500 · Valuation-aware stock selection</text>',
        '<text x="40" y="66" font-size="13" fill="#52627a">Reported excess return per delayed window · percentage points · historical simulation</text>',
        '<rect x="730" y="81" width="12" height="12" fill="#94a3b8"/><text x="749" y="92" font-size="12">Relay baseline</text>',
        '<rect x="875" y="81" width="12" height="12" fill="#0f766e"/><text x="894" y="92" font-size="12">Relay + PCF</text>',
    ]
    for tick in (-10, -5, 0, 5, 10, 15):
        position = ordinate(tick)
        color = "#64748b" if tick == 0 else "#dde4ee"
        parts.append(f'<line x1="{left}" x2="{left + plot_width}" y1="{position:.2f}" y2="{position:.2f}" stroke="{color}"/>')
        parts.append(f'<text x="59" y="{position + 4:.2f}" text-anchor="end" font-size="12">{tick}</text>')
    for case_index, case in enumerate(EXPECTED_CASES):
        center = left + (case_index + 0.5) * plot_width / len(EXPECTED_CASES)
        for strategy_index, strategy in enumerate(("relay_tie", "relay_tie_pcf")):
            row = next(row for row in rows if row["case"] == case and row["strategy"] == strategy)
            value = row["reported_excess_pp"]
            horizontal = center - 14 + strategy_index * 14
            vertical = min(ordinate(value), ordinate(0))
            bar_height = abs(ordinate(value) - ordinate(0))
            color = "#94a3b8" if strategy_index == 0 else "#0f766e"
            parts.append(f'<rect x="{horizontal:.2f}" y="{vertical:.2f}" width="12" height="{bar_height:.2f}" fill="{color}"><title>{escape(case)} {strategy}: {value:.2f} pp</title></rect>')
        parts.append(f'<text transform="translate({center:.2f},408) rotate(55)" font-size="11">{escape(case)}</text>')
    parts.extend([
        '<text x="40" y="474" font-size="12" fill="#52627a">Source: original report, sections 15.2 and 15.4 · 23 matched windows · 2026YTD ends June 16</text>',
        '<text x="40" y="494" font-size="12" fill="#52627a">Rebuilt from rounded report observations; no continuous NAV or independent execution audit is implied.</text>',
        '</g></svg>\n',
    ])
    return "\n".join(parts)


def results_text(rows: list[dict], supplementary: list[dict]) -> str:
    lines = [
        "# Historical results: paired delayed evaluation windows", "",
        "![Window excess returns](../assets/delay20_excess.svg)", "",
        "## Scope and provenance", "",
        "Calculated from rounded observations in sections 15.2 and 15.4 of [the original research record](../回测结果.md). This reproduces reported results, not model training or order execution.", "",
        "The main comparison has 23 matching windows: 2015H1–2025H2 plus 2026YTD (through June 16). Each begins on its 21st trading-day record. The additional PCF-only 2026H1 observation is supplementary and is never counted alongside overlapping 2026YTD.", "",
        "## Descriptive summary", "",
        "Returns and drawdowns are percentages; excess and differences are percentage points. Each window has equal weight, including shorter YTD. None of these averages is an annualized or continuous-account metric.", "",
        "| Sample | Strategy | Windows | Mean return | Mean reported excess | Median reported excess | Mean within-window MDD | Positive excess windows |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for sample, exclude_2015 in (("All paired windows", False), ("Excluding 2015", True)):
        for strategy in ("relay_tie", "relay_tie_pcf"):
            selected = [row for row in rows if row["strategy"] == strategy and not (exclude_2015 and row["case"].startswith("2015"))]
            lines.append(f"| {sample} | `{strategy}` | {len(selected)} | {mean(row['return_pct'] for row in selected):.2f}% | {mean(row['reported_excess_pp'] for row in selected):.2f} pp | {median(row['reported_excess_pp'] for row in selected):.2f} pp | {mean(row['mdd_pct'] for row in selected):.2f}% | {sum(row['reported_excess_pp'] > 0 for row in selected)}/{len(selected)} |")
    baseline = {row["case"]: row for row in rows if row["strategy"] == "relay_tie"}
    filtered = [row for row in rows if row["strategy"] == "relay_tie_pcf"]
    differences = [row["return_pct"] - baseline[row["case"]]["return_pct"] for row in filtered]
    lines += [
        "", f"Across paired windows, PCF changes mean window return by **{mean(differences):+.2f} pp**, with higher return in **{sum(value > 0 for value in differences)}/23** windows and equal return in **{sum(abs(value) < 1e-9 for value in differences)}/23**. This is descriptive, not a significance test.", "",
        "## Window observations", "",
        "| Window | Evaluation dates | Days | Benchmark | Relay | Relay + PCF | Relay excess | PCF excess | PCF − relay return |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in filtered:
        other = baseline[row["case"]]
        lines.append(f"| {row['case']} | {row['evaluation_window']} | {row['trading_days']} | {row['benchmark_return_pct']:.2f}% | {other['return_pct']:.2f}% | {row['return_pct']:.2f}% | {other['reported_excess_pp']:.2f} pp | {row['reported_excess_pp']:.2f} pp | {row['return_pct'] - other['return_pct']:+.2f} pp |")
    lines += ["", "## Supplementary observation", ""]
    for row in supplementary:
        lines.append(f"- `{row['strategy']}`, {row['case']}, {row['evaluation_window']}: return {row['return_pct']:.2f}%, excess {row['reported_excess_pp']:.2f} pp, within-window MDD {row['mdd_pct']:.2f}%. Excluded from paired summary.")
        difference = row["return_pct"] - row["benchmark_return_pct"]
        if abs(difference - row["reported_excess_pp"]) > 0.021:
            lines.append(f"- Resolved metric mismatch: displayed return minus benchmark is {difference:.2f} pp, whereas the original reported field is {row['reported_excess_pp']:.2f}. Daily records show the latter is summed daily excess, not compound return difference. See [the full-precision reconciliation](reconciliation_2026H1/RECONCILIATION.md). Original source values are preserved.")
    lines += [
        "", "## Metric and execution boundaries", "",
        "- Excess is the source's difference between compounded portfolio and benchmark returns. Small subtraction discrepancies arise from rounding.",
        "- Averaged within-window drawdowns are not the maximum drawdown of an investable multi-year portfolio.",
        "- The source describes Qlib costs and net portfolio returns. Fees and day-21 initial construction costs were not independently reconstructed here.",
        "- The author's day-21 construction procedure and the report's delayed-window calculation are distinguished in [the timing protocol](../docs/METHODOLOGY.md). Tables alone do not establish execution timing.",
        "- Source summary cells can differ from means of rounded rows. This page always computes from extracted observations; the original is unchanged.",
        "- No full-period CAGR, Sharpe, significance, or live-performance claim is inferred.", "",
        "## Machine-readable artifacts", "",
        "- [Paired rows](delay20_windows.csv)",
        "- [Supplementary rows](supplementary_windows.csv)",
        "- [Source hash and metadata](provenance.json)", "",
        "Rebuild: `python tools/build_showcase.py`. Verify: `python tools/build_showcase.py --check`.", "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the research presentation from the committed report; no backtest is run.")
    parser.add_argument("--check", action="store_true", help="Verify generated artifacts without writing")
    arguments = parser.parse_args()
    source_bytes = SOURCE.read_bytes()
    rows, supplementary = extract_rows(source_bytes.decode("utf-8-sig"))
    metadata = {
        "source": SOURCE.relative_to(ROOT).as_posix(),
        "source_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "sections": ["15.2", "15.4"],
        "paired_windows": len(EXPECTED_CASES),
        "paired_rows": len(rows),
        "supplementary_rows": len(supplementary),
        "value_origin": "rounded Markdown table observations",
        "execution_verified": False,
        "overlap_policy": "2026YTD is paired; overlapping PCF-only 2026H1 is supplementary",
    }
    artifacts = {
        "results/delay20_windows.csv": csv_text(rows),
        "results/supplementary_windows.csv": csv_text(supplementary),
        "results/provenance.json": json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        "assets/delay20_excess.svg": chart_text(rows),
        "results/RESULTS.md": results_text(rows, supplementary),
    }
    stale = []
    for relative_path, content in artifacts.items():
        path = ROOT / relative_path
        expected = content.encode("utf-8")
        if arguments.check:
            if not path.exists() or path.read_bytes() != expected:
                stale.append(relative_path)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(expected)
    if stale:
        raise SystemExit("Missing or stale artifacts: " + ", ".join(stale))
    print(f"{'Verified' if arguments.check else 'Built'} {len(artifacts)} artifacts: {len(rows)} paired rows, {len(supplementary)} supplementary row(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
