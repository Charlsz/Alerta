"""Variables de producción agrícola (Sub-índice de Exposición Productiva — SEP).

Fuente: tablas DuckDB `raw_eva` y `raw_eva_calendario`.

Variables que construye:
    area_sembrada, area_cosechada, rendimiento_promedio, rendimiento_cv,
    participacion_municipal, fase_fenologica
"""
from __future__ import annotations

import logging

import duckdb
import pandas as pd

from src.ingestion.load_duckdb import get_connection

logger = logging.getLogger(__name__)

_TABLE = "features_produccion"


def _build_rendimiento(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """Agrega EVA por municipio y cultivo: rendimiento promedio y CV histórico."""
    df = con.execute("""
        SELECT
            LOWER(TRIM(cultivo))            AS cultivo,
            TRIM(codigo_municipio)          AS codigo_municipio,
            AVG(CAST(rendimiento AS DOUBLE)) AS rendimiento_promedio,
            -- CV = desv_std / media (0 si media es 0)
            CASE
                WHEN AVG(CAST(rendimiento AS DOUBLE)) > 0
                THEN STDDEV(CAST(rendimiento AS DOUBLE)) / AVG(CAST(rendimiento AS DOUBLE))
                ELSE 0
            END                             AS rendimiento_cv,
            SUM(CAST(area_sembrada  AS DOUBLE)) AS area_sembrada,
            SUM(CAST(area_cosechada AS DOUBLE)) AS area_cosechada
        FROM raw_eva
        WHERE rendimiento    IS NOT NULL
          AND codigo_municipio IS NOT NULL
          AND cultivo          IS NOT NULL
        GROUP BY cultivo, codigo_municipio
    """).df()
    return df


def _build_participacion(df: pd.DataFrame) -> pd.DataFrame:
    """Calcula la participación del municipio en el área nacional por cultivo."""
    area_nacional = df.groupby("cultivo")["area_sembrada"].transform("sum")
    df["participacion_municipal"] = df["area_sembrada"] / area_nacional.replace(0, float("nan"))
    return df


def _build_fase_fenologica(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """Extrae los meses de siembra y cosecha por cultivo desde EVA Calendario."""
    try:
        df = con.execute("""
            SELECT
                LOWER(TRIM(cultivo))        AS cultivo,
                TRIM(codigo_municipio)      AS codigo_municipio,
                CAST(mes_siembra  AS INT)   AS mes_siembra,
                CAST(mes_cosecha  AS INT)   AS mes_cosecha
            FROM raw_eva_calendario
            WHERE cultivo IS NOT NULL
        """).df()
    except Exception:  # noqa: BLE001
        logger.warning("[produccion] raw_eva_calendario no disponible, fase_fenologica = NULL.")
        return pd.DataFrame(columns=["cultivo", "codigo_municipio", "mes_siembra", "mes_cosecha"])
    return df


def build(force: bool = False) -> None:
    """Genera la tabla `features_produccion` en DuckDB."""
    con = get_connection()

    if not force:
        existing = con.execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = ?", [_TABLE]
        ).fetchone()[0]  # type: ignore[index]
        if existing:
            logger.info("[produccion] Tabla '%s' ya existe, omitiendo.", _TABLE)
            con.close()
            return

    logger.info("[produccion] Construyendo variables EVA...")
    df = _build_rendimiento(con)
    df = _build_participacion(df)

    fenologica = _build_fase_fenologica(con)
    if not fenologica.empty:
        df = df.merge(fenologica, on=["cultivo", "codigo_municipio"], how="left")
    else:
        df["mes_siembra"] = None
        df["mes_cosecha"] = None

    con.execute(f"CREATE OR REPLACE TABLE {_TABLE} AS SELECT * FROM df")
    (rows,) = con.execute(f"SELECT COUNT(*) FROM {_TABLE}").fetchone()  # type: ignore[misc]
    logger.info("[produccion] Tabla '%s' creada: %d filas.", _TABLE, rows)
    con.close()
