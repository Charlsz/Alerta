"""Ingesta de deforestación desde GFW Data API (Global Forest Watch).

La API actual ya no sirve `umd_tree_cover_loss` como tabla SQL (es ráster).
Para municipios usamos:
  - gadm__tcl__adm2_change  → pérdida anual (ha) por adm1/adm2
  - gadm_administrative_boundaries → nombres de departamento/municipio

Endpoint que acepta nuestra API key: GET .../download/json?sql=...
(POST .../query a veces falla con keys sin dominio).

Tras un clone, si los JSON ya existen, no hace falta GFW_API_KEY.
Con GFW_API_KEY + --force se re-descarga y se reescribe data/raw/.
"""
from __future__ import annotations

import json
import logging
import os
import re
from collections import defaultdict
from pathlib import Path

import requests

from config import config

logger = logging.getLogger(__name__)

_GFW_API_BASE = "https://data-api.globalforestwatch.org"
_TCL_DATASET = "gadm__tcl__adm2_change"
_GADM_DATASET = "gadm_administrative_boundaries"

_TREE_OUT = "raw_gfw_subnational_2_tree_cover_loss.json"
_PRIMARY_OUT = "raw_gfw_subnational_2_primary_loss.json"
_FILES = [_TREE_OUT, _PRIMARY_OUT]


def _headers(api_key: str) -> dict[str, str]:
    return {"x-api-key": api_key, "Accept": "application/json"}


def _resolve_version(dataset: str, api_key: str) -> str | None:
    try:
        r = requests.get(
            f"{_GFW_API_BASE}/dataset/{dataset}/latest",
            headers=_headers(api_key),
            timeout=60,
        )
        r.raise_for_status()
        return r.json()["data"]["version"]
    except Exception as exc:
        logger.warning("[GFW] No se pudo resolver versión de %s: %s", dataset, exc)
        return None


def _download_json(api_key: str, dataset: str, version: str, sql: str) -> list:
    """GET /download/json — funciona con keys sin dominio registrado."""
    url = f"{_GFW_API_BASE}/dataset/{dataset}/{version}/download/json"
    r = requests.get(
        url,
        headers=_headers(api_key),
        params={"sql": sql},
        timeout=300,
    )
    r.raise_for_status()
    data = r.json()
    if not isinstance(data, list):
        raise RuntimeError(f"Respuesta inesperada de {dataset}: {str(data)[:200]}")
    return data


def _adm_codes(gid_2: str) -> tuple[int, int] | None:
    # COL.1.11_2 → adm1=1, adm2=11
    m = re.match(r"^[A-Z]{3}\.(\d+)\.(\d+)_", str(gid_2 or ""))
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))


def _load_name_map(api_key: str) -> dict[tuple[int, int], tuple[str, str]]:
    version = _resolve_version(_GADM_DATASET, api_key)
    if not version:
        raise RuntimeError("No hay versión de gadm_administrative_boundaries")
    sql = (
        "SELECT gid_2, name_1, name_2 FROM gadm_administrative_boundaries "
        "WHERE gid_0='COL' AND gid_2 IS NOT NULL AND name_2 IS NOT NULL"
    )
    rows = _download_json(api_key, _GADM_DATASET, version, sql)
    mapping: dict[tuple[int, int], tuple[str, str]] = {}
    for row in rows:
        codes = _adm_codes(row.get("gid_2"))
        if not codes:
            continue
        mapping[codes] = (row.get("name_1") or "", row.get("name_2") or "")
    logger.info("[GFW] Nombres GADM COL: %d unidades adm2", len(mapping))
    return mapping


