"""Limpieza y homologación de las tablas raw_* en DuckDB.

Produce tablas `clean_*` con tipos correctos, nombres de columna
normalizados y código DANE de 5 dígitos consistente.

Pipeline completo (Paso 5 + extensión Paso 6D):
    raw_estaciones      → clean_estaciones
    raw_eva             → clean_eva
    raw_eva_vista       → clean_eva_vista
    raw_eva_calendario  → clean_eva_calendario
    raw_insumos         → clean_insumos
    raw_precipitacion   → clean_precipitacion
    raw_temperatura     → clean_temperatura
    raw_humedad         → clean_humedad         ← nuevo
    raw_presion         → clean_presion         ← nuevo
    raw_tambiente       → clean_tambiente       ← nuevo
    raw_dane_municipios → clean_dane_municipios ← nuevo

Reglas generales:
    1. Nombres de columna en minúsculas sin espacios.
    2. codigo_municipio → VARCHAR(5) con LPAD.
    3. Valores numéricos casteados a DOUBLE; texto a VARCHAR.
    4. Fechas casteadas a TIMESTAMP.
    5. Filas con campos clave nulos son eliminadas.
"""
from __future__ import annotations

import logging

import duckdb

from src.ingestion.load_duckdb import get_connection

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _raw_columns(con: duckdb.DuckDBPyConnection, table: str) -> list[str]:
    return [
        row[0].lower().strip()
        for row in con.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name = ?",
            [table],
        ).fetchall()
    ]


def _safe_col(cols: list[str], *candidates: str) -> str | None:
    for c in candidates:
        if c in cols:
            return c
    return None


def _table_exists(con: duckdb.DuckDBPyConnection, table: str) -> bool:
    return bool(
        con.execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = ?",
            [table],
        ).fetchone()[0]  # type: ignore[index]
    )


def _log_table(con: duckdb.DuckDBPyConnection, table: str) -> None:
    (rows,) = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()  # type: ignore[misc]
    logger.info("[clean] %-40s %d filas", f"'{table}'", rows)


# ─────────────────────────────────────────────────────────────────────────────
# Limpiezas originales (Paso 5)
# ─────────────────────────────────────────────────────────────────────────────

def _clean_estaciones(con: duckdb.DuckDBPyConnection) -> None:
    cols = _raw_columns(con, "raw_estaciones")
    lat = _safe_col(cols, "latitud", "latitud_", "lat")
    lon = _safe_col(cols, "longitud", "longitud_", "lon", "lng")
    cod = _safe_col(cols, "codigoestacion", "codigo_estacion", "codigo")
    nom = _safe_col(cols, "nombreestacion", "nombre_estacion", "nombre")
    dep = _safe_col(cols, "departamento", "depto")
    mun = _safe_col(cols, "municipio")

    missing = [n for n, c in [("lat", lat), ("lon", lon), ("cod", cod)] if c is None]
    if missing:
        logger.error("[clean_estaciones] Faltan columnas: %s. Disponibles: %s", missing, cols)
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
            {'TRIM(CAST(estado AS VARCHAR))' if 'estado' in cols else "''"} AS estado,
            {'TRIM(CAST(tipoestacion AS VARCHAR))' if 'tipoestacion' in cols else "''"} AS tipoestacion
        FROM raw_estaciones
        WHERE {cod} IS NOT NULL
          AND TRY_CAST({lat} AS DOUBLE) IS NOT NULL
          AND TRY_CAST({lon} AS DOUBLE) IS NOT NULL
    """)
    _log_table(con, "clean_estaciones")


def _clean_eva(con: duckdb.DuckDBPyConnection, raw: str, clean: str) -> None:
    cols = _raw_columns(con, raw)
    anio  = _safe_col(cols, "anio", "a_o", "periodo", "year")
    cod_m = _safe_col(cols, "codigomunicipio", "codigo_municipio", "cod_municipio", "codmunicipio")
    dep   = _safe_col(cols, "departamento", "depto")
    mun   = _safe_col(cols, "municipio", "nombremunicipio")
    cult  = _safe_col(cols, "cultivo", "nombrecultivo", "nombre_cultivo")
    a_sem = _safe_col(cols, "area_sembrada", "areasembrada", "areasembr")
    a_cos = _safe_col(cols, "area_cosechada", "areacosechada", "areacosec")
    prod  = _safe_col(cols, "produccion", "produccion_t", "prod")
    rend  = _safe_col(cols, "rendimiento", "rendimient")

    cod_expr = f"LPAD(TRIM(CAST({cod_m} AS VARCHAR)), 5, '0')" if cod_m else "NULL::VARCHAR"

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
    cols = _raw_columns(con, "raw_eva_calendario")
    cod_m  = _safe_col(cols, "codigomunicipio", "codigo_municipio", "cod_municipio")
    cult   = _safe_col(cols, "cultivo", "nombrecultivo")
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
    cols  = _raw_columns(con, "raw_insumos")
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
    """Limpia tablas de observaciones IDEAM (reutilizable para todos los sensores)."""
    cols    = _raw_columns(con, raw)
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

    # Umbral mínimo físico por sensor
    min_val = {
        "precipitacion":      "0",
        "temperatura_maxima": "-10",
        "humedad":            "0",
        "presion":            "500",
        "temperatura_ambiente": "-20",
    }.get(sensor_label, "-9999")

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
          AND TRY_CAST({valor} AS DOUBLE) >= {min_val}
    """)
    _log_table(con, clean)


