"""
P2 Data Mining pipeline — orchestrates preprocessing through PCA.

Main entry point for the Market Research & Pricing Analysis platform.
"""

from __future__ import annotations

import pandas as pd

from data_mining.anomaly_detection import run_anomaly_detection
from data_mining.association_rules import run_association_rules
from data_mining.clustering import run_clustering
from data_mining.dimensionality_reduction import run_pca
from data_mining.mock_data import get_mock_data
from data_mining.preprocessing import clean_data
from data_mining.statistical_analysis import compute_statistics


def _step(msg: str) -> None:
    """Print a pipeline step line (UTF-8 checkmark with ASCII fallback on Windows)."""
    line = f"✓ {msg}"
    try:
        print(line)
    except UnicodeEncodeError:
        print(line.replace("✓", "[OK]"))


def _fail(step_name: str, error: Exception) -> None:
    try:
        print(f"✗ {step_name} failed : {error}")
    except UnicodeEncodeError:
        print(f"[FAIL] {step_name} failed : {error}")


def _attach_cluster_labels(cleaned_df: pd.DataFrame, clustering_result: dict) -> pd.DataFrame:
    """Merge cluster_label from clustering rows into cleaned_df (by row order)."""
    rows = clustering_result.get("rows", [])
    cleaned_df = cleaned_df.copy()
    if len(rows) != len(cleaned_df):
        label_map = {r["title"]: r["cluster_label"] for r in rows}
        cleaned_df["cluster_label"] = cleaned_df["title"].map(label_map)
    else:
        cleaned_df["cluster_label"] = [r["cluster_label"] for r in rows]
    return cleaned_df


def _attach_anomaly_scores(cleaned_df: pd.DataFrame, anomaly_result: dict) -> pd.DataFrame:
    """Reinject if_score and lof_score from anomaly detection into cleaned_df."""
    items = anomaly_result.get("anomalies", [])
    cleaned_df = cleaned_df.copy()
    if len(items) == len(cleaned_df):
        cleaned_df["if_score"] = [row["if_score"] for row in items]
        cleaned_df["lof_score"] = [row["lof_score"] for row in items]
    else:
        score_map = {row["title"]: row for row in items}
        cleaned_df["if_score"] = cleaned_df["title"].map(
            lambda t: score_map.get(str(t), {}).get("if_score")
        )
        cleaned_df["lof_score"] = cleaned_df["title"].map(
            lambda t: score_map.get(str(t), {}).get("lof_score")
        )
    return cleaned_df


def _collect_warnings(
    clustering_result: dict | None,
    anomaly_result: dict | None,
    rules_result: dict | None,
    pca_result: dict | None,
) -> list[str]:
    warnings: list[str] = []
    if clustering_result:
        w = clustering_result.get("dbscan_warning")
        if w:
            warnings.append(w)
        for cw in clustering_result.get("cluster_warnings") or []:
            warnings.append(cw)
    if anomaly_result:
        w = anomaly_result.get("agreement_warning")
        if w:
            warnings.append(w)
    if rules_result:
        w = rules_result.get("high_confidence_warning")
        if w:
            warnings.append(w)
    if pca_result:
        w = pca_result.get("pca_note")
        if w:
            warnings.append(w)
    return warnings


