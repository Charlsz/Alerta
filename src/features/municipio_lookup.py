"""Tabla de homologación nombre_municipio → codigo_municipio.

Fuentes:
  - clean_estaciones (asignación espacial de estaciones IDEAM a municipio)
  - IGAC municipios.gpkg (capa oficial DANE)
"""
from __future__ import annotations

import logging
import unicodedata
from pathlib import Path

import duckdb
import geopandas as gpd
import pandas as pd

from config import config
from src.ingestion.load_duckdb import get_connection, table_exists

logger = logging.getLogger(__name__)

_TABLE = "municipio_lookup"


def normalize_name(s: str) -> str:
    """Remove accents, uppercase, strip whitespace."""
    s = unicodedata.normalize("NFD", s.upper().strip())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def _build_lookup_df(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """Build deduplicated (normalized_name, codigo_municipio) from both sources."""
    records: list[tuple[str, str]] = []

    try:
        rows = con.execute("""
            SELECT DISTINCT nombre_municipio, codigo_municipio
            FROM clean_estaciones
            WHERE codigo_municipio IS NOT NULL
              AND nombre_municipio IS NOT NULL
              AND TRIM(nombre_municipio) != ''
        """).fetchall()
        records.extend((normalize_name(r[0]), r[1]) for r in rows)
        logger.info("[municipio_lookup] %d desde clean_estaciones", len(rows))
    except Exception as exc:
        logger.warning("[municipio_lookup] Error clean_estaciones: %s", exc)

    gpkg = Path(config.data_raw) / "municipios.gpkg"
    if gpkg.exists():
        try:
            gdf = gpd.read_file(gpkg, layer="municipios")
            if "nombre_municipio" in gdf.columns and "codigo_municipio" in gdf.columns:
                pairs = gdf[["nombre_municipio", "codigo_municipio"]].dropna().drop_duplicates()
                records.extend(
                    (normalize_name(r["nombre_municipio"]), r["codigo_municipio"])
                    for _, r in pairs.iterrows()
                )
                logger.info("[municipio_lookup] %d desde IGAC", len(pairs))
        except Exception as exc:
            logger.warning("[municipio_lookup] Error IGAC: %s", exc)
    else:
        logger.warning("[municipio_lookup] %s no existe", gpkg)

    df = pd.DataFrame(records, columns=["normalized_name", "codigo_municipio"])
    return df.drop_duplicates(subset=["normalized_name", "codigo_municipio"]).dropna()


def build(force: bool = False) -> None:
    """Create or replace municipio_lookup table in DuckDB."""
    con = get_connection()

    if not force and table_exists(con, _TABLE):
        logger.info("[municipio_lookup] %s ya existe, omitiendo.", _TABLE)
        con.close()
        return

    df = _build_lookup_df(con)
    if df.empty:
        logger.warning("[municipio_lookup] Sin datos para poblar.")
        con.close()
        return

    con.execute(f"CREATE TABLE {_TABLE} (normalized_name VARCHAR, codigo_municipio VARCHAR)")
    con.executemany(
        f"INSERT INTO {_TABLE} (normalized_name, codigo_municipio) VALUES (?, ?)",
        df.itertuples(index=False),
    )
    (rows,) = con.execute(f"SELECT COUNT(*) FROM {_TABLE}").fetchone()
    logger.info("[municipio_lookup] Tabla %s: %d filas.", _TABLE, rows)
    con.close()


def run(force: bool = False) -> None:
    """Build lookup and assign codigo_municipio to IDEAM clean tables."""
    con = get_connection()
    build(force=force)

    ideam_tables = [
        "clean_precipitacion",
        "clean_temperatura",
        "clean_humedad",
        "clean_presion",
        "clean_tambiente",
    ]

    for tbl in ideam_tables:
        if not table_exists(con, tbl):
            continue

        con.execute(f"ALTER TABLE {tbl} ADD COLUMN IF NOT EXISTS codigo_municipio VARCHAR")

        # Build per-table mapping: distinct municipio → codigo_municipio
        distinct = [
            r[0] for r in con.execute(
                f"SELECT DISTINCT TRIM(municipio) FROM {tbl} WHERE municipio IS NOT NULL"
            ).fetchall()
        ]

        mapping_rows = []
        for name in distinct:
            norm = normalize_name(name)
            code = con.execute(
                f"SELECT codigo_municipio FROM {_TABLE} WHERE normalized_name = ? LIMIT 1",
                [norm],
            ).fetchone()
            if code:
                mapping_rows.append((norm, name, code[0]))

        if not mapping_rows:
            continue

        # Write mapping to temp table and UPDATE with a single JOIN
        tmp = f"_tmp_{tbl}"
        con.execute(f"CREATE TEMP TABLE {tmp} (municipio VARCHAR, codigo_municipio VARCHAR)")
        con.executemany(
            f"INSERT INTO {tmp} (municipio, codigo_municipio) VALUES (?, ?)",
            [(r[1], r[2]) for r in mapping_rows],
        )

        con.execute(f"""
            UPDATE {tbl} AS t
            SET codigo_municipio = m.codigo_municipio
            FROM {tmp} AS m
            WHERE TRIM(t.municipio) = m.municipio
              AND t.codigo_municipio IS NULL
        """)

        (updated,) = con.execute(
            f"SELECT COUNT(*) FROM {tbl} WHERE codigo_municipio IS NOT NULL"
        ).fetchone()
        (total,) = con.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()
        logger.info(
            "[municipio_lookup] %s: %d / %d con codigo_municipio", tbl, updated, total
        )

    con.close()
