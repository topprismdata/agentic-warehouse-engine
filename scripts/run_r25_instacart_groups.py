"""R25: Instacart multi-group T0 validation (small/fast)."""

from __future__ import annotations
import random, sys, time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from world_state import sample as sampler
from world_state.regime_sequence import build_sequence
from simulation.sequential import SequentialBenchmark
from world_state.schemas import (
    SkuMaster, StorageClass, SourceType, Location, ZoneType, Order, OrderLine
)
from or_experts.policies import EXPERT_IDS
from features.affinity import compute_affinity  # suppress unused
# patch E7 time budget to 2s for this small experiment
import or_experts.e4_e7 as e47
_orig_e7 = e47.assign_e7_rolling_lite
def _fast_e7(*args, time_budget_s=2.0, **kwargs):
    return _orig_e7(*args, time_budget_s=2.0, **kwargs)
e47.assign_e7_rolling_lite = _fast_e7

t0 = time.time()
log = lambda m: print(f"[{time.time()-t0:.1f}s] {m}", flush=True)


def run_group(name, n_skus, alpha, seed=42, n_orders=200):
    log(f"=== {name} ({n_skus} SKUs, alpha={alpha}) ===")
    rng = random.Random(seed)
    weights = [1.0 / ((i + 1) ** alpha) for i in range(n_skus)]
    sku_ids = [f"G{i:03d}" for i in range(n_skus)]
    sids_loc = [f"L{i:02d}" for i in range(n_skus * 2)]
    locations = []
    xyz = {}
    for i, loc_id in enumerate(sids_loc):
        x = round(i * 1.4 + 0.7, 2); y = round(i * 0.4, 2); z = 0.0
        locations.append(Location(location_id=loc_id, zone=ZoneType.FORWARD_PICK,
                                     aisle=0, bay=i // 2, level=i % 2, x=x, y=y, z=z,
                                     capacity_volume_m3=2.0, capacity_weight_kg=200.0,
                                     pickable=True, source_type=SourceType.OBSERVED))
        xyz[loc_id] = (x, y, z)
    # 5 periods × ~40 orders
    canon_orders, canon_lines = [], []
    anchor = datetime(2025, 1, 1, tzinfo=timezone.utc)
    for i in range(n_orders):
        t = anchor + timedelta(days=(i % 5), hours=8 + (i % 8))
        oid = f"O{i:05d}"
        canon_orders.append(Order(order_id=oid, order_time=t, known_at_time=t,
                                    channel="i", cutoff=t + timedelta(hours=2),
                                    priority=0, wave_id=None, source_type=SourceType.OBSERVED))
        for k in range(rng.randint(1, 3)):
            sku = rng.choices(sku_ids, weights=weights, k=1)[0]
            canon_lines.append(OrderLine(order_id=oid, sku_id=sku, quantity=1.0,
                                          uom="ea", pick_sequence=k + 1, source_type=SourceType.OBSERVED))
    seq_params = build_sequence(sids_loc)
    sku_master = [SkuMaster(sku_id=s, category_id="IG", unit_volume_m3=0.01,
                              unit_weight_kg=5.0, case_pack=24, pallet_qty=48,
                              shelf_life_days=None, storage_class=StorageClass.AMBIENT,
                              source_type=SourceType.OBSERVED)
                  for s in sku_ids]
    bench = SequentialBenchmark(sku_master, locations, xyz,
                                canon_orders, canon_lines, seq_params, anchor,
                                mc_unit_ratio=0.0005)
    m = bench.run(seed_for_view=seed)
    b = bench.beam_search(beam_width=6, seed_for_view=seed)
    gap = (m.myopic_total - b.total_cost) / max(m.myopic_total, 1e-9)
    winners = [pr.myopic_winner.split("_")[0] for pr in m.periods]
    dist = Counter(winners)
    log(f"  myopic={m.myopic_total:.0f} bfip={b.total_cost:.0f} gap={gap*100:.2f}%")
    log(f"  winners: {dict(dist)} | distinct={len(dist)}")
    return dict(group=name, n_skus=n_skus, gap=gap,
                winners=dict(dist), fixed_best=m.fixed_best.split("_")[0],
                myopic=m.myopic_total, bfip=b.total_cost, n_winners=len(dist))


log("=== R25: Instacart multi-group T0 ===")
log("Instacart actual: top-10% = 81.4%, mid-10% = 9.5% of order lines")
results = []
results.append(run_group("top10pct_concentrated", n_skus=20, alpha=1.5, seed=42))
results.append(run_group("mid10pct_flatter", n_skus=20, alpha=1.0, seed=42))

out = ROOT / "outputs" / "experiments" / "r25_instacart_groups.md"
with open(out, "w") as f:
    f.write("# R25 — Instacart Multi-Group T0 Validation\n\n")
    f.write(f"**Date**: {datetime.now(timezone.utc).isoformat()}\n\n")
    f.write("**Question**: Does T0 diversity hold across demand-concentration\n")
    f.write("regimes? Instacart: top-10% SKUs = 81.4%, mid-10% = 9.5% of order lines.\n")
    f.write("Proxied by Zipf(1.5) concentrated vs Zipf(1.0) flatter.\n\n")
    f.write("## Results\n\n")
    f.write("| Group | n SKUs | myopic | BFIP | gap | winners | distinct | fixed-best |\n")
    f.write("|-------|--------|--------|------|-----|---------|----------|------------|\n")
    for r in results:
        wb = ", ".join(f"{k}({v})" for k, v in r["winners"].items())
        f.write(f"| {r['group']} | {r['n_skus']} | {r['myopic']:.0f} | {r['bfip']:.0f} | "
                f"{r['gap']*100:.2f}% | {wb} | {r['n_winners']} | {r['fixed_best']} |\n")
    f.write("\n## Interpretation\n")
    top = results[0]["n_winners"]; mid = results[1]["n_winners"]
    f.write(f"- Concentrated (top-10%): {top} distinct winners\n")
    f.write(f"- Flatter (mid-10%): {mid} distinct winners\n")
    if top >= 3 and mid >= 3:
        f.write("- **Both groups multi-winner** → T0 generalizes across regimes\n")
    else:
        f.write(f"- Mixed: top={top} vs mid={mid} winners — concentration may matter\n")
log(f"wrote {out.relative_to(ROOT)}")
log("=== done ===")
