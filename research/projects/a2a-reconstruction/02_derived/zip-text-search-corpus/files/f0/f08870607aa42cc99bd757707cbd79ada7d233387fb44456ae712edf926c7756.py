"""Held-out executable checks for the A2A-proposed null-source identity class.

These checks intentionally differ from the pre-existing compatibility oracle:
an event with no source may fold historical source-less state, but must not
mutate or satisfy migration for a later source-scoped reference instance.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

from towow.l0.commit_gate.concept_retire_gate import check_concept_retire_migration
from towow.l0.projection.projection import ProjectionStore
from towow.l1.consensus_invalidation import active_references_to
from towow.schemas.enums import (
    ActorType,
    BaseClassification,
    EventCategory,
    EventType,
    SubjectEntityType,
    SubjectRole,
)
from towow.schemas.event_intent import Subject, Supersede
from towow.schemas.event_record import EventRecord, Provenance


LOCATOR = "@concept:shared-target@v1"


def _record(seq: int, event_type: EventType, after: dict[str, object]) -> EventRecord:
    return EventRecord(
        event_id=f"evt-{seq}-{uuid.uuid4().hex[:8]}",
        sequence_number=seq,
        timestamp=datetime(2026, 7, 25, tzinfo=UTC),
        record_hash=f"hash-{seq}",
        local_intent_id=f"intent-{seq}",
        event_type=event_type,
        event_category=EventCategory.STATE_TRANSITION,
        payload={"after_state": after},
        provenance=Provenance(actor_type=ActorType.SYSTEM.value, actor_id="r54-evaluator"),
        base_classification=BaseClassification.IMMUTABLE_TRUTH,
        supersede=Supersede(is_supersede=False),
        subjects=[
            Subject(
                entity_type=SubjectEntityType.AT_REFERENCE,
                entity_id=LOCATOR,
                role=SubjectRole.PRIMARY,
            )
        ],
        schema_version="1.0.0",
    )


def _add(seq: int, source: str | None) -> EventRecord:
    after: dict[str, object] = {
        "at_reference": LOCATOR,
        "target_concept_name": "shared-target",
    }
    if source is not None:
        after["source_concept_id"] = source
    return _record(seq, EventType.AT_REFERENCE_ADDED, after)


def _legacy_remove(seq: int) -> EventRecord:
    return _record(seq, EventType.AT_REFERENCE_REMOVED, {"at_reference": LOCATOR})


def test_projection_legacy_removal_cannot_deactivate_sourced_instances(tmp_path: Path) -> None:
    store = ProjectionStore(tmp_path / "graph")
    for record in (
        _add(1, None),
        _add(2, "consumer-a@v1"),
        _add(3, "consumer-b@v1"),
        _legacy_remove(4),
    ):
        store._apply(record)

    graph = store.read("at_reference_graph") or {}
    states = {
        (ref.get("source_concept_id") or None, ref["reference_id"]): ref["is_active"]
        for ref in graph.get("references", [])
    }
    assert states == {
        (None, LOCATOR): False,
        ("consumer-a@v1", LOCATOR): True,
        ("consumer-b@v1", LOCATOR): True,
    }


def test_event_fold_legacy_removal_cannot_erase_sourced_instances(tmp_path: Path) -> None:
    towow_dir = tmp_path / ".towow"
    towow_dir.mkdir()
    records = (_add(1, None), _add(2, "consumer-a@v1"), _add(3, "consumer-b@v1"), _legacy_remove(4))
    (towow_dir / "events.log").write_text(
        "\n".join(record.model_dump_json() for record in records) + "\n",
        encoding="utf-8",
    )

    active = active_references_to(towow_dir, "shared-target@v1")
    assert {
        (ref.get("source_concept_id"), ref.get("at_reference"))
        for ref in active
    } == {
        ("consumer-a@v1", LOCATOR),
        ("consumer-b@v1", LOCATOR),
    }


def test_legacy_removal_is_not_migration_evidence_for_sourced_dependent() -> None:
    retire = SimpleNamespace(
        event_type="ConceptGraphProposal",
        payload={
            "transition_type": "superseded",
            "after_state": {
                "proposed_changes": [
                    {
                        "change_type": "supersede_concept",
                        "entity_type": "concept",
                        "entity_id": "shared-target@v1",
                        "new_value": {"superseded_reason": "retire"},
                    }
                ]
            },
        },
        supersede=SimpleNamespace(is_supersede=True, superseded_event_id="evt-old"),
        subjects=[],
    )
    legacy_removal = SimpleNamespace(
        event_type="AtReferenceRemoved",
        payload={"after_state": {"at_reference": LOCATOR}},
    )
    active_reference = {
        "source_concept_id": "consumer-a@v1",
        "target_concept_name": "shared-target",
        "at_reference": LOCATOR,
        "on_target_supersede_policy": "explicit_decision_required",
    }

    result = check_concept_retire_migration(
        [retire, legacy_removal],
        superseded_concept_resolver=lambda _event_id: None,
        active_references_for=lambda _concept_id: [active_reference],
    )

    assert result.passed is False
    assert result.findings[0].source_concept_id == "consumer-a@v1"
    assert result.findings[0].via == "unmigrated"
