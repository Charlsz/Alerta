"use client";
import { useState } from "react";
import FilterBar from "@/app/components/FilterBar";
import Map from "@/app/components/Map";
import Ranking from "@/app/components/Ranking";
import MunicipioCard from "@/app/components/MunicipioCard";

export default function Home() {
  const [cultivo, setCultivo] = useState("");
  const [departamento, setDepartamento] = useState("");
  const [selected, setSelected] = useState(null);

  const handleFilter = (key, val) => {
    if (key === "cultivo") setCultivo(val);
    if (key === "departamento") setDepartamento(val);
  };

  return (
    <main style={{ maxWidth: 1200, margin: "0 auto", padding: 24, fontFamily: "system-ui" }}>
      <h1 style={{ marginBottom: 16 }}>Alerta — Riesgo Climático Agrícola</h1>
      <FilterBar cultivo={cultivo} departamento={departamento} onChange={handleFilter} />
      <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: 16 }}>
        <Map onSelect={setSelected} />
        <MunicipioCard codigo={selected} />
      </div>
      <Ranking cultivo={cultivo} departamento={departamento} onSelect={setSelected} />
    </main>
  );
}
