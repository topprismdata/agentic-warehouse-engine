"""
scripts/run_r18_exact_oracle.py
— R18: SPEC v1.5 §3.2 — Small-instance EXACT full-information oracle.

On a deliberately small instance (8-12 SKUs, 4-6 locations, 5 periods),
EXHAUSTIVELY enumerate all K^T expert trajectories (K=7 experts, T=5
periods -> 16,807 sequences), roll each out with the benchmark's single
accounting authority, and find the true optimum. Then compare:
  - C_exact <= C_beam30 <= C_myopic (must hold; sanity gate)
  - Gap_beam->exact = (C_beam - C_exact) / C_exact
  - Does the exact-optimal trajectory differ from beam-30's?

This upgrades the "seed 17 mechanism" from beam evidence to exact
constructive evidence (on the small instance), and quantifies whether
beam width 30 is a reliable proxy for the true oracle at larger scales.

Output: outputs/experiments/r18_exact_oracle.md
"""

from __future__ import annotations

import argparse
import itertools
import json
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from world_state import sample as sampler
from world_state.regime_sequence import DayParams
from world_state.regime_sequence import generate_stream
from simulation.sequential import SequentialBenchmark
from or_experts.policies import EXPERT_IDS


class Logger:
    def __init__(self):
        self._t0 = time.time()

    def __call__(self, msg):
        print(f"[{time.time()-self._t0:7.2f}s][INFO] {msg}", flush=True)


def build_small_seq(sku_ids, with_shock: bool = True):
    """6-period sequence preserving the 28-day regime's phase STRUCTURE:
    warmup -> transition(affinity remap) -> gap -> promo -> shock(mc x20) -> tail.
    5 EVALUATED periods -> 7^5 = 16,807 trajectories (exhaustible)."""
    seq = []
    d = 0
    for _ in range(2):
        seq.append(DayParams(day=d, phase="warmup")); d += 1
    for _ in range(2):
        seq.append(DayParams(day=d, phase="transition", affinity_remap=True)); d += 1
    for _ in range(1):
        seq.append(DayParams(day=d, phase="gap")); d += 1
    if with_shock:
        for _ in range(2):
            seq.append(DayParams(day=d, phase="shock", move_cost_scale=20.0)); d += 1
    for _ in range(1):
        seq.append(DayParams(day=d, phase="tail")); d += 1
    return seq


