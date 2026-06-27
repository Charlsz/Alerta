# Alerta

Plataforma de alerta temprana para riesgo climático agrícola basada en datos abiertos, orientada a priorizar municipios, cultivos y zonas agrícolas vulnerables en Colombia.

## Descripción

Este proyecto integra datos meteorológicos, productivos, territoriales y socioeconómicos para calcular un **Índice de Riesgo Agrícola (IRA)** por municipio y cultivo. El resultado se visualiza en un mapa interactivo con ranking de municipios y fichas de detalle que explican por qué cada territorio está en riesgo.

El sistema está diseñado para anticipar pérdidas de cosecha antes de que ocurran, cuando todavía hay tiempo para actuar.

Incluye un **asistente conversacional con IA** que explica el riesgo de cada municipio en lenguaje natural y genera **reportes ejecutivos automatizados en PDF** con análisis y recomendaciones de mitigación.

## Enunciado del reto

**Agricultura y Desarrollo Rural — Datos Abiertos Colombia, Nivel Avanzado**

Reto: Implementar modelos de IA para predecir rendimientos agrícolas y riesgos climáticos.

Datos sugeridos: Producción agrícola, uso del suelo, datos meteorológicos y precios de mercado.

Impacto: Mayor productividad y resiliencia de comunidades rurales.

Requisitos del nivel avanzado:
- Integrar múltiples fuentes de datos abiertos (13–17 fuentes)
- Aplicar modelos de análisis sobre los datos (no solo visualizarlos)
- Producir valor accionable — una conclusión que alguien pueda usar para tomar una decisión real
- Presentar los resultados en una interfaz pública accesible sin conocimientos técnicos

## Objetivo general

Desarrollar una plataforma de alerta temprana para riesgo climático agrícola que utilice datos abiertos para analizar, integrar y visualizar información climática, productiva y territorial a nivel municipal.

## Objetivos específicos

- Integrar fuentes de datos abiertas de clima, producción agropecuaria, territorio y contexto socioeconómico.
- Construir variables e indicadores para caracterizar riesgo climático agrícola.
- Priorizar municipios, cultivos y zonas agrícolas vulnerables mediante un Índice de Riesgo Agroclimático (IRA).
- Implementar modelos de inteligencia artificial para detección de anomalías y predicción de rendimiento.
- Desplegar una plataforma web para consulta, visualización y exploración de resultados.

## Metodología del Índice de Riesgo Agroclimático (IRA)

El IRA es un número entre 0 y 1 que combina tres dimensiones para producir un score de riesgo por municipio y cultivo.

### Sub-índices

**1. Sub-índice de Peligro Climático (SPC) — peso 0.5**
Mide la intensidad y anomalía de las condiciones meteorológicas respecto al histórico de ese municipio. Incluye:
- Precipitación acumulada a 7 y 30 días.
- Días secos consecutivos y días con lluvia extrema.
- Temperatura máxima media a 7 días y anomalía vs. histórico.
- Días con temperatura máxima sobre umbral crítico por cultivo.
- Humedad relativa media y anomalía a 30 días.
- Presión atmosférica media y anomalía a 30 días.
- Temperatura ambiente media y temperatura mínima media a 30 días.

**2. Sub-índice de Exposición Productiva (SEP) — peso 0.3**
Mide la importancia agrícola del municipio y su dependencia del cultivo analizado:
- Área sembrada y cosechada por cultivo (EVA).
- Rendimiento promedio histórico y variabilidad (coeficiente de variación).
- Participación del cultivo en la producción municipal.
- Fase fenológica activa según calendario de siembras y cosechas (EVA Calendario).

**3. Sub-índice de Vulnerabilidad Económica (SVE) — peso 0.2**
Mide la capacidad de respuesta y el contexto socioeconómico:
- Nivel e índice de precios de insumos agrícolas (UPRA).
- Anomalía del índice de insumos vs. promedio 12 meses.
- Cambio de precios en 3 meses.
- Necesidades Básicas Insatisfechas — NBI (DANE).

### Fórmula del IRA

```
IRA = 0.5 × SPC + 0.3 × SEP + 0.2 × SVE
```

Cada sub-índice se normaliza entre 0 y 1 antes de combinarlos. El IRA final se clasifica en cuatro niveles: **Bajo (0–0.25)**, **Medio (0.25–0.50)**, **Alto (0.50–0.75)** y **Crítico (0.75–1.0)**.

### Componente de IA

Sobre el IRA base se aplican cuatro componentes de inteligencia artificial:

