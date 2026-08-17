"""
world_state/wepa_adapter.py — v1.0 §6 + SPEC v1.5: WEPAStacks data → canonical schema.

slapstack 0.1.1 (pip-installed) bundles the actual WEPAStacks data:
  use_cases/wepastacks/1_layout.csv  (21KB, warehouse layout)
  use_cases/wepastacks/2_orders.json (43MB, 411,830 orders over ~3 months)
  use_cases/wepastacks/3_initial_fill_lvl.json

This adapter extracts the RETRIEVAL (outbound) orders and maps them to:
  - SKUs → top-N by retrieval frequency
  - Locations → the -2 (storage) cells from layout
  - OrderLines → per-order SKU retrievals with line_day timestamps

The retrieved-SKU-vs-location problem is a proxy for slotting: we
optimize "which SKU is stored in which location cell" using the actual
retrieval order stream. This is Track B (order-aware) in SPEC v1.0.

v1.5 scope: WEPA-Natural validation (external validity: does trap
mechanism exist in REAL warehouse data?). WEPA-Stress (controlled
shock injection) is a later step.
"""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Tuple

from .schemas import Order, OrderLine, SourceType

ANCHOR = datetime(2025, 1, 1, tzinfo=timezone.utc)


def _find_pkg_path() -> Path:
    """Locate the pip-installed slapstack package's use_cases dir."""
    import slapstack
    pkg_root = Path(slapstack.__file__).parent
    return pkg_root / "use_cases" / "wepastacks"


def load_layout(base: Path) -> Tuple[Dict[Tuple[int, int], int], int, int]:
    """Parse WEPAStacks layout CSV.
    Returns (location_map, n_rows, n_cols) where location_map[(r,c)] = code."""
    loc_map = {}
    with open(base / "1_layout.csv") as f:
        reader = csv.reader(f)
        for r, row in enumerate(reader):
            for c, val in enumerate(row):
                if val:
                    try:
                        code = int(val)
                        if code != -1 and code != 0:  # -1 = no cell, 0 = empty
                            loc_map[(r, c)] = code
                    except ValueError:
                        pass
    if loc_map:
        n_rows = max(r for r, c in loc_map) + 1
        n_cols = max(c for r, c in loc_map) + 1
    else:
        n_rows = n_cols = 0
    return loc_map, n_rows, n_cols


def load_orders(base: Path, max_orders: int = None,
                sku_filter: set = None) -> List[Tuple[str, int, int, int, int, int]]:
    """Load WEPAStacks orders (delivery + retrieval).
    Each: (action, sku_id, timestamp, source_lane, sink_lane, quantity)."""
    with open(base / "2_orders.json") as f:
        data = json.load(f)
    if max_orders:
        data = data[:max_orders]
    if sku_filter:
        data = [o for o in data if o[1] in sku_filter]
    return data


def _get_storage_locs(loc_map: Dict[Tuple[int, int], int]) -> List[Tuple[int, int]]:
    """Locations with code -2 are storage cells (where SKUs can be placed)."""
    return [pos for pos, code in loc_map.items() if code == -2]


def build_canonical(
    base: Path = None,
    top_n_skus: int = 60,
    max_orders: int = 30000,
    n_days: int = 21,
) -> Dict:
    """Build a canonical WorldState from WEPAStacks data:
      - top-N SKUs by retrieval frequency
      - storage locations as 'picking faces'
      - retrieval orders → canonical OrderLine
      - layout = uniform grid of storage cells (we abstract SLAPStack
        block-stacking into single-SKU-per-location slotting for this
        experiment; the WEPA geometry is preserved via the cell grid)

    Returns dict suitable for SequentialBenchmark construction:
      sku_ids, locations, xyz, orders, lines, anchor
    """
    if base is None:
        base = _find_pkg_path()
    loc_map, n_rows, n_cols = load_layout(base)
    storage = _get_storage_locs(loc_map)
    if len(storage) < top_n_skus:
        raise ValueError(f"WEPA has only {len(storage)} storage cells; "
                         f"need >= {top_n_skus}")

    # filter to RETRIEVAL orders (outbound = demand)
    all_orders = load_orders(base, max_orders=max_orders * 3)
    retrievals = [o for o in all_orders if o[0] == "retrieval"]
    sku_freq = Counter(o[1] for o in retrievals)
    top_skus = [s for s, _ in sku_freq.most_common(top_n_skus)]
    sku_set = set(top_skus)
    retrievals = [o for o in retrievals if o[1] in sku_set][:max_orders]

    # map top-N SKUs → canonical SKU ids (S00000..)
    sku_ids = [f"S{i:05d}" for i in range(top_n_skus)]
    sku_id_of = {orig: sid for orig, sid in zip(top_skus, sku_ids)}

    # storage layout as a grid (WEPA geometry: assign xyz based on cell coords)
    import math
    locations = []
    xyz = {}
    for i, (r, c) in enumerate(storage[:top_n_skus * 2]):  # allow 2 per cell
        x = round(c * 1.4 + 0.7, 2)
        y = round(r * 1.4 + 0.7, 2)
        z = 0.0
        loc_id = f"WEPA-{i:04d}"
        from .schemas import Location, ZoneType
        loc = Location(location_id=loc_id, zone=ZoneType.FORWARD_PICK,
                       aisle=0, bay=r, level=c, x=x, y=y, z=z,
                       capacity_volume_m3=2.0, capacity_weight_kg=200.0,
                       pickable=True, source_type=SourceType.OBSERVED)
        locations.append(loc)
        xyz[loc_id] = (x, y, z)

    # build canonical orders and lines
    orders, lines = [], []
    for seq_i, o in enumerate(retrievals):
        action, sku_orig, ts, src, sink, qty = o
        # each retrieval is one canonical order with one line
        oid = f"O{seq_i:07d}"
        # derive day from timestamp (WEPA timestamps are epoch seconds)
        if isinstance(ts, (int, float)) and ts > 0:
            day_offset = int(ts) % n_days
        else:
            day_offset = seq_i % n_days
        t = ANCHOR + timedelta(days=day_offset, hours=8 + (seq_i % 10))
        orders.append(Order(
            order_id=oid, order_time=t, known_at_time=t,
            channel="retrieval", cutoff=t + timedelta(hours=4),
            priority=0, wave_id=None, source_type=SourceType.OBSERVED,
        ))
        lines.append(OrderLine(
            order_id=oid, sku_id=sku_id_of[sku_orig], quantity=float(qty),
            uom="pallet", pick_sequence=1, source_type=SourceType.OBSERVED,
        ))

    return dict(
        sku_ids=sku_ids, sku_orig_to_canonical=sku_id_of,
        locations=locations, xyz=xyz, anchor=ANCHOR,
        orders=orders, lines=lines,
        n_storage=len(storage), n_retrievals=len(retrievals),
        n_top_skus=top_n_skus,
    )


