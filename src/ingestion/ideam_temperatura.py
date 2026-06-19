"""Ingesta de temperatura máxima del aire IDEAM desde datos.gov.co (CSV directo)."""
import argparse
import datetime
import io
import logging
from pathlib import Path

import pandas as pd
import requests

from config import IRAConfig

logger = logging.getLogger(__name__)


def _download_csv(dataset_id: str, where_clause: str | None = None) -> pd.DataFrame:
    """Download a SODA dataset as CSV with optional $where filter."""
    url = f"https://www.datos.gov.co/resource/{dataset_id}.csv"
    params = {}
    if where_clause:
        params["$where"] = where_clause
    resp = requests.get(url, params=params, stream=True, timeout=600)
    resp.raise_for_status()
    return pd.read_csv(io.BytesIO(resp.content), low_memory=False)


def run(config: IRAConfig, force: bool = False) -> None:
    """Download recent IDEAM temperature data and persist to data/raw/."""
    output_path = Path(config.data_raw) / "ideam_tmax.parquet"
    if output_path.exists() and not force:
        logger.info("ideam_tmax.parquet already exists. Skipping download.")
        return

    cutoff = datetime.date.today() - datetime.timedelta(days=5 * 365)
    where = f"fechaobservacion >= '{cutoff.isoformat()}'"

    logger.info("Downloading IDEAM temperature (ccvq-rp9s) with $where=%s ...", where)
    df = _download_csv("ccvq-rp9s", where_clause=where)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(output_path, index=False)

    # Log date range and row count if the expected column exists.
    if "fechaobservacion" in df.columns and not df.empty:
        df["fechaobservacion"] = pd.to_datetime(df["fechaobservacion"], errors="coerce")
        min_date = df["fechaobservacion"].min()
        max_date = df["fechaobservacion"].max()
        logger.info(
            "Saved ideam_tmax.parquet with %s rows (%s to %s) to %s",
            len(df),
            min_date.date() if pd.notna(min_date) else "N/A",
            max_date.date() if pd.notna(max_date) else "N/A",
            output_path,
        )
    else:
        logger.info("Saved ideam_tmax.parquet with %s rows to %s", len(df), output_path)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    parser = argparse.ArgumentParser(description="Ingest IDEAM temperature dataset from datos.gov.co")
    parser.add_argument("--force", action="store_true", help="Force re-download even if file exists")
    args = parser.parse_args()

    config = IRAConfig()
    run(config, force=args.force)


if __name__ == "__main__":
    main()
