"""
world_state/instacart_adapter.py — Spec §4.2 Track B: real baskets + synthetic rack.

Source: Kaggle mirror psparks/instacart-market-basket-analysis (CC0).
3.4M orders / 32.4M order-product rows / 49,689 products.

Design decisions (explicit, per review discipline — do not change silently):
  1. USER-LEVEL split, not row-level: Instacart has NO absolute timestamps
     (only dow/hour/days_since_prior), so day-splitting is impossible. We split
     by USER (train users vs held-out users), which is STRICTER — one user's
     baskets can never appear on both sides (no identity leakage).
  2. SKU subset = top-N by basket frequency (default 120, matching the
     60-location rack capacity). This mirrors an FMCG DC's high-velocity subset;
     the long tail (49k SKUs) is out of scope by construction.
  3. quantity = 1 for every line (Instacart rows carry no counts).
  4. Timestamps are SYNTHETIC (dow/hour of day are real, dates are generated);
     basket CONTENT is OBSERVED. Net lineage for orders/order_lines rows:
     DERIVED (observed content + synthetic time), per spec §4.1 semi-synthetic
     discipline — flagged, not hidden.
  5. Aisle (135) is the category dimension; category concentration is whatever
     the real data says (estimated, not set, in R07).
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd

from .schemas import (
    Order, OrderLine, SourceType, StorageClass,
)


def load_instacart(
    raw_dir,
    n_users: int = 3000,
    top_n_skus: int = 120,
    user_split_frac: float = 0.7,
    seed: int = 42,
) -> Dict:
    """Sample complete users, keep their prior+train orders, map to canonical rows.

    Returns dict with:
      train_orders/train_lines   — users' baskets for slotting (affinity, freq)
      test_orders/test_lines     — held-out users' baskets for evaluation
      sku_ids, sku_category      — the top-N SKU universe
      estimated_concentration    — observed share of same-aisle co-occurrence
    """
    rng = random.Random(seed)
    raw_dir = Path(raw_dir)

    orders_df = pd.read_csv(raw_dir / "orders.csv",
                            dtype={"order_id": int, "user_id": int, "eval_set": str,
                                   "order_number": int, "order_dow": int,
                                   "order_hour_of_day": int})
    products_df = pd.read_csv(raw_dir / "products.csv",
                              dtype={"product_id": int, "aisle_id": int, "department_id": int})

    # --- sample complete users (deterministic) ------------------------------
    all_users = orders_df["user_id"].drop_duplicates().to_numpy()
    rng.shuffle(all_users)
    picked = all_users[:n_users]
    sub = orders_df[orders_df["user_id"].isin(set(picked))]

    # --- split by USER (train/eval), never by row ---------------------------
    rng.shuffle(picked)
    n_train_users = int(len(picked) * user_split_frac)
    train_users = set(picked[:n_train_users])

    # --- load order-product rows only for sampled orders --------------------
    order_to_user = dict(zip(sub["order_id"], sub["user_id"]))
    wanted = set(order_to_user)
    usecols = ["order_id", "product_id", "add_to_cart_order"]
    op_chunks = []
    for f in ("order_products__prior.csv", "order_products__train.csv"):
        for chunk in pd.read_csv(raw_dir / f, usecols=usecols, chunksize=5_000_000,
                                 dtype={"order_id": int, "product_id": int,
                                        "add_to_cart_order": int}):
            op_chunks.append(chunk[chunk["order_id"].isin(wanted)])
    op = pd.concat(op_chunks, ignore_index=True)

    # --- top-N SKUs by basket frequency (train side only: no eval leakage) --
    train_mask = sub["user_id"].isin(train_users)
    train_order_ids = set(sub.loc[train_mask, "order_id"])
    op_train = op[op["order_id"].isin(train_order_ids)]
    freq = op_train["product_id"].value_counts()
    top_skus = freq.head(top_n_skus).index.tolist()

    sku_ids = [f"P{int(p):05d}" for p in top_skus]
    pid_to_sku = {int(p): f"P{int(p):05d}" for p in top_skus}
    aisle = dict(zip(products_df["product_id"], products_df["aisle_id"]))
    sku_category = {pid_to_sku[int(p)]: f"AISLE{int(a):03d}"
                    for p, a in zip(products_df["product_id"], products_df["aisle_id"])
                    if int(p) in pid_to_sku}

    # --- canonical Order/OrderLine rows --------------------------------------
    anchor = datetime(2025, 1, 1, tzinfo=timezone.utc)
    meta = sub.set_index("order_id")

    def build(order_ids: set) -> Tuple[List[Order], List[OrderLine]]:
        orders, lines = [], []
        rows = op[op["order_id"].isin(order_ids) & op["product_id"].isin(pid_to_sku)]
        grouped = rows.groupby("order_id", sort=True)
        for oid, group in grouped:
            om = meta.loc[oid]
            t = anchor + timedelta(
                days=int(rng.randrange(14)), hours=float(om["order_hour_of_day"]))
            if t.tzinfo is None:
                t = t.replace(tzinfo=timezone.utc)
            oid_str = f"O{int(oid):08d}"
            orders.append(Order(
                order_id=oid_str, order_time=t, known_at_time=t,
                channel="b2c",
                cutoff=t + timedelta(hours=4),
                priority=0, wave_id=None,
                source_type=SourceType.DERIVED,
            ))
            for r in group.itertuples(index=False):
                lines.append(OrderLine(
                    order_id=oid_str, sku_id=pid_to_sku[int(r.product_id)],
                    quantity=1.0, uom="each",
                    pick_sequence=int(r.add_to_cart_order),
                    source_type=SourceType.DERIVED,
                ))
        return orders, lines

    tr_orders, tr_lines = build(train_order_ids)
    eval_order_ids = set(sub.loc[~train_mask, "order_id"]) & set(op["order_id"].unique())
    ev_orders, ev_lines = build(eval_order_ids)

    # --- observed same-aisle co-occurrence (for comparison vs synthetic 0.7) -
    from collections import defaultdict
    lines_by_order = defaultdict(list)
    for ln in tr_lines:
        lines_by_order[ln.order_id].append(ln.sku_id)
    same_pairs = 0
    total_pairs = 0
    for oid, skus in lines_by_order.items():
        aisles = [sku_category.get(s, "?") for s in skus]
        for i in range(len(aisles)):
            for j in range(i + 1, len(aisles)):
                total_pairs += 1
                if aisles[i] == aisles[j]:
                    same_pairs += 1
    concentration = same_pairs / total_pairs if total_pairs else 0.0

    return {
        "train_orders": tr_orders, "train_lines": tr_lines,
        "test_orders": ev_orders, "test_lines": ev_lines,
        "sku_ids": sku_ids, "sku_category": sku_category,
        "estimated_concentration": concentration,
        "n_train_users": n_train_users,
        "n_eval_users": len(picked) - n_train_users,
    }
