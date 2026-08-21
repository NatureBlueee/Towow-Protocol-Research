"""Process-isolated, signed G2 relation evidence for CE-001.

The controller sees endpoint/source descriptors, public manifests and signed
receipts.  It never loads an owner's private profile or private key.  A
RelationVersion is only a derived snapshot of already verified owner evidence;
it is not an owner act, Authority, Effect, Acceptance, or a green global state.
"""

from __future__ import annotations

import base64
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
from typing import Any
import uuid

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


ROOT = Path(__file__).resolve().parent
AXES = ("constituted", "understood", "claimed", "authorized", "activated")
RELATION_OWNERS = ("O_Q", "O_V", "O_R", "O_S", "O_P")
ALL_OWNERS = RELATION_OWNERS + ("O_E",)
DEFAULT_OBJECT_ID = "Venue-V/Circuit-C7"
DEFAULT_PURPOSE = "CE001_TEMPORARY_POWER_RELATION_FORMATION"
REQUEST_SCHEMA_VERSION = "ce001-g2-request-v3"
OWNER_RECEIPT_SCHEMA_VERSION = "ce001-owner-receipt-v3"
PLATFORM_RECEIPT_SCHEMA_VERSION = "ce001-platform-receipt-v2"
LOCAL_TRUST_CLASS = "LOCAL_SYNTHETIC_EPHEMERAL_SELF_KEY"
PLATFORM_LOCAL_ASSERTION = "LOCAL_FIXTURE_SELF_ASSERTION_VERIFIED"
REQUEST_TTL_SECONDS = 30
REQUEST_KEYS = {
    "request_schema_version",
    "query_id",
    "run_id",
    "episode_id",
    "request_ordinal",
    "process_ordinal",
    "request_nonce",
    "issued_at",
    "expires_at",
    "owner_id",
    "endpoint_binding",
    "kind",
    "q",
    "object_id",
    "purpose",
    "relation_revision",
    "relation_revision_hash",
    "relation_version_hash",
    "relation_schema_hash",
    "scope",
    "operation_ids",
    "request_payload",
}
OWNER_RESPONSE_KINDS = {
    "PRIVATE_COLUMN": {
        "PRIVATE_COLUMN_ABSENT",
        "PRIVATE_COLUMN_WITHHELD",
        "PRIVATE_COLUMN_DISCLOSED",
        "PRIVATE_COLUMN_UNKNOWN",
    },
    "CONSTITUTE": {"CONSTITUTE", "REFUSE", "UNKNOWN"},
    "EXPLAIN_BACK": {"EXPLAIN_BACK", "REFUSE", "UNKNOWN"},
    "CLAIM": {"CLAIM", "CLAIM_WITH_OPPOSITION", "REFUSE", "UNKNOWN"},
    "AUTHORIZE": {"AUTHORIZE", "REFUSE", "UNKNOWN"},
    "ACTIVATE": {"ACTIVATE", "REFUSE", "UNKNOWN"},
}
PLATFORM_RESPONSE_KINDS = {
    "CAPABILITY_PROOF": {"CAPABILITY_PROOF"},
    "CAPABILITY_READBACK": {"CAPABILITY_READBACK"},
}
DEFAULT_Q_STATEMENT = (
    "T0+90min前为Venue V/Circuit C7提供至少45分钟3kW±5%临时供电；"
    "满足噪声、安全、exact-target限制且不得给其他线路送电"
)
BASE_SCHEMA = {
    "roles": ["REQUESTER", "VENUE"],
    "actions": ["REQUEST_TEMPORARY_POWER"],
    "evidence": ["Q_VERSION"],
    "evaluation": ["EXACT_C7", "3KW_PLUS_MINUS_5_PERCENT", "45_MINUTES"],
    "exit": ["REFUSE_BEFORE_ACTIVATION"],
    "constraints": ["NO_OTHER_CIRCUIT"],
}
E2_SCHEMA = {
    "roles": ["REQUESTER", "VENUE", "RESOURCE_PROVIDER", "SAFETY_APPROVER", "PAYER"],
    "actions": [
        "REQUEST_TEMPORARY_POWER",
        "SUPPLY_C7",
        "APPROVE_C7_CONNECTION",
        "AUTHORIZE_PAYMENT",
    ],
    "evidence": ["Q_VERSION", "PURPOSE_TOKEN", "SAFETY_APPROVAL", "TARGET_BINDING"],
    "evaluation": ["EXACT_C7", "3KW_PLUS_MINUS_5_PERCENT", "45_MINUTES"],
    "exit": ["REFUSE_BEFORE_ACTIVATION", "REVOKE_BEFORE_EFFECT"],
    "constraints": ["NO_OTHER_CIRCUIT", "BATTERY_ONLY_AT_VENUE"],
}


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def canonical(value: Any) -> str:
    return canonical_bytes(value).decode("utf-8")


def digest(value: Any) -> str:
    return sha256(canonical_bytes(value)).hexdigest()


