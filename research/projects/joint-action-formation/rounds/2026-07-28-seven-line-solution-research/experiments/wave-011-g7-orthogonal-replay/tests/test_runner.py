from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import private_oracle  # noqa: E402
import runner  # noqa: E402


class RunnerIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = runner.load_public_fixture()
        cls.worlds = {
            world["world_id"]: world for world in cls.fixture["worlds"]
        }

    def test_runner_never_imports_or_opens_private_oracle(self) -> None:
        source = (ROOT / "runner.py").read_text(encoding="utf-8")
        executable = "\n".join(
            line for line in source.splitlines() if not line.lstrip().startswith("#")
        )
        self.assertNotIn("import private_oracle", executable)
        self.assertNotIn("private_oracle.json", executable)

    def test_six_worker_sources_are_distinct_and_do_not_import_each_other(self) -> None:
        identities = {
            method: runner._worker_identity(path)
            for method, path in runner.WORKERS.items()
        }
        hashes = {identity["source_sha256"] for identity in identities.values()}
        self.assertEqual(len(hashes), 6)
        for path in runner.WORKERS.values():
            source = path.read_text(encoding="utf-8")
            self.assertNotIn("from workers", source)
            self.assertNotIn("import workers", source)
            self.assertNotIn("private_oracle", source)

    def test_no_dispatch_and_uncertain_effect_execute_different_paths(self) -> None:
        no_dispatch = runner.run_world(self.worlds["w003"], "MATURE")
        uncertain = runner.run_world(self.worlds["w004"], "MATURE")
        self.assertIsNone(no_dispatch["effect_readback"])
        self.assertIsNotNone(uncertain["effect_readback"])
        self.assertNotEqual(
            no_dispatch["final_action"], uncertain["final_action"]
        )

    def test_old_runtime_restart_is_fenced(self) -> None:
        record = runner.run_world(self.worlds["w017"], "MATURE")
        self.assertTrue(record["old_runtime_fenced"])
        restart = record["migration"]["old_runtime_restart"]
        self.assertIsNotNone(restart)
        # The caller sees only a lost response.  The effector's independent
        # ledger is the authoritative proof that the old epoch did not commit.
        dispatches = [
            entry["payload"]["receipt"]
            for entry in record["provider_ledgers"]["effector"]
            if entry["event"] == "DISPATCH"
        ]
        self.assertGreaterEqual(len(dispatches), 2)
        self.assertFalse(dispatches[-1]["committed"])
        self.assertEqual(dispatches[-1]["outcome"], "FENCED_OR_DENIED")

    def test_capsule_field_drop_fails_closed(self) -> None:
        record = runner.run_world(self.worlds["w018"], "MATURE")
        self.assertFalse(record["migration"]["imported"])
        self.assertEqual(record["final_action"], "BOUNDED_UNKNOWN")
        grade = private_oracle.grade_run("w018", record)
        self.assertFalse(grade["checks"]["migration_capsule"])
        self.assertIn(
            "missing migration fields: acceptance_records,compensation_obligations",
            grade["capsule_violations"],
        )

    def test_only_explicit_delegation_enters_delegated_stratum(self) -> None:
        delegated = runner.run_world(self.worlds["w001"], "DELEGATED_CENTER")
        independent = runner.run_world(self.worlds["w002"], "DELEGATED_CENTER")
        self.assertEqual(
            delegated["authority_stratum"], "LEGITIMATELY_DELEGATED"
        )
        self.assertEqual(
            independent["authority_stratum"], "INDEPENDENT_AUTHORITY"
        )
        self.assertEqual(delegated["final_action"], "CONTINUE")
        self.assertEqual(independent["final_action"], "BLOCK")

    def test_saved_results_are_bound_to_current_fixture(self) -> None:
        results = json.loads((ROOT / "results.json").read_text(encoding="utf-8"))
        # The full saved replay is regenerated after fixture or worker changes;
        # this test catches stale result artifacts.
        self.assertEqual(
            results["raw_runner"]["summary"]["fixture_sha256"],
            runner.digest(self.fixture),
        )


if __name__ == "__main__":
    unittest.main()
