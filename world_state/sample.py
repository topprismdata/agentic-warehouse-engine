"""
world_state/sample.py — Synthetic data generator for v0.1.

Spec anchor: §4.3 (no future leakage), Appendix B (minimum schema).

This module produces a fully synthetic, lineage-marked world state. It is the only
permitted source of v0.1 rows — the seed is centralized so any baseline (B0/B1/...)
sees the exact same World State.
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timedelta, timezone, date
from typing import Dict, List, Tuple
import numpy as np
import random

from .schemas import (
    SkuMaster, Order, OrderLine, ForecastDaily,
    Location, InventorySnapshot, SlotAssignment,
    Constraint, DecisionPlan,
    SourceType, StorageClass, ZoneType,
)


# -------------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------------

UTC = timezone.utc


def _aware(dt: datetime) -> datetime:
    """Ensure tz-aware (UTC). Spec §8.4 requires it; silent fail elsewhere."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


# -------------------------------------------------------------------------
# Generators
# -------------------------------------------------------------------------

def make_sku_master(n: int, rng: random.Random) -> List[SkuMaster]:
    rows = []
    for i in range(n):
        sid = f"S{i:05d}"
        rows.append(SkuMaster(
            sku_id=sid,
            category_id=f"CAT{i % 8:02d}",
            unit_volume_m3=round(rng.uniform(0.0005, 0.05), 5),
            unit_weight_kg=round(rng.uniform(0.05, 12.0), 3),
            case_pack=rng.choice([6, 12, 24, 48]),
            pallet_qty=rng.choice([48, 96, 144, 240]),
            shelf_life_days=rng.choice([None, 30, 90, 180, 365]),
            storage_class=StorageClass(rng.choice(["ambient", "chilled"])),
            source_type=SourceType.SYNTHETIC,
        ))
    return rows


