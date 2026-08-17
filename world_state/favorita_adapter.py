"""
world_state/favorita_adapter.py — Real Favorita data → canonical schema.

Loads the actual Favorita Grocery Sales Forecasting dataset
(downloaded 2026-08-17, 890MB, CC0 via Kaggle mirror).
Maps store-level unit sales into our OrderLine format:
  - top-N items by total units sold (across all stores)
  - 1-day aggregation per (item, store) -> order line
  - 14-day window for the experiment
"""

from __future__ import annotations
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Tuple
import pandas as pd
import numpy as np

from .schemas import Order, OrderLine, SourceType

ANCHOR = datetime(2025, 1, 1, tzinfo=timezone.utc)
DATA = Path("/Users/guohongbin/projects/agentic-warehouse-engine/data/raw/favorita/extract")


def build_canonical(top_n_skus: int = 40, n_days: int = 14, n_orders: int = 2000) -> Dict:
    train_path = DATA / "train.csv"
    # train.csv has 4.7B rows — use chunked reading + only relevant columns
    log = print
    log(f"  scanning train.csv (chunked) for top-{top_n_skus} items by units...")
    item_units = defaultdict(float)
    for chunk in pd.read_csv(train_path, usecols=["item_nbr", "unit_sales"],
                              chunksize=10_000_000, dtype={"item_nbr": "int32", "unit_sales": "float32"}):
        for item, units in zip(chunk["item_nbr"].values, chunk["unit_sales"].values):
            item_units[int(item)] += float(units)
    top_items = sorted(item_units, key=item_units.get, reverse=True)[:top_n_skus]
    top_set = set(top_items)
    log(f"  top {len(top_items)} items: {item_units[top_items[0]]:.0f} units (top1) "
        f"to {item_units[top_items[-1]]:.0f} (topN)")
    log(f"  reading train.csv again, filtering to top items, aggregating by (date, store, item)...")

    # day_offset -> store -> item -> units
    days: Dict[int, Dict[int, Dict[int, float]]] = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
    for chunk in pd.read_csv(train_path,
                              usecols=["date", "store_nbr", "item_nbr", "unit_sales"],
                              chunksize=10_000_000,
                              dtype={"date": "str", "store_nbr": "int16",
                                     "item_nbr": "int32", "unit_sales": "float32"}):
        mask = chunk["item_nbr"].isin(top_set)
        if not mask.any():
            continue
        sub = chunk[mask]
        for d, s, i, u in zip(sub["date"].values, sub["store_nbr"].values,
                              sub["item_nbr"].values, sub["unit_sales"].values):
            days[d][int(s)][int(i)] += float(u)

    # build canonical orders
    sku_ids = [f"FV{i:05d}" for i in range(top_n_skus)]
    id_map = {orig: sid for orig, sid in zip(top_items, sku_ids)}
    dates_sorted = sorted(days.keys())[-n_days:]  # last n_days
    log(f"  using {len(dates_sorted)} days: {dates_sorted[0]} to {dates_sorted[-1]}")

    orders, lines = [], []
    seq_i = 0
    # build orders: one order per (day, store) with multiple line items
    # day_index: 0..n_days-1, mapped from the actual date
    date_to_idx = {d: i for i, d in enumerate(dates_sorted)}
    for d in dates_sorted:
        day_idx = date_to_idx[d]
        for store_id, item_dict in days[d].items():
            items_in_order = [(id_map[i], int(round(u))) for i, u in item_dict.items() if int(round(u)) > 0]
            if not items_in_order:
                continue
            t = ANCHOR + timedelta(days=day_idx)
            oid = f"F{seq_i:08d}"
            orders.append(Order(
                order_id=oid, order_time=t, known_at_time=t,
                channel="favorita", cutoff=t + timedelta(hours=4),
                priority=0, wave_id=None, source_type=SourceType.OBSERVED))
            for k, (sid, qty) in enumerate(items_in_order):
                lines.append(OrderLine(
                    order_id=oid, sku_id=sid, quantity=float(qty), uom="unit",
                    pick_sequence=k + 1, source_type=SourceType.OBSERVED))
            seq_i += 1
            if seq_i >= n_orders:
                break
        if seq_i >= n_orders:
            break
    log(f"  built {len(orders)} orders, {len(lines)} lines")
    # locations: uniform grid
    n_loc = max(2 * top_n_skus, 12)
    from .schemas import Location, ZoneType
    locations = []
    xyz = {}
    for i in range(n_loc):
        x = round(i * 1.4 + 0.7, 2); y = round(i * 0.4, 2); z = 0.0
        loc_id = f"FV-LOC-{i:03d}"
        locations.append(Location(location_id=loc_id, zone=ZoneType.FORWARD_PICK,
            aisle=0, bay=i // 2, level=i % 2, x=x, y=y, z=z,
            capacity_volume_m3=2.0, capacity_weight_kg=200.0,
            pickable=True, source_type=SourceType.OBSERVED))
        xyz[loc_id] = (x, y, z)
    return dict(sku_ids=sku_ids, sku_orig_to_canonical=id_map,
                locations=locations, xyz=xyz, anchor=ANCHOR,
                orders=orders, lines=lines,
                n_top_skus=top_n_skus, n_orders=len(orders))
