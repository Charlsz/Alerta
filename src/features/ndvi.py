"""Variables de NDVI (índice de vegetación) por municipio.

Fuente: HDX — MODIS NDVI subnational para Colombia (2022–2026).
Variables: ndvi_media_30d, ndvi_anomalia_30d.
"""
from __future__ import annotations

import logging

import pandas as pd

from src.ingestion.load_duckdb import get_connection, table_exists

logger = logging.getLogger(__name__)

_TABLE = "features_ndvi"


def build(force: bool = False) -> None:
    con = get_connection()
    if not force and table_exists(con, _TABLE):
        logger.info("[ndvi] Tabla '%s' ya existe, omitiendo.", _TABLE)
        con.close()
        return

    if not table_exists(con, "clean_ndvi"):
        logger.warning("[ndvi] clean_ndvi no existe.")
        con.close()
        return

    df = con.execute("""
        SELECT
            codigo_municipio,
            DATE_TRUNC('month', fecha) AS periodo,
            AVG(ndvi) AS ndvi_media_30d,
            AVG(ndvi_anomalia) AS ndvi_anomalia_30d
        FROM clean_ndvi
        GROUP BY codigo_municipio, periodo
    """).df()

    con.execute(f"CREATE OR REPLACE TABLE {_TABLE} AS SELECT * FROM df")
    (rows,) = con.execute(f"SELECT COUNT(*) FROM {_TABLE}").fetchone()
    logger.info("[ndvi] Tabla '%s' creada: %d filas.", _TABLE, rows)
    con.close()
