"""
Association rule mining on cleaned product data (P2) — FP-Growth + lift.

Input: cleaned DataFrame from preprocessing.clean_data.
"""

from __future__ import annotations

import pandas as pd
from mlxtend.frequent_patterns import association_rules, fpgrowth
from mlxtend.preprocessing import TransactionEncoder

SUPPORT_CANDIDATES = [0.05, 0.10, 0.15, 0.20]
MIN_ITEMSETS = 10
MAX_ITEMSETS = 100
FALLBACK_SUPPORT = 0.05
LIFT_THRESHOLD = 1.2
LIFT_FALLBACK = 1.0
MAX_RULES = 20
HIGH_CONFIDENCE_THRESHOLD = 0.95


def _discretize_gamme_prix(df: pd.DataFrame) -> pd.DataFrame:
    work = df.copy()
    q1 = work["prix_mad"].quantile(0.25)
    q3 = work["prix_mad"].quantile(0.75)

    def _bin(price: float) -> str:
        if price <= q1:
            return "bas"
        if price <= q3:
            return "moyen"
        return "élevé"

    work["gamme_prix"] = work["prix_mad"].apply(_bin)
    return work


def _row_to_transaction(row: pd.Series) -> list[str]:
    items = [
        f"marque_{row['marque']}",
        f"etat_{row['etat']}",
        f"source_{row['source']}",
        f"gamme_{row['gamme_prix']}",
    ]
    mots_cles = row.get("mots_cles")
    if isinstance(mots_cles, list):
        items.extend(str(m) for m in mots_cles if m)
    return items


def _build_transactions(df: pd.DataFrame) -> list[list[str]]:
    return [_row_to_transaction(row) for _, row in df.iterrows()]


def _encode_transactions(transactions: list[list[str]]) -> pd.DataFrame:
    encoder = TransactionEncoder()
    array = encoder.fit(transactions).transform(transactions)
    return pd.DataFrame(array, columns=encoder.columns_)


def _choose_support(
    encoded: pd.DataFrame,
) -> tuple[float, list[dict]]:
    search_results = []
    chosen = FALLBACK_SUPPORT

    for min_support in SUPPORT_CANDIDATES:
        itemsets = fpgrowth(encoded, min_support=min_support, use_colnames=True)
        count = len(itemsets)
        search_results.append(
            {
                "min_support": round(float(min_support), 3),
                "itemsets_found": int(count),
            }
        )

    valid = [
        row
        for row in search_results
        if MIN_ITEMSETS <= row["itemsets_found"] <= MAX_ITEMSETS
    ]
    if valid:
        chosen = valid[0]["min_support"]
    else:
        chosen = FALLBACK_SUPPORT

    return float(chosen), search_results


def _frozenset_to_list(items) -> list[str]:
    return sorted(str(i) for i in items)


def _build_interpretation(
    antecedent: list[str],
    consequent: list[str],
    confidence: float,
    lift: float,
) -> str:
    ante = ", ".join(antecedent)
    cons = ", ".join(consequent)
    return f"Si {ante} alors {cons} (confiance: {confidence * 100:.1f}%, lift: {lift:.3f})"


def _rules_to_top_list(rules_df: pd.DataFrame) -> list[dict]:
    gamme_rules = rules_df[
        rules_df["consequents"].apply(
            lambda cons: any(str(item).startswith("gamme_") for item in cons)
        )
    ].sort_values("lift", ascending=False)

    top = gamme_rules.head(MAX_RULES)
    result = []

    for _, rule in top.iterrows():
        antecedent = _frozenset_to_list(rule["antecedents"])
        consequent = _frozenset_to_list(rule["consequents"])
        support = round(float(rule["support"]), 3)
        confidence = round(float(rule["confidence"]), 3)
        lift = round(float(rule["lift"]), 3)
        overfitting_warning = confidence >= HIGH_CONFIDENCE_THRESHOLD

        result.append(
            {
                "antecedent": antecedent,
                "consequent": consequent,
                "support": support,
                "confidence": confidence,
                "lift": lift,
                "overfitting_warning": overfitting_warning,
                "interpretation": _build_interpretation(
                    antecedent,
                    consequent,
                    confidence,
                    lift,
                ),
            }
        )

    return result


def run_association_rules(df: pd.DataFrame) -> dict:
    """
    Mine association rules predicting price range (gamme_prix) from product attributes.

    Parameters
    ----------
    df : pd.DataFrame
        Cleaned data with prix_mad, marque, etat, mots_cles, source.

    Returns
    -------
    dict
        Support search summary, chosen support, rule counts, top rules, warnings.
    """
    work = _discretize_gamme_prix(df)
    transactions = _build_transactions(work)
    encoded = _encode_transactions(transactions)

    chosen_support, support_search = _choose_support(encoded)

    itemsets = fpgrowth(encoded, min_support=chosen_support, use_colnames=True)

    if itemsets.empty:
        return {
            "support_search": support_search,
            "chosen_support": round(float(chosen_support), 3),
            "total_rules": 0,
            "top_rules": [],
            "high_confidence_warning": None,
        }

    rules = association_rules(
        itemsets,
        metric="lift",
        min_threshold=LIFT_THRESHOLD,
    )

    if rules.empty:
        rules = association_rules(
            itemsets,
            metric="lift",
            min_threshold=LIFT_FALLBACK,
        )

    top_rules = _rules_to_top_list(rules) if not rules.empty else []

    has_high_confidence = any(r["overfitting_warning"] for r in top_rules)
    if has_high_confidence:
        high_confidence_warning = (
            "Certaines regles ont une confiance >= 95% — "
            "possible surapprentissage sur petit dataset. "
            "Ces regles doivent etre validees sur les vraies donnees."
        )
    else:
        high_confidence_warning = None

    return {
        "support_search": support_search,
        "chosen_support": round(float(chosen_support), 3),
        "total_rules": int(len(top_rules)),
        "top_rules": top_rules,
        "high_confidence_warning": high_confidence_warning,
    }


if __name__ == "__main__":
    from data_mining.mock_data import get_mock_data
    from data_mining.preprocessing import clean_data

    cleaned = clean_data(get_mock_data())
    rules_result = run_association_rules(cleaned)

    print("Chosen support :", rules_result["chosen_support"])
    print("Total rules    :", rules_result["total_rules"])
    print("High conf. warning :", rules_result["high_confidence_warning"])
    print("\nTop 5 rules :")
    for rule in rules_result["top_rules"][:5]:
        print(f"  [{rule['overfitting_warning']}] {rule['interpretation']}")
