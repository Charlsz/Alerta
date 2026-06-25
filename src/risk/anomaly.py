"""Detección de anomalías multivariadas con IsolationForest.

Entrena un modelo por cultivo (o uno global si hay pocos datos).
Genera `anomaly_score` y `is_anomaly` por fila.

El modelo entrenado se serializa en data/models/ para que la API
lo cargue sin volver a entrenar.
"""
from __future__ import annotations

import logging
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from config import config
from src.features.normalize import ALL_FEATURE_COLS, normalize
from src.ingestion.load_duckdb import get_connection

logger = logging.getLogger(__name__)

_MODELS_DIR = Path("data/models")
_MIN_SAMPLES = 30   # Mínimo de filas para entrenar un modelo por cultivo
_CONTAMINATION = 0.05  # Fracción esperada de anomalías


def _model_path(cultivo: str) -> Path:
    return _MODELS_DIR / f"iforest_{cultivo.replace(' ', '_')}.joblib"


def _build_pipeline() -> Pipeline:
    """Pipeline: estandarizar + IsolationForest."""
    return Pipeline([
        ("scaler", StandardScaler()),
        ("iforest", IsolationForest(
            n_estimators=100,
            contamination=_CONTAMINATION,
            random_state=42,
            n_jobs=-1,
        )),
    ])


def train_and_score(df: pd.DataFrame) -> pd.DataFrame:
    """Entrena IsolationForest por cultivo y asigna score de anomalía.

    Args:
        df: DataFrame con columnas de ALL_FEATURE_COLS + 'cultivo'.

    Returns:
        df con columnas adicionales `anomaly_score` y `is_anomaly`.
    """
    _MODELS_DIR.mkdir(parents=True, exist_ok=True)
    df = df.copy()
    df["anomaly_score"] = np.nan
    df["is_anomaly"]    = False

    feature_cols = [c for c in ALL_FEATURE_COLS if c in df.columns]
    X_all = df[feature_cols].fillna(0).values

    cultivos = df["cultivo"].unique()
    for cultivo in cultivos:
        mask   = df["cultivo"] == cultivo
        X_cult = X_all[mask]

        if len(X_cult) < _MIN_SAMPLES:
            logger.warning(
                "[anomaly] Cultivo '%s': solo %d muestras, usando modelo global.",
                cultivo, len(X_cult),
            )
            X_cult = X_all  # usar todos los datos como proxy
            fit_mask = slice(None)  # entrenar con todo
        else:
            fit_mask = mask

        model_path = _model_path(cultivo)
        if model_path.exists():
            pipe = joblib.load(model_path)
            logger.info("[anomaly] Modelo cargado para '%s'.", cultivo)
        else:
            pipe = _build_pipeline()
            pipe.fit(X_all[fit_mask] if isinstance(fit_mask, np.ndarray) else X_all)
            joblib.dump(pipe, model_path)
            logger.info("[anomaly] Modelo entrenado y guardado para '%s'.", cultivo)

        # IsolationForest: score_samples devuelve valores negativos (más negativo = más anómalo)
        raw_scores = pipe.named_steps["iforest"].score_samples(
            pipe.named_steps["scaler"].transform(X_cult)
        )
        # Invertir y normalizar a [0,1] para que más alto = más anómalo
        scores_normalized = 1 - (raw_scores - raw_scores.min()) / (
            raw_scores.max() - raw_scores.min() + 1e-9
        )
        predictions = pipe.predict(X_cult)  # -1 = anómalo, 1 = normal

        df.loc[mask, "anomaly_score"] = scores_normalized
        df.loc[mask, "is_anomaly"]    = predictions == -1

    return df


_TABLE = "anomaly_scores"


def build(force: bool = False) -> None:
    """Lee features_municipio_cultivo, normaliza, entrena IsolationForest y guarda."""
    con = get_connection()

    if not force:
        exists = con.execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = ?",
            [_TABLE],
        ).fetchone()[0]
        if exists:
            logger.info("[anomaly] '%s' ya existe, omitiendo.", _TABLE)
            con.close()
            return

    logger.info("[anomaly] Leyendo features_municipio_cultivo...")
    df = con.execute("SELECT * FROM features_municipio_cultivo").df()
    if df.empty:
        logger.error("[anomaly] features_municipio_cultivo vacía.")
        con.close()
        return

    key_cols = ["codigo_municipio", "cultivo", "periodo"]
    keys = df[key_cols].copy()
    features = normalize(df)

    result = train_and_score(features)
    result = pd.concat([keys, result[["anomaly_score", "is_anomaly"]]], axis=1)

    con.execute(f"CREATE OR REPLACE TABLE {_TABLE} AS SELECT * FROM result")
    (rows,) = con.execute(f"SELECT COUNT(*) FROM {_TABLE}").fetchone()
    logger.info("[anomaly] '%s' creada: %d filas.", _TABLE, rows)
    con.close()
