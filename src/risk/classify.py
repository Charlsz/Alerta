"""Asigna nivel de riesgo textual a un score IRA en [0, 1]."""
from __future__ import annotations

from config import config


def classify_ira(score: float) -> str:
    """Retorna 'Bajo', 'Medio', 'Alto' o 'Crítico' según el score IRA."""
    for nivel, (lo, hi) in config.ira_niveles.items():
        if lo <= score < hi:
            return nivel
    return "Crítico"  # fallback para score == 1.0 exacto
