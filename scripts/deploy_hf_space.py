"""One-shot deploy helper for Hugging Face Spaces (not part of runtime)."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import dotenv_values
from huggingface_hub import HfApi


def main() -> None:
    token = os.environ.get("HF_TOKEN")
    if not token:
        raise SystemExit("HF_TOKEN is required")

    api = HfApi(token=token)
    repo = "cgalvis21/alerta"
    vals = dotenv_values(Path(".env"))

    secrets = {
        "OPENROUTER_API_KEY": vals.get("OPENROUTER_API_KEY") or "",
        "GFW_API_KEY": vals.get("GFW_API_KEY") or "",
        "ALERTA_LIVE_REFRESH": "1",
        "ALERTA_DUCKDB_PATH": "data/alerta_serving.duckdb",
        "ALERTA_GFW_REFRESH_HOURS": "168",
        "NEXT_PUBLIC_API_URL": "http://127.0.0.1:8000",
        "API_PORT": "8000",
    }
    for key, value in secrets.items():
        if not value:
            print(f"skip empty secret {key}")
            continue
        api.add_space_secret(repo_id=repo, key=key, value=value)
        print(f"set secret {key} (len={len(value)})")

    try:
        api.delete_file(
            "data/alerta.duckdb",
            repo_id=repo,
            repo_type="space",
            commit_message="chore: remove full warehouse DuckDB from Space",
        )
        print("deleted data/alerta.duckdb from space")
    except Exception as exc:
        print("delete warehouse:", type(exc).__name__, str(exc)[:160])

    ignore = [
        ".env",
        ".git*",
        "**/__pycache__/**",
        "**/node_modules/**",
        "**/.next/**",
        "data/alerta.duckdb",
        "data/alerta.db",
        "data/models/**",
        "data/alerta_serving.*.duckdb",
        "data/.last_gfw_refresh.json",
        "data/raw/raw_gfw_subnational_2_drivers.json",
        "data/raw/raw_gfw_subnational_2_primary_drivers.json",
        ".venv/**",
        "venv/**",
        "*.pyc",
        "scripts/deploy_hf_space.py",
    ]

    api.upload_folder(
        folder_path=".",
        repo_id=repo,
        repo_type="space",
        commit_message="deploy: sync main with serving DB, GFW refresh, UX and AI PDF report",
        ignore_patterns=ignore,
    )
    print("upload complete")
    info = api.space_info(repo)
    print("space sdk:", info.sdk)
    print("space runtime:", getattr(info, "runtime", None))


if __name__ == "__main__":
    main()
