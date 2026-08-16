"""
or_experts/b1_static_abc.py — Baseline B1 (Static ABC).

Spec anchor: §16.2 B1 — "Static ABC: historical Pick Frequency".
Classic rank-by-frequency approach. v0.1:

  - Compute pick_frequency[sku] = total quantity over all orders
  - Sort SKUs by frequency DESC, sort pickable locations by distance ASC
  - Assign rank-i SKU to rank-i location

This is intentionally a *static* baseline (no future forecast, no affinity).
It anchors NormalizedCost = 1.0 — every other expert's cost is divided by B1's.
"""

from __future__ import annotations

from collections import defaultdict
from typing import List, Dict, Tuple
import random

from world_state.schemas import (
    SkuMaster, Order, OrderLine, Location, SlotAssignment,
    DecisionPlan, ProblemType, RiskClass, SourceType,
)
from datetime import datetime, timezone


def _euclidean(xyz: Tuple[float, float, float]) -> float:
    return (xyz[0] ** 2 + xyz[1] ** 2 + xyz[2] ** 2) ** 0.5


def assign_static_abc(
    sku_ids: List[str],
    order_lines: List[OrderLine],
    pickable_locations: List[Location],
    xyz_lookup: Dict[str, Tuple[float, float, float]],
    decision_id: str,
    as_of: datetime,
) -> Tuple[List[SlotAssignment], Dict[str, str]]:
    """Static ABC — rank by historical pick frequency, FILL nearest locations
    to capacity before moving further away.

    v1.1 fix (R09 review): the original round-robin (rank i -> loc i mod L)
    stuffed a LOW-frequency SKU into the nearest location's second capacity
    slot whenever n > L, systematically mis-slotting the 2nd-highest SKU. That
    defect leaked into every benchmark anchored on B1 (R01-R08); those runs
    are re-executed and re-numbered after this fix.
    """
    freq: Dict[str, float] = defaultdict(float)
    for line in order_lines:
        freq[line.sku_id] += line.quantity

    ranked_skus = sorted(sku_ids, key=lambda s: freq.get(s, 0.0), reverse=True)
    ranked_locs = sorted(pickable_locations, key=lambda l: _euclidean((l.x, l.y, l.z)))

    import math as _math
    cap = max(1, _math.ceil(len(sku_ids) / len(ranked_locs)))
    remaining = {l.location_id: cap for l in ranked_locs}

    sku_to_loc: Dict[str, str] = {}
    rows: List[SlotAssignment] = []
    for sku in ranked_skus:
        placed = None
        for l in ranked_locs:
            if remaining[l.location_id] > 0:
                placed = l
                break
        if placed is None:
            raise RuntimeError(f"E1 capacity exhausted at {sku}")
        remaining[placed.location_id] -= 1
        sku_to_loc[sku] = placed.location_id
        rows.append(SlotAssignment(
            timestamp=as_of,
            sku_id=sku,
            location_id=placed.location_id,
            assigned_capacity=1.0,
            reason="E1_StaticABC",
            decision_id=decision_id,
            source_type=SourceType.SYNTHETIC,
        ))
    return rows, sku_to_loc


def total_pick_distance(
    order_lines: List[OrderLine],
    sku_to_loc: Dict[str, str],
    xyz_lookup: Dict[str, Tuple[float, float, float]],
) -> float:
    """Sum of distances × quantity across all pick lines."""
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
    confidence: float = 1.0,
) -> DecisionPlan:
    """B1 is the deterministic baseline; confidence=1.0 by construction."""
    return DecisionPlan(
        decision_id=f"DP-B1-{assignments[0].timestamp.isoformat()}",
        problem_type=ProblemType.DYNAMIC_SLOTTING,
        horizon_start=assignments[0].timestamp,
        horizon_end=assignments[0].timestamp,
        actions=[
            {"action": f"ASSIGN {a.sku_id} -> {a.location_id}",
             "reason": "B1_StaticABC",
             "expected_saving": baseline_cost - expected_cost if a == assignments[0] else 0.0,
             "confidence": confidence}
            for a in assignments
        ],
        expected_cost=expected_cost,
        baseline_cost=baseline_cost,
        confidence=confidence,
        verifier_status="feasible",
        approval_status="auto",
        risk_class=RiskClass.LOW,
        model_version="B1_StaticABC@v0.1",
        constraint_version="v0.1.0",
        lineage=SourceType.DERIVED,
        source_type=SourceType.DERIVED,
    )
