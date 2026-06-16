"""Variables climáticas (Sub-índice de Peligro Climático — SPC).

Fuente:
    - clean_precipitacion  (IDEAM precipitación)
    - clean_temperatura    (IDEAM temperatura máxima)
    - clean_humedad        (IDEAM humedad del aire)       ← nuevo
    - clean_presion        (IDEAM presión atmosférica)    ← nuevo
    - clean_tambiente      (IDEAM temperatura ambiente)  ← nuevo
    - estaciones_municipio (join espacial)
    - data/raw/chirps/     (NetCDF históricos para anomalías)

Variables que construye por municipio × periodo (mes):
    SPC originales (8 vars):
        precip_acum_7d, precip_acum_30d, precip_anomalia_30d,
        dias_secos_consecutivos, dias_lluvia_extrema,
        tmax_media_7d, tmax_anomalia_30d, dias_tmax_critica

    SPC nuevas (6 vars):
        humedad_media_30d, humedad_anomalia_30d,
        presion_media_30d, presion_anomalia_30d,
        tambiente_media_30d, tmin_media_30d
"""
from __future__ import annotations

import logging
from pathlib import Path

import duckdb
import pandas as pd

from config import config
from src.ingestion.load_duckdb import get_connection

logger = logging.getLogger(__name__)

_TABLE   = "features_clima"
_CHIRPS_DIR = Path(config.data_raw) / "chirps"


# ─────────────────────────────────────────────────────────────────────────────
# Helper: join estación → municipio
# ─────────────────────────────────────────────────────────────────────────────

def _attach_municipio(table: str) -> str:
    """SQL que enriquece una tabla de observaciones con codigo_municipio."""
    return f"""
        SELECT o.*, e.codigo_municipio, e.nombre_municipio
        FROM {table} o
        JOIN estaciones_municipio e
          ON TRIM(o.codigoestacion) = e.codigoestacion
        WHERE o.fechaobservacion IS NOT NULL
          AND o.valorobservado   IS NOT NULL
          AND e.codigo_municipio IS NOT NULL
    """


# ─────────────────────────────────────────────────────────────────────────────
# Precipitación
# ─────────────────────────────────────────────────────────────────────────────

