# ── Imagen base ───────────────────────────────────────────────────────────────
# Usamos python:3.12-slim para mantener la imagen liviana.
FROM python:3.12-slim

# Etiqueta de mantenedor
LABEL maintainer="Alerta – Riesgo Climático Agrícola"

# ── Variables de entorno ──────────────────────────────────────────────────────
# Evita que Python genere .pyc y que bufferee stdout/stderr.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# ── Directorio de trabajo ─────────────────────────────────────────────────────
WORKDIR /app

# ── Dependencias del sistema ──────────────────────────────────────────────────
# libgdal-dev y gdal-bin son necesarios para GeoPandas / rasterio.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libgdal-dev \
        gdal-bin \
        libgeos-dev \
        curl \
    && rm -rf /var/lib/apt/lists/*

# ── Dependencias Python ───────────────────────────────────────────────────────
# Copiar primero solo requirements.txt para aprovechar la caché de capas.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Código fuente ─────────────────────────────────────────────────────────────
COPY . .

# ── Directorio de datos ───────────────────────────────────────────────────────
# Se crea vacío; en desarrollo se monta como volumen desde el host.
RUN mkdir -p data/raw data/processed data/features

# ── Puerto expuesto ───────────────────────────────────────────────────────────
EXPOSE 8000

# ── Comando por defecto: API ──────────────────────────────────────────────────
# Para correr el pipeline en vez de la API:
#   docker compose run backend python scripts/run_ingestion.py
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
