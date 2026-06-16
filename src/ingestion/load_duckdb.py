"""Carga los archivos Parquet de data/raw/ a tablas en DuckDB.

Este módulo es el puente entre la capa de ingesta (data/raw/*.parquet)
y el motor analítico (data/alerta.duckdb).

Cada función crea o reemplaza una tabla. El esquema se infiere
desde el Parquet; la limpieza de tipos ocurre en src/features/.
"""
from __future__ import annotations

import logging
from pathlib import Path

import duckdb

from config import config

logger = logging.getLogger(__name__)


def get_connection() -> duckdb.DuckDBPyConnection:
    """Abre (o crea) el archivo DuckDB y carga la extensión espacial."""
    config.ensure_dirs()
    con = duckdb.connect(config.duckdb_path)
    con.execute("INSTALL spatial; LOAD spatial;")
    return con


def _load_parquet(con: duckdb.DuckDBPyConnection, parquet_path: Path, table: str) -> int:
    """Lee un Parquet y lo carga en DuckDB como tabla. Retorna número de filas."""
    if not parquet_path.exists():
        logger.warning("[DuckDB] No existe %s, omitiendo tabla %s.", parquet_path, table)
        return 0
    con.execute(f"""
        CREATE OR REPLACE TABLE {table} AS
        SELECT * FROM read_parquet('{parquet_path}')
    """)
    (rows,) = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()  # type: ignore[misc]
    logger.info("[DuckDB] Tabla %-35s %d filas", f"'{table}'", rows)
    return rows


def run(force: bool = False) -> None:  # noqa: ARG001  (force reservado para compatibilidad)
    """Carga todos los Parquet crudos a DuckDB.

    Las tablas se crean con CREATE OR REPLACE, por lo que siempre
    reflejan el último estado de data/raw/.
    """
    con = get_connection()
    raw = Path(config.data_raw)

    tables = [
        (raw / "ideam_estaciones.parquet", "raw_estaciones"),
        (raw / "eva.parquet",              "raw_eva"),
        (raw / "eva_vista.parquet",        "raw_eva_vista"),
        (raw / "eva_calendario.parquet",   "raw_eva_calendario"),
        (raw / "insumos.parquet",          "raw_insumos"),
        (raw / "ideam_precip.parquet",     "raw_precipitacion"),
        (raw / "ideam_tmax.parquet",       "raw_temperatura"),
    ]

    total_rows = 0
    for parquet_path, table in tables:
        total_rows += _load_parquet(con, parquet_path, table)

    logger.info("[DuckDB] Carga completada. Total filas: %d", total_rows)
    con.close()
