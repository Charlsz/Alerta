"""Limpieza y homologación de las tablas raw_* en DuckDB.

Este módulo es el Paso 5: actúa sobre las tablas cargadas por load_duckdb.py
y produce tablas `clean_*` con tipos correctos, nombres de columna
normalizados y código DANE de 5 dígitos consistente.

Pipeline:
    raw_estaciones      → clean_estaciones
    raw_eva             → clean_eva
    raw_eva_vista       → clean_eva_vista
    raw_eva_calendario  → clean_eva_calendario
    raw_insumos         → clean_insumos
    raw_precipitacion   → clean_precipitacion
    raw_temperatura     → clean_temperatura

Reglas generales aplicadas en todas las tablas:
    1. Nombres de columna en minúsculas sin espacios.
    2. codigo_municipio → VARCHAR(5) con cero a la izquierda (LPAD).
    3. Valores numéricos casteados a DOUBLE; texto a VARCHAR.
    4. Fechas casteadas a TIMESTAMP.
    5. Filas con código municipio o fecha nulos son eliminadas.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable

import duckdb

from src.ingestion.load_duckdb import get_connection

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _col_exists(con: duckdb.DuckDBPyConnection, table: str, col: str) -> bool:
    """Comprueba si una columna existe en la tabla (en DuckDB)."""
    rows = con.execute(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name = ? AND column_name = ?",
        [table, col],
    ).fetchall()
    return len(rows) > 0


def _raw_columns(con: duckdb.DuckDBPyConnection, table: str) -> list[str]:
    """Devuelve los nombres de columna de una tabla raw (en minúsculas)."""
    return [
        row[0].lower().strip()
        for row in con.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name = ?",
            [table],
        ).fetchall()
    ]


def _safe_col(cols: list[str], *candidates: str) -> str | None:
    """Busca la primera columna que coincida con alguno de los candidatos."""
    for c in candidates:
        if c in cols:
            return c
    return None


# ──────────────────────────────────────────────────────────────────────────────
# Limpiezas individuales
# ──────────────────────────────────────────────────────────────────────────────

def _clean_estaciones(con: duckdb.DuckDBPyConnection) -> None:
    """Limpia el catálogo de estaciones IDEAM.

    Columnas clave esperadas (SODA hp9r-jxuu):
        codigoestacion, nombreestacion, departamento, municipio,
        latitud, longitud, altitud, estado, tipoestacion,
        fechainstalacion, fechasuspension
    """
    cols = _raw_columns(con, "raw_estaciones")

    lat = _safe_col(cols, "latitud", "latitud_", "lat")
    lon = _safe_col(cols, "longitud", "longitud_", "lon", "lng")
    cod = _safe_col(cols, "codigoestacion", "codigo_estacion", "codigo")
    nom = _safe_col(cols, "nombreestacion", "nombre_estacion", "nombre")
    dep = _safe_col(cols, "departamento", "depto")
    mun = _safe_col(cols, "municipio")

    missing = [name for name, col in [("lat", lat), ("lon", lon), ("cod", cod)] if col is None]
    if missing:
        logger.error("[clean_estaciones] Faltan columnas requeridas: %s. Columnas disponibles: %s", missing, cols)
        return

    con.execute(f"""
        CREATE OR REPLACE TABLE clean_estaciones AS
        SELECT
            TRIM(CAST({cod}            AS VARCHAR))                AS codigoestacion,
            TRIM(CAST({nom or "''"}    AS VARCHAR))                AS nombreestacion,
            TRIM(UPPER(CAST({dep or "''"} AS VARCHAR)))           AS departamento,
            TRIM(UPPER(CAST({mun or "''"} AS VARCHAR)))           AS municipio,
            TRY_CAST({lat} AS DOUBLE)                             AS latitud,
            TRY_CAST({lon} AS DOUBLE)                             AS longitud,
            {'TRY_CAST(altitud AS DOUBLE)' if 'altitud' in cols else 'NULL::DOUBLE'} AS altitud,
            {'TRIM(CAST(estado AS VARCHAR))' if 'estado' in cols else "''"}         AS estado,
            {'TRIM(CAST(tipoestacion AS VARCHAR))' if 'tipoestacion' in cols else "''"} AS tipoestacion
        FROM raw_estaciones
        WHERE {cod} IS NOT NULL
          AND TRY_CAST({lat} AS DOUBLE) IS NOT NULL
          AND TRY_CAST({lon} AS DOUBLE) IS NOT NULL
    """)
    _log_table(con, "clean_estaciones")


def _clean_eva(con: duckdb.DuckDBPyConnection, raw: str, clean: str) -> None:
    """Limpia EVA y EVA Vista.

    Columnas clave esperadas (SODA 2pnw-mmge / fp29-z39g):
        anio/periodo, departamento, municipio, codigomunicipio,
        cultivo/nombrecultivo, area_sembrada/areasembrada,
        area_cosechada/areacosechada, produccion, rendimiento
    """
    cols = _raw_columns(con, raw)

    anio   = _safe_col(cols, "anio", "a_o", "periodo", "year")
    cod_m  = _safe_col(cols, "codigomunicipio", "codigo_municipio", "cod_municipio", "codmunicipio")
    dep    = _safe_col(cols, "departamento", "depto")
    mun    = _safe_col(cols, "municipio", "nombremunicipio")
    cult   = _safe_col(cols, "cultivo", "nombrecultivo", "nombre_cultivo")
    a_sem  = _safe_col(cols, "area_sembrada", "areasembrada", "areasembr")
    a_cos  = _safe_col(cols, "area_cosechada", "areacosechada", "areacosec")
    prod   = _safe_col(cols, "produccion", "produccion_t", "prod")
    rend   = _safe_col(cols, "rendimiento", "rendimient")

    # Código municipio: si no existe como columna lo construimos desde depto+municipio
    if cod_m:
        cod_expr = f"LPAD(TRIM(CAST({cod_m} AS VARCHAR)), 5, '0')"
    else:
        logger.warning("[%s] No hay columna de código municipio. Se usará NULL.", clean)
        cod_expr = "NULL::VARCHAR"

    con.execute(f"""
        CREATE OR REPLACE TABLE {clean} AS
        SELECT
            {f'TRY_CAST({anio} AS INTEGER)' if anio else 'NULL::INTEGER'}   AS anio,
            {cod_expr}                                                        AS codigo_municipio,
            TRIM(UPPER(CAST({dep or "''"} AS VARCHAR)))                      AS departamento,
            TRIM(UPPER(CAST({mun or "''"} AS VARCHAR)))                      AS municipio,
            TRIM(LOWER(CAST({cult or "''"} AS VARCHAR)))                     AS cultivo,
            TRY_CAST({a_sem or 'NULL'} AS DOUBLE)                            AS area_sembrada,
            TRY_CAST({a_cos or 'NULL'} AS DOUBLE)                            AS area_cosechada,
            TRY_CAST({prod or 'NULL'}  AS DOUBLE)                            AS produccion,
            TRY_CAST({rend or 'NULL'}  AS DOUBLE)                            AS rendimiento
        FROM {raw}
        WHERE {cod_expr} IS NOT NULL
          AND {cult or "'x'"} IS NOT NULL
    """)
    _log_table(con, clean)


def _clean_eva_calendario(con: duckdb.DuckDBPyConnection) -> None:
    """Limpia el calendario de siembras y cosechas.

    Columnas clave esperadas (SODA 4229-puwp):
        cultivo, codigomunicipio, mes_siembra, mes_cosecha, semestre
    """
    cols = _raw_columns(con, "raw_eva_calendario")

    cod_m = _safe_col(cols, "codigomunicipio", "codigo_municipio", "cod_municipio")
    cult  = _safe_col(cols, "cultivo", "nombrecultivo")
    m_siem = _safe_col(cols, "mes_siembra", "messiembra", "mes_inicio")
    m_cos  = _safe_col(cols, "mes_cosecha", "mescosecha", "mes_fin")
    sem    = _safe_col(cols, "semestre", "periodo")

    cod_expr = f"LPAD(TRIM(CAST({cod_m} AS VARCHAR)), 5, '0')" if cod_m else "NULL::VARCHAR"

    con.execute(f"""
        CREATE OR REPLACE TABLE clean_eva_calendario AS
        SELECT
            {cod_expr}                                               AS codigo_municipio,
            TRIM(LOWER(CAST({cult or "''"} AS VARCHAR)))            AS cultivo,
            TRY_CAST({m_siem or 'NULL'} AS INTEGER)                 AS mes_siembra,
            TRY_CAST({m_cos  or 'NULL'} AS INTEGER)                 AS mes_cosecha,
            TRIM(CAST({sem   or "''"} AS VARCHAR))                  AS semestre
        FROM raw_eva_calendario
        WHERE {cult or "'x'"} IS NOT NULL
    """)
    _log_table(con, "clean_eva_calendario")


def _clean_insumos(con: duckdb.DuckDBPyConnection) -> None:
    """Limpia el índice de precios de insumos agrícolas.

    Columnas clave esperadas (SODA gwbi-fnzs):
        fecha / periodo / mes, indice / valor / valor_indice
    """
    cols = _raw_columns(con, "raw_insumos")

    fecha = _safe_col(cols, "fecha", "periodo", "mes", "fecha_referencia", "date")
    valor = _safe_col(cols, "indice", "valor", "valor_indice", "indice_general", "índice")
    grupo = _safe_col(cols, "grupo", "tipo", "insumo", "categoria")

    if not fecha or not valor:
        logger.error("[clean_insumos] No se encontraron columnas fecha/valor. Cols: %s", cols)
        return

    con.execute(f"""
        CREATE OR REPLACE TABLE clean_insumos AS
        SELECT
            TRY_CAST(TRY_STRPTIME(
                TRIM(CAST({fecha} AS VARCHAR)),
                '%Y-%m-%dT%H:%M:%S.%f'
            ) AS TIMESTAMP)                         AS periodo,
            {'TRIM(LOWER(CAST(' + grupo + ' AS VARCHAR)))' if grupo else "'total'"} AS grupo,
            TRY_CAST({valor} AS DOUBLE)             AS insumos_nivel
        FROM raw_insumos
        WHERE {valor} IS NOT NULL
        ORDER BY periodo
    """)
    _log_table(con, "clean_insumos")


def _clean_ideam(con: duckdb.DuckDBPyConnection, raw: str, clean: str, sensor_label: str) -> None:
    """Limpia tablas de observaciones IDEAM (precipitación y temperatura).

    Columnas clave esperadas (SODA s54a-sgyg / ccvq-rp9s):
        codigoestacion, codigosensor, fechaobservacion,
        valorobservado, nombreestacion, departamento, municipio,
        latitud, longitud, descripcionsensor, unidadmedida
    """
    cols = _raw_columns(con, raw)

    cod_est = _safe_col(cols, "codigoestacion", "codigo_estacion")
    fecha   = _safe_col(cols, "fechaobservacion", "fecha_observacion", "fecha")
    valor   = _safe_col(cols, "valorobservado", "valor_observado", "valor")
    dep     = _safe_col(cols, "departamento", "depto")
    mun     = _safe_col(cols, "municipio")
    lat     = _safe_col(cols, "latitud")
    lon     = _safe_col(cols, "longitud")
    unidad  = _safe_col(cols, "unidadmedida", "unidad_medida", "unidad")

    missing = [n for n, c in [("codigoestacion", cod_est), ("fechaobservacion", fecha), ("valorobservado", valor)] if c is None]
    if missing:
        logger.error("[%s] Columnas faltantes: %s. Disponibles: %s", clean, missing, cols)
        return

    con.execute(f"""
        CREATE OR REPLACE TABLE {clean} AS
        SELECT
            TRIM(CAST({cod_est} AS VARCHAR))                              AS codigoestacion,
            TRY_STRPTIME(
                TRIM(CAST({fecha} AS VARCHAR)),
                '%Y-%m-%dT%H:%M:%S.%f'
            )::TIMESTAMP                                                  AS fechaobservacion,
            TRY_CAST({valor} AS DOUBLE)                                   AS valorobservado,
            TRIM(UPPER(CAST({dep or "''"} AS VARCHAR)))                   AS departamento,
            TRIM(UPPER(CAST({mun or "''"} AS VARCHAR)))                   AS municipio,
            TRY_CAST({lat or 'NULL'} AS DOUBLE)                           AS latitud,
            TRY_CAST({lon or 'NULL'} AS DOUBLE)                           AS longitud,
            '{sensor_label}'                                              AS sensor,
            {'TRIM(CAST(' + unidad + ' AS VARCHAR))' if unidad else "''"} AS unidadmedida
        FROM {raw}
        WHERE {fecha} IS NOT NULL
          AND {valor} IS NOT NULL
          AND TRY_CAST({valor} AS DOUBLE) IS NOT NULL
          -- Eliminar valores físicamente imposibles
          AND TRY_CAST({valor} AS DOUBLE) >= 0
    """)
    _log_table(con, clean)


def _log_table(con: duckdb.DuckDBPyConnection, table: str) -> None:
    (rows,) = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()  # type: ignore[misc]
    logger.info("[clean] %-35s %d filas", f"'{table}'", rows)


# ──────────────────────────────────────────────────────────────────────────────
# Punto de entrada público
# ──────────────────────────────────────────────────────────────────────────────

def build(force: bool = False) -> None:
    """Ejecuta todas las limpiezas en orden. Crea tablas clean_*.

    Si force=False y todas las tablas clean_* ya existen, omite el paso.
    """
    con = get_connection()

    clean_tables = [
        "clean_estaciones", "clean_eva", "clean_eva_vista",
        "clean_eva_calendario", "clean_insumos",
        "clean_precipitacion", "clean_temperatura",
    ]

    if not force:
        existing = [
            row[0]
            for row in con.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_name LIKE 'clean_%'"
            ).fetchall()
        ]
        if all(t in existing for t in clean_tables):
            logger.info("[clean] Todas las tablas clean_* ya existen, omitiendo.")
            con.close()
            return

    logger.info("[clean] Limpiando estaciones IDEAM...")
    _clean_estaciones(con)

    logger.info("[clean] Limpiando EVA...")
    _clean_eva(con, "raw_eva",       "clean_eva")
    _clean_eva(con, "raw_eva_vista", "clean_eva_vista")

    logger.info("[clean] Limpiando EVA Calendario...")
    _clean_eva_calendario(con)

    logger.info("[clean] Limpiando índice de insumos...")
    _clean_insumos(con)

    logger.info("[clean] Limpiando precipitación IDEAM...")
    _clean_ideam(con, "raw_precipitacion", "clean_precipitacion", "precipitacion")

    logger.info("[clean] Limpiando temperatura máxima IDEAM...")
    _clean_ideam(con, "raw_temperatura",   "clean_temperatura",   "temperatura_maxima")

    logger.info("[clean] Paso 5 completado.")
    con.close()
