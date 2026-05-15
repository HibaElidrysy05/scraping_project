"""Tests de non-régression P2 (unittest, sans pytest obligatoire)."""

from __future__ import annotations

import unittest

from data_mining.association_rules import run_association_rules
from data_mining.load_from_db import map_product_columns
from data_mining.mock_data import get_mock_data
from data_mining.pipeline import run_pipeline_from_mock
from data_mining.preprocessing import clean_data
import pandas as pd


class TestMockPipeline(unittest.TestCase):
    def test_pipeline_mock_metrics(self):
        r = run_pipeline_from_mock(seed=42)
        self.assertEqual(r["status"], "done")
        self.assertEqual(r["rows_analysed"], 44)
        self.assertEqual(r["clustering"]["optimal_k"], 4)
        self.assertEqual(r["anomalies"]["total_confirmed"], 1)
        self.assertEqual(r["association_rules"]["total_rules"], 14)

    def test_association_apriori_comparison_present(self):
        cleaned = clean_data(get_mock_data(seed=42))
        rules = run_association_rules(cleaned)
        comp = rules.get("algorithm_comparison")
        self.assertIsNotNone(comp)
        self.assertIn("fpgrowth_itemsets", comp)
        self.assertIn("apriori_itemsets", comp)
        self.assertEqual(comp["primary_algorithm"], "fpgrowth")

    def test_p1_etat_from_column(self):
        raw = get_mock_data(seed=42).head(5).copy()
        raw["etat"] = "Neuf"
        raw["devise"] = "MAD"
        cleaned = clean_data(raw)
        self.assertTrue((cleaned["etat"] == "neuf").all())


class TestLoadFromDb(unittest.TestCase):
    def test_map_product_columns_keeps_p1_fields(self):
        df_raw = pd.DataFrame(
            {
                "titre_complet": ["Phone A"],
                "prix": [100.0],
                "plateforme": ["Jumia.ma"],
                "search_query": ["iphone"],
                "created_at": ["2026-05-15"],
                "devise": ["MAD"],
                "etat": ["Neuf"],
            }
        )
        mapped = map_product_columns(df_raw)
        self.assertEqual(mapped.loc[0, "title"], "Phone A")
        self.assertIn("devise", mapped.columns)
        self.assertIn("etat", mapped.columns)
        self.assertIn("100", str(mapped.loc[0, "price"]))


if __name__ == "__main__":
    unittest.main()
