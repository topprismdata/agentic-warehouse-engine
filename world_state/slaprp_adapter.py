"""world_state/slaprp_adapter.py — SLAPRP benchmark → canonical schema.

Prunet, Absi, Cattaruzza 2025 (Zenodo 7866860) provides the SLAPRP testbed:
two sets of instances (Silva 2020 + Guo 2021) with aisles/bays, SKUs,
orders (with co-pick lists), and fixed assignments.

This is the first dataset with:
  - Multi-SKU orders (real basket structure for E3 affinity to exploit)
  - Varying sizes (50–1000 orders, 40–3840 SKUs, varying aisle/bay)
  - Published optimal values (in the xlsx) for validation against BFIP

The SLAPRP is also the paper that SPEC v1.0 §6 listed as the exact
benchmark for Storage Location Assignment + Picker Routing (BCP).
"""
from __future__ import annotations
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Tuple
import random

from .schemas import Order, OrderLine, SourceType

ANCHOR = datetime(2025, 1, 1, tzinfo=timezone.utc)
DATA = Path("/Users/guohongbin/projects/agentic-warehouse-engine/data/raw/slaprp/instances")


def parse_instance(path: Path) -> Dict:
    """Parse a SLAPRP instance file (Guo format).

    Format (from readme.txt):
      1. n_aisles n_bays
      2. wa wb wc (correlation params)
      3. n_skus
      4. n_orders
      5. order_lengths (one per order)
      6.. 5+n_orders: SKUs per order (length=order_lengths[i])
      then: fixed assignments: SKU location pairs (until EOF)
    """
    with open(path) as f:
        toks = f.read().split()
    it = iter(toks)
    n_aisles = int(next(it))
    n_bays = int(next(it))
    wa = float(next(it)); wb = float(next(it)); wc = float(next(it))
    n_skus = int(next(it))
    n_orders = int(next(it))
    order_lengths = [int(next(it)) for _ in range(n_orders)]
    orders_skus = []
    for length in order_lengths:
        orders_skus.append([int(next(it)) for _ in range(length)])
    # fixed assignments: pairs until EOF (each "sku location" line)
    fixed = []
    try:
        while True:
            sku = int(next(it)); loc = int(next(it))
            fixed.append((sku, loc))
    except StopIteration:
        pass
    return dict(n_aisles=n_aisles, n_bays=n_bays, n_skus=n_skus,
                n_orders=n_orders, order_lengths=order_lengths,
                orders_skus=orders_skus, fixed_assignments=fixed,
                wa=wa, wb=wb, wc=wc, source_path=str(path))


def build_canonical_from_slaprp(
    instance_path: Path = None,
    n_days: int = 5,
    n_orders: int = 200,
    seed: int = 42,
) -> Dict:
    """Build canonical data from a single SLAPRP instance, treating the
    order stream as a 5-day request horizon.

    SKUs are 1-indexed in SLAPRP; map to S00000-prefixed canonical ids.
    Locations are aisle-bay tuples; map to sequential canonical locs.
    """
    if instance_path is None:
        # default to a small Guo instance
        guo = DATA / "instances_Guo_2021"
        instance_path = next(guo.glob("SLAPRP_Guo_small_O50_*.txt"))
    inst = parse_instance(instance_path)
    rng = random.Random(seed)
    n_skus = inst["n_skus"]
    # map SKU 1..N to S00001..S0000N
    sku_ids = [f"SL{i:05d}" for i in range(1, n_skus + 1)]
    sku_map = {i: sku_ids[i-1] for i in range(1, n_skus + 1)}
    # locations: n_aisles * n_bays positions (use first n_skus)
    n_locs_total = inst["n_aisles"] * inst["n_bays"]
    loc_ids = [f"SL-LOC-{i:04d}" for i in range(n_locs_total)]
    # build canonical locations
    from .schemas import Location, ZoneType
    locations = []
    xyz = {}
    for i, loc_id in enumerate(loc_ids):
        aisle = i // inst["n_bays"]
        bay = i % inst["n_bays"]
        x = round(aisle * 2.0 + 0.5, 2); y = round(bay * 1.2 + 0.5, 2); z = 0.0
        locations.append(Location(location_id=loc_id, zone=ZoneType.FORWARD_PICK,
            aisle=aisle, bay=bay, level=0, x=x, y=y, z=z,
            capacity_volume_m3=2.0, capacity_weight_kg=200.0,
            pickable=True, source_type=SourceType.OBSERVED))
        xyz[loc_id] = (x, y, z)
    # sample orders: shuffle the instance's order list, take first n_orders
    n_inst_orders = len(inst["orders_skus"])
    if n_orders > n_inst_orders:
        n_orders = n_inst_orders
    perm = list(range(n_inst_orders))
    rng.shuffle(perm)
    selected = perm[:n_orders]
    canon_orders, canon_lines = [], []
    for i, idx in enumerate(selected):
        sku_list = inst["orders_skus"][idx]
        t = ANCHOR + timedelta(days=i % n_days, hours=8 + (i % 8))
        oid = f"SL{i:06d}"
        canon_orders.append(Order(order_id=oid, order_time=t, known_at_time=t,
            channel="slaprp", cutoff=t + timedelta(hours=4),
            priority=0, wave_id=None, source_type=SourceType.OBSERVED))
        for k, sku in enumerate(sku_list):
            canon_lines.append(OrderLine(order_id=oid, sku_id=sku_map[sku],
                quantity=1.0, uom="unit", pick_sequence=k + 1,
                source_type=SourceType.OBSERVED))
    return dict(sku_ids=sku_ids, locations=locations, xyz=xyz,
                orders=canon_orders, lines=canon_lines, anchor=ANCHOR,
                n_skus=n_skus, n_orders=len(canon_orders),
                n_aisles=inst["n_aisles"], n_bays=inst["n_bays"],
                instance=str(instance_path.name))


if __name__ == "__main__":
    import sys
    sys.path.insert(0, ".")
    from world_state.slaprp_adapter import build_canonical_from_slaprp
    d = build_canonical_from_slaprp()
    print(f"orders: {len(d['orders'])}, lines: {len(d['lines'])}, "
          f"SKUs: {d['n_skus']}, instance: {d['instance']}")
    # show order sizes
    from collections import Counter
    sizes = [len(oid) for oid in d['orders']]
    print(f"order size distribution: {dict(Counter(sizes))}")
