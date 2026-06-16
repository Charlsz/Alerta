"""Ingesta de EVA Calendario de siembra y cosecha desde datos.gov.co."""
from __future__ import annotations

import argparse
import logging
from pathlib import Path

import pandas as pd

from config import config
from src.ingestion._soda import fetch_soda

logger = logging.getLogger(__name__)

_DATASET_ID = "4229-puwp"
_OUTPUT = "eva_calendario.parquet"


def run(force: bool = False) -> None:
    """Descarga EVA Calendario a data/raw/."""
    output_path = Path(config.data_raw) / _OUTPUT
    if output_path.exists() and not force:
        logger.info("[EVA Calendario] Ya existe %s, omitiendo.", _OUTPUT)
        return

    records = fetch_soda(_DATASET_ID, page_size=config.soda_page_size)
    df = pd.DataFrame(records)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(output_path, index=False)
    logger.info("[EVA Calendario] %d filas guardadas en %s", len(df), output_path)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    parser = argparse.ArgumentParser(description="Descarga EVA Calendario desde datos.gov.co")
    parser.add_argument("--force", action="store_true", help="Fuerza re-descarga")
    args = parser.parse_args()
    run(force=args.force)


if __name__ == "__main__":
    main()
