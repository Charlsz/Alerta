"""Variables económicas (Sub-índice de Vulnerabilidad Económica — SVE).

Fuente: tabla DuckDB `raw_insumos`.

Variables que construye (serie mensual nacional):
    insumos_nivel        — valor actual del índice
    insumos_anomalia_12m — desvío vs. media móvil 12 meses
    insumos_delta_3m     — cambio en los últimos 3 meses

Nota: el índice de insumos es nacional (no tiene desagregación municipal),
por lo que estas variables son iguales para todos los municipios en un periodo.
Se unen a la tabla maestra en store.py mediante el campo `periodo`.
"""
from __future__ import annotations

import logging

import pandas as pd

from src.ingestion.load_duckdb import get_connection

logger = logging.getLogger(__name__)

_TABLE = "features_vulnerabilidad"


def build(force: bool = False) -> None:
    """Genera la tabla `features_vulnerabilidad` en DuckDB."""
    con = get_connection()

    if not force:
        existing = con.execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = ?", [_TABLE]
        ).fetchone()[0]  # type: ignore[index]
        if existing:
            logger.info("[vulnerabilidad] Tabla '%s' ya existe, omitiendo.", _TABLE)
            con.close()
            return

    logger.info("[vulnerabilidad] Construyendo variables de insumos agrícolas...")

    # Leer tabla cruda y normalizar columnas
    df = con.execute("SELECT * FROM raw_insumos").df()
    df.columns = [c.lower().strip() for c in df.columns]

    # Detectar columna de fecha y de valor del índice
    fecha_col = next((c for c in df.columns if "fecha" in c or "periodo" in c or "mes" in c), None)
    valor_col = next((c for c in df.columns if "indice" in c or "valor" in c or "índice" in c), None)

    if not fecha_col or not valor_col:
        logger.error(
            "[vulnerabilidad] No se encontraron columnas fecha/valor en raw_insumos. "
            "Columnas disponibles: %s", list(df.columns)
        )
        con.close()
        return

    df = df[[fecha_col, valor_col]].rename(columns={fecha_col: "periodo", valor_col: "insumos_nivel"})
    df["periodo"] = pd.to_datetime(df["periodo"], errors="coerce").dt.to_period("M").dt.to_timestamp()
    df["insumos_nivel"] = pd.to_numeric(df["insumos_nivel"], errors="coerce")
    df = df.dropna().sort_values("periodo").reset_index(drop=True)

    # Media móvil 12 meses y anomalía
    df["insumos_media_12m"]    = df["insumos_nivel"].rolling(12, min_periods=6).mean()
    df["insumos_anomalia_12m"] = df["insumos_nivel"] - df["insumos_media_12m"]

    # Delta 3 meses
    df["insumos_delta_3m"] = df["insumos_nivel"].diff(3)

    result = df[["periodo", "insumos_nivel", "insumos_anomalia_12m", "insumos_delta_3m"]]

    con.execute(f"CREATE OR REPLACE TABLE {_TABLE} AS SELECT * FROM result")
    (rows,) = con.execute(f"SELECT COUNT(*) FROM {_TABLE}").fetchone()  # type: ignore[misc]
    logger.info("[vulnerabilidad] Tabla '%s' creada: %d filas.", _TABLE, rows)
    con.close()