def _fetch_loss_long(api_key: str, primary_only: bool) -> list[dict]:
    version = _resolve_version(_TCL_DATASET, api_key)
    if not version:
        raise RuntimeError(f"No hay versión de {_TCL_DATASET}")
    primary_clause = "AND is__umd_regional_primary_forest_2001=true" if primary_only else ""
    sql = f"""
        SELECT iso, adm1, adm2,
               umd_tree_cover_loss__year AS year,
               SUM(umd_tree_cover_loss__ha) AS ha
        FROM {_TCL_DATASET}
        WHERE iso='COL'
          AND umd_tree_cover_density_2000__threshold=30
          {primary_clause}
        GROUP BY iso, adm1, adm2, umd_tree_cover_loss__year
    """
    rows = _download_json(api_key, _TCL_DATASET, version, sql)
    logger.info(
        "[GFW] Filas long %s: %d",
        "primary" if primary_only else "tree_cover",
        len(rows),
    )
    return rows


def _pivot_wide(long_rows: list[dict], name_map: dict[tuple[int, int], tuple[str, str]]) -> list[dict]:
    """Convierte (adm, year, ha) al formato legacy que usa features/deforestacion.py."""
    buckets: dict[tuple[int, int], dict] = {}
    unmatched = 0
    for row in long_rows:
        try:
            adm1 = int(row["adm1"])
            adm2 = int(row["adm2"])
            year = int(row["year"])
            ha = float(row["ha"] or 0)
        except (TypeError, ValueError, KeyError):
            continue
        names = name_map.get((adm1, adm2))
        if not names:
            unmatched += 1
            continue
        depto, muni = names
        key = (adm1, adm2)
        if key not in buckets:
            buckets[key] = {
                "country": "Colombia",
                "subnational1": depto,
                "subnational2": muni,
                "threshold": 30,
            }
        buckets[key][f"tc_loss_ha_{year}"] = ha

    if unmatched:
        logger.warning("[GFW] %d filas sin nombre GADM (omitidas)", unmatched)
    return list(buckets.values())


def _write_json(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False)
    logger.info("[GFW] %s guardado (%d municipios)", path.name, len(rows))


def _download_all(api_key: str) -> None:
    name_map = _load_name_map(api_key)
    tree_long = _fetch_loss_long(api_key, primary_only=False)
    primary_long = _fetch_loss_long(api_key, primary_only=True)
    raw = Path(config.data_raw)
    _write_json(raw / _TREE_OUT, _pivot_wide(tree_long, name_map))
    _write_json(raw / _PRIMARY_OUT, _pivot_wide(primary_long, name_map))


def _all_exist() -> bool:
    return all(
        (Path(config.data_raw) / f).exists() and (Path(config.data_raw) / f).stat().st_size > 0
        for f in _FILES
    )


def _missing() -> list[str]:
    missing = []
    for f in _FILES:
        path = Path(config.data_raw) / f
        if not path.exists() or path.stat().st_size == 0:
            missing.append(f)
    return missing


def run(force: bool = False) -> None:
    """Asegura JSON de deforestación en data/raw/.

    1. Si existen y no hay --force → no descarga (clones / Spaces sin red).
    2. Si hay GFW_API_KEY y (faltan o --force) → re-descarga vía Data API.
    """
    Path(config.data_raw).mkdir(parents=True, exist_ok=True)

    if _all_exist() and not force:
        logger.info(
            "[GFW] Datos locales listos (%s). No se necesita GFW_API_KEY.",
            ", ".join(_FILES),
        )
        return

    api_key = os.environ.get("GFW_API_KEY", "").strip()
    if api_key:
        logger.info("[GFW] Usando GFW_API_KEY para %s.", "actualizar" if force else "completar")
        try:
            _download_all(api_key)
            logger.info("[GFW] Descarga completada exitosamente.")
            return
        except Exception as exc:
            logger.warning("[GFW] Descarga falló: %s", exc)
            if _all_exist():
                logger.warning("[GFW] Se mantienen los JSON locales existentes.")
                return
            raise

    missing = _missing()
    if missing:
        logger.error(
            "[GFW] Faltan %d archivo(s): %s\n"
            "  1. Configure GFW_API_KEY en .env y vuelva a ejecutar.\n"
            "  2. O restaure los JSON desde el repo (git checkout -- data/raw/).",
            len(missing),
            ", ".join(missing),
        )
        raise RuntimeError(f"No se pudieron obtener los datos GFW. Faltan: {missing}")
