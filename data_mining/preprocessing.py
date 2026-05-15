"""
Preprocessing pipeline for scraped product data (P2).

Applies cleaning, price parsing, feature extraction, and deduplication
in a fixed order. Input columns expected from P1 / mock_data:
title, price, source, query, created_at
"""

from __future__ import annotations

import re

import numpy as np
import pandas as pd

# Exchange rates to MAD — update here when rates change
CONVERSION_TO_MAD = {
    "MAD": 1.0,
    "USD": 10.2,
    "EUR": 11.0,
}

_MARQUES = [
    "Apple",
    "Samsung",
    "Xiaomi",
    "HP",
    "Huawei",
    "Lenovo",
    "Asus",
    "Dell",
    "Sony",
    "Oppo",
]

_MOTS_CLES = [
    "Pro",
    "Max",
    "Ultra",
    "Plus",
    "Mini",
    "Lite",
    "SSD",
    "4K",
    "Gaming",
    "5G",
    "256GB",
    "512GB",
    "128GB",
    "64GB",
    "32GB",
    "1TB",
    "i3",
    "i5",
    "i7",
    "i9",
    "Ryzen",
    "Core",
    "RAM",
    "Go",
    "GB",
    "pouces",
    "inch",
    "Snapdragon",
    "Dimensity",
    "AMOLED",
    "LCD",
    "FHD",
    "HD",
]


def _is_invalid_price(price) -> bool:
    if price is None or (isinstance(price, float) and np.isnan(price)):
        return True
    if pd.isna(price):
        return True
    s = str(price).strip()
    if s == "0":
        return True
    if "0 Dhs" in s or "0 dhs" in s.lower():
        return True
    return False


def _parse_prix_valeur(price_str: str) -> float:
    """Extract numeric value from raw price string (MAD-style thousands separators)."""
    match = re.search(r"[\d\s,\.]+", price_str)
    if not match:
        return np.nan
    numeric = match.group().replace(" ", "").replace(",", "")
    try:
        return float(numeric)
    except ValueError:
        return np.nan


def _extract_devise(price_str: str) -> str:
    upper = price_str.upper()
    if "€" in price_str or "EUR" in upper:
        return "EUR"
    if "$" in price_str or "USD" in upper:
        return "USD"
    if "DHS" in upper or "DH" in upper or "MAD" in upper:
        return "MAD"
    return "MAD"


def _extract_etat(title: str) -> str:
    lower = title.lower()
    if "neuf" in lower:
        return "neuf"
    if "reconditionné" in lower or "reconditionne" in lower:
        return "reconditionné"
    if "occasion" in lower:
        return "occasion"
    return "inconnu"


def _extract_marque(title: str) -> str:
    """First brand match in title (case-insensitive word boundary)."""
    for marque in _MARQUES:
        if re.search(rf"\b{re.escape(marque)}\b", title, re.IGNORECASE):
            return marque
    return "autre"


def _extract_mots_cles(title: str) -> list[str]:
    """All keyword matches in title (case-insensitive)."""
    found = []
    for mot in _MOTS_CLES:
        if re.search(rf"\b{re.escape(mot)}\b", title, re.IGNORECASE):
            found.append(mot)
    return found


def _conversion_label(devise: str) -> str:
    if devise == "USD":
        return "USD→MAD"
    if devise == "EUR":
        return "EUR→MAD"
    return "MAD"


_VALID_DEVISES = frozenset({"MAD", "USD", "EUR"})


def _normalize_etat_p1(val) -> str:
    if val is None or (isinstance(val, float) and np.isnan(val)) or pd.isna(val):
        return "inconnu"
    s = str(val).strip().lower()
    if not s:
        return "inconnu"
    if s == "neuf":
        return "neuf"
    if "recondition" in s:
        return "reconditionné"
    if s == "occasion":
        return "occasion"
    return "inconnu"


def _normalize_devise_p1(val) -> str:
    if val is None or (isinstance(val, float) and np.isnan(val)) or pd.isna(val):
        print("[preprocessing] WARNING: devise P1 vide — défaut MAD")
        return "MAD"
    s = str(val).strip().upper()
    if s in _VALID_DEVISES:
        return s
    print(f"[preprocessing] WARNING: devise P1 invalide {val!r} — défaut MAD")
    return "MAD"