def run_pipeline(df: pd.DataFrame) -> dict:
    """
    Run the full P2 data mining pipeline on scraped product data.

    Parameters
    ----------
    df : pd.DataFrame
        Raw or mock data with columns expected by preprocessing
        (title, price, source, query, created_at).

    Returns
    -------
    dict
        Unified results: stats, clustering, anomalies, rules, PCA, warnings.
    """
    steps_ok = {
        "preprocessing": False,
        "statistics": False,
        "clustering": False,
        "anomaly_detection": False,
        "association_rules": False,
        "pca": False,
    }

    cleaned_df: pd.DataFrame | None = None
    stats = None
    clustering_result = None
    anomaly_result = None
    rules_result = None
    pca_result = None

    # STEP 1 — preprocessing
    try:
        cleaned_df = clean_data(df)
        if cleaned_df.empty:
            raise ValueError("No valid data after preprocessing")
        steps_ok["preprocessing"] = True
        _step(f"Preprocessing done — {len(cleaned_df)} rows")
    except Exception as exc:
        _fail("preprocessing", exc)
        return {
            "status": "failed",
            "rows_analysed": 0,
            "stats": None,
            "clustering": None,
            "anomalies": None,
            "association_rules": None,
            "pca": None,
            "warnings": [],
        }

    # STEP 2 — statistical analysis
    try:
        stats = compute_statistics(cleaned_df)
        steps_ok["statistics"] = True
        _step("Statistical analysis done")
    except Exception as exc:
        _fail("statistical analysis", exc)

    # STEP 3 — clustering
    try:
        clustering_result = run_clustering(cleaned_df)
        cleaned_df = _attach_cluster_labels(cleaned_df, clustering_result)
        steps_ok["clustering"] = True
        _step(
            f"Clustering done — optimal K: {clustering_result['optimal_k']}, "
            f"best: {clustering_result['best_algorithm']}"
        )
    except Exception as exc:
        _fail("clustering", exc)

    # STEP 4 — anomaly detection
    try:
        anomaly_result = run_anomaly_detection(cleaned_df)
        cleaned_df = _attach_anomaly_scores(cleaned_df, anomaly_result)
        steps_ok["anomaly_detection"] = True
        _step(
            f"Anomaly detection done — "
            f"{anomaly_result['total_anomalies_confirmed']} confirmed anomalies"
        )
    except Exception as exc:
        _fail("anomaly detection", exc)

    # STEP 5 — association rules
    try:
        rules_result = run_association_rules(cleaned_df)
        steps_ok["association_rules"] = True
        _step(f"Association rules done — {rules_result['total_rules']} rules found")
    except Exception as exc:
        _fail("association rules", exc)

    # STEP 6 — PCA
    if clustering_result is not None:
        try:
            pca_result = run_pca(cleaned_df, clustering_result)
            steps_ok["pca"] = True
            _step(
                f"PCA done — {pca_result['components_for_80_percent']} components "
                f"for 80% variance"
            )
        except Exception as exc:
            _fail("PCA", exc)
    else:
        _fail("PCA", RuntimeError("clustering did not run — PCA skipped"))

    if all(steps_ok.values()):
        status = "done"
    elif steps_ok["preprocessing"]:
        status = "partial"
    else:
        status = "failed"

    warnings = _collect_warnings(clustering_result, anomaly_result, rules_result, pca_result)

    clustering_out = None
    if clustering_result is not None:
        clustering_out = {
            "optimal_k": clustering_result["optimal_k"],
            "k_forced": clustering_result["k_forced"],
            "k_range_tested": clustering_result["k_range_tested"],
            "k_cap_reason": clustering_result["k_cap_reason"],
            "best_algorithm": clustering_result["best_algorithm"],
            "kmeans_silhouette": clustering_result["kmeans_silhouette"],
            "silhouette_interpretation": clustering_result["silhouette_interpretation"],
            "dbscan_silhouette": clustering_result["dbscan_silhouette"],
            "dbscan_warning": clustering_result["dbscan_warning"],
            "cluster_counts": clustering_result["cluster_counts"],
            "cluster_summary": clustering_result["cluster_summary"],
            "elbow_data": clustering_result["elbow_data"],
        }

    anomalies_out = None
    if anomaly_result is not None:
        anomalies_out = {
            "optimal_contamination": anomaly_result["optimal_contamination"],
            "total_confirmed": anomaly_result["total_anomalies_confirmed"],
            "agreement_rate": anomaly_result["agreement_rate"],
            "agreement_warning": anomaly_result["agreement_warning"],
            "items": anomaly_result["anomalies"],
        }

    rules_out = None
    if rules_result is not None:
        rules_out = {
            "chosen_support": rules_result["chosen_support"],
            "total_rules": rules_result["total_rules"],
            "top_rules": rules_result["top_rules"],
            "high_confidence_warning": rules_result["high_confidence_warning"],
            "algorithm_comparison": rules_result.get("algorithm_comparison"),
        }

    pca_out = None
    if pca_result is not None:
        pca_out = {
            "variance_explained": pca_result["variance_explained"],
            "components_for_80_percent": pca_result["components_for_80_percent"],
            "features_used": pca_result.get("features_used"),
            "pca_note": pca_result.get("pca_note"),
            "points": pca_result["points"],
            "centroids": pca_result["centroids"],
        }

    result = {
        "status": status,
        "rows_analysed": int(len(cleaned_df)),
        "stats": stats,
        "clustering": clustering_out,
        "anomalies": anomalies_out,
        "association_rules": rules_out,
        "pca": pca_out,
        "warnings": warnings,
    }

    _step("Pipeline complete")
    return result


def run_pipeline_from_mock(seed: int | None = 42) -> dict:
    """Load mock scraped data and run the full pipeline (for testing without P1)."""
    return run_pipeline(get_mock_data(seed=seed))


