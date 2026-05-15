"""
P2 — Data Mining & analyse (Market Research & Pricing).

Point d'entrée recommandé pour le test d'intégration :
    python -m data_mining.run_p2 all
"""

from data_mining.load_from_db import load_products_dataframe
from data_mining.pipeline import (
    export_pipeline_result,
    run_pipeline,
    run_pipeline_from_django,
    run_pipeline_from_mock,
    run_pipeline_from_mysql,
    run_pipeline_from_sqlite,
)

__all__ = [
    "run_pipeline",
    "run_pipeline_from_mock",
    "run_pipeline_from_sqlite",
    "run_pipeline_from_django",
    "run_pipeline_from_mysql",
    "load_products_dataframe",
    "export_pipeline_result",
]
