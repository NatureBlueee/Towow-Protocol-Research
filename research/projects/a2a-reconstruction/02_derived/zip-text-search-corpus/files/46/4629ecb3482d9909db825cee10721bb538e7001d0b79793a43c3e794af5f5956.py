from __future__ import annotations

import hashlib
import json
import os
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return value


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    with temp.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
    os.replace(temp, path)


@dataclass
class CaseStore:
    root: Path

    @classmethod
    def create(cls, root: Path, title: str, case_id: str | None = None) -> "CaseStore":
        root.mkdir(parents=True, exist_ok=False)
        for relative in ("private", "shared/relation/versions", "outputs"):
            (root / relative).mkdir(parents=True, exist_ok=True)
        case = {
            "case_id": case_id or f"case-{uuid4().hex[:12]}",
            "title": title,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "instrument_version": "0.5.0",
            "research_only": True,
            "security_notice": "This fieldkit is not encrypted and is not a production legal or security control.",
            "parties": {},
            "current_relation_version": None,
        }
        write_json(root / "case.json", case)
        (root / "shared/events.jsonl").touch()
        return cls(root)

    @classmethod
    def open(cls, root: Path) -> "CaseStore":
        if not (root / "case.json").exists():
            raise FileNotFoundError(f"Not a Towow case directory: {root}")
        return cls(root)

    @property
    def case_path(self) -> Path:
        return self.root / "case.json"

    def case(self) -> dict[str, Any]:
        return read_json(self.case_path)

    def update_case(self, value: dict[str, Any]) -> None:
        write_json(self.case_path, value)

    def add_party(self, party_id: str, label: str, authority_root: str, contact_ref: str | None = None) -> None:
        case = self.case()
        parties = case.setdefault("parties", {})
        if party_id in parties:
            raise ValueError(f"Party already exists: {party_id}")
        parties[party_id] = {
            "label": label,
            "authority_root": authority_root,
            "contact_ref": contact_ref,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.update_case(case)
        (self.root / "private" / party_id).mkdir(parents=True, exist_ok=True)

    def set_private_intake(self, party_id: str, intake: dict[str, Any]) -> Path:
        case = self.case()
        if party_id not in case.get("parties", {}):
            raise ValueError(f"Unknown party: {party_id}")
        path = self.root / "private" / party_id / "intake.json"
        write_json(path, intake)
        return path

    def issue_mandate(self, party_id: str, mandate: dict[str, Any]) -> Path:
        case = self.case()
        if party_id not in case.get("parties", {}):
            raise ValueError(f"Unknown party: {party_id}")
        mandate = dict(mandate)
        mandate.setdefault("mandate_id", f"mandate-{uuid4().hex[:12]}")
        mandate.setdefault("party_id", party_id)
        mandate.setdefault("issued_at", datetime.now(timezone.utc).isoformat())
        mandate.setdefault("status", "ACTIVE")
        path = self.root / "private" / party_id / f"{mandate['mandate_id']}.json"
        write_json(path, mandate)
        return path

    def add_relation_version(self, relation: dict[str, Any]) -> Path:
        case = self.case()
        relation = dict(relation)
        relation.setdefault("relation_id", case["case_id"])
        relation.setdefault("version", self._next_relation_version())
        relation.setdefault("created_at", datetime.now(timezone.utc).isoformat())
        relation.setdefault("status", "FORMING")
        relation["content_hash"] = sha256_json({k: v for k, v in relation.items() if k != "content_hash"})
        filename = f"v{int(relation['version']):04d}.json"
        path = self.root / "shared" / "relation" / "versions" / filename
        write_json(path, relation)
        write_json(self.root / "shared" / "relation" / "current.json", relation)
        case["current_relation_version"] = int(relation["version"])
        self.update_case(case)
        self.append_event(
            event_type="RELATION_VERSION_CREATED",
            actor="research_instrument",
            payload={"version": relation["version"], "content_hash": relation["content_hash"]},
            relation_version=int(relation["version"]),
        )
        return path

    def current_relation(self) -> dict[str, Any]:
        return read_json(self.root / "shared" / "relation" / "current.json")

    def _next_relation_version(self) -> int:
        current = self.case().get("current_relation_version")
        return 1 if current is None else int(current) + 1

    def _last_event_hash(self) -> str | None:
        path = self.root / "shared" / "events.jsonl"
        if not path.exists():
            return None
        last = None
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    last = json.loads(line)
        return None if last is None else str(last.get("event_hash"))

    def append_event(
        self,
        *,
        event_type: str,
        actor: str,
        payload: dict[str, Any],
        relation_version: int | None = None,
        authority_ref: str | None = None,
    ) -> dict[str, Any]:
        event = {
            "event_id": f"evt-{uuid4().hex}",
            "event_type": event_type,
            "actor": actor,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "relation_version": relation_version,
            "authority_ref": authority_ref,
            "payload": payload,
            "prev_hash": self._last_event_hash(),
        }
        event["event_hash"] = sha256_json(event)
        with (self.root / "shared" / "events.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(canonical_json(event) + "\n")
        return event

    def record_adjudication(self, adjudication: dict[str, Any]) -> Path:
        """Store an independent outcome adjudication and anchor it in the event log."""
        value = dict(adjudication)
        value.setdefault("adjudication_id", f"adj-{uuid4().hex[:12]}")
        value.setdefault("recorded_at", datetime.now(timezone.utc).isoformat())
        path = self.root / "outputs" / f"{value['adjudication_id']}.json"
        write_json(path, value)
        self.append_event(
            event_type="OUTCOME_ADJUDICATED",
            actor=str(value.get("adjudicator_id", "independent_adjudicator")),
            payload={
                "adjudication_id": value["adjudication_id"],
                "stable_disposition": value.get("stable_disposition"),
                "confidence": value.get("confidence"),
                "source_hash": sha256_json(value),
            },
            relation_version=self.case().get("current_relation_version"),
        )
        return path

    def export_redacted(self, destination: Path) -> Path:
        """Export shared and output artifacts without private intakes or mandates.

        This is a convenience function for research review, not a de-identification
        guarantee. The caller must inspect free text before external disclosure.
        """
        if destination.exists():
            raise FileExistsError(destination)
        destination.mkdir(parents=True)
        shutil.copy2(self.case_path, destination / "case.json")
        shutil.copytree(self.root / "shared", destination / "shared")
        shutil.copytree(self.root / "outputs", destination / "outputs")
        notice = {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "source_case_id": self.case().get("case_id"),
            "excluded": ["private/"],
            "warning": "Free-text shared artifacts may still contain identifying information; human review is required.",
        }
        write_json(destination / "REDACTION_NOTICE.json", notice)
        return destination

    def validate(self) -> dict[str, Any]:
        errors: list[str] = []
        warnings: list[str] = []
        case = self.case()
        if not case.get("parties"):
            warnings.append("No parties have been registered.")
        events_path = self.root / "shared" / "events.jsonl"
        previous: str | None = None
        event_count = 0
        if events_path.exists():
            with events_path.open("r", encoding="utf-8") as handle:
                for line_number, line in enumerate(handle, start=1):
                    if not line.strip():
                        continue
                    event_count += 1
                    try:
                        event = json.loads(line)
                    except json.JSONDecodeError as exc:
                        errors.append(f"events.jsonl:{line_number}: invalid JSON: {exc}")
                        continue
                    stored_hash = event.pop("event_hash", None)
                    calculated = sha256_json(event)
                    if stored_hash != calculated:
                        errors.append(f"events.jsonl:{line_number}: hash mismatch")
                    if event.get("prev_hash") != previous:
                        errors.append(f"events.jsonl:{line_number}: broken previous hash")
                    previous = stored_hash
        relation_version = case.get("current_relation_version")
        if relation_version is not None:
            current_path = self.root / "shared" / "relation" / "current.json"
            if not current_path.exists():
                errors.append("case.json names a current relation version, but current.json is missing")
            else:
                current = read_json(current_path)
                if int(current.get("version", -1)) != int(relation_version):
                    errors.append("current relation version disagrees with case.json")
                stored_content_hash = current.get("content_hash")
                hash_input = {k: v for k, v in current.items() if k != "content_hash"}
                if stored_content_hash != sha256_json(hash_input):
                    errors.append("current relation content hash mismatch")
                version_path = self.root / "shared" / "relation" / "versions" / f"v{int(relation_version):04d}.json"
                if not version_path.exists():
                    errors.append("current relation version file is missing")
                elif read_json(version_path) != current:
                    errors.append("current relation differs from its versioned file")
        return {
            "valid": not errors,
            "errors": errors,
            "warnings": warnings,
            "event_count": event_count,
            "party_count": len(case.get("parties", {})),
            "current_relation_version": relation_version,
        }

    def metrics(self) -> dict[str, Any]:
        events: list[dict[str, Any]] = []
        with (self.root / "shared" / "events.jsonl").open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    events.append(json.loads(line))
        counts: dict[str, int] = {}
        for event in events:
            key = str(event.get("event_type", "UNKNOWN"))
            counts[key] = counts.get(key, 0) + 1
        formation_types = {
            "PROBE_REQUESTED",
            "PROBE_RESULT",
            "REFUSAL",
            "COUNTERCONDITION",
            "CAPABILITY_PATH_FORMED",
            "RELATION_VERSION_CREATED",
        }
        reality_types = {"OPERATION_ATTEMPT", "EFFECT_WITNESSED", "ADOPTION_RECORDED", "ACCEPTANCE_STANCE"}
        human_minutes = 0.0
        sensitive_disclosure_units = 0.0
        elapsed_seconds = 0.0
        disposition_counts: dict[str, int] = {}
        for event in events:
            payload = event.get("payload", {})
            if not isinstance(payload, dict):
                continue
            human_minutes += float(payload.get("human_minutes", 0) or 0)
            sensitive_disclosure_units += float(payload.get("sensitive_disclosure_units", 0) or 0)
            elapsed_seconds += float(payload.get("elapsed_seconds", 0) or 0)
            disposition = payload.get("disposition") or payload.get("stable_disposition")
            if disposition:
                key = str(disposition)
                disposition_counts[key] = disposition_counts.get(key, 0) + 1
        return {
            "case_id": self.case().get("case_id"),
            "event_count": len(events),
            "event_types": counts,
            "formation_event_count": sum(counts.get(item, 0) for item in formation_types),
            "reality_event_count": sum(counts.get(item, 0) for item in reality_types),
            "relation_versions": self.case().get("current_relation_version") or 0,
            "explicit_human_minutes": human_minutes,
            "explicit_sensitive_disclosure_units": sensitive_disclosure_units,
            "explicit_elapsed_seconds": elapsed_seconds,
            "disposition_mentions": disposition_counts,
            "note": "Only explicitly recorded numeric fields are summed; the instrument never infers human effort or disclosure from text length.",
        }
