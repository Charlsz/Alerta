"""Bootstrap + background GFW refresh for Hugging Face Spaces / Docker free tier.

On startup:
  1. Resolve DuckDB path (prefer small serving DB ~6MB)
  2. Optionally download serving DB from ALERTA_DUCKDB_URL
  3. Start a daemon thread that refreshes GFW on an interval

Env vars:
  ALERTA_DUCKDB_PATH       Path to DuckDB (default: data/alerta_serving.duckdb if present)
  ALERTA_DUCKDB_URL        HTTP(S) URL to download serving DB if missing
  ALERTA_LIVE_REFRESH      1/true to enable background refresh (auto-on when SPACE_ID set)
  ALERTA_GFW_REFRESH_HOURS Hours between GFW refreshes (default 168 = weekly)
  GFW_API_KEY              Needed to re-download GFW; rebuild-from-local JSON works without it
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import threading
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from config import config

logger = logging.getLogger("live_refresh")

_DEFAULT_SERVING = Path("data/alerta_serving.duckdb")
_MARKER = Path("data/.last_gfw_refresh.json")
_stop = threading.Event()
_thread: threading.Thread | None = None


def resolve_duckdb_path() -> str:
    """Pick serving DB when available — keeps Spaces/clones off the ~800MB warehouse."""
    explicit = os.environ.get("ALERTA_DUCKDB_PATH", "").strip()
    if explicit:
        config.duckdb_path = explicit
        return explicit

    full = Path("data/alerta.duckdb")
    serving = _DEFAULT_SERVING
    if serving.exists():
        config.duckdb_path = str(serving)
    elif full.exists():
        config.duckdb_path = str(full)
    else:
        config.duckdb_path = str(serving)
    return config.duckdb_path


def _env_flag(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def live_refresh_enabled() -> bool:
    auto = bool(os.environ.get("SPACE_ID"))
    return _env_flag("ALERTA_LIVE_REFRESH", default=auto)


def gfw_refresh_seconds() -> float:
    hours = float(os.environ.get("ALERTA_GFW_REFRESH_HOURS", "168"))
    return max(1.0, hours) * 3600.0


def bootstrap_duckdb() -> Path:
    """Ensure a DuckDB file exists, downloading from URL if configured."""
    resolve_duckdb_path()
    path = Path(config.duckdb_path)
    url = os.environ.get("ALERTA_DUCKDB_URL", "").strip()

    if path.exists() and path.stat().st_size > 0:
        logger.info(
            "[bootstrap] Usando DuckDB existente: %s (%.1f MB)",
            path,
            path.stat().st_size / 1e6,
        )
        return path

    if not url:
        logger.warning(
            "[bootstrap] No hay DuckDB en %s y ALERTA_DUCKDB_URL está vacío. "
            "Exporte con `python scripts/export_serving_db.py` o configure la URL.",
            path,
        )
        return path

    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".download.duckdb")
    logger.info("[bootstrap] Descargando DuckDB desde ALERTA_DUCKDB_URL …")
    urllib.request.urlretrieve(url, tmp)  # noqa: S310 — trusted deploy env URL
    tmp.replace(path)
    logger.info("[bootstrap] DuckDB listo: %s (%.1f MB)", path, path.stat().st_size / 1e6)
    return path


def refresh_status() -> dict:
    path = Path(config.duckdb_path)
    payload = {
        "duckdb_path": str(path),
        "duckdb_exists": path.exists(),
        "duckdb_mb": round(path.stat().st_size / 1e6, 2) if path.exists() else None,
        "gfw_api_key_set": bool(os.environ.get("GFW_API_KEY", "").strip()),
        "live_refresh_enabled": live_refresh_enabled(),
        "gfw_refresh_hours": gfw_refresh_seconds() / 3600.0,
        "last_gfw_refresh": None,
        "note": (
            "GFW/Hansen se actualiza ~1 vez al año; el refresh en Spaces re-descarga y "
            "reconstruye deforestacion. Clima + IRA completo: GitHub Actions -> nueva serving DB."
        ),
    }
    if _MARKER.exists():
        try:
            payload["last_gfw_refresh"] = json.loads(_MARKER.read_text(encoding="utf-8"))
        except Exception:
            payload["last_gfw_refresh"] = {"error": "marker unreadable"}
    return payload


def _write_marker(ok: bool, detail: str) -> None:
    _MARKER.parent.mkdir(parents=True, exist_ok=True)
    _MARKER.write_text(
        json.dumps(
            {
                "ok": ok,
                "detail": detail,
                "finished_at": datetime.now(timezone.utc).isoformat(),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def refresh_gfw(force_download: bool = True) -> None:
    """Re-download GFW when possible and rebuild features_deforestacion on a DB copy."""
    from src.features import deforestacion as feat_defor
    from src.ingestion import gfw_deforestacion

    api_key = os.environ.get("GFW_API_KEY", "").strip()
    if api_key:
        gfw_deforestacion.run(force=force_download)
    else:
        logger.warning(
            "[live] Sin GFW_API_KEY: se reusa JSON local y solo se reconstruye "
            "features_deforestacion."
        )
        gfw_deforestacion.run(force=False)

    serving = Path(config.duckdb_path)
    if not serving.exists():
        raise FileNotFoundError(
            f"No existe {serving}. Exporte antes: python scripts/export_serving_db.py"
        )

    tmp = serving.with_suffix(".refresh.duckdb")
    for p in (tmp, Path(str(tmp) + ".wal")):
        if p.exists():
            p.unlink()

    shutil.copy2(serving, tmp)
    old_path = config.duckdb_path
    t0 = time.time()
    try:
        config.duckdb_path = str(tmp)
        feat_defor.build(force=True)
    finally:
        config.duckdb_path = old_path

    bak = serving.with_suffix(".bak.duckdb")
    if bak.exists():
        bak.unlink()
    serving.replace(bak)
    tmp.replace(serving)
    bak.unlink(missing_ok=True)

    detail = f"features_deforestacion rebuilt in {time.time() - t0:.1f}s"
    logger.info("[live] %s", detail)
    _write_marker(True, detail)


def _loop() -> None:
    interval = gfw_refresh_seconds()
    logger.info(
        "[live] Refresh GFW cada %.0f h. Hansen es ~anual; clima/IRA vía GitHub Actions.",
        interval / 3600.0,
    )
    if _stop.wait(45):
        return
    while not _stop.is_set():
        try:
            logger.info("[live] Iniciando refresh GFW…")
            refresh_gfw(force_download=True)
            logger.info("[live] Refresh GFW OK")
        except Exception as exc:
            logger.exception("[live] Refresh GFW falló: %s", exc)
            _write_marker(False, str(exc)[:500])
        if _stop.wait(interval):
            break


def start_background_refresh() -> None:
    global _thread
    if not live_refresh_enabled():
        logger.info("[live] Background refresh desactivado")
        return
    if _thread and _thread.is_alive():
        return
    _stop.clear()
    _thread = threading.Thread(target=_loop, name="alerta-gfw-refresh", daemon=True)
    _thread.start()
    logger.info("[live] Hilo de refresh GFW iniciado")


def stop_background_refresh() -> None:
    _stop.set()
