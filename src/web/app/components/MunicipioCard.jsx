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
  if (v == null) return "\u2014";
  return Number(v).toLocaleString("es-CO", { maximumFractionDigits: 0 }) + " ha";
}

function fmtTon(v) {
  if (v == null) return "\u2014";
  return Number(v).toLocaleString("es-CO", { maximumFractionDigits: 1 }) + " t/ha";
}

export default function MunicipioCard({ codigo, cultivo: propCultivo, periodo: propPeriodo }) {
  // Always fetch all data for the municipio
  const { data, loading } = useAPI(codigo ? `/api/municipio/${codigo}` : null);

  // Internal selection state
  const [focusCultivo, setFocusCultivo] = useState(null);
  const [focusPeriodo, setFocusPeriodo] = useState(null);

  // Effective selection: prop > internal > first available
  const effectiveCultivo = focusCultivo || propCultivo;
  const effectivePeriodo = focusPeriodo || propPeriodo;

  const [messages, setMessages] = useState([]);
  const [question, setQuestion] = useState("");
  const [asking, setAsking] = useState(false);
  const [multiAgent, setMultiAgent] = useState(null);
  const [ndviData, setNdviData] = useState(null);
  const [deforData, setDeforData] = useState(null);
  const [loaded, setLoaded] = useState(false);
  const keyRef = useRef(null);

  // Compute: latest row per cultivo, sorted by IRA desc
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

  // Current selected cultivo (resolved name), fallback to first available
  const selectedCultivo = effectiveCultivo || cultivoOptions[0]?.cultivo || null;
  const selectedPeriodo = effectivePeriodo || cultivoOptions.find(c => c.cultivo === selectedCultivo)?.periodo || null;

  // All periods for the selected cultivo, sorted descending
  const periodOptions = useMemo(() => {
    if (!data?.data || !selectedCultivo) return [];
    return data.data
      .filter(d => d.cultivo === selectedCultivo)
      .sort((a, b) => (a.periodo < b.periodo ? 1 : -1));
  }, [data, selectedCultivo]);

  // Display row (latest period of selected cultivo, or a specific one)
  const displayRow = selectedPeriodo
    ? periodOptions.find(d => d.periodo === selectedPeriodo) || periodOptions[0]
    : periodOptions[0];

  // Auto-load NDVI, deforestation, multi-agent on mount/change
  useEffect(() => {
    if (!codigo) return;
    const k = `${codigo}-${selectedCultivo || ""}`;
    if (keyRef.current && keyRef.current !== k) {
      setMultiAgent(null); setNdviData(null); setDeforData(null); setMessages([]); setLoaded(false);
    }
    keyRef.current = k;
    Promise.all([
      fetch(`/api/municipio/${codigo}/deforestacion`).then(r => r.json()).catch(() => null),
      fetch(`/api/municipio/${codigo}/ndvi`).then(r => r.json()).catch(() => null),
      fetch(`/api/municipio/${codigo}/multiagent?cultivo=${encodeURIComponent(selectedCultivo || "")}&periodo=${encodeURIComponent(selectedPeriodo || "")}`).then(r => r.json()).catch(() => null),
    ]).then(([d, n, m]) => {
      setDeforData(d);
      setNdviData(n);
      setMultiAgent(m);
      setLoaded(true);
    });
  }, [codigo, selectedCultivo, selectedPeriodo]);

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
        body: JSON.stringify({ question: q, cultivo: selectedCultivo, periodo: selectedPeriodo }),
      });
      const json = await res.json();
      setMessages((prev) => [...prev, { role: "assistant", text: json.answer || "Error al obtener respuesta." }]);
    } catch {
      setMessages((prev) => [...prev, { role: "assistant", text: "Error de conexión." }]);
    }
    setAsking(false);
  };

  // ── Empty / Loading states ───────────────────────────────────────────────
  if (!codigo) return <p className="empty-state">Selecciona un municipio en el mapa o ranking.</p>;
  if (loading) return <p className="empty-state">Cargando...</p>;
  if (!data?.data?.length) return <p className="empty-state">Sin datos para este municipio.</p>;
  if (!cultivoOptions.length) return <p className="empty-state">Sin datos de cultivos para este municipio.</p>;

  // Resolve nombre/departamento from any row
  const firstRow = data.data[0];
  const r = displayRow;

  return (
    <div className="card">
      <div className="card-header">
        <h2 className="card-title">{firstRow.nombre_municipio || codigo}</h2>
        <p className="card-subtitle">{firstRow.nombre_departamento}</p>
      </div>

      {/* Cultivo tabs */}
      {cultivoOptions.length > 1 && (
        <div className="cultivo-tabs">
          {cultivoOptions.map(c => (
            <button
              key={c.cultivo}
              className={`cultivo-tab ${c.cultivo === selectedCultivo ? "cultivo-tab--active" : ""}`}
              onClick={() => { setFocusCultivo(c.cultivo); setFocusPeriodo(c.periodo); setMessages([]); }}
            >
              <span className="cultivo-tab-name">{c.cultivo}</span>
              <RiskBadge nivel={c.ira_nivel} />
            </button>
          ))}
        </div>
      )}

      {/* Selection info */}
      {r && (
        <div className="context-banner">
          <span>Mostrando <strong>{r.cultivo}</strong> — último período ({String(r.periodo).slice(0, 7)})</span>
        </div>
      )}

      {/* IRA Score */}
      {r && (
        <>
          <div className="ira-hero">
            <RiskBadge nivel={r.ira_nivel} />
            <span className="ira-hero-score">IRA {r.ira_score?.toFixed(3)}</span>
          </div>

          {/* Sub-index bars */}
          <div className="bars-group">
            <h4 className="section-label">Componentes del riesgo</h4>
            <Bar value={r.spc} label="Clima (SPC)" color={getScoreColor(r.spc)} />
            <Bar value={r.sep} label="Cultivo (SEP)" color={getScoreColor(r.sep)} />
            <Bar value={r.sve} label="Pobreza (SVE)" color={getScoreColor(r.sve)} />
          </div>

          {/* Key indicators */}
          <div className="metrics-grid">
            <div className="metric-card">
              <span className="metric-value">{fmtTon(r.rendimiento_predicho)}</span>
              <span className="metric-label">Rendimiento esperado</span>
            </div>
            <div className="metric-card">
              <span className="metric-value">{r.anomaly_score != null ? r.anomaly_score.toFixed(2) : "\u2014"}</span>
              <span className="metric-label">Anomalía</span>
            </div>
            <div className="metric-card">
              <span className="metric-value">{r.rendimiento_nnet != null ? fmtTon(r.rendimiento_nnet) : "\u2014"}</span>
              <span className="metric-label">Red Neuronal</span>
            </div>
          </div>

          {/* Top-3 features */}
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
        </>
      )}

      {/* Deforestation */}
      {deforData?.data && !deforData?.error && (
        <div className="card-section">
          <h4 className="section-label">Pérdida de bosque</h4>
          <div className="metrics-grid">
            <div className="metric-card">
              <span className="metric-value">{
                (() => {
                  const e = Object.entries(deforData.data).find(([k]) => k.startsWith("deforestacion_") && !k.includes("total") && !k.includes("promedio") && !k.includes("tendencia"));
                  return e ? fmtHa(e[1]) : "\u2014";
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
              <span className="metric-value" style={{ fontSize: "0.75rem" }}>{deforData.data.deforestacion_tendencia_label || "\u2014"}</span>
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

      {/* Multi-Agent */}
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
      {r && (
        <div style={{ marginTop: 12, textAlign: "right" }}>
          <a href={`/reporte/${codigo}?cultivo=${encodeURIComponent(r.cultivo)}&periodo=${encodeURIComponent(r.periodo)}`} target="_blank" className="btn btn--ghost" style={{ fontSize: "0.8125rem" }}>
            Reporte PDF ({r.cultivo}) →
          </a>
        </div>
      )}

      {/* Chat IA */}
      <div className="card-section">
        <h4 className="section-label">Asistente IA</h4>
        {r && <p className="context-note">El asistente analiza específicamente el cultivo <strong>{r.cultivo}</strong>.</p>}
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
