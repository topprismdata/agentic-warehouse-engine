"""
or_experts/b3_affinity.py — Baseline B3 (Affinity Slotting).

Spec anchor: §16.2 B3 — "Affinity Slotting: History + Co-pick"; §12.4 two-stage
(zone → location) collapsed to cluster → single shared location.

Algorithm (deterministic):
  1. freq[sku] from history; A_ij graph from features/affinity.py (Top-K)
  2. Cluster greedily by descending freq: unassigned head pulls its strongest
     unassigned neighbors into a cluster (bounded by max_cluster)
  3. Locations ranked by distance to entrance; clusters (by head freq desc)
     each occupy ONE location — co-picked SKUs share a stop, so an order's
     route collapses to fewer distinct stops.

Expected effect: with basket structure present, B3 < B1 because multi-SKU
orders visit fewer distinct locations. Without basket structure B3 ≈ B1.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Tuple

from world_state.schemas import (
    OrderLine, Location, SlotAssignment, DecisionPlan,
    ProblemType, RiskClass, SourceType,
)
from features.affinity import AffinityGraph
from datetime import datetime


def _euclidean(xyz: Tuple[float, float, float]) -> float:
    return (xyz[0] ** 2 + xyz[1] ** 2 + xyz[2] ** 2) ** 0.5


def assign_affinity(
    sku_ids: List[str],
    order_lines: List[OrderLine],
    affinity: AffinityGraph,
    pickable_locations: List[Location],
    xyz_lookup: Dict[str, Tuple[float, float, float]],
    decision_id: str,
    as_of: datetime,
    max_cluster: int = 4,
    affinity_threshold: float = 0.0,
    location_capacity: int = None,
) -> Tuple[List[SlotAssignment], Dict[str, str]]:
    """Capacity-aware affinity slotting.

    v0.2 review finding F2: the old version overflowed clusters of 3-4 SKUs
    into capacity-2 locations (14 violations) while CP-SAT obeyed capacity as
    a HARD constraint — an unfair fight. Spec §10.4: hard constraints bind
    every expert identically. Now: clusters are capped at capacity, and any
    cluster that cannot fit is SPLIT rather than overflowed; a final assert
    guarantees zero violations (total capacity >= n makes a packing exist).
    """
    import math as _math
    freq: Dict[str, float] = defaultdict(float)
    for line in order_lines:
        freq[line.sku_id] += line.quantity

    # --- 1. greedy clustering by descending frequency -----------------------
    unassigned = set(sku_ids)
    clusters: List[List[str]] = []
    for sku in sorted(sku_ids, key=lambda s: freq.get(s, 0.0), reverse=True):
        if sku not in unassigned:
            continue
        cluster = [sku]
        unassigned.discard(sku)
        for nbr, a in affinity.neighbors(sku, threshold=affinity_threshold):
            if nbr in unassigned and len(cluster) < max_cluster:
                cluster.append(nbr)
                unassigned.discard(nbr)
        clusters.append(cluster)
    # leftovers (no affinity edges): singletons appended
    for sku in sorted(unassigned, key=lambda s: freq.get(s, 0.0), reverse=True):
        clusters.append([sku])

    # --- 2. capacity-fair placement: split, never overflow -------------------
    ranked_locs = sorted(pickable_locations, key=lambda l: _euclidean((l.x, l.y, l.z)))
    if location_capacity is None:
        location_capacity = max(1, _math.ceil(len(sku_ids) / len(ranked_locs)))
    max_cluster = min(max_cluster, location_capacity)
    remaining = {l.location_id: location_capacity for l in ranked_locs}

    sku_to_loc: Dict[str, str] = {}
    rows: List[SlotAssignment] = []

    def place(chunk: List[str]):
        for l in ranked_locs:  # nearest-first with remaining capacity
            if remaining[l.location_id] >= len(chunk):
                remaining[l.location_id] -= len(chunk)
                for sku in chunk:
                    sku_to_loc[sku] = l.location_id
                    rows.append(SlotAssignment(
                        timestamp=as_of, sku_id=sku, location_id=l.location_id,
                        assigned_capacity=float(len(chunk)), reason="B3_Affinity",
                        decision_id=decision_id, source_type=SourceType.SYNTHETIC,
                    ))
                return True
        return False

    queue: List[List[str]] = list(clusters)
    while queue:
        cluster = queue.pop(0)
        if place(cluster):
            continue
        # fragmentation: split in half and retry both halves
        if len(cluster) > 1:
            mid = len(cluster) // 2
            queue.insert(0, cluster[mid:])
            queue.insert(0, cluster[:mid])
        else:
            # single SKU with no capacity anywhere left: total capacity >= n
            # makes this unreachable unless earlier splits wasted space; assert.
            raise RuntimeError("B3 placement failed: no location with capacity")

    assert all(v >= 0 for v in remaining.values())
    return rows, sku_to_loc


def build_decision_plan(
    assignments: List[SlotAssignment],
    expected_cost: float,
    baseline_cost: float,
    confidence: float = 1.0,
) -> DecisionPlan:
    return DecisionPlan(
        decision_id=f"DP-B3-{assignments[0].timestamp.isoformat()}",
        problem_type=ProblemType.DYNAMIC_SLOTTING,
        horizon_start=assignments[0].timestamp,
        horizon_end=assignments[0].timestamp,
        actions=[
            {"action": f"ASSIGN {a.sku_id} -> {a.location_id}",
             "reason": "B3_Affinity", "expected_saving": 0.0, "confidence": confidence}
            for a in assignments
        ],
        expected_cost=expected_cost,
        baseline_cost=baseline_cost,
        confidence=confidence,
        verifier_status="feasible",
        approval_status="auto",
        risk_class=RiskClass.LOW,
        model_version="B3_Affinity@v0.2",
        constraint_version="v0.1.0",
        lineage=SourceType.DERIVED,
        source_type=SourceType.DERIVED,
    )