1. **Detección de anomalías multivariadas (IsolationForest)** — entrenado por cultivo para identificar municipios que presentan combinaciones inusuales de variables climáticas, productivas y económicas. Si un cultivo tiene menos de 50 muestras, se usa un modelo global.

2. **Predicción de rendimiento (RandomForest/XGBoost)** — predice el rendimiento esperado (t/ha) del próximo ciclo agrícola por municipio y cultivo usando 22 variables predictoras. Cada cultivo con ≥50 muestras recibe su propio modelo; cultivos pequeños usan un modelo global. La importancia de variables se explica vía SHAP, permitiendo al usuario entender qué factores disparan la alerta en cada municipio.

3. **Asistente conversacional (LLM via OpenRouter)** — por cada municipio, el usuario puede hacer preguntas en lenguaje natural sobre el nivel de riesgo, los componentes del IRA, la predicción de rendimiento y recibir recomendaciones de mitigación. Usa `openrouter/owl-alpha` (modelo gratuito) con contexto completo de los datos del municipio.

4. **Generación de reportes ejecutivos (IA generativa)** — el LLM produce un reporte estructurado con análisis de riesgo, desglose de componentes, predicción de rendimiento y recomendaciones concretas, renderizado como página imprimible/PDF.

## Fuentes de datos implementadas

| Categoría | Fuente | Dataset ID | Qué aporta | Estado |
|---|---|---|---|---|
| Clima | IDEAM — Precipitación | s54a-sgyg | Precipitación diaria (280M filas, filtro últimos 5 años) | ✅ Implementado |
| Clima | IDEAM — Temperatura máxima | ccvq-rp9s | Temperatura máxima diaria (27M filas, últimos 5 años) | ✅ Implementado |
| Clima | IDEAM — Humedad relativa | uext-mhny | Humedad del aire (87M filas, últimos 5 años) | ✅ Implementado |
| Clima | IDEAM — Presión atmosférica | 62tk-nxj5 | Presión atmosférica (34M filas, últimos 5 años) | ✅ Implementado |
| Clima | IDEAM — Temperatura ambiente | sbwg-7ju4 | Temperatura ambiente media y mínima (90M filas, últimos 5 años) | ✅ Implementado |
| Clima | IDEAM — Viento | sgfv-3yp8 | Velocidad del viento (600K filas, últimos 2 años) | ✅ Implementado |
| Satelital | MODIS (HDX) | ndvi-municipio | NDVI mensual por municipio (184K filas, 2022–2026) | ✅ Implementado |
| Ambiental | GFW / Hansen | Subnational 2 | Pérdida de cobertura arbórea por municipio (26K filas, 2001–2025) | ✅ Implementado |
| Producción | EVA | 2pnw-mmge | Área sembrada, cosechada, producción y rendimiento (200K filas) | ✅ Implementado |
| Producción | EVA — Vista | fp29-z39g | Vista estadística auxiliar (170 filas) | ✅ Implementado |
| Producción | EVA — Calendario | UPRA Excel | Calendario de siembras y cosechas por cultivo | ✅ Implementado |
| Insumos | UPRA | gwbi-fnzs | Índice de precios de insumos agrícolas (88 filas) | ✅ Implementado |
| Cartografía | IGAC / DANE | FeatureServer + GeoJSON | Geometrías municipales (1.122 municipios) | ✅ Implementado |
| Cartografía | Catálogo estaciones IDEAM | hp9r-jxuu | Ubicación de estaciones meteorológicas (9.685 estaciones) | ✅ Implementado |
| Socioeconómico | DANE — NBI | Excel DANE | Necesidades Básicas Insatisfechas por municipio (1.123 municipios) | ✅ Implementado |

## Variables calculadas (26 features)

| Sub-índice | Variables | Fuente |
|---|---|---|
| SPC (14) | precip_acum_7d, precip_acum_30d, precip_anomalia_30d, dias_secos_consecutivos, dias_lluvia_extrema, tmax_media_7d, tmax_anomalia_30d, dias_tmax_critica, humedad_media_30d, humedad_anomalia_30d, presion_media_30d, presion_anomalia_30d, tambiente_media_30d, tmin_media_30d | IDEAM |
| SEP (6) | area_sembrada, area_cosechada, rendimiento_promedio, rendimiento_cv, participacion_municipal, fase_fenologica | EVA + EVA Calendario |
| SVE (6) | insumos_nivel, insumos_anomalia_12m, insumos_delta_3m, nbi_total, poblacion_rural, pct_rural | UPRA + DANE |

## Arquitectura

