"""Explicabilidad del IRA con SHAP.

Genera las top-3 variables que más contribuyen al score de cada fila.
Se usa KernelExplainer sobre el IRA final (caja blanca) para mantenerlo
compatible con cualquier cambio de modelo.
"""
from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd
import shap

from config import config
from src.features.normalize import ALL_FEATURE_COLS, _SEP_COLS, _SPC_COLS, _SVE_COLS

logger = logging.getLogger(__name__)

# Etiquetas legibles para la UI (en español, sin nombre de columna crudo)
_LABELS: dict[str, str] = {
    "precip_acum_7d":           "Lluvia acumulada 7 días",
    "precip_acum_30d":          "Lluvia acumulada 30 días",
    "precip_anomalia_30d":      "Anomalía de lluvia vs. histórico",
    "dias_secos_consecutivos":  "Días secos consecutivos",
    "dias_lluvia_extrema":      "Días con lluvia extrema",
    "tmax_media_7d":            "Temperatura máxima media 7 días",
    "tmax_anomalia_30d":        "Anomalía de temperatura vs. histórico",
    "dias_tmax_critica":        "Días con temperatura crítica",
    "area_sembrada":            "Área sembrada",
    "area_cosechada":           "Área cosechada",
    "rendimiento_promedio":     "Rendimiento promedio histórico",
    "rendimiento_cv":           "Variabilidad del rendimiento",
    "participacion_municipal":  "Participación en producción nacional",
    "fase_fenologica":          "Fase crítica (siembra o cosecha)",
    "insumos_nivel":            "Nivel de precios de insumos",
    "insumos_anomalia_12m":     "Anomalía de precios vs. 12 meses",
    "insumos_delta_3m":         "Cambio de precios en 3 meses",
}


def _ira_predictor(X: np.ndarray, feature_cols: list[str]) -> np.ndarray:
    """Función que replica el cálculo del IRA para SHAP.

    Recibe matriz X y devuelve array de scores IRA.
    """
    df = pd.DataFrame(X, columns=feature_cols)

    spc_cols = [c for c in _SPC_COLS if c in feature_cols]
    sep_cols = [c for c in _SEP_COLS if c in feature_cols]
    sve_cols = [c for c in _SVE_COLS if c in feature_cols]

    spc = df[spc_cols].mean(axis=1).fillna(0)
    sep = df[sep_cols].mean(axis=1).fillna(0)
    sve = df[sve_cols].mean(axis=1).fillna(0)

    return (config.w_spc * spc + config.w_sep * sep + config.w_sve * sve).clip(0, 1).values


def compute_top3(df: pd.DataFrame, sample_size: int = 100) -> pd.DataFrame:
    """Calcula las top-3 variables SHAP por fila.

    Para eficiencia, usa un subconjunto aleatorio como background de SHAP.
    Retorna df con columna `top3_variables` (lista de dicts con 'var', 'label', 'shap').

    Args:
        df: DataFrame con columnas normalizadas de features.
        sample_size: Tamaño del background para KernelExplainer.
    """
    feature_cols = [c for c in ALL_FEATURE_COLS if c in df.columns]
    X = df[feature_cols].fillna(0).values

    background = shap.kmeans(X, min(sample_size, len(X)))

    def predictor(x: np.ndarray) -> np.ndarray:
        return _ira_predictor(x, feature_cols)

    explainer = shap.KernelExplainer(predictor, background)

    logger.info("[SHAP] Calculando valores SHAP para %d filas...", len(X))
    shap_values = explainer.shap_values(X, nsamples=50, silent=True)  # nsamples bajo para velocidad

    top3_list = []
    for row_shap in shap_values:
        abs_shap = np.abs(row_shap)
        top_idx  = abs_shap.argsort()[::-1][:3]
        top3 = [
            {
                "var":   feature_cols[i],
                "label": _LABELS.get(feature_cols[i], feature_cols[i]),
                "shap":  round(float(row_shap[i]), 4),
            }
            for i in top_idx
        ]
        top3_list.append(top3)

    df = df.copy()
    df["top3_variables"] = top3_list
    return df
