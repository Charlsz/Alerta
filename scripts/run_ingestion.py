"""Run all ingestion scripts in order."""
import argparse
import importlib
import logging

from config import IRAConfig

logger = logging.getLogger(__name__)

_INGESTION_MODULES = [
    "src.ingestion.ideam_estaciones",
    "src.ingestion.eva",
    "src.ingestion.eva_calendario",
    "src.ingestion.ideam_precipitacion",
    "src.ingestion.ideam_temperatura",
    "src.ingestion.insumos",
]


def run_all(config: IRAConfig, force: bool = False) -> None:
    """Execute every ingestion module and continue on individual failures."""
    for module_name in _INGESTION_MODULES:
        try:
            module = importlib.import_module(module_name)
            module.run(config, force=force)
            logger.info("%s completed successfully", module_name)
        except Exception as exc:
            logger.error("%s failed: %s", module_name, exc)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    parser = argparse.ArgumentParser(description="Run all data ingestion scripts")
    parser.add_argument("--force", action="store_true", help="Force re-download for all datasets")
    args = parser.parse_args()

    config = IRAConfig()
    run_all(config, force=args.force)


if __name__ == "__main__":
    main()
