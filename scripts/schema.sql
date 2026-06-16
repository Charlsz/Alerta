-- =============================================================================
-- schema.sql  —  Esquema de referencia del proyecto Alerta
-- =============================================================================
-- Este archivo documenta todas las tablas que viven en data/alerta.duckdb.
-- NO se ejecuta automáticamente; es referencia para el equipo y para auditoría.
--
-- Capas:
--   raw_*    → carga directa desde Parquet (load_duckdb.py)
--   clean_*  → tipos corregidos, DANE homologado (clean.py)
--   feat_*   → features derivadas por módulo de features/
--   ira_*    → resultados del motor de riesgo (risk/)
-- =============================================================================


-- ---------------------------------------------------------------------------
-- CAPA RAW: datos crudos inferidos desde Parquet
-- ---------------------------------------------------------------------------

-- Catálogo de estaciones hidrometeorológicas IDEAM
-- Fuente: datos.gov.co hp9r-jxuu
CREATE TABLE IF NOT EXISTS raw_estaciones (
    codigoestacion      VARCHAR,
    nombreestacion      VARCHAR,
    departamento        VARCHAR,
    municipio           VARCHAR,
    latitud             VARCHAR,   -- crudo: puede ser string
    longitud            VARCHAR,
    altitud             VARCHAR,
    estado              VARCHAR,
    tipoestacion        VARCHAR,
    fechainstalacion    VARCHAR,
    fechasuspension     VARCHAR
);

-- Evaluaciones Agropecuarias Municipales
-- Fuente: datos.gov.co 2pnw-mmge
CREATE TABLE IF NOT EXISTS raw_eva (
    anio                VARCHAR,
    departamento        VARCHAR,
    municipio           VARCHAR,
    codigomunicipio     VARCHAR,
    cultivo             VARCHAR,
    area_sembrada       VARCHAR,
    area_cosechada      VARCHAR,
    produccion          VARCHAR,
    rendimiento         VARCHAR
    -- columnas adicionales según versión del dataset
);

-- EVA Vista consolidada
-- Fuente: datos.gov.co fp29-z39g
CREATE TABLE IF NOT EXISTS raw_eva_vista (
    LIKE raw_eva
);

-- EVA Calendario de siembras y cosechas
-- Fuente: datos.gov.co 4229-puwp
CREATE TABLE IF NOT EXISTS raw_eva_calendario (
    codigomunicipio     VARCHAR,
    cultivo             VARCHAR,
    mes_siembra         VARCHAR,
    mes_cosecha         VARCHAR,
    semestre            VARCHAR
);

-- Índice de precios de insumos agrícolas (UPRA)
-- Fuente: datos.gov.co gwbi-fnzs
CREATE TABLE IF NOT EXISTS raw_insumos (
    fecha               VARCHAR,
    indice              VARCHAR,
    grupo               VARCHAR
    -- columnas adicionales según versión
);

-- Precipitación IDEAM (últimos 5 años)
-- Fuente: datos.gov.co s54a-sgyg
CREATE TABLE IF NOT EXISTS raw_precipitacion (
    codigoestacion      VARCHAR,
    codigosensor        VARCHAR,
    fechaobservacion    VARCHAR,
    valorobservado      VARCHAR,
    nombreestacion      VARCHAR,
    departamento        VARCHAR,
    municipio           VARCHAR,
    latitud             VARCHAR,
    longitud            VARCHAR,
    descripcionsensor   VARCHAR,
    unidadmedida        VARCHAR
);

-- Temperatura máxima del aire IDEAM (últimos 5 años)
-- Fuente: datos.gov.co ccvq-rp9s
CREATE TABLE IF NOT EXISTS raw_temperatura (
    LIKE raw_precipitacion
);


-- ---------------------------------------------------------------------------
-- CAPA CLEAN: tipos corregidos y código DANE homologado
-- ---------------------------------------------------------------------------

-- Estaciones IDEAM limpias
CREATE TABLE IF NOT EXISTS clean_estaciones (
    codigoestacion      VARCHAR         NOT NULL,
    nombreestacion      VARCHAR,
    departamento        VARCHAR,
    municipio           VARCHAR,
    latitud             DOUBLE          NOT NULL,
    longitud            DOUBLE          NOT NULL,
    altitud             DOUBLE,
    estado              VARCHAR,
    tipoestacion        VARCHAR
);

-- EVA limpia
CREATE TABLE IF NOT EXISTS clean_eva (
    anio                INTEGER,
    codigo_municipio    VARCHAR(5)      NOT NULL,   -- DANE 5 dígitos
    departamento        VARCHAR,
    municipio           VARCHAR,
    cultivo             VARCHAR         NOT NULL,
    area_sembrada       DOUBLE,
    area_cosechada      DOUBLE,
    produccion          DOUBLE,
    rendimiento         DOUBLE
);

-- EVA Vista limpia
CREATE TABLE IF NOT EXISTS clean_eva_vista (
    LIKE clean_eva
);

-- EVA Calendario limpio
CREATE TABLE IF NOT EXISTS clean_eva_calendario (
    codigo_municipio    VARCHAR(5),
    cultivo             VARCHAR,
    mes_siembra         INTEGER,
    mes_cosecha         INTEGER,
    semestre            VARCHAR
);

-- Índice de insumos limpio
CREATE TABLE IF NOT EXISTS clean_insumos (
    periodo             TIMESTAMP       NOT NULL,
    grupo               VARCHAR,
    insumos_nivel       DOUBLE          NOT NULL
);

