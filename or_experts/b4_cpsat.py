"""
or_experts/b4_cpsat.py — Expert B4 (CP-SAT joint frequency + affinity).

Spec anchor: §11.2 Skill/Algorithm Card (CP-SAT example), §12.3 candidate
locations, §14.1 small/medium scale, Appendix C.2 solver return schema.

Model (all linear — the quadratic affinity term is linearized via position
ranks, per spec §12.4 two-stage collapsed to one assignment problem):

  vars    x[i,l] ∈ {0,1}           sku i assigned location l
           pos[i] ∈ [0, L-1]        = Σ_l rank_l · x[i,l]      (aux, linear)
           d[i,j] ≥ 0               ≥ |pos[i] − pos[j]|        (aux, linear)
  s.t.     Σ_l x[i,l] = 1           ∀i  (each sku exactly one location)
  obj      min  Σ_i freq_i · dist_l · x[i,l]                 (travel term)
             + λ · Σ_(i,j)∈TopK A_ij · d[i,j]                 (affinity term)

Candidate locations (spec §12.3): hard-filter first, cap at max_candidates
per SKU. With n_locations ≤ 100 all locations qualify at v0.1 scale.

λ (lambda_affinity) is the freq-vs-affinity tradeoff; R03 sweeps it.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from ortools.sat.python import cp_model

from world_state.schemas import (
    OrderLine, Location, SlotAssignment, DecisionPlan,
    ProblemType, RiskClass, SourceType,
)
from features.affinity import AffinityGraph
from datetime import datetime


def _euclidean(xyz: Tuple[float, float, float]) -> float:
    return (xyz[0] ** 2 + xyz[1] ** 2 + xyz[2] ** 2) ** 0.5


@dataclass
class SolverReport:
    """Appendix C.2 contract: status / objective / actions / stats / fallback."""
    status: str                     # feasible / infeasible / timeout / error
    objective_value: Optional[float]
    solver_stats: Dict[str, float] = field(default_factory=dict)
    fallback_used: bool = False
    fallback_reason: str = ""

    def to_dict(self):
        return {
            "status": self.status,
            "objective_value": self.objective_value,
            "solver_stats": self.solver_stats,
            "fallback_used": self.fallback_used,
            "fallback_reason": self.fallback_reason,
        }


def solve_cpsat(
    sku_ids: List[str],
    order_lines: List[OrderLine],
    affinity: AffinityGraph,
    pickable_locations: List[Location],
    xyz_lookup: Dict[str, Tuple[float, float, float]],
    lambda_affinity: float = 0.5,
    time_budget_s: float = 10.0,
    max_candidates_per_sku: int = 100,
    location_capacity: Optional[int] = None,
    verbose: bool = False,
) -> Tuple[List[SlotAssignment], Dict[str, str], SolverReport]:
    # --- inputs ---------------------------------------------------------------
    freq: Dict[str, float] = {}
    for line in order_lines:
        freq[line.sku_id] = freq.get(line.sku_id, 0.0) + line.quantity

    # locations ranked by distance (rank 0 = nearest entrance)
    ranked = sorted(pickable_locations, key=lambda l: _euclidean((l.x, l.y, l.z)))
    L = len(ranked)
    dist = [_euclidean((l.x, l.y, l.z)) for l in ranked]
    # scale ranks to meter-space so the two objective terms share units
    rank_scale = (max(dist) / max(L - 1, 1)) if L > 1 else 1.0

    freq_scale = max(freq.values()) if freq else 1.0
    aff_scale = max((a for _, nbrs in affinity.topk.items() for _, a in nbrs), default=1.0) or 1.0

    m = cp_model.CpModel()
    n = len(sku_ids)
    idx = {s: i for i, s in enumerate(sku_ids)}

    # Location capacity (spec §10.4 hard constraint): without it the solver parks
    # ALL high-frequency SKUs at the nearest location — mathematically optimal,
    # physically nonsense. Default = uniform ceil(n/L) (what B1's round-robin implies).
    if location_capacity is None:
        location_capacity = max(1, math.ceil(n / L))

    # x[i][l]
    x = [[m.NewBoolVar(f"x_{i}_{l}") for l in range(L)] for i in range(n)]
    for i in range(n):
        m.AddExactlyOne(x[i])
    for l in range(L):
        m.Add(sum(x[i][l] for i in range(n)) <= location_capacity)

    # pos[i] = Σ_l l · x[i][l]  (rank index)
    pos = [m.NewIntVar(0, L - 1, f"pos_{i}") for i in range(n)]
    for i in range(n):
        m.Add(pos[i] == sum(l * x[i][l] for l in range(L)))

    # travel term (normalized by freq_scale)
    travel_terms = []
    for i, s in enumerate(sku_ids):
        f = freq.get(s, 0.0) / freq_scale
        for l in range(L):
            travel_terms.append(f * dist[l] * x[i][l])

    # affinity term (normalized by aff_scale): d[i,j] ≥ |pos_i - pos_j|
    edge_terms = []
    seen = set()
    d_vars = {}
    for s, nbrs in affinity.topk.items():
        if s not in idx:
            continue
        for j_sku, a_ij in nbrs:
            if j_sku not in idx:
                continue
            key = (min(s, j_sku), max(s, j_sku))
            if key in seen:
                continue
            seen.add(key)
            i, j = idx[s], idx[j_sku]
            d = m.NewIntVar(0, L - 1, f"d_{i}_{j}")
            m.Add(d >= pos[i] - pos[j])
            m.Add(d >= pos[j] - pos[i])
            d_vars[key] = d
            edge_terms.append((a_ij / aff_scale) * d)

    m.Minimize(sum(travel_terms) + lambda_affinity * rank_scale * sum(edge_terms))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_budget_s
    status_code = solver.Solve(m)

    if status_code not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return [], {}, SolverReport(
            status="infeasible" if status_code == cp_model.INFEASIBLE else "timeout",
            objective_value=None,
            solver_stats={"status_code": int(status_code)},
            fallback_used=False,
        )

    gap = 0.0
    if status_code == cp_model.FEASIBLE:
        bound = solver.BestObjectiveBound()
        obj = solver.ObjectiveValue()
        gap = abs(obj - bound) / max(abs(obj), 1e-9)

    sku_to_loc: Dict[str, str] = {}
    rows: List[SlotAssignment] = []
    as_of = datetime(2025, 1, 1, tzinfo=__import__("datetime").timezone.utc)
    for i, s in enumerate(sku_ids):
        for l in range(L):
            if solver.Value(x[i][l]):
                sku_to_loc[s] = ranked[l].location_id
                rows.append(SlotAssignment(
                    timestamp=as_of,
                    sku_id=s,
                    location_id=ranked[l].location_id,
                    assigned_capacity=1.0,
                    reason=f"B4_CPSAT(lambda={lambda_affinity})",
                    decision_id="DP-B4",
                    source_type=SourceType.SYNTHETIC,
                ))
                break

    report = SolverReport(
        status="feasible",
        objective_value=float(solver.ObjectiveValue()),
        solver_stats={
            "wall_time_s": solver.WallTime(),
            "branches": float(solver.NumBranches()),
            "deterministic_time": solver.ResponseProto().deterministic_time,
            "optimal": status_code == cp_model.OPTIMAL,
            "gap_relative": gap,
        },
    )
    if verbose:
        print(f"[cpsat] {report.to_dict()}")
    return rows, sku_to_loc, report
