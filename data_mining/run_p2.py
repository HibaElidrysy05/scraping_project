"""
Point d'entrée unique P2 — test d'intégration projet.

Usage:
    python -m data_mining.run_p2 check     # imports + dépendances
    python -m data_mining.run_p2 mock      # pipeline mock (démo soutenance)
    python -m data_mining.run_p2 sqlite    # pipeline sur db.sqlite3 local (dev)
    python -m data_mining.run_p2 mysql     # pipeline sur MySQL (settings Django)
    python -m data_mining.run_p2 django    # idem via ORM Django
    python -m data_mining.run_p2 schema    # compare schéma SQLite vs MySQL
    python -m data_mining.run_p2 pca       # scatter PCA (mock)
    python -m data_mining.run_p2 test      # tests unitaires
    python -m data_mining.run_p2 all       # tout (recommandé avant big test)
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = Path(__file__).resolve().parent / "output"
DEFAULT_SQLITE = ROOT / "DM_Scraping" / "db.sqlite3"

MOCK_EXPECT = {
    "status": "done",
    "rows_analysed": 44,
    "optimal_k": 4,
    "total_rules": 14,
    "total_anomalies": 1,
}


def _log(msg: str) -> None:
    try:
        print(msg, flush=True)
    except UnicodeEncodeError:
        enc = sys.stdout.encoding or "utf-8"
        print(msg.encode(enc, errors="replace").decode(enc, errors="replace"), flush=True)


def cmd_check() -> int:
    _log("=== P2 health check ===")
    errors = []

    for mod in (
        "pandas",
        "numpy",
        "sklearn",
        "mlxtend",
        "matplotlib",
    ):
        try:
            __import__(mod)
            _log(f"  [OK] {mod}")
        except ImportError:
            _log(f"  [FAIL] {mod} manquant")
            errors.append(mod)

    if DEFAULT_SQLITE.exists():
        conn = sqlite3.connect(DEFAULT_SQLITE)
        try:
            n = conn.execute('SELECT COUNT(*) FROM "Product"').fetchone()[0]
            plats = conn.execute(
                'SELECT plateforme, COUNT(*) FROM "Product" GROUP BY plateforme'
            ).fetchall()
            _log(f"  [OK] SQLite {DEFAULT_SQLITE.name} : {n} lignes — {plats}")
        finally:
            conn.close()
    else:
        _log(f"  [INFO] Pas de {DEFAULT_SQLITE} (mock seul pour le big test)")

    if errors:
        _log("\nInstaller : pip install pandas numpy scikit-learn mlxtend matplotlib")
        return 1
    _log("\n[OK] Environnement P2 prêt")
    return 0


def cmd_mock(export: bool = True) -> int:
    from data_mining.pipeline import export_pipeline_result, run_pipeline_from_mock

    _log("=== Pipeline MOCK (seed=42) ===")
    result = run_pipeline_from_mock(seed=42)

    ok = (
        result["status"] == MOCK_EXPECT["status"]
        and result["rows_analysed"] == MOCK_EXPECT["rows_analysed"]
        and result["clustering"]["optimal_k"] == MOCK_EXPECT["optimal_k"]
        and result["association_rules"]["total_rules"] == MOCK_EXPECT["total_rules"]
        and result["anomalies"]["total_confirmed"] == MOCK_EXPECT["total_anomalies"]
    )

    _log(f"\nStatus={result['status']} rows={result['rows_analysed']} "
         f"K={result['clustering']['optimal_k']} rules={result['association_rules']['total_rules']}")

    if export:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        path = OUTPUT_DIR / "pipeline_mock.json"
        export_pipeline_result(result, str(path))
        _log(f"Export : {path}")

    if not ok:
        _log("[FAIL] Métriques mock différentes des valeurs de référence")
        return 1
    _log("[OK] Pipeline mock validé")
    return 0


def cmd_mysql() -> int:
    from data_mining.pipeline import export_pipeline_result, run_pipeline_from_mysql

    _log("=== Pipeline MYSQL (PyMySQL + settings Django) ===")
    try:
        result = run_pipeline_from_mysql()
    except Exception as exc:
        _log(f"[SKIP/FAIL] MySQL : {exc}")
        return 0 if "non accessible" in str(exc).lower() or "connect" in str(exc).lower() else 1

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    export_pipeline_result(result, str(OUTPUT_DIR / "pipeline_mysql.json"))
    _log(f"Status={result['status']} rows={result['rows_analysed']}")
    _log(f"Export : {OUTPUT_DIR / 'pipeline_mysql.json'}")
    return 0 if result["status"] in ("done", "partial") else 1


def cmd_django() -> int:
    from data_mining.pipeline import export_pipeline_result, run_pipeline_from_django

    _log("=== Pipeline DJANGO ORM (MySQL) ===")
    try:
        result = run_pipeline_from_django()
    except Exception as exc:
        _log(f"[SKIP/FAIL] Django/MySQL : {exc}")
        return 0 if "connect" in str(exc).lower() or "vide" in str(exc).lower() else 1

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    export_pipeline_result(result, str(OUTPUT_DIR / "pipeline_django.json"))
    _log(f"Status={result['status']} rows={result['rows_analysed']}")
    return 0 if result["status"] in ("done", "partial") else 1


def cmd_schema() -> int:
    import json
    from data_mining.load_from_db import compare_schema_sqlite_vs_mysql

    _log("=== Comparaison schéma Product ===")
    report = compare_schema_sqlite_vs_mysql()
    _log(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report.get("compatible", True) else 1


def cmd_sqlite() -> int:
    from data_mining.pipeline import export_pipeline_result, run_pipeline_from_sqlite

    if not DEFAULT_SQLITE.exists():
        _log(f"[SKIP] {DEFAULT_SQLITE} introuvable")
        return 0

    _log("=== Pipeline SQLITE local ===")
    try:
        result = run_pipeline_from_sqlite()
    except Exception as exc:
        _log(f"[FAIL] {exc}")
        return 1

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    export_pipeline_result(result, str(OUTPUT_DIR / "pipeline_sqlite.json"))
    _log(f"Status={result['status']} rows={result['rows_analysed']}")
    _log(f"Export : {OUTPUT_DIR / 'pipeline_sqlite.json'}")
    _log("[OK] Pipeline SQLite terminé")
    return 0 if result["status"] in ("done", "partial") else 1


def cmd_pca(use_sqlite: bool = False) -> int:
    from data_mining.pipeline import run_pipeline_from_mock, run_pipeline_from_sqlite
    from data_mining.visualize_pca import plot_pca_scatter

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if use_sqlite and DEFAULT_SQLITE.exists():
        _log("=== PCA scatter (SQLite) ===")
        result = run_pipeline_from_sqlite()
        out = OUTPUT_DIR / "pca_scatter_real.png"
    else:
        _log("=== PCA scatter (mock) ===")
        result = run_pipeline_from_mock(seed=42)
        out = OUTPUT_DIR / "pca_scatter_mock.png"

    plot_pca_scatter(result, out)
    return 0


def cmd_test() -> int:
    _log("=== Tests unitaires P2 ===")
    loader = unittest.TestLoader()
    suite = loader.discover("data_mining.tests", pattern="test_*.py")
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return 0 if result.wasSuccessful() else 1


def cmd_all() -> int:
    code = 0
    for name, fn in (
        ("check", cmd_check),
        ("schema", cmd_schema),
        ("test", cmd_test),
        ("mock", cmd_mock),
        ("django", cmd_django),
        ("mysql", cmd_mysql),
        ("sqlite", cmd_sqlite),
        ("pca", lambda: cmd_pca(False)),
    ):
        _log(f"\n{'=' * 60}\n>>> {name.upper()}\n{'=' * 60}")
        if fn() != 0:
            code = 1
    _log(f"\n{'=' * 60}")
    _log("RÉSULTAT GLOBAL : " + ("OK" if code == 0 else "ÉCHEC — voir logs ci-dessus"))
    return code


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="P2 Data Mining — test d'intégration")
    parser.add_argument(
        "command",
        nargs="?",
        default="all",
        choices=("check", "mock", "sqlite", "mysql", "django", "schema", "pca", "test", "all"),
        help="commande (défaut: all)",
    )
    parser.add_argument(
        "--sqlite-pca",
        action="store_true",
        help="avec 'pca' : utiliser SQLite au lieu du mock",
    )
    args = parser.parse_args(argv)

    commands = {
        "check": cmd_check,
        "mock": cmd_mock,
        "sqlite": cmd_sqlite,
        "mysql": cmd_mysql,
        "django": cmd_django,
        "schema": cmd_schema,
        "pca": lambda: cmd_pca(args.sqlite_pca),
        "test": cmd_test,
        "all": cmd_all,
    }
    return commands[args.command]()


if __name__ == "__main__":
    sys.exit(main())
