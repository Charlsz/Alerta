"use client";
import { use, useEffect, useState } from "react";
import RiskBadge from "@/app/components/RiskBadge";

export default function ReportePage({ params }) {
  const { codigo } = use(params);
  const [data, setData] = useState(null);
  const [reporte, setReporte] = useState("");
  const [defor, setDefor] = useState(null);
  const [ndvi, setNdvi] = useState(null);
  const [multiAgent, setMultiAgent] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!codigo) return;
    // fetch data + LLM report in parallel
    Promise.all([
      fetch(`/api/municipio/${codigo}`).then((r) => r.json()),
      fetch(`/api/municipio/${codigo}/deforestacion`).then((r) => r.json()),
      fetch(`/api/municipio/${codigo}/ndvi`).then((r) => r.json()),
      fetch(`/api/municipio/${codigo}/multiagent`).then((r) => r.json()),
      fetch(`/api/municipio/${codigo}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: "Responde directo, sin explicar tu razonamiento. Analiza el riesgo agrícola de este municipio en lenguaje simple para un agricultor. Sin guiones, asteriscos, viñetas ni caracteres especiales. Solo 1 o 2 párrafos de texto plano. Incluye: nivel de riesgo actual, componentes mas preocupantes (SPC, SEP o SVE), rendimiento esperado del cultivo, y 1 o 2 recomendaciones practicas. Maximo 150 palabras. REGLA IMPORTANTE: No expliques tu razonamiento ni muestres tu proceso de análisis. Responde ÚNICAMENTE el texto final del análisis, sin prefacios, sin introducciones como 'El usuario quiere...', sin 'Basado en los datos...'. Empieza directamente con la respuesta.",
        }),
      }).then((r) => r.json()),
    ]).then(([d, df, n, m, r]) => {
      setData(d);
      setDefor(df?.data || null);
      setNdvi(n || null);
      setMultiAgent(m?.agentes ? m : null);
      setReporte(r.answer || "");
    }).finally(() => setLoading(false));
  }, [codigo]);

  if (loading) return <div className="empty-state" style={{ textAlign: "center", padding: 40 }}>Generando reporte...</div>;
  if (!data?.data?.length) return <div className="empty-state" style={{ padding: 40 }}>Sin datos para este municipio.</div>;

  const r = data.data.find((item) => item.rendimiento_predicho != null) || data.data[0];
  const nivel = r.ira_nivel;
  const borderColor = nivel === "Crítico" ? "var(--color-critico)" : nivel === "Alto" ? "var(--color-alto)" : nivel === "Medio" ? "var(--color-medio)" : "var(--color-bajo)";

  return (
    <div className="report-page">
      <div className="report-toolbar no-print">
        <button className="btn btn--primary" onClick={() => window.print()}>Imprimir / Guardar PDF</button>
        {" "}
        <button className="btn btn--ghost" onClick={() => window.close()}>Cerrar</button>
      </div>

      <div className="report-header" style={{ borderBottomColor: borderColor }}>
        <div>
          <h1>Reporte de Riesgo Agrícola</h1>
          <p className="report-meta">{r.nombre_municipio}, {r.nombre_departamento} — {r.cultivo}</p>
        </div>
        <div className="report-ira"><RiskBadge nivel={nivel} /> IRA: {r.ira_score?.toFixed(3)}</div>
      </div>

      <div className="report-grid">
        <div className="report-card">
          <h3>SPC — Peligro Climático</h3>
          <div className="value">{r.spc?.toFixed(3)}</div>
          <div className="sub">Peso: 50%</div>
        </div>
        <div className="report-card">
          <h3>SEP — Exposición Productiva</h3>
          <div className="value">{r.sep?.toFixed(3)}</div>
          <div className="sub">Peso: 30%</div>
        </div>
        <div className="report-card">
          <h3>SVE — Vulnerabilidad Económica</h3>
          <div className="value">{r.sve?.toFixed(3)}</div>
          <div className="sub">Peso: 20%</div>
        </div>
        <div className="report-card">
          <h3>Rendimiento (XGBoost)</h3>
          <div className="value">{r.rendimiento_predicho != null ? `${r.rendimiento_predicho} toneladas/ha` : "—"}</div>
          <div className="sub">{r.rendimiento_ic_inf != null ? `Intervalo de Confianza 95%: [${r.rendimiento_ic_inf.toFixed(1)} – ${r.rendimiento_ic_sup.toFixed(1)}]` : ""}</div>
        </div>
        <div className="report-card">
          <h3>Rendimiento (Red Neuronal)</h3>
          <div className="value">{r.rendimiento_nnet != null ? `${r.rendimiento_nnet} toneladas/ha` : "—"}</div>
          <div className="sub">{r.nnet_ic_inf != null ? `Intervalo de Confianza 95%: [${r.nnet_ic_inf.toFixed(1)} – ${r.nnet_ic_sup.toFixed(1)}]` : ""}</div>
        </div>
      </div>

      <table className="report-table">
        <thead>
          <tr><th>Indicador</th><th>Valor</th><th>Interpretación</th></tr>
        </thead>
        <tbody>
          <tr><td>Anomalía</td><td>{r.anomaly_score != null ? r.anomaly_score.toFixed(2) : "—"}</td><td>{r.is_anomaly ? "Atípico respecto al historial" : "Dentro del rango esperado"}</td></tr>
          <tr><td>Período</td><td>{r.periodo}</td><td>Trimestre de análisis</td></tr>
        </tbody>
      </table>

      {defor && (
        <div className="report-grid">
          <div className="report-card">
            <h3>Pérdida de Bosque 2025</h3>
            <div className="value">{defor.deforestacion_2025?.toFixed(0)} hectáreas</div>
            <div className="sub">Deforestación en el año más reciente</div>
          </div>
          <div className="report-card">
            <h3>Pérdida Total (5 años)</h3>
            <div className="value">{defor.deforestacion_total_5y?.toFixed(0)} hectáreas</div>
            <div className="sub">Acumulado 2021–2025</div>
          </div>
          <div className="report-card">
            <h3>Pérdida Total (10 años)</h3>
            <div className="value">{defor.deforestacion_total_10y?.toFixed(0)} hectáreas</div>
            <div className="sub">Acumulado 2016–2025</div>
          </div>
          <div className="report-card">
            <h3>Tendencia</h3>
            <div className="value">{defor.deforestacion_tendencia_label}</div>
            <div className="sub">Basada en datos GFW/Hansen 2001–2025</div>
          </div>
        </div>
      )}

      {ndvi?.data?.length > 0 && (
        <div className="report-card" style={{ marginBottom: "var(--space-xl)" }}>
          <h3>Salud de la Vegetación (NDVI — Índice de Vegetación Satelital)</h3>
          <p style={{ marginTop: 4 }}>Último NDVI: <strong>{ndvi.data[0].ndvi?.toFixed(3)}</strong> ({ndvi.data[0].periodo})</p>
          {ndvi.data[0].anomalia != null && (
            <p>Anomalía de vegetación: <strong>{ndvi.data[0].anomalia.toFixed(1)}%</strong></p>
          )}
          <p className="sub" style={{ marginTop: 8 }}>Vegetación más débil de lo normal sugiere posible estrés de cultivos. Fuente: MODIS (Terra/Aqua).</p>
        </div>
      )}

      {multiAgent?.agentes && (
        <div style={{ marginBottom: "var(--space-xl)" }}>
          <h3 className="report-section-title">Análisis Multi-Agente</h3>
          <div className="report-grid">
            {multiAgent.agentes.map((a, i) => (
              <div key={i} className="report-card" style={{ fontSize: "0.8125rem" }}>
                <strong>{a.agente}:</strong> nivel <em>{a.nivel}</em>
                {a.hallazgos?.length > 0 && (
                  <ul style={{ margin: "6px 0", paddingLeft: 16, fontSize: "0.75rem", color: "var(--color-text-secondary)" }}>
                    {a.hallazgos.map((h, j) => <li key={j}>{h}</li>)}
                  </ul>
                )}
              </div>
            ))}
          </div>
          {multiAgent.coordinador && (
            <div className="agent-coordinator">
              <strong>Coordinador ({multiAgent.coordinador.prioridad}):</strong> {multiAgent.coordinador.resumen}
            </div>
          )}
        </div>
      )}

      <h3 className="report-section-title">Análisis Generado por IA</h3>
      <div className="report-text">{reporte}</div>

      <div className="report-footer">
        <p>Alerta — Plataforma de Alerta Temprana para Riesgo Climático Agrícola en Colombia</p>
        <p>Generado el {new Date().toLocaleDateString("es-CO")} | Datos: IDEAM, DANE, UPRA, IGAC</p>
      </div>
    </div>
  );
}
