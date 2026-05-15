"""
Charge les produits P1 depuis MySQL (Django), PyMySQL direct, SQLite local ou CSV.

Retourne un DataFrame prêt pour preprocessing.clean_data / run_pipeline.

Source recommandée en production (alignée sur settings.py Django) :
    load_products_dataframe(source="django")
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DM_SCRAPING = ROOT / "DM_Scraping"
DEFAULT_SQLITE = DM_SCRAPING / "db.sqlite3"
TABLE_NAME = "Product"

COLUMN_MAPPING = {
    "titre_complet": "title",
    "prix": "price",
    "plateforme": "source",
    "search_query": "query",
    "created_at": "created_at",
}

PRODUCT_COLUMNS = (
    "id",
    "titre_complet",
    "prix",
    "devise",
    "plateforme",
    "note_vendeur",
    "nombre_avis",
    "etat",
    "type_vendeur",
    "img_link",
    "link",
    "search_query",
    "date_collecte",
    "id_recherche",
    "created_at",
    "user_id",
)


def map_product_columns(df_raw: pd.DataFrame) -> pd.DataFrame:
    """Renomme les colonnes P1 → pipeline et enrichit price avec devise si besoin."""
    df = df_raw.rename(columns=COLUMN_MAPPING).copy()

    if "price" in df.columns:
        df["price"] = df["price"].astype(object)

    for col in ("title", "price", "source", "query", "created_at"):
        if col not in df.columns:
            if col == "query":
                df[col] = "unknown"
            elif col == "created_at":
                df[col] = pd.Timestamp.now()
            elif col in ("title", "price"):
                raise ValueError(f"Colonne requise absente après mapping: {col}")

    if "devise" in df.columns and "price" in df.columns:
        mask = df["price"].notna() & df["devise"].notna()
        numeric_price = pd.to_numeric(df.loc[mask, "price"], errors="coerce")
        valid = numeric_price.notna()
        if valid.any():
            idx = numeric_price.index[valid]
            df.loc[idx, "price"] = (
                numeric_price.loc[valid].astype(str).str.strip()
                + " "
                + df.loc[idx, "devise"].astype(str).str.strip()
            )

    if "prix_valeur" not in df.columns and "price_value" not in df.columns:
        prix_col = "prix" if "prix" in df_raw.columns else "price"
        if prix_col in df_raw.columns:
            df["prix_valeur"] = pd.to_numeric(df_raw[prix_col], errors="coerce")
        elif "price" in df.columns:
            df["prix_valeur"] = pd.to_numeric(df["price"], errors="coerce")

    return df


def _ensure_django() -> None:
    """Configure Django (même settings que manage.py / MySQL)."""
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    if str(DM_SCRAPING) not in sys.path:
        sys.path.insert(0, str(DM_SCRAPING))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "DM_Scraping.settings")
    import django
    from django.apps import apps

    if apps.ready:
        return
    django.setup()


def _mysql_params_from_env() -> dict[str, Any]:
    """Fallback si Django settings indisponible (ex. rest_framework manquant)."""
    return {
        "host": os.environ.get("MYSQL_HOST", "localhost"),
        "port": int(os.environ.get("MYSQL_PORT", "3306")),
        "user": os.environ.get("MYSQL_USER", "root"),
        "password": os.environ.get("MYSQL_PASSWORD", ""),
        "database": os.environ.get("MYSQL_DATABASE", "Scraper"),
        "charset": "utf8mb4",
    }


def get_django_db_params() -> dict[str, Any]:
    """Lit les paramètres MySQL depuis Django settings (ou variables d'environnement)."""
    try:
        _ensure_django()
        from django.conf import settings

        db = settings.DATABASES["default"]
    except Exception:
        return _mysql_params_from_env()

    engine = db.get("ENGINE", "")
    if "mysql" not in engine:
        raise RuntimeError(
            f"Django ENGINE={engine!r} — attendu django.db.backends.mysql. "
            "Vérifiez DM_Scraping/DM_Scraping/settings.py."
        )
    return {
        "host": db.get("HOST") or "localhost",
        "port": int(db.get("PORT") or 3306),
        "user": db.get("USER"),
        "password": db.get("PASSWORD"),
        "database": db.get("NAME"),
        "charset": "utf8mb4",
    }


def load_from_django(
    user_id: int | None = None,
    search_query: str | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    """
    Charge Product via l'ORM Django (MySQL configuré dans settings.py).

    Même table / schéma que le backend P1 — pas de SQL dialecte SQLite.
    """
    _ensure_django()
    from Scraper.models import Product

    qs = Product.objects.all().order_by("-created_at")
    if user_id is not None:
        qs = qs.filter(user_id=user_id)
    if search_query:
        qs = qs.filter(search_query__icontains=search_query)
    if limit:
        qs = qs[:limit]

    rows = list(qs.values(*PRODUCT_COLUMNS))
    if not rows:
        raise ValueError("Aucun produit en base MySQL (table Product vide).")

    return map_product_columns(pd.DataFrame(rows))


def load_from_mysql(
    host: str | None = None,
    port: int | None = None,
    user: str | None = None,
    password: str | None = None,
    database: str | None = None,
) -> pd.DataFrame:
    """
    Charge Product via PyMySQL (sans passer par l'ORM).

    Par défaut, reprend les paramètres Django settings.
    """
    try:
        import pymysql
    except ImportError as exc:
        raise ImportError("PyMySQL requis : pip install PyMySQL") from exc

    params = get_django_db_params()
    if host is not None:
        params["host"] = host
    if port is not None:
        params["port"] = port
    if user is not None:
        params["user"] = user
    if password is not None:
        params["password"] = password
    if database is not None:
        params["database"] = database

    conn = pymysql.connect(
        host=params["host"],
        port=params["port"],
        user=params["user"],
        password=params["password"],
        database=params["database"],
        charset=params.get("charset", "utf8mb4"),
    )
    try:
        # Backticks pour MySQL si le nom de table est réservé / sensible à la casse
        df_raw = pd.read_sql_query(f"SELECT * FROM `{TABLE_NAME}`", conn)
    finally:
        conn.close()

    if df_raw.empty:
        raise ValueError(f"Table `{TABLE_NAME}` vide dans MySQL {params['database']}")

    return map_product_columns(df_raw)


def load_from_sqlite(db_path: str | Path | None = None) -> pd.DataFrame:
    """Lit la table Product depuis db.sqlite3 (dev local uniquement)."""
    path = Path(db_path) if db_path else DEFAULT_SQLITE
    if not path.exists():
        raise FileNotFoundError(f"Base SQLite introuvable: {path}")

    import sqlite3

    conn = sqlite3.connect(path)
    try:
        df_raw = pd.read_sql_query(f'SELECT * FROM "{TABLE_NAME}"', conn)
    finally:
        conn.close()

    if df_raw.empty:
        raise ValueError(f"Table {TABLE_NAME} vide dans {path}")

    return map_product_columns(df_raw)


def load_from_csv(csv_path: str | Path) -> pd.DataFrame:
    """Charge un export CSV équipe (colonnes P1)."""
    df_raw = pd.read_csv(csv_path)
    return map_product_columns(df_raw)


def load_products_dataframe(
    source: str = "django",
    path: str | Path | None = None,
    **kwargs: Any,
) -> pd.DataFrame:
    """
    Point d'entrée unifié.

    Parameters
    ----------
    source : {'django', 'mysql', 'sqlite', 'csv'}
        django = ORM + MySQL (production, aligné backend)
        mysql  = PyMySQL direct (même schéma, sans ORM)
        sqlite = fichier local dev
        csv    = export fichier
    """
    src = source.lower()
    if src == "django":
        return load_from_django(**kwargs)
    if src == "mysql":
        return load_from_mysql()
    if src == "sqlite":
        return load_from_sqlite(path)
    if src == "csv":
        if not path:
            raise ValueError("path requis pour source='csv'")
        return load_from_csv(path)
    raise ValueError(f"source inconnue: {source!r} — utiliser django|mysql|sqlite|csv")


def compare_schema_sqlite_vs_mysql() -> dict[str, Any]:
    """
    Compare les colonnes Product SQLite (si présent) vs attente schéma P1.
    Utile pour diagnostic intégration.
    """
    expected = set(PRODUCT_COLUMNS) - {"user_id"} | {"user_id"}
    report: dict[str, Any] = {
        "expected_columns": sorted(PRODUCT_COLUMNS),
        "sqlite": None,
        "mysql": None,
        "compatible": True,
        "notes": [],
    }

    if DEFAULT_SQLITE.exists():
        import sqlite3

        conn = sqlite3.connect(DEFAULT_SQLITE)
        cur = conn.execute(f'PRAGMA table_info("{TABLE_NAME}")')
        sqlite_cols = [r[1] for r in cur.fetchall()]
        conn.close()
        report["sqlite"] = sqlite_cols
        missing = set(PRODUCT_COLUMNS) - set(sqlite_cols)
        if missing:
            report["notes"].append(f"SQLite manque: {sorted(missing)}")

    try:
        params = get_django_db_params()
        if isinstance(params, dict) and "database" not in params:
            raise RuntimeError("params invalides")
        import pymysql

        conn = pymysql.connect(
            host=params["host"],
            port=params["port"],
            user=params["user"],
            password=params["password"],
            database=params["database"],
            charset="utf8mb4",
        )
        cur = conn.cursor()
        cur.execute(f"SHOW COLUMNS FROM `{TABLE_NAME}`")
        mysql_cols = [r[0] for r in cur.fetchall()]
        conn.close()
        report["mysql"] = mysql_cols
        missing = set(PRODUCT_COLUMNS) - set(mysql_cols)
        extra = set(mysql_cols) - set(PRODUCT_COLUMNS) - {"id"}
        if missing:
            report["compatible"] = False
            report["notes"].append(f"MySQL manque: {sorted(missing)}")
        if extra:
            report["notes"].append(f"MySQL colonnes en plus: {sorted(extra)}")
    except Exception as exc:
        report["mysql"] = f"non accessible: {exc}"
        report["notes"].append("MySQL non joignable — démarrer le serveur pour test complet")

    return report
