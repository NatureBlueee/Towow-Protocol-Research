from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib import font_manager

plt.rcParams["axes.unicode_minus"] = False
import numpy as np
import pandas as pd
from scipy.optimize import linprog
from scipy.special import expit, logit
from scipy.stats import beta
from sklearn.isotonic import IsotonicRegression

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "code"))

from towow_sjac.column_generation import Mode, column_generate, solve_integer
from towow_sjac.engine import PolyhedralBoundaryCoordinator
from towow_sjac.oracles import PolytopeOracle

RNG = np.random.default_rng(20260724)
RESULTS = ROOT / "results"
FIGURES = ROOT / "figures"
RESULTS.mkdir(exist_ok=True)
FIGURES.mkdir(exist_ok=True)


def linprog_max(c, A, b, bounds):
    res = linprog(-c, A_ub=A, b_ub=b, bounds=bounds, method="highs")
    return res


def boundary_oracle_experiment(instances: int = 300, d: int = 8, n_agents: int = 5, m: int = 18):
    rows = []
    for inst in range(instances):
        center = RNG.uniform(0.12, 0.28, size=d)
        c = RNG.uniform(0.2, 1.0, size=d)
        c /= np.linalg.norm(c)
        all_A, all_b, per_agent = [], [], []
        for a in range(n_agents):
            A = RNG.gamma(shape=1.5, scale=1.0, size=(m, d))
            A /= np.linalg.norm(A, axis=1, keepdims=True)
            slack = RNG.uniform(0.05, 0.35, size=m)
            b = A @ center + slack
            all_A.append(A)
            all_b.append(b)
            per_agent.append((A, b))
        A_full = np.vstack(all_A)
        b_full = np.concatenate(all_b)
        bounds = [(0.0, 1.0)] * d
        full = linprog_max(c, A_full, b_full, bounds)
        if not full.success or -full.fun <= 1e-9:
            continue
        opt = -float(full.fun)

        for seed_per_agent in (1, 2, 4, 8):
            seed_A, seed_b = [], []
            seed_indices = []
            for A, b in per_agent:
                idx = RNG.choice(m, size=seed_per_agent, replace=False)
                seed_indices.append(idx)
                seed_A.extend(A[idx])
                seed_b.extend(b[idx])
            seed_A_np = np.asarray(seed_A)
            seed_b_np = np.asarray(seed_b)
            static = linprog_max(c, seed_A_np, seed_b_np, bounds)
            if static.success:
                y = static.x
                violation = float(np.max(A_full @ y - b_full))
                feasible = violation <= 1e-8
                obj = float(c @ y)
            else:
                feasible, obj, violation = False, np.nan, np.inf
            rows.append({
                "instance": inst,
                "method": f"static_{seed_per_agent}",
                "seed_per_agent": seed_per_agent,
                "feasible": feasible,
                "objective_ratio": obj / opt if feasible else np.nan,
                "proposed_objective_ratio": obj / opt if np.isfinite(obj) else np.nan,
                "max_violation": violation,
                "disclosed_constraints": seed_per_agent * n_agents,
                "rounds": 1,
            })

            oracles = [PolytopeOracle(f"p{j}", A, b) for j, (A, b) in enumerate(per_agent)]
            engine = PolyhedralBoundaryCoordinator(d, c, oracles, bounds=bounds)
            for aa, bb in zip(seed_A_np, seed_b_np):
                engine.seed_cut(aa, bb)
            adaptive = engine.solve(max_iterations=250)
            if adaptive.feasible:
                y2 = adaptive.vector
                violation2 = float(np.max(A_full @ y2 - b_full))
                obj2 = float(c @ y2)
            else:
                violation2, obj2 = np.inf, np.nan
            rows.append({
                "instance": inst,
                "method": f"adaptive_{seed_per_agent}",
                "seed_per_agent": seed_per_agent,
                "feasible": bool(adaptive.feasible and violation2 <= 1e-8),
                "objective_ratio": obj2 / opt if adaptive.feasible else np.nan,
                "proposed_objective_ratio": obj2 / opt if adaptive.feasible else np.nan,
                "max_violation": violation2,
                "disclosed_constraints": adaptive.disclosed_cuts,
                "rounds": adaptive.iterations,
            })

        rows.append({
            "instance": inst,
            "method": "full_disclosure",
            "seed_per_agent": m,
            "feasible": True,
            "objective_ratio": 1.0,
            "proposed_objective_ratio": 1.0,
            "max_violation": float(np.max(A_full @ full.x - b_full)),
            "disclosed_constraints": m * n_agents,
            "rounds": 1,
        })

    df = pd.DataFrame(rows)
    df.to_csv(RESULTS / "boundary_oracle_trials.csv", index=False)
    summary = df.groupby("method", as_index=False).agg(
        feasibility_rate=("feasible", "mean"),
        mean_objective_ratio=("objective_ratio", "mean"),
        median_disclosed_constraints=("disclosed_constraints", "median"),
        mean_rounds=("rounds", "mean"),
        mean_max_violation=("max_violation", lambda s: np.nanmean(np.where(np.isfinite(s), s, np.nan))),
    )
    summary.to_csv(RESULTS / "boundary_oracle_summary.csv", index=False)

    order = ["static_1", "adaptive_1", "static_2", "adaptive_2", "static_4", "adaptive_4", "static_8", "adaptive_8", "full_disclosure"]
    plot = summary.set_index("method").reindex(order)
    fig, ax = plt.subplots(figsize=(10, 5.4))
    x = np.arange(len(plot))
    ax.bar(x, plot["feasibility_rate"])
    ax.set_xticks(x, [s.replace("_", "\n") for s in plot.index])
    ax.set_ylim(0, 1.08)
    ax.set_ylabel("True feasibility rate")
    ax.set_title("Static projection vs. adaptive boundary oracles")
    for i, value in enumerate(plot["feasibility_rate"]):
        ax.text(i, value + 0.025, f"{value:.2f}", ha="center", fontsize=9)
    fig.tight_layout()
    fig.savefig(FIGURES / "boundary_feasibility.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(9, 5.2))
    ax.scatter(summary["median_disclosed_constraints"], summary["feasibility_rate"], s=70)
    for _, row in summary.iterrows():
        ax.annotate(row["method"], (row["median_disclosed_constraints"], row["feasibility_rate"]), xytext=(5, 5), textcoords="offset points", fontsize=8)
    ax.set_xlabel("Median number of disclosed boundary constraints")
    ax.set_ylabel("True feasibility rate")
    ax.set_title("Feasibility–disclosure trade-off")
    ax.set_ylim(0, 1.08)
    fig.tight_layout()
    fig.savefig(FIGURES / "boundary_disclosure_tradeoff.png", dpi=180)
    plt.close(fig)
    return summary


def generate_mode_instance(n_agents=24, n_caps=12):
    required = np.ones(n_caps, dtype=float)
    modes: list[Mode] = []
    mode_id = 0
    # Every agent has one public, low-bandwidth profile mode.
    for agent in range(n_agents):
        k = int(RNG.integers(1, 3))
        caps = np.zeros(n_caps, dtype=int)
        # Public descriptions overrepresent common first 8 capabilities.
        weights = np.array([1.0]*8 + [0.35]*(n_caps-8), dtype=float)
        weights /= weights.sum()
        caps[RNG.choice(n_caps, size=k, replace=False, p=weights)] = 1
        modes.append(Mode(agent, mode_id, caps, float(RNG.uniform(1.0, 4.5)), True))
        mode_id += 1
        for _ in range(int(RNG.integers(1, 4))):
            k2 = int(RNG.integers(2, 5))
            caps2 = np.zeros(n_caps, dtype=int)
            caps2[RNG.choice(n_caps, size=k2, replace=False)] = 1
            modes.append(Mode(agent, mode_id, caps2, float(RNG.uniform(1.0, 5.0)), False))
            mode_id += 1
    # Plant a feasible complementarity structure in hidden modes, especially rare caps.
    perm = RNG.permutation(n_agents)[:4]
    chunks = np.array_split(np.arange(n_caps), 4)
    for agent, chunk in zip(perm, chunks):
        caps = np.zeros(n_caps, dtype=int)
        caps[chunk] = 1
        # Add one cross-capability to create nontrivial overlap.
        caps[int(RNG.integers(0, n_caps))] = 1
        modes.append(Mode(int(agent), mode_id, caps, float(RNG.uniform(1.0, 3.0)), False))
        mode_id += 1
    return required, modes


def team_constitution_experiment(instances: int = 300):
    rows = []
    for inst in range(instances):
        required, modes = generate_mode_instance()
        n_agents = max(m.agent for m in modes) + 1
        full = solve_integer(required, modes, n_agents)
        if not full.feasible:
            continue
        public = [m for m in modes if m.public]
        public_result = solve_integer(required, public, n_agents)
        rows.append({
            "instance": inst, "method": "public_profile_search",
            "feasible": public_result.feasible,
            "cost_ratio": public_result.cost / full.cost if public_result.feasible else np.nan,
            "disclosed_modes": len(public), "rounds": 1,
        })
        hidden = [m for m in modes if not m.public]
        reveal_count = max(1, int(0.20 * len(hidden)))
        revealed = list(public) + [hidden[i] for i in RNG.choice(len(hidden), size=reveal_count, replace=False)]
        random_result = solve_integer(required, revealed, n_agents)
        rows.append({
            "instance": inst, "method": "random_20pct_disclosure",
            "feasible": random_result.feasible,
            "cost_ratio": random_result.cost / full.cost if random_result.feasible else np.nan,
            "disclosed_modes": len(revealed), "rounds": 1,
        })
        cg = column_generate(required, modes, n_agents, max_rounds=30)
        rows.append({
            "instance": inst, "method": "price_guided_oracle",
            "feasible": cg.feasible,
            "cost_ratio": cg.cost / full.cost if cg.feasible else np.nan,
            "disclosed_modes": cg.disclosed_modes, "rounds": cg.rounds,
        })
        rows.append({
            "instance": inst, "method": "full_private_disclosure",
            "feasible": True, "cost_ratio": 1.0,
            "disclosed_modes": len(modes), "rounds": 1,
        })
    df = pd.DataFrame(rows)
    df.to_csv(RESULTS / "team_constitution_trials.csv", index=False)
    summary = df.groupby("method", as_index=False).agg(
        feasibility_rate=("feasible", "mean"),
        mean_cost_ratio=("cost_ratio", "mean"),
        median_disclosed_modes=("disclosed_modes", "median"),
        mean_rounds=("rounds", "mean"),
    )
    summary.to_csv(RESULTS / "team_constitution_summary.csv", index=False)

    order = ["public_profile_search", "random_20pct_disclosure", "price_guided_oracle", "full_private_disclosure"]
    plot = summary.set_index("method").reindex(order)
    fig, ax = plt.subplots(figsize=(9, 5.3))
    x = np.arange(len(plot))
    ax.bar(x, plot["feasibility_rate"])
    ax.set_xticks(x, ["Public profile\nsearch", "Random 20%\ndisclosure", "Price-guided\nlocal oracle", "Full private\ndisclosure"])
    ax.set_ylim(0, 1.08)
    ax.set_ylabel("Feasible multi-party arrangement rate")
    ax.set_title("Predefined search vs. open-world column generation")
    for i, value in enumerate(plot["feasibility_rate"]):
        ax.text(i, value + 0.025, f"{value:.2f}", ha="center", fontsize=9)
    fig.tight_layout()
    fig.savefig(FIGURES / "team_feasibility.png", dpi=180)
    plt.close(fig)
    return summary


def upper_failure_bound(errors: int, n: int, alpha: float = 0.05) -> float:
    if n == 0:
        return 1.0
    if errors == n:
        return 1.0
    return float(beta.ppf(1 - alpha, errors + 1, n - errors))


def select_threshold(scores, success, target_risk=0.05, min_n=100):
    candidates = np.unique(np.quantile(scores, np.linspace(0.0, 0.999, 500)))
    best = None
    for t in candidates:
        mask = scores >= t
        n = int(mask.sum())
        if n < min_n:
            continue
        errors = int((~success[mask]).sum())
        ub = upper_failure_bound(errors, n)
        if ub <= target_risk:
            coverage = n / len(scores)
            if best is None or coverage > best[0]:
                best = (coverage, float(t), errors / n, ub)
    return best


def evaluate_gate(name, scores, success, threshold):
    mask = scores >= threshold
    n = int(mask.sum())
    return {
        "method": name,
        "coverage": n / len(scores),
        "executed": n,
        "error_rate": float((~success[mask]).mean()) if n else np.nan,
        "threshold": threshold,
    }


def probabilistic_oracle_experiment(n_cal=16000, n_test=16000):
    def sample(n, drift=False):
        x1 = RNG.normal(0, 1, n)
        x2 = RNG.normal(0, 1, n)
        group = RNG.binomial(1, 0.25 if not drift else 0.45, n)
        true_logit = 1.5*x1 + 0.9*x2 - 0.4
        if drift:
            true_logit = true_logit - 1.8*group + 0.5*np.sin(2*x1)
        p = expit(true_logit)
        success = RNG.random(n) < p
        model_logit = 1.8*true_logit + 0.9 + RNG.normal(0, 0.8, n)
        if drift:
            # The model does not know a new subgroup failure mode and remains overconfident.
            model_logit = model_logit + 2.0*group
        raw = expit(model_logit)
        return raw, success.astype(bool), group

    cal_score, cal_y, _ = sample(n_cal, drift=False)
    id_score, id_y, _ = sample(n_test, drift=False)
    ood_score, ood_y, ood_group = sample(n_test, drift=True)
    iso = IsotonicRegression(out_of_bounds="clip")
    iso.fit(cal_score, cal_y.astype(int))
    cal_p = iso.predict(cal_score)
    id_p = iso.predict(id_score)
    ood_p = iso.predict(ood_score)
    chosen = select_threshold(cal_p, cal_y, target_risk=0.05, min_n=200)
    if chosen is None:
        threshold = 0.99
    else:
        threshold = chosen[1]
    rows = []
    for split, scores, y in [("in_distribution", id_p, id_y), ("distribution_shift", ood_p, ood_y)]:
        base = evaluate_gate("calibrated_fixed_gate", scores, y, threshold)
        base["split"] = split
        rows.append(base)
        ung = {"method": "unguarded", "split": split, "coverage": 1.0, "executed": len(y), "error_rate": float((~y).mean()), "threshold": 0.0}
        rows.append(ung)

    # Audited adaptive gate: process the shifted stream in batches, always audit a random
    # 20% and recalibrate on the most recent 4000 audited outcomes. This is an engineering
    # control, not a distribution-free guarantee.
    batch = 800
    audit_scores, audit_y = list(cal_score[-1000:]), list(cal_y[-1000:])
    executed, errors, total = 0, 0, 0
    thresholds = []
    for start in range(0, n_test, batch):
        s_raw = ood_score[start:start+batch]
        y = ood_y[start:start+batch]
        local_iso = IsotonicRegression(out_of_bounds="clip")
        local_iso.fit(np.asarray(audit_scores), np.asarray(audit_y, dtype=int))
        p = local_iso.predict(s_raw)
        cal_recent = local_iso.predict(np.asarray(audit_scores))
        selected = select_threshold(cal_recent, np.asarray(audit_y, dtype=bool), 0.05, min_n=80)
        t = selected[1] if selected else 1.01
        thresholds.append(t)
        mask = p >= t
        executed += int(mask.sum())
        errors += int((~y[mask]).sum())
        total += len(y)
        audit_mask = RNG.random(len(y)) < 0.20
        audit_scores.extend(s_raw[audit_mask].tolist())
        audit_y.extend(y[audit_mask].tolist())
        if len(audit_scores) > 4000:
            audit_scores = audit_scores[-4000:]
            audit_y = audit_y[-4000:]
    rows.append({
        "method": "audited_adaptive_gate", "split": "distribution_shift",
        "coverage": executed/total, "executed": executed,
        "error_rate": errors/executed if executed else np.nan,
        "threshold": float(np.mean(thresholds)),
    })

    df = pd.DataFrame(rows)
    df.to_csv(RESULTS / "probabilistic_oracle_summary.csv", index=False)
    fig, ax = plt.subplots(figsize=(9, 5.3))
    plot = df.copy()
    labels = [f"{r.method}\n{r.split}" for r in plot.itertuples()]
    x = np.arange(len(plot))
    ax.bar(x, plot["error_rate"])
    ax.axhline(0.05, linestyle="--", linewidth=1.5, label="Target risk 5%")
    ax.set_xticks(x, labels, rotation=20, ha="right")
    ax.set_ylabel("True failure rate among executed actions")
    ax.set_title("Risk can be managed, not guaranteed under unrestricted shift")
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIGURES / "probability_shift.png", dpi=180)
    plt.close(fig)
    return df


