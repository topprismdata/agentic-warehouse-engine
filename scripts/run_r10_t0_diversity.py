"""
scripts/run_r10_t0_diversity.py
— R10: T0 Expert Diversity under the v1.2 SEQUENTIAL protocol (SPEC v1.2 §3).

Runs the 28-day regime sequence x seeds; at each of the 7 evaluated phases
(warm-up excluded) every expert is scored (pick + λm*moves). Reports:
  - per-phase myopic winner and margins
  - winner distribution (dominance test: no single expert may own >=80%)
  - alignment of switches with regime phases
  - always-X cumulative totals (Fixed-Best candidates) + myopic total
Go (T0): top-expert win share < 80% AND >= 3 distinct winners.
No-Go: one expert >= 95%. 80-95% = weak/borderline — escalate to T1 before
spending on selectors.

Output: outputs/experiments/r10_t0_diversity.md
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
from or_experts.policies import EXPERT_IDS


class Logger:
    def __init__(self):
        self._t0 = time.time()

    def __call__(self, msg):
        print(f"[{time.time()-self._t0:7.2f}s][INFO] {msg}", flush=True)

    def info(self, msg):
        self(msg)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--seeds", type=int, nargs="+", default=[7, 17, 27])
    p.add_argument("--smoke", action="store_true")
    args = p.parse_args()

    log = Logger()
    log("=== run_r10_t0_diversity.py (v1.2 T0) ===")
    cfg = yaml.safe_load(open(ROOT / "config" / "main_config.yaml"))
    ws = cfg["world_state"]
    if args.smoke:
        ws = dict(ws, n_skus=40, n_locations=20)
        args.seeds = args.seeds[:2]
        log("  --smoke: shrunk world")

    all_winners, all_margins, per_seed_totals = [], [], {}
    violations = []
    phase_winners = Counter()
    rows = []

    for seed in args.seeds:
        rng = random.Random(seed)
        sku_master = sampler.make_sku_master(ws["n_skus"], rng)
        sku_ids = [s.sku_id for s in sku_master]
        sku_cat = {s.sku_id: s.category_id for s in sku_master}
        locations, xyz = sampler.make_locations(ws["n_locations"], rng)
        anchor = datetime(2025, 1, 1, tzinfo=timezone.utc)

        seq = build_sequence(sku_ids)
        orders, lines = generate_stream(sku_ids, sku_cat, seq, rng, anchor,
                                        orders_per_day_mean=ws["orders_per_day_mean"],
                                        orders_per_day_std=ws["orders_per_day_std"])
        log(f"seed {seed}: stream {len(orders)} orders / {len(lines)} lines / "
            f"{len(seq)} days / {len(set(dp.phase for dp in seq))} phases")

        bench = SequentialBenchmark(sku_master, locations, xyz, orders, lines,
                                    seq, anchor, mc_unit_ratio=0.0005)
        res = bench.run(seed_for_view=seed, log=None)
        violations.extend(res.violations)

        winners = [pr.myopic_winner for pr in res.periods]
        all_winners.extend(winners)
        for pr in res.periods:
            phase_winners[(pr.phase, pr.myopic_winner)] += 1
            sorted_c = sorted(pr.costs.items(), key=lambda kv: kv[1])
            margin = (sorted_c[1][1] - sorted_c[0][1]) / max(sorted_c[1][1], 1e-9)
            all_margins.append((pr.phase, margin))
        per_seed_totals[seed] = (res.total_by_expert_alone, res.myopic_total,
                                 res.fixed_best, res.fixed_best_total)
        log(f"  winners: {winners} | fixed-best={res.fixed_best} "
            f"({res.fixed_best_total:.0f}) myopic={res.myopic_total:.0f}")
        for pr in res.periods:
            ref = max(pr.costs.values())
            rows.append((seed, pr.t, pr.phase, pr.myopic_winner,
                         {e.split('_')[0]: round(pr.costs[e] / ref, 3) for e in EXPERT_IDS},
                         pr.moves[pr.myopic_winner]))

    # ---- T0 statistics ---------------------------------------------------------
    n_periods = len(all_winners)
    dist = Counter(all_winners)
    top, top_n = dist.most_common(1)[0]
    share = top_n / n_periods
    n_distinct = len(dist)

    # phase alignment: does the winner differ across regimes?
    by_phase = {}
    for (phase, w), c in phase_winners.items():
        by_phase.setdefault(phase, Counter())[w] += c
    aligned = sum(1 for ph, c in by_phase.items() if c.most_common(1)[0][1] >= 2) \
        if per_seed_totals else 0

    go = share < 0.80 and n_distinct >= 3
    verdict = "GO" if go else ("NO-GO" if share >= 0.95 else "BORDERLINE")

    log(f"T0 stats: periods={n_periods} top={top} share={share:.0%} "
        f"distinct={n_distinct} violations={len(violations)}")
    log(f"phase winners: { {ph: c.most_common(1)[0][0] for ph, c in by_phase.items()} }")
    log(f"T0 VERDICT: {verdict}")

    # validate (non-vacuous) on one seed's final state
    from world_state import validate_pipeline
    seed0 = args.seeds[0]
    rng0 = random.Random(seed0)
    sm0 = sampler.make_sku_master(ws["n_skus"], rng0)
    locs0, xyz0 = sampler.make_locations(ws["n_locations"], rng0)
    ids0 = [s.sku_id for s in sm0]
    cat0 = {s.sku_id: s.category_id for s in sm0}
    anchor = datetime(2025, 1, 1, tzinfo=timezone.utc)
    seq0 = build_sequence(ids0)
    o0, l0 = generate_stream(ids0, cat0, seq0, rng0, anchor)
    world = {"sku_master": sm0, "orders": o0, "order_lines": l0,
             "forecast_daily": [], "locations": locs0, "inventory_snapshot": [],
             "slot_assignment": [type("A", (), {})()], "constraints": [],
             "decision_plan": []}
    # use a real SlotAssignment row set from the bench? keep it simple: reuse sampler constraints
    from world_state.schemas import SlotAssignment, SourceType
    bench0 = SequentialBenchmark(sm0, locs0, xyz0, o0, l0, seq0, anchor)
    res0 = bench0.run(seed_for_view=seed0)
    layout0 = res0.periods[-1].layout_after
    world["slot_assignment"] = [SlotAssignment(timestamp=anchor, sku_id=s, location_id=l,
                                               assigned_capacity=1.0, reason="R10",
                                               decision_id="DP-R10",
                                               source_type=SourceType.SYNTHETIC)
                                for s, l in layout0.items()]
    world["constraints"] = sampler.make_constraints(locs0)
    report = validate_pipeline(world)

    # write report
    detail = "\n".join(
        f"| {sd} | {t} | {ph} | {w} | {mv} | {costs} |"
        for sd, t, ph, w, costs, mv in rows)
    phase_tbl = "\n".join(
        f"| {ph} | {c.most_common(1)[0][0]} | {dict(c)} |"
        for ph, c in sorted(by_phase.items()))
    margins_by_phase = {}
    for ph, m in all_margins:
        margins_by_phase.setdefault(ph, []).append(m)
    margin_tbl = "\n".join(
        f"| {ph} | {statistics.fmean(v)*100:.1f}% |"
        for ph, v in sorted(margins_by_phase.items()))

    out = ROOT / "outputs" / "experiments" / "r10_t0_diversity.md"
    out.write_text(f"""# R10 — T0 Expert Diversity(v1.2 序列协议,28 天 / 8 相位,warm-up 除外 7 期)

