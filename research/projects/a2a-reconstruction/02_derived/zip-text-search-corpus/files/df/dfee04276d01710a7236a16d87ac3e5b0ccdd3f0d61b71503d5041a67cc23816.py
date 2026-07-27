"""RUN-008 unit tests for bg_worktree_poller.

# spec source:
#   src/towow/l2/bg_worktree_poller.py
#   docs/claude-code-daemon-mechanics.md §4.2 选项 A
#
# Covers:
#   T-Fix.Poll1 — poll_loop returns 'no_worktree_bg_done' when bg terminates without worktree
#   T-Fix.Poll2 — poll_loop returns 'symlinked' when daemon creates worktree mid-poll
#   T-Fix.Poll3 — poll_loop returns 'missing_state' when state.json never appears
#   T-Fix.Poll4 — stale base detected → emit ObligationViolated audit trail
"""

from __future__ import annotations

import json
import subprocess
import threading
import time
from typing import TYPE_CHECKING

from towow.l0.event_log import EventLog
from towow.l2.bg_worktree_poller import poll_loop
from towow.schemas.enums import EventType

if TYPE_CHECKING:
    from pathlib import Path


def _make_state_json(jobs_root: Path, short_id: str, **fields: object) -> Path:
    job_dir = jobs_root / short_id
    job_dir.mkdir(parents=True, exist_ok=True)
    state_path = job_dir / "state.json"
    state_path.write_text(json.dumps(fields), encoding="utf-8")
    return state_path


def _init_git_repo(repo_dir: Path, file_content: str = "v0") -> str:
    """Init repo + first commit; returns HEAD commit hash."""
    repo_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q"], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "t@t.com"],
        cwd=repo_dir, check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=repo_dir, check=True, capture_output=True,
    )
    (repo_dir / "f.txt").write_text(file_content)
    subprocess.run(["git", "add", "f.txt"], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "init"],
        cwd=repo_dir, check=True, capture_output=True,
    )
    proc = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_dir, capture_output=True, text=True, check=True,
    )
    return proc.stdout.strip()


# ════════════════════════════════════════════════════════════════════════════════
#  T-Fix.Poll1 — bg terminates without worktree
# ════════════════════════════════════════════════════════════════════════════════


def test_t_fix_poll1_no_worktree_bg_done(tmp_path: Path, monkeypatch) -> None:
    """When state=done + worktreePath always None → poll_loop returns no_worktree_bg_done."""
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    jobs_root = tmp_path / ".claude" / "jobs"
    main_wt = tmp_path / "main"
    _init_git_repo(main_wt)
    _make_state_json(jobs_root, "abc1de2f", state="done", worktreePath=None)
    outcome = poll_loop("abc1de2f", main_wt, timeout_s=2.0, poll_interval_s=0.1)
    assert outcome == "no_worktree_bg_done"


# ════════════════════════════════════════════════════════════════════════════════
#  T-Fix.Poll2 — daemon creates worktree mid-poll → symlink fires
# ════════════════════════════════════════════════════════════════════════════════


def test_t_fix_poll2_symlinked_on_worktree_appear(tmp_path: Path, monkeypatch) -> None:
    """When state.json's worktreePath transitions None → set, poll_loop symlinks .towow."""
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    jobs_root = tmp_path / ".claude" / "jobs"
    main_wt = tmp_path / "main"
    daemon_wt = tmp_path / "daemon_iso"

    _init_git_repo(main_wt)
    (main_wt / ".towow").mkdir()  # poller needs this to create symlink
    _init_git_repo(daemon_wt, file_content="daemon_v1")

    # initial: no worktreePath
    _make_state_json(jobs_root, "abc1de2f", state="working", worktreePath=None)

    # in background thread, after 0.3s, update state.json with worktreePath
    def update_after_delay() -> None:
        time.sleep(0.3)
        _make_state_json(
            jobs_root, "abc1de2f", state="working",
            worktreePath=str(daemon_wt),
        )

    t = threading.Thread(target=update_after_delay)
    t.start()
    outcome = poll_loop("abc1de2f", main_wt, timeout_s=3.0, poll_interval_s=0.1)
    t.join()

    assert outcome == "symlinked"
    assert (daemon_wt / ".towow").is_symlink()
    assert (daemon_wt / ".towow").resolve() == (main_wt / ".towow").resolve()


