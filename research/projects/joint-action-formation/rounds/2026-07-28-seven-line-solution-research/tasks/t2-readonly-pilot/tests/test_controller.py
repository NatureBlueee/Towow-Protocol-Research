from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


TASK_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TASK_ROOT))

import controller  # noqa: E402


def load_json(relative_path: str) -> dict:
    return json.loads((TASK_ROOT / relative_path).read_text(encoding="utf-8"))


def valid_query(
    *,
    authority_id: str = "BUYER-DATA",
    request_type: str = "REQUEST_MINIMAL_COUNTERCONDITION",
) -> dict:
    return {
        "authority_id": authority_id,
        "request_type": request_type,
        "purpose": "determine whether a value-preserving next step exists",
        "relation_version_ref": "REL-T2-V1",
        "retention_scope": "RUN_ONLY",
    }


def batch(
    queries: list,
    *,
    method_id: str = "METHOD-A",
    run_id: str = "RUN-1",
    round_number: int = 1,
    previous_round_hash: str | None = None,
) -> dict:
    return {
        "schema_version": "1.0",
        "task_id": controller.TASK_ID,
        "method_id": method_id,
        "run_id": run_id,
        "round": round_number,
        "previous_round_hash": previous_round_hash,
        "queries": queries,
    }


class ControllerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.blind = load_json("blind/input.json")
        self.oracle = load_json("oracle/truth.json")

    def run_batch(self, value: dict, state: dict | None = None) -> tuple[dict, dict]:
        state = controller.initial_state() if state is None else state
        output = controller.process_batch(
            value,
            state,
            blind=self.blind,
            oracle=self.oracle,
        )
        return output, state

    def test_legal_query_returns_only_allowlisted_minimum_and_receipt(self) -> None:
        output, state = self.run_batch(batch([valid_query()]))
        result = output["results"][0]

        self.assertEqual(result["decision"], "DISCLOSE")
        self.assertEqual(result["response_type"], "COUNTERCONDITION")
        self.assertEqual(set(result["disclosed_fields"]), {"conditions"})
        self.assertEqual(
            result["receipt"]["disclosed_fields"],
            ["conditions"],
        )
        self.assertEqual(len(result["receipt"]["receipt_hash"]), 64)
        self.assertEqual(len(output["round_hash"]), 64)
        self.assertEqual(len(output["history_hash"]), 64)

        run = next(iter(state["runs"].values()))
        self.assertEqual(len(run["rounds"]), 1)
        self.assertEqual(
            run["rounds"][0]["output"]["round_hash"],
            output["round_hash"],
        )

    def test_unknown_authority_unknown_request_and_wrong_authority_are_refused(
        self,
    ) -> None:
        queries = [
            valid_query(authority_id="UNKNOWN-AUTHORITY"),
            valid_query(request_type="REQUEST_PRIVATE_STATE_DUMP"),
            valid_query(
                authority_id="BUYER-BUSINESS",
                request_type="REQUEST_MINIMAL_COUNTERCONDITION",
            ),
        ]
        output, _ = self.run_batch(batch(queries))
        results = output["results"]

        self.assertEqual(
            [item["decision"] for item in results],
            ["REFUSE", "REFUSE", "REFUSE"],
        )
        self.assertEqual(
            [item["reason_code"] for item in results],
            [
                "UNKNOWN_AUTHORITY",
                "UNKNOWN_REQUEST_TYPE",
                "REQUEST_NOT_ALLOWED_FOR_AUTHORITY",
            ],
        )
        for item in results:
            self.assertEqual(item["disclosed_fields"], {})
            self.assertEqual(item["receipt"]["disclosed_fields"], [])

    def test_duplicate_query_does_not_disclose_twice(self) -> None:
        query = valid_query()
        output, _ = self.run_batch(batch([query, dict(query)]))
        first, duplicate = output["results"]

        self.assertEqual(first["decision"], "DISCLOSE")
        self.assertEqual(duplicate["decision"], "REPLAY")
        self.assertEqual(duplicate["response_type"], "REPLAY")
        self.assertEqual(duplicate["disclosed_fields"], {})
        self.assertEqual(
            duplicate["replay_of_receipt_id"],
            first["receipt"]["receipt_id"],
        )
        self.assertEqual(duplicate["response_hash"], first["response_hash"])

    def test_exact_round_replay_is_idempotent_and_conflict_is_rejected(self) -> None:
        value = batch([valid_query()])
        state = controller.initial_state()
        first, state = self.run_batch(value, state)
        replay, state = self.run_batch(value, state)

        self.assertEqual(replay, first)
        run = next(iter(state["runs"].values()))
        self.assertEqual(len(run["rounds"]), 1)

        conflict = batch(
            [
                valid_query(
                    authority_id="BUYER-BUSINESS",
                    request_type="CLARIFY_ACCEPTANCE",
                )
            ]
        )
        with self.assertRaisesRegex(
            controller.ControllerError,
            "conflicting replay",
        ):
            self.run_batch(conflict, state)

    def test_response_behavior_is_fixed_across_methods(self) -> None:
        query = valid_query(
            authority_id="PROVIDER-TECH",
            request_type="REQUEST_CAPABILITY_EVIDENCE",
        )
        output_a, _ = self.run_batch(
            batch([query], method_id="METHOD-A", run_id="RUN-A")
        )
        output_b, _ = self.run_batch(
            batch([query], method_id="METHOD-B", run_id="RUN-B")
        )
        result_a = output_a["results"][0]
        result_b = output_b["results"][0]

        for field in (
            "decision",
            "response_type",
            "disclosed_fields",
            "reason_code",
            "response_hash",
        ):
            self.assertEqual(result_a[field], result_b[field])

    def test_second_round_requires_hash_chain_and_replays_prior_query(self) -> None:
        query = valid_query()
        first, state = self.run_batch(batch([query]))
        second_batch = batch(
            [query],
            round_number=2,
            previous_round_hash=first["round_hash"],
        )
        second, state = self.run_batch(second_batch, state)

        self.assertEqual(second["previous_round_hash"], first["round_hash"])
        self.assertEqual(second["results"][0]["decision"], "REPLAY")
        self.assertNotEqual(second["round_hash"], first["round_hash"])
        self.assertNotEqual(second["history_hash"], first["history_hash"])

        bad_chain = batch(
            [valid_query(request_type="REQUEST_DATA_PURPOSE_BOUNDARY")],
            round_number=3,
            previous_round_hash="0" * 64,
        )
        with self.assertRaisesRegex(
            controller.ControllerError,
            "previous_round_hash",
        ):
            self.run_batch(bad_chain, state)

    def test_malformed_query_is_refused_without_hidden_diagnostics(self) -> None:
        malformed = {**valid_query(), "unexpected": "field"}
        output, _ = self.run_batch(batch([malformed]))
        result = output["results"][0]

        self.assertEqual(result["decision"], "REFUSE")
        self.assertEqual(result["reason_code"], "MALFORMED_QUERY")
        self.assertEqual(result["disclosed_fields"], {})

    def test_unbounded_retention_is_refused(self) -> None:
        query = {**valid_query(), "retention_scope": "FOREVER"}
        output, _ = self.run_batch(batch([query]))
        result = output["results"][0]

        self.assertEqual(result["decision"], "REFUSE")
        self.assertEqual(result["reason_code"], "RETENTION_SCOPE_NOT_ALLOWED")
        self.assertEqual(result["disclosed_fields"], {})

    def test_solver_response_does_not_expose_hidden_names_or_paths(self) -> None:
        output, _ = self.run_batch(
            batch(
                [
                    valid_query(),
                    valid_query(request_type="REQUEST_PRIVATE_STATE_DUMP"),
                ]
            )
        )
        serialized = json.dumps(output, ensure_ascii=False, sort_keys=True)
        for forbidden in (
            "oracle/truth.json",
            "private_local_states_at_s0",
            "reference_relation_v2",
            "pseudo_success_mutations",
            "source_closure",
            "04_示例案例_企业AI只读试点.md",
        ):
            self.assertNotIn(forbidden, serialized)

    def test_blind_payload_and_method_visible_schemas_do_not_contain_answers(
        self,
    ) -> None:
        visible_paths = [
            "blind/input.json",
            "evaluator/spec.json",
            "schemas/query-batch.schema.json",
            "schemas/final-submission.schema.json",
        ]
        visible_text = "\n".join(
            (TASK_ROOT / path).read_text(encoding="utf-8")
            for path in visible_paths
        )
        for forbidden in (
            "REL-T2-V2-REFERENCE",
            "PROBE-T2-REF-1",
            "buyer_controlled_sandbox",
            "raw_row_export_count_is_zero",
            "T2-ENTERPRISE-PILOT-ORACLE-V1",
            "04_示例案例_企业AI只读试点.md",
        ):
            self.assertNotIn(forbidden, visible_text)

        manifest = load_json("manifest.json")
        self.assertEqual(
            manifest["solver_payload_allowlist"],
            [
                "blind/input.json",
                "evaluator/spec.json",
                "schemas/query-batch.schema.json",
                "schemas/final-submission.schema.json",
            ],
        )
        self.assertNotIn("controller.py", manifest["solver_payload_allowlist"])

    def test_manifest_artifact_hashes(self) -> None:
        manifest = load_json("manifest.json")
        for artifact in manifest["artifacts"]:
            path = TASK_ROOT / artifact["path"]
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertEqual(actual, artifact["sha256"], artifact["path"])

    def test_cli_persists_state_and_replays_round_idempotently(self) -> None:
        value = batch([valid_query()])
        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary = Path(temporary_directory)
            input_path = temporary / "query.json"
            state_path = temporary / "controller-state.json"
            input_path.write_text(
                json.dumps(value, ensure_ascii=False),
                encoding="utf-8",
            )
            command = [
                sys.executable,
                str(TASK_ROOT / "controller.py"),
                "--input",
                str(input_path),
                "--state",
                str(state_path),
            ]
            first = subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
            )
            replay = subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
            )

            self.assertEqual(json.loads(replay.stdout), json.loads(first.stdout))
            persisted = json.loads(state_path.read_text(encoding="utf-8"))
            run = next(iter(persisted["runs"].values()))
            self.assertEqual(len(run["rounds"]), 1)


if __name__ == "__main__":
    unittest.main()
