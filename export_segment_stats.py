"""
Paste this into your clustering notebook (or import it) and run it
BEFORE the cell that applies StandardScaler to full_clustering_df.
That cell overwrites CostValue/Frequency/Recency with scaled values,
so stats exported afterwards would be wrong.

It exports ONLY segment-level aggregates, no Customer ID.
Segments smaller than MIN_SIZE are suppressed to avoid exposing individuals.
"""
import json
import pandas as pd

MIN_SIZE = 20


def build_segment_stats(full_df: pd.DataFrame, tx_df: pd.DataFrame, top_n: int = 5) -> dict:
    labelled = tx_df.merge(
        full_df[["Customer ID", "Cluster Label"]], on="Customer ID", how="inner"
    )
    stats = {}
    for label, g in full_df.groupby("Cluster Label"):
        if len(g) < MIN_SIZE:
            stats[label] = {"suppressed": True, "reason": f"fewer than {MIN_SIZE} customers"}
            continue
        seg_tx = labelled[labelled["Cluster Label"] == label]
        top_products = (
            seg_tx.groupby("Description")["Quantity"].sum()
            .sort_values(ascending=False).head(top_n).index.tolist()
        )
        top_countries = (
            seg_tx.drop_duplicates("Customer ID")["Country"]
            .value_counts(normalize=True).head(3).round(2).to_dict()
        )
        stats[label] = {
            "n_customers": int(len(g)),
            "share_of_customers": round(len(g) / len(full_df), 3),
            "median_recency_days": float(g["Recency"].median()),
            "median_frequency_orders": float(g["Frequency"].median()),
            "median_spend_gbp": round(float(g["CostValue"].median()), 2),
            "top_products": top_products,
            "top_country_share": top_countries,
        }
    return stats


# --- usage in the notebook ---
# stats = build_segment_stats(full_clustering_df, copy_df)
# with open("segment_stats.json", "w") as f:
#     json.dump(stats, f, indent=2)
