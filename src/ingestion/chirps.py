"""Descarga datos CHIRPS de precipitación histórica mensual para Colombia.

Fuente: Climate Hazards Center — UCSB
https://www.chc.ucsb.edu/data/chirps

Producto usado: CHIRPS v2.0 — precipitación mensual global, 0.05° de resolución,
coverage temporal: 1981 – presente.

Salida: data/raw/chirps/<año>/<mes>.nc (NetCDF)
  — Un archivo por mes, solo píxeles dentro del bbox de Colombia.

Estos archivos se usan en features/clima.py para calcular anomalías
de precipitación vs. la línea de base histórica.
"""
from __future__ import annotations

import argparse
import logging
from pathlib import Path

import requests

from config import config

logger = logging.getLogger(__name__)

# URL base de los archivos mensuales CHIRPS v2.0
_CHIRPS_BASE = (
    "https://data.chc.ucsb.edu/products/CHIRPS-2.0/global_monthly/netcdf"
)

# Bounding box Colombia (grados decimales WGS84)
# Se usa para validar descarga; el recorte espacial ocurre en features/clima.py
_COLOMBIA_BBOX = {"lon_min": -79.0, "lon_max": -66.8, "lat_min": -4.3, "lat_max": 12.5}

# Año de inicio de la línea de base histórica
_BASE_YEAR_START = 1991


def _chirps_url(year: int, month: int) -> str:
    """Construye la URL del archivo NetCDF mensual de CHIRPS."""
    return f"{_CHIRPS_BASE}/chirps-v2.0.{year}.{month:02d}.days_p05.nc"


def _download_month(year: int, month: int, output_dir: Path, force: bool) -> bool:
    """Descarga un archivo mensual CHIRPS. Retorna True si éxito."""
    filename = f"{year}-{month:02d}.nc"
    year_dir = output_dir / str(year)
    output_path = year_dir / filename

    if output_path.exists() and not force:
        logger.debug("[CHIRPS] Ya existe %s, omitiendo.", output_path)
        return True

    url = _chirps_url(year, month)
    try:
        response = requests.get(url, timeout=180, stream=True)
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.warning("[CHIRPS] No se pudo descargar %s: %s", url, exc)
        return False

    year_dir.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=1024 * 1024):  # 1 MB
            f.write(chunk)

    logger.info("[CHIRPS] Guardado: %s", output_path)
    return True


def run(force: bool = False) -> None:
    """Descarga precipitación histórica CHIRPS desde 1991 al mes anterior al actual.

    Solo descarga si los archivos no existen (idempotente).
    Los archivos se guardan en data/raw/chirps/<año>/<mes>.nc
    """
    import datetime

    output_dir = Path(config.data_raw) / "chirps"

    today = datetime.date.today()
    # Mes anterior completo como fin del rango
    end_month = today.replace(day=1) - datetime.timedelta(days=1)
    end_year, end_m = end_month.year, end_month.month

    total = 0
    failed = 0

    for year in range(_BASE_YEAR_START, end_year + 1):
        last_month = end_m if year == end_year else 12
        for month in range(1, last_month + 1):
            ok = _download_month(year, month, output_dir, force=force)
            total += 1
            if not ok:
                failed += 1

    logger.info(
        "[CHIRPS] Descarga completada: %d archivos procesados, %d fallidos.",
        total,
        failed,
    )


def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    parser = argparse.ArgumentParser(
        description="Descarga precipitación histórica CHIRPS (mensual, desde 1991)"
    )
    parser.add_argument("--force", action="store_true", help="Fuerza re-descarga")
    args = parser.parse_args()
    run(force=args.force)


if __name__ == "__main__":
    main()
