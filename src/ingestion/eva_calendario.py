"""Ingesta de datos EVA Calendario desde Excel de UPRA."""
import argparse
import io
import logging
from pathlib import Path

import pandas as pd
import requests

from config import IRAConfig

logger = logging.getLogger(__name__)

_URL = (
    "https://upra.gov.co/sites/default/files/2025-08/"
    "Consolidado%20calendarios%20EVA%202024.xlsx"
)


def run(config: IRAConfig, force: bool = False) -> None:
    """Download EVA Calendario Excel from UPRA and persist to data/raw/."""
    output_path = Path(config.data_raw) / "eva_calendario.parquet"
    if output_path.exists() and not force:
        logger.info("eva_calendario.parquet already exists. Skipping download.")
        return

    logger.info("Downloading EVA Calendario from UPRA...")
    resp = requests.get(_URL, timeout=60)
    resp.raise_for_status()
    df = pd.read_excel(io.BytesIO(resp.content))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(output_path, index=False)
    logger.info("Saved eva_calendario.parquet with %s rows to %s", len(df), output_path)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    parser = argparse.ArgumentParser(description="Ingest EVA Calendario dataset from datos.gov.co")
    parser.add_argument("--force", action="store_true", help="Force re-download even if file exists")
    args = parser.parse_args()

    config = IRAConfig()
    run(config, force=args.force)


if __name__ == "__main__":
    main()