# ════════════════════════════════════════════════════════════════════════════════
#  T-Fix.Poll3 — state.json never appears
# ════════════════════════════════════════════════════════════════════════════════


def test_t_fix_poll3_missing_state(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    main_wt = tmp_path / "main"
    _init_git_repo(main_wt)
    # don't create jobs/abc1de2f/state.json
    outcome = poll_loop("nonexistent_id", main_wt, timeout_s=1.0, poll_interval_s=0.1)
    assert outcome == "missing_state"


# ════════════════════════════════════════════════════════════════════════════════
#  T-Fix.Poll4 — stale base detection → emit ObligationViolated audit
# ════════════════════════════════════════════════════════════════════════════════


def test_t_fix_poll4_stale_base_emits_obligation_violated(
    tmp_path: Path, monkeypatch,
) -> None:
    """Daemon worktree HEAD differs → raw bytes and canonical readback both retain the audit."""
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    jobs_root = tmp_path / ".claude" / "jobs"
    main_wt = tmp_path / "main"
    daemon_wt = tmp_path / "daemon_iso"

    # init main + bootstrap .towow + events.log
    main_head_v1 = _init_git_repo(main_wt, file_content="v1")
    (main_wt / ".towow").mkdir()
    (main_wt / ".towow" / "events.log").write_text("")

    # init daemon worktree with DIFFERENT commit (stale base)
    daemon_head = _init_git_repo(daemon_wt, file_content="daemon_old_base")
    assert main_head_v1 != daemon_head  # confirm different HEAD

    # state.json with daemon worktree set
    _make_state_json(jobs_root, "abc1de2f", state="working", worktreePath=str(daemon_wt))

    outcome = poll_loop("abc1de2f", main_wt, timeout_s=2.0, poll_interval_s=0.1)
    assert outcome == "symlinked"

    # Verify ObligationViolated event appended to main events.log
    events = (main_wt / ".towow" / "events.log").read_text(encoding="utf-8").strip().splitlines()
    violated = [
        json.loads(line) for line in events
        if json.loads(line).get("payload", {}).get("stub_original_payload", {}).get("kind")
        == "ObligationViolated"
    ]
    assert len(violated) >= 1
    v = violated[-1]
    desc = v["payload"]["stub_original_payload"]["violation_description"]
    assert daemon_head[:12] in desc
    assert main_head_v1[:12] in desc

    # A raw JSON line is only a filesystem effect. The audit trail is accepted only
    # when a fresh canonical reader can validate and return the writer-stamped record.
    canonical = EventLog(main_wt / ".towow" / "events.log")
    visible = [
        record
        for record in canonical.get_events_by_type(EventType.NODE_TOUCHED)
        if record.payload.get("stub_original_payload", {}).get("kind")
        == "ObligationViolated"
    ]
    assert len(visible) == 1
    assert visible[0].sequence_number >= 0
    assert visible[0].record_hash


def test_t_fix_poll4_same_base_no_violation(tmp_path: Path, monkeypatch) -> None:
    """Daemon worktree HEAD == main HEAD → no ObligationViolated emitted."""
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    jobs_root = tmp_path / ".claude" / "jobs"
    main_wt = tmp_path / "main"

    main_head = _init_git_repo(main_wt)
    (main_wt / ".towow").mkdir()
    (main_wt / ".towow" / "events.log").write_text("")

    # daemon worktree is the SAME git repo (linked worktree, same HEAD)
    daemon_wt_dir = tmp_path / "daemon_same"
    subprocess.run(
        ["git", "worktree", "add", str(daemon_wt_dir), "-b", "test-branch"],
        cwd=main_wt, check=True, capture_output=True,
    )
    daemon_head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=daemon_wt_dir,
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    assert main_head == daemon_head

    _make_state_json(jobs_root, "abc1de2f", state="working", worktreePath=str(daemon_wt_dir))

    outcome = poll_loop("abc1de2f", main_wt, timeout_s=2.0, poll_interval_s=0.1)
    assert outcome == "symlinked"

    events = (main_wt / ".towow" / "events.log").read_text(encoding="utf-8").strip()
    # main events.log should be empty (no ObligationViolated)
    assert events == ""