def hash_bytes(raw: bytes) -> str:
    return sha256(raw).hexdigest()


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_text(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_utc(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ReceiptVerificationError(f"{field} must be an explicit UTC Z timestamp")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ReceiptVerificationError(f"{field} is not a valid timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise ReceiptVerificationError(f"{field} must be UTC")
    return parsed


def endpoint_binding(manifest: dict[str, Any]) -> dict[str, Any]:
    """Freeze the actual spawned endpoint and its explicitly local trust class."""

    value = {
        "owner_id": manifest["owner_id"],
        "pid": manifest["pid"],
        "process_instance_id": manifest["process_instance_id"],
        "key_id": manifest["key_id"],
        "public_key_b64": manifest["public_key_b64"],
        "source": manifest["source"],
        "profile_source": manifest["profile_source"],
        "endpoint_id": manifest.get("endpoint_id"),
        "endpoint_descriptor_sha256": manifest.get("endpoint_descriptor_sha256"),
        "evidence_origin": manifest.get("evidence_origin"),
        "trust_anchor_status": manifest.get("trust_anchor_status"),
    }
    return {"value": value, "sha256": digest(value)}


def schema_delta(before: dict[str, list[str]], after: dict[str, list[str]]) -> dict[str, Any]:
    fields: dict[str, Any] = {}
    for key in sorted(set(before) | set(after)):
        old = set(before.get(key, []))
        new = set(after.get(key, []))
        added = sorted(new - old)
        removed = sorted(old - new)
        if added or removed:
            fields[key] = {"added": added, "removed": removed}
    return {
        "changed_fields": fields,
        "material": any(
            key in fields
            for key in ("roles", "actions", "evidence", "evaluation", "exit", "constraints")
        ),
    }


class ReceiptVerificationError(ValueError):
    """A signature, byte, identity or exact-binding check failed."""


class ProcessProtocolError(RuntimeError):
    """A worker failed to return a valid JSON-lines protocol response."""


@dataclass
class VerificationState:
    last_request_ordinal: int = 0
    process_ordinals: dict[str, int] | None = None
    consumed_query_ids: set[str] | None = None
    consumed_nonces: set[str] | None = None
    consumed_request_hashes: set[str] | None = None

    def __post_init__(self) -> None:
        if self.process_ordinals is None:
            self.process_ordinals = {}
        if self.consumed_query_ids is None:
            self.consumed_query_ids = set()
        if self.consumed_nonces is None:
            self.consumed_nonces = set()
        if self.consumed_request_hashes is None:
            self.consumed_request_hashes = set()


class Trace:
    def __init__(self, episode_id: str, run_id: str = "interactive") -> None:
        self.episode_id = episode_id
        self.run_id = run_id
        self.records: list[dict[str, Any]] = []

    def add(self, event: str, **payload: Any) -> None:
        self.records.append(
            {
                "seq": len(self.records) + 1,
                "run_id": self.run_id,
                "episode_id": self.episode_id,
                "event": event,
                **payload,
            }
        )


def _q_from_config(config: dict[str, Any]) -> dict[str, str]:
    if "q" in config:
        q = dict(config["q"])
    else:
        q = {
            "id": "CE001-Q",
            "version": config.get("q_version", "Q@v1"),
            "statement": config.get("q_statement", DEFAULT_Q_STATEMENT),
        }
    supplied_hash = q.pop("hash", None)
    computed = digest(q)
    if supplied_hash is not None and supplied_hash != computed:
        raise ReceiptVerificationError("Q hash does not match exact Q bytes")
    q["hash"] = computed
    return q


def _resolve_endpoint_document(config: dict[str, Any]) -> tuple[dict[str, Any], Path]:
    if "owner_profiles" in config:
        raise ValueError("controller-visible owner_profiles are forbidden; use endpoint descriptors")
    descriptor_name = config.get("endpoint_manifest", "endpoints.json")
    path = Path(descriptor_name)
    if not path.is_absolute():
        path = ROOT / "fixtures" / path
    document = json.loads(path.read_text(encoding="utf-8"))
    return document, path.resolve()


def _resolved_descriptor(raw: dict[str, Any], manifest_path: Path) -> dict[str, Any]:
    descriptor = dict(raw)
    for field in ("worker_source", "profile_source"):
        path = Path(descriptor[field])
        if not path.is_absolute():
            path = manifest_path.parent / path
        descriptor[field] = str(path.resolve())
    return descriptor


class SignedProcess:
    """Long-lived subprocess with a public ready manifest."""

    def __init__(
        self,
        *,
        descriptor: dict[str, Any],
        profile_case: str,
        owner_id: str,
        platform: bool = False,
    ) -> None:
        self.owner_id = owner_id
        self.descriptor = descriptor
        command = [
            sys.executable,
            descriptor["worker_source"],
            "--profile-source",
            descriptor["profile_source"],
            "--profile-case",
            profile_case,
        ]
        if not platform:
            command.extend(["--owner-id", owner_id])
        self.process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            bufsize=1,
        )
        self.manifest = self._read_message()
        expected_type = "platform_ready" if platform else "owner_ready"
        if self.manifest.get("type") != expected_type:
            self.close()
            raise ProcessProtocolError(f"worker did not become ready: {self.manifest}")
        if self.manifest.get("owner_id") != owner_id:
            self.close()
            raise ProcessProtocolError("ready manifest owner mismatch")
        if self.manifest.get("pid") != self.process.pid:
            self.close()
            raise ReceiptVerificationError(
                "owner process identity collision: manifest PID differs from spawned child PID"
            )
        self.manifest["endpoint_id"] = f"fixture-endpoint:{owner_id}"
        self.manifest["endpoint_descriptor_sha256"] = digest(descriptor)
        worker_raw = Path(descriptor["worker_source"]).read_bytes()
        if self.manifest["source"]["sha256"] != hash_bytes(worker_raw):
            self.close()
            raise ProcessProtocolError("worker source manifest mismatch")
        if (
            self.manifest.get("evidence_origin") != LOCAL_TRUST_CLASS
            or self.manifest.get("trust_anchor_status") != "NOT_ESTABLISHED"
        ):
            self.close()
            raise ReceiptVerificationError(
                "worker must disclose local synthetic ephemeral self-key trust boundary"
            )
        self.issued_count = 0

    def _read_message(self) -> dict[str, Any]:
        assert self.process.stdout is not None
        line = self.process.stdout.readline()
        if not line:
            stderr = self.process.stderr.read() if self.process.stderr else ""
            raise ProcessProtocolError(
                f"worker exited before response rc={self.process.poll()} stderr={stderr}"
            )
        try:
            return json.loads(line)
        except json.JSONDecodeError as exc:
            raise ProcessProtocolError(f"worker returned non-JSON: {line!r}") from exc

    def query(self, request: dict[str, Any], trace: Trace) -> dict[str, Any]:
        if request["owner_id"] != self.owner_id:
            raise ValueError("query owner_id does not match routed owner process")
        raw_request = canonical_bytes(request)
        trace.add(
            "owner_query" if self.owner_id in RELATION_OWNERS else "platform_native_query",
            query_id=request["query_id"],
            owner_id=self.owner_id,
            kind=request["kind"],
            request_raw_bytes_b64=base64.b64encode(raw_request).decode("ascii"),
            request_raw_bytes_sha256=hash_bytes(raw_request),
            routed_process_instance_id=self.manifest["process_instance_id"],
            routed_pid=self.manifest["pid"],
        )
        assert self.process.stdin is not None
        self.process.stdin.write(raw_request.decode("utf-8") + "\n")
        self.process.stdin.flush()
        receipt = self._read_message()
        if receipt.get("type") in {"owner_error", "platform_error"}:
            raise ProcessProtocolError(str(receipt))
        self.issued_count += 1
        trace.add(
            "owner_receipt_received"
            if self.owner_id in RELATION_OWNERS
            else "platform_receipt_received",
            query_id=request["query_id"],
            owner_id=self.owner_id,
            receipt=receipt,
        )
        return receipt

    def close(self) -> dict[str, Any]:
        if self.process.stdin and not self.process.stdin.closed:
            self.process.stdin.close()
        try:
            returncode = self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:  # pragma: no cover - defensive cleanup
            self.process.terminate()
            returncode = self.process.wait(timeout=5)
        stderr = self.process.stderr.read() if self.process.stderr else ""
        if self.process.stdout:
            self.process.stdout.close()
        if self.process.stderr:
            self.process.stderr.close()
        return {
            "owner_id": self.owner_id,
            "pid": self.manifest.get("pid") if hasattr(self, "manifest") else self.process.pid,
            "process_instance_id": self.manifest.get("process_instance_id")
            if hasattr(self, "manifest")
            else None,
            "returncode": returncode,
            "stderr": stderr,
        }


class OwnerDirectory:
    """Descriptor-only owner router.

    Construction does not accept profiles.  `start()` launches one independent
    owner-local process for every requested owner.
    """

    def __init__(
        self,
        descriptors: dict[str, dict[str, Any]] | None = None,
        profile_case: str = "MISSING_ALL",
    ) -> None:
        self.__descriptors = descriptors or {}
        self.__profile_case = profile_case
        self.__processes: dict[str, SignedProcess] = {}

    def start(self) -> None:
        try:
            for owner_id in RELATION_OWNERS:
                if owner_id not in self.__descriptors:
                    raise ValueError(f"missing endpoint descriptor: {owner_id}")
                self.__processes[owner_id] = SignedProcess(
                    descriptor=self.__descriptors[owner_id],
                    profile_case=self.__profile_case,
                    owner_id=owner_id,
                )
            manifests = self.manifests()
            for field in ("pid", "process_instance_id", "key_id", "public_key_b64"):
                values = [manifest.get(field) for manifest in manifests]
                if None in values or len(set(values)) != len(RELATION_OWNERS):
                    raise ReceiptVerificationError(
                        f"owner identity collision: {field} must be distinct across owners"
                    )
        except Exception:
            self.close()
            raise

    def ask(self, owner_id: str, query: dict[str, Any], trace: Trace) -> dict[str, Any]:
        if query.get("owner_id") != owner_id:
            raise ValueError("query owner_id does not match routed owner process")
        if owner_id not in self.__processes:
            raise ValueError(f"owner process is not started: {owner_id}")
        return self.__processes[owner_id].query(query, trace)

    def manifests(self) -> list[dict[str, Any]]:
        return [self.__processes[owner].manifest for owner in RELATION_OWNERS]

    def issued_counts(self) -> dict[str, int]:
        return {
            owner: self.__processes[owner].issued_count if owner in self.__processes else 0
            for owner in ALL_OWNERS
        }

    def next_process_ordinal(self, owner_id: str) -> int:
        if owner_id not in self.__processes:
            raise ValueError(f"owner process is not started: {owner_id}")
        return self.__processes[owner_id].issued_count + 1

    def close(self) -> list[dict[str, Any]]:
        results = [self.__processes[owner].close() for owner in list(self.__processes)]
        self.__processes.clear()
        return results


def verify_receipt(
    receipt: dict[str, Any],
    manifest: dict[str, Any],
    expected_binding: dict[str, Any],
) -> dict[str, Any]:
    """Verify exact signed bytes, signer manifest and semantic binding.

    A matching digest alone is never accepted as proof.
    """

    try:
        raw = base64.b64decode(receipt["raw_bytes_b64"], validate=True)
        signature = base64.b64decode(receipt["signature_b64"], validate=True)
        public_raw = base64.b64decode(receipt["public_key_b64"], validate=True)
    except Exception as exc:
        raise ReceiptVerificationError("receipt base64 is invalid") from exc
    if raw != canonical_bytes(receipt["preimage"]):
        raise ReceiptVerificationError("raw signed bytes differ from canonical preimage")
    if receipt["raw_bytes_sha256"] != hash_bytes(raw) or receipt["act_hash"] != hash_bytes(raw):
        raise ReceiptVerificationError("receipt raw-byte hash mismatch")
    if receipt["public_key_b64"] != manifest["public_key_b64"]:
        raise ReceiptVerificationError("receipt public key is not process manifest key")
    if receipt["key_id"] != manifest["key_id"]:
        raise ReceiptVerificationError("receipt key_id is not process manifest key_id")
    try:
        Ed25519PublicKey.from_public_bytes(public_raw).verify(signature, raw)
    except (InvalidSignature, ValueError) as exc:
        raise ReceiptVerificationError("Ed25519 signature verification failed") from exc
    preimage = json.loads(raw)
    if preimage != receipt["preimage"]:
        raise ReceiptVerificationError("decoded raw bytes differ from displayed preimage")
    for key, expected in expected_binding.items():
        if preimage.get(key) != expected:
            raise ReceiptVerificationError(f"exact binding mismatch: {key}")
    if preimage.get("source") != manifest.get("source"):
        raise ReceiptVerificationError("signed source differs from process source manifest")
    process = preimage.get("process", {})
    if (
        process.get("pid") != manifest.get("pid")
        or process.get("instance_id") != manifest.get("process_instance_id")
        or process.get("key_id") != manifest.get("key_id")
    ):
        raise ReceiptVerificationError("signed process identity differs from manifest")
    return preimage


@dataclass(frozen=True)
class RelationVersion:
    relation_id: str
    revision: str
    q: dict[str, str]
    object_id: str
    purpose: str
    schema: dict[str, list[str]]
    schema_hash: str
    relation_revision_hash: str
    verified_source_act_hashes: list[str]
    version_hash: str
    delta: dict[str, Any]
    evidence_status: str
    constitution_closure: dict[str, Any]
    relation_established: bool
    downstream_relation_gate_open: bool
    non_entailments: list[str]

    @classmethod
    def derive(
        cls,
        *,
        relation_id: str,
        revision: str,
        q: dict[str, str],
        object_id: str,
        purpose: str,
        schema: dict[str, list[str]],
        prior_schema: dict[str, list[str]],
        relation_revision_hash: str,
        verified_source_act_hashes: list[str],
        constitution_closure: dict[str, Any],
    ) -> "RelationVersion":
        version_hash = digest(
            {
                "relation_id": relation_id,
                "revision": revision,
                "q": q,
                "object_id": object_id,
                "purpose": purpose,
                "schema_hash": digest(schema),
                "relation_revision_hash": relation_revision_hash,
                "verified_source_act_hashes": verified_source_act_hashes,
                "constitution_closure": constitution_closure,
            }
        )
        established = constitution_closure["status"] == "CLOSED_EXACT_FIVE_OWNER"
        return cls(
            relation_id=relation_id,
            revision=revision,
            q=q,
            object_id=object_id,
            purpose=purpose,
            schema=schema,
            schema_hash=digest(schema),
            relation_revision_hash=relation_revision_hash,
            verified_source_act_hashes=verified_source_act_hashes,
            version_hash=version_hash,
            delta=schema_delta(prior_schema, schema),
            evidence_status=(
                "DERIVED_SNAPSHOT_OF_VERIFIED_EXACT_BOUND_OWNER_EVIDENCE"
                if established
                else "DERIVED_CANDIDATE_WITH_UNRESOLVED_CONSTITUTION"
            ),
            constitution_closure=constitution_closure,
            relation_established=established,
            downstream_relation_gate_open=established,
            non_entailments=[
                "NOT_AN_OWNER_ACT",
                "NOT_AUTHORITY",
                "NOT_EFFECT",
                "NOT_ACCEPTANCE",
                "NOT_SETTLEMENT",
                "NOT_CONTRACT_SUCCESS",
            ],
        )


def _query(
    *,
    episode_id: str,
    run_id: str,
    ordinal: int,
    process_ordinal: int,
    owner_id: str,
    endpoint: dict[str, Any],
    kind: str,
    q: dict[str, str],
    object_id: str,
    purpose: str,
    revision: str,
    revision_hash: str,
    version_hash: str | None,
    relation_schema_hash: str | None,
    scope: str = "RELATION",
    **request_payload: Any,
) -> dict[str, Any]:
    issued_at = utc_now()
    operation_ids = list(request_payload.pop("operation_ids", []))
    request = {
        "request_schema_version": REQUEST_SCHEMA_VERSION,
        "query_id": f"{episode_id}-q{ordinal:03d}-{owner_id}-{kind}",
        "run_id": run_id,
        "owner_id": owner_id,
        "episode_id": episode_id,
        "request_ordinal": ordinal,
        "process_ordinal": process_ordinal,
        "request_nonce": str(uuid.uuid4()),
        "issued_at": utc_text(issued_at),
        "expires_at": utc_text(issued_at + timedelta(seconds=REQUEST_TTL_SECONDS)),
        "endpoint_binding": endpoint,
        "kind": kind,
        "q": q,
        "object_id": object_id,
        "purpose": purpose,
        "relation_revision": revision,
        "relation_revision_hash": revision_hash,
        "relation_version_hash": version_hash,
        "relation_schema_hash": relation_schema_hash,
        "scope": scope,
        "operation_ids": operation_ids,
        "request_payload": request_payload,
    }
    if set(request) != REQUEST_KEYS:
        raise AssertionError("controller request schema drift")
    return request


def _verify_for_request(
    receipt: dict[str, Any],
    process_manifest: dict[str, Any],
    request: dict[str, Any],
    state: VerificationState | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    if set(request) != REQUEST_KEYS:
        raise ReceiptVerificationError("request schema fields mismatch")
    if request.get("request_schema_version") != REQUEST_SCHEMA_VERSION:
        raise ReceiptVerificationError("request schema version is not allowed")
    if request.get("endpoint_binding") != endpoint_binding(process_manifest):
        raise ReceiptVerificationError(
            "request endpoint binding/source differs from actual process manifest"
        )
    request_raw = canonical_bytes(request)
    request_hash = hash_bytes(request_raw)
    payload_hash = digest(request["request_payload"])
    operation_ids = request["operation_ids"]
    if (
        not isinstance(operation_ids, list)
        or any(not isinstance(item, str) for item in operation_ids)
        or len(operation_ids) != len(set(operation_ids))
    ):
        raise ReceiptVerificationError("operation_ids must be a unique string list")
    if request["kind"] in {"AUTHORIZE", "ACTIVATE"} and not operation_ids:
        raise ReceiptVerificationError("operation_ids are required for downstream intent")
    if request["kind"] not in {"AUTHORIZE", "ACTIVATE"} and operation_ids:
        raise ReceiptVerificationError("operation_ids are forbidden for this request kind")

    expected_type = (
        "platform_receipt"
        if request["owner_id"] == "PLATFORM_VENUE_NATIVE"
        else "owner_receipt"
    )
    expected_schema = (
        PLATFORM_RECEIPT_SCHEMA_VERSION
        if expected_type == "platform_receipt"
        else OWNER_RECEIPT_SCHEMA_VERSION
    )
    if receipt.get("type") != expected_type:
        raise ReceiptVerificationError("receipt type is not allowed for endpoint")
    preimage = verify_receipt(
        receipt,
        process_manifest,
        {
            "schema_version": expected_schema,
            "request_schema_version": request["request_schema_version"],
            "owner_id": request["owner_id"],
            "run_id": request["run_id"],
            "episode_id": request["episode_id"],
            "query_id": request["query_id"],
            "q": request["q"],
            "object_id": request["object_id"],
            "purpose": request["purpose"],
            "relation_revision": request["relation_revision"],
            "relation_revision_hash": request["relation_revision_hash"],
            "relation_version_hash": request["relation_version_hash"],
            "relation_schema_hash": request["relation_schema_hash"],
            "scope": request["scope"],
            "requested_kind": request["kind"],
            "request_ordinal": request["request_ordinal"],
            "process_ordinal": request["process_ordinal"],
            "request_nonce": request["request_nonce"],
            "request_issued_at": request["issued_at"],
            "request_expires_at": request["expires_at"],
            "request_raw_bytes_b64": base64.b64encode(request_raw).decode("ascii"),
            "request_raw_bytes_sha256": request_hash,
            "request_payload_sha256": payload_hash,
            "operation_ids": operation_ids,
            "endpoint_binding": request["endpoint_binding"],
            "endpoint_binding_sha256": request["endpoint_binding"]["sha256"],
        },
    )
    response_kinds = (
        PLATFORM_RESPONSE_KINDS
        if expected_type == "platform_receipt"
        else OWNER_RESPONSE_KINDS
    )
    allowed = response_kinds.get(request["kind"])
    if allowed is None or preimage.get("kind") not in allowed:
        raise ReceiptVerificationError("response kind is not allowed for requested kind")
    if preimage.get("evidence_origin") != LOCAL_TRUST_CLASS:
        raise ReceiptVerificationError("receipt evidence origin boundary mismatch")
    if preimage.get("trust_anchor_status") != "NOT_ESTABLISHED":
        raise ReceiptVerificationError("receipt trust anchor boundary mismatch")
    if request["kind"] in {"AUTHORIZE", "ACTIVATE"}:
        if preimage.get("payload", {}).get("operation_ids") != operation_ids:
            raise ReceiptVerificationError("response operation_ids mismatch")

    issued_at = parse_utc(request["issued_at"], "request issued_at")
    expires_at = parse_utc(request["expires_at"], "request expires_at")
    signed_at = parse_utc(preimage.get("signed_at"), "receipt signed_at")
    checked_at = (now or utc_now()).astimezone(timezone.utc)
    if expires_at <= issued_at:
        raise ReceiptVerificationError("request freshness window is invalid")
    if expires_at - issued_at > timedelta(seconds=REQUEST_TTL_SECONDS):
        raise ReceiptVerificationError("request freshness window exceeds policy")
    if issued_at > checked_at:
        raise ReceiptVerificationError("future-issued request rejected")
    if checked_at > expires_at:
        raise ReceiptVerificationError("stale request rejected")
    if not (issued_at <= signed_at <= expires_at):
        raise ReceiptVerificationError("receipt signed_at is outside request freshness window")

    if state is not None:
        assert state.process_ordinals is not None
        assert state.consumed_query_ids is not None
        assert state.consumed_nonces is not None
        assert state.consumed_request_hashes is not None
        process_id = process_manifest["process_instance_id"]
        expected_request_ordinal = state.last_request_ordinal + 1
        expected_process_ordinal = state.process_ordinals.get(process_id, 0) + 1
        if request["request_ordinal"] != expected_request_ordinal:
            raise ReceiptVerificationError("global request ordinal is not strictly consecutive")
        if (
            request["process_ordinal"] != expected_process_ordinal
            or preimage.get("issuer_ordinal") != expected_process_ordinal
        ):
            raise ReceiptVerificationError("per-process ordinal is not strictly consecutive")
        if request["query_id"] in state.consumed_query_ids:
            raise ReceiptVerificationError("query replay rejected")
        if request["request_nonce"] in state.consumed_nonces:
            raise ReceiptVerificationError("nonce replay rejected")
        if request_hash in state.consumed_request_hashes:
            raise ReceiptVerificationError("request hash replay rejected")
        state.last_request_ordinal = request["request_ordinal"]
        state.process_ordinals[process_id] = request["process_ordinal"]
        state.consumed_query_ids.add(request["query_id"])
        state.consumed_nonces.add(request["request_nonce"])
        state.consumed_request_hashes.add(request_hash)
    return preimage


def _ask_verified(
    directory: OwnerDirectory,
    owner_id: str,
    request: dict[str, Any],
    trace: Trace,
    manifests: dict[str, dict[str, Any]],
    rejected: list[dict[str, Any]],
    verification_state: VerificationState,
) -> dict[str, Any] | None:
    receipt = directory.ask(owner_id, request, trace)
    try:
        preimage = _verify_for_request(
            receipt, manifests[owner_id], request, verification_state
        )
    except ReceiptVerificationError as exc:
        # The controller-created request was still issued and the worker still
        # consumed its per-process slot even when the returned receipt failed.
        # Record those one-way facts so a rejected receipt cannot desynchronise
        # or relax the next request's ordinal/replay checks.
        assert verification_state.process_ordinals is not None
        assert verification_state.consumed_query_ids is not None
        assert verification_state.consumed_nonces is not None
        assert verification_state.consumed_request_hashes is not None
        process_id = manifests[owner_id]["process_instance_id"]
        request_hash = hash_bytes(canonical_bytes(request))
        if (
            request["request_ordinal"] == verification_state.last_request_ordinal + 1
            and request["process_ordinal"]
            == verification_state.process_ordinals.get(process_id, 0) + 1
            and request["query_id"] not in verification_state.consumed_query_ids
            and request["request_nonce"] not in verification_state.consumed_nonces
            and request_hash not in verification_state.consumed_request_hashes
        ):
            verification_state.last_request_ordinal = request["request_ordinal"]
            verification_state.process_ordinals[process_id] = request["process_ordinal"]
            verification_state.consumed_query_ids.add(request["query_id"])
            verification_state.consumed_nonces.add(request["request_nonce"])
            verification_state.consumed_request_hashes.add(request_hash)
        rejected.append(
            {
                "owner_id": owner_id,
                "query_id": request["query_id"],
                "reason": str(exc),
                "receipt": receipt,
            }
        )
        trace.add(
            "owner_receipt_rejected",
            owner_id=owner_id,
            query_id=request["query_id"],
            reason=str(exc),
            act_hash=receipt.get("act_hash"),
        )
        return None
    trace.add(
        "owner_receipt_verified",
        owner_id=owner_id,
        query_id=request["query_id"],
        act_hash=receipt["act_hash"],
        signature_verified=True,
        exact_binding_verified=True,
    )
    return {**receipt, "verified_preimage": preimage}


def _axis_record(
    axis: str,
    acts: list[dict[str, Any]],
    required_clauses: set[str],
) -> dict[str, Any]:
    by_owner: dict[str, list[dict[str, Any]]] = {owner: [] for owner in RELATION_OWNERS}
    for act in acts:
        owner = act["verified_preimage"]["owner_id"]
        if owner in by_owner:
            by_owner[owner].append(act)
    expected = {
        "constituted": {"CONSTITUTE", "REFUSE", "UNKNOWN"},
        "understood": {"EXPLAIN_BACK", "REFUSE", "UNKNOWN"},
        "claimed": {"CLAIM", "CLAIM_WITH_OPPOSITION", "REFUSE", "UNKNOWN"},
        "authorized": {"AUTHORIZE", "REFUSE", "UNKNOWN"},
        "activated": {"ACTIVATE", "REFUSE", "UNKNOWN"},
    }[axis]
    states: dict[str, str] = {}
    support: list[str] = []
    oppose: list[str] = []
    for owner, candidates in by_owner.items():
        matching = [a for a in candidates if a["verified_preimage"]["kind"] in expected]
        if not matching:
            states[owner] = "UNKNOWN_NO_VERIFIED_EXACT_BOUND_OWNER_ACT"
            continue
        act = matching[-1]
        pre = act["verified_preimage"]
        kind = pre["kind"]
        if kind == "UNKNOWN":
            states[owner] = "UNKNOWN_OWNER_POLICY_MISSING_OR_NO_DECISION"
        elif kind == "REFUSE":
            states[owner] = "REFUSED_BLOCKING"
            oppose.append(act["act_id"])
        elif kind == "CLAIM_WITH_OPPOSITION":
            opposition = pre["payload"]["opposition"]
            blocking = bool(opposition.get("blocking")) or str(
                opposition.get("position", "")
            ).upper().startswith(("DO_NOT", "DENY", "REFUSE", "WITHDRAW"))
            states[owner] = (
                "BLOCKING_OPPOSITION" if blocking else "CLAIMED_WITH_SCOPED_OPPOSITION"
            )
            oppose.append(act["act_id"])
            if not blocking:
                support.append(act["act_id"])
        elif axis == "understood":
            explained = set(pre["payload"].get("explained_clause_ids", []))
            if required_clauses <= explained:
                states[owner] = "SUPPORTED_BY_VERIFIED_EXPLAIN_BACK"
                support.append(act["act_id"])
            else:
                states[owner] = "MISUNDERSTOOD_OR_PARTIAL"
                oppose.append(act["act_id"])
        elif axis == "authorized":
            states[owner] = "G5_UNVERIFIED_OWNER_INTENT_ONLY"
            support.append(act["act_id"])
        elif axis == "activated":
            states[owner] = "G6_UNVERIFIED_NO_EFFECT"
            support.append(act["act_id"])
        else:
            states[owner] = "SUPPORTED_BY_VERIFIED_OWNER_ACT"
            support.append(act["act_id"])
    return {
        "axis": axis,
        "owner_states": states,
        "supporting_act_ids": support,
        "opposing_act_ids": oppose,
        "global_status": "NOT_COMPUTED",
    }


def run_e2(config: dict[str, Any], *, run_id: str = "interactive") -> dict[str, Any]:
    episode_id = config["episode_id"]
    q = _q_from_config(config)
    object_id = config.get("object_id", DEFAULT_OBJECT_ID)
    purpose = config.get("purpose", DEFAULT_PURPOSE)
    revision = config.get("version", "v1")
    profile_case = config["profile_case"]
    endpoint_doc, endpoint_path = _resolve_endpoint_document(config)
    descriptors = {
        owner: _resolved_descriptor(endpoint_doc["owners"][owner], endpoint_path)
        for owner in RELATION_OWNERS
    }
    trace = Trace(episode_id, run_id)
    directory = OwnerDirectory(descriptors, profile_case)
    acts: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    exits: list[dict[str, Any]] = []
    issued_counts: dict[str, int] = {}
    directory.start()
    process_manifests = directory.manifests()
    manifests = {item["owner_id"]: item for item in process_manifests}
    verification_state = VerificationState()
    ordinal = 1
    seed_revision_hash = digest(
        {
            "relation_id": "REL-CE001-E2",
            "revision": revision,
            "q": q,
            "object_id": object_id,
            "purpose": purpose,
        }
    )
    try:
        private_request = _query(
            episode_id=episode_id,
            run_id=run_id,
            ordinal=ordinal,
            process_ordinal=directory.next_process_ordinal("O_R"),
            owner_id="O_R",
            endpoint=endpoint_binding(manifests["O_R"]),
            kind="PRIVATE_COLUMN",
            q=q,
            object_id=object_id,
            purpose=purpose,
            revision=revision,
            revision_hash=seed_revision_hash,
            version_hash=None,
            relation_schema_hash=digest(E2_SCHEMA),
            scope="PRIVATE_ACTION_SET",
        )
        private_act = _ask_verified(
            directory,
            "O_R",
            private_request,
            trace,
            manifests,
            rejected,
            verification_state,
        )
        ordinal += 1
        if private_act is None:
            column_state = "UNKNOWN"
            private_source_hash = "REJECTED"
        else:
            acts.append(private_act)
            column_state = private_act["verified_preimage"]["payload"]["column_state"]
            private_source_hash = private_act["act_hash"]

        schema = {key: list(values) for key, values in E2_SCHEMA.items()}
        if column_state != "DISCLOSED":
            schema["roles"].remove("RESOURCE_PROVIDER")
            schema["actions"].remove("SUPPLY_C7")
        revision_hash = digest(
            {
                "relation_id": "REL-CE001-E2",
                "revision": revision,
                "q": q,
                "object_id": object_id,
                "purpose": purpose,
                "schema_hash": digest(schema),
                "private_column_state": column_state,
                "verified_private_source_hash": private_source_hash,
            }
        )

        constitution_acts: list[dict[str, Any]] = []
        for owner_id in RELATION_OWNERS:
            request = _query(
                episode_id=episode_id,
                run_id=run_id,
                ordinal=ordinal,
                process_ordinal=directory.next_process_ordinal(owner_id),
                owner_id=owner_id,
                endpoint=endpoint_binding(manifests[owner_id]),
                kind="CONSTITUTE",
                q=q,
                object_id=object_id,
                purpose=purpose,
                revision=revision,
                revision_hash=revision_hash,
                version_hash=None,
                relation_schema_hash=digest(schema),
            )
            act = _ask_verified(
                directory,
                owner_id,
                request,
                trace,
                manifests,
                rejected,
                verification_state,
            )
            ordinal += 1
            if act is not None:
                acts.append(act)
                constitution_acts.append(act)

        source_hashes = [private_source_hash] + [
            act["act_hash"] for act in constitution_acts
        ]
        constituted_by_owner = {
            act["verified_preimage"]["owner_id"]: (
                act["verified_preimage"]["kind"] == "CONSTITUTE"
                and act["verified_preimage"]["decision"] == "CONSTITUTED"
                and act["verified_preimage"]["relation_revision_hash"] == revision_hash
                and act["verified_preimage"]["relation_schema_hash"] == digest(schema)
            )
            for act in constitution_acts
        }
        constitution_closure = {
            "status": (
                "CLOSED_EXACT_FIVE_OWNER"
                if all(constituted_by_owner.get(owner) is True for owner in RELATION_OWNERS)
                else "UNRESOLVED_CONSTITUTION"
            ),
            "required_owners": list(RELATION_OWNERS),
            "owner_exact_constitution": {
                owner: constituted_by_owner.get(owner, False) for owner in RELATION_OWNERS
            },
            "required_relation_revision_hash": revision_hash,
            "required_relation_schema_hash": digest(schema),
            "may_be_treated_as_established_relation": all(
                constituted_by_owner.get(owner) is True for owner in RELATION_OWNERS
            ),
        }
        version = RelationVersion.derive(
            relation_id="REL-CE001-E2",
            revision=revision,
            q=q,
            object_id=object_id,
            purpose=purpose,
            schema=schema,
            prior_schema=BASE_SCHEMA,
            relation_revision_hash=revision_hash,
            verified_source_act_hashes=source_hashes,
            constitution_closure=constitution_closure,
        )
        trace.add(
            "relation_version_derived",
            relation_version=asdict(version),
            source_act_hashes=source_hashes,
        )
        required_clauses = sorted(
            {
                item
                for field in ("roles", "actions", "evidence", "evaluation", "exit", "constraints")
                for item in schema[field]
            }
        )
        operations = [
            f"{episode_id}:OP:SUPPLY_C7",
            f"{episode_id}:OP:APPROVE_C7_CONNECTION",
            f"{episode_id}:OP:AUTHORIZE_PAYMENT",
        ]
        for owner_id in RELATION_OWNERS:
            blocked = False
            for kind, payload in (
                ("EXPLAIN_BACK", {"required_clause_ids": required_clauses}),
                ("CLAIM", {}),
            ):
                request = _query(
                    episode_id=episode_id,
                    run_id=run_id,
                    ordinal=ordinal,
                    process_ordinal=directory.next_process_ordinal(owner_id),
                    owner_id=owner_id,
                    endpoint=endpoint_binding(manifests[owner_id]),
                    kind=kind,
                    q=q,
                    object_id=object_id,
                    purpose=purpose,
                    revision=revision,
                    revision_hash=revision_hash,
                    version_hash=version.version_hash,
                    relation_schema_hash=version.schema_hash,
                    **payload,
                )
                act = _ask_verified(
                    directory,
                    owner_id,
                    request,
                    trace,
                    manifests,
                    rejected,
                    verification_state,
                )
                ordinal += 1
                if act is None:
                    blocked = True
                    break
                acts.append(act)
                pre = act["verified_preimage"]
                if pre["kind"] in {"UNKNOWN", "REFUSE"}:
                    blocked = True
                    break
                opposition = pre["payload"].get("opposition", {})
                if opposition and (
                    opposition.get("blocking")
                    or str(opposition.get("position", "")).upper().startswith(
                        ("DO_NOT", "DENY", "REFUSE", "WITHDRAW")
                    )
                ):
                    blocked = True
                    break
            if blocked or not version.downstream_relation_gate_open:
                continue
            for kind in ("AUTHORIZE", "ACTIVATE"):
                request = _query(
                    episode_id=episode_id,
                    run_id=run_id,
                    ordinal=ordinal,
                    process_ordinal=directory.next_process_ordinal(owner_id),
                    owner_id=owner_id,
                    endpoint=endpoint_binding(manifests[owner_id]),
                    kind=kind,
                    q=q,
                    object_id=object_id,
                    purpose=purpose,
                    revision=revision,
                    revision_hash=revision_hash,
                    version_hash=version.version_hash,
                    relation_schema_hash=version.schema_hash,
                    operation_ids=operations,
                )
                act = _ask_verified(
                    directory,
                    owner_id,
                    request,
                    trace,
                    manifests,
                    rejected,
                    verification_state,
                )
                ordinal += 1
                if act is None:
                    break
                acts.append(act)
                if act["verified_preimage"]["kind"] in {"UNKNOWN", "REFUSE"}:
                    break
    finally:
        issued_counts = directory.issued_counts()
        exits = directory.close()

    required_set = set(required_clauses)
    evidence = {axis: _axis_record(axis, acts, required_set) for axis in AXES}
    evidence["authorized"]["truth_owner_boundary"] = "G5_UNVERIFIED"
    evidence["activated"]["truth_owner_boundary"] = "G6_UNVERIFIED"
    evidence["activated"]["O_E_state"] = "NOT_RUN"
    opposition = [
        {
            "act_id": act["act_id"],
            "owner_id": act["verified_preimage"]["owner_id"],
            "scope": act["verified_preimage"]["scope"],
            "opposition": act["verified_preimage"]["payload"]["opposition"],
            "source": act["verified_preimage"]["source"],
        }
        for act in acts
        if act["verified_preimage"]["kind"] == "CLAIM_WITH_OPPOSITION"
    ]
    return {
        "episode_id": episode_id,
        "run_id": run_id,
        "path": "RELATION_FORMATION",
        "q": q,
        "q_version": q["version"],
        "object_id": object_id,
        "purpose": purpose,
        "relation_version": asdict(version),
        "private_column_evidence": {
            "state": column_state,
            "verified_act_hash": private_source_hash,
        },
        "owner_acts": acts,
        "rejected_receipts": rejected,
        "axis_evidence": evidence,
        "opposition": opposition,
        "issued_counts": issued_counts,
        "process_manifests": process_manifests,
        "process_exits": exits,
        "g2_line_local_envelope": {
            "schema_version": "g2-line-local-envelope-v1",
            "line_id": "G2",
            "episode_binding": {
                "episode_id": episode_id,
                "q_hash": q["hash"],
                "object_id": object_id,
                "purpose": purpose,
            },
            "evidence_class": LOCAL_TRUST_CLASS,
            "request_response_conformance": "EXACT_LOCAL_FIXTURE_CONFORMANCE",
            "relation_candidate_or_snapshot": {
                "version_hash": version.version_hash,
                "evidence_status": version.evidence_status,
                "constitution_closure": constitution_closure["status"],
                "established_for_g2_local_fixture": version.relation_established,
                "eligible_for_g2_intent_queries": version.downstream_relation_gate_open,
            },
            "raw_evidence_refs": [act["act_hash"] for act in acts],
            "contract_fields_emitted": [],
            "external_truth_status": "NOT_ESTABLISHED",
            "unverified_adjacent_lines": ["G5", "G6"],
        },
        "evidence_boundaries": {
            "evidence_origin": LOCAL_TRUST_CLASS,
            "real_owner_identity": "NOT_ESTABLISHED",
            "real_owner": "NOT_RUN",
            "authority": "NOT_ESTABLISHED",
            "legal_sufficiency": "NOT_ESTABLISHED",
            "effect": "NOT_RUN",
            "acceptance": "NOT_RUN",
            "settlement": "NOT_RUN",
            "relation_version": (
                "DERIVED_ESTABLISHED_G2_SNAPSHOT_NOT_OWNER_OR_AUTHORITY_OR_EFFECT_OR_ACCEPTANCE"
                if version.relation_established
                else "DERIVED_CANDIDATE_UNRESOLVED_CONSTITUTION_NOT_A_RELATION_FACT"
            ),
        },
        "trace": trace.records,
    }


def run_platform_direct(config: dict[str, Any], *, run_id: str = "interactive") -> dict[str, Any]:
    if "platform_direct_applicable" in config:
        raise ValueError("bare platform_direct_applicable is forbidden")
    episode_id = config["episode_id"]
    q = _q_from_config(config)
    object_id = config.get("object_id", DEFAULT_OBJECT_ID)
    purpose = config.get("purpose", DEFAULT_PURPOSE)
    revision = config.get("version", "v1")
    endpoint_doc, endpoint_path = _resolve_endpoint_document(config)
    descriptor = _resolved_descriptor(endpoint_doc["platform"], endpoint_path)
    process = SignedProcess(
        descriptor=descriptor,
        profile_case=config["platform_profile_case"],
        owner_id="PLATFORM_VENUE_NATIVE",
        platform=True,
    )
    manifest = process.manifest
    trace = Trace(episode_id, run_id)
    verification_state = VerificationState()
    revision_hash = digest(
        {
            "path": "PLATFORM_NATIVE",
            "q": q,
            "object_id": object_id,
            "purpose": purpose,
            "revision": revision,
        }
    )
    exits: list[dict[str, Any]] = []
    try:
        proof_request = _query(
            episode_id=episode_id,
            run_id=run_id,
            ordinal=1,
            process_ordinal=process.issued_count + 1,
            owner_id="PLATFORM_VENUE_NATIVE",
            endpoint=endpoint_binding(manifest),
            kind="CAPABILITY_PROOF",
            q=q,
            object_id=object_id,
            purpose=purpose,
            revision=revision,
            revision_hash=revision_hash,
            version_hash=None,
            relation_schema_hash=None,
            scope="PLATFORM_NATIVE_CAPABILITY",
        )
        proof = process.query(proof_request, trace)
        proof_preimage = _verify_for_request(
            proof, manifest, proof_request, verification_state
        )
        if proof_preimage["decision"] != "APPLICABLE":
            raise ReceiptVerificationError("platform-native capability proof is not applicable")
        readback_request = _query(
            episode_id=episode_id,
            run_id=run_id,
            ordinal=2,
            process_ordinal=process.issued_count + 1,
            owner_id="PLATFORM_VENUE_NATIVE",
            endpoint=endpoint_binding(manifest),
            kind="CAPABILITY_READBACK",
            q=q,
            object_id=object_id,
            purpose=purpose,
            revision=revision,
            revision_hash=revision_hash,
            version_hash=None,
            relation_schema_hash=None,
            scope="PLATFORM_NATIVE_CAPABILITY",
            capability_proof_hash=proof["act_hash"],
        )
        readback = process.query(readback_request, trace)
        readback_preimage = _verify_for_request(
            readback, manifest, readback_request, verification_state
        )
        if (
            readback_preimage["decision"] != "READBACK_CONFIRMED"
            or readback_preimage["payload"]["capability_proof_hash"] != proof["act_hash"]
            or readback_preimage["payload"]["native_target"] != object_id
        ):
            raise ReceiptVerificationError("platform-native readback is missing or wrong-bound")
        trace.add(
            "platform_local_fixture_self_assertion_verified",
            capability_proof_hash=proof["act_hash"],
            capability_readback_hash=readback["act_hash"],
            signature_verified=True,
            exact_binding_verified=True,
            effect_asserted=False,
        )
    finally:
        exits = [process.close()]
    return {
        "episode_id": episode_id,
        "run_id": run_id,
        "path": "T5_PLATFORM_DIRECT_BYPASS",
        "q": q,
        "q_version": q["version"],
        "object_id": object_id,
        "relation_version": None,
        "relation_artifact_created": False,
        "owner_acts": [],
        "axis_evidence": {
            axis: {
                "axis": axis,
                "status": "NOT_APPLICABLE_PLATFORM_NATIVE",
                "global_status": "NOT_COMPUTED",
                "supporting_act_ids": [],
                "opposing_act_ids": [],
            }
            for axis in AXES
        },
        "bypass_evidence": {
            "capability_proof": proof,
            "capability_readback": readback,
            "verification_classification": PLATFORM_LOCAL_ASSERTION,
            "local_fixture_self_assertion_verified": True,
            "real_platform_identity": "NOT_ESTABLISHED",
            "real_platform_applicability": "NOT_ESTABLISHED",
            "self_configured_profile_and_endpoint": True,
            "second_relation_fact_source_created": False,
            "effect": "NOT_RUN",
        },
        "process_manifests": [manifest],
        "process_exits": exits,
        "g2_line_local_envelope": {
            "schema_version": "g2-line-local-envelope-v1",
            "line_id": "G2",
            "episode_binding": {
                "episode_id": episode_id,
                "q_hash": q["hash"],
                "object_id": object_id,
                "purpose": purpose,
            },
            "evidence_class": PLATFORM_LOCAL_ASSERTION,
            "request_response_conformance": "EXACT_LOCAL_FIXTURE_CONFORMANCE",
            "relation_candidate_or_snapshot": None,
            "raw_evidence_refs": [proof["act_hash"], readback["act_hash"]],
            "contract_fields_emitted": [],
            "external_truth_status": "NOT_ESTABLISHED",
            "unverified_adjacent_lines": ["G5", "G6"],
        },
        "evidence_boundaries": {
            "evidence_origin": LOCAL_TRUST_CLASS,
            "platform_assertion_classification": PLATFORM_LOCAL_ASSERTION,
            "real_platform_identity": "NOT_ESTABLISHED",
            "real_platform_applicability": "NOT_ESTABLISHED",
            "real_owner": "NOT_RUN",
            "authority": "NOT_ESTABLISHED",
            "legal_sufficiency": "NOT_ESTABLISHED",
            "effect": "NOT_RUN",
            "acceptance": "NOT_RUN",
            "settlement": "NOT_RUN",
        },
        "trace": trace.records,
    }


def run_scenario(config: dict[str, Any], *, run_id: str = "interactive") -> dict[str, Any]:
    if config["kind"] == "PLATFORM_DIRECT":
        return run_platform_direct(config, run_id=run_id)
    if config["kind"] == "E2_RELATION":
        return run_e2(config, run_id=run_id)
    raise ValueError(f"unknown scenario kind: {config['kind']}")


def semantic_projection(output: dict[str, Any]) -> dict[str, Any]:
    """Remove runtime identity/cryptographic randomness for rerun comparison."""

    relation = output["relation_version"]
    semantic_relation = None
    if relation is not None:
        semantic_relation = {
            "relation_id": relation["relation_id"],
            "revision": relation["revision"],
            "q": relation["q"],
            "object_id": relation["object_id"],
            "purpose": relation["purpose"],
            "schema": relation["schema"],
            "delta": relation["delta"],
            "evidence_status": relation["evidence_status"],
            "non_entailments": relation["non_entailments"],
            "verified_source_count": len(relation["verified_source_act_hashes"]),
        }
        if "constitution_closure" in relation:
            semantic_relation.update(
                {
                    "constitution_closure": {
                        "status": relation["constitution_closure"]["status"],
                        "required_owners": relation["constitution_closure"][
                            "required_owners"
                        ],
                        "owner_exact_constitution": relation[
                            "constitution_closure"
                        ]["owner_exact_constitution"],
                        "may_be_treated_as_established_relation": relation[
                            "constitution_closure"
                        ]["may_be_treated_as_established_relation"],
                    },
                    "relation_established": relation["relation_established"],
                    "downstream_relation_gate_open": relation[
                        "downstream_relation_gate_open"
                    ],
                }
            )
    return {
        "episode_id": output["episode_id"],
        "path": output["path"],
        "q": output["q"],
        "object_id": output["object_id"],
        "relation_version": semantic_relation,
        "private_column_state": output.get("private_column_evidence", {}).get("state"),
        "axis_owner_states": {
            axis: output["axis_evidence"][axis].get("owner_states")
            for axis in AXES
        },
        "opposition": [
            {
                "owner_id": item["owner_id"],
                "scope": item["scope"],
                "opposition": item["opposition"],
            }
            for item in output.get("opposition", [])
        ],
        "rejected_reasons": [
            {"owner_id": item["owner_id"], "reason": item["reason"]}
            for item in output.get("rejected_receipts", [])
        ],
        "platform": (
            {
                "proof_decision": output["bypass_evidence"]["capability_proof"]["preimage"][
                    "decision"
                ],
                "readback_decision": output["bypass_evidence"]["capability_readback"]["preimage"][
                    "decision"
                ],
            }
            if output["path"] == "T5_PLATFORM_DIRECT_BYPASS"
            else None
        ),
        "evidence_boundaries": output["evidence_boundaries"],
    }
