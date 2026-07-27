#!/usr/bin/env python3
"""Build frozen prompts from public inputs and the baseline source."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "runs" / "r5-4-run-001-source-identity"
REPO = ROOT.parents[1]
PROMPTS = RUN / "prompts"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _slice(path: Path, start: int, end: int) -> str:
    lines = _read(path).splitlines()
    return "\n".join(f"{i}: {lines[i - 1]}" for i in range(start, min(end, len(lines)) + 1))


def _public_source() -> str:
    projection = REPO / "harness/src/towow/l0/projection/projection.py"
    invalidation = REPO / "harness/src/towow/l1/consensus_invalidation.py"
    retire = REPO / "harness/src/towow/l0/commit_gate/concept_retire_gate.py"
    return "\n\n".join(
        [
            "## projection.py reducer\n" + _slice(projection, 2355, 2450),
            "## projection.py helper area\n" + _slice(projection, 3010, 3075),
            "## consensus_invalidation.py\n" + _slice(invalidation, 1, 230),
            "## concept_retire_gate.py migration logic\n" + _slice(retire, 240, 520),
        ]
    )


def main() -> None:
    PROMPTS.mkdir(parents=True, exist_ok=True)
    public = _read(RUN / "inputs/public_problem.md")
    card = _read(RUN / "inputs/static_capability_card.md")
    a = _read(RUN / "inputs/agent_a_private.md")
    b = _read(RUN / "inputs/agent_b_private.md")
    source = _public_source()

    (PROMPTS / "static_builder.md").write_text(
        f"""# Condition: static single-agent baseline

{public}

{card}

You are the only builder. You cannot ask either owner. Based on the public code
below, return a minimal unified diff for the listed repository paths. Include
tests only if the supplied source is enough; do not invent unseen APIs. A patch
that cannot be made responsibly may return UNKNOWN.

{source}
""",
        encoding="utf-8",
    )
    fixed_queries = """Answer only these fixed narrow questions:
1. Which fields identify the local owner and locator?
2. What exact effect must a local removal have and must not have?
3. What backward-compatibility behavior is mandatory for source-less historical events?
4. Which downstream folds or auxiliary events must preserve the same identity?
Do not propose code. Minimize disclosure."""
    (PROMPTS / "central_a_report.md").write_text(
        f"# Least-privilege central query to owner A\n\n{a}\n\n{fixed_queries}\n",
        encoding="utf-8",
    )
    (PROMPTS / "central_b_report.md").write_text(
        f"# Least-privilege central query to owner B\n\n{b}\n\n{fixed_queries}\n",
        encoding="utf-8",
    )
    (PROMPTS / "a2a_a_round1.md").write_text(
        f"""# Direct A2A — owner A, round 1

{public}

{a}

Start a direct negotiation with owner B. You do not know B's event sequence or
acceptance rules. Decide what minimum question or proposal is necessary. You
may ASK, REFUSE, return UNKNOWN, COUNTER, or PROPOSE. Do not write code and do
not pretend to accept for B.
""",
        encoding="utf-8",
    )
    (PROMPTS / "public_source.txt").write_text(source + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
