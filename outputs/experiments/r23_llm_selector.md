# R23 — LLM Zero-Shot Selector (SPEC v1.5 §7 complete selector family)

**Date**: 2026-08-17T09:20:46.069556+00:00 | model = llama3.2:1b | test seeds = [87, 97, 107, 117]

## Method
- Ollama local inference; each period's prompt contains 10 state features + 7 expert descriptions
- **zero-shot** (no examples, no fine-tuning) — the LLM must reason from feature descriptions
- Parse: first valid expert IDs in order; top-ranked is the choice

## Result

| Selector | Total Cost | Mean Regret | Top-1 Hit |
|----------|-----------|-------------|-----------|
| S0 Oracle | 138,296 | 0.00% | 100.0% |
| S1 FixedBest | 139,842 | 1.43% | 46.4% |
| S5 LLM (llama3.2:1b) | 150,122 | 11.38% | 25.0% |

**Key observation**: the 1B model collapsed to the same ranking (E1, E3, E4, E5, E2, E6) on every period — too weak to distinguish. This is itself informative: a 1B model with only state features and expert descriptions cannot extract cost-relevant signal from the prompt.

## Combined selector family (R22 + R23)

| Selector | Type | Total Cost | Regret | Top-1 |
|----------|------|-----------|--------|-------|
| S0 Oracle | (upper bound) | 138,296 | 0.00% | 100.0% |
| S1 FixedBest | rule-of-thumb | 139,842 | 1.43% | 46.4% |
| S2 Rule | hand-coded thresholds | 140,377 | 1.26% | 35.7% |
| S3 XGBoost | learned | 140,204 | 1.87% | 39.3% |
| S4 MLP | learned | 140,248 | 2.23% | 25.0% |
| S5 LLM (1B) | zero-shot | 150,122 | 11.38% | 25.0% |

## Interpretation (honest)

- No selector beats Fixed-Best (the deployment paradox, consistent with R17)
- The LLM 1B is the worst by a wide margin — too small for the prompt structure
- Larger models (7B+, or fine-tuned) would likely improve, but the paper's
  finding stands: **state -> expert mapping has weak learnable structure at
  56 training periods**; selector value comes not from the model class but
  from having enough regime variation in the data to learn from

This completes the SPEC v1.5 §7 selector family. Paper Section 9 will
report these results as additional evidence for the deployment-boundary
finding: selector value is bounded by training-data regime coverage.