**Date**: {datetime.now(timezone.utc).isoformat()} | seeds = {args.seeds} | world = {ws['n_skus']} SKU / {ws['n_locations']} loc
**Cost**: per-period pick(L0 route)+ λm·moves(λs=0,SPEC §9 声明)| myopic path 评估

## Per-period detail(cost 相对当期最差 expert 归一)

| seed | t | phase | myopic winner | #moves | costs by expert |
|------|---|-------|---------------|--------|-----------------|
{detail}

## Winner switching(T0 核心)

- 总期次 = {n_periods}(={len(args.seeds)} seeds × 7 phases)
- winner 分布: {dict(dist)}
- **top expert share = {top} {top_n}/{n_periods} = {share:.0%}**(阈值:<80% Go,≥95% No-Go)
- distinct winners = {n_distinct}(要求 ≥3)

## Phase → winner 对齐

| phase | modal winner | 分布 |
|-------|--------------|------|
{phase_tbl}

## 各相位 winner 与第二名差距(切换信号强度)

| phase | mean margin |
|-------|-------------|
{margin_tbl}

## Always-X / Fixed-Best / Myopic(每 seed)

{chr(10).join(f"- seed {sd}: fixed-best={fb}({fbt:.0f}) myopic={my:.0f} always-E1={ta.get('E1_StaticABC',0):.0f} always-E4={ta.get('E4_Forecast',0):.0f}" for sd, (ta, my, fb, fbt) in per_seed_totals.items())}

## Gates
- capacity violations across ALL expert-periods: **{len(violations)}** {'(PASS)' if not violations else '(FAIL)'}
- validate_pipeline (non-vacuous): hard-fails = **{len(report.hard_failures)}**
- T0 verdict: **{verdict}**(share={share:.0%}, distinct={n_distinct})

## 判读
- {'**GO**:expert 最优性随相位切换且可解释 → 继续 T1(Myopic vs Dynamic Oracle)。' if verdict=='GO' else ('**NO-GO**:单一 expert 统治,selector 研究价值不足 → 停,报告。' if verdict=='NO-GO' else '**BORDERLINE**:80–95% 统治 → 先跑 T1 看 sequential 是否有增量价值再定。')}
- 本 T0 在合成平台(构造性 regime);T 关通过后按 v1.2 §12 切 WEPA/SLAPStack 复核。
""")
    log(f"wrote outputs/experiments/r10_t0_diversity.md")
    sys.exit(0 if go else (3 if verdict == "NO-GO" else 1))


if __name__ == "__main__":
    main()
