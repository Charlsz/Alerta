"""Construye la tabla maestra `features_municipio_cultivo` en DuckDB.

Une:
    features_clima       (por municipio × periodo)
    features_produccion  (por municipio × cultivo)
    features_vulnerabilidad (por periodo — nacional)

Salida: tabla DuckDB `features_municipio_cultivo`
    Llave: (codigo_municipio, cultivo, periodo)

Esta tabla es la entrada directa de src/risk/.
"""
from __future__ import annotations

import logging

from src.ingestion.load_duckdb import get_connection

logger = logging.getLogger(__name__)

_TABLE = "features_municipio_cultivo"


def build(force: bool = False) -> None:
    """Une las tres capas de features en la tabla maestra."""
    con = get_connection()

    if not force:
        existing = con.execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = ?", [_TABLE]
        ).fetchone()[0]  # type: ignore[index]
        if existing:
            logger.info("[store] Tabla '%s' ya existe, omitiendo.", _TABLE)
            con.close()
            return

    logger.info("[store] Construyendo tabla maestra de features...")

    sql = f"""
        CREATE OR REPLACE TABLE {_TABLE} AS
        SELECT
            -- Llave
            c.codigo_municipio,
            p.cultivo,
            c.periodo,

            -- SPC: peligro climático
            c.precip_acum_7d,
            c.precip_acum_30d,
            c.precip_anomalia_30d,
            c.dias_secos_consecutivos,
            c.dias_lluvia_extrema,
            c.tmax_media_7d,
            c.tmax_anomalia_30d,
            c.dias_tmax_critica,

            -- SEP: exposición productiva
            p.area_sembrada,
            p.area_cosechada,
            p.rendimiento_promedio,
            p.rendimiento_cv,
            p.participacion_municipal,
            -- fase fenológica: 1 si el mes del periodo es mes de siembra o cosecha
            CASE
                WHEN MONTH(c.periodo) IN (p.mes_siembra, p.mes_cosecha) THEN 1
                ELSE 0
            END AS fase_fenologica,

            -- SVE: vulnerabilidad económica
            v.insumos_nivel,
            v.insumos_anomalia_12m,
            v.insumos_delta_3m

        FROM features_clima          c
        JOIN features_produccion     p ON c.codigo_municipio = p.codigo_municipio
        LEFT JOIN features_vulnerabilidad v ON DATE_TRUNC('month', c.periodo) = DATE_TRUNC('month', v.periodo)
        WHERE c.codigo_municipio IS NOT NULL
          AND p.cultivo IS NOT NULL
    """
    con.execute(sql)
    (rows,) = con.execute(f"SELECT COUNT(*) FROM {_TABLE}").fetchone()  # type: ignore[misc]
    logger.info("[store] Tabla '%s' creada: %d filas.", _TABLE, rows)
    con.close()
