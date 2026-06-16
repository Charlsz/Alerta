"""Normalización min-max robusta de features para el cálculo del IRA.

Usa percentiles p1-p99 para evitar que outliers extremos colapsen la escala.
Resultado: todas las variables numéricas en [0, 1].
"""
from __future__ import annotations

import logging

import pandas as pd

logger = logging.getLogger(__name__)

# Columnas a normalizar para cada sub-índice
_SPC_COLS = [
    "precip_acum_7d", "precip_acum_30d", "precip_anomalia_30d",
    "dias_secos_consecutivos", "dias_lluvia_extrema",
    "tmax_media_7d", "tmax_anomalia_30d", "dias_tmax_critica",
]
_SEP_COLS = [
    "area_sembrada", "area_cosechada", "rendimiento_promedio",
    "rendimiento_cv", "participacion_municipal", "fase_fenologica",
]
_SVE_COLS = [
    "insumos_nivel", "insumos_anomalia_12m", "insumos_delta_3m",
]

ALL_FEATURE_COLS = _SPC_COLS + _SEP_COLS + _SVE_COLS


def normalize(df: pd.DataFrame) -> pd.DataFrame:
    """Normaliza con min-max robusto (p1-p99) las columnas de features.

    Las columnas que no existen o son completamente NaN se rellenan con 0.
    """
    df = df.copy()
    for col in ALL_FEATURE_COLS:
        if col not in df.columns or df[col].isna().all():
            logger.warning("[normalize] Columna '%s' ausente o toda NaN. Se asigna 0.", col)
            df[col] = 0.0
            continue

        p1  = df[col].quantile(0.01)
        p99 = df[col].quantile(0.99)
        rng = p99 - p1

        if rng == 0:
            # Variable constante: no aporta información, se fija en 0
            df[col] = 0.0
        else:
            df[col] = (df[col].clip(p1, p99) - p1) / rng

    return df
