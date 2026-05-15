"""
Shared feature encoding for clustering, anomaly detection, and PCA.
"""

from __future__ import annotations

import pandas as pd
from sklearn.preprocessing import StandardScaler

ETAT_ENCODING = {
    "neuf": 3,
    "reconditionné": 2,
    "occasion": 1,
    "inconnu": 0,
}


def add_encoded_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add marque_encoded (mean prix_mad) and etat_encoded (ordinal)."""
    work = df.copy()
    marque_means = work.groupby("marque", observed=True)["prix_mad"].mean()
    work["marque_encoded"] = work["marque"].map(marque_means)
    work["etat_encoded"] = work["etat"].map(ETAT_ENCODING).fillna(0).astype(int)
    return work


def build_scaled_matrix(
    df: pd.DataFrame,
    extra_columns: tuple[str, ...] = (),
) -> tuple[pd.DataFrame, object]:
    """
    Build StandardScaler matrix: prix_mad + marque_encoded + etat_encoded (+ optional extras).
    Returns (X_scaled ndarray, fitted StandardScaler).
    """
    work = add_encoded_features(df)
    columns = ["prix_mad", "marque_encoded", "etat_encoded"]
    for col in extra_columns:
        if col in work.columns and col not in columns:
            columns.append(col)

    scaler = StandardScaler()
    x_scaled = scaler.fit_transform(work[columns].values)
    return x_scaled, scaler
