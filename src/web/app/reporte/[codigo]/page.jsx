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
          question: "Genera un reporte ejecutivo de riesgo agrícola para este municipio. Incluye: resumen del nivel de riesgo, desglose de los 3 componentes (SPC, SEP, SVE), predicción de rendimiento vs. promedio histórico, y 3 recomendaciones de mitigación concretas. Usa formato claro con viñetas. Máximo 400 palabras.",
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

  if (loading) return <div style={{ padding: 40, textAlign: "center" }}>Generando reporte...</div>;
  if (!data?.data?.length) return <div style={{ padding: 40 }}>Sin datos para este municipio.</div>;

  const r = data.data[0];
  const nivel = r.ira_nivel;
  const color = nivel === "Crítico" ? "#dc3545" : nivel === "Alto" ? "#fd7e14" : nivel === "Medio" ? "#ffc107" : "#28a745";

  return (
    <html>
      <head>
        <style>{`
          * { box-sizing: border-box; margin: 0; padding: 0; }
          body { font-family: system-ui, sans-serif; padding: 40px; color: #222; line-height: 1.5; }
          .header { display: flex; justify-content: space-between; align-items: center; border-bottom: 3px solid ${color}; padding-bottom: 16px; margin-bottom: 24px; }
          .header h1 { font-size: 24px; }
          .header .nivel { font-size: 18px; font-weight: bold; color: ${color}; }
          .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-bottom: 24px; }
          .card { border: 1px solid #ddd; border-radius: 8px; padding: 16px; }
          .card h3 { font-size: 14px; color: #666; margin-bottom: 8px; text-transform: uppercase; }
          .card .valor { font-size: 28px; font-weight: bold; }
          .card .sub { font-size: 12px; color: #999; }
          table { width: 100%; border-collapse: collapse; margin-bottom: 24px; }
          th, td { padding: 8px 12px; text-align: left; border-bottom: 1px solid #eee; font-size: 14px; }
          th { background: #f5f5f5; font-weight: 600; }
          .reporte-texto { background: #fafafa; border: 1px solid #eee; border-radius: 8px; padding: 20px; margin-bottom: 24px; white-space: pre-wrap; font-size: 14px; line-height: 1.6; }
          .acciones { margin-top: 16px; }
          .btn-imprimir { padding: 10px 24px; font-size: 14px; background: #007bff; color: #fff; border: none; border-radius: 6px; cursor: pointer; }
          .btn-imprimir:hover { background: #0056b3; }
          .footer { border-top: 1px solid #ddd; padding-top: 16px; font-size: 12px; color: #999; text-align: center; }
          @media print {
            body { padding: 20px; }
            .no-print { display: none !important; }
            .card { break-inside: avoid; }
          }
        `}</style>
      </head>
      <body>
        <div className="no-print" style={{ marginBottom: 16 }}>
          <button className="btn-imprimir" onClick={() => window.print()}>Imprimir / Guardar PDF</button>
          {" "}
          <button className="btn-imprimir" style={{ background: "#6c757d" }} onClick={() => window.close()}>Cerrar</button>
        </div>

        <div className="header">
          <div>
            <h1>Reporte de Riesgo Agrícola</h1>
            <p>{r.nombre_municipio}, {r.nombre_departamento} — {r.cultivo}</p>
          </div>
          <div className="nivel"><RiskBadge nivel={nivel} /> IRA: {r.ira_score?.toFixed(3)}</div>
        </div>

        <div className="grid">
          <div className="card">
            <h3>SPC — Peligro Climático</h3>
            <div className="valor">{r.spc?.toFixed(3)}</div>
            <div className="sub">Peso: 50%</div>
          </div>
          <div className="card">
            <h3>SEP — Exposición Productiva</h3>
            <div className="valor">{r.sep?.toFixed(3)}</div>
            <div className="sub">Peso: 30%</div>
          </div>
          <div className="card">
            <h3>SVE — Vulnerabilidad Económica</h3>
            <div className="valor">{r.sve?.toFixed(3)}</div>
            <div className="sub">Peso: 20%</div>
          </div>
          <div className="card">
            <h3>Rendimiento Predicho (XGBoost)</h3>
            <div className="valor">{r.rendimiento_predicho != null ? `${r.rendimiento_predicho} t/ha` : "—"}</div>
            <div className="sub">{r.rendimiento_ic_inf != null ? `IC 95%: [${r.rendimiento_ic_inf.toFixed(1)} – ${r.rendimiento_ic_sup.toFixed(1)}]` : ""}</div>
          </div>
          <div className="card">
            <h3>Rendimiento Predicho (Red Neuronal)</h3>
            <div className="valor">{r.rendimiento_nnet != null ? `${r.rendimiento_nnet} t/ha` : "—"}</div>
            <div className="sub">{r.nnet_ic_inf != null ? `IC 95%: [${r.nnet_ic_inf.toFixed(1)} – ${r.nnet_ic_sup.toFixed(1)}]` : ""}</div>
          </div>
        </div>

        <table>
          <thead>
            <tr><th>Indicador</th><th>Valor</th><th>Interpretación</th></tr>
          </thead>
          <tbody>
            <tr><td>Anomalía</td><td>{r.anomaly_score != null ? r.anomaly_score.toFixed(2) : "—"}</td><td>{r.is_anomaly ? "Atípico respecto al historial" : "Dentro del rango esperado"}</td></tr>
            <tr><td>Período</td><td>{r.periodo}</td><td>Trimestre de análisis</td></tr>
          </tbody>
        </table>

        {defor && (
          <>
            <div className="grid">
              <div className="card">
                <h3>Pérdida de Bosque 2025</h3>
                <div className="valor">{defor.deforestacion_2025?.toFixed(0)} ha</div>
                <div className="sub">Deforestación en el año más reciente</div>
              </div>
              <div className="card">
                <h3>Pérdida Total (5 años)</h3>
                <div className="valor">{defor.deforestacion_total_5y?.toFixed(0)} ha</div>
                <div className="sub">Acumulado 2021–2025</div>
              </div>
              <div className="card">
                <h3>Pérdida Total (10 años)</h3>
                <div className="valor">{defor.deforestacion_total_10y?.toFixed(0)} ha</div>
                <div className="sub">Acumulado 2016–2025</div>
              </div>
              <div className="card">
                <h3>Tendencia</h3>
                <div className="valor">{defor.deforestacion_tendencia_label}</div>
                <div className="sub">Basada en datos GFW/Hansen 2001–2025</div>
              </div>
            </div>
          </>
        )}

        {ndvi?.data?.length > 0 && (
          <div className="card" style={{ marginBottom: 24 }}>
            <h3>Salud de la Vegetación (NDVI Satelital)</h3>
            <p>Último NDVI: <strong>{ndvi.data[0].ndvi?.toFixed(3)}</strong> ({ndvi.data[0].periodo})</p>
            {ndvi.data[0].anomalia != null && (
              <p>Anomalía de vegetación: <strong>{ndvi.data[0].anomalia.toFixed(1)}%</strong></p>
            )}
            <p style={{ fontSize: 12, color: "#666", marginTop: 8 }}>Vegetación más débil de lo normal sugiere posible estrés de cultivos. Fuente: MODIS (Terra/Aqua).</p>
          </div>
        )}

        {multiAgent?.agentes && (
          <div style={{ marginBottom: 24 }}>
            <h3 style={{ marginBottom: 8 }}>Análisis Multi-Agente</h3>
            <div className="grid">
              {multiAgent.agentes.map((a, i) => (
                <div key={i} className="card" style={{ fontSize: 13 }}>
                  <strong>{a.agente}:</strong> nivel <em>{a.nivel}</em>
                  {a.hallazgos?.length > 0 && (
                    <ul style={{ margin: "6px 0 0 0", paddingLeft: 16, fontSize: 12, color: "#555" }}>
                      {a.hallazgos.map((h, j) => <li key={j}>{h}</li>)}
                    </ul>
                  )}
                </div>
              ))}
            </div>
            {multiAgent.coordinador && (
              <div className="card" style={{ background: "#fff3e0", marginTop: 8 }}>
                <strong>Coordinador ({multiAgent.coordinador.prioridad}):</strong> {multiAgent.coordinador.resumen}
              </div>
            )}
          </div>
        )}

        <h3 style={{ marginBottom: 12 }}>Análisis Generado por IA</h3>
        <div className="reporte-texto">{reporte}</div>

        <div className="footer">
          <p>Alerta — Plataforma de Alerta Temprana para Riesgo Climático Agrícola en Colombia</p>
          <p>Generado el {new Date().toLocaleDateString("es-CO")} | Datos: IDEAM, DANE, UPRA, IGAC</p>
        </div>
      </body>
    </html>
  );
}
