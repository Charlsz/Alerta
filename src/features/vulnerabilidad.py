"""Variables de vulnerabilidad económica y social (Sub-índice SVE).

Fuentes:
    - clean_insumos          (índice precios insumos agrícolas UPRA)
    - clean_dane_municipios  (NBI, población rural — DANE)  ← nuevo

Variables que construye:
    Insumos (3 vars, serie mensual nacional):
        insumos_nivel, insumos_anomalia_12m, insumos_delta_3m

    DANE por municipio (3 vars, estáticas — se unen por codigo_municipio):
        nbi_total, poblacion_rural, pct_rural                ← nuevas
"""
from __future__ import annotations

import logging

import pandas as pd

from src.ingestion.load_duckdb import get_connection

logger = logging.getLogger(__name__)

_TABLE      = "features_vulnerabilidad"
_TABLE_DANE = "features_dane"


def _table_exists(con, table: str) -> bool:
    return bool(
        con.execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = ?",
            [table],
        ).fetchone()[0]
    )


def _build_insumos(con) -> pd.DataFrame:
    """Serie mensual de insumos con anomalías."""
    df = con.execute("SELECT * FROM clean_insumos").df()
    df.columns = [c.lower().strip() for c in df.columns]

    fecha_col = next((c for c in df.columns if "periodo" in c or "fecha" in c or "mes" in c), None)
    valor_col = next((c for c in df.columns if "nivel" in c or "indice" in c or "valor" in c), None)

    if not fecha_col or not valor_col:
        logger.error("[vulnerabilidad] Columnas no encontradas. Cols: %s", list(df.columns))
        return pd.DataFrame()

    df = (df[[fecha_col, valor_col]]
          .rename(columns={fecha_col: "periodo", valor_col: "insumos_nivel"}))
    df["periodo"]       = pd.to_datetime(df["periodo"], errors="coerce").dt.to_period("M").dt.to_timestamp()
    df["insumos_nivel"] = pd.to_numeric(df["insumos_nivel"], errors="coerce")
    df = df.dropna().sort_values("periodo").reset_index(drop=True)

    df["insumos_media_12m"]    = df["insumos_nivel"].rolling(12, min_periods=6).mean()
    df["insumos_anomalia_12m"] = df["insumos_nivel"] - df["insumos_media_12m"]
    df["insumos_delta_3m"]     = df["insumos_nivel"].diff(3)

    return df[["periodo", "insumos_nivel", "insumos_anomalia_12m", "insumos_delta_3m"]]


def _build_dane(con) -> pd.DataFrame:
    """Variables socioeconómicas municipales: NBI (DANE Excel), población rural (si disponible)."""
    empty = pd.DataFrame(columns=["codigo_municipio", "nbi_total",
                                  "poblacion_rural", "pct_rural"])

    # Try new clean_dane_nbi first (DANE Excel), fall back to clean_dane_municipios (SODA)
    source = "clean_dane_nbi" if _table_exists(con, "clean_dane_nbi") else \
             ("clean_dane_municipios" if _table_exists(con, "clean_dane_municipios") else None)
    if not source:
        logger.warning("[vulnerabilidad] Ninguna tabla DANE disponible. Vars serán NaN.")
        return empty

    cols = [r[0] for r in con.execute(
        f"SELECT column_name FROM information_schema.columns WHERE table_name='{source}'"
    ).fetchall()]

    selected = ["codigo_municipio"]
    for c in ("nbi_total", "poblacion_rural", "pct_rural"):
        selected.append(c if c in cols else f"NULL::DOUBLE AS {c}")

    df = con.execute(f"""
        SELECT {', '.join(selected)}
        FROM {source}
        WHERE codigo_municipio IS NOT NULL
    """).df()
    logger.info("[vulnerabilidad] %s: %d municipios cargados.", source, len(df))
    return df


def build(force: bool = False) -> None:
    """Genera features_vulnerabilidad y features_dane en DuckDB."""
    con = get_connection()

    if not force:
        if _table_exists(con, _TABLE) and _table_exists(con, _TABLE_DANE):
            logger.info("[vulnerabilidad] Tablas ya existen, omitiendo.")
            con.close()
            return

    logger.info("[vulnerabilidad] Construyendo variables de insumos agrícolas...")
    insumos_df = _build_insumos(con)
    if not insumos_df.empty:
        con.execute(f"CREATE OR REPLACE TABLE {_TABLE} AS SELECT * FROM insumos_df")
        (rows,) = con.execute(f"SELECT COUNT(*) FROM {_TABLE}").fetchone()  # type: ignore[misc]
        logger.info("[vulnerabilidad] '%s' creada: %d filas.", _TABLE, rows)

    logger.info("[vulnerabilidad] Construyendo variables socioeconómicas DANE...")
    dane_df = _build_dane(con)
    con.execute(f"CREATE OR REPLACE TABLE {_TABLE_DANE} AS SELECT * FROM dane_df")
    (rows,) = con.execute(f"SELECT COUNT(*) FROM {_TABLE_DANE}").fetchone()  # type: ignore[misc]
    logger.info("[vulnerabilidad] '%s' creada: %d filas.", _TABLE_DANE, rows)

    con.close()
