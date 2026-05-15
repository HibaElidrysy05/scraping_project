"""
Descriptive statistics on cleaned product data (P2).

Operates on the output of preprocessing.clean_data (prix_mad, source, marque, etat).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

CV_HIGH_DISPERSION_THRESHOLD = 100.0


def _to_float(value) -> float:
    return round(float(value), 2)


def _coefficient_of_variation(series: pd.Series) -> float:
    mean = series.mean()
    if mean == 0 or pd.isna(mean):
        return 0.0
    return _to_float((series.std() / mean) * 100)


def _full_metrics(series: pd.Series) -> dict:
    """Global / per-platform metrics on prix_mad."""
    q1 = series.quantile(0.25)
    q3 = series.quantile(0.75)
    cv = _coefficient_of_variation(series)
    return {
        "count": int(series.count()),
        "min": _to_float(series.min()),
        "max": _to_float(series.max()),
        "mean": _to_float(series.mean()),
        "median": _to_float(series.median()),
        "std": _to_float(series.std()),
        "Q1": _to_float(q1),
        "Q3": _to_float(q3),
        "IQR": _to_float(q3 - q1),
        "cv": cv,
        "high_dispersion": bool(cv > CV_HIGH_DISPERSION_THRESHOLD),
    }


def _marque_metrics(series: pd.Series) -> dict:
    """Reduced metrics for per-brand breakdown."""
    return {
        "count": int(series.count()),
        "min": _to_float(series.min()),
        "max": _to_float(series.max()),
        "mean": _to_float(series.mean()),
        "median": _to_float(series.median()),
    }


def _price_distribution(series: pd.Series) -> list[dict]:
    """Five equal-width bins over prix_mad with product counts per bin."""
    if series.empty:
        return []

    binned = pd.cut(series, bins=5)
    counts = binned.value_counts().sort_index()

    distribution = []
    for interval, count in counts.items():
        left = _to_float(interval.left)
        right = _to_float(interval.right)
        distribution.append(
            {
                "range": f"{left}-{right}",
                "count": int(count),
            }
        )
    return distribution


def _price_distribution_quantiles(series: pd.Series) -> list[dict]:
    """Four quantile-based bins: min→Q1, Q1→median, median→Q3, Q3→max."""
    if series.empty:
        return []

    q1 = series.quantile(0.25)
    median = series.quantile(0.50)
    q3 = series.quantile(0.75)
    min_val = series.min()
    max_val = series.max()

    bins = [
        ("bas (min-Q1)", (min_val, q1)),
        ("moyen-bas (Q1-median)", (q1, median)),
        ("moyen-haut (median-Q3)", (median, q3)),
        ("élevé (Q3-max)", (q3, max_val)),
    ]

    distribution = []
    for label, (low, high) in bins:
        if label.startswith("bas"):
            mask = (series >= low) & (series <= high)
        else:
            mask = (series > low) & (series <= high)
        distribution.append(
            {
                "range": label,
                "count": int(mask.sum()),
            }
        )
    return distribution


def compute_statistics(df: pd.DataFrame) -> dict:
    """
    Compute descriptive statistics on cleaned product prices (prix_mad).

    Parameters
    ----------
    df : pd.DataFrame
        Cleaned data from preprocessing.clean_data

    Returns
    -------
    dict
        global, par_plateforme, par_marque, distribution, distribution_quantiles
    """
    prices = df["prix_mad"].dropna()

    result = {
        "global": _full_metrics(prices),
        "par_plateforme": {},
        "par_marque": {},
        "distribution": _price_distribution(prices),
        "distribution_quantiles": _price_distribution_quantiles(prices),
    }

    for platform, group in df.groupby("source", sort=True):
        result["par_plateforme"][str(platform)] = _full_metrics(group["prix_mad"])

    for marque, group in df.groupby("marque", sort=True):
        result["par_marque"][str(marque)] = _marque_metrics(group["prix_mad"])

    return result


if __name__ == "__main__":
    import json

    from data_mining.mock_data import get_mock_data
    from data_mining.preprocessing import clean_data

    cleaned = clean_data(get_mock_data())
    stats = compute_statistics(cleaned)
    print(json.dumps(stats, indent=2, ensure_ascii=False))
