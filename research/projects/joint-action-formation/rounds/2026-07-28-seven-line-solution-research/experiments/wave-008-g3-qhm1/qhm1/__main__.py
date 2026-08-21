from __future__ import annotations

import json
from pathlib import Path

from .runner import build_report


def main() -> None:
    report = build_report()
    output_dir = Path(__file__).resolve().parents[1] / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "report.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "model-check.json").write_text(
        json.dumps(
            report["oracle"],
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (output_dir / "theory-gates.json").write_text(
        json.dumps(
            report["theory_gates"],
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    trace_lines = []
    for run in report["runs"]:
        trace_lines.append(
            json.dumps(
                {
                    "public_trial_id": run["public_trial_id"],
                    "truth_id_revealed_after_run": run["truth_id"],
                    "system": run["system"],
                    "outcome": run["outcome"],
                    "trace": run["trace"],
                    "receipts": run["receipts"],
                    "orthogonal_vector": run["orthogonal_vector"],
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
    (output_dir / "traces.jsonl").write_text(
        "\n".join(trace_lines) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "report": str(report_path),
                "outcome_counts": report["outcome_counts"],
                "external_calls": report["external_calls"],
                "synthetic_existing_compositions_close_all_bounded_worlds":
                    report["comparative_result"][
                        "synthetic_existing_compositions_close_all_bounded_worlds"
                    ],
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
