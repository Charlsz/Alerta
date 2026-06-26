"""Create deforestation features in DuckDB from GFW data."""
from __future__ import annotations

import json
import logging
import re
import unicodedata
from pathlib import Path

import duckdb
import pandas as pd

from src.ingestion.load_duckdb import get_connection, table_exists

logger = logging.getLogger(__name__)

_TABLE = "features_deforestacion"


def _normalize(name: str) -> str:
    name = unicodedata.normalize("NFKD", name)
    name = name.encode("ascii", "ignore").decode("ascii")
    name = re.sub(r"[^A-Z0-9\s]", "", name.upper())
    name = re.sub(r"\s+", " ", name).strip()
    return name


# ponytail: manual fixups for commonly mismatched names
_NAME_FIXUPS = {
    "MIRITI PARANA": "MIRITI - PARANA",
    "CAROLINA DEL PRINCIPE": "CAROLINA",
    "EL SOPETRAN": "SOPETRAN",
    "SAN VICENTE": "SAN VICENTE DE CHUCURI",
    "SANTAFE DE ANTIOQUIA": "SANTA FE DE ANTIOQUIA",
    "SAN ESTANISLAO DE KOSTKA": "SAN ESTANISLAO",
    "GUICAN": "GUICAN DE LA SIERRA",
    "PIENDAMA": "PIENDAMO",
    "CARMEN DE APICALA": "EL CARMEN",
    "CAROLINA": "CAROLINA DEL PRINCIPE",
    "EL CARMEN": "CARMEN DE APICALA",
    "PUEBLO BELLO": "PUEBLOBELLO",
    "SANTA ROSA": "SANTA ROSA DE CABAL",
    "SAN PEDRO": "SAN PEDRO DE LOS MILAGROS",
    "SAN LUIS": "SAN LUIS DE PALENQUE",
    "SAN JOSE": "SAN JOSE DE LA MONTANA",
    "SAN JOSE DE PARE": "SAN JOSE DE LA MONTANA",
    "SAN MIGUEL": "SAN MIGUEL DE PUTUMAYO",
    "SAN BENITO": "SAN BENITO ABAD",
    "SAN ANTONIO": "SAN ANTONIO DEL TEQUENDAMA",
}

# Extra department-prefixed fallbacks
_DEPT_PREFIX_MAP = {
    "SANTA ROSA DEL SUR": "BOLIVAR",
    "TIERRA ALTA": "CORDOBA",
    "SAN BENITO ABAD": "SUCRE",
}


def _build_name_map(con: duckdb.DuckDBPyConnection) -> tuple[dict[str, str], set[str]]:
    df = con.execute("SELECT codigo_municipio, nombre_municipio, nombre_departamento FROM municipios_geom").df()
    mapping = {}
    all_names = set()
    for _, row in df.iterrows():
        n = _normalize(row["nombre_municipio"])
        mapping[n] = row["codigo_municipio"]
        all_names.add(n)
        # Also add normalized with department
        dn = _normalize(f"{row['nombre_municipio']} {row['nombre_departamento']}")
        mapping[dn] = row["codigo_municipio"]
    return mapping, all_names


def _find_fuzzy_match(key: str, name_map: dict[str, str], all_names: set[str]) -> str | None:
    """Try simple substring matching as fallback."""
    key_words = set(key.split())
    for candidate in all_names:
        cand_words = set(candidate.split())
        # If all words of key appear in candidate or vice versa
        if len(key_words & cand_words) >= min(len(key_words), len(cand_words)):
            return name_map[candidate]
    return None


def _json_path(name: str) -> Path:
    return Path("data/raw") / f"raw_gfw_subnational_2_{name}.json"


def _load_json_data(name: str, value_key: str, start_year: int = 2001) -> pd.DataFrame:
    path = _json_path(name)
    if not path.exists():
        return pd.DataFrame()
    with open(path, encoding="utf-8") as f:
        records = json.load(f)
    rows = []
    for rec in records:
        if rec.get("threshold") != 30:
            continue
        for year in range(start_year, 2026):
            col = f"tc_loss_ha_{year}"
            val = rec.get(col)
            if val is not None and float(val) > 0:
                rows.append({
                    "departamento": rec["subnational1"],
                    "municipio": rec["subnational2"],
                    "year": year,
                    value_key: float(val),
                })
    return pd.DataFrame(rows)


