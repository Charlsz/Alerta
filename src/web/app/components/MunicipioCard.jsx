"use client";
import { useState, useEffect, useRef } from "react";
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
  const params = new URLSearchParams();
  if (cultivo) params.set("cultivo", cultivo);
  if (periodo) params.set("periodo", periodo);
  const { data, loading } = useAPI(codigo ? `/api/municipio/${codigo}?${params}` : null);
  const [messages, setMessages] = useState([]);
  const [question, setQuestion] = useState("");
  const [asking, setAsking] = useState(false);
  const [multiAgent, setMultiAgent] = useState(null);
  const [ndviData, setNdviData] = useState(null);
  const [deforData, setDeforData] = useState(null);
  const [loaded, setLoaded] = useState(false);
  const keyRef = useRef(null);

  const key = `${codigo}-${cultivo}`;

  // Auto-load NDVI, deforestation, multi-agent on mount/change
  useEffect(() => {
    if (!codigo) return;
    const k = `${codigo}-${cultivo}`;
    if (keyRef.current && keyRef.current !== k) {
      setMultiAgent(null); setNdviData(null); setDeforData(null); setMessages([]); setLoaded(false);
    }
    keyRef.current = k;
    Promise.all([
      fetch(`/api/municipio/${codigo}/deforestacion`).then(r => r.json()).catch(() => null),
      fetch(`/api/municipio/${codigo}/ndvi`).then(r => r.json()).catch(() => null),
      fetch(`/api/municipio/${codigo}/multiagent`).then(r => r.json()).catch(() => null),
    ]).then(([d, n, m]) => {
      setDeforData(d);
      setNdviData(n);
      setMultiAgent(m);
      setLoaded(true);
    });
  }, [codigo, cultivo]);

  if (!codigo) return <p className="empty-state">Selecciona un municipio en el mapa o ranking.</p>;
  if (loading) return <p className="empty-state">Cargando...</p>;
  if (!data?.data?.length) return <p className="empty-state">Sin datos para este municipio.</p>;

  const r = data.data[0];

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
        body: JSON.stringify({ question: q, cultivo, periodo }),
      });
      const json = await res.json();
      setMessages((prev) => [...prev, { role: "assistant", text: json.answer || "Error al obtener respuesta." }]);
    } catch {
      setMessages((prev) => [...prev, { role: "assistant", text: "Error de conexión." }]);
    }
    setAsking(false);
  };

  return (
    <div className="card">
      <div className="card-header">
        <h2 className="card-title">{r.nombre_municipio || r.codigo_municipio}</h2>
        <p className="card-subtitle">{r.nombre_departamento} — {r.cultivo}</p>
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
          Reporte PDF completo →
        </a>
      </div>

      {/* Chat IA */}
      <div className="card-section">
        <h4 className="section-label">Asistente IA</h4>
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
