"""
scripts/run_r11_t1_oracle.py
— R11: T1 Myopic vs Dynamic Oracle (SPEC v1.2 §3).

Question: does LONG-HORIZON expert routing beat per-period greedy when both
pay physical move costs? Beam-search dynamic oracle (myopic trajectory
injected as guaranteed incumbent → beam ≤ myopic exactly; the reported gap
is a conservative LOWER BOUND on the true oracle gap).

Decision rule (declared before running):
  GO         : beam beats myopic by >= 2% on ALL seeds
  NO-GO      : gap < 0.5% on ALL seeds
  BORDERLINE : otherwise → widen beam before deciding

Also reported (v1.2 §8): Over-Reslotting (Σ moves myopic vs dynamic),
Policy Stability (expert switches), per-seed trajectories, beam-width
sensitivity (8/30/80 on seed 0's world).

Output: outputs/experiments/r11_t1_oracle.md
"""

from __future__ import annotations

import argparse
import random
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
    return SequentialBenchmark(sm, locs, xyz, o, l, seq, anchor,
                               mc_unit_ratio=0.0005)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--seeds", type=int, nargs="+", default=[7, 17, 27])
    p.add_argument("--smoke", action="store_true")
    p.add_argument("--beam", type=int, default=30)
    args = p.parse_args()

    log = Logger()
    log("=== run_r11_t1_oracle.py (v1.2 T1) ===")
    cfg = yaml.safe_load(open(ROOT / "config" / "main_config.yaml"))
    ws = cfg["world_state"]
    if args.smoke:
        ws = dict(ws, n_skus=40, n_locations=20)
        args.seeds = args.seeds[:2]
        log("  --smoke: shrunk world")

    rows, gaps = [], []
    for seed in args.seeds:
        bench = build_bench(ws, seed)
        m = bench.run()
        b = bench.beam_search(beam_width=args.beam)
        gap = (m.myopic_total - b.total_cost) / m.myopic_total
        gaps.append(gap)
        my_moves = sum(pr.moves[pr.myopic_winner] for pr in m.periods)
        dy_moves = sum(r["moves"] for r in b.per_period)
        my_switches = sum(1 for i in range(1, len(m.periods))
                          if m.periods[i].myopic_winner != m.periods[i-1].myopic_winner)
        dy_switches = sum(1 for i in range(1, len(b.trajectory))
                          if b.trajectory[i] != b.trajectory[i-1])
        rows.append((seed, m.myopic_total, b.total_cost, gap,
                     m.fixed_best, m.fixed_best_total,
                     my_moves, dy_moves, my_switches, dy_switches,
                     [pr.myopic_winner for pr in m.periods], b.trajectory))
        log(f"seed {seed}: myopic={m.myopic_total:.0f} beam({args.beam})={b.total_cost:.0f} "
            f"gap={gap*100:.2f}% | moves my/dy={my_moves}/{dy_moves} | "
            f"switches my/dy={my_switches}/{dy_switches}")

    # gates
    go = all(g >= 0.02 for g in gaps)
    nogo = all(g < 0.005 for g in gaps)
    verdict = "GO" if go else ("NO-GO" if nogo else "BORDERLINE")

    # beam-width sensitivity on the first seed
    ws0 = rows[0]
    sens = []
    for w in (8, 30, 80):
        bench = build_bench(ws, args.seeds[0])
        b = bench.beam_search(beam_width=w)
        sens.append((w, b.total_cost))
        log(f"sensitivity: beam({w}) = {b.total_cost:.0f}")
    conv = (max(t for _, t in sens) - min(t for _, t in sens)) / sens[-1][1] if sens else 1.0

    # myopic-vs-beam sanity (asserted inside beam_search, reported here too)
    sanity = all(b <= m + 1e-9 for (_, m, b, *_r) in rows)

    log(f"T1 gates: gaps={[f'{g*100:.2f}%' for g in gaps]} -> {verdict} "
        f"| beam<=myopic sanity={'PASS' if sanity else 'FAIL'} | "
        f"width-convergence spread={conv*100:.3f}%")

    detail = "\n".join(
        f"| {sd} | {mt:.0f} | {bt:.0f} | **{g*100:.2f}%** | {fb}({fbt:.0f}) | "
        f"{mm}/{dm} | {ms}/{ds} |"
        for sd, mt, bt, g, fb, fbt, mm, dm, ms, ds, _a, _b in rows)
    traj_rows = "\n".join(
        f"| {sd} | {' → '.join(e.split('_')[0] for e in mt_)} | {' → '.join(e.split('_')[0] for e in dt_)} |"
        for sd, *_x, mt_, dt_ in rows)

    out = ROOT / "outputs" / "experiments" / "r11_t1_oracle.md"
    out.write_text(f"""# R11 — T1 Myopic vs Dynamic Oracle(v1.2 §3,序列协议,λs=0)

**Date**: {datetime.now(timezone.utc).isoformat()} | seeds = {args.seeds} | beam = {args.beam} | world = {ws['n_skus']} SKU / {ws['n_locations']} loc
**口径**: mc_unit 锚定冷启动 layout(trajectory 无关);myopic 与 beam 共用同一 benchmark 实例与评估函数(单一记账权威)

## 方法
- Myopic Oracle:逐期事后 argmin(含当期 move 罚;路径依赖 rollout)
- Dynamic Oracle(近似):宽度 {args.beam} beam search,**myopic trajectory 每层注入保底** → beam ≤ myopic 严格成立;报告的 gap 是真实 oracle gap 的**保守下界**(beam 更优 x% 即证明 oracle ≥ x%)
- 判据(预先声明):GO = 全 seeds gap ≥ 2%;NO-GO = 全 seeds < 0.5%;之间 BORDERLINE(先加宽 beam 再定)

## 结果

| seed | myopic total | beam total | gap | fixed-best | Σmoves my/dy | switches my/dy |
|------|-------------|------------|-----|------------|--------------|----------------|
{detail}

**mean gap = {sum(gaps)/len(gaps)*100:.2f}%**(全 seeds: {', '.join(f'{g*100:.2f}%' for g in gaps)})

## Trajectories(myopic vs beam)

| seed | myopic | beam(dynamic) |
|------|--------|---------------|
{traj_rows}

## Beam-width 敏感性(seed {args.seeds[0]})

| width | total |
|-------|-------|
{chr(10).join(f"| {w} | {t:.0f} |" for w, t in sens)}

- spread(最大-最小)/best = **{conv*100:.3f}%**(≤0.3% 视为收敛)

## Gates
- beam ≤ myopic(全 seeds,内部 assert): **{'PASS' if sanity else 'FAIL'}**
- beam-width 收敛: **{'PASS' if conv <= 0.003 else 'WARN'}**({conv*100:.3f}%)
- **T1 verdict: {verdict}**

## 判读
- {'**GO**:长期 horizon 优化显著优于逐期贪婪(≥2% 全 seeds,保守下界)→ sequential expert routing 有真实价值,DWERP 成立;继续 T2。' if verdict=='GO' else ('**NO-GO**:beam 宽度内未发现 sequential 增值(<0.5% 全 seeds)。注意这是 beam-limited 否定,非严格证明;若加宽 beam 仍 null,报告 v1.2 §3 的"Myopic≈Dynamic"分支。' if verdict=='NO-GO' else '**BORDERLINE**:2%/0.5% 之间 → 加宽 beam/加 seeds 后复跑再定。')}
- Over-Reslotting(v1.2 §8):若 myopic Σmoves > dynamic Σmoves 且 gap>0,即贪婪过度重配置的直接证据(逐行见上表)。
- 口径变更声明:mc_unit 从 R10 的 myopic-path 锚定改为冷启动锚定(beam 可比性要求);myopic 数字与 R10 有微小差异,以本报告为准。
""")
    log(f"wrote outputs/experiments/r11_t1_oracle.md")
    sys.exit(0 if go else (3 if nogo else 1))


if __name__ == "__main__":
    main()
