"""
R24: CrossStacks validation — does the WEPA null result generalize?

CrossStacks is structurally different from WEPA:
- 8,401 SKUs (vs 1,000 in WEPA) — broader demand distribution
- Balanced delivery/retrieval (true cross-docking pattern)
- Larger layout (1,952 storage cells)

If WEPA-Natural gap=0 was a WEPA-specific artifact, CrossStacks may
show a different pattern. If both are gap=0, the deployment-boundary
finding is stronger (two independent warehouses).
"""

from __future__ import annotations
import json, random, sys
from datetime import datetime, timezone
from pathlib import Path

import yaml
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from world_state.wepa_adapter import build_crossstacks_canonical
from world_state.regime_sequence import DayParams
from world_state.schemas import SkuMaster, StorageClass, SourceType
from simulation.sequential import SequentialBenchmark
from or_experts.policies import EXPERT_IDS
from evaluation.route_cost import total_route_cost
import time

t0 = time.time()
log = lambda m: print(f"[{time.time()-t0:.1f}s] {m}", flush=True)

log("=== R24: CrossStacks validation ===")
data = build_crossstacks_canonical(top_n_skus=40, max_orders=5000)
log(f"  {data['n_retrievals']} orders, {len(data['locations'])} locations")

orders, lines = data["orders"], data["lines"]
n_periods = 5
order_day = {o.order_id: int((o.order_time - data["anchor"]).days) for o in orders}
max_day = max(order_day.values()) + 1
seq = [DayParams(day=d, phase=f"p{min(d * n_periods // max(1, max_day), n_periods-1)}")
       for d in range(max_day + 2)]

sku_master = [SkuMaster(sku_id=s, category_id="CS", unit_volume_m3=0.01,
                        unit_weight_kg=5.0, case_pack=24, pallet_qty=48,
                        shelf_life_days=None, storage_class=StorageClass.AMBIENT,
                        source_type=SourceType.OBSERVED)
              for s in data["sku_ids"]]

bench = SequentialBenchmark(sku_master, data["locations"], data["xyz"],
                            orders, lines, seq, data["anchor"], mc_unit_ratio=0.0005)
m = bench.run(seed_for_view=42)
b = bench.beam_search(beam_width=20, seed_for_view=42)
gap = (m.myopic_total - b.total_cost) / max(m.myopic_total, 1e-9)
winners = [pr.myopic_winner for pr in m.periods]
log(f"myopic={m.myopic_total:.0f} bfip={b.total_cost:.0f} gap={gap*100:.2f}%")
log(f"winners: {[w.split('_')[0] for w in winners]}")

out = ROOT / "outputs" / "experiments" / "r24_crossstacks.md"
out.write_text(f"""# R24 — CrossStacks Validation (WEPA-Natural replicate)

**Date**: {datetime.now(timezone.utc).isoformat()} | SKUs = 40 | orders = {data['n_retrievals']} | periods = {n_periods}

## Result
- myopic total: **{m.myopic_total:.0f}**
- BFIP total: **{b.total_cost:.0f}**
- **gap = {gap*100:.2f}%**
- winners by period: {[w.split('_')[0] for w in winners]}
- fixed-best: {m.fixed_best} ({m.fixed_best_total:.0f})

## Comparison with WEPA-Natural (R21)
| Dataset | gap | Myopic=BFIP? | Winner diversity |
|---------|-----|---------------|------------------|
| WEPA    | 0.00% | yes | 3-4 distinct |
| CrossStacks | **{gap*100:.2f}%** | {'yes' if abs(gap) < 0.005 else 'no'} | {len(set(winners))} distinct |

## Interpretation
{'Both independent warehouses show gap=0 — the deployment-boundary finding (paper §11) is not WEPA-specific. Trap requires non-stationary regime changes beyond normal warehouse operations.' if abs(gap) < 0.005 else f'CrossStacks shows a gap of {gap*100:.2f}% — interesting discrepancy with WEPA. The larger SKU universe (8,401 vs ~1,000) may create regime-like variation in the natural data. Investigate further.'}
""")
log(f"wrote outputs/experiments/r24_crossstacks.md")
log("=== done ===")