```
┌──────────┐    ┌───────────────┐    ┌───────────┐    ┌──────────┐
│ Fuentes  │───→│ data/raw/     │───→│ DuckDB    │───→│ FastAPI  │
│ externas │    │ *.parquet     │    │ alerta.db │    │ :8000    │
└──────────┘    └───────────────┘    └───────────┘    └────┬─────┘
                                                            │
                                               ┌────────────┴─────┐
                                               │ Next.js :3000    │
                                               │ (proxy /api/*)   │
                                               └──────────────────┘
```

- **Ingesta**: scripts independientes descargan datos de IDEAM, EVA, UPRA, IGAC → Parquet
- **Feature engineering**: DuckDB SQL construye tablas limpias y 26 variables por municipio × cultivo
- **Riesgo**: IRA + IsolationForest + RandomForest para predicción de rendimiento
- **API**: FastAPI con 9 endpoints REST (filters, ranking, municipios, municipio detalle, chat LLM, multiagent, ndvi, deforestacion, status)
- **Frontend**: Next.js 15 con Leaflet para mapa interactivo, chat asistente, reportes PDF
- **LLM**: OpenRouter API (modelo `openrouter/owl-alpha`) para asistente conversacional y generación de reportes
- **Automatización**: GitHub Actions (cron semanal) + Docker Compose

## Herramientas y tecnologías

### Procesamiento y análisis de datos
- Python 3.14
- Pandas / NumPy
- DuckDB + extensión espacial
- GeoPandas + Shapely

### Modelado y analítica
- Scikit-learn (IsolationForest, RandomForest, XGBoost, cross-validation)
- Joblib (persistencia de modelos)
- SHAP (explicabilidad de modelos)

### Inteligencia Artificial generativa
- OpenRouter API (modelo `openrouter/owl-alpha`)
- Integración LLM para chat conversacional y reportes automatizados

### Backend y API
- FastAPI + Uvicorn
- DuckDB (conexión directa, sin ORM)
- 9 endpoints REST

### Frontend y visualización
- Next.js 15 (App Router)
- React 19
- Leaflet (mapas interactivos)
- Chat asistente con IA
- Reportes PDF imprimibles

### Orquestación y despliegue
- Makefile (comandos agrupados)
- Script único `scripts/run.py` con pasos `ingest`, `features`, `risk`
- Docker Compose (API + frontend)
- GitHub Actions (pipeline automático semanal)

## Cómo ejecutar

```bash
# 0. Configurar API key para el asistente IA (opcional para chat/reportes)
# Copiar .env.example a .env y agregar OPENROUTER_API_KEY

# 1. Instalar dependencias
make install

# 2. Pipeline completo (horas, dependiendo de internet)
make pipeline          # equivalente a: make ingest && make features && make risk

# O paso a paso:
python scripts/run.py ingest          # descarga datos crudos
python scripts/run.py features        # construye variables en DuckDB
python scripts/run.py risk --force    # calcula IRA + anomalías + predicciones

# 3. Iniciar servicios
make api              # uvicorn en :8000
make web              # Next.js en :3000

# 4. Abrir navegador en http://localhost:3000

# 5. (Opcional) Iniciar con Docker
make docker-build && make docker-up
```

## Endpoints de la API

| Método | Ruta | Descripción |
|---|---|---|---|---|
| GET | `/api/status` | Estado del pipeline y última actualización de datos |
| GET | `/api/filters` | Cultivos y departamentos disponibles |
| GET | `/api/ranking` | Ranking paginado municipio–cultivo por IRA |
| GET | `/api/municipios` | GeoJSON con último IRA por municipio (1.122 features) |
| GET | `/api/municipio/{codigo}` | Historial completo por municipio y cultivo |
| GET | `/api/municipio/{codigo}/deforestacion` | Datos de deforestación GFW/Hansen |
| GET | `/api/municipio/{codigo}/ndvi` | Serie temporal NDVI satelital (MODIS) |
| GET | `/api/municipio/{codigo}/multiagent` | Análisis multi-agente del riesgo |
| POST | `/api/municipio/{codigo}/chat` | Pregunta al asistente IA sobre el municipio |
| GET | `/reporte/{codigo}` | Reporte ejecutivo imprimible/PDF (frontend) |

## Salidas del pipeline

