"""Ingesta de datos EVA (Evaluaciones Agropecuarias Municipales) desde datos.gov.co."""
from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from config import config
from src.ingestion._soda import fetch_soda

logger = logging.getLogger(__name__)

# Resource IDs en datos.gov.co
_EVA_ID = "2pnw-mmge"
_EVA_VISTA_ID = "fp29-z39g"


def _save(records: list[dict], output_path: Path, label: str) -> None:
    """Convierte lista de registros a Parquet y guarda en disco."""
    df = pd.DataFrame(records)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(output_path, index=False)
    logger.info("[%s] %d filas guardadas en %s", label, len(df), output_path)


def run(force: bool = False) -> None:
    """Descarga EVA y EVA Vista a data/raw/."""
    datasets = [
        (_EVA_ID, Path(config.data_raw) / "eva.parquet", "EVA"),
        (_EVA_VISTA_ID, Path(config.data_raw) / "eva_vista.parquet", "EVA Vista"),
    ]

    for dataset_id, output_path, label in datasets:
        if output_path.exists() and not force:
            logger.info("[%s] Ya existe %s, omitiendo.", label, output_path.name)
            continue
        records = fetch_soda(dataset_id, page_size=config.soda_page_size)
        _save(records, output_path, label)

