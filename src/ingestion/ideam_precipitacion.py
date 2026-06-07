"""Ingesta de precipitación IDEAM desde datos.gov.co (SODA API)."""
import argparse
import datetime
import logging
import os
from pathlib import Path

import pandas as pd
import requests

from config import IRAConfig

logger = logging.getLogger(__name__)

_SODA_BASE = "https://www.datos.gov.co/resource"


def _fetch_dataset(dataset_id: str, config: IRAConfig, where_clause: str | None = None) -> pd.DataFrame:
    """Download a full SODA dataset using pagination and an optional $where clause."""
    headers = {}
    app_token = os.getenv("SODA_APP_TOKEN")
    if app_token:
        headers["X-App-Token"] = app_token

    limit = config.soda_page_size
    offset = 0
    records: list[dict] = []

    while True:
        params: dict[str, str | int] = {"$limit": limit, "$offset": offset}
        if where_clause:
            params["$where"] = where_clause

        url = f"{_SODA_BASE}/{dataset_id}.json"
        try:
            response = requests.get(url, headers=headers, params=params, timeout=120)
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
    """Download recent IDEAM precipitation data and persist to data/raw/."""
    output_path = Path(config.data_raw) / "ideam_precip.parquet"
    if output_path.exists() and not force:
        logger.info("ideam_precip.parquet already exists. Skipping download.")
        return

    # Filter for the last 5 years to avoid downloading ~280M rows.
    cutoff = datetime.date.today() - datetime.timedelta(days=5 * 365)
    where = f"fechaobservacion >= '{cutoff.isoformat()}'"

    logger.info("Downloading IDEAM precipitation (s54a-sgyg) with $where=%s ...", where)
    df = _fetch_dataset("s54a-sgyg", config, where_clause=where)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(output_path, index=False)

    # Log date range and row count if the expected column exists.
    if "fechaobservacion" in df.columns and not df.empty:
        df["fechaobservacion"] = pd.to_datetime(df["fechaobservacion"], errors="coerce")
        min_date = df["fechaobservacion"].min()
        max_date = df["fechaobservacion"].max()
        logger.info(
            "Saved ideam_precip.parquet with %s rows (%s to %s) to %s",
            len(df),
            min_date.date() if pd.notna(min_date) else "N/A",
            max_date.date() if pd.notna(max_date) else "N/A",
            output_path,
        )
    else:
        logger.info("Saved ideam_precip.parquet with %s rows to %s", len(df), output_path)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    parser = argparse.ArgumentParser(description="Ingest IDEAM precipitation dataset from datos.gov.co")
    parser.add_argument("--force", action="store_true", help="Force re-download even if file exists")
    args = parser.parse_args()

    config = IRAConfig()
    run(config, force=args.force)


if __name__ == "__main__":
    main()