# --- CrossStacks adapter --------------------------------------------------

def _find_crossstacks_path() -> Path:
    import slapstack
    return Path(slapstack.__file__).parent / "use_cases" / "crossstacks"


def build_crossstacks_canonical(
    top_n_skus: int = 80,
    max_orders: int = 15000,
    n_days: int = 14,
) -> Dict:
    """CrossStacks: 1,952 storage cells, 8,401 SKUs, 16,802 orders
    (balanced delivery/retrieval — true cross-docking pattern)."""
    base = _find_crossstacks_path()
    loc_map, n_rows, n_cols = load_layout(base)
    storage = _get_storage_locs(loc_map)
    if len(storage) < top_n_skus:
        raise ValueError(f"CrossStacks has only {len(storage)} storage cells")

    all_orders = load_orders(base, max_orders=max_orders * 2)
    retrievals = [o for o in all_orders if o[0] == "retrieval"]
    sku_freq = Counter(o[1] for o in retrievals)
    top_skus = [s for s, _ in sku_freq.most_common(top_n_skus)]
    sku_set = set(top_skus)
    retrievals = [o for o in retrievals if o[1] in sku_set][:max_orders]

    sku_ids = [f"X{i:05d}" for i in range(top_n_skus)]
    sku_id_of = {orig: sid for orig, sid in zip(top_skus, sku_ids)}

    locations = []
    xyz = {}
    for i, (r, c) in enumerate(storage[:top_n_skus * 2]):
        x = round(c * 1.4 + 0.7, 2); y = round(r * 1.4 + 0.7, 2); z = 0.0
        loc_id = f"CS-{i:04d}"
        from .schemas import Location, ZoneType
        loc = Location(location_id=loc_id, zone=ZoneType.FORWARD_PICK,
                       aisle=0, bay=r, level=c, x=x, y=y, z=z,
                       capacity_volume_m3=2.0, capacity_weight_kg=200.0,
                       pickable=True, source_type=SourceType.OBSERVED)
        locations.append(loc); xyz[loc_id] = (x, y, z)

    orders, lines = [], []
    for seq_i, o in enumerate(retrievals):
        action, sku_orig, ts, src, sink, qty = o
        oid = f"X{seq_i:07d}"
        day_offset = int(ts) % n_days if isinstance(ts, (int, float)) and ts > 0 else seq_i % n_days
        t = ANCHOR + timedelta(days=day_offset, hours=8 + (seq_i % 10))
        orders.append(Order(order_id=oid, order_time=t, known_at_time=t,
                            channel="retrieval", cutoff=t + timedelta(hours=4),
                            priority=0, wave_id=None, source_type=SourceType.OBSERVED))
        lines.append(OrderLine(order_id=oid, sku_id=sku_id_of[sku_orig],
                               quantity=float(qty), uom="pallet", pick_sequence=1,
                               source_type=SourceType.OBSERVED))

    return dict(sku_ids=sku_ids, sku_orig_to_canonical=sku_id_of,
                locations=locations, xyz=xyz, anchor=ANCHOR,
                orders=orders, lines=lines,
                n_storage=len(storage), n_retrievals=len(retrievals),
                n_top_skus=top_n_skus)
