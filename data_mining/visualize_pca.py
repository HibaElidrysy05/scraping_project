"""Génère un scatter plot PNG depuis la sortie PCA du pipeline."""

from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt

matplotlib.use("Agg")  # backend non-interactif

from data_mining.pipeline import run_pipeline_from_mock

OUTPUT_DIR = Path("data_mining/output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Couleurs cohérentes par segment de prix (ordre croissant)
SEGMENT_COLORS = {
    "entrée de gamme": "#3498db",  # bleu clair
    "bas de gamme": "#2ecc71",  # vert
    "milieu de gamme": "#f39c12",  # orange
    "haut de gamme": "#e74c3c",  # rouge
    "premium": "#9b59b6",  # violet
}


def _variance_ratios(pca: dict) -> list[float]:
    """Extrait les ratios de variance (API pipeline: variance_explained)."""
    ve = pca.get("variance_explained") or pca.get("explained_variance_ratio") or []
    if not ve:
        return []
    if isinstance(ve[0], dict):
        return [float(v.get("variance_ratio", 0)) for v in ve]
    return [float(v) for v in ve]


def _centroid_items(pca: dict) -> list[dict]:
    """Normalise centroids dict ou list vers une liste de points annotables."""
    raw = pca.get("centroids") or []
    if isinstance(raw, dict):
        return [
            {"cluster_label": label, "pca_x": coords["pca_x"], "pca_y": coords["pca_y"]}
            for label, coords in raw.items()
        ]
    return raw


def plot_pca_scatter(result: dict, save_path: Path) -> None:
    pca = result.get("pca") or {}
    points = pca.get("points", [])
    centroids = _centroid_items(pca)
    variance = _variance_ratios(pca)

    if not points:
        print("[WARN] Pas de points PCA, sortie annulée")
        return

    fig, ax = plt.subplots(figsize=(10, 7), dpi=120)

    by_label: dict[str, dict[str, list]] = {}
    for p in points:
        label = p.get("cluster_label", "inconnu")
        by_label.setdefault(label, {"x": [], "y": []})
        by_label[label]["x"].append(p["pca_x"])
        by_label[label]["y"].append(p["pca_y"])

    for label, coords in by_label.items():
        color = SEGMENT_COLORS.get(label, "#7f8c8d")
        ax.scatter(
            coords["x"],
            coords["y"],
            c=color,
            label=f"{label} (n={len(coords['x'])})",
            alpha=0.7,
            s=80,
            edgecolors="white",
            linewidth=1.5,
        )

    for c in centroids:
        ax.scatter(
            c["pca_x"],
            c["pca_y"],
            marker="*",
            c="black",
            s=300,
            edgecolors="white",
            linewidth=2,
            zorder=10,
        )
        ax.annotate(
            c.get("cluster_label", ""),
            (c["pca_x"], c["pca_y"]),
            textcoords="offset points",
            xytext=(8, 8),
            fontsize=9,
            fontweight="bold",
        )

    var_x = variance[0] * 100 if variance else 0
    var_y = variance[1] * 100 if len(variance) > 1 else 0
    ax.set_xlabel(f"PC1 ({var_x:.1f}% variance)", fontsize=11)
    ax.set_ylabel(f"PC2 ({var_y:.1f}% variance)", fontsize=11)
    ax.set_title(
        "Projection PCA des produits par segment de prix\n"
        "Étoiles noires = centroïdes des clusters",
        fontsize=13,
        fontweight="bold",
    )
    ax.legend(loc="best", fontsize=10, framealpha=0.9)
    ax.grid(True, alpha=0.3, linestyle="--")
    ax.axhline(y=0, color="gray", linewidth=0.5, alpha=0.5)
    ax.axvline(x=0, color="gray", linewidth=0.5, alpha=0.5)

    plt.tight_layout()
    plt.savefig(save_path, dpi=120, bbox_inches="tight")
    plt.close()
    print(f"[OK] Scatter PCA sauvegardé : {save_path}")


if __name__ == "__main__":
    import sys

    use_sqlite = "--sqlite" in sys.argv or "--real" in sys.argv
    if use_sqlite:
        from data_mining.pipeline import run_pipeline_from_sqlite

        print("=== Génération scatter PCA (SQLite local) ===")
        result = run_pipeline_from_sqlite()
        out_name = "pca_scatter_real.png"
    else:
        print("=== Génération scatter PCA (mock data) ===")
        result = run_pipeline_from_mock(seed=42)
        out_name = "pca_scatter_mock.png"

    plot_pca_scatter(result, OUTPUT_DIR / out_name)
    print(f"\nFichier généré : data_mining/output/{out_name}")
