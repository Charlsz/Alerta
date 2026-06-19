"""Ingesta de precipitación IDEAM desde datos.gov.co (CSV directo)."""
import argparse
import datetime
import io
import logging
from pathlib import Path

import pandas as pd
import requests

from config import config

logger = logging.getLogger(__name__)


def _download_csv(dataset_id: str, where_clause: str | None = None) -> pd.DataFrame:
    """Download a SODA dataset as CSV with optional $where filter."""
    url = f"https://www.datos.gov.co/resource/{dataset_id}.csv"
    params: dict[str, str | int] = {"$limit": 5_000_000}
    if where_clause:
        params["$where"] = where_clause
    resp = requests.get(url, params=params, stream=True, timeout=600)
    resp.raise_for_status()
    return pd.read_csv(io.BytesIO(resp.content), low_memory=False)


def run(force: bool = False) -> None:
    """Download recent IDEAM precipitation data and persist to data/raw/."""
    output_path = Path(config.data_raw) / "ideam_precip.parquet"
    if output_path.exists() and not force:
        logger.info("[Precipitación IDEAM] Ya existe %s, omitiendo.", output_path.name)
        return

    cutoff = datetime.date.today() - datetime.timedelta(days=5 * 365)
    where = f"fechaobservacion >= '{cutoff.isoformat()}'"

    logger.info("[Precipitación IDEAM] Descargando (s54a-sgyg) con $where=%s ...", where)
    df = _download_csv("s54a-sgyg", where_clause=where)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(output_path, index=False)

    # Log date range and row count if the expected column exists.
    if "fechaobservacion" in df.columns and not df.empty:
        df["fechaobservacion"] = pd.to_datetime(df["fechaobservacion"], errors="coerce")
        min_date = df["fechaobservacion"].min()
        max_date = df["fechaobservacion"].max()
        logger.info(
            "[Precipitación IDEAM] %d filas | %s → %s | %s",
            len(df),
            min_date.date() if pd.notna(min_date) else "N/A",
            max_date.date() if pd.notna(max_date) else "N/A",
            output_path,
        )
    else:
        logger.info("[Precipitación IDEAM] %d filas guardadas en %s", len(df), output_path)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    parser = argparse.ArgumentParser(description="Descarga precipitación IDEAM")
    parser.add_argument("--force", action="store_true", help="Fuerza re-descarga")
    args = parser.parse_args()

    run(force=args.force)


if __name__ == "__main__":
    main()
