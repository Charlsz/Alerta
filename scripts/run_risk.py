"""Orquestador del motor de riesgo (Pasos 7 y 7B).

Orden:
    1. normalize   — normaliza features_municipio_cultivo
    2. anomaly     — IsolationForest (detección de anomalías)
    3. ira         — calcula SPC, SEP, SVE e IRA score
    4. predict     — modelo predictivo de rendimiento (XGBoost/RF)
    5. store_risk  — guarda tabla ira_resultados en DuckDB

Uso:
    python scripts/run_risk.py
    python scripts/run_risk.py --force
    python scripts/run_risk.py --only predict
"""
from __future__ import annotations

import argparse
import importlib
import logging
import sys
import time
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class RiskStep:
    name: str
    module: str


_STEPS: list[RiskStep] = [
    RiskStep("predict",    "src.risk.predict_rendimiento"),
    RiskStep("anomaly",    "src.risk.anomaly"),
    RiskStep("ira",        "src.risk.ira"),
]


def _run_step(step: RiskStep, force: bool) -> bool:
    try:
        mod = importlib.import_module(step.module)
        fn = mod.build if hasattr(mod, "build") else mod.run  # type: ignore[attr-defined]
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
    parser = argparse.ArgumentParser(description="Motor de riesgo agroclimático")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--only", metavar="STEP",
                        help=f"Solo este paso: {', '.join(s.name for s in _STEPS)}")
    args = parser.parse_args()

    steps = _STEPS
    if args.only:
        steps = [s for s in _STEPS if s.name == args.only]
        if not steps:
            logger.error("Step '%s' no existe.", args.only)
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
        sys.exit(1)


if __name__ == "__main__":
    main()
