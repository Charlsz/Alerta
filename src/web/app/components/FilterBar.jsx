"use client";
import useAPI from "../hooks/useAPI";

export default function FilterBar({ cultivo, departamento, onChange }) {
  const { data } = useAPI("/api/filters");

  return (
    <div className="filters">
      <select className="filter-select" value={cultivo || ""} onChange={(e) => onChange("cultivo", e.target.value)}>
        <option value="">Todos los cultivos</option>
        {(data?.cultivos || []).map((c) => <option key={c} value={c}>{c}</option>)}
      </select>
      <select className="filter-select" value={departamento || ""} onChange={(e) => onChange("departamento", e.target.value)}>
        <option value="">Todos los departamentos</option>
        {(data?.departamentos || []).map((d) => <option key={d} value={d}>{d}</option>)}
      </select>
    </div>
  );
}
