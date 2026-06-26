"""Clean and normalize raw feature DataFrames (EVA, IDEAM, etc.)."""
import logging

import duckdb

from src.ingestion.load_duckdb import get_connection

logger = logging.getLogger(__name__)

_CLEAN_SQL = {
    "clean_eva": """
        SELECT
            c_d_dep AS codigo_departamento,
            departamento,
            LPAD(TRIM(c_d_mun), 5, '0') AS codigo_municipio,
            municipio,
            LOWER(TRIM(cultivo)) AS cultivo,
            TRIM(grupo_de_cultivo) AS grupo_cultivo,
            TRIM(subgrupo_de_cultivo) AS subgrupo_cultivo,
            TRIM(desagregaci_n_regional_y) AS desagregacion,
            a_o,
            periodo,
            CAST(NULLIF(TRIM(rea_sembrada_ha), '') AS DOUBLE) AS area_sembrada,
            CAST(NULLIF(TRIM(rea_cosechada_ha), '') AS DOUBLE) AS area_cosechada,
            CAST(NULLIF(TRIM(producci_n_t), '') AS DOUBLE) AS produccion,
            CAST(NULLIF(TRIM(rendimiento_t_ha), '') AS DOUBLE) AS rendimiento,
            TRIM(estado_fisico_produccion) AS estado_fisico,
            TRIM(nombre_cientifico) AS nombre_cientifico,
            TRIM(ciclo_de_cultivo) AS ciclo
        FROM raw_eva
    """,
    "clean_precipitacion": "SELECT * FROM raw_precipitacion",
    "clean_temperatura": "SELECT * FROM raw_temperatura",
    "clean_humedad": "SELECT * FROM raw_humedad",
    "clean_presion": "SELECT * FROM raw_presion",
    "clean_tambiente": "SELECT * FROM raw_tambiente",
    "clean_insumos": "SELECT * FROM raw_insumos",
    "clean_eva_calendario": "SELECT * FROM raw_eva_calendario",
    "clean_dane_municipios": "SELECT * FROM raw_dane_municipios",
    "clean_dane_nbi": "SELECT * FROM raw_dane_nbi",
}


def build(force: bool = False) -> None:
    """Crea tablas clean_* en DuckDB a partir de tablas raw_*."""
    con = get_connection()
    for table, sql in _CLEAN_SQL.items():
        raw_table = "raw_" + table[6:]
        exists = con.execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = ?",
            [raw_table],
        ).fetchone()[0]
        if not exists:
            logger.warning("[clean] Tabla origen %s no existe, saltando %s.", raw_table, table)
            con.execute(f"CREATE OR REPLACE TABLE {table} AS SELECT NULL LIMIT 0")
            continue

        if not force:
            already = con.execute(
                "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = ?",
                [table],
            ).fetchone()[0]
            if already:
                logger.info("[clean] %s ya existe, omitiendo.", table)
                continue

        con.execute(f"CREATE OR REPLACE TABLE {table} AS {sql}")
        (rows,) = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
        logger.info("[clean] %-40s %d filas", f"'{table}'", rows)
    con.close()
