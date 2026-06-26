"""Run any pipeline step.

Usage:
    python scripts/run.py ingest
    python scripts/run.py features --force
    python scripts/run.py risk --only ira
"""
import argparse
import importlib
import logging
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("PYTHONIOENCODING", "utf-8")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
    force=True,
)
logger = logging.getLogger("run")

STEPS = {
    "ingest": [
        ("estaciones",    "src.ingestion.ideam_estaciones"),
        ("municipios",    "src.ingestion.igac_municipios"),
        ("eva",           "src.ingestion.eva"),
        ("eva_calendario","src.ingestion.eva_calendario"),
        ("insumos",       "src.ingestion.insumos"),
        ("dane",          "src.ingestion.dane_municipios"),
        ("precipitacion", "src.ingestion.ideam_precipitacion"),
        ("temperatura",   "src.ingestion.ideam_temperatura"),
        ("humedad",       "src.ingestion.ideam_humedad"),
        ("presion",       "src.ingestion.ideam_presion"),
        ("tambiente",     "src.ingestion.ideam_tambiente"),
        ("chirps",        "src.ingestion.chirps"),
    ],
    "features": [
        ("load_duckdb",    "src.ingestion.load_duckdb"),
        ("clean",          "src.features.clean"),
        ("spatial",        "src.features.spatial"),
        ("produccion",     "src.features.produccion"),
        ("clima",          "src.features.clima"),
        ("vulnerabilidad", "src.features.vulnerabilidad"),
        ("store",          "src.features.store"),
    ],
    "risk": [
        ("predict",    "src.risk.predict_rendimiento"),
        ("anomaly",    "src.risk.anomaly"),
        ("ira",        "src.risk.ira"),
        ("store_risk", "src.risk.store_risk"),
    ],
}


def main():
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

    parser = argparse.ArgumentParser(description="Run a data pipeline.")
    parser.add_argument("pipeline", choices=list(STEPS))
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--only", metavar="STEP")
    args = parser.parse_args()

    steps = STEPS[args.pipeline]
    if args.only:
        steps = [s for s in steps if s[0] == args.only]
        if not steps:
            logger.error("Step '%s' not found.", args.only)
            sys.exit(1)

    results = {}
    for name, module in steps:
        logger.info("=== %s ===", name.upper())
        t0 = time.time()
        try:
            mod = importlib.import_module(module)
            fn = getattr(mod, "build", None) or getattr(mod, "run", None)
            if fn:
                fn(force=args.force)
            results[name] = True
            logger.info("OK %s (%.1fs)", name, time.time() - t0)
        except Exception as exc:
            logger.error("[%s] %s", name, exc, exc_info=True)
            results[name] = False

    if any(not ok for ok in results.values()):
        sys.exit(1)


if __name__ == "__main__":
    main()
