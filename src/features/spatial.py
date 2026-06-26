"""Join espacial: asigna código DANE de municipio a cada estación IDEAM.

Entrada:
    - data/raw/ideam_estaciones.parquet  (lat, lon por estación)
    - data/raw/municipios.gpkg           (polígonos municipales IGAC/DANE)

Salida:
    Tabla DuckDB `estaciones_municipio`:
        codigoestacion, latitud, longitud, codigo_municipio, nombre_municipio,
        codigo_departamento, nombre_departamento

Esta tabla es la llave que permite agregar mediciones IDEAM por municipio.
"""
from __future__ import annotations

import logging

import geopandas as gpd
import pandas as pd

from config import config
from src.ingestion.load_duckdb import get_connection

logger = logging.getLogger(__name__)

_RAW_ESTACIONES = f"{config.data_raw}/ideam_estaciones.parquet"
_RAW_MUNICIPIOS = f"{config.data_raw}/municipios.gpkg"
_TABLE = "estaciones_municipio"


def _load_estaciones() -> gpd.GeoDataFrame:
    """Lee estaciones y las convierte a GeoDataFrame (puntos lat/lon)."""
    df = pd.read_parquet(_RAW_ESTACIONES)

    # Normalizar nombres de columna a minúsculas sin espacios
    df.columns = [c.lower().strip() for c in df.columns]

    # Las columnas de lat/lon pueden llamarse diferente según la versión del dataset
    lat_col = next((c for c in df.columns if "latit" in c), None)
    lon_col = next((c for c in df.columns if "longit" in c), None)
    id_col  = next((c for c in df.columns if "codigo" in c), "codigoestacion")

    if not lat_col or not lon_col:
        raise ValueError(f"No se encontraron columnas lat/lon en estaciones. Columnas: {list(df.columns)}")

    df[lat_col] = pd.to_numeric(df[lat_col], errors="coerce")
    df[lon_col] = pd.to_numeric(df[lon_col], errors="coerce")
    df = df.dropna(subset=[lat_col, lon_col])

    gdf = gpd.GeoDataFrame(
        df[[id_col, lat_col, lon_col]].rename(columns={id_col: "codigoestacion", lat_col: "latitud", lon_col: "longitud"}),
        geometry=gpd.points_from_xy(df[lon_col], df[lat_col]),
        crs="EPSG:4326",
    )
    return gdf


def _load_municipios() -> gpd.GeoDataFrame:
    """Lee la capa de municipios del GeoPackage."""
    gdf = gpd.read_file(_RAW_MUNICIPIOS, layer="municipios")
    if gdf.crs is None or gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs("EPSG:4326")
    return gdf


def build(force: bool = False) -> None:
    """Genera la tabla `estaciones_municipio` en DuckDB."""
    con = get_connection()

    if not force:
        existing = con.execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = ?",
            [_TABLE],
        ).fetchone()[0]  # type: ignore[index]
        if existing:
            logger.info("[spatial] Tabla '%s' ya existe, omitiendo.", _TABLE)
            con.close()
            return

    logger.info("[spatial] Cargando estaciones y municipios...")
    estaciones = _load_estaciones()
    municipios = _load_municipios()

    logger.info("[spatial] Join espacial: %d estaciones x %d municipios...", len(estaciones), len(municipios))
    joined = gpd.sjoin(estaciones, municipios[["codigo_municipio", "nombre_municipio",
                                               "codigo_departamento", "nombre_departamento", "geometry"]],
                       how="left", predicate="within")

    result = joined[[
        "codigoestacion", "latitud", "longitud",
        "codigo_municipio", "nombre_municipio",
        "codigo_departamento", "nombre_departamento",
    ]].drop_duplicates(subset=["codigoestacion"])

    sin_municipio = result["codigo_municipio"].isna().sum()
    if sin_municipio:
        logger.warning("[spatial] %d estaciones sin municipio asignado (fuera del bbox).", sin_municipio)

    con.execute(f"CREATE OR REPLACE TABLE {_TABLE} AS SELECT * FROM result")
    (rows,) = con.execute(f"SELECT COUNT(*) FROM {_TABLE}").fetchone()  # type: ignore[misc]
    logger.info("[spatial] Tabla '%s' creada: %d filas.", _TABLE, rows)


    # Guardar geometrías de municipios (polígonos) para el API GeoJSON
    _TABLE_GEOM = "municipios_geom"
    municipios_geo = municipios[["codigo_municipio", "nombre_municipio",
                                 "codigo_departamento", "nombre_departamento", "geometry"]].copy()
    import shapely
    municipios_geo["geom"] = municipios_geo.geometry.apply(shapely.to_geojson)
    municipios_geo = municipios_geo.drop(columns=["geometry"])
    con.execute(f"CREATE OR REPLACE TABLE {_TABLE_GEOM} AS SELECT * FROM municipios_geo")
    (rows,) = con.execute(f"SELECT COUNT(*) FROM {_TABLE_GEOM}").fetchone()
    logger.info("[spatial] Tabla '%s' creada: %d filas.", _TABLE_GEOM, rows)
    con.close()
