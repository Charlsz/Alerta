"""Orquestador de ingesta: corre todos los módulos de src/ingestion/ en orden.

Uso:
    python scripts/run_ingestion.py
    python scripts/run_ingestion.py --force       # fuerza re-descarga de todo
    python scripts/run_ingestion.py --only eva    # corre solo un módulo
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
class IngestStep:
    name: str
    module: str  # ruta importable, ej. "src.ingestion.eva"


# Orden de ejecución: estaciones primero (otros dependen de ellas para joins)
_STEPS: list[IngestStep] = [
    IngestStep("estaciones", "src.ingestion.ideam_estaciones"),
    IngestStep("municipios", "src.ingestion.igac_municipios"),
    IngestStep("eva", "src.ingestion.eva"),
    IngestStep("eva_calendario", "src.ingestion.eva_calendario"),
    IngestStep("insumos", "src.ingestion.insumos"),
    IngestStep("precipitacion", "src.ingestion.ideam_precipitacion"),
    IngestStep("temperatura", "src.ingestion.ideam_temperatura"),
    # CHIRPS va al final: es el más pesado (~400 MB histórico)
    IngestStep("chirps", "src.ingestion.chirps"),
]


def _run_step(step: IngestStep, force: bool) -> bool:
    """Importa el módulo y llama run(force=force). Retorna True si éxito."""
    try:
        mod = importlib.import_module(step.module)
        run_fn: Callable = mod.run  # type: ignore[attr-defined]
        run_fn(force=force)
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

    parser = argparse.ArgumentParser(description="Pipeline de ingesta de datos")
    parser.add_argument("--force", action="store_true", help="Fuerza re-descarga de todos los datasets")
    parser.add_argument(
        "--only",
        metavar="STEP",
        help=f"Corre solo este módulo. Opciones: {', '.join(s.name for s in _STEPS)}",
    )
    args = parser.parse_args()

    steps = _STEPS
    if args.only:
        steps = [s for s in _STEPS if s.name == args.only]
        if not steps:
            logger.error("Step '%s' no encontrado. Opciones: %s", args.only, [s.name for s in _STEPS])
            sys.exit(1)

    results: dict[str, bool] = {}
    for step in steps:
        logger.info("\n%s Iniciando: %s %s", "=" * 20, step.name.upper(), "=" * 20)
        t0 = time.time()
        ok = _run_step(step, force=args.force)
        elapsed = time.time() - t0
        results[step.name] = ok
        status = "✅" if ok else "❌"
        logger.info("%s %s completado en %.1fs", status, step.name, elapsed)

    # Resumen final
    logger.info("\n%s RESUMEN %s", "=" * 20, "=" * 20)
    failed = [name for name, ok in results.items() if not ok]
    for name, ok in results.items():
        logger.info("  %s %s", "✅" if ok else "❌", name)

    if failed:
        logger.warning("Fallaron %d módulos: %s", len(failed), failed)
        sys.exit(1)
    else:
        logger.info("Ingesta completada exitosamente.")


if __name__ == "__main__":
    main()
