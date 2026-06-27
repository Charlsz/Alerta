"""Ingesta de Velocidad del Viento IDEAM desde datos.gov.co (SODA JSON).

Variable que aporta: velocidad_viento (m/s).
Fuente: https://www.datos.gov.co/d/sgfv-3yp8
"""
import datetime
import logging
from pathlib import Path

import pandas as pd
import requests

from config import config

logger = logging.getLogger(__name__)

_PAGE_SIZE = 200000
_MAX_PAGES = 3  # ~600K records, ~10 days coverage


def _download_json(dataset_id: str, where_clause: str | None = None) -> pd.DataFrame:
    """Download SODA dataset via JSON endpoint."""
    url = f"https://www.datos.gov.co/resource/{dataset_id}.json"
    params: dict = {"$limit": _PAGE_SIZE, "$order": "fechaobservacion DESC"}
    if where_clause:
        params["$where"] = where_clause

    all_rows = []
    offset = 0
    for _ in range(_MAX_PAGES):
        params["$offset"] = offset
        try:
            resp = requests.get(url, params=params, timeout=120)
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            logger.warning("[Viento IDEAM] Error en offset %d: %s", offset, exc)
            break
        if not data:
            break
        all_rows.extend(data)
        if len(data) < _PAGE_SIZE:
            break
        offset += _PAGE_SIZE
        logger.info("[Viento IDEAM] Descargados %d registros...", len(all_rows))

    return pd.DataFrame(all_rows)


def run(force: bool = False) -> None:
    """Download recent IDEAM wind speed data and persist to data/raw/."""
    output_path = Path(config.data_raw) / "ideam_viento.parquet"
    if output_path.exists() and not force:
        logger.info("[Viento IDEAM] Ya existe %s, omitiendo.", output_path.name)
        return

    cutoff = datetime.date.today() - datetime.timedelta(days=365 * 2)
    where = f"fechaobservacion >= '{cutoff.isoformat()}'"
    logger.info("[Viento IDEAM] Descargando (sgfv-3yp8)...")
    df = _download_json("sgfv-3yp8", where_clause=where)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(output_path, index=False)

    if "fechaobservacion" in df.columns and not df.empty:
        df["fechaobservacion"] = pd.to_datetime(df["fechaobservacion"], errors="coerce")
        min_date = df["fechaobservacion"].min()
        max_date = df["fechaobservacion"].max()
        logger.info(
            "[Viento IDEAM] %d filas | %s -> %s | %s",
            len(df),
            min_date.date() if pd.notna(min_date) else "N/A",
            max_date.date() if pd.notna(max_date) else "N/A",
            output_path,
        )
    else:
        logger.info("[Viento IDEAM] %d filas guardadas en %s", len(df), output_path)