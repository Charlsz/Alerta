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
from src.features.normalize import _SEP_COLS, _SPC_COLS, _SVE_COLS, normalize
from src.ingestion.load_duckdb import get_connection, table_exists

logger = logging.getLogger(__name__)

_TABLE = "ira_scores"


def classify_ira(score: float) -> str:
    for nivel, (lo, hi) in config.ira_niveles.items():
        if lo <= score < hi:
            return nivel
    return "Crítico"


def compute_subindices(df: pd.DataFrame) -> pd.DataFrame:
    """Calcula SPC, SEP, SVE e IRA para cada fila del DataFrame normalizado.

    Precondición: df ya tiene las columnas de ALL_FEATURE_COLS normalizadas en [0,1].
    """
    df = df.copy()

    df["spc"] = df[[c for c in _SPC_COLS if c in df.columns]].mean(axis=1, skipna=True)
    df["sep"] = df[[c for c in _SEP_COLS if c in df.columns]].mean(axis=1, skipna=True)
    df["sve"] = df[[c for c in _SVE_COLS if c in df.columns]].mean(axis=1, skipna=True)

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


def build(force: bool = False) -> None:
    """Lee features_municipio_cultivo, normaliza, calcula IRA y guarda en DuckDB."""
    con = get_connection()

    if not force and table_exists(con, _TABLE):

        logger.info("...", _TABLE)

        return

    logger.info("[IRA] Leyendo features_municipio_cultivo...")
    df = con.execute("SELECT * FROM features_municipio_cultivo").df()
    if df.empty:
        logger.error("[IRA] features_municipio_cultivo vacía.")
        con.close()
        return

    key_cols = ["codigo_municipio", "cultivo", "periodo"]
    keys = df[key_cols].copy()
    features = normalize(df)

    result = compute_subindices(features)
    result = pd.concat([keys, result[["spc", "sep", "sve", "ira_score", "ira_nivel"]]], axis=1)

    con.execute(f"CREATE OR REPLACE TABLE {_TABLE} AS SELECT * FROM result")
    (rows,) = con.execute(f"SELECT COUNT(*) FROM {_TABLE}").fetchone()
    logger.info("[IRA] '%s' creada: %d filas.", _TABLE, rows)
    con.close()
