"""Variables climáticas (Sub-índice de Peligro Climático — SPC).

Fuente:
    - clean_precipitacion  (IDEAM precipitación)
    - clean_temperatura    (IDEAM temperatura máxima)
    - clean_humedad        (IDEAM humedad del aire)       ← nuevo
    - clean_presion        (IDEAM presión atmosférica)    ← nuevo
    - clean_tambiente      (IDEAM temperatura ambiente)  ← nuevo
    - estaciones_municipio (join espacial)

Variables que construye por municipio × periodo (mes):
    SPC originales (8 vars):
        precip_acum_7d, precip_acum_30d, precip_anomalia_30d,
        dias_secos_consecutivos, dias_lluvia_extrema,
        tmax_media_7d, tmax_anomalia_30d, dias_tmax_critica

    SPC nuevas (7 vars):
        humedad_media_30d, humedad_anomalia_30d,
        presion_media_30d, presion_anomalia_30d,
        tambiente_media_30d, tmin_media_30d,
        viento_media_30d
"""
from __future__ import annotations

import logging

import duckdb
import pandas as pd

from src.ingestion.load_duckdb import get_connection, table_exists

logger = logging.getLogger(__name__)

_TABLE = "features_clima"


# ─────────────────────────────────────────────────────────────────────────────
# Helper: join estación → municipio
# ─────────────────────────────────────────────────────────────────────────────

def _attach_municipio(table: str) -> str:
    """SQL que enriquece una tabla de observaciones con codigo_municipio."""
    return f"""
        SELECT o.*, e.codigo_municipio, e.nombre_municipio
        FROM {table} o
        JOIN estaciones_municipio e
          ON CAST(o.codigoestacion AS VARCHAR) = e.codigoestacion
        WHERE o.fechaobservacion IS NOT NULL
          AND o.valorobservado   IS NOT NULL
          AND e.codigo_municipio IS NOT NULL
    """


# ─────────────────────────────────────────────────────────────────────────────
# Precipitación
# ─────────────────────────────────────────────────────────────────────────────

