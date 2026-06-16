"""Normalización min-max robusta (p1-p99) de features para el IRA.

Actualizado para incluir las 14 variables SPC, 6 SEP, 6 SVE = 26 variables.
"""
from __future__ import annotations

import logging

import pandas as pd

logger = logging.getLogger(__name__)

# ── Sub-índice de Peligro Climático (SPC) — 14 variables ────────────────────
_SPC_COLS = [
    # Precipitación (originales)
    "precip_acum_7d",
    "precip_acum_30d",
    "precip_anomalia_30d",
    "dias_secos_consecutivos",
    "dias_lluvia_extrema",
    # Temperatura máxima (originales)
    "tmax_media_7d",
    "tmax_anomalia_30d",
    "dias_tmax_critica",
    # Humedad del aire (nuevas)
    "humedad_media_30d",
    "humedad_anomalia_30d",
    # Presión atmosférica (nuevas)
    "presion_media_30d",
    "presion_anomalia_30d",
    # Temperatura ambiente (nuevas)
    "tambiente_media_30d",
    "tmin_media_30d",
]

# ── Sub-índice de Exposición Productiva (SEP) — 6 variables ─────────────────
_SEP_COLS = [
    "area_sembrada",
    "area_cosechada",
    "rendimiento_promedio",
    "rendimiento_cv",
    "participacion_municipal",
    "fase_fenologica",
]

# ── Sub-índice de Vulnerabilidad Económica (SVE) — 6 variables ───────────────
_SVE_COLS = [
    # Insumos (originales)
    "insumos_nivel",
    "insumos_anomalia_12m",
    "insumos_delta_3m",
    # DANE (nuevas)
    "nbi_total",
    "poblacion_rural",
    "pct_rural",
]

ALL_FEATURE_COLS = _SPC_COLS + _SEP_COLS + _SVE_COLS  # 26 variables


def normalize(df: pd.DataFrame) -> pd.DataFrame:
    """Normaliza con min-max robusto (p1-p99). Columnas ausentes → 0."""
    df = df.copy()
    for col in ALL_FEATURE_COLS:
        if col not in df.columns or df[col].isna().all():
            logger.warning("[normalize] Columna '%s' ausente o toda NaN → 0.", col)
            df[col] = 0.0
            continue

        p1  = df[col].quantile(0.01)
        p99 = df[col].quantile(0.99)
        rng = p99 - p1

        df[col] = 0.0 if rng == 0 else (df[col].clip(p1, p99) - p1) / rng

    return df
