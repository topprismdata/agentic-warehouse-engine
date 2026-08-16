"""
scripts/run_r16_trap_phase_diagram.py
— R16: T4 Controlled Trap Phase Diagram (SPEC v1.4 §5).

Instead of waiting for rare traps on random seeds, CONSTRUCT them:
  warmup(4d stable) -> transition(3d affinity-remap) -> gap(Δt stable)
  -> shock(3d move-cost ×M) -> tail(1d)
Grid: Δt ∈ {0,1,2,4} × M ∈ {2,5,10,20}; per cell NTG =
(C_myopic − C_beam)/C_myopic over the evaluated horizon (all phases after
warmup). Material trap flag: NTG > 1%.
Answers: which (LeadTimeToShock, ShockMagnitude) combinations create
inter-temporal traps for myopic optimization.

Output: outputs/experiments/r16_trap_phase_diagram.md + figures/trap_phase_diagram.png
"""

from __future__ import annotations

import argparse
import json
import random
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import yaml
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from world_state import sample as sampler
from world_state.regime_sequence import DayParams
from world_state.regime_sequence import generate_stream
from simulation.sequential import SequentialBenchmark

DELTAS = [0, 1, 2, 4]
MAGS = [2.0, 5.0, 10.0, 20.0]


class Logger:
    def __init__(self):
        self._t0 = time.time()

    def __call__(self, msg):
        print(f"[{time.time()-self._t0:7.2f}s][INFO] {msg}", flush=True)


def build_seq(sku_ids, delta: int, mag: float):
    seq = []
    d = 0
    for _ in range(4):
        seq.append(DayParams(day=d, phase="warmup")); d += 1
    for _ in range(3):
        seq.append(DayParams(day=d, phase="transition", affinity_remap=True)); d += 1
    for _ in range(delta):
        seq.append(DayParams(day=d, phase="gap")); d += 1
    for _ in range(3):
        seq.append(DayParams(day=d, phase="shock", move_cost_scale=mag)); d += 1
    seq.append(DayParams(day=d, phase="tail")); d += 1
    return seq


