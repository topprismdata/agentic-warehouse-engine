"""
scripts/run_r15_info_boundary.py
— R15: T3 Information Boundary (SPEC v1.4 §1) — the reviewer-proofing experiment.

Question: can a DEPLOYABLE policy (Information_t only) capture the
inter-temporal opportunity that the ex-post oracle demonstrates?

Conditions per seed:
  greedyFC   deployable greedy (H=1, forecast-driven)   — today's realistic baseline
  antH2-aw   anticipatory H=2, schedule-aware           — knows tariff/labor calendar
  antH2-bl   anticipatory H=2, schedule-blind           — surprise shocks
  myopic     ex-post per-period realized oracle         — clairvoyant greedy
  oracle     ex-post beam dynamic oracle                — clairvoyant sequential (upper bound)

Capture Rate = (C_greedyFC - C_deployable) / (C_greedyFC - C_oracle).

Output: outputs/experiments/r15_info_boundary.md
"""

from __future__ import annotations

import argparse
import random
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from world_state import sample as sampler
from world_state.regime_sequence import build_sequence, generate_stream
from simulation.sequential import SequentialBenchmark
from simulation.anticipatory import anticipatory_rollout, deployable_greedy


class Logger:
    def __init__(self):
        self._t0 = time.time()

    def __call__(self, msg):
        print(f"[{time.time()-self._t0:7.2f}s][INFO] {msg}", flush=True)


