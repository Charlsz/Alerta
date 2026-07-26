"use client";
import { useState, useEffect, useRef, useMemo } from "react";
import useAPI from "../hooks/useAPI";
import RiskBadge from "./RiskBadge";

function Bar({ value, label, color }) {
  const pct = Math.round((value ?? 0) * 100);
  return (
    <div className="bar-row">
      <span className="bar-label">{label}</span>
      <div className="bar-track">
        <div className="bar-fill" style={{ width: `${pct}%`, background: color || "var(--color-primary)" }} />
      </div>
      <span className="bar-value">{pct}%</span>
    </div>
  );
}

function getScoreColor(v) {
  if (v == null) return "#888";
  if (v >= 0.75) return "#ef4444";
  if (v >= 0.50) return "#f97316";
  if (v >= 0.25) return "#eab308";
  return "#22c55e";
}

function fmtHa(v) {
  if (v == null) return "—";
  return Number(v).toLocaleString("es-CO", { maximumFractionDigits: 0 }) + " ha";
}

function fmtTon(v) {
  if (v == null) return "—";
  return Number(v).toLocaleString("es-CO", { maximumFractionDigits: 1 }) + " t/ha";
}

export default function MunicipioCard({ codigo, cultivo, periodo }) {
  const hasPropSelection = !!(cultivo && periodo);

  // When props bring cultivo/periodo, filter server-side (efficient).
  // When no props, fetch all data for the municipio.
  const apiParams = new URLSearchParams();
  if (hasPropSelection) {
    apiParams.set("cultivo", cultivo);
    apiParams.set("periodo", periodo);
  }
  const { data, loading } = useAPI(codigo ? `/api/municipio/${codigo}?${apiParams}` : null);

  // Internal selection for overview mode
  const [focusCultivo, setFocusCultivo] = useState(null);
  const [focusPeriodo, setFocusPeriodo] = useState(null);

  // Effective selection: props > internal state
  const effectiveCultivo = hasPropSelection ? cultivo : focusCultivo;
  const effectivePeriodo = hasPropSelection ? periodo : focusPeriodo;
  const hasSelection = !!(effectiveCultivo && effectivePeriodo);

  const [messages, setMessages] = useState([]);
  const [question, setQuestion] = useState("");
  const [asking, setAsking] = useState(false);
  const [multiAgent, setMultiAgent] = useState(null);
  const [ndviData, setNdviData] = useState(null);
  const [deforData, setDeforData] = useState(null);
  const [loaded, setLoaded] = useState(false);
  const keyRef = useRef(null);

  // Reset internal selection when codigo changes
  useEffect(() => {
    if (!codigo) return;
    const k = `${codigo}-${cultivo}`;
    if (keyRef.current && keyRef.current !== k) {
      setMultiAgent(null); setNdviData(null); setDeforData(null); setMessages([]); setLoaded(false);
      setFocusCultivo(null); setFocusPeriodo(null);
    }
    keyRef.current = k;
    Promise.all([
      fetch(`/api/municipio/${codigo}/deforestacion`).then(r => r.json()).catch(() => null),
      fetch(`/api/municipio/${codigo}/ndvi`).then(r => r.json()).catch(() => null),
      fetch(`/api/municipio/${codigo}/multiagent?cultivo=${encodeURIComponent(effectiveCultivo || '')}&periodo=${encodeURIComponent(effectivePeriodo || '')}`).then(r => r.json()).catch(() => null),
    ]).then(([d, n, m]) => {
      setDeforData(d);
      setNdviData(n);
      setMultiAgent(m);
      setLoaded(true);
    });
  }, [codigo, cultivo]); // eslint-disable-line react-hooks/exhaustive-deps

  // Compute display row
  const displayRow = useMemo(() => {
    if (!data?.data?.length) return null;
    if (!hasSelection) return null;
    if (hasPropSelection) return data.data[0];
    return data.data.find(d => d.cultivo === effectiveCultivo && d.periodo === effectivePeriodo) || null;
  }, [data, hasSelection, hasPropSelection, effectiveCultivo, effectivePeriodo]);

  // For overview mode: latest row per cultivo, sorted by IRA desc
  const cultivoOptions = useMemo(() => {
    if (!data?.data) return [];
    const latest = {};
    for (const d of data.data) {
      const key = d.cultivo;
      if (!latest[key] || d.periodo > latest[key].periodo) {
        latest[key] = d;
      }
    }
    return Object.values(latest).sort((a, b) => (b.ira_score || 0) - (a.ira_score || 0));
  }, [data]);

  const totalCultivos = cultivoOptions.length;
  const nthCultivos = totalCultivos > 1 ? `${totalCultivos} cultivos` : "1 cultivo";

  const ask = async () => {
    const q = question.trim();
    if (!q || asking) return;
    setMessages((prev) => [...prev, { role: "user", text: q }]);
    setQuestion("");
    setAsking(true);
    try {
      const res = await fetch(`/api/municipio/${codigo}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: q, cultivo: effectiveCultivo, periodo: effectivePeriodo }),
      });
      const json = await res.json();
      setMessages((prev) => [...prev, { role: "assistant", text: json.answer || "Error al obtener respuesta." }]);
    } catch {
      setMessages((prev) => [...prev, { role: "assistant", text: "Error de conexión." }]);
    }
    setAsking(false);
  };

  // ── Estados vacíos ──────────────────────────────────────────────────────
  if (!codigo) return <p className="empty-state">Selecciona un municipio en el mapa o ranking.</p>;
  if (loading) return <p className="empty-state">Cargando...</p>;
  if (!data?.data?.length) return <p className="empty-state">Sin datos para este municipio.</p>;
  if (!hasSelection) {
    return (
      <div className="card">
        <div className="card-header">
          <h2 className="card-title">{data.data[0].nombre_municipio || codigo}</h2>
          <p className="card-subtitle">{data.data[0].nombre_departamento}</p>
        </div>

        <div className="context-banner">
          <span>Este municipio tiene <strong>{nthCultivos}</strong> con datos de IRA</span>
        </div>

        <div className="card-section">
          <h4 className="section-label">Selecciona un cultivo para ver sus indicadores</h4>
          <div className="cultivo-grid">
            {cultivoOptions.map((c) => (
              <button
                key={c.cultivo}
                className="cultivo-option"
                onClick={() => { setFocusCultivo(c.cultivo); setFocusPeriodo(c.periodo); }}
              >
                <span className="cultivo-option-name">{c.cultivo}</span>
                <RiskBadge nivel={c.ira_nivel} />
                <span className="cultivo-option-ira">IRA {c.ira_score?.toFixed(3)}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Reporte PDF */}
        <div style={{ marginTop: 12, textAlign: "right" }}>
          <a href={`/reporte/${codigo}`} target="_blank" className="btn btn--ghost" style={{ fontSize: "0.8125rem" }}>
            Reporte PDF completo →
          </a>
        </div>
      </div>
    );
  }

  if (!displayRow) return <p className="empty-state">Sin datos para el cultivo seleccionado.</p>;
  const r = displayRow;

  return (
    <div className="card">
      <div className="card-header">
        <h2 className="card-title">{r.nombre_municipio || r.codigo_municipio}</h2>
        <p className="card-subtitle">{r.nombre_departamento}</p>
      </div>

      {/* Context banner */}
      <div className="context-banner">
        <span>Mostrando datos de <strong>{r.cultivo}</strong></span>
        {totalCultivos > 1 && (
          <button className="context-banner-btn" onClick={() => { setFocusCultivo(null); setFocusPeriodo(null); }}>
            Ver todos los cultivos
          </button>
        )}
      </div>

      {/* IRA Score grande */}
      <div className="ira-hero">
        <RiskBadge nivel={r.ira_nivel} />
        <span className="ira-hero-score">IRA {r.ira_score?.toFixed(3)}</span>
      </div>

      {/* Barras de sub-índices */}
      <div className="bars-group">
        <h4 className="section-label">Componentes del riesgo</h4>
        <Bar value={r.spc} label="Clima (SPC)" color={getScoreColor(r.spc)} />
        <Bar value={r.sep} label="Cultivo (SEP)" color={getScoreColor(r.sep)} />
        <Bar value={r.sve} label="Pobreza (SVE)" color={getScoreColor(r.sve)} />
      </div>

      {/* Indicadores clave */}
      <div className="metrics-grid">
        <div className="metric-card">
          <span className="metric-value">{fmtTon(r.rendimiento_predicho)}</span>
          <span className="metric-label">Rendimiento esperado</span>
        </div>
        <div className="metric-card">
          <span className="metric-value">{r.anomaly_score != null ? r.anomaly_score.toFixed(2) : "—"}</span>
          <span className="metric-label">Anomalía</span>
        </div>
        <div className="metric-card">
          <span className="metric-value">{r.rendimiento_nnet != null ? fmtTon(r.rendimiento_nnet) : "—"}</span>
          <span className="metric-label">Red Neuronal</span>
        </div>
      </div>

      {/* Importancia top-3 variables */}
      {(() => {
        try {
          const top3 = typeof r.importancia_top3 === "string" ? JSON.parse(r.importancia_top3) : r.importancia_top3;
          if (!Array.isArray(top3) || top3.length === 0) return null;
          return (
            <div className="card-section">
              <h4 className="section-label">Variables más influyentes</h4>
              <div className="top3-grid">
                {top3.map((item, i) => (
                  <div key={i} className="top3-chip">
                    <span className="top3-rank">{i + 1}</span>
                    <span className="top3-var">{item.var}</span>
                    <span className="top3-shap">{item.shap?.toFixed(4)}</span>
                  </div>
                ))}
              </div>
            </div>
          );
        } catch {
          return null;
        }
      })()}

      {/* Deforestación */}
      {deforData?.data && !deforData?.error && (
        <div className="card-section">
          <h4 className="section-label">Pérdida de bosque</h4>
          <div className="metrics-grid">
            <div className="metric-card">
              <span className="metric-value">{
                (() => {
                  const e = Object.entries(deforData.data).find(([k]) => k.startsWith("deforestacion_") && !k.includes("total") && !k.includes("promedio") && !k.includes("tendencia"));
                  return e ? fmtHa(e[1]) : "—";
                })()
              }</span>
              <span className="metric-label">Último año</span>
            </div>
            <div className="metric-card">
              <span className="metric-value">{fmtHa(deforData.data.deforestacion_total_5y)}</span>
              <span className="metric-label">Últimos 5 años</span>
            </div>
            <div className="metric-card">
              <span className="metric-value">{fmtHa(deforData.data.deforestacion_total_10y)}</span>
              <span className="metric-label">Últimos 10 años</span>
            </div>
            <div className="metric-card">
              <span className="metric-value" style={{ fontSize: "0.75rem" }}>{deforData.data.deforestacion_tendencia_label || "—"}</span>
              <span className="metric-label">Tendencia</span>
            </div>
          </div>
        </div>
      )}

      {/* NDVI */}
      {ndviData?.data?.length > 0 && (
        <div className="card-section">
          <h4 className="section-label">Salud de la vegetación (NDVI satelital)</h4>
          <div className="metrics-grid">
            <div className="metric-card">
              <span className="metric-value">{ndviData.data[0].ndvi?.toFixed(3)}</span>
              <span className="metric-label">NDVI actual</span>
            </div>
            {ndviData.data[0].anomalia != null && (
              <div className="metric-card">
                <span className="metric-value" style={{ color: ndviData.data[0].anomalia < 0 ? "#ef4444" : "#22c55e" }}>
                  {ndviData.data[0].anomalia > 0 ? "+" : ""}{ndviData.data[0].anomalia.toFixed(1)}%
                </span>
                <span className="metric-label">vs. histórico</span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Análisis Multi-Agente */}
      {multiAgent?.agentes?.length > 0 && (
        <div className="card-section">
          <h4 className="section-label">Análisis Multi-Agente</h4>
          {multiAgent.agentes.map((a, i) => (
            <div key={i} className="agent-item">
              <strong>{a.agente}:</strong> <RiskBadge nivel={a.nivel} />
              {a.hallazgos?.length > 0 && <ul className="agent-hallazgos">{a.hallazgos.map((h, j) => <li key={j}>{h}</li>)}</ul>}
            </div>
          ))}
          {multiAgent.coordinador && (
            <div className="agent-coordinator">
              <strong>Conclusión ({multiAgent.coordinador.prioridad}):</strong> {multiAgent.coordinador.resumen}
            </div>
          )}
        </div>
      )}

      {loaded && !multiAgent?.agentes?.length && (
        <div className="card-section">
          <p className="empty-state" style={{ padding: 0, fontSize: "0.8125rem" }}>No hay suficientes datos para el análisis multi-agente de este municipio.</p>
        </div>
      )}

      {/* Reporte PDF */}
      <div style={{ marginTop: 12, textAlign: "right" }}>
        <a href={`/reporte/${codigo}?cultivo=${encodeURIComponent(r.cultivo)}&periodo=${encodeURIComponent(r.periodo)}`} target="_blank" className="btn btn--ghost" style={{ fontSize: "0.8125rem" }}>
          Reporte PDF ({r.cultivo}) →
        </a>
      </div>

      {/* Chat IA */}
      <div className="card-section">
        <h4 className="section-label">Asistente IA</h4>
        <p className="context-note">
          El asistente analiza específicamente el cultivo <strong>{r.cultivo}</strong>.
        </p>
        <div className="chat-messages">
          {messages.map((m, i) => (
            <div key={i} className={`chat-message chat-message--${m.role}`}>
              <strong>{m.role === "user" ? "Tú" : "Asistente"}:</strong> {m.text}
            </div>
          ))}
          {asking && <p className="empty-state" style={{ padding: "4px 0" }}>Pensando...</p>}
          {!messages.length && <p className="empty-state" style={{ padding: "4px 0", fontSize: "0.8125rem" }}>Pregunta sobre el riesgo, los indicadores o qué acciones tomar.</p>}
        </div>
        <div className="chat-input-group">
          <input
            className="chat-input"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && ask()}
            placeholder="¿Qué significa este nivel de riesgo?"
          />
          <button className="btn btn--primary" onClick={ask} disabled={asking || !question.trim()}>
            {asking ? "..." : "Enviar"}
          </button>
        </div>
      </div>
    </div>
  );
}
