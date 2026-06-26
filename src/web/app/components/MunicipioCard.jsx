"use client";
import { useState } from "react";
import useAPI from "../hooks/useAPI";
import RiskBadge from "./RiskBadge";

export default function MunicipioCard({ codigo }) {
  const { data, loading } = useAPI(codigo ? `/api/municipio/${codigo}` : null);
  const [messages, setMessages] = useState([]);
  const [question, setQuestion] = useState("");
  const [asking, setAsking] = useState(false);

  if (!codigo) return <p>Selecciona un municipio en el mapa o ranking.</p>;
  if (loading) return <p>Cargando...</p>;
  if (!data?.data?.length) return <p>Sin datos para este municipio.</p>;

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
    <div style={{ border: "1px solid #ddd", borderRadius: 8, padding: 16, marginTop: 16 }}>
      <h2>{r.nombre_municipio || r.codigo_municipio}</h2>
      <p>{r.nombre_departamento} — {r.cultivo}</p>
      <p><RiskBadge nivel={r.ira_nivel} /> IRA: {r.ira_score?.toFixed(3)}</p>
      <table style={{ fontSize: 13, marginTop: 8 }}>
        <tbody>
          <tr><td>SPC (Peligro)</td><td>{r.spc?.toFixed(3)}</td></tr>
          <tr><td>SEP (Exposición)</td><td>{r.sep?.toFixed(3)}</td></tr>
          <tr><td>SVE (Vulnerabilidad)</td><td>{r.sve?.toFixed(3)}</td></tr>
          <tr><td>Anomalía</td><td>{r.anomaly_score != null ? r.anomaly_score.toFixed(2) : "—"}</td></tr>
          <tr><td>Rendimiento predicho (XGBoost)</td><td>{r.rendimiento_predicho != null ? `${r.rendimiento_predicho} t/ha` : "—"}</td></tr>
          <tr><td>Rendimiento predicho (Red Neuronal)</td><td>{r.rendimiento_nnet != null ? `${r.rendimiento_nnet} t/ha` : "—"}</td></tr>
        </tbody>
      </table>

      <div style={{ marginTop: 8, textAlign: "right" }}>
        <a href={`/reporte/${codigo}`} target="_blank" style={{ fontSize: 12, color: "#007bff", textDecoration: "none" }}>
          Reporte PDF completo →
        </a>
      </div>

      <div style={{ marginTop: 8, borderTop: "1px solid #eee", paddingTop: 12 }}>
        <p style={{ fontWeight: 600, marginBottom: 8, fontSize: 14 }}>Asistente IA</p>
        <div style={{ maxHeight: 200, overflowY: "auto", fontSize: 13, marginBottom: 8 }}>
          {messages.map((m, i) => (
            <div key={i} style={{ marginBottom: 6, padding: "4px 8px", background: m.role === "user" ? "#f0f7ff" : "#f9f9f9", borderRadius: 6 }}>
              <strong>{m.role === "user" ? "Tú" : "Asistente"}:</strong> {m.text}
            </div>
          ))}
          {asking && <p style={{ color: "#999", fontSize: 12 }}>Pensando...</p>}
          {!messages.length && <p style={{ color: "#999", fontSize: 12 }}>Pregunta sobre el riesgo, los indicadores o acciones recomendadas.</p>}
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && ask()}
            placeholder="¿Qué significa este nivel de riesgo?"
            style={{ flex: 1, padding: "6px 10px", fontSize: 13, border: "1px solid #ccc", borderRadius: 4 }}
          />
          <button onClick={ask} disabled={asking || !question.trim()} style={{ padding: "6px 14px", fontSize: 13, borderRadius: 4, border: "1px solid #888", cursor: "pointer" }}>
            {asking ? "..." : "Enviar"}
          </button>
        </div>
      </div>
    </div>
  );
}
