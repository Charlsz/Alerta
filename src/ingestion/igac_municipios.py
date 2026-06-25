"""Descarga la capa oficial de municipios de Colombia desde el IGAC.

Fuente: Geoportal IGAC — Cartografía Básica Colombia
https://geoportal.igac.gov.co/contenido/datos-abiertos-cartografia-y-geografia

Salida: data/raw/municipios.gpkg
  — Capa 'municipios' con campos:
      codigo_municipio (VARCHAR 5, código DANE),
      nombre_municipio (VARCHAR),
      codigo_departamento (VARCHAR 2),
      nombre_departamento (VARCHAR),
      geometry (MultiPolygon, EPSG:4326)

El GPKG se usa más adelante en spatial.py para asignar
coord lat/lon de estaciones IDEAM al municipio correspondiente.
"""
from __future__ import annotations

import io
import logging
from pathlib import Path

import geopandas as gpd
import requests

from config import config

logger = logging.getLogger(__name__)

# URL del shapefile de MGN municipios Colombia publicado por el DANE / IGAC.
# Se usa la versión del Marco Geo-estadístico Nacional (MGN) que es la fuente
# de códigos DANE usados en EVA y en IDEAM.
_MGN_URL = (
    "https://geoservicios.dane.gov.co/arcgis/rest/services/"
    "MGN_2022_COLOMBIA/FeatureServer/4/query"
    "?where=1%3D1&outFields=*&f=geojson&outSR=4326"
)

# Fallback: GeoJSON de municipios Colombia (MGN 2018, ODbL)
_FALLBACK_URL = (
    "https://raw.githubusercontent.com/"
    "caticoa3/colombia_mapa/master/co_2018_MGN_MPIO_POLITICO.geojson"
)

_OUTPUT = "municipios.gpkg"
_LAYER = "municipios"

# Mapeo de posibles nombres de columna en la fuente → nombre estándar del proyecto
_COL_MAP = {
    # MGN DANE
    "mpio_cdpmp": "codigo_municipio",
    "mpio_ccnct": "codigo_municipio",
    "mpio_cnmbr": "nombre_municipio",

    "dpto_ccdgo": "codigo_departamento",
    "dpto_cnmbr": "nombre_departamento",
    # Nombres alternativos
    "codigo_municipio": "codigo_municipio",
    "nombre_municipio": "nombre_municipio",
    "codigo_departamento": "codigo_departamento",
    "nombre_departamento": "nombre_departamento",
}


def _normalize_columns(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Renombra columnas al esquema estándar del proyecto."""
    rename = {
        col: _COL_MAP[col.lower()]
        for col in gdf.columns
        if col.lower() in _COL_MAP
    }
    gdf = gdf.rename(columns=rename)
    cols = list(dict.fromkeys(c for c in _COL_MAP.values() if c in gdf.columns))  # dedup, preserve order
    return gdf[cols + ["geometry"]]


def _fetch_geojson(url: str, label: str) -> gpd.GeoDataFrame | None:
    """Intenta descargar un GeoJSON y retorna GeoDataFrame o None si falla."""
    try:
        logger.info("[Municipios IGAC] Descargando desde %s ...", label)
        response = requests.get(url, timeout=120)
        response.raise_for_status()
        gdf = gpd.read_file(io.BytesIO(response.content))
        if gdf.empty:
            logger.warning("[Municipios IGAC] Respuesta vacía desde %s", label)
            return None
        return gdf
    except Exception as exc:  # noqa: BLE001
        logger.warning("[Municipios IGAC] Fallo en %s: %s", label, exc)
        return None


def run(force: bool = False) -> None:
    """Descarga la capa de municipios y la guarda como GeoPackage."""
    output_path = Path(config.data_raw) / _OUTPUT
    if output_path.exists() and not force:
        logger.info("[Municipios IGAC] Ya existe %s, omitiendo.", _OUTPUT)
        return

    # Intentar fuente primaria (DANE FeatureServer)
    gdf = _fetch_geojson(_MGN_URL, "DANE FeatureServer")

    # Fallback público si la fuente primaria falla
    if gdf is None:
        gdf = _fetch_geojson(_FALLBACK_URL, "fallback GitHub")

    if gdf is None:
        logger.error(
            "[Municipios IGAC] No se pudo obtener la capa de municipios. "
            "Descarga manual desde https://geoportal.igac.gov.co y "
            "guarda como data/raw/municipios.gpkg"
        )
        return

    # Reproyectar a WGS84 si hace falta
    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:4326")
    elif gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs("EPSG:4326")

    gdf = _normalize_columns(gdf)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    gdf.to_file(output_path, layer=_LAYER, driver="GPKG")
    logger.info(
        "[Municipios IGAC] %d municipios guardados en %s", len(gdf), output_path
    )

