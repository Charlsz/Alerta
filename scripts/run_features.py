"""Orquestador de feature engineering (Pasos 4-6).

Orden de ejecución:
    1. load_duckdb    — Parquet → tablas raw_*
    2. clean          — raw_* → clean_* (tipos, DANE, filtros)
    3. clean_bridge   — crea vistas raw_*_view → clean_*
    4. spatial        — join espacial estaciones → municipio
    5. produccion     — features EVA
    6. clima          — features IDEAM + CHIRPS
    7. vulnerabilidad — features insumos
    8. store          — tabla maestra features_municipio_cultivo

Uso:
    python scripts/run_features.py
    python scripts/run_features.py --force
    python scripts/run_features.py --only clean
"""
from __future__ import annotations

import argparse
import importlib
import logging
import sys
import time
from dataclasses import dataclass
from typing import Callable

logger = logging.getLogger(__name__)


@dataclass
class FeatureStep:
    name: str
    module: str


_STEPS: list[FeatureStep] = [
    FeatureStep("load_duckdb",    "src.ingestion.load_duckdb"),
    FeatureStep("clean",          "src.features.clean"),
    FeatureStep("clean_bridge",   "src.features.clean_bridge"),
    FeatureStep("spatial",        "src.features.spatial"),
    FeatureStep("produccion",     "src.features.produccion"),
    FeatureStep("clima",          "src.features.clima"),
    FeatureStep("vulnerabilidad", "src.features.vulnerabilidad"),
    FeatureStep("store",          "src.features.store"),
]


def _run_step(step: FeatureStep, force: bool) -> bool:
    try:
        mod = importlib.import_module(step.module)
        fn: Callable = mod.run if hasattr(mod, "run") else mod.build  # type: ignore[attr-defined]
        fn(force=force)
        return True
    except Exception as exc:  # noqa: BLE001
        logger.error("[%s] ERROR: %s", step.name, exc, exc_info=True)
        return False


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    parser = argparse.ArgumentParser(description="Pipeline de feature engineering")
    parser.add_argument("--force", action="store_true", help="Reconstruye todas las tablas")
    parser.add_argument("--only", metavar="STEP", help=f"Solo este paso: {', '.join(s.name for s in _STEPS)}")
    args = parser.parse_args()

    steps = _STEPS
    if args.only:
        steps = [s for s in _STEPS if s.name == args.only]
        if not steps:
            logger.error("Step '%s' no existe. Opciones: %s", args.only, [s.name for s in _STEPS])
            sys.exit(1)

    results: dict[str, bool] = {}
    for step in steps:
        logger.info("\n%s %s %s", "=" * 20, step.name.upper(), "=" * 20)
        t0 = time.time()
        ok = _run_step(step, force=args.force)
        results[step.name] = ok
        logger.info("%s %s (%.1fs)", "✅" if ok else "❌", step.name, time.time() - t0)

    failed = [n for n, ok in results.items() if not ok]
    logger.info("\n%s RESUMEN %s", "=" * 20, "=" * 20)
    for name, ok in results.items():
        logger.info("  %s %s", "✅" if ok else "❌", name)
    if failed:
        logger.warning("Fallaron: %s", failed)
        sys.exit(1)


if __name__ == "__main__":
    main()
