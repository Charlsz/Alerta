"use client";
import { useState } from "react";
import useAPI from "../hooks/useAPI";
import RiskBadge from "./RiskBadge";

export default function MunicipioCard({ codigo, cultivo }) {
  const params = new URLSearchParams();
  if (cultivo) params.set("cultivo", cultivo);
  const { data, loading } = useAPI(codigo ? `/api/municipio/${codigo}?${params}` : null);
  const [messages, setMessages] = useState([]);
  const [question, setQuestion] = useState("");
  const [asking, setAsking] = useState(false);
  const [multiAgent, setMultiAgent] = useState(null);
  const [loadingAgent, setLoadingAgent] = useState(false);
  const [ndviData, setNdviData] = useState(null);
  const [loadingNdvi, setLoadingNdvi] = useState(false);
  const [deforData, setDeforData] = useState(null);
  const [loadingDefor, setLoadingDefor] = useState(false);

  const loadDefor = async () => {
    if (loadingDefor) return;
    setLoadingDefor(true);
    try {
      const res = await fetch(`/api/municipio/${codigo}/deforestacion`);
      setDeforData(await res.json());
    } catch { setDeforData(null); }
    setLoadingDefor(false);
  };

  const loadNdvi = async () => {
    if (loadingNdvi) return;
    setLoadingNdvi(true);
    try {
      const res = await fetch(`/api/municipio/${codigo}/ndvi`);
      setNdviData(await res.json());
    } catch { setNdviData(null); }
    setLoadingNdvi(false);
  };

  const loadMultiAgent = async () => {
    if (loadingAgent) return;
    setLoadingAgent(true);
    try {
      const res = await fetch(`/api/municipio/${codigo}/multiagent`);
      setMultiAgent(await res.json());
    } catch { setMultiAgent(null); }
    setLoadingAgent(false);
  };

  if (!codigo) return <p className="empty-state">Selecciona un municipio en el mapa o ranking.</p>;
  if (loading) return <p className="empty-state">Cargando...</p>;
  if (!data?.data?.length) return <p className="empty-state">Sin datos para este municipio.</p>;

  const r = data.data.find((item) => item.rendimiento_predicho != null) || data.data[0];

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
        body: JSON.stringify({ question: q }),
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
        <p style={{ marginTop: 8 }}><RiskBadge nivel={r.ira_nivel} /> IRA: {r.ira_score?.toFixed(3)}</p>
      </div>

      <table className="detail-table">
        <tbody>
          <tr><td>SPC (Peligro)</td><td>{r.spc?.toFixed(3)}</td></tr>
          <tr><td>SEP (Exposición)</td><td>{r.sep?.toFixed(3)}</td></tr>
          <tr><td>SVE (Vulnerabilidad)</td><td>{r.sve?.toFixed(3)}</td></tr>
          <tr><td>Anomalía</td><td>{r.anomaly_score != null ? r.anomaly_score.toFixed(2) : "—"}</td></tr>
<tr><td>Rendimiento (XGBoost)</td><td>{r.rendimiento_predicho != null ? `${r.rendimiento_predicho} toneladas/ha` : "—"}</td></tr>
<tr><td>Rendimiento (Red Neuronal)</td><td>{r.rendimiento_nnet != null ? `${r.rendimiento_nnet} toneladas/ha` : "—"}</td></tr>
        </tbody>
      </table>

      <div style={{ marginTop: 8, textAlign: "right" }}>
        <a href={`/reporte/${codigo}`} target="_blank" style={{ fontSize: "0.8125rem" }}>
          Reporte PDF completo →
        </a>
      </div>

      <div className="card-section">
        <p className="card-section-title">Análisis Multi-Agente</p>
        {!multiAgent && !loadingAgent && (
          <button className="btn btn--ghost" onClick={loadMultiAgent} style={{ fontSize: "0.8125rem" }}>
            Cargar análisis
          </button>
        )}
        {loadingAgent && <p className="empty-state" style={{ padding: 0 }}>Analizando...</p>}
        {multiAgent?.agentes?.map((a, i) => (
          <div key={i} className="agent-item">
            <strong>{a.agente}:</strong> nivel <em>{a.nivel}</em>
            {a.hallazgos?.length > 0 && <ul>{a.hallazgos.map((h, j) => <li key={j}>{h}</li>)}</ul>}
          </div>
        ))}
        {multiAgent?.coordinador && (
          <div className="agent-coordinator">
            <strong>Coordinador ({multiAgent.coordinador.prioridad}):</strong> {multiAgent.coordinador.resumen}
          </div>
        )}
      </div>

      <div className="card-section">
        <p className="card-section-title">NDVI (Índice de Vegetación) Satelital — MODIS</p>
        {!ndviData && !loadingNdvi && (
          <button className="btn btn--ghost" onClick={loadNdvi} style={{ fontSize: "0.8125rem" }}>
            Cargar NDVI
          </button>
        )}
        {loadingNdvi && <p className="empty-state" style={{ padding: 0 }}>Cargando...</p>}
        {ndviData?.data?.length > 0 && (
          <div style={{ fontSize: "0.8125rem" }}>
            <p>Último NDVI: <strong>{ndviData.data[0].ndvi?.toFixed(3)}</strong> ({ndviData.data[0].periodo})
              {ndviData.data[0].anomalia != null && (
                <span> — Anomalía: <strong>{ndviData.data[0].anomalia.toFixed(1)}%</strong></span>
              )}
            </p>
            <p style={{ color: "var(--color-text-tertiary)", marginTop: 2 }}>Datos del satélite Terra/Aqua (MODIS), agregados por municipio</p>
          </div>
        )}
      </div>

      <div className="card-section">
        <p className="card-section-title">Deforestación (GFW/Hansen)</p>
        {!deforData && !loadingDefor && (
          <button className="btn btn--ghost" onClick={loadDefor} style={{ fontSize: "0.8125rem" }}>
            Cargar datos
          </button>
        )}
        {loadingDefor && <p className="empty-state" style={{ padding: 0 }}>Cargando...</p>}
        {deforData?.data && (
          <div style={{ fontSize: "0.8125rem" }}>
            <p>Pérdida bosque 2025: <strong>{deforData.data.deforestacion_2025?.toFixed(0)} hectáreas</strong></p>
            <p>Total últimos 5 años: <strong>{deforData.data.deforestacion_total_5y?.toFixed(0)} hectáreas</strong></p>
            <p>Total últimos 10 años: <strong>{deforData.data.deforestacion_total_10y?.toFixed(0)} hectáreas</strong></p>
            <p>Tendencia: <strong>{deforData.data.deforestacion_tendencia_label}</strong></p>
            <p style={{ color: "var(--color-text-tertiary)", marginTop: 2 }}>Fuente: Global Forest Watch (Hansen/UMD)</p>
          </div>
        )}
      </div>

      <div className="card-section">
        <p className="card-section-title">Asistente IA</p>
        <div className="chat-messages">
          {messages.map((m, i) => (
            <div key={i} className={`chat-message chat-message--${m.role}`}>
              <strong>{m.role === "user" ? "Tú" : "Asistente"}:</strong> {m.text}
            </div>
          ))}
          {asking && <p className="empty-state" style={{ padding: "4px 0" }}>Pensando...</p>}
          {!messages.length && <p className="empty-state" style={{ padding: "4px 0" }}>Pregunta sobre el riesgo, los indicadores o acciones recomendadas.</p>}
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