def make_locations(n: int, rng: random.Random) -> Tuple[List[Location], Dict[str, Tuple[float, float, float]]]:
    """N locations laid out along a single aisle; entrance at (0,0,0).

    Returns (rows, xyz_lookup) — xyz_lookup is used downstream for cost computation.
    """
    rows, lookup = [], {}
    bay_count = max(1, n // 3)  # 3 levels per bay-ish split
    for i in range(n):
        bay = i // 3
        level = i % 3
        # realistic DC geometry: bays 6 m apart, aisle depth up to ~120 m.
        # (The v0.1 1.2 m grid made travel trivial vs pick time — caught by R04
        #  when B0's flow matched B1: a warehouse you can cross in 5 seconds
        #  cannot reward slotting in a TIME metric.)
        x = round(bay * 6.0 + 2.0, 2)   # aisle depth (m)
        y = round(level * 1.6, 2)       # shelf level height (m)
        z = round(rng.choice([-1.2, 1.2]), 2)  # side of aisle
        loc_id = f"L{bay:02d}{level:01d}"
        rows.append(Location(
            location_id=loc_id,
            zone=ZoneType.FORWARD_PICK if level == 0 else ZoneType.RESERVE,
            aisle=0, bay=bay, level=level,
            x=x, y=y, z=z,
            capacity_volume_m3=2.0,
            capacity_weight_kg=200.0,
            pickable=True,  # manual rack warehouse: all levels pickable (higher = slower, captured by y)
            source_type=SourceType.SYNTHETIC,
        ))
        lookup[loc_id] = (x, y, z)
    return rows, lookup


def make_orders(
    sku_ids: List[str],
    location_xyz: Dict[str, Tuple[float, float, float]],
    n_days: int,
    orders_per_day_mean: float,
    orders_per_day_std: float,
    day_anchor: datetime,
    rng: random.Random,
    sku_category: Dict[str, str] = None,
    category_concentration: float = 0.0,
) -> Tuple[List[Order], List[OrderLine]]:
    """Generate N days of synthetic orders; known_at_time == order_time for v0.1.

    SKU popularity follows a Zipf-like law: weight(rank) = 1/(rank+1)^1.5. This
    mirrors real FMCG pick-frequency concentration (spec §2.1 ABC insight) —
    without it, Static ABC cannot beat Random and the benchmark is meaningless.

    Basket structure (spec §13.2 temporal affinity / Oracle C5 market-basket):
      when sku_category is provided and category_concentration > 0, each order
      draws a lead category, and each line comes from that category w.p.
      `category_concentration`, else from the global Zipf. This produces
      co-pick structure that affinity slotting (B3) can exploit; without it
      B3 degenerates to B1 (uniform co-occurrence).
    """
    # Zipf-ish weights over sku order (sku_ids is sorted by construction)
    weights = [1.0 / ((i + 1) ** 1.5) for i in range(len(sku_ids))]

    # Per-category Zipf weights for basket sampling
    cat_members: Dict[str, List[str]] = {}
    if sku_category:
        for s in sku_ids:
            cat_members.setdefault(sku_category.get(s, "CAT??"), []).append(s)
    cat_weights = {
        c: [1.0 / ((i + 1) ** 1.5) for i in range(len(m))]
        for c, m in cat_members.items()
    }
    cat_names = list(cat_members.keys())

    def draw_line(lead_cat: str) -> str:
        if lead_cat and rng.random() < category_concentration:
            m, w = cat_members[lead_cat], cat_weights[lead_cat]
            return rng.choices(m, weights=w, k=1)[0]
        return rng.choices(sku_ids, weights=weights, k=1)[0]

    orders, lines = [], []
    order_seq = 0
    for d in range(n_days):
        # Sample today's order count from a positive distribution
        n_orders = max(1, int(rng.gauss(orders_per_day_mean, orders_per_day_std)))
        for _ in range(n_orders):
            order_seq += 1
            # Spread orders through the day; known_at_time == order_time (no delay)
            t = day_anchor + timedelta(days=d, hours=rng.uniform(8, 18))
            t = _aware(t)
            order_id = f"O{order_seq:06d}"
            lead = rng.choice(cat_names) if cat_names else None
            line_count = rng.randint(1, 6)
            chosen = [draw_line(lead) for _ in range(line_count)]
            orders.append(Order(
                order_id=order_id,
                order_time=t,
                known_at_time=t,  # spec §4.3: equal means no forecast leakage even under replay
                channel=rng.choice(["b2b", "b2c"]),
                cutoff=t + timedelta(hours=4),
                priority=rng.randint(0, 4),
                wave_id=f"W{d:02d}",
                source_type=SourceType.SYNTHETIC,
            ))
            for seq, sku in enumerate(chosen, start=1):
                lines.append(OrderLine(
                    order_id=order_id,
                    sku_id=sku,
                    quantity=float(rng.randint(1, 12)),
                    uom="each",
                    pick_sequence=seq,
                    source_type=SourceType.SYNTHETIC,
                ))
    return orders, lines


def make_forecast_daily(
    sku_ids: List[str], orders: List[Order], order_lines: List[OrderLine],
    n_days: int, day_anchor: datetime,
) -> List[ForecastDaily]:
    """ForecastDaily stub: as_of=target-1, model_version=v0.1.

    For each (as_of, target, sku), set known_order_qty to the actual orders seen in
    `orders` whose known_at_time is < as_of_date AND target_date is order's date.
    Then set forecast_residual = max(0, p50 - known_qty).
    """
    rows = []
    # order_id -> Order map. NOTE: order_lines has 1-6 rows per order, so
    # zipping (lines, orders) positionally scrambles timestamps — caught by
    # the v0.2 three-round review (5/12 rows wrong on a smoke check).
    order_map = {o.order_id: o for o in orders}
    # Build lookup: target_date -> sku -> known qty
    known_by_day_sku: Dict[Tuple[date, str], float] = {}
    for ol in order_lines:
        order = order_map.get(ol.order_id)
        if order is None:
            continue
        d = order.order_time.date()
        known_by_day_sku[(d, ol.sku_id)] = known_by_day_sku.get((d, ol.sku_id), 0.0) + ol.quantity

    for d in range(n_days):
        as_of = day_anchor + timedelta(days=d)
        target = as_of + timedelta(days=1)
        for sku in sku_ids:
            known = known_by_day_sku.get((target.date(), sku), 0.0)
            # naive baseline: forecast residual = max(0, known * 0.2) + small noise
            residual = round(max(0.0, known * 0.2), 2)
            p50 = round(known + residual, 2)
            rows.append(ForecastDaily(
                as_of_date=as_of.date(),
                target_date=target.date(),
                sku_id=sku,
                p10=None, p50=p50, p90=None,
                known_order_qty=known,
                forecast_residual=residual,
                model_version="v0.1-naive",
                source_type=SourceType.DERIVED,
            ))
    return rows


def make_inventory_snapshot(
    sku_ids: List[str], locations: List[Location], t: datetime,
    rng: random.Random,
) -> List[InventorySnapshot]:
    """One snapshot per sku with one forward-pick location, plus 1 reserve copy.

    spec §10.2 requires `inventory_snapshot` be timestamp-keyed.
    """
    rows = []
    t = _aware(t)
    forward = [loc for loc in locations if loc.pickable]
    if not forward:
        forward = locations
    for sku in sku_ids:
        loc = rng.choice(forward)
        rows.append(InventorySnapshot(
            timestamp=t,
            sku_id=sku,
            location_id=loc.location_id,
            on_hand=round(rng.uniform(20, 200), 1),
            available=round(rng.uniform(10, 150), 1),
            reserved=round(rng.uniform(0, 30), 1),
            batch_id=None, expiry_date=None,
            source_type=SourceType.SYNTHETIC,
        ))
    return rows


def make_constraints(locations: List[Location]) -> List[Constraint]:
    """Spec §10.4 hard constraint graph baseline — emitted at the canonical
    rule_version "v0.1-default". Adding new rules requires bumping this semver
    so all DecisionPlan rows can be tied to the rule set that produced them.
    """
    rows = []
    t = _aware(datetime(2025, 1, 1, 0, 0, 0))
    rule_version = "v0.1.0"
    # weight cap on every reserve
    for loc in locations:
        if loc.zone == ZoneType.RESERVE:
            rows.append(Constraint(
                constraint_id=f"max_weight:{loc.location_id}",
                scope=f"loc:{loc.location_id}",
                type="max_weight",
                hard=True,
                source="synthetic-rule",
                effective_time=t,
                rule_version=rule_version,
                source_type=SourceType.SYNTHETIC,
            ))
    # FEFO on chilled storage class (marker)
    rows.append(Constraint(
        constraint_id="fefo:chilled:global",
        scope="storage_class:chilled",
        type="fefo",
        hard=True,
        source="synthetic-rule",
        effective_time=t,
        rule_version=rule_version,
        source_type=SourceType.SYNTHETIC,
    ))
    return rows
