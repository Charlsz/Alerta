# Roadmap

Lo que falta para completar el proyecto según la visión de Alerta. Priorizado por impacto y esfuerzo.

## ✅ Completado

| Feature | Estado | Implementado en |
|---------|--------|-----------------|
| Asistente conversacional (LLM) | ✅ | `POST /api/municipio/{codigo}/chat` + chat UI en MunicipioCard |
| Reportes PDF automatizados con IA | ✅ | `src/web/app/reporte/[codigo]/page.jsx` con generación vía LLM |
| XGBoost | ✅ | `requirements.txt` (el pipeline lo usa automáticamente si está instalado) |
| Despliegue público (Docker) | ✅ | `Dockerfile` + `src/web/Dockerfile` + `docker-compose.yml` |
| Pipeline automático semanal | ✅ | `.github/workflows/pipeline.yml` con cron semanal + dispatch manual |
| Endpoint /api/status | ✅ | Muestra última actualización y estado del pipeline |

## Crítico — Datos rotos o ausentes

### 1. Reemplazar CHIRPS con NASA POWER o ERA5-Land

**Problema:** CHIRPS cambió su formato de distribución a un único archivo NetCDF combinado de ~7.7 GB. El pipeline actual no puede procesarlo. `precip_anomalia_30d` es NULL en todas las filas.

**Camino sugerido:**
1. Evaluar dos alternativas:
   - **NASA POWER API**: consultas por punto (lat, lon), requiere una llamada por centroide de municipio (1.122 requests).
   - **ERA5-Land** vía Copernicus CDS (`cdsapi`): un solo request para toda Colombia en bounding box.
2. Crear `src/ingestion/nasa_power.py` o adaptar `src/ingestion/chirps.py` para usar la nueva fuente.
3. Actualizar `src/features/clima.py` para leer de la nueva tabla.
4. Verificar que `precip_anomalia_30d` tenga valores en DuckDB.

**Archivos a tocar:** `src/ingestion/chirps.py`, `src/features/clima.py`, `scripts/run.py`

---

### 2. Parche DANE NBI

**Problema:** El dataset `fjhr-4qb9` fue eliminado de datos.gov.co. `nbi_total`, `poblacion_rural` y `pct_rural` son NULL, lo que degrada el sub-índice SVE.

**Camino sugerido:**
1. Descargar el Excel de NBI 2018 desde la página del DANE (Estadísticas → Pobreza → NBI).
2. Crear `src/ingestion/dane_nbi.py` que lea el Excel y lo guarde como parquet con `codigo_municipio` en formato DANE de 5 dígitos.
3. Actualizar `src/features/vulnerabilidad.py` para leer de la nueva tabla en lugar de `clean_dane_municipios`.
4. Confirmar que `nbi_total` y `pct_rural` tengan valores reales en `features_municipio_cultivo`.

**Archivos a tocar:** `src/ingestion/dane_nbi.py` (nuevo), `src/features/vulnerabilidad.py`, `scripts/run.py`

---

### 3. Viento IDEAM

**Problema:** Es el sexto dataset climático del IDEAM. Existe en `datos.gov.co` con ID `sgfv-3yp8` (169M filas) pero nunca se implementó el script de ingesta.

**Camino sugerido:**
1. Copiar `src/ingestion/ideam_humedad.py` → `src/ingestion/ideam_viento.py`.
2. Cambiar dataset ID a `sgfv-3yp8`, tabla a `raw_viento`.
3. Agregar al orquestador en `scripts/run.py`.
4. En `src/features/clima.py`, agregar `viento_media_7d` y `viento_anomalia_30d` siguiendo el patrón de humedad.
5. Agregar las nuevas variables al SPC en `src/risk/ira.py` y a la lista de predictores en `normalize.py`.

**Archivos a tocar:** `src/ingestion/ideam_viento.py` (nuevo), `src/features/clima.py`, `src/risk/ira.py`, `src/features/normalize.py`, `scripts/run.py`

---

## Medio — Mejora de calidad del modelo

### 4. Calibrar pesos del IRA con datos reales

**Problema:** Hoy los pesos del IRA son fijos (SPC=0.5, SEP=0.3, SVE=0.2) definidos en `config.py`. Idealmente deberían calibrarse con datos históricos de pérdidas agrícolas reales.

**Camino sugerido:**
1. Buscar el reporte de pérdidas agrícolas históricas del MADR (Excel público con pérdidas por municipio, año y cultivo).
2. Crear un script que cruce las pérdidas reportadas vs. el IRA calculado para ese período.
3. Ajustar los pesos para maximizar correlación entre IRA alto y pérdida real observada.
4. Actualizar `config.py` con los nuevos pesos.

**Nota:** Este paso puede requerir investigación externa para localizar el dataset adecuado. No hay una fuente limpia conocida en datos.gov.co.

