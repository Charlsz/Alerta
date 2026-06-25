.PHONY: help install ingest features risk web pipeline test lint

# ── Ayuda ─────────────────────────────────────────────────────────────────────
help:  ## Muestra esta ayuda
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

# ── Entorno ───────────────────────────────────────────────────────────────────
install:  ## Instala dependencias Python y Node
	pip install -r requirements.txt
	cd src/web && npm install

# ── Pipeline de datos ─────────────────────────────────────────────────────────
ingest:  ## Descarga todos los datos crudos a data/raw/
	python scripts/run.py ingest

features:  ## Construye variables e indicadores en DuckDB
	python scripts/run.py features

risk:  ## Calcula IRA, anomalías y explicabilidad
	python scripts/run.py risk

pipeline: ingest features risk  ## Corre el pipeline completo end-to-end

# ── Servicios ─────────────────────────────────────────────────────────────────
web:  ## Inicia el frontend Next.js en modo desarrollo
	cd src/web && npm run dev

# ── Calidad ───────────────────────────────────────────────────────────────────
test:  ## Corre todos los tests con pytest
	pytest tests/ -v --cov=src --cov-report=term-missing

lint:  ## Verifica estilo de código con ruff
	ruff check src/ scripts/ config.py
