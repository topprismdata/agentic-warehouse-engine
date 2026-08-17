"""
or_experts/e4_e7.py — Experts E4–E7 for the OR Expert Library v1 (spec update §5).

E4 Forecast Dynamic ABC : rank by forecast p50 (informed: promotions known)
E5 Robust Slotting      : rank by p50 penalized by forecast spread (risk-adjusted)
E6 Forecast+Affinity    : CP-SAT travel weighted by p50 + affinity term
E7 Rolling-Horizon lite : CP-SAT over (new assignment + move penalties) —
                          move_cost high ⇒ optimal ≈ keep current layout.
                          Full multi-period rolling is Step 10; this is the
                          single-window reduction (declared).
All capacity-aware (ceil(n/L), spec §10.4) and audited by the caller.
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple

from ortools.sat.python import cp_model

from world_state.schemas import (
    OrderLine, Location, SlotAssignment, DecisionPlan,
    ProblemType, RiskClass, SourceType,
)
from features.affinity import AffinityGraph
from features.forecast import SkuForecast
from datetime import datetime, timezone


def _ranked_locations(pickable: List[Location]):
    return sorted(pickable, key=lambda l: math.dist((l.x, l.y, l.z), (0, 0, 0)))


def _capacity(n: int, L: int) -> int:
    return max(1, math.ceil(n / max(L, 1)))


def _fill_by_score(sku_score: Dict[str, float], sku_ids, locs, reason, decision_id, as_of,
                   location_capacity=None):
    """Assign highest score to nearest location with remaining capacity."""
    L = len(locs)
    cap = location_capacity or _capacity(len(sku_ids), L)
    remaining = {l.location_id: cap for l in locs}
    sku_to_loc, rows = {}, []
    for sku in sorted(sku_ids, key=lambda s: sku_score.get(s, 0.0), reverse=True):
        placed = False
        for l in locs:
            if remaining[l.location_id] > 0:
                remaining[l.location_id] -= 1
                sku_to_loc[sku] = l.location_id
                rows.append(SlotAssignment(timestamp=as_of, sku_id=sku,
                                           location_id=l.location_id,
                                           assigned_capacity=1.0, reason=reason,
                                           decision_id=decision_id,
                                           source_type=SourceType.SYNTHETIC))
                placed = True
                break
        if not placed:
            raise RuntimeError(f"capacity exhausted placing {sku}")
    return rows, sku_to_loc


# --- E4: forecast dynamic ABC -------------------------------------------------

def assign_e4_forecast_abc(sku_ids, fc: Dict[str, SkuForecast], pickable, decision_id, as_of):
    locs = _ranked_locations(pickable)
    score = {s: fc[s].p50 for s in sku_ids}
    return _fill_by_score(score, sku_ids, locs, "E4_ForecastABC", decision_id, as_of)


# --- E5: robust slotting (spread-penalized) ------------------------------------

def assign_e5_robust(sku_ids, fc: Dict[str, SkuForecast], pickable, decision_id, as_of,
                     kappa: float = 0.5):
    """score = p50 - kappa * (p90 - p10): high-uncertainty SKUs lose golden
    slots. With flat uncertainty (R1) E5 ≈ E4; under R5 it degrades gracefully."""
    locs = _ranked_locations(pickable)
    score = {s: fc[s].p50 - kappa * (fc[s].p90 - fc[s].p10) for s in sku_ids}
    return _fill_by_score(score, sku_ids, locs, "E5_Robust", decision_id, as_of)


# --- E6: forecast + affinity via CP-SAT -----------------------------------------

def assign_e6_forecast_affinity(sku_ids, fc, affinity: AffinityGraph, pickable,
                                xyz_lookup, decision_id, as_of,
                                lambda_affinity: float = 0.3,
                                time_budget_s: float = 0.1,
                                fmax_ref: float = None):
    """fmax_ref: STABLE normalization (e.g. max historical frequency). If the
    regime input (promotion x8) inflates the in-model max, every other SKU's
    travel weight gets compressed 8x and the affinity term silently dominates —
    R09 review caught E6 producing nonsense clusterings on R2 this way."""
    ranked = _ranked_locations(pickable)
    L = len(ranked)
    dist = [math.dist((l.x, l.y, l.z), (0, 0, 0)) for l in ranked]
    n = len(sku_ids)
    cap = _capacity(n, L)
    rank_scale = (max(dist) / max(L - 1, 1)) if L > 1 else 1.0
    fmax = fmax_ref or max((fc[s].p50 for s in sku_ids), default=1.0) or 1.0
    amax = max((a for nbrs in affinity.topk.values() for _, a in nbrs), default=1.0) or 1.0

    m = cp_model.CpModel()
    idx = {s: i for i, s in enumerate(sku_ids)}
    x = [[m.NewBoolVar(f"x{i}_{l}") for l in range(L)] for i in range(n)]
    pos = [m.NewIntVar(0, L - 1, f"p{i}") for i in range(n)]
    for i in range(n):
        m.AddExactlyOne(x[i])
        m.Add(pos[i] == sum(l * x[i][l] for l in range(L)))
    for l in range(L):
        m.Add(sum(x[i][l] for i in range(n)) <= cap)

    terms = []
    for i, s in enumerate(sku_ids):
        f = fc[s].p50 / fmax
        for l in range(L):
            terms.append(f * dist[l] * x[i][l])
    seen = set()
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
            d = m.NewIntVar(0, L - 1, f"d{i}_{j}")
            m.Add(d >= pos[i] - pos[j])
            m.Add(d >= pos[j] - pos[i])
            terms.append(lambda_affinity * rank_scale * (a_ij / amax) * d)
    m.Minimize(sum(terms))

    solver = cp_model.CpSolver()
    # DETERMINISM (R11 review): wall-clock budget + multithreading made the
    # same solve return different incumbents — beam search and its replay
    # disagreed (0.2% cost mismatch). Benchmarks must be reproducible: single
    # worker + deterministic-time budget.
    solver.parameters.num_search_workers = 1
    solver.parameters.max_deterministic_time = time_budget_s
    st = solver.Solve(m)
    if st not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        raise RuntimeError("E6 infeasible")

    sku_to_loc, rows = {}, []
    for i, s in enumerate(sku_ids):
        for l in range(L):
            if solver.Value(x[i][l]):
                sku_to_loc[s] = ranked[l].location_id
                rows.append(SlotAssignment(timestamp=as_of, sku_id=s,
                                           location_id=ranked[l].location_id,
                                           assigned_capacity=1.0,
                                           reason=f"E6_FcAff(l={lambda_affinity})",
                                           decision_id=decision_id,
                                           source_type=SourceType.SYNTHETIC))
                break
    return rows, sku_to_loc


# --- E7: rolling-horizon lite (re-slot with move penalties) ---------------------

def assign_e7_rolling_lite(sku_ids, fc, pickable, xyz_lookup, current_loc: Dict[str, str],
                           decision_id, as_of,
                           move_cost: float = 0.0,
                           time_budget_s: float = 0.1):
    """Single-window reduction of rolling-horizon: minimize expected pick cost
    PLUS move_cost per changed assignment (ABSOLUTE magnitudes — no fmax
    normalization, which under promotion scaled every travel term down 8x and
    froze the solver; R09 review). Caller passes
    move_cost = 0.15 * fmax_hist * mean_dist * regime_scale so R1 keeps the
    incumbent, R2 moves promoted SKUs, R6 (x20) freezes everything."""
    ranked = _ranked_locations(pickable)
    L = len(ranked)
    dist = [math.dist((l.x, l.y, l.z), (0, 0, 0)) for l in ranked]
    n = len(sku_ids)
    cap = _capacity(n, L)
    loc_pos = {l.location_id: k for k, l in enumerate(ranked)}

    m = cp_model.CpModel()
    x = [[m.NewBoolVar(f"x{i}_{l}") for l in range(L)] for i in range(n)]
    y = [m.NewBoolVar(f"y{i}") for i in range(n)]  # 1 = sku moves
    for i in range(n):
        m.AddExactlyOne(x[i])
        for l in range(L):
            cur = loc_pos.get(current_loc.get(sku_ids[i]))
            if cur is not None and cur != l:
                m.AddImplication(x[i][l], y[i])
    for l in range(L):
        m.Add(sum(x[i][l] for i in range(n)) <= cap)

    # scale move_cost into the same units as pick distance: pick term is
    # (freq/fmax)*dist summed; a move is worth `move_cost` distance-equivalents
    terms = []
    for i, s in enumerate(sku_ids):
        f = fc[s].p50                      # ABSOLUTE: promotion raises a SKU's
        for l in range(L):                 # weight without compressing others
            terms.append(f * dist[l] * x[i][l])
        terms.append(move_cost * y[i])
    m.Minimize(sum(terms))

    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = 1
    solver.parameters.max_deterministic_time = time_budget_s
    st = solver.Solve(m)
    if st not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        raise RuntimeError("E7 infeasible")

    sku_to_loc, rows = {}, []
    for i, s in enumerate(sku_ids):
        for l in range(L):
            if solver.Value(x[i][l]):
                sku_to_loc[s] = ranked[l].location_id
                rows.append(SlotAssignment(timestamp=as_of, sku_id=s,
                                           location_id=ranked[l].location_id,
                                           assigned_capacity=1.0,
                                           reason=f"E7_RollingLite(mc={move_cost:.0f})",
                                           decision_id=decision_id,
                                           source_type=SourceType.SYNTHETIC))
                break
    return rows, sku_to_loc
