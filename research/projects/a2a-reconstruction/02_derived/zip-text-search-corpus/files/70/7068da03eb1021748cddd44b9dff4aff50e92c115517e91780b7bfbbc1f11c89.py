"""Background poller — RUN-008 V/W fix 兜底.

# spec source:
#   docs/claude-code-daemon-mechanics.md §4.2 选项 A (推荐)
#   docs/DOGFOOD-RUN-001-FINDINGS.md V/W
#
# 设计意图:
#   spawn 时 helper 不传 -w → daemon 多数情况不创独立 worktree → bg 跟 main
#   共享 cwd + .towow + events.log 自然满足 V-04 单源.
#
#   但 RUN-005 那次 daemon 偶尔自动 isolate (trigger 条件不透明, 见 daemon-
#   mechanics §2.3). 为兜底这种偶发, helper spawn 后 fork 本 poller 作 detached
#   subprocess, 周期 poll daemon state.json:
#     - worktreePath 始终 None + bg 终止 → no-op exit
#     - worktreePath 变成非 None (daemon 偶发 isolate) → 立即 symlink + 检测
#       base stale 时 emit ObligationViolated audit trail
#     - timeout (default 1h) → no-op exit
#
# Usage (helper 内部):
#   subprocess.Popen([sys.executable, "-m", "towow.l2.bg_worktree_poller",
#                     "<short_id>", "<main_worktree>"], start_new_session=True, ...)
"""

from __future__ import annotations

import contextlib
import json
import subprocess
import sys
import time
import uuid
from pathlib import Path


# Import lazily inside helpers — module loaded as standalone subprocess.
def _ensure_shared_towow(daemon_worktree: Path, main_worktree: Path) -> bool:
    """Re-implement here so poller has minimal import surface (avoid circular)."""
    main_towow = main_worktree.resolve() / ".towow"
    if not main_towow.is_dir():
        return False
    target_towow = daemon_worktree.resolve() / ".towow"
    if target_towow.is_symlink():
        return True
    if target_towow.exists():
        return False
    target_towow.parent.mkdir(parents=True, exist_ok=True)
    target_towow.symlink_to(main_towow, target_is_directory=True)
    return True


def _git_head_commit(repo_dir: Path) -> str | None:
    """Re-implement for self-containment."""
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo_dir), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if proc.returncode == 0:
            return proc.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        pass
    return None


def _emit_obligation_violated_stale_base(
    main_towow: Path,
    bg_short_id: str,
    daemon_worktree: Path,
    daemon_head: str,
    main_head: str,
) -> None:
    """W hard enforce audit trail: emit ObligationViolated when bg worktree base != main HEAD.

    Best-effort — failure to emit is non-fatal. The record still goes through
    EventLog's path-B writer so canonical readers receive writer-stamped fields.
    """
    intent_id = f"oblig-violate-stale-{uuid.uuid4().hex[:8]}"
    payload = {
        "target_entity_type": "obligation",
        "target_entity_id": "v3-fork-base-must-be-main-head",
        "touch_type": "write",
        "kind": "ObligationViolated",
        "stub_original_payload": {
            "kind": "ObligationViolated",
            "obligation_id": "v3-fork-base-must-be-main-head",
            "obligation_lifecycle_state": "violated",
            "violated_in_envelope_event_id": f"poller-detect-{bg_short_id}",
            "violation_description": (
                f"daemon bg worktree {daemon_worktree} HEAD={daemon_head[:12]} != "
                f"main HEAD={main_head[:12]}. daemon spare-pool 复用 stale base; "
                "bg 在 stale code 上做的工作可能跟 main 后续 commit 不一致. "
                "建议 bg agent 跑 `git fetch && git rebase " + main_head + "`."
            ),
            "recommended_action": "fix",
        },
    }
    from towow.l0.event_log import EventLog
    from towow.schemas.enums import (
        ActorType,
        BaseClassification,
        EventCategory,
        EventType,
        SubjectEntityType,
        SubjectRole,
    )
    from towow.schemas.event_intent import EventIntent, ProvenanceHint, Subject, Supersede

    intent = EventIntent(
        local_intent_id=intent_id,
        event_type=EventType.NODE_TOUCHED,
        event_category=EventCategory.ENVELOPE,
        payload=payload,
        provenance_hint=ProvenanceHint(
            actor_type=ActorType.SYSTEM.value,
            actor_id="bg-worktree-poller",
            session_id=f"sess-poller-{bg_short_id}",
        ),
        base_classification=BaseClassification.DISCARDABLE_NOISE,
        supersede=Supersede(is_supersede=False),
        subjects=[
            Subject(
                entity_type=SubjectEntityType.OBLIGATION,
                entity_id="v3-fork-base-must-be-main-head",
                role=SubjectRole.PRIMARY,
            ),
        ],
        schema_version="1.0.0",
    )
    with contextlib.suppress(OSError, RuntimeError, ValueError):  # best-effort; don't fail poller
        EventLog(main_towow / "events.log").write_direct(intent)


