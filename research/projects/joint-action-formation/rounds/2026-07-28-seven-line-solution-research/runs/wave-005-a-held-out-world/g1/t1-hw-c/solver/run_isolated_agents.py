#!/usr/bin/env python3
"""Run one fresh ephemeral Codex process per explicitly named HW-C packet.

The orchestrator copies bytes without parsing packet JSON.  The model-visible
working directory contains only the public method contract, public submission
schema, isolated return schema, and one holder packet.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOLVER = ROOT / "solver"
LOCAL = ROOT / "delivery-packets" / "local"
RUNS = ROOT / "candidate-isolated-runs"
MODEL = "gpt-5.6-sol"
ALLOWED_PARTIES = {
    "FALLOW-26",
    "GROVE-61",
    "HOLLOW-34",
    "ISLET-53",
    "JUNCTION-88",
    "LAGOON-97",
    "MORAIN-20",
    "NARROW-63",
    "ORBIT-07",
    "PINNACLE-39",
    "QUARRY-55",
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prompt(party: str, packet_sha256: str) -> str:
    return f"""Task ID: HWC-ISOLATED-{party}
Packet version: sha256:{packet_sha256}

Question:
What is the minimal authorized coordinator/controller return from {party}'s
single local packet under the method-visible contract?

Why it matters:
The blind coordinator must reconstruct opportunities without centralizing raw
local packets or treating authorization as execution.

Evidence you may use:
- method-visible-README.md
- submission_schema.json
- isolated_return_schema.json
- local-packet.json (source sha256 {packet_sha256})

Required result:
Return one JSON object matching isolated_return_schema.json. Copy exact
authorized receipt/projection/update/permission objects when the packet exposes
them. Do not return raw local facts that are not explicitly deliverable.

Success means:
- party and source_sha256 match the isolated packet.
- authorized_returns contains only explicitly deliverable minimal material.
- REFUSE, ABSENT, UNKNOWN, version updates, and execution permission remain
  distinct.
- evidence_refs use only IDs visible in the packet/public contract.

Hard boundaries:
- The working directory is the complete allowlist. Do not inspect any parent,
  absolute, repository, hidden, Git, private, tests, oracle, scorer, controller
  index, coordinator index, or other local-packet path.
- Do not execute or simulate an authorized action.
- Do not report AUTHORIZED as EXECUTED or invent receipts, ACKs, anchors,
  measurements, parties, directions, versions, compatibility keys, or evidence.
- Existing/simple interpretations count as success when they preserve the exact
  packet boundary.
- Return JSON only. Do not edit files.

Use method-visible-README.md for semantics, submission_schema.json only for the
eventual coordinator shape, and isolated_return_schema.json for this response.
"""


def run_party(party: str) -> int:
    if party not in ALLOWED_PARTIES:
        raise SystemExit(f"party not allowlisted: {party}")
    source = LOCAL / f"{party}.json"
    packet_sha256 = digest(source)
    destination = RUNS / party
    destination.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix=f"hwc-{party.lower()}-") as raw:
        isolated = Path(raw)
        copies = {
            "method-visible-README.md": ROOT / "method-visible" / "README.md",
            "submission_schema.json": ROOT
            / "method-visible"
            / "submission_schema.json",
            "isolated_return_schema.json": SOLVER
            / "isolated_return_schema.json",
            "local-packet.json": source,
        }
        for name, path in copies.items():
            shutil.copyfile(path, isolated / name)

        task_prompt = prompt(party, packet_sha256)
        (destination / "prompt.txt").write_text(
            task_prompt, encoding="utf-8"
        )
        allowlist = {
            "task_id": f"HWC-ISOLATED-{party}",
            "party": party,
            "model_requested": MODEL,
            "files": [
                {
                    "model_visible_name": name,
                    "source_path": str(path.relative_to(ROOT)),
                    "sha256": digest(path),
                }
                for name, path in copies.items()
            ],
            "forbidden": [
                "controller_input.json",
                "delivery-packets/controller-index.json",
                "delivery-packets/coordinator.json",
                "private/**",
                "tests/**",
                "other delivery-packets/local/*.json",
            ],
        }
        (destination / "allowlist.json").write_text(
            json.dumps(allowlist, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        command = [
            "codex",
            "exec",
            "--ephemeral",
            "--ignore-user-config",
            "--skip-git-repo-check",
            "--sandbox",
            "workspace-write",
            "--cd",
            str(isolated),
            "--model",
            MODEL,
            "--output-schema",
            str(isolated / "isolated_return_schema.json"),
            "--json",
            "--output-last-message",
            str(destination / "last-message.json"),
            task_prompt,
        ]
        completed = subprocess.run(
            command,
            text=True,
            capture_output=True,
            check=False,
        )
        (destination / "stdout.jsonl").write_text(
            completed.stdout, encoding="utf-8"
        )
        (destination / "stderr.log").write_text(
            completed.stderr, encoding="utf-8"
        )
        exit_record = {
            "task_id": f"HWC-ISOLATED-{party}",
            "party": party,
            "exit_code": completed.returncode,
            "model_requested": MODEL,
            "packet_sha256": packet_sha256,
            "finished_at": datetime.now(timezone.utc).isoformat(),
        }
        (destination / "exit.json").write_text(
            json.dumps(exit_record, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return completed.returncode


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("parties", nargs="+")
    args = parser.parse_args()
    for party in args.parties:
        code = run_party(party)
        if code != 0:
            return code
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
