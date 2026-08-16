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
    # 1. Compute pick frequency per sku across all orders (this is what spec §16.2 calls "Historical Pick Frequency")
    freq: Dict[str, float] = defaultdict(float)
    for line in order_lines:
        freq[line.sku_id] += line.quantity

    # SKUs we have no picks for still need *some* assignment; default freq=0 sorts last
    ranked_skus = sorted(sku_ids, key=lambda s: freq.get(s, 0.0), reverse=True)

    # 2. Pickable locations ranked by distance to entrance (closest first)
    ranked_locs = sorted(
        pickable_locations,
        key=lambda loc: _euclidean((loc.x, loc.y, loc.z)),
    )

    sku_to_loc: Dict[str, str] = {}
    rows: List[SlotAssignment] = []
    # 3. Assign one-to-one by rank. If sku count > location count, wrap (cycles).
    for i, sku in enumerate(ranked_skus):
        loc = ranked_locs[i % len(ranked_locs)]
        sku_to_loc[sku] = loc.location_id
        rows.append(SlotAssignment(
            timestamp=as_of,
            sku_id=sku,
            location_id=loc.location_id,
            assigned_capacity=1.0,
            reason="B1_StaticABC",
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
