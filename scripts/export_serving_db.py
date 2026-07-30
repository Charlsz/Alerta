"""Export a small DuckDB with only the tables the web API needs.

Full `data/alerta.duckdb` is ~800MB (raw climate). The serving DB is ~6MB and is
what clones / Hugging Face Spaces should run against.

Usage:
    python scripts/export_serving_db.py
    python scripts/export_serving_db.py --source data/alerta.duckdb --out data/alerta_serving.duckdb
"""
from __future__ import annotations

import argparse
import logging
import shutil
import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from config import config  # noqa: E402

logger = logging.getLogger("export_serving_db")

SERVING_TABLES = [
    "ira_resultados",
    "estaciones_municipio",
    "municipios_geom",
    "features_deforestacion",
    "features_ndvi",
]


def export(source: Path, out: Path) -> Path:
    if not source.exists():
        raise FileNotFoundError(
            f"No existe {source}. Corre el pipeline completo antes de exportar "
            "(python scripts/run.py ingest && features && risk)."
        )

    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".tmp.duckdb")
    for p in (tmp, Path(str(tmp) + ".wal")):
        if p.exists():
            p.unlink()

    dst = duckdb.connect(str(tmp))
    dst.execute("INSTALL spatial; LOAD spatial;")
    # Forward slashes keep DuckDB happy on Windows paths.
    src_path = source.resolve().as_posix()
    dst.execute(f"ATTACH '{src_path}' AS src (READ_ONLY)")

    missing = []
    for table in SERVING_TABLES:
        try:
            dst.execute(f"CREATE TABLE {table} AS SELECT * FROM src.{table}")
        except Exception:
            missing.append(table)
            continue
        n = dst.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        logger.info("%-28s %s filas", table, n)

    dst.execute("DETACH src")
    dst.close()

    if missing:
        tmp.unlink(missing_ok=True)
        raise RuntimeError(f"Faltan tablas en la DB origen: {missing}")

    if out.exists():
        out.unlink()
    shutil.move(str(tmp), str(out))
    mb = out.stat().st_size / 1e6
    logger.info("Serving DB lista: %s (%.1f MB)", out, mb)
    return out


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Export small serving DuckDB for deploy")
    parser.add_argument("--source", type=Path, default=Path(config.duckdb_path))
    parser.add_argument("--out", type=Path, default=Path("data/alerta_serving.duckdb"))
    args = parser.parse_args()
    export(args.source, args.out)


if __name__ == "__main__":
    main()
