"use client";
import useAPI from "../hooks/useAPI";
import RiskBadge from "./RiskBadge";

export default function Ranking({ cultivo, departamento, onSelect }) {
  const params = new URLSearchParams({ limit: 50 });
  if (cultivo) params.set("cultivo", cultivo);
  if (departamento) params.set("departamento", departamento);
  const { data, loading } = useAPI(`/api/ranking?${params}`);

  if (loading) return <p>Cargando ranking...</p>;
  if (!data?.data?.length) return <p>Sin datos.</p>;

  return (
    <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
      <thead>
        <tr style={{ textAlign: "left", borderBottom: "2px solid #ddd" }}>
          <th>#</th><th>Municipio</th><th>Depto</th><th>Cultivo</th><th>IRA</th><th>Nivel</th><th>Anomalía</th>
        </tr>
      </thead>
      <tbody>
        {data.data.map((r, i) => (
          <tr
            key={`${r.codigo_municipio}-${r.cultivo}`}
            onClick={() => onSelect?.(r.codigo_municipio)}
            style={{ cursor: "pointer", borderBottom: "1px solid #eee" }}
          >
            <td>{i + 1}</td>
            <td>{r.nombre_municipio || r.codigo_municipio}</td>
            <td>{r.nombre_departamento || "—"}</td>
            <td>{r.cultivo}</td>
            <td>{r.ira_score?.toFixed(3)}</td>
            <td><RiskBadge nivel={r.ira_nivel} /></td>
            <td>{r.anomaly_score != null ? r.anomaly_score.toFixed(2) : "—"}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
