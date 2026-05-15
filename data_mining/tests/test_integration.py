"""Tests d'intégration P2 ↔ Django/MySQL (skip si BDD indisponible)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DM = ROOT / "DM_Scraping"


def _mysql_available() -> bool:
    try:
        from data_mining.load_from_db import get_django_db_params
        import pymysql

        p = get_django_db_params()
        conn = pymysql.connect(
            host=p["host"],
            port=p["port"],
            user=p["user"],
            password=p["password"],
            database=p["database"],
            charset="utf8mb4",
            connect_timeout=3,
        )
        conn.close()
        return True
    except Exception:
        return False


def _django_products_count() -> int:
    from data_mining.load_from_db import load_from_django

    _ensure = __import__("data_mining.load_from_db", fromlist=["_ensure_django"])
    _ensure._ensure_django()
    from Scraper.models import Product

    return Product.objects.count()


class TestSchemaCompatibility(unittest.TestCase):
    def test_map_matches_django_model_fields(self):
        from data_mining.load_from_db import map_product_columns, PRODUCT_COLUMNS

        row = {
            "titre_complet": "Test Phone",
            "prix": 999.0,
            "devise": "MAD",
            "plateforme": "Jumia.ma",
            "search_query": "iphone",
            "created_at": "2026-01-01",
            "etat": "Neuf",
        }
        df = map_product_columns(pd.DataFrame([row]))
        self.assertEqual(df.loc[0, "title"], "Test Phone")
        self.assertEqual(df.loc[0, "source"], "Jumia.ma")
        self.assertIn("etat", df.columns)
        self.assertIn("titre_complet", PRODUCT_COLUMNS)

    def test_no_sqlite_specific_sql_in_loaders(self):
        """Le chemin django/mysql ne doit pas importer sqlite3."""
        import data_mining.load_from_db as ldb

        with open(ldb.__file__, encoding="utf-8") as f:
            src = f.read()
        self.assertIn("load_from_django", src)
        self.assertIn("load_from_mysql", src)
        # sqlite isolé dans load_from_sqlite uniquement
        django_block = src.split("def load_from_django")[1].split("def load_from_mysql")[0]
        self.assertNotIn("sqlite3", django_block)


@unittest.skipUnless(DM.exists(), "DM_Scraping absent")
class TestDjangoIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        if str(DM) not in sys.path:
            sys.path.insert(0, str(DM))

    def test_django_settings_uses_mysql(self):
        from data_mining.load_from_db import get_django_db_params

        try:
            params = get_django_db_params()
        except Exception as exc:
            self.skipTest(f"Django settings indisponible: {exc}")
        self.assertIn("database", params)
        self.assertEqual(params["database"], "Scraper")

    @unittest.skipUnless(_mysql_available(), "MySQL non accessible")
    def test_load_from_mysql_returns_dataframe(self):
        from data_mining.load_from_db import load_from_mysql

        df = load_from_mysql()
        self.assertGreater(len(df), 0)
        self.assertIn("title", df.columns)
        self.assertIn("price", df.columns)

    @unittest.skipUnless(_mysql_available(), "MySQL non accessible")
    def test_load_from_django_matches_mysql_row_count(self):
        from data_mining.load_from_db import load_from_django, load_from_mysql

        n = _django_products_count()
        if n == 0:
            self.skipTest("Table Product vide")
        df_orm = load_from_django(limit=min(n, 500))
        df_sql = load_from_mysql()
        self.assertEqual(len(df_orm), min(n, 500))
        self.assertEqual(len(df_sql), n)

    @unittest.skipUnless(_mysql_available(), "MySQL non accessible")
    def test_pipeline_from_django_runs(self):
        from data_mining.pipeline import run_pipeline_from_django

        if _django_products_count() == 0:
            self.skipTest("Table Product vide")
        result = run_pipeline_from_django(limit=50)
        self.assertIn(result["status"], ("done", "partial", "failed"))
        self.assertGreaterEqual(result["rows_analysed"], 1)


class TestAnalyticsApiContract(unittest.TestCase):
    """Structure JSON attendue par le frontend (sans serveur HTTP)."""

    def test_pipeline_result_keys_for_api(self):
        from data_mining.pipeline import run_pipeline_from_mock

        r = run_pipeline_from_mock(seed=42)
        for key in (
            "status",
            "rows_analysed",
            "stats",
            "clustering",
            "anomalies",
            "association_rules",
            "pca",
            "warnings",
        ):
            self.assertIn(key, r)


if __name__ == "__main__":
    unittest.main()
