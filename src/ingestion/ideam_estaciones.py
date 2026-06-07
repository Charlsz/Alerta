"""Ingesta del catálogo de estaciones IDEAM desde datos.gov.co (SODA API)."""
import argparse
import logging
import os
from pathlib import Path

import pandas as pd
import requests

from config import IRAConfig

logger = logging.getLogger(__name__)

_SODA_BASE = "https://www.datos.gov.co/resource"


def _fetch_dataset(dataset_id: str, config: IRAConfig) -> pd.DataFrame:
    """Download a full SODA dataset using pagination."""
    headers = {}
    app_token = os.getenv("SODA_APP_TOKEN")
    if app_token:
        headers["X-App-Token"] = app_token

    limit = config.soda_page_size
    offset = 0
    records: list[dict] = []

    while True:
        url = f"{_SODA_BASE}/{dataset_id}.json?$limit={limit}&$offset={offset}"
        try:
            response = requests.get(url, headers=headers, timeout=120)
            response.raise_for_status()
        except requests.RequestException as exc:
            logger.warning("Download failed for %s at offset %s: %s", dataset_id, offset, exc)
            break

        batch = response.json()
        if not batch:
            break

        records.extend(batch)
        offset += limit

    df = pd.DataFrame(records)
    return df


def run(config: IRAConfig, force: bool = False) -> None:
    """Download IDEAM stations catalog and persist to data/raw/."""
    output_path = Path(config.data_raw) / "ideam_estaciones.parquet"
    if output_path.exists() and not force:
        logger.info("ideam_estaciones.parquet already exists. Skipping download.")
        return

    logger.info("Downloading IDEAM stations catalog (hp9r-jxuu)...")
    df = _fetch_dataset("hp9r-jxuu", config)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(output_path, index=False)
    logger.info("Saved ideam_estaciones.parquet with %s rows to %s", len(df), output_path)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    parser = argparse.ArgumentParser(description="Ingest IDEAM stations catalog from datos.gov.co")
    parser.add_argument("--force", action="store_true", help="Force re-download even if file exists")
    args = parser.parse_args()

    config = IRAConfig()
    run(config, force=args.force)


if __name__ == "__main__":
    main()
