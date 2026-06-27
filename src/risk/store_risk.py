"""Une todos los resultados de riesgo en la tabla final `ira_resultados`.

Fuentes:
    - ira_scores                  (spc, sep, sve, ira_score, ira_nivel)
    - anomaly_scores              (anomaly_score, is_anomaly)
    - predicciones_rendimiento    (rendimiento_predicho, importancia_top3)
    - predicciones_nnet           (rendimiento_nnet, nnet_ic_inf, nnet_ic_sup)
"""
from __future__ import annotations

import logging

from src.ingestion.load_duckdb import get_connection, table_exists

logger = logging.getLogger(__name__)

_TABLE = "ira_resultados"


def build(force: bool = False) -> None:
    """LEFT JOIN las tres tablas de riesgo en ira_resultados."""
    con = get_connection()

    if not force and table_exists(con, _TABLE):

        logger.info("...", _TABLE)

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
            p.importancia_top3,
            n.rendimiento_nnet,
            n.nnet_ic_inf,
            n.nnet_ic_sup
        FROM ira_scores i
        LEFT JOIN anomaly_scores a
            ON  i.codigo_municipio = a.codigo_municipio
            AND i.cultivo          = a.cultivo
            AND i.periodo          = a.periodo
        LEFT JOIN predicciones_rendimiento p
            ON  i.codigo_municipio = p.codigo_municipio
            AND i.cultivo          = p.cultivo
            AND i.periodo          = p.periodo
        LEFT JOIN predicciones_nnet n
            ON  i.codigo_municipio = n.codigo_municipio
            AND i.cultivo          = n.cultivo
            AND i.periodo          = n.periodo
    """
    con.execute(sql)
    (rows,) = con.execute(f"SELECT COUNT(*) FROM {_TABLE}").fetchone()
    logger.info("[store_risk] '%s' creada: %d filas.", _TABLE, rows)
    con.close()
