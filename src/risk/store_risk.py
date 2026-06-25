"""Une todos los resultados de riesgo en la tabla final `ira_resultados`.

Fuentes:
    - ira_scores                  (spc, sep, sve, ira_score, ira_nivel)
    - anomaly_scores              (anomaly_score, is_anomaly)
    - predicciones_rendimiento    (rendimiento_predicho, importancia_top3)
"""
from __future__ import annotations

import logging

import pandas as pd

from src.ingestion.load_duckdb import get_connection

logger = logging.getLogger(__name__)

_TABLE = "ira_resultados"


def build(force: bool = False) -> None:
    """LEFT JOIN las tres tablas de riesgo en ira_resultados."""
    con = get_connection()

    if not force:
        exists = con.execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = ?",
            [_TABLE],
        ).fetchone()[0]
        if exists:
            logger.info("[store_risk] '%s' ya existe, omitiendo.", _TABLE)
            con.close()
            return

    logger.info("[store_risk] Uniendo resultados de riesgo...")

    sql = f"""
        CREATE OR REPLACE TABLE {_TABLE} AS
        SELECT
            i.codigo_municipio,
            i.cultivo,
            i.periodo,
            i.spc,
            i.sep,
            i.sve,
            i.ira_score,
            i.ira_nivel,
            a.anomaly_score,
            a.is_anomaly,
            p.rendimiento_predicho,
            p.rendimiento_ic_inf,
            p.rendimiento_ic_sup,
            p.importancia_top3
        FROM ira_scores i
        LEFT JOIN anomaly_scores a
            ON  i.codigo_municipio = a.codigo_municipio
            AND i.cultivo          = a.cultivo
            AND i.periodo          = a.periodo
        LEFT JOIN predicciones_rendimiento p
            ON  i.codigo_municipio = p.codigo_municipio
            AND i.cultivo          = p.cultivo
            AND i.periodo          = p.periodo
    """
    con.execute(sql)
    (rows,) = con.execute(f"SELECT COUNT(*) FROM {_TABLE}").fetchone()
    logger.info("[store_risk] '%s' creada: %d filas.", _TABLE, rows)
    con.close()
