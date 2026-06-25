"""Ingesta del catálogo de estaciones IDEAM desde datos.gov.co."""
from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from config import config
from src.ingestion._soda import fetch_soda

logger = logging.getLogger(__name__)

_DATASET_ID = "hp9r-jxuu"
_OUTPUT = "ideam_estaciones.parquet"


def run(force: bool = False) -> None:
    """Descarga el catálogo de estaciones IDEAM a data/raw/."""
    output_path = Path(config.data_raw) / _OUTPUT
    if output_path.exists() and not force:
        logger.info("[Estaciones IDEAM] Ya existe %s, omitiendo.", _OUTPUT)
        return

    # Dataset pequeño (~5k filas) — no necesita filtro de fecha ni order
    records = fetch_soda(_DATASET_ID, page_size=config.soda_page_size)
    df = pd.DataFrame(records)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(output_path, index=False)
    logger.info("[Estaciones IDEAM] %d estaciones guardadas en %s", len(df), output_path)

