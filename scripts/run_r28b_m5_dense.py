"""R28b: M5 with all 10 stores — robustness check on R28's distinct=1 finding."""
from __future__ import annotations
import sys, time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from collections import Counter, defaultdict
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import pandas as pd
from world_state.schemas import (Order, OrderLine, SkuMaster, StorageClass, SourceType,
                                   Location, ZoneType)
from world_state.regime_sequence import DayParams
from simulation.sequential import SequentialBenchmark
t0 = time.time()
log = lambda m: print(f"[{time.time()-t0:.1f}s] {m}", flush=True)

log("=== R28b: M5 with ALL 10 stores ===")
train = pd.read_parquet("data/raw/m5/m5_train.parquet")
train['ds'] = pd.to_datetime(train['ds'])
parts = train['unique_id'].str.split('_', expand=True)
parts.columns = ['dept', 'item', 'state', 'store_a', 'store_b']
train = pd.concat([train, parts], axis=1)
train['item'] = train['item'].astype(int)
last = train['ds'].max()
cutoff = last - pd.Timedelta(days=29)
sub = train[train['ds'] >= cutoff].copy()
sub.loc[:, 'day_idx'] = (sub['ds'] - cutoff).dt.days
top_items = sub.groupby('item')['y'].sum().nlargest(40).index.tolist()
sub = sub[sub['item'].isin(set(top_items))]
sku_ids = [f"M5{i:04d}" for i in range(40)]
id_map = {int(o): s for o, s in zip(top_items, sku_ids)}
by_dsb = defaultdict(list)
for _, r in sub.iterrows():
    by_dsb[(int(r['day_idx']), f"{r['state']}_{r['store_a']}_{r['store_b']}")].append(
        (id_map[int(r['item'])], float(r['y'])))
