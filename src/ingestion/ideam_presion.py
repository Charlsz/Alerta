"""Ingesta de Presión Atmosférica IDEAM desde datos.gov.co.

Volumen total: ~33.9 M filas. Se filtra por los últimos 5 años.

Variable que aporta: presion_atmosferica (hPa).
Fuente: https://www.datos.gov.co/resource/62tk-nxj5
"""
from __future__ import annotations

import datetime
import logging
from pathlib import Path

import pandas as pd

from config import config
from src.ingestion._soda import fetch_soda

logger = logging.getLogger(__name__)

_DATASET_ID = "62tk-nxj5"
_OUTPUT = "ideam_presion.parquet"
_YEARS_BACK = 5


def run(force: bool = False) -> None:
    """Descarga presión atmosférica IDEAM (últimos 5 años) a data/raw/."""
    output_path = Path(config.data_raw) / _OUTPUT
    if output_path.exists() and not force:
        logger.info("[Presión IDEAM] Ya existe %s, omitiendo.", _OUTPUT)
        return

    cutoff = datetime.date.today() - datetime.timedelta(days=_YEARS_BACK * 365)
    where = f"fechaobservacion >= '{cutoff.isoformat()}'"

    logger.info("[Presión IDEAM] Descargando desde %s (~33.9 M filas totales)...", cutoff)
    records = fetch_soda(
        _DATASET_ID,
        page_size=config.soda_page_size,
        where=where,
        order="fechaobservacion",
    )

    df = pd.DataFrame(records)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(output_path, index=False)

    if "fechaobservacion" in df.columns and not df.empty:
        fechas = pd.to_datetime(df["fechaobservacion"], errors="coerce")
        logger.info(
            "[Presión IDEAM] %d filas | %s → %s | guardado en %s",
            len(df), fechas.min().date(), fechas.max().date(), output_path,
        )
    else:
        logger.info("[Presión IDEAM] %d filas guardadas en %s", len(df), output_path)

