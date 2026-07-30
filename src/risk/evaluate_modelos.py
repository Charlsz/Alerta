"""Evaluación comparativa de modelos de rendimiento — Paso 7D.

Los pasos 7B (`predict_rendimiento`, XGBoost/RandomForest) y 7C
(`nnet_rendimiento`, MLP) *generan* predicciones de rendimiento, pero
ninguno evalúa su desempeño de forma persistida ni permite comparar
cuál modelo es mejor: el árbol solo loguea R² por validación cruzada y
la red neuronal calcula R² sobre su propio set de entrenamiento (sin
partición, propenso a sobreajuste).

Este módulo cierra ese vacío. Realiza una **partición temporal held-out**
(los períodos más recientes quedan fuera del entrenamiento, evitando
data leakage en una serie temporal), entrena ambos modelos con la misma
partición y calcula métricas comparables sobre el conjunto de prueba:

    - R²   (coeficiente de determinación)
    - MAE  (error absoluto medio, t/ha)
    - RMSE (raíz del error cuadrático medio, t/ha)

Reutiliza los mismos pipelines de producción (`_build_pipeline` de cada
módulo) y la misma lista de predictores, de modo que las métricas
reflejan los modelos que realmente se sirven.

Salida en DuckDB:
    evaluacion_modelos:
        (modelo, r2, mae, rmse, n_train, n_test, periodo_corte, generado_en)
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from src.ingestion.load_duckdb import get_connection, table_exists
from src.risk.nnet_rendimiento import _build_pipeline as _build_nnet_pipeline
from src.risk.predict_rendimiento import _PREDICTOR_COLS
from src.risk.predict_rendimiento import _build_pipeline as _build_tree_pipeline

logger = logging.getLogger(__name__)

_TABLE_OUT = "evaluacion_modelos"
_TEST_FRACTION = 0.2   # Proporción de los períodos más recientes reservada a prueba
_MIN_TEST_ROWS = 20    # Mínimo de filas de prueba para una evaluación fiable


def _prepare_supervised(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series]:
    """Construye el problema supervisado y[t] = rendimiento[t+1].

    Idéntica lógica que `predict_rendimiento` / `nnet_rendimiento` para que
    la evaluación sea representativa de lo que esos modelos aprenden.
    """
    df = df.sort_values(["codigo_municipio", "cultivo", "periodo"]).copy()
    df["target"] = (
        df.groupby(["codigo_municipio", "cultivo"])["rendimiento_promedio"].shift(-1)
    )
    df = df.dropna(subset=["target", "rendimiento_promedio"])

    feature_cols = [c for c in _PREDICTOR_COLS if c in df.columns]
    X = df[feature_cols].fillna(0.0)
    y = df["target"]
    return df, X, y


def _temporal_split(
    df: pd.DataFrame, X: pd.DataFrame, y: pd.Series
) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series, object]:
    """Parte por período: entrena con los más antiguos, prueba con los recientes.

    Un split aleatorio filtraría información del futuro (el rendimiento de
    períodos posteriores) al entrenamiento. Al cortar por período se respeta
    el orden temporal, como ocurriría en producción.
    """
    periodos = np.sort(df["periodo"].unique())
    n_test_periodos = max(1, int(round(len(periodos) * _TEST_FRACTION)))
    periodo_corte = periodos[-n_test_periodos]

    test_mask = df["periodo"] >= periodo_corte
    X_train, X_test = X[~test_mask], X[test_mask]
    y_train, y_test = y[~test_mask], y[test_mask]
    return X_train, X_test, y_train, y_test, periodo_corte


def _evaluate(name: str, pipe, X_train, y_train, X_test, y_test) -> dict:
    """Entrena en train, mide en test. Devuelve fila de métricas."""
    pipe.fit(X_train, y_train)
    y_pred = pipe.predict(X_test)

    metrics = {
        "modelo": name,
        "r2":   round(float(r2_score(y_test, y_pred)), 4),
        "mae":  round(float(mean_absolute_error(y_test, y_pred)), 4),
        "rmse": round(float(np.sqrt(mean_squared_error(y_test, y_pred))), 4),
        "n_train": int(len(X_train)),
        "n_test":  int(len(X_test)),
    }
    logger.info(
        "[eval] %-12s | R²=%.3f  MAE=%.3f  RMSE=%.3f  (train=%d, test=%d)",
        name, metrics["r2"], metrics["mae"], metrics["rmse"],
        metrics["n_train"], metrics["n_test"],
    )
    return metrics


def evaluate_models(df: pd.DataFrame) -> pd.DataFrame:
    """Evalúa XGBoost/RF y la red neuronal sobre la misma partición temporal.

    Returns:
        DataFrame con una fila por modelo:
            (modelo, r2, mae, rmse, n_train, n_test, periodo_corte, generado_en)
        Vacío si no hay suficientes datos para una evaluación fiable.
    """
    df_sup, X, y = _prepare_supervised(df)
    if df_sup.empty:
        logger.warning("[eval] Sin filas supervisadas (falta rendimiento t+1).")
        return pd.DataFrame()

    X_train, X_test, y_train, y_test, periodo_corte = _temporal_split(df_sup, X, y)

    if len(X_test) < _MIN_TEST_ROWS or len(X_train) < _MIN_TEST_ROWS:
        logger.warning(
            "[eval] Datos insuficientes tras split temporal (train=%d, test=%d).",
            len(X_train), len(X_test),
        )
        return pd.DataFrame()

    filas = [
        _evaluate("arbol_gbm", _build_tree_pipeline(), X_train, y_train, X_test, y_test),
        _evaluate("red_neuronal", _build_nnet_pipeline(), X_train, y_train, X_test, y_test),
    ]

    generado = datetime.now(timezone.utc).isoformat()
    for f in filas:
        f["periodo_corte"] = str(periodo_corte)
        f["generado_en"] = generado

    resultado = pd.DataFrame(filas)
    mejor = resultado.loc[resultado["r2"].idxmax(), "modelo"]
    logger.info("[eval] Mejor modelo por R²: %s", mejor)
    return resultado


def build(force: bool = False) -> None:
    """Punto de entrada del pipeline. Lee features, evalúa, guarda en DuckDB."""
    con = get_connection()

    if not force and table_exists(con, _TABLE_OUT):
        logger.info("[eval] Tabla '%s' ya existe, omitiendo.", _TABLE_OUT)
        con.close()
        return

    logger.info("[eval] Cargando tabla maestra de features...")
    df = con.execute("SELECT * FROM features_municipio_cultivo").df()

    if df.empty:
        logger.error("[eval] features_municipio_cultivo está vacía. Ejecuta features primero.")
        con.close()
        return

    resultado = evaluate_models(df)
    if resultado.empty:
        con.close()
        return

    con.execute(f"CREATE OR REPLACE TABLE {_TABLE_OUT} AS SELECT * FROM resultado")
    (rows,) = con.execute(f"SELECT COUNT(*) FROM {_TABLE_OUT}").fetchone()  # type: ignore[misc]
    logger.info("[eval] Tabla '%s' creada: %d modelos evaluados.", _TABLE_OUT, rows)
    con.close()
