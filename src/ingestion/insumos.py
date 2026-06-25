"""Ingesta del Índice de Precios de Insumos Agrícolas (UPRA) desde datos.gov.co."""
from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from config import config
from src.ingestion._soda import fetch_soda

logger = logging.getLogger(__name__)

_DATASET_ID = "gwbi-fnzs"
_OUTPUT = "insumos.parquet"


def run(force: bool = False) -> None:
    """Descarga el índice de insumos agrícolas a data/raw/."""
    output_path = Path(config.data_raw) / _OUTPUT
    if output_path.exists() and not force:
        logger.info("[Índice Insumos] Ya existe %s, omitiendo.", _OUTPUT)
        return

    # Dataset pequeño (serie mensual nacional) — descarga completa sin filtros
    records = fetch_soda(_DATASET_ID, page_size=config.soda_page_size)
    df = pd.DataFrame(records)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(output_path, index=False)
    logger.info("[Índice Insumos] %d filas guardadas en %s", len(df), output_path)

