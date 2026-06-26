"""Ingesta de datos EVA Calendario desde Excel de UPRA."""
import io
import logging
from pathlib import Path

import pandas as pd
import requests

from config import config

logger = logging.getLogger(__name__)

_URL = (
    "https://upra.gov.co/sites/default/files/2025-08/"
    "Consolidado%20calendarios%20EVA%202024.xlsx"
)


def run(force: bool = False) -> None:
    """Download EVA Calendario Excel from UPRA and persist to data/raw/."""
    output_path = Path(config.data_raw) / "eva_calendario.parquet"
    if output_path.exists() and not force:
        logger.info("[EVA Calendario] Ya existe %s, omitiendo.", output_path.name)
        return

    logger.info("[EVA Calendario] Descargando desde UPRA...")
    resp = requests.get(_URL, timeout=60)
    resp.raise_for_status()
    df = pd.read_excel(
        io.BytesIO(resp.content),
        sheet_name="CNal",
        header=4,
    )
    df.columns = [c.lower().strip() for c in df.columns]
    # Drop rows where all core columns are NaN (footer notes)
    df = df.dropna(subset=["código cultivo", "cultivo"], how="all")
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].astype(str)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(output_path, index=False)
    logger.info("[EVA Calendario] %d filas guardadas en %s", len(df), output_path)

