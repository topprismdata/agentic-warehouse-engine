"""
world_state/loader.py — Shared World State builder for experiment scripts.

Extracted from R01's stage1 so R02+ reuse identical construction logic.
R01 keeps its inline copy for legacy reproducibility (its numbers were
produced under the pre-basket sampler and per-line cost).
"""

from __future__ import annotations

import random
from datetime import datetime, timezone
from typing import Dict

from . import sample as sampler


def build_world(cfg: dict, seed: int, use_basket: bool = False) -> Dict:
    rng = random.Random(seed)

    ws = cfg["world_state"]
    sku_master = sampler.make_sku_master(ws["n_skus"], rng)
    locations, xyz_lookup = sampler.make_locations(ws["n_locations"], rng)
    sku_ids = [s.sku_id for s in sku_master]
    sku_category = {s.sku_id: s.category_id for s in sku_master}

    day_anchor = datetime(2025, 1, 1, tzinfo=timezone.utc)
    orders, order_lines = sampler.make_orders(
        sku_ids=sku_ids,
        location_xyz=xyz_lookup,
        n_days=ws["n_days"],
        orders_per_day_mean=ws["orders_per_day_mean"],
        orders_per_day_std=ws["orders_per_day_std"],
        day_anchor=day_anchor,
        rng=rng,
        sku_category=sku_category if use_basket else None,
        category_concentration=ws.get("category_concentration", 0.7) if use_basket else 0.0,
    )
    forecast = sampler.make_forecast_daily(sku_ids, orders, order_lines, ws["n_days"], day_anchor)
    inv = sampler.make_inventory_snapshot(sku_ids, locations, day_anchor, rng)
    constraints = sampler.make_constraints(locations)

    return {
        "sku_master": sku_master,
        "orders": orders,
        "order_lines": order_lines,
        "forecast_daily": forecast,
        "locations": locations,
        "inventory_snapshot": inv,
        "slot_assignment": [],
        "constraints": constraints,
        "decision_plan": [],
        "xyz_lookup": xyz_lookup,
        "sku_ids": sku_ids,
        "sku_category": sku_category,
        "day_anchor": day_anchor,
        "_rng": rng,
    }
