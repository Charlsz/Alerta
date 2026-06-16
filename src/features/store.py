"""Construye la tabla maestra `features_municipio_cultivo` en DuckDB.

Une:
    features_clima          (14 vars SPC — por municipio × periodo)
    features_produccion     (6 vars SEP  — por municipio × cultivo)
    features_vulnerabilidad (3 vars SVE insumos — por periodo, nacional)
    features_dane           (3 vars SVE dane    — por municipio, estático)

Salida: tabla DuckDB `features_municipio_cultivo`
    Llave: (codigo_municipio, cultivo, periodo)
    Total columnas de features: 26

Esta tabla es la entrada directa de src/risk/.
"""
from __future__ import annotations

import logging

from src.ingestion.load_duckdb import get_connection

logger = logging.getLogger(__name__)

_TABLE = "features_municipio_cultivo"


def _table_exists(con, table: str) -> bool:
    return bool(
        con.execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = ?",
            [table],
        ).fetchone()[0]
    )


def build(force: bool = False) -> None:
    """Une las cuatro capas de features en la tabla maestra (26 variables)."""
    con = get_connection()

    if not force:
        if _table_exists(con, _TABLE):
            logger.info("[store] Tabla '%s' ya existe, omitiendo.", _TABLE)
            con.close()
            return

    # Verificar que features_dane existe (puede ser vacío si DANE no está disponible)
    dane_join = ""
    dane_cols = "NULL::DOUBLE AS nbi_total, NULL::DOUBLE AS poblacion_rural, NULL::DOUBLE AS pct_rural"
    if _table_exists(con, "features_dane"):
        dane_join = "LEFT JOIN features_dane d ON c.codigo_municipio = d.codigo_municipio"
        dane_cols = "d.nbi_total, d.poblacion_rural, d.pct_rural"

    logger.info("[store] Construyendo tabla maestra de features (26 variables)...")

    sql = f"""
        CREATE OR REPLACE TABLE {_TABLE} AS
        SELECT
            -- Llave compuesta
            c.codigo_municipio,
            p.cultivo,
            c.periodo,

            -- SPC: peligro climático (14 variables)
            c.precip_acum_7d,
            c.precip_acum_30d,
            c.precip_anomalia_30d,
            c.dias_secos_consecutivos,
            c.dias_lluvia_extrema,
            c.tmax_media_7d,
            c.tmax_anomalia_30d,
            c.dias_tmax_critica,
            c.humedad_media_30d,
            c.humedad_anomalia_30d,
            c.presion_media_30d,
            c.presion_anomalia_30d,
            c.tambiente_media_30d,
            c.tmin_media_30d,

            -- SEP: exposición productiva (6 variables)
            p.area_sembrada,
            p.area_cosechada,
            p.rendimiento_promedio,
            p.rendimiento_cv,
            p.participacion_municipal,
            CASE
                WHEN MONTH(c.periodo) IN (p.mes_siembra, p.mes_cosecha) THEN 1
                ELSE 0
            END AS fase_fenologica,

            -- SVE: vulnerabilidad económica (6 variables)
            v.insumos_nivel,
            v.insumos_anomalia_12m,
            v.insumos_delta_3m,
            {dane_cols}

        FROM features_clima          c
        JOIN features_produccion     p
          ON c.codigo_municipio = p.codigo_municipio
        LEFT JOIN features_vulnerabilidad v
          ON DATE_TRUNC('month', c.periodo) = DATE_TRUNC('month', v.periodo)
        {dane_join}
        WHERE c.codigo_municipio IS NOT NULL
          AND p.cultivo          IS NOT NULL
    """
    con.execute(sql)
    (rows,) = con.execute(f"SELECT COUNT(*) FROM {_TABLE}").fetchone()  # type: ignore[misc]
    logger.info("[store] Tabla '%s' creada: %d filas, 26 features.", _TABLE, rows)
    con.close()