def _prix_valeur_source_column(columns) -> str | None:
    if "prix_valeur" in columns:
        return "prix_valeur"
    if "price_value" in columns:
        return "price_value"
    return None


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Run the full preprocessing pipeline on scraped product data.

    Parameters
    ----------
    df : pd.DataFrame
        Raw data with at least: title, price, source, query, created_at

    Returns
    -------
    pd.DataFrame
        Copy of input with added columns:
        prix_valeur, devise, prix_mad, converted_from, etat, marque, mots_cles
    """
    rows_before = len(df)
    out = df.copy()

    has_etat_col = "etat" in df.columns
    has_devise_col = "devise" in df.columns
    prix_src_col = _prix_valeur_source_column(df.columns)
    has_prix_valeur_col = prix_src_col is not None

    print(
        f"[preprocessing] Colonnes P1 détectées: "
        f"etat={has_etat_col}, devise={has_devise_col}, prix_valeur={has_prix_valeur_col}"
    )
    print(
        "[preprocessing] Valeurs manquantes : suppression des lignes invalides "
        "(pas d'imputation — titre/prix requis)"
    )

    # 1. Remove invalid rows
    out = out[out["price"].notna()]
    out = out[~out["price"].apply(_is_invalid_price)]
    out = out[out["title"].notna()]

    # 2. prix_valeur — colonne P1 ou parsing chaîne prix
    if has_prix_valeur_col:
        out["prix_valeur"] = pd.to_numeric(out[prix_src_col], errors="coerce")
    else:
        out["prix_valeur"] = out["price"].astype(str).apply(_parse_prix_valeur)
    out = out[out["prix_valeur"].notna()]

    # 3. devise — colonne P1 ou extraction depuis prix textuel
    if has_devise_col:
        out["devise"] = out["devise"].apply(_normalize_devise_p1)
    else:
        out["devise"] = out["price"].astype(str).apply(_extract_devise)

    # 4. Convert to MAD → prix_mad + conversion trace
    out["converted_from"] = out["devise"].apply(_conversion_label)
    out["prix_mad"] = out.apply(
        lambda row: row["prix_valeur"] * CONVERSION_TO_MAD.get(row["devise"], 1.0),
        axis=1,
    )
    devise_counts = out["devise"].value_counts()
    mad_n = int(devise_counts.get("MAD", 0))
    usd_n = int(devise_counts.get("USD", 0))
    eur_n = int(devise_counts.get("EUR", 0))
    print(f"Devises détectées : MAD={mad_n}, USD={usd_n}, EUR={eur_n}")

    # 5. etat — colonne P1 ou extraction depuis titre
    if has_etat_col:
        out["etat"] = out["etat"].apply(_normalize_etat_p1)
    else:
        out["etat"] = out["title"].astype(str).apply(_extract_etat)

    # 6. Extract marque from title
    out["marque"] = out["title"].astype(str).apply(_extract_marque)

    # 7. Extract mots_cles from title
    out["mots_cles"] = out["title"].astype(str).apply(_extract_mots_cles)

    # 8. Remove duplicates (title + price + source)
    out = out.drop_duplicates(subset=["title", "price", "source"], keep="first")

    # 9. Reset index
    out = out.reset_index(drop=True)

    rows_after = len(out)
    removed = rows_before - rows_after
    print(f"Rows before : {rows_before} | Rows after : {rows_after} | Removed : {removed}")
    print("Sources des features:")
    print(f"  etat       : {'colonne P1' if has_etat_col else 'extraction titre'}")
    print(f"  devise     : {'colonne P1' if has_devise_col else 'extraction prix'}")
    print(
        f"  prix_valeur: {'colonne P1' if has_prix_valeur_col else 'parsing prix string'}"
    )

    return out


if __name__ == "__main__":
    from data_mining.mock_data import get_mock_data

    raw = get_mock_data()
    cleaned = clean_data(raw)
    print(cleaned[["title", "prix_mad", "devise", "etat", "marque", "mots_cles"]].head(10))
