"""Ingesta de NDVI (índice de vegetación) desde HDX.

Fuente: https://data.humdata.org/dataset/col-ndvi-subnational
Datos MODIS agregados por unidad administrativa (P-code = código DANE).
Incluye NDVI dekadal, promedio histórico y anomalía (%).
"""
from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from config import config

logger = logging.getLogger(__name__)

_URL = "https://data.humdata.org/dataset/7f2ba5ba-8df1-41cf-ab18-fc1da928a1e5/resource/be4beefc-ee9d-4eed-ad5f-d99b08975a8e/download/col-ndvi-subnat-5ytd.csv"
_OUTPUT = "ndvi.parquet"


def run(force: bool = False) -> None:
    output_path = Path(config.data_raw) / _OUTPUT
    if output_path.exists() and not force:
        logger.info("[NDVI] Ya existe %s, omitiendo.", _OUTPUT)
        return

    logger.info("[NDVI] Descargando desde HDX (5 años)...")
    df = pd.read_csv(_URL, low_memory=False)
    logger.info("[NDVI] Descargadas %d filas.", len(df))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(output_path, index=False)

    cols = list(df.columns)
    logger.info("[NDVI] Guardado en %s. Columnas: %s", output_path, cols)
    if not df.empty:
        logger.info("[NDVI] Rango fechas: %s -> %s", df["date"].min(), df["date"].max())
