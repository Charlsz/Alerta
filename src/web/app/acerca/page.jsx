"use client";
export default function AcercaPage() {
  const dataSources = [
    ["Clima", "IDEAM — Precipitación", "Precipitación diaria (280M filas)"],
    ["Clima", "IDEAM — Temperatura máxima", "Temperatura máxima diaria (27M filas)"],
    ["Clima", "IDEAM — Humedad relativa", "Humedad del aire (87M filas)"],
    ["Clima", "IDEAM — Presión atmosférica", "Presión atmosférica (34M filas)"],
    ["Clima", "IDEAM — Temperatura ambiente", "Temperatura ambiente media y mínima (90M filas)"],
    ["Clima", "IDEAM — Viento", "Velocidad del viento (600K filas)"],
    ["Satelital", "MODIS (HDX)", "NDVI mensual por municipio (184K filas)"],
    ["Ambiental", "GFW / Hansen", "Pérdida de cobertura arbórea (26K filas)"],
    ["Producción", "EVA", "Área sembrada, cosechada, producción y rendimiento (200K filas)"],
    ["Insumos", "UPRA", "Índice de precios de insumos agrícolas"],
    ["Cartografía", "IGAC / DANE", "Geometrías municipales (1.122 municipios)"],
    ["Socioeconómico", "DANE — NBI", "Necesidades Básicas Insatisfechas"],
  ];

  const iraComponents = [
    { sigla: "SPC", nombre: "Peligro Climático", peso: "50%", value: "0.5", desc: "Precipitación, temperatura, humedad, presión y viento contra el histórico del municipio." },
    { sigla: "SEP", nombre: "Exposición Productiva", peso: "30%", value: "0.3", desc: "Área sembrada, rendimiento histórico, fase fenológica y dependencia del cultivo." },
    { sigla: "SVE", nombre: "Vulnerabilidad Económica", peso: "20%", value: "0.2", desc: "Precios de insumos, NBI, población rural y contexto socioeconómico." },
  ];

  const archSteps = [
    ["Ingesta", "Scripts independientes descargan datos de IDEAM, EVA, UPRA, IGAC y los almacenan como Parquet."],
    ["Features", "DuckDB SQL construye 26 variables por municipio × cultivo a partir de los datos crudos."],
    ["Riesgo", "Cálculo del IRA, detección de anomalías (IsolationForest) y predicción de rendimiento (XGBoost + Red Neuronal)."],
    ["API", "FastAPI con 9 endpoints REST expuestos para ranking, municipios, chat LLM y más."],
    ["Frontend", "Next.js 15 con mapa Leaflet interactivo, fichas de detalle y reportes PDF imprimibles."],
  ];

  return (
    <main className="about-page">
      <div className="about-hero">
        <h1>Alerta</h1>
        <p>Plataforma de alerta temprana para riesgo climático agrícola basada en datos abiertos, orientada a priorizar municipios, cultivos y zonas vulnerables en Colombia.</p>
      </div>

      <section className="about-section">
        <div className="about-section-header">
          <div className="about-section-icon" style={{ color: "var(--accent)", fontWeight: 700 }}>+</div>
          <h2>Qué hace</h2>
        </div>
        <p>
          Integra datos meteorológicos, productivos, territoriales y socioeconómicos de 15 fuentes
          abiertas para calcular un <strong>Índice de Riesgo Agrícola (IRA)</strong> por municipio y
          cultivo. El resultado se visualiza en un mapa interactivo, ranking de municipios y fichas
          de detalle que explican el origen del riesgo.
        </p>
        <p>
          El sistema anticipa pérdidas de cosecha antes de que ocurran. Incluye un asistente
          conversacional con IA que explica el riesgo de cada municipio en lenguaje natural y genera
          reportes ejecutivos automatizados en PDF con análisis y recomendaciones de mitigación.
        </p>
      </section>

      <section className="about-section">
        <div className="about-section-header">
          <div className="about-section-icon" style={{ color: "var(--accent)", fontWeight: 700 }}>#</div>
          <h2>Índice de Riesgo Agrícola (IRA)</h2>
        </div>
        <p>Número entre 0 y 1 que combina tres dimensiones para producir un score de riesgo por municipio y cultivo. Se clasifica en cuatro niveles: <strong>Bajo</strong> (0–0.25), <strong>Medio</strong> (0.25–0.50), <strong>Alto</strong> (0.50–0.75) y <strong>Crítico</strong> (0.75–1.0).</p>
        <div className="about-formula">IRA = 0.5 × SPC + 0.3 × SEP + 0.2 × SVE</div>
        <div className="about-grid-2">
          {iraComponents.map((c) => (
            <div key={c.sigla} className="about-card-component">
              <h3>{c.sigla}</h3>
              <div className="label">{c.nombre}</div>
              <div className="value">{c.value}</div>
              <div className="desc" style={{ marginTop: 8 }}>Peso: {c.peso}</div>
              <div className="desc">{c.desc}</div>
            </div>
          ))}
        </div>
      </section>

      <section className="about-section">
        <div className="about-section-header">
          <div className="about-section-icon" style={{ color: "var(--accent)", fontWeight: 700 }}>~</div>
          <h2>Componentes de IA</h2>
        </div>
        <div className="about-grid">
          <div className="about-card">
            <div className="about-card-title">Detección de anomalías</div>
            <p>IsolationForest entrenado por cultivo para identificar municipios con combinaciones inusuales de variables climáticas, productivas y económicas.</p>
          </div>
          <div className="about-card">
            <div className="about-card-title">Predicción de rendimiento</div>
            <p>XGBoost y Red Neuronal que predicen el rendimiento esperado (toneladas/ha) usando 22 variables. Explicabilidad vía SHAP para entender qué factores disparan cada alerta.</p>
          </div>
          <div className="about-card">
            <div className="about-card-title">Asistente conversacional</div>
            <p>LLM vía OpenRouter que responde preguntas en lenguaje natural sobre el nivel de riesgo, componentes del IRA y recomendaciones de mitigación.</p>
          </div>
          <div className="about-card">
            <div className="about-card-title">Reportes ejecutivos</div>
            <p>IA generativa produce un reporte estructurado con análisis, desglose de componentes, predicción de rendimiento y recomendaciones, renderizado como página imprimible/PDF.</p>
          </div>
        </div>
      </section>

      <section className="about-section">
        <div className="about-section-header">
          <div className="about-section-icon" style={{ color: "var(--accent)", fontWeight: 700 }}>#</div>
          <h2>Fuentes de datos</h2>
        </div>
        <p>El proyecto integra 15 fuentes de datos abiertos del gobierno colombiano y organismos internacionales:</p>
        <div className="about-card" style={{ padding: "4px 24px" }}>
          <ul className="about-list">
            {dataSources.map(([cat, name, desc]) => (
              <li key={name}>
                <span className="about-tag">{cat}</span>
                <strong>{name}</strong> — {desc}
              </li>
            ))}
          </ul>
        </div>
      </section>

      <section className="about-section">
        <div className="about-section-header">
          <div className="about-section-icon" style={{ color: "var(--accent)", fontWeight: 700 }}>@</div>
          <h2>Arquitectura</h2>
        </div>
        <div className="about-arch">{[
          "┌──────────┐    ┌───────────────┐    ┌───────────┐    ┌──────────┐",
          "│ Fuentes  │───→│ data/raw/     │───→│ DuckDB    │───→│ FastAPI  │",
          "│ externas │    │ *.parquet     │    │ alerta.db │    │ :8000    │",
          "└──────────┘    └───────────────┘    └───────────┘    └────┬─────┘",
          "                                                             │    ",
          "                                                ┌────────────┴─────┐",
          "                                                │ Next.js :3000    │",
          "                                                │ (proxy /api/*)   │",
          "                                                └──────────────────┘",
        ].join("\n")}</div>
        <ul className="about-arch-list">
          {archSteps.map(([step, desc]) => (
            <li key={step}>
              <span className="about-arch-step">{step}</span>
              <span>{desc}</span>
            </li>
          ))}
        </ul>
      </section>

      <section className="about-section">
        <div className="about-section-header">
          <div className="about-section-icon" style={{ color: "var(--accent)", fontWeight: 700 }}>*</div>
          <h2>Tecnologías</h2>
        </div>
        <div className="about-card">
          <div className="about-tag-wrap">
            {["Python 3.14", "Next.js 15", "React 19", "DuckDB", "FastAPI", "Leaflet", "Scikit-learn", "XGBoost", "SHAP", "OpenRouter", "Docker", "GitHub Actions"].map((t) => (
              <span key={t} className="about-tag" style={{ color: "var(--text)", background: "var(--bg)", fontSize: "0.75rem", padding: "4px 12px" }}>{t}</span>
            ))}
          </div>
        </div>
      </section>
    </main>
  );
}
