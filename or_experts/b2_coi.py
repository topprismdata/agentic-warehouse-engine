"""
or_experts/b2_coi.py — Baseline B2 (COI / Cube-aware).

Spec anchor: §16.2 B2 — "COI / Cube-aware: Cube + Order Frequency".
Classic Cube-per-Order-Index slotting:

  COI(sku) = required_storage_volume / pick_frequency

Lower COI ⇒ closer to the entrance. Equivalently, rank SKUs by
pick_frequency / unit_volume descending — a density interpretation
(frequency per unit of consumed space).

v0.1 simplification: each SKU occupies `unit_volume_m3 * assigned_capacity`
where assigned_capacity is fixed at 1.0, so COI reduces to freq/volume ranking.
The full version (v0.2) will use real volume requirements from inventory.
"""

from __future__ import annotations

from collections import defaultdict
from typing import List, Dict, Tuple
import random

from world_state.schemas import (
    SkuMaster, Order, OrderLine, Location, SlotAssignment,
    DecisionPlan, ProblemType, RiskClass, SourceType,
)
from datetime import datetime


def _euclidean(xyz: Tuple[float, float, float]) -> float:
    return (xyz[0] ** 2 + xyz[1] ** 2 + xyz[2] ** 2) ** 0.5


def assign_coi(
    sku_master: List[SkuMaster],
    order_lines: List[OrderLine],
    pickable_locations: List[Location],
    xyz_lookup: Dict[str, Tuple[float, float, float]],
    decision_id: str,
    as_of: datetime,
) -> Tuple[List[SlotAssignment], Dict[str, str]]:
    # 1. pick frequency per sku
    freq: Dict[str, float] = defaultdict(float)
    for line in order_lines:
        freq[line.sku_id] += line.quantity

    # 2. unit volume per sku (proxy: COI = volume / freq; rank DESC on freq/volume)
    vol = {s.sku_id: max(s.unit_volume_m3, 1e-6) for s in sku_master}
    density = {sku: freq.get(sku, 0.0) / vol[sku] for sku in vol}

    ranked_skus = sorted(vol.keys(), key=lambda s: density.get(s, 0.0), reverse=True)
    ranked_locs = sorted(
        pickable_locations,
        key=lambda loc: _euclidean((loc.x, loc.y, loc.z)),
    )

    sku_to_loc: Dict[str, str] = {}
    rows: List[SlotAssignment] = []
    for i, sku in enumerate(ranked_skus):
        loc = ranked_locs[i % len(ranked_locs)]
        sku_to_loc[sku] = loc.location_id
        rows.append(SlotAssignment(
            timestamp=as_of,
            sku_id=sku,
            location_id=loc.location_id,
            assigned_capacity=1.0,
            reason="B2_COI",
            decision_id=decision_id,
            source_type=SourceType.SYNTHETIC,
        ))
    return rows, sku_to_loc


def build_decision_plan(
    assignments: List[SlotAssignment],
    expected_cost: float,
    baseline_cost: float,
    confidence: float = 1.0,
) -> DecisionPlan:
    return DecisionPlan(
        decision_id=f"DP-B2-{assignments[0].timestamp.isoformat()}",
        problem_type=ProblemType.DYNAMIC_SLOTTING,
        horizon_start=assignments[0].timestamp,
        horizon_end=assignments[0].timestamp,
        actions=[
            {"action": f"ASSIGN {a.sku_id} -> {a.location_id}",
             "reason": "B2_COI", "expected_saving": 0.0, "confidence": confidence}
            for a in assignments
        ],
        expected_cost=expected_cost,
        baseline_cost=baseline_cost,
        confidence=confidence,
        verifier_status="feasible",
        approval_status="auto",
        risk_class=RiskClass.LOW,
        model_version="B2_COI@v0.1",
        constraint_version="v0.1.0",
        lineage=SourceType.DERIVED,
        source_type=SourceType.DERIVED,
    )
