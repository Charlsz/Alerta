"""Clean and normalize raw feature DataFrames (EVA, IDEAM, etc.)."""
import logging

import pandas as pd

logger = logging.getLogger(__name__)


def _safe_col(cols: list, *candidates: str) -> str | None:
    """Return first candidate column name that exists in cols, else None."""
    for c in candidates:
        if c in cols:
            return c
    return None


def _clean_eva(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize EVA column names and coerce municipio code to 6-char string."""
    cols = list(df.columns)
    logger.debug("EVA raw columns: %s", cols)

    a_sem = _safe_col(cols, "area_sembrada", "areasembrada", "rea_sembrada_ha", "rea_sembrada")
    a_cos = _safe_col(cols, "area_cosechada", "areacosechada", "rea_cosechada_ha", "rea_cosechada")
    prod = _safe_col(cols, "produccion", "producci_n_t", "produccion_t", "prod")
    cod_m = _safe_col(cols, "c_d_mun", "codigomunicipio", "codigo_municipio", "codmunicipio")

    rename = {}
    if a_sem and a_sem != "area_sembrada":
        rename[a_sem] = "area_sembrada"
    if a_cos and a_cos != "area_cosechada":
        rename[a_cos] = "area_cosechada"
    if prod and prod != "produccion":
        rename[prod] = "produccion"
    if cod_m and cod_m != "c_d_mun":
        rename[cod_m] = "c_d_mun"

    df = df.rename(columns=rename)

    # LPAD via zfill — no DB dependency needed
    if "c_d_mun" in df.columns:
        df["c_d_mun"] = (
            pd.to_numeric(df["c_d_mun"], errors="coerce")
            .fillna(0)
            .astype(int)
            .astype(str)
            .str.zfill(6)
        )

    for col in ["area_sembrada", "area_cosechada", "produccion"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df
