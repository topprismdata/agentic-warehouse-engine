"""
or_experts/b0_random.py — Baseline B0 (Random).

Spec anchor: §16.2 B0 — "Current / Random".
Cost basis: total route distance (Euclidean to entrance) across the 14-day horizon
under random SKU → location assignment. v0.1 uses entrance = (0, 0, 0).
"""

from __future__ import annotations

from collections import defaultdict
from typing import List, Dict, Tuple
import random

from world_state.schemas import (
    SkuMaster, Order, OrderLine, Location, SlotAssignment,
    DecisionPlan, ProblemType, RiskClass, SourceType,
)
from world_state.validate import validate_pipeline
from datetime import datetime, timezone


def _euclidean(xyz: Tuple[float, float, float]) -> float:
    return (xyz[0] ** 2 + xyz[1] ** 2 + xyz[2] ** 2) ** 0.5


def assign_random(
    sku_ids: List[str],
    pickable_locations: List[Location],
    xyz_lookup: Dict[str, Tuple[float, float, float]],
    decision_id: str,
    as_of: datetime,
    rng: random.Random,
    location_capacity: int = None,
) -> Tuple[List[SlotAssignment], Dict[str, str]]:
    """Random sku -> location, ONE assignment per sku, determinism via rng.

    v0.2 review F2 follow-up: a plan violating the hard capacity constraint is
    infeasible and would never pass an Execution Gateway (spec §14.2/§15.4) —
    so the "dumb" baseline draws a random FEASIBLE assignment (shuffle SKUs,
    fill locations up to capacity) instead of an infeasible one. Same ignorance,
    valid plan.
    """
    import math as _math
    n, L = len(sku_ids), len(pickable_locations)
    if location_capacity is None:
        location_capacity = max(1, _math.ceil(n / max(L, 1)))

    shuffled = list(sku_ids)
    rng.shuffle(shuffled)
    slots = [loc.location_id for loc in pickable_locations for _ in range(location_capacity)]

    sku_to_loc: Dict[str, str] = {}
    rows: List[SlotAssignment] = []
    for sku, loc in zip(shuffled, slots):
        sku_to_loc[sku] = loc
        rows.append(SlotAssignment(
            timestamp=as_of,
            sku_id=sku,
            location_id=loc,
            assigned_capacity=1.0,
            reason="B0_Random",
            decision_id=decision_id,
            source_type=SourceType.SYNTHETIC,
        ))
    # n <= L*capacity by construction of capacity — if more SKUs than slots,
    # wrap (only possible when capacity was passed explicitly too small)
    for i, sku in enumerate(shuffled[len(slots):]):
        loc = pickable_locations[i % L].location_id
        sku_to_loc[sku] = loc
        rows.append(SlotAssignment(
            timestamp=as_of, sku_id=sku, location_id=loc, assigned_capacity=1.0,
            reason="B0_Random", decision_id=decision_id,
            source_type=SourceType.SYNTHETIC,
        ))
    return rows, sku_to_loc


def replay_total_pick_distance(
    orders: List[Order],
    order_lines: List[OrderLine],
    sku_to_loc: Dict[str, str],
    xyz_lookup: Dict[str, Tuple[float, float, float]],
) -> float:
    """Sum of Euclidean distances from entrance to the picked location, per line."""
    if not order_lines:
        return 0.0
    total = 0.0
    entrance = (0.0, 0.0, 0.0)
    for line in order_lines:
        loc = sku_to_loc.get(line.sku_id)
        if loc is None:
            continue
        xyz = xyz_lookup.get(loc, entrance)
        total += _euclidean(xyz) * line.quantity
    return float(total)


def build_decision_plan(
    assignments: List[SlotAssignment],
    expected_cost: float,
    baseline_cost: float,
    confidence: float = 0.0,
) -> DecisionPlan:
    return DecisionPlan(
        decision_id=f"DP-B0-{assignments[0].timestamp.isoformat()}",
        problem_type=ProblemType.DYNAMIC_SLOTTING,
        horizon_start=assignments[0].timestamp,
        horizon_end=assignments[0].timestamp,
        actions=[
            {"action": f"MOVE {a.sku_id} -> {a.location_id}",
             "reason": a.reason, "expected_saving": 0.0, "confidence": confidence}
            for a in assignments
        ],
        expected_cost=expected_cost,
        baseline_cost=baseline_cost,
        confidence=confidence,
        verifier_status="feasible",
        approval_status="auto",
        risk_class=RiskClass.LOW,
        model_version="B0_Random@v0.1",
        constraint_version="v0.1.0",
        lineage=SourceType.DERIVED,
        source_type=SourceType.DERIVED,
    )
