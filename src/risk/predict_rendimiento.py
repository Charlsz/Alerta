"""Modelo predictivo de rendimiento agrícola — Paso 7B.

Implementa un pipeline de Machine Learning para predecir el rendimiento
esperado (t/ha) del próximo ciclo agrícola por municipio y cultivo.

Arquitectura:
    - Modelo base: XGBoost Regressor (o RandomForest como fallback)
    - Features: 26 variables de features_municipio_cultivo
    - Target: rendimiento del período siguiente (t+1)
    - Estrategia: un modelo por cultivo si hay >= MIN_SAMPLES; global otherwise
    - Explicabilidad: SHAP TreeExplainer
    - Persistencia: data/models/rendimiento_{cultivo}.joblib

Salidas en DuckDB:
    predicciones_rendimiento:
        (codigo_municipio, cultivo, periodo, rendimiento_predicho,
         rendimiento_ic_inf, rendimiento_ic_sup, importancia_top3)
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from config import config
from src.features.normalize import ALL_FEATURE_COLS
from src.ingestion.load_duckdb import get_connection, table_exists

logger = logging.getLogger(__name__)

_MODELS_DIR  = Path("data/models")
_TABLE_OUT   = "predicciones_rendimiento"
_MIN_SAMPLES = 50    # Mínimo de filas para entrenar modelo por cultivo
_N_ESTIMATORS = 200
_CV_FOLDS     = 5

# Columnas de features que alimentan el modelo predictivo
# (excluye SEP derivadas del propio rendimiento para evitar data leakage)
_PREDICTOR_COLS = [
    # SPC — clima
    "precip_acum_7d", "precip_acum_30d", "precip_anomalia_30d",
    "dias_secos_consecutivos", "dias_lluvia_extrema",
    "tmax_media_7d", "tmax_anomalia_30d", "dias_tmax_critica",
    "humedad_media_30d", "humedad_anomalia_30d",
    "presion_media_30d", "presion_anomalia_30d",
    "tambiente_media_30d", "tmin_media_30d",
    # SEP — exposición (sin rendimiento para no hacer leakage)
    "area_sembrada", "area_cosechada", "participacion_municipal", "fase_fenologica",
    # SVE — vulnerabilidad
    "insumos_nivel", "insumos_anomalia_12m", "insumos_delta_3m",
    "nbi_total", "pct_rural",
]


def _model_path(cultivo: str) -> Path:
    return _MODELS_DIR / f"rendimiento_{cultivo.replace(' ', '_').lower()}.joblib"


def _build_pipeline() -> Pipeline:
    """Pipeline: escalar + RandomForestRegressor.

    Se usa RandomForest como modelo base porque:
    1. No requiere dependencias extra (XGBoost opcional).
    2. Soporta bien datos mixtos con muchos NaN imputados.
    3. Provee importancia de variables nativa compatible con SHAP.

    Si xgboost está instalado se usa XGBRegressor por mejor desempeño.
    """
    try:
        from xgboost import XGBRegressor  # type: ignore[import-untyped]
        regressor = XGBRegressor(
            n_estimators=_N_ESTIMATORS,
            max_depth=6,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            n_jobs=-1,
            verbosity=0,
        )
        logger.info("[predict] Usando XGBRegressor.")
    except ImportError:
        regressor = RandomForestRegressor(
            n_estimators=_N_ESTIMATORS,
            max_depth=12,
            min_samples_leaf=5,
            random_state=42,
            n_jobs=-1,
        )
        logger.info("[predict] XGBoost no instalado. Usando RandomForestRegressor.")

    return Pipeline([
        ("scaler", StandardScaler()),
        ("model",  regressor),
    ])


def _prepare_dataset(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """Prepara X e y con ventana deslizante: y[t] = rendimiento[t+1].

    Esto construye un problema de predicción supervisada donde
    las features del período actual predicen el rendimiento siguiente.
    """
    df = df.sort_values(["codigo_municipio", "cultivo", "periodo"]).copy()
    # Target: rendimiento del siguiente período en el mismo municipio-cultivo
    df["target"] = df.groupby(["codigo_municipio", "cultivo"])["rendimiento_promedio"].shift(-1)
    df = df.dropna(subset=["target", "rendimiento_promedio"])

    feature_cols = [c for c in _PREDICTOR_COLS if c in df.columns]
    X = df[feature_cols].fillna(0.0)
    y = df["target"]
    return df, X, y


def _get_shap_top3(pipe: Pipeline, X_sample: pd.DataFrame) -> list[dict]:
    """Extrae las 3 variables más importantes del modelo.

    Intenta SHAP TreeExplainer primero; fallback a feature_importances_.
    """
    feature_cols = list(X_sample.columns)
    try:
        import shap  # type: ignore[import-untyped]
        model = pipe.named_steps["model"]
        X_scaled = pipe.named_steps["scaler"].transform(X_sample)
        explainer = shap.TreeExplainer(model)
        shap_vals = explainer.shap_values(X_scaled)
        mean_abs  = np.abs(shap_vals).mean(axis=0)
        top3_idx  = np.argsort(mean_abs)[::-1][:3]
        return [
            {"var": feature_cols[i], "shap": round(float(mean_abs[i]), 4)}
            for i in top3_idx
        ]
    except Exception:  # noqa: BLE001
        # Fallback: feature_importances_ nativas (RF / XGB)
        model = pipe.named_steps["model"]
        if hasattr(model, "feature_importances_"):
            imp = model.feature_importances_
            top3_idx = np.argsort(imp)[::-1][:3]
            return [
                {"var": feature_cols[i], "importance": round(float(imp[i]), 4)}
                for i in top3_idx
            ]
    return []


def train_and_predict(df: pd.DataFrame, force: bool = False) -> pd.DataFrame:
    """Entrena un modelo por cultivo y genera predicciones de rendimiento.

    Args:
        df: DataFrame con features_municipio_cultivo (26 vars + rendimiento_promedio).
        force: Si True, re-entrena aunque ya exista el modelo.

    Returns:
        DataFrame con columnas:
            codigo_municipio, cultivo, periodo,
            rendimiento_predicho, rendimiento_ic_inf, rendimiento_ic_sup,
            importancia_top3 (JSON string)
    """
    _MODELS_DIR.mkdir(parents=True, exist_ok=True)

    df_prep, X_all, y_all = _prepare_dataset(df)
    feature_cols = list(X_all.columns)

    resultados: list[pd.DataFrame] = []
    cultivos = df_prep["cultivo"].unique()

    for cultivo in cultivos:
        mask   = df_prep["cultivo"] == cultivo
        df_c   = df_prep[mask].copy()
        X_c    = X_all[mask]
        y_c    = y_all[mask]

        if len(df_c) < _MIN_SAMPLES:
            logger.warning(
                "[predict] Cultivo '%s': solo %d muestras, usando modelo global.",
                cultivo, len(df_c),
            )
            X_train, y_train = X_all, y_all
        else:
            X_train, y_train = X_c, y_c

        model_path = _model_path(cultivo)
        if model_path.exists() and not force:
            pipe = joblib.load(model_path)
            logger.info("[predict] Modelo cargado para '%s'.", cultivo)
        else:
            pipe = _build_pipeline()
            pipe.fit(X_train, y_train)

            # Validación cruzada (solo para cultivos con suficientes datos)
            if len(X_train) >= _CV_FOLDS * 10:
                cv_scores = cross_val_score(
                    pipe, X_train, y_train,
                    cv=_CV_FOLDS, scoring="r2", n_jobs=-1,
                )
                logger.info(
                    "[predict] Cultivo '%s' | R² CV: %.3f ± %.3f (n=%d)",
                    cultivo, cv_scores.mean(), cv_scores.std(), len(X_train),
                )

            joblib.dump(pipe, model_path)
            logger.info("[predict] Modelo entrenado y guardado: %s", model_path)

        # Predicciones sobre el conjunto del cultivo
        y_pred = pipe.predict(X_c)

        # Intervalo de confianza: ±1 std de los árboles (RF) o estimación simple (XGB)
        try:
            model = pipe.named_steps["model"]
            X_c_scaled = pipe.named_steps["scaler"].transform(X_c)
            if hasattr(model, "estimators_"):
                tree_preds = np.array([t.predict(X_c_scaled) for t in model.estimators_])
                ic_std     = tree_preds.std(axis=0)
            else:
                ic_std = np.full(len(y_pred), y_pred.std() * 0.1)
        except Exception:  # noqa: BLE001
            ic_std = np.zeros(len(y_pred))

        # Top-3 variables explicativas
        importancia = _get_shap_top3(pipe, X_c.head(min(200, len(X_c))))
        importancia_json = json.dumps(importancia, ensure_ascii=False)

        result_c = df_c[["codigo_municipio", "cultivo", "periodo"]].copy()
        result_c["rendimiento_predicho"]  = y_pred.round(3)
        result_c["rendimiento_ic_inf"]    = (y_pred - 1.96 * ic_std).round(3)
        result_c["rendimiento_ic_sup"]    = (y_pred + 1.96 * ic_std).round(3)
        result_c["importancia_top3"]      = importancia_json

        resultados.append(result_c)

    if not resultados:
        logger.warning("[predict] No se generaron predicciones.")
        return pd.DataFrame()

    final = pd.concat(resultados, ignore_index=True)
    logger.info(
        "[predict] Predicciones generadas: %d filas para %d cultivos.",
        len(final), len(cultivos),
    )
    return final


def build(force: bool = False) -> None:
    """Punto de entrada del pipeline. Lee features, entrena, guarda en DuckDB."""
    con = get_connection()

    if not force and table_exists(con, _TABLE_OUT):
        logger.info("[predict] Tabla '%s' ya existe, omitiendo.", _TABLE_OUT)
        con.close()
        return

    logger.info("[predict] Cargando tabla maestra de features...")
    df = con.execute("SELECT * FROM features_municipio_cultivo").df()

    if df.empty:
        logger.error("[predict] features_municipio_cultivo está vacía. Ejecuta el pipeline de features primero.")
        con.close()
        return

    logger.info("[predict] Iniciando entrenamiento y predicción (%d filas)...", len(df))
    predictions = train_and_predict(df, force=force)

    if predictions.empty:
        con.close()
        return

    con.execute(f"CREATE OR REPLACE TABLE {_TABLE_OUT} AS SELECT * FROM predictions")
    (rows,) = con.execute(f"SELECT COUNT(*) FROM {_TABLE_OUT}").fetchone()  # type: ignore[misc]
    logger.info("[predict] Tabla '%s' creada: %d predicciones.", _TABLE_OUT, rows)
    con.close()
