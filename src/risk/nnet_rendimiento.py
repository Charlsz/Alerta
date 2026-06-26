"""Red neuronal para predicción de rendimiento agrícola.

Usa MLPRegressor (sklearn) — red neuronal con 2 capas ocultas.
No requiere dependencias adicionales (TF/PyTorch).

Almacena resultados en la tabla `predicciones_nnet`.
"""
from __future__ import annotations

import logging
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from config import config
from src.ingestion.load_duckdb import get_connection
from src.risk.predict_rendimiento import _PREDICTOR_COLS

logger = logging.getLogger(__name__)

_MODELS_DIR = Path("data/models")
_TABLE_OUT = "predicciones_nnet"
_N_ITER = 500


def _build_pipeline() -> Pipeline:
    return Pipeline([
        ("scaler", StandardScaler()),
        ("model", MLPRegressor(
            hidden_layer_sizes=(64, 32),
            activation="relu",
            solver="adam",
            max_iter=_N_ITER,
            random_state=42,
            early_stopping=True,
            validation_fraction=0.1,
            n_iter_no_change=20,
            verbose=False,
        )),
    ])


def train_and_predict(df: pd.DataFrame, force: bool = False) -> pd.DataFrame:
    _MODELS_DIR.mkdir(parents=True, exist_ok=True)

    df = df.sort_values(["codigo_municipio", "cultivo", "periodo"]).copy()
    df["target"] = df.groupby(["codigo_municipio", "cultivo"])["rendimiento_promedio"].shift(-1)
    df = df.dropna(subset=["target"])

    feature_cols = [c for c in _PREDICTOR_COLS if c in df.columns]
    X = df[feature_cols].fillna(0.0)
    y = df["target"]
    grupos = df[["codigo_municipio", "cultivo", "periodo"]]

    model_path = _MODELS_DIR / "nnet_rendimiento.joblib"
    if model_path.exists() and not force:
        pipe = joblib.load(model_path)
        logger.info("[nnet] Modelo cargado.")
    else:
        pipe = _build_pipeline()
        pipe.fit(X, y)
        train_score = pipe.score(X, y)
        logger.info("[nnet] Modelo entrenado. R² train: %.4f (n=%d)", train_score, len(X))
        joblib.dump(pipe, model_path)

    y_pred = pipe.predict(X)
    resultado = grupos.copy()
    resultado["rendimiento_nnet"] = y_pred.round(3)
    resultado["nnet_ic_inf"] = (y_pred - y_pred.std() * 1.96).round(3)
    resultado["nnet_ic_sup"] = (y_pred + y_pred.std() * 1.96).round(3)
    return resultado


def build(force: bool = False) -> None:
    con = get_connection()
    if not force:
        exists = con.execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = ?",
            [_TABLE_OUT],
        ).fetchone()[0]
        if exists:
            logger.info("[nnet] Tabla '%s' ya existe, omitiendo.", _TABLE_OUT)
            con.close()
            return

    logger.info("[nnet] Cargando features...")
    df = con.execute("SELECT * FROM features_municipio_cultivo").df()
    if df.empty:
        logger.error("[nnet] features_municipio_cultivo vacía.")
        con.close()
        return

    predictions = train_and_predict(df, force=force)
    con.execute(f"CREATE OR REPLACE TABLE {_TABLE_OUT} AS SELECT * FROM predictions")
    (rows,) = con.execute(f"SELECT COUNT(*) FROM {_TABLE_OUT}").fetchone()
    logger.info("[nnet] Tabla '%s' creada: %d filas.", _TABLE_OUT, rows)
    con.close()
