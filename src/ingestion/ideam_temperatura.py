"""Ingesta de temperatura máxima del aire IDEAM desde datos.gov.co (CSV directo)."""
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
    """Download recent IDEAM temperature data and persist to data/raw/."""
    output_path = Path(config.data_raw) / "ideam_tmax.parquet"
    if output_path.exists() and not force:
        logger.info("[Temperatura IDEAM] Ya existe %s, omitiendo.", output_path.name)
        return

    cutoff = datetime.date.today() - datetime.timedelta(days=5 * 365)
    where = f"fechaobservacion >= '{cutoff.isoformat()}'"

    logger.info("[Temperatura IDEAM] Descargando (ccvq-rp9s) con $where=%s ...", where)
    df = _download_csv("ccvq-rp9s", where_clause=where)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(output_path, index=False)

    # Log date range and row count if the expected column exists.
    if "fechaobservacion" in df.columns and not df.empty:
        df["fechaobservacion"] = pd.to_datetime(df["fechaobservacion"], errors="coerce")
        min_date = df["fechaobservacion"].min()
        max_date = df["fechaobservacion"].max()
        logger.info(
            "[Temperatura IDEAM] %d filas | %s → %s | %s",
            len(df),
            min_date.date() if pd.notna(min_date) else "N/A",
            max_date.date() if pd.notna(max_date) else "N/A",
            output_path,
        )
    else:
        logger.info("[Temperatura IDEAM] %d filas guardadas en %s", len(df), output_path)