def poll_loop(
    bg_short_id: str,
    main_worktree: Path,
    timeout_s: float = 3600.0,
    poll_interval_s: float = 10.0,
) -> str:
    """Poll daemon state.json until worktreePath set, terminal state, or timeout.

    Returns one of:
      'symlinked' — daemon created worktree; symlink created
      'symlink_blocked' — daemon worktree exists but its .towow is already a real dir
      'no_worktree_bg_done' — bg terminated without worktree creation (no symlink needed)
      'no_worktree_timeout' — poller timeout without observing worktree creation
      'missing_state' — state.json file doesn't appear; abort
    """
    state_path = Path.home() / ".claude" / "jobs" / bg_short_id / "state.json"
    deadline = time.monotonic() + timeout_s

    # initial wait for state.json to exist
    for _ in range(30):
        if state_path.exists():
            break
        time.sleep(0.5)
    if not state_path.exists():
        return "missing_state"

    while time.monotonic() < deadline:
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            time.sleep(poll_interval_s)
            continue

        worktree_path_str = state.get("worktreePath")
        if worktree_path_str:
            # daemon created an isolated worktree
            daemon_wt = Path(worktree_path_str)
            ok = _ensure_shared_towow(daemon_wt, main_worktree)
            outcome = "symlinked" if ok else "symlink_blocked"
            # W hard enforce: check if daemon worktree base is stale
            if ok:
                main_head = _git_head_commit(main_worktree)
                daemon_head = _git_head_commit(daemon_wt)
                if main_head and daemon_head and main_head != daemon_head:
                    _emit_obligation_violated_stale_base(
                        main_worktree.resolve() / ".towow",
                        bg_short_id,
                        daemon_wt,
                        daemon_head,
                        main_head,
                    )
            return outcome

        # daemon never created worktree but bg already terminated?
        cur_state = state.get("state", "")
        if cur_state in ("done", "stopped", "blocked"):
            return "no_worktree_bg_done"

        time.sleep(poll_interval_s)

    return "no_worktree_timeout"


def main() -> int:
    """CLI entry: python -m towow.l2.bg_worktree_poller <short_id> <main_worktree>"""
    if len(sys.argv) < 3:
        sys.stderr.write(
            "usage: bg_worktree_poller <bg_short_id> <main_worktree_path>\n",
        )
        return 2
    short_id = sys.argv[1]
    main_worktree = Path(sys.argv[2])
    outcome = poll_loop(short_id, main_worktree)
    # write outcome to a small marker file in ~/.claude/jobs/<short>/poller_outcome
    try:
        marker = Path.home() / ".claude" / "jobs" / short_id / "poller_outcome"
        marker.write_text(outcome, encoding="utf-8")
    except OSError:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
