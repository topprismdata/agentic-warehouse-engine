"""
scripts/run_r14_t15_transition_costs.py
— R14: T1.5 (SPEC v1.4 §3) — C_move vs C_switch decomposition as a
METHODOLOGY result.

Questions:
  1. False Switch Penalty rate: expert name changed, layout ~unchanged
     (d(A_t,A_{t-1}) <= eps moves) — the 1[E!=E'] penalty charges a cost
     the warehouse never physically pays.
  2. Hidden Physical Reconfiguration rate: expert SAME, layout massively
     changed (>= theta moves) — the indicator penalty misses real cost.
  3. Three cost conditions — move-only / switch-only / both — do optimal
     trajectories and the myopic-vs-dynamic gap change?

d(A_t, A_{t-1}) proxied by n_moves (declared in SPEC v1.4 §3).

Output: outputs/experiments/r14_t15_transition_costs.md
"""

from __future__ import annotations

import argparse
import random
import statistics
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from world_state import sample as sampler
from world_state.regime_sequence import build_sequence, generate_stream
from simulation.sequential import SequentialBenchmark

EPS_FALSE_SWITCH = 2     # <= 2 moves counts as "layout ~unchanged"
THETA_HIDDEN = 20        # >= 20 moves under the SAME expert = hidden reconfig
SWITCH_PENALTIES = [1.0, 5.0, 20.0]   # lambda_s multipliers for switch-only


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


def traj_events(traj_experts, traj_moves):
    """Count false-switch and hidden-reconfig events along a trajectory."""
    false_sw = hidden = 0
    for i in range(1, len(traj_experts)):
        changed_name = traj_experts[i] != traj_experts[i - 1]
        moved = traj_moves[i]
        if changed_name and moved <= EPS_FALSE_SWITCH:
            false_sw += 1
        if (not changed_name) and moved >= THETA_HIDDEN:
            hidden += 1
    return false_sw, hidden


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--seeds", type=int, nargs="+", default=[7, 17, 27, 37, 97, 117])
    p.add_argument("--smoke", action="store_true")
    p.add_argument("--beam", type=int, default=20)
    args = p.parse_args()

    log = Logger()
    log("=== run_r14_t15_transition_costs.py (SPEC v1.4 T1.5) ===")
    cfg = yaml.safe_load(open(ROOT / "config" / "main_config.yaml"))
    ws = cfg["world_state"]
    if args.smoke:
        ws = dict(ws, n_skus=40, n_locations=20)
        args.seeds = args.seeds[:2]
        log("  --smoke: shrunk world")

    conditions = {"move_only": dict(lambda_move=1.0, lambda_switch=0.0)}
    for ls in SWITCH_PENALTIES:
        conditions[f"switch_only(s={ls:g})"] = dict(lambda_move=0.0, lambda_switch=ls)
    conditions["both(m=1,s=5)"] = dict(lambda_move=1.0, lambda_switch=5.0)

    # condition -> seed -> dict(results)
    cond_res = {}

    for cname, kw in conditions.items():
        per_seed = {}
        fs_my = fs_dy = hd_my = hd_dy = 0
        gaps = []
        for seed in args.seeds:
            bench = build_bench(ws, seed)
            bench.lambda_move = kw["lambda_move"]
            bench.lambda_switch = kw["lambda_switch"]
            m = bench.run()
            b = bench.beam_search(beam_width=args.beam)
            my_e = [pr.myopic_winner for pr in m.periods]
            my_m = [pr.moves[pr.myopic_winner] for pr in m.periods]
            dy_e = [r["expert"] for r in b.per_period]
            dy_m = [r["moves"] for r in b.per_period]
            a, c = traj_events(my_e, my_m)
            d, e = traj_events(dy_e, dy_m)
            fs_my += a; hd_my += c; fs_dy += d; hd_dy += e
            gap = (m.myopic_total - b.total_cost) / max(m.myopic_total, 1e-9)
            gaps.append(gap)
            per_seed[seed] = dict(gap=gap, my=my_e, dy=dy_e,
                                  my_moves=my_m, dy_moves=dy_m,
                                  my_total=m.myopic_total, dy_total=b.total_cost)
            log(f"  {cname:20s} seed{seed}: gap={gap*100:5.2f}% "
                f"my_switches={len(set(my_e))-1} dy_switches={len(set(dy_e))-1}")
        n_trans = (len(args.seeds)) * (len(per_seed[args.seeds[0]]["my"]) - 1)
        cond_res[cname] = dict(per_seed=per_seed, fs_my=fs_my, fs_dy=fs_dy,
                               hd_my=hd_my, hd_dy=hd_dy, n_trans=n_trans,
                               mean_gap=statistics.fmean(gaps))
        log(f"  {cname}: false-switch my={fs_my}/{n_trans} dy={fs_dy}/{n_trans} | "
            f"hidden-reconfig my={hd_my}/{n_trans} dy={hd_dy}/{n_trans} | "
            f"mean gap={cond_res[cname]['mean_gap']*100:.2f}%")

    # ---- report ----------------------------------------------------------------
    rows = "\n".join(
        f"| {cn} | {r['fs_my']}/{r['n_trans']} ({r['fs_my']/r['n_trans']:.0%}) | "
        f"{r['fs_dy']}/{r['n_trans']} ({r['fs_dy']/r['n_trans']:.0%}) | "
        f"{r['hd_my']}/{r['n_trans']} ({r['hd_my']/r['n_trans']:.0%}) | "
        f"{r['hd_dy']}/{r['n_trans']} ({r['hd_dy']/r['n_trans']:.0%}) | "
        f"{r['mean_gap']*100:.2f}% |"
        for cn, r in cond_res.items())

    out = ROOT / "outputs" / "experiments" / "r14_t15_transition_costs.md"
    out.write_text(f"""# R14 — T1.5:C_move vs C_switch 拆分(SPEC v1.4 §3,Methodology Result)

**Date**: {datetime.now(timezone.utc).isoformat()} | seeds = {args.seeds} | beam = {args.beam} | world = {ws['n_skus']} SKU / {ws['n_locations']} loc
**d(A,A_prev) 代理**: n_moves(SPEC v1.4 声明)| FalseSwitch 阈: moves <= {EPS_FALSE_SWITCH};HiddenReconfig 阈: moves >= {THETA_HIDDEN}

## 两类代理失真(指示罚 1[expert_changed] 的缺陷)

| 条件 | False Switch(myopic) | False Switch(dynamic) | Hidden Reconfig(myopic) | Hidden Reconfig(dynamic) | mean gap |
|------|----------------------|----------------------|-------------------------|--------------------------|----------|
{rows}

- **False Switch** = 换了 expert 名但仓库几乎没动 —— 指示罚收取了物理上不存在的成本
- **Hidden Reconfig** = expert 没换但大量搬库 —— 指示罚漏掉真实成本

## 判读
- 若任一失真率显著(≥10% 的期次),则 **"algorithm-switch count is an inadequate
  surrogate for warehouse reconfiguration cost"** 成立 → 支持 C_transition =
  d(layout_t, layout_t+1) 的公式化(SPEC v1.4 §2)
- switch-only 条件下 gap 的变化 = 纯策略切换成本对 sequential 价值的贡献
- move-only vs both 的 gap 差 = 两种成本的交互

## 后续
T3 信息边界实验(anticipatory receding-horizon + CaptureRate)—— SPEC v1.4 §1。
""")
    log(f"wrote outputs/experiments/r14_t15_transition_costs.md")
    log("=== done ===")


if __name__ == "__main__":
    main()
