.PHONY: install db ingest features risk api web pipeline test

install:
	pip install -r requirements.txt
	cd src/web && npm install

db:
	psql -c "CREATE DATABASE alerta;" || true
	psql alerta -f scripts/schema.sql

ingest:
	python scripts/run_ingestion.py

features:
	python scripts/run_features.py

risk:
	python scripts/run_risk.py

pipeline: ingest features risk

api:
	uvicorn src.api.main:app --reload --port 8000

web:
	cd src/web && npm run dev

test:
	pytest tests/ -v