def run_cell(ws, seed, delta, mag, beam):
    rng = random.Random(seed)
    sm = sampler.make_sku_master(ws["n_skus"], rng)
    ids = [s.sku_id for s in sm]
    cat = {s.sku_id: s.category_id for s in sm}
    locs, xyz = sampler.make_locations(ws["n_locations"], rng)
    anchor = datetime(2025, 1, 1, tzinfo=timezone.utc)
    seq = build_seq(ids, delta, mag)
    o, l = generate_stream(ids, cat, seq, rng, anchor,
                           orders_per_day_mean=ws["orders_per_day_mean"],
                           orders_per_day_std=ws["orders_per_day_std"])
    bench = SequentialBenchmark(sm, locs, xyz, o, l, seq, anchor, mc_unit_ratio=0.0005)
    m = bench.run(seed_for_view=seed)
    b = bench.beam_search(beam_width=beam, seed_for_view=seed)
    ntg = (m.myopic_total - b.total_cost) / max(m.myopic_total, 1e-9)
    # myopic moves during gap+shock (the over-reslotting signature)
    moves_transition = sum(pr.moves[pr.myopic_winner] for pr in m.periods
                           if pr.phase == "transition")
    moves_shock = sum(pr.moves[pr.myopic_winner] for pr in m.periods
                      if pr.phase == "shock")
    dy_moves_shock = sum(r["moves"] for r in b.per_period if r["phase"] == "shock")
    return dict(ntg=ntg, my_total=m.myopic_total, dy_total=b.total_cost,
                my_trans_moves=moves_transition,
                my_shock_moves=moves_shock, dy_shock_moves=dy_moves_shock)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--seeds", type=int, nargs="+", default=[17, 97])
    p.add_argument("--smoke", action="store_true")
    p.add_argument("--beam", type=int, default=12)
    args = p.parse_args()

    log = Logger()
    log("=== run_r16_trap_phase_diagram.py (SPEC v1.4 T4) ===")
    cfg = yaml.safe_load(open(ROOT / "config" / "main_config.yaml"))
    ws = cfg["world_state"]
    if args.smoke:
        ws = dict(ws, n_skus=40, n_locations=20)
        log("  --smoke: shrunk world")

    cache_path = ROOT / "outputs" / "experiments" / "r16_trap_cells.json"
    cache = json.loads(cache_path.read_text()) if cache_path.exists() else {}

    cells = {}
    for delta in DELTAS:
        for mag in MAGS:
            per_seed = []
            for seed in args.seeds:
                key = f"{delta}|{mag}|{seed}|{ws['n_skus']}|{args.beam}"
                cell = cache.get(key)
                if cell is None:
                    cell = run_cell(ws, seed, delta, mag, args.beam)
                    cache[key] = cell
                    log(f"Δt={delta} M={mag:4.0f} seed{seed}: "
                        f"NTG={cell['ntg']*100:5.2f}% "
                        f"my(shock mv)={cell['my_shock_moves']:3d} "
                        f"dy(shock mv)={cell['dy_shock_moves']:3d}")
                per_seed.append(cell)
            cells[(delta, mag)] = per_seed

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(cache))

    # aggregate: mean NTG per cell
    grid = [[statistics.fmean(c["ntg"] for c in cells[(d, mm)]) * 100
             for mm in MAGS] for d in DELTAS]

    log("NTG grid (rows=Δt, cols=M):")
    for d, row in zip(DELTAS, grid):
        log(f"  Δt={d}: " + " ".join(f"{v:6.2f}%" for v in row))

    # heatmap
    fig, ax = plt.subplots(figsize=(7.5, 5))
    im = ax.imshow(grid, cmap="RdYlGn_r", aspect="auto",
                   vmin=0, vmax=max(max(r) for r in grid) * 1.05)
    ax.set_xticks(range(len(MAGS)))
    ax.set_xticklabels([f"×{int(m)}" for m in MAGS])
    ax.set_yticks(range(len(DELTAS)))
    ax.set_yticklabels([str(d) for d in DELTAS])
    ax.set_xlabel("shock magnitude M_s (move-cost multiplier)")
    ax.set_ylabel("Δt days (transition → shock gap)")
    ax.set_title("Trap Phase Diagram — NormalizedTrapGain % (myopic vs dynamic)")
    for i in range(len(DELTAS)):
        for j in range(len(MAGS)):
            v = grid[i][j]
            ax.text(j, i, f"{v:.1f}%", ha="center", va="center",
                    color="black" if v < max(max(r) for r in grid) * 0.6 else "white",
                    fontsize=10)
    fig.colorbar(im, label="NTG %")
    fig.tight_layout()
    figdir = ROOT / "outputs" / "figures"
    figdir.mkdir(parents=True, exist_ok=True)
    fig.savefig(figdir / "trap_phase_diagram.png", dpi=140)
    log("wrote outputs/figures/trap_phase_diagram.png")

    # moves signature: average myopic shock-moves vs dynamic's
    sig_rows = []
    for d in DELTAS:
        for mm in MAGS:
            cs = cells[(d, mm)]
            sig_rows.append((d, mm,
                             statistics.fmean(c["ntg"] for c in cs) * 100,
                             statistics.fmean(c["my_trans_moves"] for c in cs),
                             statistics.fmean(c["my_shock_moves"] for c in cs),
                             statistics.fmean(c["dy_shock_moves"] for c in cs)))

    tbl = "\n".join(
        f"| {d} | ×{int(mm)} | {ntg:.2f}% | {'**TRAP**' if ntg > 1.0 else '—'} | "
        f"{mt:.0f} | {ms:.0f} | {ds:.0f} |"
        for d, mm, ntg, mt, ms, ds in sig_rows)

    out = ROOT / "outputs" / "experiments" / "r16_trap_phase_diagram.md"
    out.write_text(f"""# R16 — T4 Controlled Trap Phase Diagram(SPEC v1.4 §5)

**Date**: {datetime.now(timezone.utc).isoformat()} | seeds = {args.seeds} | beam = {args.beam} | world = {ws['n_skus']} SKU / {ws['n_locations']} loc
**序列**: warmup(4d)→transition(3d affinity-remap)→gap(Δt)→shock(3d,move-cost ×M)→tail(1d);NTG = (C_my − C_dy)/C_my(全评估视野)

## NTG 网格(rows = Δt = LeadTimeToShock,cols = shock magnitude)

| Δt | M | NTG | material trap(>1%) | my moves@transition | my moves@shock | dy moves@shock |
|----|---|-----|--------------------|--------------------|----------------|----------------|
{tbl}

**热力图**: `outputs/figures/trap_phase_diagram.png`

## 判读(先验:短 Δt × 大 M = trap 区域)
- 观察 trap 区域的实际边界与 NTG 梯度:Δt 变大(离 shock 远)→ myopic 的错误重配有更多
  时间摊销 → NTG 下降;M 变大 → 同样错误更贵 → NTG 上升
- my_shock_moves vs dy_shock_moves:dynamic 在 shock 期的"少搬/搬得准"签名
- 本图回答的是科学问题(什么条件组合产生 inter-temporal trap),不依赖随机 seed 运气
""")
    log(f"wrote outputs/experiments/r16_trap_phase_diagram.md")
    log("=== done ===")


if __name__ == "__main__":
    main()
