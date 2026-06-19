"""Ingesta de variables socioeconómicas municipales DANE.

Descarga el dataset de NBI (Necesidades Básicas Insatisfechas) y
población rural por municipio desde datos.gov.co.

Variables que aporta para el SVE:
    nbi_total        — % hogares con NBI (proxy de vulnerabilidad estructural)
    poblacion_rural  — Habitantes en zona rural
    pct_rural        — % de población en zona rural

Fuente principal: datos.gov.co - NBI por municipio (DANE)
Dataset ID: fjhr-4qb9  (NBI municipal por cabecera/resto)
"""
from __future__ import annotations

import argparse
import logging
from pathlib import Path

import pandas as pd

from config import config
from src.ingestion._soda import fetch_soda

logger = logging.getLogger(__name__)

_DATASET_ID = "fjhr-4qb9"
_OUTPUT = "dane_municipios.parquet"

# Columnas candidatas según variantes del dataset DANE en datos.gov.co
_COD_CANDIDATES   = ["cod_dane", "codigo_dane", "codigodane", "divipola", "codigo_municipio", "c_digo_dane"]
_NBI_CANDIDATES   = ["nbi_total", "nbi", "porcentaje_nbi", "pct_nbi", "total"]
_POB_RURAL_CANDS  = ["poblacion_resto", "pob_resto", "resto", "rural", "poblacion_rural"]
_POB_TOTAL_CANDS  = ["total_personas", "poblacion_total", "total", "pob_total"]
_NOMBRE_CANDS     = ["municipio", "nombre_municipio", "nom_municipio", "municipio_1"]
_DEPTO_CANDS      = ["departamento", "depto", "nombre_departamento"]


def _find_col(cols: list[str], candidates: list[str]) -> str | None:
    cols_lower = [c.lower().strip() for c in cols]
    for cand in candidates:
        if cand in cols_lower:
            return cols[cols_lower.index(cand)]
    return None


def run(force: bool = False) -> None:
    """Descarga variables socioeconómicas DANE y las guarda en data/raw/."""
    output_path = Path(config.data_raw) / _OUTPUT
    if output_path.exists() and not force:
        logger.info("[DANE municipios] Ya existe %s, omitiendo.", _OUTPUT)
        return

    logger.info("[DANE municipios] Descargando NBI municipal...")
    records = fetch_soda(_DATASET_ID, page_size=config.soda_page_size)
    df = pd.DataFrame(records)

    if df.empty:
        logger.warning("[DANE municipios] Dataset vacío. Verificar ID %s.", _DATASET_ID)
        # Guardar vacío para no romper el pipeline
        df.to_parquet(output_path, index=False)
        return

    cols = list(df.columns)
    cod_col  = _find_col(cols, _COD_CANDIDATES)
    nbi_col  = _find_col(cols, _NBI_CANDIDATES)
    rur_col  = _find_col(cols, _POB_RURAL_CANDS)
    tot_col  = _find_col(cols, _POB_TOTAL_CANDS)
    nom_col  = _find_col(cols, _NOMBRE_CANDS)
    dep_col  = _find_col(cols, _DEPTO_CANDS)

    logger.info(
        "[DANE municipios] Columnas detectadas — cod: %s | nbi: %s | rural: %s | total: %s",
        cod_col, nbi_col, rur_col, tot_col,
    )

    select: dict[str, pd.Series] = {}
    if cod_col:
        select["codigo_municipio"] = df[cod_col].astype(str).str.strip().str.zfill(5)
    if nom_col:
        select["nombre_municipio"] = df[nom_col].astype(str).str.strip().str.upper()
    if dep_col:
        select["departamento"] = df[dep_col].astype(str).str.strip().str.upper()
    if nbi_col:
        select["nbi_total"] = pd.to_numeric(df[nbi_col], errors="coerce")
    if rur_col:
        select["poblacion_rural"] = pd.to_numeric(df[rur_col], errors="coerce")
    if tot_col:
        select["poblacion_total"] = pd.to_numeric(df[tot_col], errors="coerce")

    out = pd.DataFrame(select)

    # Calcular pct_rural si tenemos los datos
    if "poblacion_rural" in out.columns and "poblacion_total" in out.columns:
        out["pct_rural"] = (out["poblacion_rural"] / out["poblacion_total"].replace(0, pd.NA) * 100).round(2)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(output_path, index=False)
    logger.info("[DANE municipios] %d municipios guardados en %s", len(out), output_path)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser(description="Descarga variables socioeconómicas DANE")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    run(force=args.force)


if __name__ == "__main__":
    main()