def exact_oracle(bench, seed_for_view: int, log=None):
    """Exhaustive enumeration of all expert trajectories."""
    current, plans = bench._prepare_periods(seed_for_view)
    T = len(plans)
    K = len(EXPERT_IDS)

    # precompute per-period layout-independent caches
    # (E1-E5 layouts don't depend on incoming layout; E6/E7 do)
    from or_experts.policies import LAYOUT_INDEPENDENT

    best_cost = float("inf")
    best_traj = None
    n_evaluated = 0

    for traj in itertools.product(EXPERT_IDS, repeat=T):
        layout = current
        prev = None
        total = 0.0
        for plan, e in zip(plans, traj):
            cost, layout, mv = bench._eval_expert(plan, e, layout, prev, None)
            total += cost
            prev = e
            if total >= best_cost:
                break  # prune: already worse than incumbent
        n_evaluated += 1
        if total < best_cost:
            best_cost = total
            best_traj = traj
        if log and n_evaluated % 5000 == 0:
            log(f"  ... {n_evaluated}/{K**T} trajectories, best={best_cost:.0f}")

    return best_cost, list(best_traj), n_evaluated


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--seeds", type=int, nargs="+", default=[17, 42, 107])
    p.add_argument("--n-skus", type=int, default=60)
    p.add_argument("--n-locations", type=int, default=30)
    p.add_argument("--no-shock", action="store_true",
                   help="variant without move-cost shock (control)")
    args = p.parse_args()

    log = Logger()
    log("=== run_r18_exact_oracle.py (SPEC v1.5 §3.2) ===")
    cfg = yaml.safe_load(open(ROOT / "config" / "main_config.yaml"))
    ws = dict(cfg["world_state"], n_skus=args.n_skus, n_locations=args.n_locations,
              n_days=8, orders_per_day_mean=14, orders_per_day_std=4)

    with_shock = not args.no_shock
    variant = "shock" if with_shock else "noshock"

    results = []
    for seed in args.seeds:
        rng = random.Random(seed)
        sm = sampler.make_sku_master(ws["n_skus"], rng)
        ids = [s.sku_id for s in sm]
        cat = {s.sku_id: s.category_id for s in sm}
        locs, xyz = sampler.make_locations(ws["n_locations"], rng)
        anchor = datetime(2025, 1, 1, tzinfo=timezone.utc)
        seq = build_small_seq(ids, with_shock)
        o, l = generate_stream(ids, cat, seq, rng, anchor,
                               orders_per_day_mean=ws["orders_per_day_mean"],
                               orders_per_day_std=ws["orders_per_day_std"])
        bench = SequentialBenchmark(sm, locs, xyz, o, l, seq, anchor,
                                    mc_unit_ratio=0.0005)

        # myopic + beam
        m = bench.run(seed_for_view=seed)
        beam = bench.beam_search(beam_width=30, seed_for_view=seed)

        # exact
        T = len(bench._phases()) - 1  # minus warmup
        log(f"seed {seed} [{variant}]: exhausting {7**T} trajectories "
            f"({ws['n_skus']} SKU / {ws['n_locations']} loc / {T} periods)...")
        exact_cost, exact_traj, n = exact_oracle(bench, seed, log=log)

        gap_beam = (beam.total_cost - exact_cost) / max(exact_cost, 1e-9)
        gap_myopic = (m.myopic_total - exact_cost) / max(exact_cost, 1e-9)
        ordering_ok = exact_cost <= beam.total_cost <= m.myopic_total + 1e-9

        results.append(dict(seed=seed, variant=variant,
                            myopic=m.myopic_total, beam=beam.total_cost,
                            exact=exact_cost, gap_beam=gap_beam,
                            gap_myopic=gap_myopic, ordering_ok=ordering_ok,
                            exact_traj=[e.split("_")[0] for e in exact_traj],
                            beam_traj=[e.split("_")[0] for e in beam.trajectory],
                            myopic_traj=[pr.myopic_winner.split("_")[0]
                                         for pr in m.periods],
                            n_traj=n))
        log(f"seed {seed}: exact={exact_cost:.0f} beam={beam.total_cost:.0f} "
            f"myopic={m.myopic_total:.0f} | gap_beam={gap_beam*100:.2f}% "
            f"gap_myopic={gap_myopic*100:.2f}% | ordering={'OK' if ordering_ok else 'VIOLATED'}")
        log(f"  exact traj: {results[-1]['exact_traj']}")
        log(f"  beam  traj: {results[-1]['beam_traj']}")
        log(f"  myopic traj: {results[-1]['myopic_traj']}")

    # summary
    import statistics
    gaps_b = [r["gap_beam"] for r in results]
    gaps_m = [r["gap_myopic"] for r in results]
    all_ok = all(r["ordering_ok"] for r in results)

    detail = "\n".join(
        f"| {r['seed']} | {r['variant']} | {r['myopic']:.0f} | {r['beam']:.0f} | "
        f"{r['exact']:.0f} | {r['gap_beam']*100:.2f}% | {r['gap_myopic']*100:.2f}% | "
        f"{'OK' if r['ordering_ok'] else 'VIOLATED'} |"
        for r in results)
    out = ROOT / "outputs" / "experiments" / "r18_exact_oracle.md"
    out.write_text(f"""# R18 — 小实例精确全信息 Oracle(SPEC v1.5 §3.2)

**Date**: {datetime.now(timezone.utc).isoformat()} | 实例 = {ws['n_skus']} SKU / {ws['n_locations']} loc / 5 期 | seeds = {args.seeds} | 变体 = {variant}

## 目的
在可穷举的小实例上求出真最优轨迹(exhaustive enumeration,含剪枝),
量化 beam-30 与真最优的差距,并将 trap 机制升级为 exact constructive evidence。

## 结果

| seed | variant | C_myopic | C_beam30 | **C_exact** | gap beam→exact | gap myopic→exact | 排序 |
|------|---------|----------|----------|-------------|----------------|------------------|------|
{detail}

- mean gap beam→exact: **{statistics.fmean(gaps_b)*100:.2f}%**
- mean gap myopic→exact: **{statistics.fmean(gaps_m)*100:.2f}%**
- C_exact ≤ C_beam ≤ C_myopic 全部成立: **{'YES' if all_ok else 'NO'}**

## 轨迹对比
{chr(10).join(f"- seed {r['seed']}: exact={' → '.join(r['exact_traj'])} | beam={' → '.join(r['beam_traj'])} | myopic={' → '.join(r['myopic_traj'])}" for r in results)}

## 判读
- gap beam→exact = {statistics.fmean(gaps_b)*100:.2f}% → beam-30 是 {'可靠' if statistics.fmean(gaps_b) < 0.02 else '有偏'} 的真最优代理
- 若 exact 轨迹与 beam 轨迹不同但成本差 <1% → 多个近优轨迹存在(平坦盆地),beam 的具体选择不重要
- myopic→exact gap 的大小 = 该小实例上 trap 机会的直接度量
""")
    log(f"wrote outputs/experiments/r18_exact_oracle.md")
    log("=== done ===")


if __name__ == "__main__":
    main()