def _build_precip(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    sql = f"""
        WITH obs AS ({_attach_municipio('clean_precipitacion')}),
        daily AS (
            SELECT
                codigo_municipio,
                CAST(fechaobservacion AS DATE)      AS fecha,
                SUM(valorobservado)                 AS precip_dia
            FROM obs
            GROUP BY codigo_municipio, CAST(fechaobservacion AS DATE)
        ),
        monthly AS (
            SELECT
                codigo_municipio,
                DATE_TRUNC('month', fecha)          AS periodo,
                SUM(precip_dia)                     AS precip_acum_30d,
                SUM(precip_dia) / 4.33              AS precip_acum_7d,
                COUNT(*) FILTER (WHERE precip_dia < 1) AS dias_secos_consecutivos,
                COUNT(*) FILTER (
                    WHERE precip_dia > PERCENTILE_CONT(0.95)
                        WITHIN GROUP (ORDER BY precip_dia)
                        OVER (PARTITION BY codigo_municipio)
                )                                   AS dias_lluvia_extrema
            FROM daily
            GROUP BY codigo_municipio, periodo
        )
        SELECT * FROM monthly
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
                AVG(valorobservado)                                  AS tmax_media_7d,
                AVG(valorobservado) -
                    AVG(AVG(valorobservado))
                        OVER (PARTITION BY codigo_municipio)         AS tmax_anomalia_30d,
                COUNT(*) FILTER (WHERE valorobservado > 33.0)        AS dias_tmax_critica
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
    if not _table_exists(con, "clean_humedad"):
        logger.warning("[clima] clean_humedad no existe. Variables de humedad serán NaN.")
        return pd.DataFrame(columns=["codigo_municipio", "periodo",
                                     "humedad_media_30d", "humedad_anomalia_30d"])
    sql = f"""
        WITH obs AS ({_attach_municipio('clean_humedad')}),
        monthly AS (
            SELECT
                codigo_municipio,
                DATE_TRUNC('month', CAST(fechaobservacion AS DATE)) AS periodo,
                AVG(valorobservado)                                  AS humedad_media_30d
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
    if not _table_exists(con, "clean_presion"):
        logger.warning("[clima] clean_presion no existe. Variables de presión serán NaN.")
        return pd.DataFrame(columns=["codigo_municipio", "periodo",
                                     "presion_media_30d", "presion_anomalia_30d"])
    sql = f"""
        WITH obs AS ({_attach_municipio('clean_presion')}),
        monthly AS (
            SELECT
                codigo_municipio,
                DATE_TRUNC('month', CAST(fechaobservacion AS DATE)) AS periodo,
                AVG(valorobservado)                                  AS presion_media_30d
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
    if not _table_exists(con, "clean_tambiente"):
        logger.warning("[clima] clean_tambiente no existe. Variables de T.ambiente serán NaN.")
        return pd.DataFrame(columns=["codigo_municipio", "periodo",
                                     "tambiente_media_30d", "tmin_media_30d"])
    sql = f"""
        WITH obs AS ({_attach_municipio('clean_tambiente')}),
        monthly AS (
            SELECT
                codigo_municipio,
                DATE_TRUNC('month', CAST(fechaobservacion AS DATE)) AS periodo,
                AVG(valorobservado)                                  AS tambiente_media_30d,
                MIN(valorobservado)                                  AS tmin_media_30d
            FROM obs
            GROUP BY codigo_municipio, periodo
        )
        SELECT * FROM monthly
    """
    return con.execute(sql).df()


# ─────────────────────────────────────────────────────────────────────────────
# Anomalía CHIRPS
# ─────────────────────────────────────────────────────────────────────────────

def _build_chirps_anomaly(precip_df: pd.DataFrame) -> pd.DataFrame:
    if not _CHIRPS_DIR.exists() or not any(_CHIRPS_DIR.rglob("*.nc")):
        logger.warning(
            "[clima] Archivos CHIRPS no encontrados en %s. "
            "precip_anomalia_30d será NaN hasta que se corra `run_ingestion --only chirps`.",
            _CHIRPS_DIR,
        )
        precip_df["precip_anomalia_30d"] = float("nan")
        return precip_df

    try:
        import numpy as np
        import xarray as xr

        nc_files      = sorted(_CHIRPS_DIR.rglob("*.nc"))
        baseline_files = [f for f in nc_files if int(f.parent.name) <= 2020]
        if not baseline_files:
            precip_df["precip_anomalia_30d"] = float("nan")
            return precip_df

        ds       = xr.open_mfdataset(baseline_files, combine="by_coords")
        baseline = ds["precip"].groupby("time.month").mean(dim="time")

        def _anomaly(row: pd.Series) -> float:
            mes = row["periodo"].month
            val = float(baseline.sel(month=mes).mean().values)
            return row["precip_acum_30d"] - val if pd.notna(row["precip_acum_30d"]) else float("nan")

        precip_df["precip_anomalia_30d"] = precip_df.apply(_anomaly, axis=1)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[clima] Error calculando anomalía CHIRPS: %s. Usando NaN.", exc)
        precip_df["precip_anomalia_30d"] = float("nan")

    return precip_df


# ─────────────────────────────────────────────────────────────────────────────
# Helper local
# ─────────────────────────────────────────────────────────────────────────────

def _table_exists(con: duckdb.DuckDBPyConnection, table: str) -> bool:
    return bool(
        con.execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = ?",
            [table],
        ).fetchone()[0]  # type: ignore[index]
    )


# ─────────────────────────────────────────────────────────────────────────────
# Punto de entrada
# ─────────────────────────────────────────────────────────────────────────────

def build(force: bool = False) -> None:
    """Genera la tabla `features_clima` (14 variables SPC) en DuckDB."""
    con = get_connection()

    if not force:
        if _table_exists(con, _TABLE):
            logger.info("[clima] Tabla '%s' ya existe, omitiendo.", _TABLE)
            con.close()
            return

    logger.info("[clima] Construyendo variables de precipitación...")
    precip = _build_precip(con)
    precip = _build_chirps_anomaly(precip)

    logger.info("[clima] Construyendo temperatura máxima...")
    tmax = _build_tmax(con)

    logger.info("[clima] Construyendo humedad del aire...")
    humedad = _build_humedad(con)

    logger.info("[clima] Construyendo presión atmosférica...")
    presion = _build_presion(con)

    logger.info("[clima] Construyendo temperatura ambiente...")
    tambiente = _build_tambiente(con)

    logger.info("[clima] Uniendo todas las variables climáticas...")
    df = (precip
          .merge(tmax,      on=["codigo_municipio", "periodo"], how="outer")
          .merge(humedad,   on=["codigo_municipio", "periodo"], how="outer")
          .merge(presion,   on=["codigo_municipio", "periodo"], how="outer")
          .merge(tambiente, on=["codigo_municipio", "periodo"], how="outer"))

    con.execute(f"CREATE OR REPLACE TABLE {_TABLE} AS SELECT * FROM df")
    (rows,) = con.execute(f"SELECT COUNT(*) FROM {_TABLE}").fetchone()  # type: ignore[misc]
    logger.info("[clima] Tabla '%s' creada: %d filas, 14 variables SPC.", _TABLE, rows)
    con.close()
