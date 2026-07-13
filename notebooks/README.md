# notebooks/ — Experimentación y análisis exploratorio

Notebooks de análisis que trabajan sobre los resultados del pipeline
(`data/alerta.duckdb`). Son de **exploración y explicación**, no forman parte del pipeline
de producción (ese vive en `src/` y se orquesta con `scripts/run.py`).

| Notebook | Contenido |
|----------|-----------|
| `01_EDA_exploracion_datos.ipynb` | Experimentación y análisis exploratorio — inventario de tablas, cobertura, distribución del IRA, calidad de datos |
| `02_limpieza_transformacion.ipynb` | Limpieza, codificación y normalización (reutiliza `src/features/normalize.py`) |
| `03_analisis_descriptivo.ipynb` | Estadísticas básicas y correlaciones (features + sub-índices + IRA) |
| `04_modelo_predictivo.ipynb` | Entrenamiento simple y validación básica (RandomForest, R²/RMSE/MAE) |
| `05_reportes_automaticos.ipynb` | Reportes ejecutivos y gráficos dinámicos, exportables a CSV/HTML |

## Requisitos

1. **Haber corrido el pipeline** para que exista `data/alerta.duckdb`:

   ```bash
   make pipeline          # ingest → features → risk
   ```

   Cada notebook detecta si la base no existe y avisa qué ejecutar.

2. **Instalar dependencias** (ya incluidas en `requirements.txt`):

   ```bash
   pip install -r requirements.txt
   jupyter lab            # o: jupyter notebook
   ```

## Notas

- Los notebooks se conectan a DuckDB en **solo lectura**; no modifican las tablas del pipeline.
- Localizan la raíz del repo automáticamente (buscan `config.py` hacia arriba), así que
  funcionan desde `notebooks/` sin ajustar rutas.
- Ejecuta en orden: `02` guarda `_data_procesada.parquet` que reutilizan `03`+.
- Salidas generadas (`_data_procesada.parquet`, `reportes/`) están en `.gitignore`.
