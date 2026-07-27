from datetime import datetime, timedelta, timezone

import numpy as np

from towow_sjac.engine import CommitmentCompiler, PolyhedralBoundaryCoordinator
from towow_sjac.events import EventStore
from towow_sjac.models import AgentExecution, Arrangement, CoordinationSchema, Delegation, Principal
from towow_sjac.oracles import PolytopeOracle
from towow_sjac.trust import InMemoryPlatformTrustAdapter


def test_boundary_coordinator_finds_feasible_optimum():
    # Shared x must satisfy x0 <= 0.6 and x1 <= 0.4.
    o1 = PolytopeOracle("a", np.array([[1.0, 0.0]]), np.array([0.6]))
    o2 = PolytopeOracle("b", np.array([[0.0, 1.0]]), np.array([0.4]))
    engine = PolyhedralBoundaryCoordinator(2, np.array([1.0, 1.0]), [o1, o2])
    result = engine.solve()
    assert result.feasible
    assert np.allclose(result.vector, [0.6, 0.4], atol=1e-7)
    assert engine.events.verify_chain()


def test_delegation_required_for_commitment():
    p1 = Principal(display_name="A")
    p2 = Principal(display_name="B")
    execution = AgentExecution(agent_instance_id="agent", principal_id=p1.id)
    schema = CoordinationSchema(name="demo")
    arrangement = Arrangement(schema_id=schema.id, status="recognized")
    delegation = Delegation(
        issuer_principal_id=p1.id,
        delegate_execution_id=execution.id,
        actions={"commit"},
        objects={arrangement.id},
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    commitment = CommitmentCompiler().compile(
        arrangement, delegation, p1.id, p2.id,
        {"deliverable": "report"}, {"required_kind": "artifact"},
        datetime.now(timezone.utc) + timedelta(days=7),
    )
    assert commitment.debtor == p1.id


def test_trust_adapter_reservation_prevents_double_spend():
    p1 = Principal(display_name="A")
    p2 = Principal(display_name="B")
    adapter = InMemoryPlatformTrustAdapter(
        identities={p1.id: {"verified": True}, p2.id: {"verified": True}},
        balances={(p1.id, "CNY"): 100.0},
    )
    from towow_sjac.models import Commitment
    c1 = Commitment(debtor=p1.id, creditor=p2.id, performance={}, evidence_rule={}, deadline=datetime.now(timezone.utc)+timedelta(days=1))
    c2 = Commitment(debtor=p1.id, creditor=p2.id, performance={}, evidence_rule={}, deadline=datetime.now(timezone.utc)+timedelta(days=1))
    adapter.reserve(c1, "CNY", 80)
    try:
        adapter.reserve(c2, "CNY", 30)
        assert False, "double reservation should fail"
    except ValueError:
        pass
