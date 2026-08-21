from __future__ import annotations

import hashlib
import json
import pathlib
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from evaluator import evaluate_causal, evaluate_legacy
from runtime import sha256_value


ARTIFACT = (
    ROOT
    / "artifacts"
    / "ct001-p-13664338600513123180"
    / "causal-twin.json"
)
FILE_SHA256 = "7de4254bec29438f24aeb5ce89c7340d86aeb794465ba3a1845085447169d472"
PAIR_SHA256 = "2733544ee9e29f1b8bb54957ce9d2a14d3f37acd7eab839a8d5c1e8e2ddfadc6"


def test_accepted_actual_artifact_recomputes_to_frozen_result():
    raw = ARTIFACT.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == FILE_SHA256
    pair = json.loads(raw)

    unsigned_pair = dict(pair)
    assert unsigned_pair.pop("pair_sha256") == PAIR_SHA256
    assert sha256_value(unsigned_pair) == PAIR_SHA256
    assert pair["state_projection_hash_equal"] is True
    assert pair["pre_decision_alpha_shape_equal"] is True

    for world_id, world in pair["worlds"].items():
        unsigned_world = dict(world)
        supplied_world_sha256 = unsigned_world.pop("bundle_sha256")
        assert sha256_value(unsigned_world) == supplied_world_sha256
        assert evaluate_legacy(world) == pair["legacy_evaluations"][world_id]
        assert evaluate_causal(world) == pair["causal_evaluations"][world_id]

    assert pair["legacy_evaluations"]["W_G"]["disposition"] == "SUCCEEDED"
    assert pair["legacy_evaluations"]["W_F"]["disposition"] == "SUCCEEDED"
    assert pair["causal_evaluations"]["W_G"]["DirectCausalActor"] == "A4"
    assert pair["causal_evaluations"]["W_G"]["disposition"] == "SUCCEEDED"
    assert pair["causal_evaluations"]["W_F"]["DirectCausalActor"] == "HELPER"
    assert (
        pair["causal_evaluations"]["W_F"]["disposition"]
        == "MATCHING_STATE_EXTERNAL_CAUSE"
    )