-- Precipitación IDEAM limpia
CREATE TABLE IF NOT EXISTS clean_precipitacion (
    codigoestacion      VARCHAR         NOT NULL,
    fechaobservacion    TIMESTAMP       NOT NULL,
    valorobservado      DOUBLE          NOT NULL,   -- mm
    departamento        VARCHAR,
    municipio           VARCHAR,
    latitud             DOUBLE,
    longitud            DOUBLE,
    sensor              VARCHAR,
    unidadmedida        VARCHAR
);

-- Temperatura máxima limpia
CREATE TABLE IF NOT EXISTS clean_temperatura (
    LIKE clean_precipitacion   -- misma estructura, sensor = 'temperatura_maxima'
);


-- ---------------------------------------------------------------------------
-- CAPA FEATURES
-- ---------------------------------------------------------------------------

-- Join espacial: estación → municipio DANE
CREATE TABLE IF NOT EXISTS estaciones_municipio (
    codigoestacion          VARCHAR     NOT NULL,
    latitud                 DOUBLE,
    longitud                DOUBLE,
    codigo_municipio        VARCHAR(5)  NOT NULL,
    nombre_municipio        VARCHAR,
    codigo_departamento     VARCHAR,
    nombre_departamento     VARCHAR
);

-- Features de producción (Sub-índice de Exposición Productiva)
CREATE TABLE IF NOT EXISTS features_produccion (
    cultivo                 VARCHAR     NOT NULL,
    codigo_municipio        VARCHAR(5)  NOT NULL,
    rendimiento_promedio    DOUBLE,
    rendimiento_cv          DOUBLE,     -- coeficiente de variación
    area_sembrada           DOUBLE,
    area_cosechada          DOUBLE,
    participacion_municipal DOUBLE,     -- fracción del área nacional
    mes_siembra             INTEGER,
    mes_cosecha             INTEGER
);

-- Features climáticas (Sub-índice de Peligro Climático)
CREATE TABLE IF NOT EXISTS features_clima (
    codigo_municipio        VARCHAR(5)  NOT NULL,
    periodo                 TIMESTAMP   NOT NULL,
    precip_acum_7d          DOUBLE,     -- mm
    precip_acum_30d         DOUBLE,     -- mm
    precip_anomalia_30d     DOUBLE,     -- mm vs. línea base CHIRPS
    dias_secos_consecutivos INTEGER,
    dias_lluvia_extrema     INTEGER,
    tmax_media_7d           DOUBLE,     -- °C
    tmax_anomalia_30d       DOUBLE,     -- °C vs. media histórica
    dias_tmax_critica       INTEGER
);

-- Features de vulnerabilidad económica (Sub-índice SVE)
CREATE TABLE IF NOT EXISTS features_vulnerabilidad (
    periodo                 TIMESTAMP   NOT NULL,
    insumos_nivel           DOUBLE,
    insumos_anomalia_12m    DOUBLE,
    insumos_delta_3m        DOUBLE
);

-- Tabla maestra: join de las tres capas de features
-- Llave: (codigo_municipio, cultivo, periodo)
CREATE TABLE IF NOT EXISTS features_municipio_cultivo (
    codigo_municipio        VARCHAR(5)  NOT NULL,
    cultivo                 VARCHAR     NOT NULL,
    periodo                 TIMESTAMP   NOT NULL,

    -- SPC
    precip_acum_7d          DOUBLE,
    precip_acum_30d         DOUBLE,
    precip_anomalia_30d     DOUBLE,
    dias_secos_consecutivos INTEGER,
    dias_lluvia_extrema     INTEGER,
    tmax_media_7d           DOUBLE,
    tmax_anomalia_30d       DOUBLE,
    dias_tmax_critica       INTEGER,

    -- SEP
    area_sembrada           DOUBLE,
    area_cosechada          DOUBLE,
    rendimiento_promedio    DOUBLE,
    rendimiento_cv          DOUBLE,
    participacion_municipal DOUBLE,
    fase_fenologica         INTEGER,    -- 1 si periodo es mes crítico

    -- SVE
    insumos_nivel           DOUBLE,
    insumos_anomalia_12m    DOUBLE,
    insumos_delta_3m        DOUBLE
);


-- ---------------------------------------------------------------------------
-- CAPA RIESGO
-- ---------------------------------------------------------------------------

-- Resultados finales del motor de riesgo
CREATE TABLE IF NOT EXISTS ira_resultados (
    codigo_municipio    VARCHAR(5)  NOT NULL,
    cultivo             VARCHAR     NOT NULL,
    periodo             TIMESTAMP   NOT NULL,

    -- Sub-índices (0-1)
    spc                 DOUBLE,     -- Sub-índice de Peligro Climático
    sep                 DOUBLE,     -- Sub-índice de Exposición Productiva
    sve                 DOUBLE,     -- Sub-índice de Vulnerabilidad Económica

    -- Score final
    ira_score           DOUBLE,     -- IRA en [0, 1]
    ira_nivel           VARCHAR,    -- 'Bajo' | 'Medio' | 'Alto' | 'Crítico'

    -- Anomalías
    anomaly_score       DOUBLE,     -- 0-1, más alto = más anómalo
    is_anomaly          BOOLEAN,

    -- Explicabilidad
    top3_variables      VARCHAR     -- JSON: [{var, label, shap}, ...]
);
