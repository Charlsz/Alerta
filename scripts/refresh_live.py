"""CLI for lightweight live refresh (see src.api.live_refresh).

Usage:
    python scripts/refresh_live.py gfw
    python scripts/refresh_live.py gfw --force
    python scripts/refresh_live.py status
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from src.api.live_refresh import (  # noqa: E402
    bootstrap_duckdb,
    refresh_gfw,
    refresh_status,
    resolve_duckdb_path,
)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    parser = argparse.ArgumentParser(description="Live data refresh for deploy")
    parser.add_argument("action", choices=["gfw", "status"])
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-download GFW even if JSON exists (needs GFW_API_KEY)",
    )
    args = parser.parse_args()

    resolve_duckdb_path()
    if args.action == "status":
        print(json.dumps(refresh_status(), ensure_ascii=False, indent=2))
        return

    try:
        bootstrap_duckdb()
        refresh_gfw(force_download=args.force or True)
    except Exception:
        logging.exception("GFW refresh failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