def trust_concurrency_experiment(trials=100000):
    balance = 100.0
    a = RNG.uniform(10, 100, trials)
    b = RNG.uniform(10, 100, trials)
    naive_both_accept = (a <= balance) & (b <= balance)
    naive_overspend = naive_both_accept & ((a+b) > balance)
    serial_overspend = np.zeros(trials, dtype=bool)
    summary = pd.DataFrame([
        {"method": "eventual_check_then_write", "overspend_rate": float(naive_overspend.mean())},
        {"method": "serializable_reservation", "overspend_rate": float(serial_overspend.mean())},
    ])
    summary.to_csv(RESULTS / "trust_concurrency_summary.csv", index=False)
    return summary


def main():
    summaries = {
        "boundary_oracle": boundary_oracle_experiment().to_dict(orient="records"),
        "team_constitution": team_constitution_experiment().to_dict(orient="records"),
        "probabilistic_oracle": probabilistic_oracle_experiment().to_dict(orient="records"),
        "trust_concurrency": trust_concurrency_experiment().to_dict(orient="records"),
    }
    with open(RESULTS / "manifest.json", "w", encoding="utf-8") as f:
        clean = json.loads(json.dumps(summaries, ensure_ascii=False, allow_nan=True).replace("NaN", "null"))
        json.dump(clean, f, ensure_ascii=False, indent=2, allow_nan=False)
    print(json.dumps(summaries, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
