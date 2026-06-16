"""Cliente SODA reutilizable para la API de datos.gov.co.

Todos los scripts de ingesta importan `fetch_soda` desde aquí.
No hay lógica de negocio — solo descarga paginada.
"""
from __future__ import annotations

import logging
import os
from typing import Any

import requests

logger = logging.getLogger(__name__)

_SODA_BASE = "https://www.datos.gov.co/resource"


def fetch_soda(
    dataset_id: str,
    page_size: int = 50_000,
    where: str | None = None,
    order: str | None = None,
) -> list[dict[str, Any]]:
    """Descarga un dataset SODA completo usando paginación.

    Args:
        dataset_id: ID del recurso en datos.gov.co (ej. ``hp9r-jxuu``).
        page_size: Filas por página. Default 50 000 (máximo SODA).
        where: Cláusula ``$where`` opcional (ej. ``fechaobservacion >= '2021-01-01'``).
        order: Campo de ordenamiento para paginación determinista (ej. ``:id``).
               Obligatorio en datasets grandes para evitar páginas duplicadas.

    Returns:
        Lista de dicts con todos los registros del dataset.
    """
    headers: dict[str, str] = {}
    token = os.getenv("SODA_APP_TOKEN")
    if token:
        headers["X-App-Token"] = token

    records: list[dict[str, Any]] = []
    offset = 0

    while True:
        params: dict[str, Any] = {"$limit": page_size, "$offset": offset}
        if where:
            params["$where"] = where
        if order:
            params["$order"] = order

        url = f"{_SODA_BASE}/{dataset_id}.json"
        try:
            response = requests.get(url, headers=headers, params=params, timeout=120)
            response.raise_for_status()
        except requests.RequestException as exc:
            logger.warning(
                "SODA request failed [%s offset=%s]: %s", dataset_id, offset, exc
            )
            break

        batch: list[dict[str, Any]] = response.json()
        if not batch:
            break

        records.extend(batch)
        logger.debug("[%s] %d filas acumuladas (offset=%d)", dataset_id, len(records), offset)
        offset += page_size

    logger.info("[%s] Descarga completada: %d filas totales", dataset_id, len(records))
    return records
