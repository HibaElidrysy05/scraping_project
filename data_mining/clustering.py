"""
Price-based product clustering (P2) — KMeans + DBSCAN on multidimensional features.

Features: prix_mad, marque_encoded (mean price), etat_encoded (ordinal).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN, KMeans
from sklearn.metrics import silhouette_score

from data_mining.feature_encoding import build_scaled_matrix

# K plafonné à [3, 5] : aligné sur le cahier des charges (bas / milieu / haut de gamme)
K_RANGE = range(3, 6)
K_RANGE_TESTED = [3, 4, 5]
K_CAP_REASON = "Plafond métier: 3 à 5 segments de prix (bas/milieu/haut)"
KMEANS_RANDOM_STATE = 42
DBSCAN_EPS = 0.5
DBSCAN_MIN_SAMPLES = 3


def _silhouette_interpretation(score: float) -> str:
    if score >= 0.71:
        return "excellent"
    if score >= 0.51:
        return "raisonnable"
    if score >= 0.26:
        return "faible"
    return "non fiable"


LABELS_BY_K: dict[int, list[str]] = {
    3: ["bas de gamme", "milieu de gamme", "haut de gamme"],
    4: ["entrée de gamme", "bas de gamme", "milieu de gamme", "haut de gamme"],
    5: [
        "entrée de gamme",
        "bas de gamme",
        "milieu de gamme",
        "haut de gamme",
        "premium",
    ],
}


def _assign_price_labels(
    labels: np.ndarray,
    prices: pd.Series,
    k: int,
) -> dict[int, str]:
    """
    Map KMeans cluster ids to K distinct human labels by ascending mean prix_mad.

    Label vocabulary depends on K (3/4/5 segments). Noise (-1) → bruit.
    """
    unique = sorted(set(labels))
    if unique == [-1] or (len(unique) == 1 and unique[0] == -1):
        return {-1: "bruit"}

    label_list = LABELS_BY_K[k]
    cluster_means: list[tuple[int, float]] = []
    for cid in unique:
        if cid == -1:
            continue
        mask = labels == cid
        cluster_means.append((cid, float(prices.iloc[mask].mean())))

    cluster_means.sort(key=lambda x: x[1])
    mapping: dict[int, str] = {}
    for rank, (cid, _) in enumerate(cluster_means):
        mapping[cid] = label_list[rank]

    if -1 in unique:
        mapping[-1] = "bruit"

    return mapping


def _build_cluster_summary(work: pd.DataFrame) -> list[dict]:
    """Per-cluster price thresholds and shares, sorted by price_mean ascending."""
    total = len(work)
    if total == 0:
        return []

    summary: list[dict] = []
    for cluster_id in sorted(work["cluster_kmeans"].unique()):
        mask = work["cluster_kmeans"] == cluster_id
        subset = work.loc[mask, "prix_mad"]
        count = int(mask.sum())
        price_mean = float(subset.mean())

        summary.append(
            {
                "label": str(work.loc[mask, "cluster_label"].iloc[0]),
                "cluster_id": int(cluster_id),
                "count": count,
                "price_min": round(float(subset.min()), 2),
                "price_max": round(float(subset.max()), 2),
                "price_median": round(float(subset.median()), 2),
                "price_mean": round(price_mean, 2),
                "share_pct": round(count / total * 100, 1),
            }
        )

    summary.sort(key=lambda row: row["price_mean"])
    return summary


def _cluster_counts_from_summary(cluster_summary: list[dict]) -> dict[str, int]:
    return {row["label"]: row["count"] for row in cluster_summary}


def get_elbow_data(df: pd.DataFrame) -> list[dict]:
    """
    Elbow + silhouette metrics for K in {3, 4, 5} (for P4 plotting).

    Plage restreinte pour rester défendable métier (segments bas/milieu/haut)
    plutôt que K=6..8 difficiles à interpréter devant un jury.

    Uses 3-feature matrix: prix_mad + marque_encoded + etat_encoded.
    """
    x_scaled, _ = build_scaled_matrix(df)
    elbow_data = []

    for k in K_RANGE:
        kmeans = KMeans(n_clusters=k, n_init=10, random_state=KMEANS_RANDOM_STATE)
        pred = kmeans.fit_predict(x_scaled)
        sil = silhouette_score(x_scaled, pred)
        elbow_data.append(
            {
                "k": int(k),
                "inertia": round(float(kmeans.inertia_), 2),
                "silhouette": round(float(sil), 2),
            }
        )

    return elbow_data


def _empty_cluster_warnings(cluster_counts: dict[str, int]) -> list[str]:
    """Warn when a human-readable segment has zero products."""
    warnings = []
    for label, count in cluster_counts.items():
        if count == 0:
            warnings.append(
                f"Cluster '{label}' est vide — envisager K plus petit pour cet échantillon"
            )
    return warnings


def run_clustering(df: pd.DataFrame) -> dict:
    """
    Run KMeans (optimal K via silhouette, K in {3, 4, 5}) and DBSCAN on encoded features.

    Parameters
    ----------
    df : pd.DataFrame
        Cleaned data with prix_mad, marque, etat, title.

    Returns
    -------
    dict
        optimal_k, elbow_data, silhouettes, labels, cluster_counts, rows, warnings.
    """
    work = df.copy()
    x_scaled, _ = build_scaled_matrix(work)
    prices = work["prix_mad"]

    # Optimal K = meilleure silhouette dans la plage métier [3, 5]
    elbow_data = get_elbow_data(work)
    optimal_k = max(elbow_data, key=lambda row: row["silhouette"])["k"]
    k_forced = False

    kmeans = KMeans(
        n_clusters=optimal_k,
        n_init=10,
        random_state=KMEANS_RANDOM_STATE,
    )
    work["cluster_kmeans"] = kmeans.fit_predict(x_scaled)

    kmeans_label_map = _assign_price_labels(
        work["cluster_kmeans"].values,
        prices,
        optimal_k,
    )
    work["cluster_label"] = work["cluster_kmeans"].map(kmeans_label_map)

    cluster_summary = _build_cluster_summary(work)
    cluster_counts = _cluster_counts_from_summary(cluster_summary)

    kmeans_silhouette = round(
        float(silhouette_score(x_scaled, work["cluster_kmeans"])),
        2,
    )
    silhouette_interpretation = _silhouette_interpretation(kmeans_silhouette)

    dbscan = DBSCAN(eps=DBSCAN_EPS, min_samples=DBSCAN_MIN_SAMPLES)
    work["cluster_dbscan"] = dbscan.fit_predict(x_scaled)

    dbscan_labels = work["cluster_dbscan"].values
    non_noise = dbscan_labels != -1
    dbscan_warning = None

    if non_noise.sum() > 1 and len(set(dbscan_labels[non_noise])) > 1:
        dbscan_silhouette = round(
            float(
                silhouette_score(
                    x_scaled[non_noise],
                    dbscan_labels[non_noise],
                )
            ),
            2,
        )
    else:
        dbscan_silhouette = -1.0

    if dbscan_silhouette == -1.0 or (non_noise.sum() == 0):
        dbscan_warning = (
            "DBSCAN produced no valid clusters on this dataset — "
            "not reliable for comparison"
        )

    if dbscan_silhouette < 0:
        best_algorithm = "KMeans"
    elif kmeans_silhouette >= dbscan_silhouette:
        best_algorithm = "KMeans"
    else:
        best_algorithm = "DBSCAN"

    cluster_warnings = _empty_cluster_warnings(cluster_counts)

    rows = [
        {
            "title": str(row["title"]),
            "prix_mad": round(float(row["prix_mad"]), 2),
            "cluster_kmeans": int(row["cluster_kmeans"]),
            "cluster_label": str(row["cluster_label"]),
            "cluster_dbscan": int(row["cluster_dbscan"]),
        }
        for _, row in work.iterrows()
    ]

    return {
        "optimal_k": int(optimal_k),
        "k_forced": k_forced,
        "k_range_tested": list(K_RANGE_TESTED),
        "k_cap_reason": K_CAP_REASON,
        "elbow_data": elbow_data,
        "kmeans_silhouette": kmeans_silhouette,
        "silhouette_interpretation": silhouette_interpretation,
        "dbscan_silhouette": dbscan_silhouette,
        "dbscan_warning": dbscan_warning,
        "cluster_warnings": cluster_warnings,
        "best_algorithm": best_algorithm,
        "cluster_counts": cluster_counts,
        "cluster_summary": cluster_summary,
        "rows": rows,
    }


if __name__ == "__main__":
    from data_mining.mock_data import get_mock_data
    from data_mining.preprocessing import clean_data

    cleaned = clean_data(get_mock_data())
    clustering_result = run_clustering(cleaned)

    print("Optimal K :", clustering_result["optimal_k"])
    print("K range   :", clustering_result["k_range_tested"])
    print("K forced  :", clustering_result["k_forced"])
    print("K cap     :", clustering_result["k_cap_reason"])
    print("Best algorithm :", clustering_result["best_algorithm"])
    print("KMeans silhouette :", clustering_result["kmeans_silhouette"])
    print("Interpretation :", clustering_result["silhouette_interpretation"])
    print("DBSCAN warning :", clustering_result["dbscan_warning"])
    print("Cluster counts :", clustering_result["cluster_counts"])
    print("Distinct labels:", len(clustering_result["cluster_counts"]))
    for row in clustering_result["cluster_summary"]:
        print(
            f"  {row['label']:20} | n={row['count']:3} | {row['share_pct']:5.1f}% | "
            f"med={row['price_median']:>10.2f} MAD"
        )
