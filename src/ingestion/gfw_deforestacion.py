"""Ingesta de datos de deforestación desde GFW (Global Forest Watch).

Descarga pérdida de cobertura arbórea y bosque primario por municipio
(subnational 2) para Colombia a través de la GFW Data API v2.

Requiere GFW_API_KEY en el entorno (o variables de entorno .env).
Como alternativa, los archivos pueden colocarse manualmente en data/raw/.

Fuente: https://www.globalforestwatch.org/
Dataset: umd_tree_cover_loss (Hansen/UMD)
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path

import requests

from config import config

logger = logging.getLogger(__name__)

# Datasets a descargar
_DATASETS = {
    "tree_cover_loss": {
        "dataset": "umd_tree_cover_loss",
        "sql": "SELECT * FROM umd_tree_cover_loss WHERE country='Colombia' AND threshold=30",
        "output": "raw_gfw_subnational_2_tree_cover_loss.json",
    },
    "primary_loss": {
        "dataset": "umd_tree_cover_loss",
        "sql": "SELECT * FROM umd_tree_cover_loss WHERE country='Colombia' AND threshold=30 AND primary_forest=true",
        "output": "raw_gfw_subnational_2_primary_loss.json",
    },
}
_FILES = list(d["output"] for d in _DATASETS.values())

_GFW_API_BASE = "https://data-api.globalforestwatch.org"


def _resolve_version(dataset: str) -> str | None:
    """Resuelve la versión más reciente del dataset."""
    try:
        r = requests.get(f"{_GFW_API_BASE}/dataset/{dataset}/latest", timeout=30)
        r.raise_for_status()
        return r.json()["data"]["version"]
    except Exception as exc:
        logger.warning("[GFW] No se pudo resolver versión de %s: %s", dataset, exc)
        return None


def _download_via_gfw_api(api_key: str, cfg: dict) -> bool:
    """Descarga un dataset vía GFW Data API query endpoint."""
    dataset = cfg["dataset"]
    sql = cfg["sql"]
    output = cfg["output"]
    dest = Path(config.data_raw) / output

    if dest.exists():
        return True

    version = _resolve_version(dataset)
    if not version:
        return False

    url = f"{_GFW_API_BASE}/dataset/{dataset}/{version}/query"
    headers = {"x-api-key": api_key}
    payload = {"sql": sql}

    logger.info("[GFW] Descargando %s via API...", output)
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=300)
        r.raise_for_status()
        body = r.json()
        rows = body.get("data") or []
        dest.parent.mkdir(parents=True, exist_ok=True)
        with open(dest, "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False, indent=2)
        logger.info("[GFW] %s guardado (%d registros)", output, len(rows))
        return True
    except Exception as exc:
        logger.warning("[GFW] Error descargando %s: %s", output, exc)
        return False


def _all_exist() -> bool:
    return all((Path(config.data_raw) / f).exists() for f in _FILES)


def run(force: bool = False) -> None:
    """Descarga datos de deforestación GFW a data/raw/."""
    if _all_exist() and not force:
        logger.info("[GFW] Todos los archivos existen, omitiendo.")
        return

    Path(config.data_raw).mkdir(parents=True, exist_ok=True)

    api_key = os.environ.get("GFW_API_KEY", "")
    if api_key:
        logger.info("[GFW] Usando GFW_API_KEY del entorno.")
        ok = 0
        for name, cfg in _DATASETS.items():
            if _download_via_gfw_api(api_key, cfg):
                ok += 1
        if ok == len(_DATASETS):
            logger.info("[GFW] Descarga completada exitosamente.")
            return

    # Si no se pudo descargar, verificar si faltan archivos
    missing = [f for f in _FILES if not (Path(config.data_raw) / f).exists()]
    if missing:
        logger.error(
            "[GFW] Faltan %d archivos. Opciones:\n"
            "  1. Configure GFW_API_KEY en .env (solicítela en "
            "https://data-api.globalforestwatch.org/)\n"
            "  2. Coloque manualmente los archivos JSON en data/raw/:\n"
            "     %s\n"
            "  3. Ejecute git add -f y commit de los archivos existentes "
            "en data/raw/raw_gfw_subnational_2_*.json",
            len(missing), ", ".join(missing),
        )
        raise RuntimeError(
            f"No se pudieron obtener los datos GFW. Faltan: {missing}"
        )
