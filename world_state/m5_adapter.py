"""world_state/m5_adapter.py — M5 Walmart → canonical schema.

The M5 hierarchical demand-forecasting dataset (Kaggle, 2011-2016, 10
stores across CA/TX/WI, 3,000+ items in FOODS/HOBBIES/HOUSEHOLD,
46.8M daily unit_sales rows).

unique_id format: DEPT_ITEM_STATE_STORE
  e.g. FOODS_1_001_CA_1  -> dept=FOODS, item=1, state=001(CA), store=CA_1
  5 split parts; combine parts 2+3+4 to get the store key.
Maps the last 30 days of (state, store, item, y) into per-day orders.
"""
from __future__ import annotations
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict

import pandas as pd

from .schemas import Order, OrderLine, SourceType

ANCHOR = datetime(2025, 1, 1, tzinfo=timezone.utc)
DATA = Path("/Users/guohongbin/projects/agentic-warehouse-engine/data/raw/m5")


def build_canonical(top_n_skus: int = 40, n_days: int = 30,
                    n_orders: int = 200, store_filter: bool = True) -> Dict:
    train = pd.read_parquet(DATA / "m5_train.parquet")
    train["ds"] = pd.to_datetime(train["ds"])
    parts = train["unique_id"].str.split("_", expand=True)
    parts.columns = ["dept", "item", "state", "store_a", "store_b"]
    train = pd.concat([train, parts], axis=1)
    if store_filter:
        # California, store 1 (CA_1)
        train = train[(train["state"] == "001") & (train["store_a"] == "CA")
                      & (train["store_b"] == "1")].copy()
    train["item"] = train["item"].astype(int)

    last = train["ds"].max()
    cutoff = last - pd.Timedelta(days=n_days - 1)
    sub = train[train["ds"] >= cutoff].copy()
    sub["day_idx"] = (sub["ds"] - cutoff).dt.days

    top_items = sub.groupby("item")["y"].sum().nlargest(top_n_skus).index.tolist()
    top_set = set(top_items)
    sub = sub[sub["item"].isin(top_set)]

    sku_ids = [f"M5{i:04d}" for i in range(top_n_skus)]
    id_map = {int(o): s for o, s in zip(top_items, sku_ids)}
    by_day = defaultdict(list)
    for _, row in sub.iterrows():
        by_day[int(row["day_idx"])].append((id_map[int(row["item"])], float(row["y"])))

    orders, lines = [], []
    seq_i = 0
    for day in range(n_days):
        items = by_day.get(day, [])
        if not items:
            continue
        t = ANCHOR + timedelta(days=day)
        oid = f"M{seq_i:06d}"
        orders.append(Order(order_id=oid, order_time=t, known_at_time=t,
            channel="m5", cutoff=t + timedelta(hours=4),
            priority=0, wave_id=None, source_type=SourceType.OBSERVED))
        for k, (sid, qty) in enumerate(sorted(items)):
            if int(qty) > 0:
                lines.append(OrderLine(order_id=oid, sku_id=sid,
                    quantity=float(int(qty)), uom="unit",
                    pick_sequence=k + 1, source_type=SourceType.OBSERVED))
        seq_i += 1
        if seq_i >= n_orders:
            break

    n_loc = max(2 * top_n_skus, 12)
    from .schemas import Location, ZoneType
    locations, xyz = [], {}
    for i in range(n_loc):
        x = round(i * 1.4 + 0.7, 2); y = round(i * 0.4, 2); z = 0.0
        loc_id = f"M5-LOC-{i:03d}"
        locations.append(Location(location_id=loc_id, zone=ZoneType.FORWARD_PICK,
            aisle=0, bay=i // 2, level=i % 2, x=x, y=y, z=z,
            capacity_volume_m3=2.0, capacity_weight_kg=200.0,
            pickable=True, source_type=SourceType.OBSERVED))
        xyz[loc_id] = (x, y, z)
    return dict(sku_ids=sku_ids, sku_orig_to_canonical=id_map,
                locations=locations, xyz=xyz, anchor=ANCHOR,
                orders=orders, lines=lines,
                n_top_skus=top_n_skus, n_orders=len(orders))


def main():
    import time
    t = time.time()
    data = build_canonical()
    print(f"orders: {len(data['orders'])}, lines: {len(data['lines'])}, "
          f"SKUs: {data['n_top_skus']} ({time.time()-t:.1f}s)")


if __name__ == "__main__":
    main()
