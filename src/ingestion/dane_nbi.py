"""Ingesta de NBI (Necesidades Básicas Insatisfechas) desde Excel oficial del DANE.

Fuente: https://www.dane.gov.co/files/censo2018/informacion-tecnica/CNPV-2018-NBI.xlsx
Reemplaza el dataset fjhr-4qb9 que fue eliminado de datos.gov.co.

Variable:
    nbi_total — % de personas en NBI por municipio (Censo 2018)
"""
from __future__ import annotations

import io
import logging
from pathlib import Path

import pandas as pd
import requests

from config import config

logger = logging.getLogger(__name__)

_URL = "https://www.dane.gov.co/files/censo2018/informacion-tecnica/CNPV-2018-NBI.xlsx"
_OUTPUT = "dane_nbi.parquet"


def run(force: bool = False) -> None:
    output_path = Path(config.data_raw) / _OUTPUT
    if output_path.exists() and not force:
        logger.info("[DANE NBI] Ya existe %s, omitiendo.", _OUTPUT)
        return

    logger.info("[DANE NBI] Descargando Excel DANE...")
    resp = requests.get(_URL, timeout=120)
    resp.raise_for_status()

    # skiprows=9: row 10 is header (Código Departamento, Nombre Departamento, ...)
    # Columns: 0=cod_depto, 1=nom_depto, 2=cod_mun, 3=nom_mun, 4=% personas en NBI
    df = pd.read_excel(io.BytesIO(resp.content), sheet_name="Municipios", skiprows=9, dtype=str)

    # keep only first 5 columns (total NBI, not cabecera/rural breakdown)
    df = df.iloc[:, :5]
    df.columns = ["cod_depto", "nom_depto", "cod_mun", "nom_mun", "nbi_total"]
    df["nbi_total"] = pd.to_numeric(df["nbi_total"], errors="coerce")

    # Build 5-digit DANE code: depto (2 digits) + mun (3 digits)
    df["codigo_municipio"] = (
        df["cod_depto"].str.strip().str.zfill(2)
        + df["cod_mun"].str.strip().str.zfill(3)
    )

    out = df[["codigo_municipio", "nbi_total"]].dropna(subset=["codigo_municipio"])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(output_path, index=False)
    logger.info("[DANE NBI] %d municipios guardados en %s", len(out), _OUTPUT)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    run(force=True)