def build(force: bool = False) -> None:
    con = get_connection()

    if not force and table_exists(con, _TABLE):
        logger.info("[deforestacion] '%s' ya existe, omitiendo.", _TABLE)
        return

    loss = _load_json_data("tree_cover_loss", "tc_loss_ha")
    if loss.empty:
        logger.error("[deforestacion] No se pudieron cargar datos.")
        con.close()
        return

    primary = _load_json_data("primary_loss", "primary_loss_ha", start_year=2002)
    if not primary.empty:
        loss = loss.merge(primary, on=["departamento", "municipio", "year"], how="left")
    loss["primary_loss_ha"] = loss.get("primary_loss_ha", 0.0).fillna(0.0)

    name_map, all_names = _build_name_map(con)
    logger.info("[deforestacion] Mapa de nombres: %d municipios en geometrías.", len(all_names))

    codes = []
    matched = 0
    unmatched = []
    for _, row in loss.iterrows():
        muni = row["municipio"]
        dept = row["departamento"]
        key = _normalize(muni)
        code = name_map.get(key)
        if not code:
            fixed_key = _NAME_FIXUPS.get(key)
            if fixed_key:
                code = name_map.get(_normalize(fixed_key))
        if not code:
            dept_key = _normalize(f"{muni} {dept}")
            code = name_map.get(dept_key)
        if not code:
            dept_fallback = _DEPT_PREFIX_MAP.get(_normalize(muni))
            if dept_fallback:
                dept_key2 = _normalize(f"{muni} {dept_fallback}")
                code = name_map.get(dept_key2)
        if not code:
            code = _find_fuzzy_match(key, name_map, all_names)
        if code:
            codes.append(code)
            matched += 1
        else:
            codes.append(None)
            if muni not in unmatched:
                unmatched.append(muni)

    loss["codigo_municipio"] = codes
    loss_clean = loss.dropna(subset=["codigo_municipio"]).copy()
    logger.info("[deforestacion] Coincidencias: %d / %d (%.0f%%)",
                matched, len(loss), 100 * matched / len(loss) if len(loss) > 0 else 0)

    if unmatched:
        logger.warning("[deforestacion] %d municipios sin coincidencia. Muestra: %s",
                       len(unmatched), unmatched[:10])

    latest_year = int(loss_clean["year"].max())
    cutoff_5y = latest_year - 4
    cutoff_10y = latest_year - 9

    def _agg(g: pd.DataFrame) -> pd.Series:
        sub5 = g[g["year"] >= cutoff_5y]
        sub10 = g[g["year"] >= cutoff_10y]
        sub_latest = g[g["year"] == latest_year]
        return pd.Series({
            "deforestacion_2025": sub_latest["tc_loss_ha"].sum(),
            "deforestacion_total_5y": sub5["tc_loss_ha"].sum(),
            "deforestacion_total_10y": sub10["tc_loss_ha"].sum(),
            "primary_loss_5y": sub5["primary_loss_ha"].sum(),
            "deforestacion_ha_promedio": g["tc_loss_ha"].mean(),
            "n_anos_datos": g["year"].nunique(),
        })

    features = loss_clean.groupby("codigo_municipio", sort=False).apply(_agg, include_groups=False).reset_index()

    # Trend calculation
    trend_data = loss_clean[loss_clean["year"] >= cutoff_5y].copy()
    trend_agg = trend_data.groupby(["codigo_municipio", "year"])["tc_loss_ha"].sum().reset_index()
    slopes = []
    for code in features["codigo_municipio"]:
        sub = trend_agg[trend_agg["codigo_municipio"] == code]
        if len(sub) >= 3:
            x = (sub["year"] - sub["year"].min()).values.astype(float)
            y = sub["tc_loss_ha"].values.astype(float)
            slope = (len(x) * (x * y).sum() - x.sum() * y.sum()) / (len(x) * (x * x).sum() - x.sum() ** 2)
            slopes.append(slope)
        else:
            slopes.append(0.0)

    features["deforestacion_tendencia"] = slopes
    features["deforestacion_tendencia_label"] = features["deforestacion_tendencia"].apply(
        lambda s: "Aumentando" if s > 50 else ("Estable" if s > -50 else "Disminuyendo")
    )
    # Ponytail: na -> "Sin datos" for the label
    features["deforestacion_tendencia_label"] = features["deforestacion_tendencia_label"].fillna("Sin datos")

    logger.info("[deforestacion] Características calculadas para %d municipios.", len(features))

    con.execute(f"CREATE OR REPLACE TABLE {_TABLE} AS SELECT * FROM features")
    (rows,) = con.execute(f"SELECT COUNT(*) FROM {_TABLE}").fetchone()
    logger.info("[deforestacion] Tabla '%s' creada: %d filas.", _TABLE, rows)
    con.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
    build(force=True)
