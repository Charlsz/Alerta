"use client";
import useAPI from "../hooks/useAPI";
import RiskBadge from "./RiskBadge";

export default function MunicipioCard({ codigo }) {
  const { data, loading } = useAPI(codigo ? `/api/municipio/${codigo}` : null);

  if (!codigo) return <p>Selecciona un municipio en el mapa o ranking.</p>;
  if (loading) return <p>Cargando...</p>;
  if (!data?.data?.length) return <p>Sin datos para este municipio.</p>;

  const r = data.data[0];
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
          <tr><td>Rendimiento predicho</td><td>{r.rendimiento_predicho != null ? `${r.rendimiento_predicho} t/ha` : "—"}</td></tr>
        </tbody>
      </table>
    </div>
  );
}
