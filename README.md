# When Not to Reconfigure?

### Sequential warehouse reconfiguration under non-stationary demand and switching costs

`Purpose: DECISION SCIENCE` · `Maturity: RESEARCH` · `Evidence: PUBLIC REAL-WORLD DATA`

> Part of **TopPrism Decision Intelligence — Decision Science Research**.
>
> This repository is a research engine, not a production WMS or commercial slotting product.

## Why this exists

Dynamic warehouse slotting systems are usually designed to answer **how to improve a layout**. This project asks a different question:

> **When should a warehouse deliberately defer a locally attractive physical reconfiguration?**

A layout that looks better for the next demand period may still be a poor decision once relocation cost, future regime changes, forecast error and model error are considered.

The project studies how much of the full-information value of dynamic reconfiguration can actually be captured by deployable receding-horizon policies.

## What this project studies

A stateful online reconfiguration problem — **DWERP (Deferred Warehouse Reconfiguration Problem)** — formalized inside the **Metrical Task Systems / online optimization with switching costs** family, and stress-tested against six public real-world demand cohorts.

```text
World State S_t
     ↓
Candidate layout / routing experts
     ↓
Operating-cost estimate
+
Reconfiguration cost
     ↓
Sequential decision policy
     ↓
Layout L_t
     ↓
Execution / simulation
     ↓
State S_{t+1}
```

The repository also studies where real warehouse mechanics depart from a clean metric abstraction through capacity, exchange, batching and asymmetric operational effects.

## Evidence

### What is currently supported

- **6 public real-world demand datasets / 8 evaluation settings**: WEPA, CrossStacks, Instacart (top-10% / mid-10%), Favorita, M5 (sparse / dense), SLAPRP.
- **29 reproducible experiments** (`R01`–`R29`) under `scripts/run_r*.py`, with reports in `outputs/experiments/`.
- **Three self-audit passes** per major conclusion: fact check → inference check → method check. Withdrawn or downgraded claims are preserved in `outputs/experiments/REVIEW_*.md`.
- **A 16-page, ~5,600-word, 25-reference manuscript** (`paper/main.pdf`) with 5 figures, currently in academic-closure state (v1.5.5) ahead of submission.

### What this evidence does **not** prove

- It does not establish that the approximate full-information planner is globally exact for all large instances. Small-instance exact certification is done on a limited grid (`R18`).
- It does not establish that all real warehouses exhibit zero deployable reconfiguration value. The empirical deployment-gap collapse (gap = 0.00% across the eight tested settings) is an observed result, not a universality proof.
- Public retail-demand datasets are not equivalent to full production WMS data with real geometry, equipment calibration and operational constraints.
- A seventh dataset (**Footwear 2025**) is referenced but could not be downloaded in the test environment; it is listed as future work (`R30`), not as completed evidence.
- The current project is not a production warehouse execution system.

## Contribution map

The currently published contributions are **three** (see `PROGRESS_v1.5.5.md` §2):

1. **Structural opportunity exists.** DWERP is formalized and stress-tested through seven T-gates (`T0` diversity, `T1a` existence, `T1b` prevalence, `T2` sensitivity, `T1.5` move vs switch, `T3` information boundary, `T4` trap phase diagram). `R18` shows beam-30 equals exact on 4/4 seeds; seed 17 reaches `TrapScore 26.3`.

2. **The deployment paradox.** Full-information reconfiguration opportunities exist, but their deployable value collapses under imperfect forecasts, imperfect internal cost models and realistic demand structure. Across the tested selector families, a fixed conservative policy (`S1 FixedBest`) remained a strong baseline against learned (`S3 XGBoost`, `S4 MLP`) and zero-shot LLM (`S5`) selectors.

3. **Boundary and mechanism.** Across six public datasets / eight evaluation settings, the empirical deployment-gap collapses to 0.00%. A clean MTS abstraction is systematically violated by real warehouse mechanics (asymmetric moves, capacity, batching, exchange chains); the gap between the theoretical metric `d_m(L, L')` and the implementation cost `d_w(L, L')` is itself a finding.

## Where it fits at TopPrism

This project is part of **TopPrism Decision Science Research**. It explores reusable principles for stateful business decisions with transition costs.

Related TopPrism work:

- `visit-scheduling-optimizer` — periodic field-sales planning under recurring constraints.
- `cultivating-ml-agent` — project-driven capability accumulation for ML agents.

## Status (v1.5.5)

**Academic-closure state.** The 29-run experiment set, three self-audit rounds, six public datasets and v4 manuscript are in place. Remaining items before first submission: `R30` Footwear data acquisition attempt, a multi-seed CI on the main results, the cover letter and the supplementary paired per-instance comparison.

Productization would require additional validation with real warehouse geometry, operational cost calibration, production constraints and execution integration.

## Repository structure

```text
world_state/     state representation and public-data adapters
or_experts/      candidate optimization / routing experts
simulation/      execution and replay environment
features/        decision features
execution/       bounded execution / gateway logic
evaluation/      cost and policy evaluation
scripts/         reproducible experiment runners
outputs/         experiment reports and self-audit records
paper/           manuscript source and PDF
config/          experiment and cost configuration
```

## Reproducibility

The repository keeps experiment outputs and self-audit records in version control so that positive findings, negative findings and withdrawn claims remain auditable.

Start from the latest progress document:

```bash
cat PROGRESS_v1.5.5.md
cat SPEC_UPDATE_v1.5.md
```

Then run the experiment script associated with the finding you want to reproduce under `scripts/`.

## Research discipline

A distinctive project rule is that major conclusions are reviewed through three separate passes:

1. **Fact check** — verify results from code and artifacts rather than memory.
2. **Inference check** — verify that the stated conclusion is actually supported by the evidence.
3. **Method check** — record what the experiment taught us about the research process itself.

Withdrawn or downgraded conclusions are kept in the experiment history rather than silently rewritten.

## Paper

See `paper/main.pdf` and `paper/main.tex`.

The current manuscript centers on the question:

> **When should a warehouse defer locally optimal physical reconfiguration under non-stationary demand, and how much of the full-information opportunity can deployable policies capture?**

## Boundaries & limitations

- `empirical deployment-gap collapse` is observed on the eight tested settings, not proved as a universal theorem.
- `FI-Beam-30` remains an approximation; small-instance exact certification is reported only for the limited `R18` grid.
- `d_m ≠ d_w` is acknowledged as a finding, not as a bug in the abstraction.
- The selector family comparison is reported on the tested datasets only; selector performance on a different deployment context has not been validated.
- The Footwear 2025 dataset is referenced but not included as completed evidence.
- Public retail-demand datasets are not production WMS data; conclusions do not transfer to live warehouse operations without additional validation.

## License

MIT. See `LICENSE`.
