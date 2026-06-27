"""Configuración central del proyecto Alerta.

Toda constante o parámetro ajustable vive aquí.
Ningún número mágico debe aparecer en src/.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict


@dataclass
class IRAConfig:
    # ── Ponderaciones de los sub-índices ────────────────────────────────────
    w_spc: float = 0.5   # Sub-índice de Peligro Climático
    w_sep: float = 0.3   # Sub-índice de Exposición Productiva
    w_sve: float = 0.2   # Sub-índice de Vulnerabilidad Económica

    # ── Paginación SODA API (datos.gov.co) ───────────────────────────────────
    soda_page_size: int = 50_000

    # ── Rutas de datos ───────────────────────────────────────────────────────
    data_raw: str = "data/raw"
    # Archivo DuckDB: motor analítico local.
    # Todas las tablas del proyecto se almacenan aquí.
    duckdb_path: str = "data/alerta.duckdb"

    # ── Clasificación IRA ────────────────────────────────────────────────────
    # Rangos [min, max) para asignar nivel de riesgo.
    ira_niveles: Dict[str, tuple] = field(
        default_factory=lambda: {
            "Bajo":    (0.00, 0.25),
            "Medio":   (0.25, 0.50),
            "Alto":    (0.50, 0.75),
            "Crítico": (0.75, 1.01),  # 1.01 para incluir score exacto de 1.0
        }
    )

    def ensure_dirs(self) -> None:
        """Crea las carpetas de datos si no existen."""
        Path(self.data_raw).mkdir(parents=True, exist_ok=True)
        Path(self.duckdb_path).parent.mkdir(parents=True, exist_ok=True)


# Instancia global lista para importar desde cualquier módulo.
# Ejemplo: from config import config
config = IRAConfig()