def run_pipeline_from_sqlite(db_path: str | None = None) -> dict:
    """Load products from local SQLite (table Product) and run the full pipeline."""
    from data_mining.load_from_db import load_from_sqlite

    return run_pipeline(load_from_sqlite(db_path))


def run_pipeline_from_django(
    user_id: int | None = None,
    search_query: str | None = None,
    limit: int | None = None,
) -> dict:
    """Load products from MySQL via Django ORM (même BDD que le backend P1)."""
    from data_mining.load_from_db import load_from_django

    return run_pipeline(load_from_django(user_id=user_id, search_query=search_query, limit=limit))


def run_pipeline_from_mysql() -> dict:
    """Load products from MySQL via PyMySQL (paramètres Django settings)."""
    from data_mining.load_from_db import load_from_mysql

    return run_pipeline(load_from_mysql())


def export_pipeline_result(result: dict, path: str) -> None:
    """Serialize pipeline result to JSON (for rapport / P4)."""
    import json
    from pathlib import Path

    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False, default=str)


if __name__ == "__main__":
    import json
    from pathlib import Path

    pipeline_result = run_pipeline_from_mock()
    out_dir = Path(__file__).resolve().parent / "output"
    export_pipeline_result(pipeline_result, str(out_dir / "pipeline_mock.json"))

    print("\n=== PIPELINE SUMMARY ===")
    print(f"Status          : {pipeline_result['status']}")
    print(f"Rows analysed   : {pipeline_result['rows_analysed']}")

    if pipeline_result["clustering"]:
        c = pipeline_result["clustering"]
        print(f"Optimal K       : {c['optimal_k']} (k_forced={c['k_forced']})")
        print(f"Best algorithm  : {c['best_algorithm']}")
        print(f"Silhouette      : {c['kmeans_silhouette']} ({c['silhouette_interpretation']})")
        print(f"DBSCAN warning  : {c['dbscan_warning']}")
        print(f"Cluster counts  : {c['cluster_counts']} ({len(c['cluster_counts'])} labels)")
        print("\n=== CLUSTER SUMMARY ===")
        for row in c.get("cluster_summary", []):
            line = (
                f"  {row['label']:20} | n={row['count']:3} | {row['share_pct']:5.1f}% | "
                f"médiane={row['price_median']:>10.2f} MAD | "
                f"[{row['price_min']:>8.2f} → {row['price_max']:>8.2f}]"
            )
            try:
                print(line)
            except UnicodeEncodeError:
                print(
                    line.replace("é", "e")
                    .replace("è", "e")
                    .replace("→", "->")
                )

    if pipeline_result["anomalies"]:
        print(f"Anomalies found : {pipeline_result['anomalies']['total_confirmed']}")
        print(f"Agreement warn. : {pipeline_result['anomalies']['agreement_warning']}")

    if pipeline_result["association_rules"]:
        print(f"Rules found     : {pipeline_result['association_rules']['total_rules']}")
        comp = pipeline_result["association_rules"].get("algorithm_comparison")
        if comp:
            print(
                f"FP-Growth vs Apriori : {comp.get('fpgrowth_rules_gamme')} / "
                f"{comp.get('apriori_rules_gamme')} règles gamme (itemsets "
                f"{comp.get('fpgrowth_itemsets')} / {comp.get('apriori_itemsets')})"
            )
        print("\nTop 3 rules (overfitting_warning) :")
        for rule in pipeline_result["association_rules"]["top_rules"][:3]:
            print(f"  overfitting={rule['overfitting_warning']}: {rule['interpretation'][:80]}...")

    if pipeline_result["pca"]:
        pca = pipeline_result["pca"]
        print(f"PCA features    : {pca.get('features_used')}")
        print(f"PCA components  : {pca['components_for_80_percent']} for 80%")
        ys = [p["pca_y"] for p in pca["points"]]
        print(f"pca_y variation : min={min(ys):.4f}, max={max(ys):.4f}")
        print(f"PCA note        : {pca.get('pca_note')}")

    if pipeline_result["stats"]:
        print(f"Global median   : {pipeline_result['stats']['global']['median']} MAD")
        print(f"Global CV       : {pipeline_result['stats']['global']['cv']}%")

    print("\n=== WARNINGS ===")
    if pipeline_result["warnings"]:
        for w in pipeline_result["warnings"]:
            try:
                print(f"  - {w}")
            except UnicodeEncodeError:
                print(f"  - {w.encode('ascii', errors='replace').decode('ascii')}")
    else:
        print("  (none)")

    print("\n=== CLUSTERING ELBOW (3 features) ===")
    if pipeline_result["clustering"]:
        print(json.dumps(pipeline_result["clustering"]["elbow_data"], indent=2))
