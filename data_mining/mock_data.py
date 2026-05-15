"""
Mock scraped product data for P2 (Data Mining) development.

Column names match the P1 Product model fields used for mining:
title, price, source, query, created_at.

Replace get_mock_data() with real DB queries when P1 is ready.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

_BRANDS = ("Apple", "Samsung", "Xiaomi", "HP", "Huawei")
_PRODUCT_TYPES = (
    "iPhone 15 Pro 256GB",
    "iPhone 14 128GB",
    "iPhone 13",
    "Galaxy S24 Ultra",
    "Galaxy A54",
    "Redmi Note 13 Pro",
    "Poco X6 Pro",
    "Pavilion 15 Laptop",
    "MateBook D15",
    "Mate 60 Pro",
    "MacBook Air M2",
    "Galaxy Tab S9",
)
_STATE_SUFFIXES = ("Neuf", "Reconditionné", "Occasion", None)  # None = missing state
_SOURCES = ("Jumia", "Avito")
_QUERIES = ("iphone", "samsung", "laptop", "xiaomi", "huawei", "smartphone")


def _format_price_mad(amount: float) -> str:
    """Format a numeric MAD amount as a raw scraped price string."""
    return f"{amount:,.2f} Dhs".replace(",", " ")


def _build_title(brand: str, product: str, state: str | None) -> str:
    parts = [brand, product]
    if state:
        parts.append(state)
    return " ".join(parts)


def _generate_base_catalog(n: int, rng: random.Random) -> list[dict]:
    rows: list[dict] = []
    for _ in range(n):
        brand = rng.choice(_BRANDS)
        product = rng.choice(_PRODUCT_TYPES)
        # Bias titles toward the brand when possible
        if brand == "Apple" and "iPhone" not in product and "MacBook" not in product:
            product = rng.choice(["iPhone 15 Pro 256GB", "iPhone 14 128GB", "iPhone 13"])
        elif brand == "Samsung" and "Galaxy" not in product:
            product = rng.choice(["Galaxy S24 Ultra", "Galaxy A54", "Galaxy Tab S9"])
        elif brand == "Xiaomi":
            product = rng.choice(["Redmi Note 13 Pro", "Poco X6 Pro"])
        elif brand == "HP":
            product = rng.choice(["Pavilion 15 Laptop", "EliteBook 840"])
        elif brand == "Huawei":
            product = rng.choice(["Mate 60 Pro", "MateBook D15"])

        state = rng.choice(_STATE_SUFFIXES)
        rows.append(
            {
                "title": _build_title(brand, product, state),
                "source": rng.choice(_SOURCES),
                "query": rng.choice(_QUERIES),
            }
        )
    return rows


def _assign_prices(rows: list[dict], rng: random.Random) -> None:
    """Assign price strings; low / mid / high MAD ranges."""
    for row in rows:
        tier = rng.choices(["low", "mid", "high"], weights=[0.25, 0.45, 0.30])[0]
        if tier == "low":
            amount = rng.uniform(500, 2000)
        elif tier == "mid":
            amount = rng.uniform(2000, 6000)
        else:
            amount = rng.uniform(6000, 22000)
        row["price"] = _format_price_mad(round(amount, 2))


def _inject_anomalies(rows: list[dict], rng: random.Random) -> None:
    """2-3 suspiciously low and 2-3 unrealistically high prices."""
    iphone_indices = [i for i, r in enumerate(rows) if "iPhone" in r["title"]]
    candidates = iphone_indices if len(iphone_indices) >= 3 else list(range(len(rows)))

    low_count = rng.randint(2, 3)
    for idx in rng.sample(candidates, min(low_count, len(candidates))):
        rows[idx]["price"] = _format_price_mad(rng.uniform(120, 199))

    high_pool = [i for i in range(len(rows)) if i not in candidates[:low_count]]
    high_count = rng.randint(2, 3)
    for idx in rng.sample(high_pool, min(high_count, len(high_pool))):
        rows[idx]["price"] = _format_price_mad(rng.uniform(45000, 89000))


def _inject_dirty_data(rows: list[dict], rng: random.Random) -> None:
    """Null prices, zero prices, and duplicate rows."""
    null_count = rng.randint(3, 4)
    for idx in rng.sample(range(len(rows)), null_count):
        rows[idx]["price"] = None

    zero_indices = rng.sample(range(len(rows)), rng.randint(1, 2))
    for idx in zero_indices:
        rows[idx]["price"] = "0 Dhs"

    dup_count = rng.randint(2, 4)
    for _ in range(dup_count):
        original = rng.choice(rows)
        duplicate = {**original}
        rows.append(duplicate)


def _assign_timestamps(rows: list[dict], rng: random.Random) -> None:
    now = datetime.now()
    for row in rows:
        offset_minutes = rng.randint(0, 14 * 24 * 60)  # last 14 days
        row["created_at"] = now - timedelta(
            minutes=offset_minutes,
            seconds=rng.randint(0, 59),
        )


def get_mock_data(seed: int | None = 42) -> pd.DataFrame:
    """
    Return a realistic mock DataFrame of scraped products.

    Parameters
    ----------
    seed : int or None
        Random seed for reproducibility (default 42). Pass None for non-deterministic data.

    Returns
    -------
    pd.DataFrame
        Columns: title, price, source, query, created_at
    """
    rng = random.Random(seed)
    np.random.seed(seed if seed is not None else None)

    target_rows = max(50, 55)
    rows = _generate_base_catalog(target_rows, rng)
    _assign_prices(rows, rng)
    _inject_anomalies(rows, rng)
    _inject_dirty_data(rows, rng)
    _assign_timestamps(rows, rng)

    df = pd.DataFrame(rows, columns=["title", "price", "source", "query", "created_at"])
    df["created_at"] = pd.to_datetime(df["created_at"])
    return df.reset_index(drop=True)


def get_mock_data_as_db_rows(seed: int | None = 42) -> list[dict]:
    """
    Same data as get_mock_data(), as list[dict] mimicking Scraper_product ORM rows.

    Each dict has keys: title, price, source, query, created_at
    (no id / img_link / link / price_value — only P2-relevant fields).
    """
    df = get_mock_data(seed=seed)
    records = df.to_dict(orient="records")
    for row in records:
        ts = row["created_at"]
        if isinstance(ts, pd.Timestamp):
            row["created_at"] = ts.to_pydatetime()
    return records


if __name__ == "__main__":
    sample = get_mock_data()
    print(sample.head(10))
    print(f"\nRows: {len(sample)}")
    print(f"Sources:\n{sample['source'].value_counts()}")
    print(f"Null prices: {sample['price'].isna().sum()}")
