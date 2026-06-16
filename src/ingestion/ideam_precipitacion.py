"""Ingesta de precipitación IDEAM desde datos.gov.co.

Volumen total: ~280 M filas. Se filtra por los últimos 5 años
y se usa $order para garantizar paginación determinista.
"""
from __future__ import annotations

import argparse
import datetime
import logging
from pathlib import Path

import pandas as pd

from config import config
from src.ingestion._soda import fetch_soda

logger = logging.getLogger(__name__)

_DATASET_ID = "s54a-sgyg"
_OUTPUT = "ideam_precip.parquet"
_YEARS_BACK = 5


def run(force: bool = False) -> None:
    """Descarga precipitación IDEAM (últimos 5 años) a data/raw/."""
    output_path = Path(config.data_raw) / _OUTPUT
    if output_path.exists() and not force:
        logger.info("[Precipitación IDEAM] Ya existe %s, omitiendo.", _OUTPUT)
        return

    cutoff = datetime.date.today() - datetime.timedelta(days=_YEARS_BACK * 365)
    where = f"fechaobservacion >= '{cutoff.isoformat()}'"

    logger.info("[Precipitación IDEAM] Descargando desde %s ...", cutoff)
    records = fetch_soda(
        _DATASET_ID,
        page_size=config.soda_page_size,
        where=where,
        order="fechaobservacion",  # orden determinista para paginación grande
    )

    df = pd.DataFrame(records)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(output_path, index=False)

    if "fechaobservacion" in df.columns and not df.empty:
        fechas = pd.to_datetime(df["fechaobservacion"], errors="coerce")
        logger.info(
            "[Precipitación IDEAM] %d filas | %s → %s | guardado en %s",
            len(df),
            fechas.min().date(),
            fechas.max().date(),
            output_path,
        )
    else:
        logger.info("[Precipitación IDEAM] %d filas guardadas en %s", len(df), output_path)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    parser = argparse.ArgumentParser(description="Descarga precipitación IDEAM")
    parser.add_argument("--force", action="store_true", help="Fuerza re-descarga")
    args = parser.parse_args()
    run(force=args.force)


if __name__ == "__main__":
    main()
