# src/features/ — Feature engineering

Construye variables e indicadores a partir de las tablas limpias en DuckDB.
Cada módulo expone `build(force=False)` que crea una tabla en DuckDB.

Salida final: tabla `features_municipio_cultivo` con 26 variables (14 SPC + 6 SEP + 6 SVE).

## Archivos

| Archivo | Líneas | Propósito |
|---------|--------|-----------|
| `clean.py` | 108 | Crea tablas `clean_*` en DuckDB desde `raw_*` con columnas normalizadas y tipos correctos |
| `clean_bridge.py` | 48 | Vistas DuckDB que mapean `raw_*` → `clean_*` para los módulos de features |
| `clima.py` | 250 | Construye 14 variables climáticas SPC por municipio × mes desde IDEAM |
| `municipio_lookup.py` | 135 | Homologación nombre_municipio → código DANE desde estaciones + IGAC |
| `normalize.py` | 63 | Normalización min-max robusta (p1–p99) para las 26 variables |
| `produccion.py` | 80 | Construye 6 variables SEP (área, rendimiento, participación, fase fenológica) |
| `spatial.py` | 102 | Join espacial estaciones IDEAM → municipios; crea `estaciones_municipio` y `municipios_geom` |
| `store.py` | 88 | Une clima + producción + vulnerabilidad en la tabla maestra (26 variables) |
| `vulnerabilidad.py` | 82 | Construye 6 variables SVE (insumos agrícolas + DANE socioeconómico) |
