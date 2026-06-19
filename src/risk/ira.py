"""Cálculo del Índice de Riesgo Agroclimático (IRA).

Fórmula:
    IRA = w_spc * SPC + w_sep * SEP + w_sve * SVE

Cada sub-índice es el promedio simple de sus variables normalizadas (0-1).
Las ponderaciones viven en config.py.
"""
from __future__ import annotations

import logging

import pandas as pd

from config import config
from src.features.normalize import ALL_FEATURE_COLS, _SEP_COLS, _SPC_COLS, _SVE_COLS
from src.risk.classify import classify_ira

logger = logging.getLogger(__name__)


def compute_subindices(df: pd.DataFrame) -> pd.DataFrame:
    """Calcula SPC, SEP, SVE e IRA para cada fila del DataFrame normalizado.

    Precondición: df ya tiene las columnas de ALL_FEATURE_COLS normalizadas en [0,1].
    """
    df = df.copy()

    # Sub-índices como promedio de sus variables (NaN se ignoran con nanmean)
    df["spc"] = df[[c for c in _SPC_COLS if c in df.columns]].mean(axis=1, skipna=True)
    df["sep"] = df[[c for c in _SEP_COLS if c in df.columns]].mean(axis=1, skipna=True)
    df["sve"] = df[[c for c in _SVE_COLS if c in df.columns]].mean(axis=1, skipna=True)

    # IRA ponderado
    df["ira_score"] = (
        config.w_spc * df["spc"]
        + config.w_sep * df["sep"]
        + config.w_sve * df["sve"]
    ).clip(0.0, 1.0)

    df["ira_nivel"] = df["ira_score"].map(classify_ira)

    logger.info(
        "[IRA] Scores calculados para %d filas. Distribución:\n%s",
        len(df),
        df["ira_nivel"].value_counts().to_string(),
    )
    return df
