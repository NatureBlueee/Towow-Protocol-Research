from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, linprog, milp


@dataclass(frozen=True)
class Mode:
    agent: int
    mode_id: int
    capabilities: np.ndarray
    cost: float
    public: bool = False


@dataclass
class TeamSynthesisResult:
    feasible: bool
    cost: float | None
    selected: list[Mode]
    disclosed_modes: int
    rounds: int


def solve_integer(required: np.ndarray, modes: list[Mode], n_agents: int, max_team_size: int = 6) -> TeamSynthesisResult:
    if not modes:
        return TeamSynthesisResult(False, None, [], 0, 0)
    c = np.array([m.cost for m in modes], dtype=float)
    cap = np.stack([m.capabilities for m in modes], axis=1)
    agent = np.zeros((n_agents, len(modes)))
    for j, m in enumerate(modes):
        agent[m.agent, j] = 1.0
    constraints = [
        LinearConstraint(cap, lb=required, ub=np.full_like(required, np.inf, dtype=float)),
        LinearConstraint(agent, lb=np.zeros(n_agents), ub=np.ones(n_agents)),
        LinearConstraint(np.ones((1, len(modes))), lb=np.array([0.0]), ub=np.array([float(max_team_size)])),
    ]
    res = milp(c, integrality=np.ones(len(modes)), bounds=Bounds(0, 1), constraints=constraints)
    if not res.success:
        return TeamSynthesisResult(False, None, [], len(modes), 0)
    selected = [m for m, x in zip(modes, res.x) if x > 0.5]
    return TeamSynthesisResult(True, float(res.fun), selected, len(modes), 0)


def column_generate(
    required: np.ndarray,
    all_modes: list[Mode],
    n_agents: int,
    max_rounds: int = 30,
    artificial_cost: float = 100.0,
) -> TeamSynthesisResult:
    known = [m for m in all_modes if m.public]
    known_keys = {(m.agent, m.mode_id) for m in known}
    n_caps = len(required)
    # Artificial capability columns keep restricted LP feasible and create useful dual prices.
    artificial = [Mode(n_agents + j, -1, np.eye(n_caps, dtype=int)[j], artificial_cost, True) for j in range(n_caps)]

    for round_idx in range(1, max_rounds + 1):
        cols = known + artificial
        c = np.array([m.cost for m in cols], dtype=float)
        cap = np.stack([m.capabilities for m in cols], axis=1)
        agent = np.zeros((n_agents, len(cols)))
        for j, m in enumerate(cols):
            if m.agent < n_agents:
                agent[m.agent, j] = 1.0
        A_ub = np.vstack([-cap, agent])
        b_ub = np.concatenate([-required, np.ones(n_agents)])
        lp = linprog(c, A_ub=A_ub, b_ub=b_ub, bounds=[(0, 1)] * len(cols), method="highs")
        if not lp.success:
            break
        marg = np.asarray(lp.ineqlin.marginals)
        pi = -marg[:n_caps]
        mu = marg[n_caps:]
        additions: list[tuple[float, Mode]] = []
        for mode in all_modes:
            key = (mode.agent, mode.mode_id)
            if key in known_keys:
                continue
            reduced = mode.cost - float(pi @ mode.capabilities) + float(mu[mode.agent])
            if reduced < -1e-8:
                additions.append((reduced, mode))
        if not additions:
            break
        # Each sovereign agent reveals at most its best improving mode in a round.
        best_by_agent: dict[int, tuple[float, Mode]] = {}
        for item in additions:
            current = best_by_agent.get(item[1].agent)
            if current is None or item[0] < current[0]:
                best_by_agent[item[1].agent] = item
        for _, mode in best_by_agent.values():
            known.append(mode)
            known_keys.add((mode.agent, mode.mode_id))

    final = solve_integer(required, known, n_agents)
    final.disclosed_modes = len(known)
    final.rounds = round_idx
    return final