| Tabla / Archivo | Filas | Contenido |
|---|---|---|---|
| `features_municipio_cultivo` | 43.192 | 26 variables por municipio × cultivo × período |
| `features_clima` | 2.328 | 15 variables climáticas (incl. viento) por municipio × mes |
| `features_ndvi` | 60.210 | NDVI medio mensual + anomalía por municipio |
| `features_deforestacion` | 1.014 | Pérdida de cobertura arbórea por municipio (2001–2025) |
| `ira_resultados` | 43.192 | IRA score + nivel + anomalía + predicción de rendimiento |
| `predicciones_rendimiento` | 33.291 | Rendimiento predicho XGBoost (t/ha) con IC 95% y SHAP top-3 |
| `predicciones_nnet` | 33.291 | Rendimiento predicho Red Neuronal (t/ha) con IC 95% |
| `data/models/iforest_*.joblib` | 183 | Modelos IsolationForest por cultivo |
| `data/models/rendimiento_*.joblib` | 183 | Modelos de predicción de rendimiento por cultivo |

## Links / datos encontrados

| Tipo | Dataset / Servicio | URL |
|---|---|---|
| Clima — Precipitación | IDEAM — datos.gov.co | https://www.datos.gov.co/Ambiente-y-Desarrollo-Sostenible/Precipitaci-n/s54a-sgyg |
| Clima — Temperatura máxima | IDEAM — datos.gov.co | https://www.datos.gov.co/Ambiente-y-Desarrollo-Sostenible/Temperatura-M-xima-del-Aire/ccvq-rp9s |
| Clima — Humedad | IDEAM — datos.gov.co | https://www.datos.gov.co/Ambiente-y-Desarrollo-Sostenible/Humedad-del-Aire/uext-mhny |
| Clima — Presión atmosférica | IDEAM — datos.gov.co | https://www.datos.gov.co/Ambiente-y-Desarrollo-Sostenible/Presi-n-Atmosf-rica/62tk-nxj5 |
| Clima — Temperatura ambiente | IDEAM — datos.gov.co | https://www.datos.gov.co/Ambiente-y-Desarrollo-Sostenible/Temperatura-Ambiente-del-Aire/sbwg-7ju4 |
| Clima — Viento | IDEAM — datos.gov.co | https://www.datos.gov.co/Ambiente-y-Desarrollo-Sostenible/Velocidad-del-Viento/sgfv-3yp8 |
| Producción — EVA | datos.gov.co | https://www.datos.gov.co/Agricultura-y-Desarrollo-Rural/Evaluaciones-Agropecuarias-Municipales-EVA/2pnw-mmge |
| Producción — EVA Vista | datos.gov.co | https://www.datos.gov.co/Agricultura-y-Desarrollo-Rural/Vista-Evaluaciones-Agropecuarias-Municipales-EVA/fp29-z39g |
| Producción — EVA Calendario | UPRA | https://upra.gov.co/sites/default/files/2025-08/Consolidado%20calendarios%20EVA%202024.xlsx |
| Insumos agrícolas | UPRA — datos.gov.co | https://www.datos.gov.co/Agricultura-y-Desarrollo-Rural/ndice-de-Precios-de-Insumos-Agr-colas/gwbi-fnzs |
| Estaciones IDEAM | datos.gov.co | https://www.datos.gov.co/Ambiente-y-Desarrollo-Sostenible/Cat-logo-Estaciones-IDEAM/hp9r-jxuu |
| Cartografía — IGAC | geoportal.igac.gov.co | https://geoportal.igac.gov.co/contenido/datos-abiertos-cartografia-y-geografia |
| Ambiental — Deforestación | datos.gov.co | https://www.datos.gov.co/Ambiente-y-Desarrollo-Sostenible/Deforestaci-n-por-a-o/cqcx-tjpz |
| Ambiental — Causas deforestación | datos.gov.co | https://www.datos.gov.co/Ambiente-y-Desarrollo-Sostenible/Causas-de-Deforestaci-n/em23-mwhw |

## Roadmap

Ver [ROADMAP.md](ROADMAP.md) para el detalle de próximas mejoras: calibración adaptativa de pesos del IRA, deep learning para series climáticas, y expansión a más cultivos.

## Notas

Este repositorio documenta el desarrollo técnico y metodológico de la solución presentada al concurso de Datos Abiertos de Colombia. El alcance, las fuentes y las herramientas se ajustaron durante la implementación según disponibilidad, calidad y utilidad analítica de los datos.

El asistente conversacional requiere una API key de OpenRouter configurada en `.env` como `OPENROUTER_API_KEY`. Sin ella, el chat y los reportes PDF muestran un mensaje de configuración pendiente; el resto de la plataforma funciona sin cambios.

La anomalía de precipitación se calcula contra el histórico IDEAM (promedio por municipio-mes), no contra CHIRPS. CHIRPS fue descartado por cambio de formato y la capa de ingesta correspondiente fue eliminada.
