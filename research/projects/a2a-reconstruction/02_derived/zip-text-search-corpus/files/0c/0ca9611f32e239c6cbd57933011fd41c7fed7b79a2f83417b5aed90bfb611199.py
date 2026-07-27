#!/usr/bin/env python3
"""Build dynamic run-001 prompts from frozen, role-bound outputs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "runs" / "r5-4-run-001-source-identity"
PROMPTS = RUN / "prompts"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _structured(path: Path) -> dict[str, object]:
    return json.loads(_text(path))["structured_output"]


def after_round1() -> None:
    public = _text(RUN / "inputs/public_problem.md")
    source = _text(PROMPTS / "public_source.txt")
    a_report = _structured(RUN / "traces/central/owner_a_report/parsed.json")
    b_report = _structured(RUN / "traces/central/owner_b_report/parsed.json")
    a_round1 = _structured(RUN / "transcripts/a2a/round1_a/parsed.json")
    b_private = _text(RUN / "inputs/agent_b_private.md")

    (PROMPTS / "central_builder.md").write_text(
        f"""# Condition: least-privilege central builder

{public}

The center issued the preregistered fixed queries. It received only these
source-owner reports, not their raw event streams:

## A report
{json.dumps(a_report, ensure_ascii=False, indent=2)}

## B report
{json.dumps(b_report, ensure_ascii=False, indent=2)}

The reports conflict on source-less legacy removal semantics. Resolve this
without inventing authority: the public goal requires historical behavior to
remain compatible, so preserve the repository's prior behavior and call out the
conflict. Produce a minimal unified diff for the exact repository paths shown
below. Do not claim either owner accepted your choice.

{source}
""",
        encoding="utf-8",
    )
    (PROMPTS / "a2a_b_round2.md").write_text(
        f"""# Direct A2A — owner B, round 2

{public}

{b_private}

Owner A sent this role-bound message:
{json.dumps(a_round1, ensure_ascii=False, indent=2)}

Respond under B's own authority. Explicitly ACCEPT, COUNTER, REFUSE, or return
UNKNOWN. Address the proposed legacy behavior, identity tuple, ongoing
source-less emissions, supersede auxiliary events, and migration evidence.
Disclose only what is necessary. Do not write code.
""",
        encoding="utf-8",
    )


def after_b2() -> None:
    public = _text(RUN / "inputs/public_problem.md")
    a_private = _text(RUN / "inputs/agent_a_private.md")
    a_round1 = _structured(RUN / "transcripts/a2a/round1_a/parsed.json")
    b_round2 = _structured(RUN / "transcripts/a2a/round2_b/parsed.json")
    (PROMPTS / "a2a_a_round3.md").write_text(
        f"""# Direct A2A — owner A, round 3

{public}

{a_private}

Your round-1 proposal:
{json.dumps(a_round1, ensure_ascii=False, indent=2)}

Owner B's counter/decision:
{json.dumps(b_round2, ensure_ascii=False, indent=2)}

Under A's authority, decide whether B's conditions preserve A's local removal,
replay, and legacy requirements. If they can be reconciled, return one exact
joint lifecycle contract, including identity fields and every affected surface,
for B to sign. Otherwise REFUSE or return UNKNOWN. Do not write code.
""",
        encoding="utf-8",
    )


def after_a3() -> None:
    public = _text(RUN / "inputs/public_problem.md")
    b_private = _text(RUN / "inputs/agent_b_private.md")
    a_round3 = _structured(RUN / "transcripts/a2a/round3_a/parsed.json")
    (PROMPTS / "a2a_b_round4.md").write_text(
        f"""# Direct A2A — owner B, round 4 signature

{public}

{b_private}

Owner A proposes this exact final contract:
{json.dumps(a_round3, ensure_ascii=False, indent=2)}

ACCEPT only if the exact contract protects B's surviving reference,
supersede response, migration evidence, and legacy compatibility without
claiming authority B did not grant. Otherwise COUNTER, REFUSE, or UNKNOWN.
This is a subject acceptance action, not code verification.
""",
        encoding="utf-8",
    )


def after_b4() -> None:
    public = _text(RUN / "inputs/public_problem.md")
    source = _text(PROMPTS / "public_source.txt")
    a_round3 = _structured(RUN / "transcripts/a2a/round3_a/parsed.json")
    b_round4 = _structured(RUN / "transcripts/a2a/round4_b/parsed.json")
    (PROMPTS / "a2a_builder.md").write_text(
        f"""# Condition: direct-A2A contract builder

{public}

The builder cannot read either private dossier. It receives only the exact
role-bound contract and B's acceptance/counter:

## A final contract
{json.dumps(a_round3, ensure_ascii=False, indent=2)}

## B decision
{json.dumps(b_round4, ensure_ascii=False, indent=2)}

If B did not ACCEPT, return UNKNOWN rather than inventing agreement. If B did
ACCEPT, implement the exact contract as a minimal unified diff for the exact
repository paths shown below. Do not treat subject acceptance as test success.

{source}
""",
        encoding="utf-8",
    )


def after_b4_counter() -> None:
    public = _text(RUN / "inputs/public_problem.md")
    a_private = _text(RUN / "inputs/agent_a_private.md")
    a_round3 = _structured(RUN / "transcripts/a2a/round3_a/parsed.json")
    b_round4 = _structured(RUN / "transcripts/a2a/round4_b/parsed.json")
    (PROMPTS / "a2a_a_round5.md").write_text(
        f"""# Direct A2A — owner A, round 5 amendment

{public}

{a_private}

Your previous contract:
{json.dumps(a_round3, ensure_ascii=False, indent=2)}

Owner B refused signature and countered:
{json.dumps(b_round4, ensure_ascii=False, indent=2)}

Decide under A's authority. If the lapse/reopen clause preserves A's original
value, return the complete amended contract (not a summary or patch), expressly
replacing the disputed clause. If it transfers unacceptable risk or weakens A's
requirements, REFUSE or return UNKNOWN. Do not claim B signed and do not write
code.
""",
        encoding="utf-8",
    )


def after_a5() -> None:
    public = _text(RUN / "inputs/public_problem.md")
    b_private = _text(RUN / "inputs/agent_b_private.md")
    a_round5 = _structured(RUN / "transcripts/a2a/round5_a/parsed.json")
    (PROMPTS / "a2a_b_round6.md").write_text(
        f"""# Direct A2A — owner B, round 6 final decision

{public}

{b_private}

Owner A's complete amended contract:
{json.dumps(a_round5, ensure_ascii=False, indent=2)}

Return ACCEPT only if this exact amended contract satisfies B's source
survival, supersede response, migration evidence, legacy, and remedy
conditions. Otherwise COUNTER, REFUSE, or UNKNOWN. B signs only for B and does
not claim implementation verification.
""",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "phase",
        choices=[
            "after_round1",
            "after_b2",
            "after_a3",
            "after_b4",
            "after_b4_counter",
            "after_a5",
        ],
    )
    args = parser.parse_args()
    globals()[args.phase]()


if __name__ == "__main__":
    main()
