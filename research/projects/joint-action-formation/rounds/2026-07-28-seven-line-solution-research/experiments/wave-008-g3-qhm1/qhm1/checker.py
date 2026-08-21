"""Exhaustive bounded closure computation for L0, L0+L1, and L0+L1+L2."""

from __future__ import annotations

from collections import deque
from dataclasses import asdict, dataclass
import hashlib
import inspect
import json

from .model import AbstractState, abstract_qualified, initial_state, transition
from .spec import ACTION_SPECS, OLD_TASK, RESOURCE_ACCOUNT, fingerprint, frozen_package
from .worlds import HiddenWorld


@dataclass(frozen=True)
class UnsatCertificate:
    max_layer: int
    horizon: int
    max_cost: int
    max_privacy_cost: int
    explored_states: int
    explored_edges: int
    frontier_exhausted: bool
    frontier_hash: str
    task_fingerprint: str
    action_model_fingerprint: str
    executable_model_fingerprint: str
    completeness_scope: str


@dataclass(frozen=True)
class CheckResult:
    max_layer: int
    sat: bool
    witness: tuple[str, ...]
    witness_cost: int | None
    final_state_digest: str | None
    explored_states: int
    explored_edges: int
    executable_model_fingerprint: str
    unsat_certificate: UnsatCertificate | None
    unresolved_reason: str | None


@dataclass(frozen=True)
class LayeredClosure:
    layers: tuple[CheckResult, CheckResult, CheckResult]
    formation_depth: int | None
    closure_status: str


@dataclass(frozen=True)
class EncodedAction:
    encoded_name: str
    underlying_action: str
    layer: int


def default_encoding() -> tuple[EncodedAction, ...]:
    return tuple(
        EncodedAction(spec.name, spec.name, spec.layer)
        for spec in ACTION_SPECS
    )


def meta_refactored_encoding() -> tuple[EncodedAction, ...]:
    """Same material transitions, but extension is encoded as L1 install(spec)."""
    encoded = []
    for spec in ACTION_SPECS:
        if spec.name == "PROPOSE_NEW_OPERATOR":
            encoded.append(
                EncodedAction("PROPOSE_SPEC", spec.name, 1)
            )
        elif spec.name == "REGISTER_NEW_OPERATOR":
            encoded.append(
                EncodedAction("INSTALL(spec)", spec.name, 1)
            )
        else:
            encoded.append(
                EncodedAction(spec.name, spec.name, spec.layer)
            )
    return tuple(encoded)


def _source_digest(value) -> str:
    try:
        source = inspect.getsource(value)
    except (OSError, TypeError):
        source = repr(value)
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def executable_model_fingerprint(
    world: HiddenWorld,
    encoding: tuple[EncodedAction, ...],
) -> str:
    transition_globals = getattr(transition, "__globals__", {})
    kernel = {
        "checker_version": "QHM1-BFS-v2",
        "package_fingerprint":
            frozen_package(world).package_fingerprint,
        "encoding_fingerprint": fingerprint(encoding),
        "initial_state_source": _source_digest(initial_state),
        "transition_source": _source_digest(transition),
        "route_ready_source": _source_digest(
            transition_globals.get("route_ready")
        ),
        "qualified_source": _source_digest(abstract_qualified),
    }
    return fingerprint(kernel)


class BoundedModelChecker:
    """Breadth-first exhaustive search over the complete declared finite model."""

    def check(
        self,
        world: HiddenWorld,
        max_layer: int,
        initial_override: AbstractState | None = None,
        encoding: tuple[EncodedAction, ...] | None = None,
    ) -> CheckResult:
        start = initial_override if initial_override is not None else initial_state(world)
        queue = deque([(start, tuple())])
        visited = {start}
        explored_edges = 0
        selected_encoding = encoding if encoding is not None else default_encoding()
        admissible = tuple(
            item for item in selected_encoding if item.layer <= max_layer
        )
        action_model_fingerprint = (
            frozen_package(world).action_model_fingerprint
            if encoding is None
            else fingerprint(selected_encoding)
        )
        executable_fingerprint = executable_model_fingerprint(
            world,
            selected_encoding,
        )

        while queue:
            state, path = queue.popleft()
            if abstract_qualified(state):
                return CheckResult(
                    max_layer=max_layer,
                    sat=True,
                    witness=path,
                    witness_cost=state.cost_used,
                    final_state_digest=state.digest(),
                    explored_states=len(visited),
                    explored_edges=explored_edges,
                    executable_model_fingerprint=executable_fingerprint,
                    unsat_certificate=None,
                    unresolved_reason=None,
                )
            for encoded_action in admissible:
                explored_edges += 1
                next_state = transition(
                    world,
                    state,
                    encoded_action.underlying_action,
                )
                if next_state is None or next_state in visited:
                    continue
                visited.add(next_state)
                queue.append(
                    (
                        next_state,
                        path + (encoded_action.encoded_name,),
                    )
                )

        hashes = sorted(state.digest() for state in visited)
        frontier_hash = hashlib.sha256(
            json.dumps(hashes, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        if not world.model_complete:
            return CheckResult(
                max_layer=max_layer,
                sat=False,
                witness=tuple(),
                witness_cost=None,
                final_state_digest=None,
                explored_states=len(visited),
                explored_edges=explored_edges,
                executable_model_fingerprint=executable_fingerprint,
                unsat_certificate=None,
                unresolved_reason=(
                    "ACTION_INVENTORY_DECLARED_INCOMPLETE; exhausted declared "
                    "edges cannot certify bounded UNSAT"
                ),
            )
        certificate = UnsatCertificate(
            max_layer=max_layer,
            horizon=RESOURCE_ACCOUNT.horizon,
            max_cost=RESOURCE_ACCOUNT.max_cost,
            max_privacy_cost=RESOURCE_ACCOUNT.max_privacy_cost,
            explored_states=len(visited),
            explored_edges=explored_edges,
            frontier_exhausted=True,
            frontier_hash=frontier_hash,
            task_fingerprint=fingerprint(OLD_TASK),
            action_model_fingerprint=action_model_fingerprint,
            executable_model_fingerprint=executable_fingerprint,
            completeness_scope=(
                "finite declared QHM1 state variables, scripted principal "
                "policies, actions with layer<=max_layer, horizon and cost bound"
            ),
        )
        return CheckResult(
            max_layer=max_layer,
            sat=False,
            witness=tuple(),
            witness_cost=None,
            final_state_digest=None,
            explored_states=len(visited),
            explored_edges=explored_edges,
            executable_model_fingerprint=executable_fingerprint,
            unsat_certificate=certificate,
            unresolved_reason=None,
        )

    def check_all_layers(
        self,
        world: HiddenWorld,
        encoding: tuple[EncodedAction, ...] | None = None,
    ) -> LayeredClosure:
        layers = tuple(
            self.check(world, level, encoding=encoding)
            for level in (0, 1, 2)
        )
        formation_depth = next(
            (result.max_layer for result in layers if result.sat),
            None,
        )
        if formation_depth is not None:
            closure_status = "SAT"
        elif any(result.unresolved_reason for result in layers):
            closure_status = "UNKNOWN"
        else:
            closure_status = "UNSAT"
        return LayeredClosure(
            layers=layers,
            formation_depth=formation_depth,
            closure_status=closure_status,
        )


def json_check_result(result: CheckResult) -> dict:
    payload = asdict(result)
    payload["witness"] = list(result.witness)
    return payload
