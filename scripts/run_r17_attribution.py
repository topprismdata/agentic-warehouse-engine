"""
scripts/run_r17_attribution.py
— R17: SPEC v1.5 §3.1 — WHY is capture 0? (attribution experiment)

Fixed warehouse trajectory per seed; swap ONLY the internal cost model the
RHC policy plans with: L1 linear / L2 stop-aware / L3 route surrogate /
L4 realized (cheating ceiling). Sweep H ∈ {1,2,3,7}. Record per level:
  - RankingFidelity: Spearman rho + Kendall tau of (predicted per-expert
    costs) vs (realized per-expert costs) at each period (SPEC v1.5 §5)
  - Top-1 / Top-2 hit rates (does the model pick the realized winner?)
  - realized total cost of the RHC trajectory -> CaptureRate vs BFIP
Deliverable: RF -> capture curve + which factor binds.

Output: outputs/experiments/r17_attribution.md (+ figures/rf_capture.png)
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
from world_state.regime_sequence import build_sequence, generate_stream
from simulation.sequential import SequentialBenchmark
from simulation.cost_models import MODEL_REGISTRY, l4_oracle_cost
from or_experts.policies import EXPERT_IDS, run_policy


class Logger:
    def __init__(self):
        self._t0 = time.time()

    def __call__(self, msg):
        print(f"[{time.time()-self._t0:7.2f}s][INFO] {msg}", flush=True)


def rankdata(xs):
    """Average-rank helper (ties get mean rank)."""
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    ranks = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        avg = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    return ranks


def spearman(a, b):
    ra, rb = rankdata(a), rankdata(b)
    ma, mb = statistics.fmean(ra), statistics.fmean(rb)
    num = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    da = sum((x - ma) ** 2 for x in ra) ** 0.5
    db = sum((y - mb) ** 2 for y in rb) ** 0.5
    return num / (da * db) if da * db > 1e-12 else float("nan")


def kendall(a, b):
    n = len(a)
    c = d = 0
    for i in range(n):
        for j in range(i + 1, n):
            s1 = (a[i] - a[j]) * (b[i] - b[j])
            if s1 > 0:
                c += 1
            elif s1 < 0:
                d += 1
    return (c - d) / (n * (n - 1) / 2) if n > 1 else float("nan")


def rhc_rollout(bench, model_fn, H: int, beam_width: int, seed_for_view: int,
                schedule_blind: bool = False):
    """Receding-horizon policy planning with `model_fn` (agent's belief).

    schedule_blind=True: future periods' move-cost uses the CURRENT period's
    mc_unit (surprise shocks); False = schedule-aware (tariff calendar known).
    v1.5 review Z2: R17's first full run unknowingly ran schedule-AWARE
    lookahead for all models — that clairvoyance is why L1 hit +51% where
    R15's (mostly-blind) anticipatory got ~0. Both modes now explicit."""
    current, plans = bench._prepare_periods(seed_for_view)
    layout = current
    prev = None
    total = 0.0
    traj = []
    rf_records = []   # (rho, tau, top1, top2)
    for i, plan in enumerate(plans):
        window = plans[i:i + H]
        cands = [(0.0, (), layout, prev)]
        for w_i, wplan in enumerate(window):
            mc = plan.mc_unit if (schedule_blind and w_i > 0) else wplan.mc_unit
            new = []
            for cum, tr, lay, prv in cands:
                cache = {}
                for e in EXPERT_IDS:
                    if e in cache:
                        fl = cache[e]
                    else:
                        fl = run_policy(e, wplan.view, lay, mc).layout
                        cache[e] = fl
                    mv = sum(1 for s in fl if lay.get(s) != fl[s])
                    sw = 1.0 if (prv is not None and e != prv) else 0.0
                    pc = model_fn(wplan.view, fl)
                    fc = (pc + bench.lambda_move * mv * mc
                          + bench.lambda_switch * sw * mc)
                    new.append((cum + fc, tr + (e,), fl, e))
            new.sort(key=lambda c: c[0])
            cands = new[:beam_width]
        best_e = cands[0][1][0]

        # realized accounting + per-expert realized costs (for RF)
        cache = {}
        real_costs = []
        for e in EXPERT_IDS:
            if e in cache:
                layout_e = cache[e]
            else:
                layout_e = run_policy(e, plan.view, layout, plan.mc_unit).layout
                cache[e] = layout_e
            mv = sum(1 for s in layout_e if layout.get(s) != layout_e[s])
            sw = 1.0 if (prev is not None and e != prev) else 0.0
            from evaluation.route_cost import total_route_cost
            real_costs.append(total_route_cost(plan.period_lines, layout_e,
                                               bench.xyz)
                              + bench.lambda_move * mv * plan.mc_unit
                              + bench.lambda_switch * sw * plan.mc_unit)
        # predicted ranking under the belief model (same incoming layout)
        pred_costs = []
        for e in EXPERT_IDS:
            fl = run_policy(e, plan.view, layout, plan.mc_unit).layout
            mv = sum(1 for s in fl if layout.get(s) != fl[s])
            pred_costs.append(model_fn(plan.view, fl)
                              + bench.lambda_move * mv * plan.mc_unit)
        rho = spearman(pred_costs, real_costs)
        tau = kendall(pred_costs, real_costs)
        best_real = min(range(len(EXPERT_IDS)), key=lambda k: real_costs[k])
        pred_rank_of_best = rankdata(pred_costs)[best_real]
        top1 = pred_rank_of_best == 1.0
        top2 = pred_rank_of_best <= 2.0
        rf_records.append((rho, tau, top1, top2))

        cost, layout, mv = bench._eval_expert(plan, best_e, layout, prev, None)
        total += cost
        traj.append(best_e)
        prev = best_e
    rhos = [r for r, *_ in rf_records if r == r]
    taus = [t for _, t, *_ in rf_records if t == t]
    return dict(total=total, traj=traj,
                rho=statistics.fmean(rhos) if rhos else float("nan"),
                tau=statistics.fmean(taus) if taus else float("nan"),
                top1=statistics.fmean([t1 for *_, t1, _ in rf_records]),
                top2=statistics.fmean([t2 for *_, _, t2 in rf_records]))


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
    p.add_argument("--seeds", type=int, nargs="+", default=[17, 37, 97, 117])
    p.add_argument("--smoke", action="store_true")
    p.add_argument("--beam", type=int, default=30)
    args = p.parse_args()

    log = Logger()
    log("=== run_r17_attribution.py (SPEC v1.5 §3.1) ===")
    cfg = yaml.safe_load(open(ROOT / "config" / "main_config.yaml"))
    ws = cfg["world_state"]
    if args.smoke:
        ws = dict(ws, n_skus=40, n_locations=20)
        args.seeds = args.seeds[:2]
        log("  --smoke: shrunk world, 2 seeds")

    cache_path = ROOT / "outputs" / "experiments" / "r17_cells.json"
    cache = json.loads(cache_path.read_text()) if cache_path.exists() else {}

    models = dict(MODEL_REGISTRY)
    HS = [1, 2, 3, 7]

    for seed in args.seeds:
        bench = build_bench(ws, seed)
        g = bench.run(seed_for_view=seed)          # greedy realized baseline (H=1 ex-post style)
        bfip = bench.beam_search(beam_width=args.beam, seed_for_view=seed)
        for mname, mfn in models.items():
            for H in HS:
                for blind in (False, True):
                    key = f"{seed}|{mname}|H{H}|{'blind' if blind else 'aware'}|{ws['n_skus']}"
                    if key in cache:
                        continue
                    r = rhc_rollout(bench, mfn, H=H, beam_width=8,
                                    seed_for_view=seed, schedule_blind=blind)
                    denom = g.myopic_total - bfip.total_cost
                    # capture only meaningful when headroom is material
                    if denom > 0.01 * g.myopic_total:
                        cap = (g.myopic_total - r["total"]) / denom
                    else:
                        cap = float("nan")
                    cache[key] = dict(total=r["total"], rho=r["rho"], tau=r["tau"],
                                      top1=r["top1"], top2=r["top2"], capture=cap)
                    log(f"seed{seed} {mname:12s} H={H} {'blind' if blind else 'aware'}: "
                        f"rho={r['rho']:+.2f} tau={r['tau']:+.2f} top1={r['top1']:.0%} "
                        f"capture={cap*100 if cap==cap else float('nan'):+6.1f}%")
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(cache))

    # aggregate: model x H -> mean rho / capture over seeds
    agg = {}
    for mname in models:
        for H in HS:
            for mode in ("aware", "blind"):
                cells = [cache[f"{s}|{mname}|H{H}|{mode}|{ws['n_skus']}"]
                         for s in args.seeds
                         if f"{s}|{mname}|H{H}|{mode}|{ws['n_skus']}" in cache]
                if not cells:
                    continue
                rhos = [c["rho"] for c in cells if c["rho"] == c["rho"]]
                caps = [c["capture"] for c in cells if c["capture"] == c["capture"]]
                agg[(mname, H, mode)] = dict(
                    rho=statistics.fmean(rhos) if rhos else float("nan"),
                    capture=statistics.fmean(caps) if caps else float("nan"),
                    top1=statistics.fmean(c["top1"] for c in cells))

    # RF -> capture scatter + model-H table
    fig, ax = plt.subplots(figsize=(7.5, 5))
    markers = {"L1_linear": "o", "L2_stopaware": "s", "L3_route": "^"}
    colors = {"aware": "tab:blue", "blind": "tab:red"}
    for mname, mk in markers.items():
        for mode in ("aware", "blind"):
            xs = [agg[(mname, H, mode)]["rho"] for H in HS
                  if (mname, H, mode) in agg]
            ys = [agg[(mname, H, mode)]["capture"] * 100 for H in HS
                  if (mname, H, mode) in agg]
            if not xs:
                continue
            ax.plot(xs, ys, mk + "-", color=colors[mode],
                    label=f"{mname} ({mode})")
            for H, x, y in zip([H for H in HS if (mname, H, mode) in agg], xs, ys):
                ax.annotate(f"H{H}", (x, y), textcoords="offset points",
                            xytext=(4, 3), fontsize=7)
    ax.set_xlabel("RankingFidelity (Spearman rho, predicted vs realized)")
    ax.set_ylabel("CaptureRate % (vs BFIP)")
    ax.set_title("RF -> Capture: internal model fidelity gates sequential value")
    ax.axhline(0, color="gray", lw=0.6)
    ax.legend()
    fig.tight_layout()
    figdir = ROOT / "outputs" / "figures"
    figdir.mkdir(parents=True, exist_ok=True)
    fig.savefig(figdir / "rf_capture.png", dpi=140)
    log("wrote outputs/figures/rf_capture.png")

    tbl = "\n".join(
        f"| {m} | {H} | {mode} | {d['rho']:+.2f} | {d['top1']:.0%} | {d['capture']*100 if d['capture']==d['capture'] else float('nan'):+.1f}% |"
        for (m, H, mode), d in sorted(agg.items()))
    out = ROOT / "outputs" / "experiments" / "r17_attribution.md"
    out.write_text(f"""# R17 — 归因实验:为什么 capture≈0(SPEC v1.5 §3.1)

**Date**: {datetime.now(timezone.utc).isoformat()} | seeds = {args.seeds} | RHC beam = 8 | BFIP beam = {args.beam} | world = {ws['n_skus']} SKU
**设计**: 固定 warehouse trajectory,仅换内部成本模型(L1 线性 / L2 stop-aware / L3 route 代理)× H ∈ {1,2,3,7};每级记 RankingFidelity(ρ/τ)+ Top-1 hit + CaptureRate(vs BFIP)

## 结果(model × H)

| model | H | schedule | Spearman ρ | Top-1 hit | CaptureRate |
|-------|---|-----------|-----------|-------------|
{tbl}

## RF → Capture 曲线
`outputs/figures/rf_capture.png`

## 归因判读(预声明框架)
- 若 ρ 随模型升级上升且 capture 同步上升 → **cost-model error 是绑定约束**
  (SPEC v1.5 核心假设:sequential opportunity 需要内部模型保持候选相对排序)
- 若 ρ 高但 capture 仍 ~0 → 绑定约束转向 **horizon insufficiency**(H 不够)
  或 forecast error;H 扫描行给出 horizon 维度
- 若 L3(与真实度量同构)capture 仍为 0 → 剩余差距 = forecast error +
  BFIP 的 clairvoyance 不可弥补部分
""")
    log(f"wrote outputs/experiments/r17_attribution.md")
    log("=== done ===")


if __name__ == "__main__":
    main()
