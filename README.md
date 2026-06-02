# Alerta

Plataforma de alerta temprana para riesgo climático agrícola basada en datos abiertos, orientada a priorizar municipios, cultivos y zonas agrícolas vulnerables en Colombia.

## Descripción

Este proyecto propone una solución analítica y geoespacial para identificar riesgo climático agrícola mediante la integración de información meteorológica reciente, series históricas, datos productivos y variables territoriales.

La plataforma busca apoyar la toma de decisiones mediante la priorización de territorios y cultivos con mayor exposición y vulnerabilidad frente a condiciones climáticas adversas.

## Objetivo general

Desarrollar una plataforma de alerta temprana para riesgo climático agrícola que utilice datos abiertos para analizar, integrar y visualizar información climática, productiva y territorial a nivel municipal.

## Objetivos específicos

- Integrar fuentes de datos abiertas de clima, producción agropecuaria, territorio y contexto socioeconómico.
- Construir variables e indicadores para caracterizar riesgo climático agrícola.
- Priorizar municipios, cultivos y zonas agrícolas vulnerables.
- Implementar modelos de analítica avanzada e inteligencia artificial para estimar riesgo climático agrícola.
- Desplegar una plataforma web para consulta, visualización y exploración de resultados.

## Alcance inicial

La solución se enfocará en:

- Integración de datos meteorológicos recientes e históricos.
- Uso de datos productivos agrícolas a nivel municipal.
- Incorporación de variables territoriales y cartografía oficial.
- Análisis geoespacial y generación de indicadores de riesgo.
- Visualización de resultados en una plataforma web con arquitectura monolítica modular.

## Fuentes de datos previstas

### Clima y meteorología
- IDEAM: precipitación, temperatura máxima, estaciones y eventos meteorológicos.
- CHIRPS: series históricas de precipitación.
- NASA POWER: variables climáticas complementarias.
- ERA5-Land: variables climáticas y de superficie.

### Producción agropecuaria
- EVA: área sembrada, área cosechada, producción y rendimiento.
- Agronet: estadísticas agrícolas y apoyo sectorial.
- UPRA: uso del suelo, aptitud y caracterización agropecuaria.

### Territorio y cartografía
- IGAC: cartografía oficial y variables territoriales.
- Colombia en Mapas: capas geográficas base para análisis espacial.

### Contexto socioeconómico
- DANE: variables socioeconómicas y de mercado.

### Observación satelital
- Sentinel-2: vegetación, cobertura y cambios en superficie.

## Herramientas y tecnologías

### Procesamiento y análisis
- Python
- Pandas
- GeoPandas
- NumPy
- Dask

### Infraestructura y análisis geoespacial
- PostgreSQL
- PostGIS
- QGIS
- Google Earth Engine

### Modelado y analítica avanzada
- Modelos de inteligencia artificial para estimación de riesgo climático agrícola
- Prithvi-EO-2.0 como referencia para exploración de modelado satelital avanzado

## Enfoque metodológico

El proyecto seguirá cuatro etapas principales:

1. **Integración de datos**  
   Recolección, limpieza, homologación y cruce de fuentes climáticas, productivas, territoriales y socioeconómicas.

2. **Construcción de variables**  
   Generación de indicadores de clima, exposición agrícola, contexto territorial y vulnerabilidad.

3. **Estimación de riesgo**  
   Aplicación de analítica avanzada e inteligencia artificial para estimar el riesgo climático agrícola.

4. **Visualización y priorización**  
   Desarrollo de una plataforma web para explorar resultados, visualizar mapas y priorizar municipios y cultivos.

## Equipo

Proyecto desarrollado en el marco de GovCamp 2026 y del reto:

**Agricultura y Desarrollo Rural – Implementar modelos de IA para predecir rendimientos agrícolas y riesgos climáticos.**

## Notas

Este repositorio documenta el desarrollo técnico y metodológico de la solución.  
El alcance, las fuentes y las herramientas podrán ajustarse durante la implementación según disponibilidad, calidad y utilidad analítica de los datos.


| Tipo                     | Dataset / Servicio                                        | Qué aporta                                                                        | URL                                                                                                                                      |
| ------------------------ | --------------------------------------------------------- | --------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| Producción agro          | Evaluaciones Agropecuarias Municipales EVA                | Base histórica de producción agrícola, áreas sembradas, cosechadas y rendimiento. | https://www.datos.gov.co/Agricultura-y-Desarrollo-Rural/Evaluaciones-Agropecuarias-Municipales-EVA/2pnw-mmge                             |
| Producción agro          | Vista Evaluaciones Agropecuarias Municipales EVA          | Vista actualizada de EVA con resultados estadísticos por municipio.               | https://www.datos.gov.co/Agricultura-y-Desarrollo-Rural/Vista-Evaluaciones-Agropecuarias-Municipales-EVA/fp29-z39g                       |
| Calendario cultivos      | EVA. Calendario Nacional de Siembras y Cosechas 2023-2024 | Distribución mensual de áreas sembradas y cosechadas por cultivo.                 | https://www.datos.gov.co/Agricultura-y-Desarrollo-Rural/Evaluaciones-Agropecuarias-Municipales-EVA-Calenda/4229-puwp/data?no_mobile=true |
| Calendario cultivos      | Consolidado calendarios EVA 2024 – UPRA                   | Archivo Excel consolidado con calendarios EVA 2024.                               | https://upra.gov.co/sites/default/files/2025-08/Consolidado%20calendarios%20EVA%202024.xlsx                                              |
| Clima observado          | Precipitación – IDEAM                                     | Lluvia registrada por estaciones automáticas; base para sequía/exceso de lluvia.  | https://www.datos.gov.co/Ambiente-y-Desarrollo-Sostenible/Precipitaci-n/s54a-sgyg                                                        |
| Clima observado          | Temperatura Máxima del Aire – IDEAM                       | Temperatura máxima por estación; útil para estrés térmico.                        | https://www.datos.gov.co/Ambiente-y-Desarrollo-Sostenible/Temperatura-M-xima-del-Aire/ccvq-rp9s                                          |
| Clima observado          | Dirección del Viento – IDEAM                              | Variable complementaria para análisis atmosférico.                                | https://www.datos.gov.co/Ambiente-y-Desarrollo-Sostenible/Direcci-n-del-Viento/kiw7-v9ta                                                 |
| Estaciones clima         | Catálogo Nacional de Estaciones del IDEAM                 | Ubicación, código y atributos de estaciones para cruces espaciales.               | https://www.datos.gov.co/Ambiente-y-Desarrollo-Sostenible/Cat-logo-Nacional-de-Estaciones-del-IDEAM/hp9r-jxuu                            |
| Territorio / mapas       | Colombia en Mapas                                         | Límites administrativos y capas geográficas para visualización y cruces.          | https://www.colombiaenmapas.gov.co                                                                                                       |
| Territorio / cartografía | IGAC – Datos Abiertos Cartografía y Geografía             | Cartografía oficial descargable.                                                  | https://geoportal.igac.gov.co/contenido/datos-abiertos-cartografia-y-geografia                                                           |
| Insumos agrícolas        | Índice de precios de insumos agrícolas                    | Costos de insumos para medir vulnerabilidad económica.                            | https://www.datos.gov.co/Agricultura-y-Desarrollo-Rural/-ndice-de-precios-de-insumos-agr-colas/gwbi-fnzs                                 |