# ─────────────────────────────────────────────────────────────────────────────
# Limpiezas nuevas (Paso 6D)
# ─────────────────────────────────────────────────────────────────────────────

def _clean_dane_municipios(con: duckdb.DuckDBPyConnection) -> None:
    """Limpia y homologa variables socioeconómicas DANE."""
    if not _table_exists(con, "raw_dane_municipios"):
        logger.warning("[clean_dane] raw_dane_municipios no existe, omitiendo.")
        return

    cols    = _raw_columns(con, "raw_dane_municipios")
    cod     = _safe_col(cols, "codigo_municipio", "cod_dane", "divipola")
    nbi     = _safe_col(cols, "nbi_total", "nbi", "porcentaje_nbi")
    pob_rur = _safe_col(cols, "poblacion_rural", "pob_resto", "resto")
    pob_tot = _safe_col(cols, "poblacion_total", "total_personas")
    pct_rur = _safe_col(cols, "pct_rural")
    nom     = _safe_col(cols, "nombre_municipio", "municipio")
    dep     = _safe_col(cols, "departamento")

    if not cod:
        logger.error("[clean_dane] No se encontró columna de código municipio. Cols: %s", cols)
        return

    con.execute(f"""
        CREATE OR REPLACE TABLE clean_dane_municipios AS
        SELECT
            LPAD(TRIM(CAST({cod} AS VARCHAR)), 5, '0')          AS codigo_municipio,
            {'TRIM(UPPER(CAST(' + nom + ' AS VARCHAR)))' if nom else "''"} AS nombre_municipio,
            {'TRIM(UPPER(CAST(' + dep + ' AS VARCHAR)))' if dep else "''"} AS departamento,
            TRY_CAST({nbi or 'NULL'}     AS DOUBLE)             AS nbi_total,
            TRY_CAST({pob_rur or 'NULL'} AS DOUBLE)             AS poblacion_rural,
            TRY_CAST({pob_tot or 'NULL'} AS DOUBLE)             AS poblacion_total,
            TRY_CAST({pct_rur or 'NULL'} AS DOUBLE)             AS pct_rural
        FROM raw_dane_municipios
        WHERE {cod} IS NOT NULL
    """)
    _log_table(con, "clean_dane_municipios")


# ─────────────────────────────────────────────────────────────────────────────
# Punto de entrada público
# ─────────────────────────────────────────────────────────────────────────────

def build(force: bool = False) -> None:
    """Ejecuta todas las limpiezas. Crea/reemplaza tablas clean_*."""
    con = get_connection()

    all_clean = [
        "clean_estaciones", "clean_eva", "clean_eva_vista", "clean_eva_calendario",
        "clean_insumos", "clean_precipitacion", "clean_temperatura",
        "clean_humedad", "clean_presion", "clean_tambiente", "clean_dane_municipios",
    ]

    if not force:
        existing = [
            row[0] for row in con.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_name LIKE 'clean_%'"
            ).fetchall()
        ]
        if all(t in existing for t in all_clean):
            logger.info("[clean] Todas las tablas clean_* ya existen, omitiendo.")
            con.close()
            return

    logger.info("[clean] === Limpiando tablas base ===")
    _clean_estaciones(con)
    _clean_eva(con, "raw_eva",       "clean_eva")
    _clean_eva(con, "raw_eva_vista", "clean_eva_vista")
    _clean_eva_calendario(con)
    _clean_insumos(con)

    logger.info("[clean] === Limpiando observaciones IDEAM ===")
    _clean_ideam(con, "raw_precipitacion", "clean_precipitacion", "precipitacion")
    _clean_ideam(con, "raw_temperatura",   "clean_temperatura",   "temperatura_maxima")
    _clean_ideam(con, "raw_humedad",       "clean_humedad",       "humedad")
    _clean_ideam(con, "raw_presion",       "clean_presion",       "presion")
    _clean_ideam(con, "raw_tambiente",     "clean_tambiente",     "temperatura_ambiente")

    logger.info("[clean] === Limpiando datos DANE ===")
    _clean_dane_municipios(con)

    logger.info("[clean] Paso completado — 11 tablas clean_* listas.")
    con.close()