def build_bench(ws, seed):
    rng = random.Random(seed)
    sm = sampler.make_sku_master(ws["n_skus"], rng)
    ids = [s.sku_id for s in sm]
    cat = {s.sku_id: s.category_id for s in sm}
    locs, xyz = sampler.make_locations(ws["n_locations"], rng)
    anchor = datetime(2025, 1, 1, tzinfo=timezone.utc)
    seq = build_sequence(ids)
    o, l = generate_stream(ids, cat, seq, rng, anchor,
                           orders_per_day_mean=ws["orders_per_day_mean"],
                           orders_per_day_std=ws["orders_per_day_std"])
    return SequentialBenchmark(sm, locs, xyz, o, l, seq, anchor, mc_unit_ratio=0.0005)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--seeds", type=int, nargs="+",
                   default=[7, 17, 27, 37, 47, 57, 67, 77, 87, 97, 107, 117])
    p.add_argument("--smoke", action="store_true")
    p.add_argument("--H", type=int, default=2)
    p.add_argument("--beam", type=int, default=20)
    args = p.parse_args()

    log = Logger()
    log("=== run_r15_info_boundary.py (SPEC v1.4 T3) ===")
    cfg = yaml.safe_load(open(ROOT / "config" / "main_config.yaml"))
    ws = cfg["world_state"]
    if args.smoke:
        ws = dict(ws, n_skus=40, n_locations=20)
        args.seeds = args.seeds[:3]
        log("  --smoke: shrunk world, 3 seeds")

    rows = []
    for seed in args.seeds:
        bench = build_bench(ws, seed)
        g = deployable_greedy(bench, seed_for_view=seed)
        aw = anticipatory_rollout(bench, H=args.H, beam_width=8,
                                  schedule_aware=True, seed_for_view=seed)
        bl = anticipatory_rollout(bench, H=args.H, beam_width=8,
                                  schedule_aware=False, seed_for_view=seed)
        m = bench.run(seed_for_view=seed)
        orc = bench.beam_search(beam_width=args.beam, seed_for_view=seed)

        def cr(c_dep):
            denom = g.total_cost - orc.total_cost
            return (g.total_cost - c_dep) / denom if abs(denom) > 1e-9 else float("nan")

        rows.append(dict(seed=seed, g=g.total_cost, aw=aw.total_cost, bl=bl.total_cost,
                         my=m.myopic_total, orc=orc.total_cost,
                         cr_aw=cr(aw.total_cost), cr_bl=cr(bl.total_cost),
                         traj_g=g.trajectory, traj_aw=aw.trajectory,
                         traj_bl=bl.trajectory))
        log(f"seed {seed}: greedyFC={g.total_cost:.0f} antAW={aw.total_cost:.0f} "
            f"antBL={bl.total_cost:.0f} | myopic={m.myopic_total:.0f} "
            f"oracle={orc.total_cost:.0f} | capture AW={rows[-1]['cr_aw']*100:5.1f}% "
            f"BL={rows[-1]['cr_bl']*100:5.1f}%")

    def fmean(xs):
        xs = [x for x in xs if x == x]
        return statistics.fmean(xs) if xs else float("nan")

    mean = dict(g=fmean([r["g"] for r in rows]), aw=fmean([r["aw"] for r in rows]),
                bl=fmean([r["bl"] for r in rows]), my=fmean([r["my"] for r in rows]),
                orc=fmean([r["orc"] for r in rows]),
                cr_aw=fmean([r["cr_aw"] for r in rows]),
                cr_bl=fmean([r["cr_bl"] for r in rows]))
    # clamp nonsensical capture (oracle above greedy) for reporting clarity
    n_valid = sum(1 for r in rows if r["g"] > r["orc"] + 1e-9)
    log(f"AGG: capture(aware)={mean['cr_aw']*100:.1f}% capture(blind)={mean['cr_bl']*100:.1f}% "
        f"| seeds with positive oracle headroom: {n_valid}/{len(rows)}")

    detail = "\n".join(
        f"| {r['seed']} | {r['g']:.0f} | {r['aw']:.0f} | {r['bl']:.0f} | "
        f"{r['my']:.0f} | {r['orc']:.0f} | "
        f"{r['cr_aw']*100 if r['cr_aw']==r['cr_aw'] else float('nan'):.1f}% | "
        f"{r['cr_bl']*100 if r['cr_bl']==r['cr_bl'] else float('nan'):.1f}% |"
        for r in rows)
    traj_tbl = "\n".join(
        f"| {r['seed']} | {' → '.join(e.split('_')[0] for e in r['traj_g'])} | "
        f"{' → '.join(e.split('_')[0] for e in r['traj_aw'])} |"
        f"{' → '.join(e.split('_')[0] for e in r['traj_bl'])} |"
        for r in rows)

    out = ROOT / "outputs" / "experiments" / "r15_info_boundary.md"
    out.write_text(f"""# R15 — T3 信息边界:可部署策略能否捕获 inter-temporal 机会(SPEC v1.4 §1)

**Date**: {datetime.now(timezone.utc).isoformat()} | seeds = {len(args.seeds)} | H = {args.H} | oracle beam = {args.beam} | world = {ws['n_skus']} SKU / {ws['n_locations']} loc
**Anticipatory 内部成本模型**: Σ p50×dist 线性代理(部署者拿不到 realized TSP;模型失配是问题的一部分)

## 信息体制阶梯(cost:oracle ≤ 可部署 ≤ 贪心)

| seed | greedyFC(H=1) | ant H={args.H} aware | ant H={args.H} blind | myopic(ex-post) | oracle(ex-post) | Capture aware | Capture blind |
|------|---------------|----------------------|----------------------|-----------------|------------------|---------------|---------------|
{detail}

- mean: greedyFC={mean['g']:.0f} | aware={mean['aw']:.0f} | blind={mean['bl']:.0f} | myopic={mean['my']:.0f} | oracle={mean['orc']:.0f}
- **mean CaptureRate: aware = {mean['cr_aw']*100:.1f}%,blind = {mean['cr_bl']*100:.1f}%**
- oracle headroom 为正的 seeds:{n_valid}/{len(rows)}(其余 seed oracle≈greedy,分母≈0,capture 无意义)

## Trajectories(greedyFC / anticipatory-aware / anticipatory-blind)

| seed | greedyFC | ant aware | ant blind |
|------|----------|-----------|-----------|
{traj_tbl}

## 判读(回应审稿人"凭什么知道明天搬库变贵")
- **schedule-aware**: 已排期成本(tariff/labor calendar)是合法 Information_t;
  capture 高 → 机会主要来自可预知日程
- **schedule-blind**: 假设当前成本持续(纯 surprise shock);capture 低 →
  机会依赖不可预知冲击时,DWERP 仍需 robustness/option-value 机制
- greedyFC vs myopic(ex-post)的差 = 贪心 oracle 的"作弊量";本实验的可部署
  基线是 greedyFC(不是 ex-post myopic),CaptureRate 以它为分母
- 已知限制:H={args.H} 的前瞻窗覆盖 mc_shock 需 Δt≤H;更优 anticipatory
  (probabilistic shock model / option-value hold)是后续工作,当前结果为
  **下界**意义上的可部署性证据

## 与 T1a/T1b 的衔接
seed 17(oracle gap 5.34%)在本表中的 capture 见明细行 —— 它回答:
"知道日程的部署者能拿到多少;不知道的损失多少"。
""")
    log(f"wrote outputs/experiments/r15_info_boundary.md")
    log("=== done ===")


if __name__ == "__main__":
    main()
