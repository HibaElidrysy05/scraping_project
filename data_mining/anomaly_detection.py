"""
Anomaly detection on cleaned product data (P2) — Isolation Forest + LOF.

Features: prix_mad + marque_encoded + etat_encoded (scaled).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor

from data_mining.feature_encoding import build_scaled_matrix

CONTAMINATION_CANDIDATES = [0.03, 0.05, 0.08, 0.10, 0.15]
TARGET_ANOMALY_RATE = 0.05
RANDOM_STATE = 42
# n_neighbors=3 : plus adapté aux petits datasets (n<100)
# évite un voisinage trop large qui nuit à la sensibilité locale
LOF_NEIGHBORS = 3


def _choose_optimal_contamination(
    x_scaled: np.ndarray,
    n_rows: int,
) -> tuple[float, list[dict]]:
    """Pick contamination whose anomaly count is closest to 5% of rows."""
    target_count = TARGET_ANOMALY_RATE * n_rows
    search_results = []

    for contamination in CONTAMINATION_CANDIDATES:
        iso = IsolationForest(
            contamination=contamination,
            random_state=RANDOM_STATE,
        )
        predictions = iso.fit_predict(x_scaled)
        anomaly_count = int((predictions == -1).sum())
        search_results.append(
            {
                "contamination": round(float(contamination), 2),
                "anomaly_count": anomaly_count,
            }
        )

    optimal = min(
        search_results,
        key=lambda row: abs(row["anomaly_count"] - target_count),
    )["contamination"]

    return float(optimal), search_results


def _anomaly_source(if_flag: bool, lof_flag: bool) -> str:
    if if_flag and lof_flag:
        return "both"
    if if_flag:
        return "IF_only"
    if lof_flag:
        return "LOF_only"
    return "none"


def _explain_anomaly(prix_mad: float, q1: float, q3: float, iqr: float) -> str:
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    if prix_mad < lower:
        return "prix anormalement bas"
    if prix_mad > upper:
        return "prix anormalement élevé"
    return "anomalie contextuelle"


def run_anomaly_detection(df: pd.DataFrame) -> dict:
    """
    Detect price anomalies with Isolation Forest + LOF (intersection = confirmed).

    Parameters
    ----------
    df : pd.DataFrame
        Cleaned data with prix_mad, marque, etat, title.

    Returns
    -------
    dict
        Contamination search, counts, agreement rate, per-row anomaly details.
    """
    work = df.copy()
    x_scaled, _ = build_scaled_matrix(work)
    n_rows = len(work)

    optimal_contamination, contamination_search = _choose_optimal_contamination(
        x_scaled,
        n_rows,
    )

    iso = IsolationForest(
        contamination=optimal_contamination,
        random_state=RANDOM_STATE,
    )
    if_predictions = iso.fit_predict(x_scaled)
    work["if_anomaly"] = if_predictions == -1
    work["if_score"] = iso.decision_function(x_scaled)

    lof = LocalOutlierFactor(
        n_neighbors=LOF_NEIGHBORS,
        contamination=optimal_contamination,
    )
    lof_predictions = lof.fit_predict(x_scaled)
    work["lof_anomaly"] = lof_predictions == -1
    work["lof_score"] = lof.negative_outlier_factor_

    work["is_anomaly"] = work["if_anomaly"] & work["lof_anomaly"]
    work["anomaly_source"] = [
        _anomaly_source(bool(if_a), bool(lof_a))
        for if_a, lof_a in zip(work["if_anomaly"], work["lof_anomaly"])
    ]

    prices = work["prix_mad"]
    q1 = float(prices.quantile(0.25))
    q3 = float(prices.quantile(0.75))
    iqr = q3 - q1

    total_confirmed = int(work["is_anomaly"].sum())
    if_only_count = int((work["if_anomaly"] & ~work["lof_anomaly"]).sum())
    lof_only_count = int((work["lof_anomaly"] & ~work["if_anomaly"]).sum())

    either_count = int((work["if_anomaly"] | work["lof_anomaly"]).sum())
    if either_count > 0:
        agreement_rate = round(float(total_confirmed / either_count * 100), 2)
    else:
        agreement_rate = 0.0

    if agreement_rate < 50:
        agreement_warning = (
            f"Faible accord IF/LOF ({agreement_rate}%) — "
            "résultats peu fiables sur ce volume de données. "
            "Les anomalies confirmées (intersection) restent valides."
        )
    else:
        agreement_warning = None

    anomalies = []
    for _, row in work.iterrows():
        is_confirmed = bool(row["is_anomaly"])
        reason = (
            _explain_anomaly(float(row["prix_mad"]), q1, q3, iqr)
            if is_confirmed
            else ""
        )
        anomalies.append(
            {
                "title": str(row["title"]),
                "prix_mad": round(float(row["prix_mad"]), 2),
                "if_anomaly": bool(row["if_anomaly"]),
                "lof_anomaly": bool(row["lof_anomaly"]),
                "if_score": round(float(row["if_score"]), 4),
                "lof_score": round(float(row["lof_score"]), 4),
                "is_anomaly": is_confirmed,
                "anomaly_source": str(row["anomaly_source"]),
                "reason": reason,
            }
        )

    return {
        "optimal_contamination": round(float(optimal_contamination), 2),
        "contamination_search": contamination_search,
        "total_anomalies_confirmed": total_confirmed,
        "if_only_count": if_only_count,
        "lof_only_count": lof_only_count,
        "agreement_rate": agreement_rate,
        "agreement_warning": agreement_warning,
        "anomalies": anomalies,
    }


if __name__ == "__main__":
    from data_mining.mock_data import get_mock_data
    from data_mining.preprocessing import clean_data

    cleaned = clean_data(get_mock_data())
    detection = run_anomaly_detection(cleaned)

    print("Optimal contamination :", detection["optimal_contamination"])
    print("Confirmed anomalies   :", detection["total_anomalies_confirmed"])
    print("Agreement rate        :", detection["agreement_rate"], "%")
    print("Agreement warning     :", detection["agreement_warning"])
    print("\nAnomalies detected :")
    for item in detection["anomalies"]:
        if item["is_anomaly"]:
            print(
                f"  {item['title'][:40]:40} | {item['prix_mad']:>10.2f} MAD | {item['reason']}"
            )
