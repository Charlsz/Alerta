"""Puente entre tablas clean_* y los módulos de features.

Los módulos de features/ fueron escritos para leer de raw_*.
Este módulo crea vistas `feat_src_*` que apuntan a clean_*
para que el resto del pipeline use datos limpios sin cambiar
los módulos ya implementados.

Llamar build() justo después de clean.build() y antes de
los módulos de features.
"""
from __future__ import annotations

import logging

from src.ingestion.load_duckdb import get_connection

logger = logging.getLogger(__name__)

# Mapeo: nombre que usa features/ → tabla clean que lo reemplaza
_VIEWS: dict[str, str] = {
    "raw_estaciones":     "clean_estaciones",
    "raw_eva":            "clean_eva",
    "raw_eva_vista":      "clean_eva_vista",
    "raw_eva_calendario": "clean_eva_calendario",
    "raw_insumos":        "clean_insumos",
    "raw_precipitacion":  "clean_precipitacion",
    "raw_temperatura":    "clean_temperatura",
}


def build(force: bool = False) -> None:  # noqa: ARG001
    """Reemplaza las tablas raw_* por vistas que apuntan a clean_*.

    DuckDB no tiene CREATE OR REPLACE VIEW, así que hacemos
    DROP + CREATE. Esto es seguro porque las tablas originales
    raw_* siguen existiendo — solo cambiamos qué ve el nombre.
    """
    con = get_connection()
    for raw_name, clean_name in _VIEWS.items():
        # Verificar que la tabla clean existe antes de crear la vista
        exists = con.execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = ?",
            [clean_name],
        ).fetchone()[0]  # type: ignore[index]

        if not exists:
            logger.warning(
                "[clean_bridge] '%s' no existe todavía, omitiendo vista para '%s'.",
                clean_name, raw_name,
            )
            continue

        con.execute(f"DROP VIEW IF EXISTS {raw_name}_view")
        con.execute(f"""
            CREATE VIEW {raw_name}_view AS SELECT * FROM {clean_name}
        """)
        logger.info("[clean_bridge] Vista '%s_view' → '%s'", raw_name, clean_name)

    logger.info("[clean_bridge] Vistas creadas. Los módulos de features usan datos limpios.")
    con.close()