orders, lines = [], []
seq_i = 0
anchor = datetime(2025, 1, 1, tzinfo=timezone.utc)
days_sorted = sorted(set(d for d, _ in by_dsb.keys()))
import random
per_day = max(1, 500 // max(1, len(days_sorted)))  # 500 orders across 30 days
for d in days_sorted:
    stores_d = [(d, sb) for (dd, sb) in by_dsb.keys() if dd == d]
    rng_loc = random.Random(d)
    rng_loc.shuffle(stores_d)
    picked = 0
    for (dd, sb) in stores_d:
        if picked >= per_day: break
        items = by_dsb[(dd, sb)]
        if not items: continue
        items_d = defaultdict(float)
        for sid, qty in items: items_d[sid] += qty
        t = anchor + timedelta(days=d)
        oid = f"M5d{seq_i:05d}"
        orders.append(Order(order_id=oid, order_time=t, known_at_time=t,
            channel="m5", cutoff=t + timedelta(hours=4),
            priority=0, wave_id=None, source_type=SourceType.OBSERVED))
        for k, (sid, qty) in enumerate(sorted(items_d.items())):
            if qty > 0:
                lines.append(OrderLine(order_id=oid, sku_id=sid,
                    quantity=qty, uom="unit",
                    pick_sequence=k + 1, source_type=SourceType.OBSERVED))
        seq_i += 1
        picked += 1
    if seq_i >= 500: break
log(f"  built {len(orders)} orders, {len(lines)} lines")

max_day = max(int((o.order_time - anchor).days) for o in orders) + 1
day_params = [DayParams(day=d, phase=f"p{d // 5}") for d in range(max_day + 1)]
n_loc = 80
locations, xyz = [], {}
for i in range(n_loc):
    x = round(i * 1.4 + 0.7, 2); y = round(i * 0.4, 2); z = 0.0
    loc_id = f"M5-LOC-{i:03d}"
    locations.append(Location(location_id=loc_id, zone=ZoneType.FORWARD_PICK,
        aisle=0, bay=i // 2, level=i % 2, x=x, y=y, z=z,
        capacity_volume_m3=2.0, capacity_weight_kg=200.0,
        pickable=True, source_type=SourceType.OBSERVED))
    xyz[loc_id] = (x, y, z)
sku_master = [SkuMaster(sku_id=s, category_id="M5", unit_volume_m3=0.01,
    unit_weight_kg=5.0, case_pack=24, pallet_qty=48, shelf_life_days=None,
    storage_class=StorageClass.AMBIENT, source_type=SourceType.OBSERVED)
    for s in sku_ids]
bench = SequentialBenchmark(sku_master, locations, xyz, orders, lines,
                            day_params, anchor, mc_unit_ratio=0.0005)
m = bench.run(seed_for_view=42)
b = bench.beam_search(beam_width=6, seed_for_view=42)
gap = (m.myopic_total - b.total_cost) / max(m.myopic_total, 1e-9)
winners = [pr.myopic_winner.split("_")[0] for pr in m.periods]
dist = Counter(winners)
log(f"  myopic={m.myopic_total:.0f} bfip={b.total_cost:.0f} gap={gap*100:.2f}%")
log(f"  winners: {dict(dist)} | distinct={len(dist)} | fixed-best={m.fixed_best.split('_')[0]}")

out = ROOT / "outputs" / "experiments" / "r28b_m5_dense.md"
with open(out, "w") as f:
    f.write("# R28b — M5 with ALL 10 stores (robustness check)\n\n")
    f.write(f"**Date**: {datetime.now(timezone.utc).isoformat()}\n\n")
    f.write("**Question**: Was R28's distinct=1 a consequence of (a) the\n")
    f.write("5-year steady-state nature of M5 hierarchical demand, or (b) the\n")
    f.write("thin signal from a single store (78 lines/30d)?\n\n")
    f.write("**Method**: Use ALL 10 stores (CA/TX/WI) over last 30 days, top-40\n")
    f.write("items by total volume.\n\n")
    f.write("## Result\n\n")
    f.write(f"- n SKUs: 40 (top by total volume)\n")
    f.write(f"- n orders: {len(orders)} (~{len(orders)//6:.0f} per period)\n")
    f.write(f"- n lines: {len(lines)} (~{len(lines)//6:.0f} per period)\n")
    f.write(f"- myopic total: {m.myopic_total:.0f}\n")
    f.write(f"- BFIP total: {b.total_cost:.0f}\n")
    f.write(f"- **gap = {gap*100:.2f}%**\n")
    wb = ", ".join(f"{k}({v})" for k, v in dist.items())
    f.write(f"- winners: {wb} (distinct={len(dist)})\n")
    f.write(f"- fixed-best: {m.fixed_best.split('_')[0]} ({m.fixed_best_total:.0f})\n\n")
    f.write("## Interpretation\n")
    if len(dist) >= 3:
        f.write("- **Multi-winner recovered** with denser data: R28's distinct=1\n")
        f.write("  was a **data-density bound** (78 lines/30d), not a true steady-\n")
        f.write("  state property of M5 hierarchical demand.\n")
    elif len(dist) == 2:
        f.write("- 2 winners recovered: marginal improvement over R28's 1.\n")
    else:
        f.write("- Still distinct=1 even with denser data: confirms M5's\n")
        f.write("  5-year steady-state produces single-winner outcomes.\n")
    f.write("\n## Cross-dataset T0 (9 real-data sources now)\n\n")
    f.write("| Source | n SKUs | data type | distinct winners | gap |\n")
    f.write("|--------|--------|-----------|-------------------|-----|\n")
    f.write("| WEPA (R21) | 40 | single warehouse, 3mo | 3-4 | 0.00% |\n")
    f.write("| CrossStacks (R24) | 40 | cross-dock, single batch | 1-2 | 0.00% |\n")
    f.write("| Instacart top (R25) | 20 | retail top 10% | 2 | 0.00% |\n")
    f.write("| Instacart mid (R25) | 20 | retail mid 10% | 2 | 0.00% |\n")
    f.write("| Favorita real (R26b) | 40 | 14d, 54 stores | 2 | 0.00% |\n")
    f.write("| M5 single store (R28) | 40 | 5-yr hierarchical | 1 | 0.00% |\n")
    f.write(f"| M5 all stores (R28b) | 40 | 5-yr hierarchical (dense) | **{len(dist)}** | **{gap*100:.2f}%** |\n")
    f.write("| SLAPRP (R29) | 40 | basket structure | 3 | 0.00% |\n")
log(f"wrote {out.relative_to(ROOT)}")
log("=== done ===")