**Archivos a tocar:** `config.py`, script de calibración nuevo

---

### 5. Deforestación (2 datasets)

**Problema:** Los datasets `cqcx-tjpz` (deforestación por año) y `em23-mwhw` (causas de deforestación) están identificados pero no se descargan ni integran.

**Camino sugerido:**
1. Verificar que tengan columna `codigo_municipio` en formato DANE 5 dígitos (muchos datasets ambientales usan solo nombre).
2. Crear `src/ingestion/deforestacion.py` con `fetch_soda("cqcx-tjpz")`.
3. Agregar variables `tasa_deforestacion` y `causa_principal` al SVE.
4. Agregar al orquestador.

**Archivos a tocar:** `src/ingestion/deforestacion.py` (nuevo), `src/features/vulnerabilidad.py`, `scripts/run.py`

---

## Bajo — Frontend y UX

### 6. Mostrar SHAP y tendencias en la UI

**Problema:** `importancia_top3` se calcula en `predict_rendimiento.py` y se guarda en `ira_resultados`, pero el frontend no lo renderiza. Tampoco hay gráfico de tendencia de los últimos 4 trimestres.

**Camino sugerido:**
1. En `MunicipioCard.jsx`, agregar sección que muestre las top-3 variables de `importancia_top3` (parseando el JSON).
2. En `MunicipioCard.jsx`, agregar un chart simple con los datos históricos del municipio (todos los períodos disponibles).
3. Agregar filtro por trimestre en `FilterBar.jsx`.

**Archivos a tocar:** `src/web/app/components/MunicipioCard.jsx`, `src/web/app/components/FilterBar.jsx`

---

## Nuevo — Nivel Avanzado (pendiente)

### 7. Datos satelitales NDVI

**Problema:** El proyecto no integra datos no estructurados (imágenes satelitales). El NDVI (Índice de Vegetación de Diferencia Normalizada) es un predictor clave para rendimiento agrícola.

**Camino sugerido:**
1. Integrar Sentinel Hub o MODIS NDVI vía API.
2. Crear `src/ingestion/satelital.py` que descargue NDVI promedio por municipio.
3. Agregar variable `ndvi_media_30d` al SPC.
4. Evaluar si se justifica una CNN para clasificación de imágenes.

**Archivos a tocar:** `src/ingestion/satelital.py` (nuevo), `src/features/clima.py`, `scripts/run.py`

---

### 8. LSTM para series climáticas

**Problema:** Las variables climáticas se agregan como promedios/anomalías simples. Un LSTM podría capturar patrones secuenciales y mejorar la predicción de rendimiento.

**Camino sugerido:**
1. Crear `src/risk/lstm_rendimiento.py` con PyTorch o TensorFlow.
2. Entrenar modelo secuencial con ventanas de 12 meses de datos climáticos diarios.
3. Comparar rendimiento vs. RandomForest/XGBoost actual.
4. Integrar como modelo alternativo o ensamble.

**Archivos a tocar:** `src/risk/lstm_rendimiento.py` (nuevo), `src/risk/predict_rendimiento.py`, `requirements.txt`

---

### 9. Sistema multiagente

**Problema:** El proyecto es monolítico. Un sistema multiagente permitiría monitoreo autónomo, alertas proactivas y recomendaciones personalizadas.

**Camino sugerido:**
1. Agente de monitoreo: verifica nuevas estaciones IDEAM cada hora.
2. Agente de alertas: dispara notificaciones cuando el IRA supera umbrales.
3. Agente de recomendaciones: sugiere acciones de mitigación por cultivo/municipio.
4. Agente de reportes: genera reportes periódicos automáticos.

---

## Resumen de esfuerzo

| Prioridad | Tarea | Esfuerzo estimado | Dependencias |
|---|---|---|---|
| ✅ | Chat LLM + Reportes PDF | Completado | — |
| ✅ | XGBoost | Completado | — |
| ✅ | Docker + docker-compose | Completado | — |
| ✅ | GitHub Actions cron | Completado | — |
| Crítico | NASA POWER / ERA5-Land | 2-3 días | Investigar API |
| Crítico | DANE NBI | 1 día | Descargar Excel |
| Crítico | Viento IDEAM | 1 día | Ninguna |
| Medio | Calibrar pesos IRA | 3-5 días | Encontrar dataset MADR |
| Medio | Deforestación | 1 día | Verificar columnas |
| Bajo | SHAP + tendencias UI | 2 días | Ninguna |
| Nuevo | NDVI satelital | 3-5 días | API clave / presupuesto |
| Nuevo | LSTM series climáticas | 5-7 días | PyTorch/TensorFlow |
| Nuevo | Sistema multiagente | 5-7 días | Definir objetivos |