# ponytail: anomaly vs historical monthly avg from IDEAM data (5-year baseline).
# CHIRPS replacement: no external dependency, works with data we already have.
def _build_precip(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    sql = f"""
        WITH obs AS ({_attach_municipio('clean_precipitacion')}),
        daily AS (
            SELECT
                codigo_municipio,
                CAST(fechaobservacion AS DATE)      AS fecha,
                SUM(CAST(valorobservado AS DOUBLE))  AS precip_dia
            FROM obs
            GROUP BY codigo_municipio, CAST(fechaobservacion AS DATE)
        ),
        p95 AS (
            SELECT codigo_municipio,
                   PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY precip_dia) AS umbral
            FROM daily
            GROUP BY codigo_municipio
        ),
        monthly AS (
            SELECT
                d.codigo_municipio,
                DATE_TRUNC('month', d.fecha)            AS periodo,
                EXTRACT(MONTH FROM d.fecha)              AS mes,
                SUM(d.precip_dia)                       AS precip_acum_30d,
                SUM(d.precip_dia) / 4.33                AS precip_acum_7d,
                COUNT(*) FILTER (WHERE d.precip_dia < 1) AS dias_secos_consecutivos,
                COUNT(*) FILTER (WHERE d.precip_dia > p.umbral) AS dias_lluvia_extrema
            FROM daily d
            LEFT JOIN p95 p ON d.codigo_municipio = p.codigo_municipio
            GROUP BY d.codigo_municipio, periodo, mes
        ),
        hist AS (
            SELECT
                codigo_municipio,
                mes,
                AVG(precip_acum_30d) AS hist_avg
            FROM monthly
            GROUP BY codigo_municipio, mes
        )
        SELECT
            m.codigo_municipio,
            m.periodo,
            m.precip_acum_30d,
            m.precip_acum_7d,
            m.dias_secos_consecutivos,
            m.dias_lluvia_extrema,
            m.precip_acum_30d - h.hist_avg AS precip_anomalia_30d
        FROM monthly m
        LEFT JOIN hist h
          ON m.codigo_municipio = h.codigo_municipio AND m.mes = h.mes
    """
    return con.execute(sql).df()


# ─────────────────────────────────────────────────────────────────────────────
# Temperatura máxima
# ─────────────────────────────────────────────────────────────────────────────

def _build_tmax(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    sql = f"""
        WITH obs AS ({_attach_municipio('clean_temperatura')}),
        monthly AS (
            SELECT
                codigo_municipio,
                DATE_TRUNC('month', CAST(fechaobservacion AS DATE)) AS periodo,
                AVG(CAST(valorobservado AS DOUBLE))                                  AS tmax_media_7d,
                AVG(CAST(valorobservado AS DOUBLE)) -
                    AVG(AVG(CAST(valorobservado AS DOUBLE)))
                        OVER (PARTITION BY codigo_municipio)         AS tmax_anomalia_30d,
                COUNT(*) FILTER (WHERE CAST(valorobservado AS DOUBLE) > 33.0) AS dias_tmax_critica
            FROM obs
            GROUP BY codigo_municipio, periodo
        )
        SELECT * FROM monthly
    """
    return con.execute(sql).df()


# ─────────────────────────────────────────────────────────────────────────────
# Humedad del aire  ← NUEVO
# ─────────────────────────────────────────────────────────────────────────────

def _build_humedad(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """Humedad relativa media y anomalía mensual por municipio."""
    if not table_exists(con, "clean_humedad"):
        logger.warning("[clima] clean_humedad no existe. Variables de humedad serán NaN.")
        return pd.DataFrame(columns=["codigo_municipio", "periodo",
                                     "humedad_media_30d", "humedad_anomalia_30d"])
    sql = f"""
        WITH obs AS ({_attach_municipio('clean_humedad')}),
        monthly AS (
            SELECT
                codigo_municipio,
                DATE_TRUNC('month', CAST(fechaobservacion AS DATE)) AS periodo,
                AVG(CAST(valorobservado AS DOUBLE))                                  AS humedad_media_30d
            FROM obs
            GROUP BY codigo_municipio, periodo
        )
        SELECT
            codigo_municipio,
            periodo,
            humedad_media_30d,
            humedad_media_30d -
                AVG(humedad_media_30d) OVER (PARTITION BY codigo_municipio) AS humedad_anomalia_30d
        FROM monthly
    """
    return con.execute(sql).df()


# ─────────────────────────────────────────────────────────────────────────────
# Presión atmosférica  ← NUEVO
# ─────────────────────────────────────────────────────────────────────────────

def _build_presion(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """Presión media y anomalía mensual por municipio."""
    if not table_exists(con, "clean_presion"):
        logger.warning("[clima] clean_presion no existe. Variables de presión serán NaN.")
        return pd.DataFrame(columns=["codigo_municipio", "periodo",
                                     "presion_media_30d", "presion_anomalia_30d"])
    sql = f"""
        WITH obs AS ({_attach_municipio('clean_presion')}),
        monthly AS (
            SELECT
                codigo_municipio,
                DATE_TRUNC('month', CAST(fechaobservacion AS DATE)) AS periodo,
                AVG(CAST(valorobservado AS DOUBLE))                                  AS presion_media_30d
            FROM obs
            GROUP BY codigo_municipio, periodo
        )
        SELECT
            codigo_municipio,
            periodo,
            presion_media_30d,
            presion_media_30d -
                AVG(presion_media_30d) OVER (PARTITION BY codigo_municipio) AS presion_anomalia_30d
        FROM monthly
    """
    return con.execute(sql).df()


# ─────────────────────────────────────────────────────────────────────────────
# Temperatura ambiente (T media + T mínima)  ← NUEVO
# ─────────────────────────────────────────────────────────────────────────────

def _build_tambiente(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """Temperatura ambiente media y mínima mensual por municipio."""
    if not table_exists(con, "clean_tambiente"):
        logger.warning("[clima] clean_tambiente no existe. Variables de T.ambiente serán NaN.")
        return pd.DataFrame(columns=["codigo_municipio", "periodo",
                                     "tambiente_media_30d", "tmin_media_30d"])
    sql = f"""
        WITH obs AS ({_attach_municipio('clean_tambiente')}),
        monthly AS (
            SELECT
                codigo_municipio,
                DATE_TRUNC('month', CAST(fechaobservacion AS DATE)) AS periodo,
                AVG(CAST(valorobservado AS DOUBLE))                                  AS tambiente_media_30d,
                MIN(CAST(valorobservado AS DOUBLE))                                  AS tmin_media_30d
            FROM obs
            GROUP BY codigo_municipio, periodo
        )
        SELECT * FROM monthly
    """
    return con.execute(sql).df()


# ponytail: CHIRPS removed. Anomaly computed in SQL via IDEAM historical avg.


# ─────────────────────────────────────────────────────────────────────────────
# Velocidad del viento  ← NUEVO
# ─────────────────────────────────────────────────────────────────────────────

def _build_viento(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """Velocidad del viento media mensual por municipio."""
    if not table_exists(con, "clean_viento"):
        logger.warning("[clima] clean_viento no existe. Variables de viento serán NaN.")
        return pd.DataFrame(columns=["codigo_municipio", "periodo",
                                     "viento_media_30d"])
    sql = f"""
        WITH obs AS ({_attach_municipio('clean_viento')})
        SELECT
            codigo_municipio,
            DATE_TRUNC('month', CAST(fechaobservacion AS DATE)) AS periodo,
            AVG(CAST(valorobservado AS DOUBLE)) AS viento_media_30d
        FROM obs
        GROUP BY codigo_municipio, periodo
    """
    return con.execute(sql).df()


# ─────────────────────────────────────────────────────────────────────────────
# Punto de entrada
# ─────────────────────────────────────────────────────────────────────────────

def build(force: bool = False) -> None:
    """Genera la tabla `features_clima` (14 variables SPC) en DuckDB."""
    con = get_connection()

    if not force:
        if table_exists(con, _TABLE):
            logger.info("[clima] Tabla '%s' ya existe, omitiendo.", _TABLE)
            con.close()
            return

    logger.info("[clima] Construyendo variables de precipitación...")
    precip = _build_precip(con)

    logger.info("[clima] Construyendo temperatura máxima...")
    tmax = _build_tmax(con)

    logger.info("[clima] Construyendo humedad del aire...")
    humedad = _build_humedad(con)

    logger.info("[clima] Construyendo presión atmosférica...")
    presion = _build_presion(con)

    logger.info("[clima] Construyendo temperatura ambiente...")
    tambiente = _build_tambiente(con)

    logger.info("[clima] Construyendo velocidad del viento...")
    viento = _build_viento(con)

    logger.info("[clima] Uniendo todas las variables climáticas...")
    df = (precip
          .merge(tmax,      on=["codigo_municipio", "periodo"], how="outer")
          .merge(humedad,   on=["codigo_municipio", "periodo"], how="outer")
          .merge(presion,   on=["codigo_municipio", "periodo"], how="outer")
          .merge(tambiente, on=["codigo_municipio", "periodo"], how="outer")
          .merge(viento,    on=["codigo_municipio", "periodo"], how="outer"))

    con.execute(f"CREATE OR REPLACE TABLE {_TABLE} AS SELECT * FROM df")
    (rows,) = con.execute(f"SELECT COUNT(*) FROM {_TABLE}").fetchone()  # type: ignore[misc]
    logger.info("[clima] Tabla '%s' creada: %d filas, 15 variables SPC.", _TABLE, rows)
    con.close()
