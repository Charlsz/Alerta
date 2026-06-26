"""Ingesta de Humedad del Aire IDEAM desde datos.gov.co.

Volumen total: ~86.8 M filas. Se filtra por los últimos 5 años
y se usa $order para garantizar paginación determinista.

Variable que aporta: humedad_relativa (%).
Fuente: https://www.datos.gov.co/resource/uext-mhny
"""
from __future__ import annotations

import datetime
import logging
from pathlib import Path

import pandas as pd

from config import config
from src.ingestion._soda import fetch_soda

logger = logging.getLogger(__name__)

_DATASET_ID = "uext-mhny"
_OUTPUT = "ideam_humedad.parquet"
_YEARS_BACK = 5


def run(force: bool = False) -> None:
    """Descarga humedad del aire IDEAM (últimos 5 años) a data/raw/."""
    output_path = Path(config.data_raw) / _OUTPUT
    if output_path.exists() and not force:
        logger.info("[Humedad IDEAM] Ya existe %s, omitiendo.", _OUTPUT)
        return

    cutoff = datetime.date.today() - datetime.timedelta(days=_YEARS_BACK * 365)
    where = f"fechaobservacion >= '{cutoff.isoformat()}'"

    logger.info("[Humedad IDEAM] Descargando desde %s (~86.8 M filas totales)...", cutoff)
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
            "[Humedad IDEAM] %d filas | %s -> %s | guardado en %s",
            len(df), fechas.min().date(), fechas.max().date(), output_path,
        )
    else:
        logger.info("[Humedad IDEAM] %d filas guardadas en %s", len(df), output_path)

