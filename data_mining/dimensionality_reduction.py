"""
PCA dimensionality reduction for P2 visualization (P4 scatter plots).

Uses prix_mad + marque_encoded + etat_encoded (+ optional if_score, lof_score).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

from data_mining.feature_encoding import add_encoded_features

_OPTIONAL_FEATURES = ("if_score", "lof_score")
_CENTROID_LABELS = ("bas de gamme", "milieu de gamme", "haut de gamme")


def _to_float(value: float) -> float:
    return round(float(value), 4)


def _prepare_feature_matrix(df: pd.DataFrame) -> tuple[np.ndarray, list[str]]:
    """3 core features + optional anomaly scores; returns scaled matrix."""
    work = add_encoded_features(df)
    columns = ["prix_mad", "marque_encoded", "etat_encoded"]
    for col in _OPTIONAL_FEATURES:
        if col in work.columns:
            columns.append(col)

    scaler = StandardScaler()
    x_scaled = scaler.fit_transform(work[columns].values)
    return x_scaled, columns


def _cluster_labels_from_result(
    df: pd.DataFrame,
    cluster_result: dict,
) -> list[str]:
    """Align cluster_label with df rows (same order or merge on title)."""
    rows = cluster_result.get("rows", [])
    if len(rows) == len(df):
        return [str(r["cluster_label"]) for r in rows]

    label_map = {str(r["title"]): str(r["cluster_label"]) for r in rows}
    return [label_map.get(str(title), "inconnu") for title in df["title"]]


def _components_for_80_percent(cumulative: np.ndarray) -> int:
    for i, cum in enumerate(cumulative, start=1):
        if cum >= 0.80:
            return int(i)
    return int(len(cumulative))


def run_pca(df: pd.DataFrame, cluster_result: dict) -> dict:
    """
    Run PCA on encoded features, return 2D points for P4.

    Parameters
    ----------
    df : pd.DataFrame
        Cleaned data from preprocessing.clean_data.
    cluster_result : dict
        Output of clustering.run_clustering (must include "rows").

    Returns
    -------
    dict
        Variance explained, 80% threshold, 2D points, centroids, pca_note.
    """
    x_scaled, feature_names = _prepare_feature_matrix(df)
    n_samples, n_features = x_scaled.shape

    n_var_components = min(n_features, n_samples, 5)
    pca_var = PCA(n_components=n_var_components)
    pca_var.fit(x_scaled)

    ratios = pca_var.explained_variance_ratio_
    cumulative = np.cumsum(ratios)

    variance_explained = [
        {
            "component": int(i + 1),
            "variance_ratio": _to_float(ratios[i]),
            "cumulative": _to_float(cumulative[i]),
        }
        for i in range(len(ratios))
    ]

    components_for_80 = _components_for_80_percent(cumulative)

    pca2 = PCA(n_components=min(2, n_features))
    coords = pca2.fit_transform(x_scaled)
    pca_x = coords[:, 0]
    pca_y = coords[:, 1] if coords.shape[1] > 1 else np.zeros(len(coords))

    if np.allclose(pca_y, 0.0):
        pca_note = (
            "Une seule feature effective — pca_y = 0 pour tous les points. "
            "La visualisation sera enrichie avec les vraies données P1 "
            "(note_vendeur, nombre_avis)."
        )
    else:
        pca_note = None

    cluster_labels = _cluster_labels_from_result(df, cluster_result)

    points = []
    for i, (_, row) in enumerate(df.iterrows()):
        points.append(
            {
                "title": str(row["title"]),
                "prix_mad": _to_float(row["prix_mad"]),
                "pca_x": _to_float(pca_x[i]),
                "pca_y": _to_float(pca_y[i]),
                "cluster_label": cluster_labels[i],
            }
        )

    points_df = pd.DataFrame(points)
    centroids: dict[str, dict[str, float]] = {}

    for label in _CENTROID_LABELS:
        subset = points_df[points_df["cluster_label"] == label]
        if subset.empty:
            continue
        centroids[label] = {
            "pca_x": _to_float(subset["pca_x"].mean()),
            "pca_y": _to_float(subset["pca_y"].mean()),
        }

    for label in points_df["cluster_label"].unique():
        if label in centroids:
            continue
        subset = points_df[points_df["cluster_label"] == label]
        centroids[str(label)] = {
            "pca_x": _to_float(subset["pca_x"].mean()),
            "pca_y": _to_float(subset["pca_y"].mean()),
        }

    return {
        "variance_explained": variance_explained,
        "components_for_80_percent": components_for_80,
        "features_used": feature_names,
        "pca_note": pca_note,
        "points": points,
        "centroids": centroids,
    }


if __name__ == "__main__":
    import json

    from data_mining.clustering import run_clustering
    from data_mining.mock_data import get_mock_data
    from data_mining.preprocessing import clean_data

    cleaned = clean_data(get_mock_data())
    clusters = run_clustering(cleaned)
    pca_result = run_pca(cleaned, clusters)

    print("Features used :", pca_result.get("features_used"))
    print("PCA note :", pca_result.get("pca_note"))
    print("Variance explained per component :")
    for v in pca_result["variance_explained"]:
        print(
            f"  PC{v['component']} : {v['variance_ratio'] * 100:.1f}% "
            f"(cumul {v['cumulative'] * 100:.1f}%)"
        )
    print("Components needed for 80% :", pca_result["components_for_80_percent"])
    ys = [p["pca_y"] for p in pca_result["points"]]
    print("pca_y range :", min(ys), "to", max(ys))
    print("Centroids :", json.dumps(pca_result["centroids"], indent=2))
