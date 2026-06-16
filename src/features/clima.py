"""Variables climáticas (Sub-índice de Peligro Climático — SPC).

Fuente:
    - raw_precipitacion  (IDEAM, últimos 5 años)
    - raw_temperatura    (IDEAM, últimos 5 años)
    - estaciones_municipio (join espacial)
    - data/raw/chirps/   (NetCDF históricos para anomalías)

Variables que construye por municipio × periodo (mes):
    precip_acum_7d, precip_acum_30d, precip_anomalia_30d,
    dias_secos_consecutivos, dias_lluvia_extrema,
    tmax_media_7d, tmax_anomalia_30d, dias_tmax_critica
"""
from __future__ import annotations

import logging
from pathlib import Path

import duckdb
import pandas as pd

from config import config
from src.ingestion.load_duckdb import get_connection

logger = logging.getLogger(__name__)

_TABLE = "features_clima"
_CHIRPS_DIR = Path(config.data_raw) / "chirps"


def _attach_municipio(con: duckdb.DuckDBPyConnection, table: str, fecha_col: str = "fechaobservacion") -> str:
    """Devuelve SQL que hace JOIN de una tabla de observaciones IDEAM con estaciones_municipio."""
    return f"""
        SELECT
            o.*,
            e.codigo_municipio,
            e.nombre_municipio
        FROM {table} o
        JOIN estaciones_municipio e
          ON TRIM(o.codigoestacion) = e.codigoestacion
        WHERE o.{fecha_col} IS NOT NULL
          AND o.valorobservado IS NOT NULL
          AND e.codigo_municipio IS NOT NULL
    """


def _build_precip(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """Construye variables de precipitación por municipio y mes."""
    sql = f"""
        WITH obs AS (
            {_attach_municipio(con, 'raw_precipitacion')}
        ),
        daily AS (
            SELECT
                codigo_municipio,
                CAST(fechaobservacion AS DATE)          AS fecha,
                SUM(CAST(valorobservado AS DOUBLE))     AS precip_dia
            FROM obs
            GROUP BY codigo_municipio, CAST(fechaobservacion AS DATE)
        ),
        monthly AS (
            SELECT
                codigo_municipio,
                DATE_TRUNC('month', fecha)              AS periodo,
                SUM(precip_dia)                         AS precip_acum_30d,
                -- acum 7d: promedio semanal como proxy (datos mensuales)
                SUM(precip_dia) / 4.33                  AS precip_acum_7d,
                -- días secos: días con precipitación < 1 mm
                COUNT(*) FILTER (WHERE precip_dia < 1)  AS dias_secos_mes,
                -- umbral lluvia extrema: percentil 95 calculado globalmente
                PERCENTILE_CONT(0.95) WITHIN GROUP
                    (ORDER BY precip_dia) OVER
                    (PARTITION BY codigo_municipio)     AS p95
            FROM daily
            GROUP BY codigo_municipio, periodo
        )
        SELECT
            codigo_municipio,
            periodo,
            precip_acum_30d,
            precip_acum_7d,
            dias_secos_mes                              AS dias_secos_consecutivos,
            COUNT(*) FILTER (
                WHERE precip_acum_30d / 30.0 > p95
            ) OVER
                (PARTITION BY codigo_municipio)        AS dias_lluvia_extrema
        FROM monthly
    """
    return con.execute(sql).df()


def _build_tmax(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """Construye variables de temperatura máxima por municipio y mes."""
    sql = f"""
        WITH obs AS (
            {_attach_municipio(con, 'raw_temperatura')}
        ),
        monthly AS (
            SELECT
                codigo_municipio,
                DATE_TRUNC('month', CAST(fechaobservacion AS DATE)) AS periodo,
                AVG(CAST(valorobservado AS DOUBLE))                  AS tmax_media_7d,
                -- anomalía simple: desvío respecto a la media global del municipio
                AVG(CAST(valorobservado AS DOUBLE)) -
                    AVG(AVG(CAST(valorobservado AS DOUBLE)))
                        OVER (PARTITION BY codigo_municipio)         AS tmax_anomalia_30d,
                -- días con Tmax > 33°C (umbral default; se refinará por cultivo en risk/)
                COUNT(*) FILTER (
                    WHERE CAST(valorobservado AS DOUBLE) > 33.0
                )                                                     AS dias_tmax_critica
            FROM obs
            GROUP BY codigo_municipio, periodo
        )
        SELECT * FROM monthly
    """
    return con.execute(sql).df()


def _build_chirps_anomaly(precip_df: pd.DataFrame) -> pd.DataFrame:
    """Calcula anomalía de precipitación vs. línea de base CHIRPS (1991–2020).

    Si los archivos CHIRPS no están descargados, retorna la columna como NaN
    y loguea un aviso. El resto del pipeline sigue funcionando sin esta variable.
    """
    if not _CHIRPS_DIR.exists() or not any(_CHIRPS_DIR.rglob("*.nc")):
        logger.warning(
            "[clima] Archivos CHIRPS no encontrados en %s. "
            "precip_anomalia_30d será NaN hasta que se corra `run_ingestion --only chirps`.",
            _CHIRPS_DIR,
        )
        precip_df["precip_anomalia_30d"] = float("nan")
        return precip_df

    try:
        import xarray as xr
        import numpy as np

        # Cargar todos los NetCDF CHIRPS (línea de base 1991-2020)
        nc_files = sorted(_CHIRPS_DIR.rglob("*.nc"))
        baseline_years = [f for f in nc_files if int(f.parent.name) <= 2020]

        if not baseline_years:
            precip_df["precip_anomalia_30d"] = float("nan")
            return precip_df

        ds = xr.open_mfdataset(baseline_years, combine="by_coords")
        # Media mensual histórica por mes del año (1..12)
        baseline = ds["precip"].groupby("time.month").mean(dim="time")

        def get_anomaly(row: pd.Series) -> float:
            mes = row["periodo"].month
            # Extraer valor del pixel más cercano a centroide del municipio
            # (aproximación; spatial.py ya hizo el join a nivel de estación)
            val = float(baseline.sel(month=mes).mean().values)
            return row["precip_acum_30d"] - val if pd.notna(row["precip_acum_30d"]) else float("nan")

        precip_df["precip_anomalia_30d"] = precip_df.apply(get_anomaly, axis=1)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[clima] Error calculando anomalía CHIRPS: %s. Usando NaN.", exc)
        precip_df["precip_anomalia_30d"] = float("nan")

    return precip_df


def build(force: bool = False) -> None:
    """Genera la tabla `features_clima` en DuckDB."""
    con = get_connection()

    if not force:
        existing = con.execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = ?", [_TABLE]
        ).fetchone()[0]  # type: ignore[index]
        if existing:
            logger.info("[clima] Tabla '%s' ya existe, omitiendo.", _TABLE)
            con.close()
            return

    logger.info("[clima] Construyendo variables de precipitación...")
    precip = _build_precip(con)
    precip = _build_chirps_anomaly(precip)

    logger.info("[clima] Construyendo variables de temperatura máxima...")
    tmax = _build_tmax(con)

    logger.info("[clima] Uniendo precipitación y temperatura por municipio-periodo...")
    df = precip.merge(tmax, on=["codigo_municipio", "periodo"], how="outer")

    con.execute(f"CREATE OR REPLACE TABLE {_TABLE} AS SELECT * FROM df")
    (rows,) = con.execute(f"SELECT COUNT(*) FROM {_TABLE}").fetchone()  # type: ignore[misc]
    logger.info("[clima] Tabla '%s' creada: %d filas.", _TABLE, rows)
    con.close()
