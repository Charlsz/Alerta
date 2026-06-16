"""Orquestador del motor de riesgo: IRA + anomalías + SHAP.

Uso:
    python scripts/run_risk.py
    python scripts/run_risk.py --force
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time

import pandas as pd

from config import config
from src.features.normalize import normalize
from src.ingestion.load_duckdb import get_connection
from src.risk.anomaly import train_and_score
from src.risk.explainability import compute_top3
from src.risk.ira import compute_subindices

logger = logging.getLogger(__name__)

_TABLE_IN  = "features_municipio_cultivo"
_TABLE_OUT = "ira_resultados"


def run(force: bool = False) -> None:
    """Lee features, calcula IRA + anomalías + SHAP y escribe `ira_resultados`."""
    con = get_connection()

    if not force:
        existing = con.execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = ?",
            [_TABLE_OUT],
        ).fetchone()[0]  # type: ignore[index]
        if existing:
            logger.info("[risk] Tabla '%s' ya existe, omitiendo.", _TABLE_OUT)
            con.close()
            return

    logger.info("[risk] Leyendo tabla de features...")
    df = con.execute(f"SELECT * FROM {_TABLE_IN}").df()
    logger.info("[risk] %d filas leídas.", len(df))

    # 1. Normalizar
    logger.info("[risk] Normalizando features (min-max p1-p99)...")
    df = normalize(df)

    # 2. Sub-índices e IRA
    logger.info("[risk] Calculando sub-índices e IRA...")
    df = compute_subindices(df)

    # 3. Anomalías
    logger.info("[risk] Detectando anomalías (IsolationForest)...")
    df = train_and_score(df)

    # 4. SHAP top-3
    logger.info("[risk] Calculando SHAP top-3 variables...")
    df = compute_top3(df)

    # 5. Serializar top3_variables a JSON string para DuckDB
    df["top3_variables"] = df["top3_variables"].apply(json.dumps, ensure_ascii=False)

    # 6. Guardar resultados
    result_cols = [
        "codigo_municipio", "cultivo", "periodo",
        "spc", "sep", "sve", "ira_score", "ira_nivel",
        "anomaly_score", "is_anomaly", "top3_variables",
    ]
    result = df[[c for c in result_cols if c in df.columns]]
    con.execute(f"CREATE OR REPLACE TABLE {_TABLE_OUT} AS SELECT * FROM result")
    (rows,) = con.execute(f"SELECT COUNT(*) FROM {_TABLE_OUT}").fetchone()  # type: ignore[misc]
    logger.info("[risk] Tabla '%s' creada: %d filas.", _TABLE_OUT, rows)
    con.close()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    parser = argparse.ArgumentParser(description="Calcula IRA, anomalías y SHAP")
    parser.add_argument("--force", action="store_true", help="Fuerza recalculo aunque ya exista")
    args = parser.parse_args()

    t0 = time.time()
    run(force=args.force)
    logger.info("Motor de riesgo completado en %.1fs", time.time() - t0)


if __name__ == "__main__":
    main()
